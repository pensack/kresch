from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import F
from .models import Product, Category, Order, User, Feedback, Bookmark, ViewedProduct, Message, Notification
import uuid
import json
import traceback

def csrf_failure(request, reason=""):
    return render(request, 'core/403_csrf.html', {'reason': reason}, status=403)

def handler500(request):
    return render(request, '500.html', status=500)

def handler404(request, exception):
    return render(request, '404.html', status=404)

print("\n>>> VIEWS.PY LOADED - VERSION 2.1 <<<\n")

def landing(request):
    return render(request, 'core/landing.html')

def browse(request):
    from django.db.models import Avg
    ptype = request.GET.get('type')
    
    products = Product.objects.filter(status='ACTIVE').select_related('vendor', 'category')
    if ptype:
        products = products.filter(product_type=ptype.upper())
        
    products = products.annotate(
        avg_rating=Avg('feedbacks__rating')
    ).order_by('-created_at')
    
    categories = Category.objects.filter(parent__isnull=True).prefetch_related('children', 'children__products')
    total_count = Product.objects.count()
    
    context = {
        'products': products,
        'categories': categories,
        'total_count': total_count,
    }
    return render(request, 'core/index.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('vendor', 'category'), pk=pk)
    
    if product.status != 'ACTIVE':
        if request.user != product.vendor and request.user.role not in ['MODERATOR', 'ADMIN']:
            return render(request, '404.html', {'reason': 'This product is pending verification or currently offline.'}, status=404)
    
    # Increment global views
    Product.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    
    # Record user view history if logged in
    if request.user.is_authenticated:
        ViewedProduct.objects.update_or_create(
            user=request.user, product=product
        )
    
    feedbacks = product.feedbacks.all().order_by('-created_at')
    
    # Calculate avg rating for vendor
    from django.db.models import Avg
    avg_rating = Feedback.objects.filter(product__vendor=product.vendor).aggregate(Avg('rating'))['rating__avg'] or 5.0
    trust_percentage = int((avg_rating / 5.0) * 100)
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(user=request.user, product=product).exists()
        
    context = {
        'product': product,
        'feedbacks': feedbacks,
        'avg_rating': avg_rating,
        'trust_percentage': trust_percentage,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'core/product_detail.html', context)

@login_required
def toggle_bookmark(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, product=product)
    if not created:
        bookmark.delete()
        return JsonResponse({'status': 'removed'})
    return JsonResponse({'status': 'added'})

@login_required
def add_feedback(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        # Feedback now requires an associated order
        order = Order.objects.filter(product=product, buyer=request.user, status='COMPLETED').last()
        if not order:
             return redirect('product_detail', pk=product_id)
            
        Feedback.objects.create(
            order=order,
            product=product,
            buyer=request.user,
            rating=request.POST.get('rating', 5),
            comment=request.POST.get('comment', '')
        )
        return redirect('product_detail', pk=product_id)
    return redirect('index')

@login_required
def seller_dashboard(request):
    if request.user.role not in ['VENDOR', 'ADMIN']:
        return redirect('index')
    
    if request.method == 'POST':
        spec_raw = request.POST.get('specifications', '{}')
        try:
            specs = json.loads(spec_raw)
        except:
            specs = {}
            
        Product.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            price_xmr=request.POST.get('price_xmr'),
            price_usd=request.POST.get('price_usd') or None,
            vendor=request.user,
            category=get_object_or_404(Category, id=request.POST.get('category')),
            product_type=request.POST.get('product_type', 'PHYSICAL'),
            digital_content=request.POST.get('digital_content', ''),
            usage_instructions=request.POST.get('usage_instructions', ''),
            image=request.FILES.get('image'),
            status='PENDING'
        )
        return redirect('seller_dashboard')
        
    my_products = Product.objects.filter(vendor=request.user).select_related('category').order_by('-created_at')
    my_orders = Order.objects.filter(product__vendor=request.user).select_related('buyer', 'product').order_by('-created_at')
    categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')
    pending_count = my_products.filter(status='PENDING').count()
    
    context = {
        'my_products': my_products,
        'my_orders': my_orders,
        'categories': categories,
        'pending_count': pending_count,
    }
    return render(request, 'core/seller_dashboard.html', context)

@login_required
def update_vendor_settings(request):
    if request.user.role != 'VENDOR':
        return redirect('index')
        
    if request.method == 'POST':
        request.user.xmr_multisig_pubkey = request.POST.get('xmr_multisig_pubkey')
        request.user.pgp_public_key = request.POST.get('pgp_public_key')
        request.user.save()
        
        Notification.objects.create(
            user=request.user,
            title="Terminal Sync Successful",
            content="Your Multisig and PGP keys have been synchronized. Your listings are now active.",
            link="/seller/"
        )
        
    return redirect('seller_dashboard')

@login_required
def submit_verification(request):
    if request.user.role != 'VENDOR':
        return redirect('index')
        
    if request.method == 'POST':
        request.user.verification_proof = request.POST.get('verification_proof', '')
        request.user.verification_status = 'PENDING'
        from django.utils import timezone
        request.user.verification_submitted_at = timezone.now()
        request.user.save()
        
        Notification.objects.create(
            user=request.user,
            title="Verification Submitted",
            content="Your application has been received and is currently under review by our moderation team.",
            link="/seller/"
        )
        
    return redirect('seller_dashboard')

@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, vendor=request.user)
    if request.method == 'POST':
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        product.price_xmr = request.POST.get('price_xmr', product.price_xmr)
        if request.POST.get('price_usd'):
            product.price_usd = request.POST.get('price_usd')
        if request.POST.get('available_qty'):
            product.available_qty = request.POST.get('available_qty')
            
        # If product was FIX_REQUIRED, reset to PENDING for moderator re-review
        if product.status == 'FIX_REQUIRED':
            product.status = 'PENDING'
            Notification.objects.create(
                user=request.user,
                title="Remediation Submitted",
                content=f"Your edits for '{product.name}' have been submitted for moderator re-review.",
                link="/seller/#listings"
            )
            
        product.save()
    return redirect('seller_dashboard')

@login_required
def duplicate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, vendor=request.user)
    Product.objects.create(
        name=f"Copy of {product.name}",
        description=product.description,
        price_xmr=product.price_xmr,
        price_usd=product.price_usd,
        vendor=request.user,
        category=product.category,
        product_type=product.product_type,
        digital_content=product.digital_content,
        usage_instructions=product.usage_instructions,
        status='PENDING'
    )
    return redirect('seller_dashboard')

@login_required
def export_inventory(request):
    if request.user.role != 'VENDOR':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Type', 'Price_XMR', 'Price_USD', 'Status', 'Views', 'Created'])
    for p in Product.objects.filter(vendor=request.user):
        writer.writerow([p.id, p.name, p.product_type, p.price_xmr, p.price_usd, p.status, p.views_count, p.created_at])
    return response

@login_required
def buyer_dashboard(request):
    orders = Order.objects.filter(buyer=request.user).select_related('product', 'product__vendor').order_by('-created_at')
    bookmarks = Bookmark.objects.filter(user=request.user).select_related('product', 'product__vendor').order_by('-created_at')
    viewed = ViewedProduct.objects.filter(user=request.user).select_related('product', 'product__vendor').order_by('-viewed_at')[:20]
    
    context = {
        'orders': orders,
        'bookmarks': bookmarks,
        'viewed_products': viewed,
    }
    return render(request, 'core/buyer_dashboard.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Check if user is buyer, vendor, or staff
    if request.user != order.buyer and request.user != order.product.vendor and request.user.role not in ['MODERATOR', 'ADMIN']:
        return redirect('index')
        
    return render(request, 'core/order_detail.html', {'order': order})

@login_required
def mod_dashboard(request):
    if request.user.role not in ['MODERATOR', 'ADMIN']:
        return render(request, '404.html', {'reason': 'Insufficient terminal clearance.'}, status=404)
    
    users = User.objects.all().order_by('-date_joined')
    from django.db.models import Count
    products = Product.objects.all().select_related('vendor', 'category').annotate(orders_count=Count('order'))
    
    # Sub-tab querysets for Catalog Management
    pending_products = products.filter(status='PENDING').order_by('created_at')
    approved_products = products.filter(status='ACTIVE').order_by('-created_at')
    all_products = products.all()
    
    # Advanced sorting and filtering for 'All' tab
    sort_param = request.GET.get('sort', 'new')
    if sort_param == 'new':
        all_products = all_products.order_by('-created_at')
    elif sort_param == 'views':
        all_products = all_products.order_by('-views_count')
    elif sort_param == 'purchases':
        all_products = all_products.order_by('-orders_count')
        
    ptype_param = request.GET.get('ptype')
    if ptype_param:
        all_products = all_products.filter(product_type=ptype_param.upper())
        
    orders = Order.objects.all().select_related('product', 'buyer', 'product__vendor').order_by('-created_at')
    categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')
    
    disputed_orders = orders.filter(status='DISPUTED')
    pending_vendors = User.objects.filter(role='VENDOR', verification_status='PENDING').order_by('-verification_submitted_at')
    
    context = {
        'users': users,
        'products': products,
        'pending_products': pending_products,
        'approved_products': approved_products,
        'all_products': all_products,
        'sort_param': sort_param,
        'ptype_param': ptype_param,
        'orders': orders,
        'categories': categories,
        'disputed_orders': disputed_orders,
        'pending_vendors': pending_vendors,
    }
    return render(request, 'core/mod_dashboard.html', context)

@login_required
def mod_manage_product(request, product_id):
    if request.user.role not in ['MODERATOR', 'ADMIN']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'APPROVE':
            product.status = 'ACTIVE'
            product.mod_notes = notes
            product.save()
            Notification.objects.create(
                user=product.vendor,
                title="Product Approved",
                content=f"Your listing '{product.name}' has been approved and is now live in the catalog.",
                link=f"/product/{product.id}/"
            )
        elif action == 'REJECT':
            product.status = 'REJECTED'
            product.mod_notes = notes
            product.save()
            Notification.objects.create(
                user=product.vendor,
                title="Listing Rejected",
                content=f"Your listing '{product.name}' was rejected. Reason: {notes}",
                link="/seller/#listings"
            )
        elif action == 'TAKE_DOWN_FIX':
            product.status = 'FIX_REQUIRED'
            product.mod_notes = notes
            product.save()
            Notification.objects.create(
                user=product.vendor,
                title="Listing Suspended (Fix Required)",
                content=f"Your listing '{product.name}' was taken down. Reason: {notes}. Please edit the listing to resolve these issues.",
                link="/seller/#listings"
            )
        elif action == 'TAKE_DOWN_PERM':
            product.status = 'SUSPENDED'
            product.mod_notes = notes
            product.save()
            Notification.objects.create(
                user=product.vendor,
                title="Listing Permanently Suspended",
                content=f"Your listing '{product.name}' has been permanently removed by a moderator. Reason: {notes}",
                link="/seller/#listings"
            )
            
    return redirect('mod_dashboard')

@login_required
def manage_category(request):
    if request.user.role not in ['MODERATOR', 'ADMIN']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        parent_id = request.POST.get('parent_id')
        
        parent = None
        if parent_id:
            parent = get_object_or_404(Category, id=parent_id)
            
        Category.objects.create(name=name, parent=parent)
        return redirect('mod_dashboard')
    return redirect('mod_dashboard')

@login_required
def mod_verify_vendor(request, vendor_id):
    if request.user.role not in ['MODERATOR', 'ADMIN']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    vendor = get_object_or_404(User, id=vendor_id, role='VENDOR')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        from django.utils import timezone
        
        if action == 'APPROVE':
            vendor.verification_status = 'VERIFIED'
            vendor.verification_notes = notes
            vendor.verified_by = request.user
            vendor.verification_reviewed_at = timezone.now()
            vendor.save()
            
            Product.objects.filter(vendor=vendor, status='PENDING').update(status='ACTIVE')
            
            Notification.objects.create(
                user=vendor,
                title="Vendor Verification Approved",
                content="Congratulations! Your account verification has been approved by a moderator. You can now publish inventory.",
                link="/seller/"
            )
        elif action == 'REJECT':
            vendor.verification_status = 'REJECTED'
            vendor.verification_notes = notes
            vendor.save()
            
            Notification.objects.create(
                user=vendor,
                title="Verification Application Rejected",
                content=f"Your verification application was rejected. Reason: {notes}",
                link="/seller/"
            )
        elif action == 'REVOKE':
            vendor.verification_status = 'UNVERIFIED'
            vendor.verification_notes = notes
            vendor.verified_by = None
            vendor.save()
            
            Product.objects.filter(vendor=vendor, status='ACTIVE').update(status='PENDING')
            
            Notification.objects.create(
                user=vendor,
                title="Verification Revoked",
                content=f"Your vendor verification has been revoked by a moderator. Reason: {notes}. All active listings have been suspended.",
                link="/seller/"
            )
            
    return redirect('mod_dashboard')

@login_required
def banned_view(request):
    if request.user.ban_status == 'NONE':
        return redirect('index')
    return render(request, 'core/ban_screen.html')

@login_required
def mod_ban_vendor(request, vendor_id):
    if request.user.role not in ['MODERATOR', 'ADMIN']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    vendor = get_object_or_404(User, id=vendor_id, role='VENDOR')
    if request.method == 'POST':
        preset = request.POST.get('preset_reason', '')
        custom = request.POST.get('custom_reason', '')
        item_link = request.POST.get('item_link', '')
        duration = request.POST.get('duration', 'PERMANENT')
        
        full_reason = f"{preset}. {custom}".strip('. ')
        if item_link:
            full_reason += f"\nOffending Item / Reference: {item_link}"
            
        from django.utils import timezone
        from datetime import timedelta
        
        if duration == 'PERMANENT':
            vendor.ban_status = 'PERMANENT'
            vendor.ban_expires_at = None
        else:
            vendor.ban_status = 'PAUSED'
            if duration == '1_WEEK':
                vendor.ban_expires_at = timezone.now() + timedelta(days=7)
            elif duration == '1_MONTH':
                vendor.ban_expires_at = timezone.now() + timedelta(days=30)
            elif duration == '3_MONTHS':
                vendor.ban_expires_at = timezone.now() + timedelta(days=90)
                
        vendor.ban_reason = full_reason
        vendor.save()
        
        # Suspend all vendor products immediately
        Product.objects.filter(vendor=vendor).update(status='SUSPENDED')
        
    return redirect('mod_dashboard')

@login_required
def resolve_dispute(request, order_id):
    if request.user.role not in ['MODERATOR', 'ADMIN']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    order = get_object_or_404(Order, id=order_id)
    action = request.POST.get('action') # 'RELEASE' or 'REFUND'
    
    if action == 'RELEASE':
        order.status = 'COMPLETED'
        # Logic to sign 2-of-3 multisig towards vendor
    elif action == 'REFUND':
        order.status = 'CANCELLED'
        # Logic to sign 2-of-3 multisig towards buyer
        
    order.save()
    return redirect('mod_dashboard')

@login_required
def checkout_step1(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if product.status != 'ACTIVE':
        return render(request, '404.html', {
            'reason': 'This product is pending verification or currently inactive and cannot be purchased.'
        }, status=403)
    
    # 1. Critical Key Check
    if not product.vendor.xmr_multisig_pubkey:
        return render(request, '404.html', {
            'reason': 'COMMUNICATIONS LINK FAILURE: The vendor has not initialized their Multisig Terminal. Purchase protocol aborted.'
        }, status=403)

    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 1))
        delivery_data = request.POST.get('delivery_data', '')
        
        order = Order.objects.create(
            buyer=request.user,
            product=product,
            quantity=qty,
            status='PENDING',
            shipping_address_encrypted=delivery_data,
            total_price_xmr=product.price_xmr * qty,
            # Placeholder for future monero-wallet-rpc integration
            escrow_address=f"8{uuid.uuid4().hex[:32]}" 
        )
        
        # Notify Vendor
        Notification.objects.create(
            user=product.vendor,
            title="New Order Pending",
            content=f"User {request.user.username} has initiated an order for {product.name}.",
            link=f"/seller/#orders"
        )
        
        return redirect('checkout_step2', order_id=order.id)
        
    return render(request, 'core/checkout_step1.html', {'product': product})

@login_required
def checkout_step2(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    return render(request, 'core/checkout_step2.html', {'order': order})

@login_required
def checkout_step3(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    order.status = 'PAID'
    order.save()
    
    # Notify Vendor
    Notification.objects.create(
        user=order.product.vendor,
        title="Payment Received",
        content=f"Escrow payment confirmed for Order #{order.id}.",
        link=f"/seller/#orders"
    )
    
    return render(request, 'core/checkout_step3.html', {'order': order})

@login_required
def send_message(request):
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        order_id = request.POST.get('order_id')
        content = request.POST.get('content')
        
        recipient = get_object_or_404(User, id=recipient_id)
        order = get_object_or_404(Order, id=order_id) if order_id else None
        
        msg = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            order=order,
            content=content
        )
        
        Notification.objects.create(
            user=recipient,
            title="New Message",
            content=f"You have a new message from {request.user.username}.",
            link=f"/messages/{msg.id}/"
        )
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})

@login_required
def notifications(request):
    notes = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'core/notifications.html', {'notifications': notes})

@login_required
def mark_read(request, note_id):
    note = get_object_or_404(Notification, id=note_id, user=request.user)
    note.is_read = True
    note.save()
    return JsonResponse({'status': 'success'})

@login_required
def admin_dashboard(request):
    if request.user.role != 'ADMIN':
        return redirect('index')
    
    users = User.objects.all().order_by('-date_joined')
    total_sales = Order.objects.filter(status='COMPLETED').count()
    total_products = Product.objects.count()
    
    context = {
        'total_users': users.count(),
        'total_sales': total_sales,
        'total_products': total_products,
        'recent_users': users[:10],
    }
    return render(request, 'core/admin/dashboard.html', context)

@login_required
def admin_users(request):
    if request.user.role != 'ADMIN': return redirect('index')
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'core/admin/users.html', {'users': users, 'role_choices': User.ROLE_CHOICES})

@login_required
def admin_user_manage(request, user_id):
    if request.user.role != 'ADMIN': return redirect('index')
    target_user = get_object_or_404(User, id=user_id)
    orders = Order.objects.filter(models.Q(buyer=target_user) | models.Q(product__vendor=target_user)).order_by('-created_at')
    return render(request, 'core/admin/user_manage.html', {'target_user': target_user, 'orders': orders, 'role_choices': User.ROLE_CHOICES})

@login_required
def admin_orders(request):
    if request.user.role != 'ADMIN': return redirect('index')
    orders = Order.objects.all().select_related('product', 'buyer', 'product__vendor').order_by('-created_at')
    return render(request, 'core/admin/orders.html', {'orders': orders})

@login_required
def admin_order_manage(request, order_id):
    if request.user.role != 'ADMIN': return redirect('index')
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'core/admin/order_manage.html', {'order': order})

@login_required
def admin_products(request):
    if request.user.role != 'ADMIN': return redirect('index')
    products = Product.objects.all().select_related('vendor', 'category').order_by('-created_at')
    return render(request, 'core/admin/products.html', {'products': products})

@login_required
def admin_product_manage(request, product_id):
    if request.user.role != 'ADMIN': return redirect('index')
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'core/admin/product_manage.html', {'product': product})

@login_required
def admin_categories(request):
    if request.user.role != 'ADMIN': return redirect('index')
    categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')
    return render(request, 'core/admin/categories.html', {'categories': categories})

@login_required
def change_role(request, user_id):
    if request.user.role != 'ADMIN':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        target_user = get_object_or_404(User, id=user_id)
        if new_role in [choice[0] for choice in User.ROLE_CHOICES]:
            target_user.role = new_role
            if new_role == 'ADMIN':
                target_user.is_staff = True
                target_user.is_superuser = True
            else:
                target_user.is_staff = False
                target_user.is_superuser = False
            target_user.save()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})

def signup_view(request):
    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        role = request.POST.get('role', 'BUYER').upper()
        
        if not display_name or len(display_name) < 4:
            return render(request, 'core/signup.html', {'error': 'Handle must be at least 4 characters.'})
            
        import secrets
        bytes_key = secrets.token_bytes(32)
        private_key = ''.join(f'{b:02x}' for b in bytes_key).upper()
        
        uid = User.generate_uid()
        fingerprint = User.get_fingerprint(private_key)
        
        try:
            user = User.objects.create_user(
                username=uid,
                display_name=display_name,
                password=private_key,
                key_fingerprint=fingerprint,
                role=role
            )

            login(request, user)
            
            redirect_url = '/seller/' if role == 'VENDOR' else '/browse/'
            formatted_key = '-'.join(private_key[i:i+8] for i in range(0, len(private_key), 8))
            
            return render(request, 'core/signup_success.html', {
                'private_key': formatted_key, 
                'redirect_url': redirect_url
            })
        except Exception as e:
            traceback.print_exc()
            return render(request, 'core/signup.html', {'error': 'Terminal error during identity generation.'})

    return render(request, 'core/signup.html')

def login_view(request):
    if request.method == 'POST':
        private_key = request.POST.get('private_key', '').strip().replace('-', '').upper()
        if not private_key:
            return render(request, 'core/login.html', {'error': 'Master Key is required.'})
            
        fingerprint = User.get_fingerprint(private_key)
        
        try:
            user_obj = User.objects.get(key_fingerprint=fingerprint)
            user = authenticate(request, username=user_obj.username, password=private_key)
            if user is not None:
                login(request, user)
                if user.role == 'VENDOR': return redirect('seller_dashboard')
                elif user.role == 'MODERATOR': return redirect('mod_dashboard')
                elif user.role == 'ADMIN': return redirect('admin_dashboard')
                return redirect('index')
            else:
                return render(request, 'core/login.html', {'error': 'Key matches index, but authentication failed.'})
        except User.DoesNotExist:
            return render(request, 'core/login.html', {'error': 'Invalid Master Key. Access Denied.'})
            
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('landing')
