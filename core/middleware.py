from django.shortcuts import redirect
from django.utils import timezone
from django.urls import reverse

class VendorBanMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.ban_status != 'NONE':
            # Check if temporary ban has expired
            if request.user.ban_status == 'PAUSED' and request.user.ban_expires_at and timezone.now() > request.user.ban_expires_at:
                request.user.ban_status = 'NONE'
                request.user.ban_reason = ''
                request.user.ban_expires_at = None
                request.user.save()
            else:
                # User is banned. Allow access ONLY to /logout/ and /banned/
                try:
                    allowed_paths = [reverse('logout'), reverse('banned_view')]
                    if request.path not in allowed_paths:
                        return redirect('banned_view')
                except:
                    pass

        return self.get_response(request)
