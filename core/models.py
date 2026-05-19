from django.db import models
from django.contrib.auth.models import AbstractUser
import secrets
import string
import hashlib

class User(AbstractUser):
    ROLE_CHOICES = [
        ('BUYER', 'Buyer'),
        ('VENDOR', 'Vendor'),
        ('MODERATOR', 'Moderator'),
        ('ADMIN', 'Admin'),
    ]
    
    display_name = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='BUYER')
    pgp_public_key = models.TextField(blank=True, null=True)
    key_fingerprint = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Financial Keys
    xmr_multisig_pubkey = models.CharField(max_length=255, blank=True, null=True, help_text="The Vendor's Monero Public Spend Key for Multisig")
    
    # Trust Metrics
    trust_score = models.IntegerField(default=100)
    total_sales = models.PositiveIntegerField(default=0)
    vendor_level = models.PositiveIntegerField(default=1)

    # Vendor Verification & Governance
    VERIFICATION_CHOICES = [
        ('UNVERIFIED', 'Unverified'),
        ('PENDING', 'Pending Review'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default='UNVERIFIED', db_index=True)
    verification_proof = models.TextField(blank=True, help_text="PGP signed statement of intent, past marketplace rep links, or identity proof.")
    verification_notes = models.TextField(blank=True, help_text="Moderator feedback or rejection reasons visible to the vendor.")
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    verification_reviewed_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_vendors')

    @staticmethod
    def generate_uid():
        alphabet = string.ascii_uppercase + string.digits
        while True:
            uid = ''.join(secrets.choice(alphabet) for _ in range(8))
            if not User.objects.filter(username=uid).exists():
                return uid

    @staticmethod
    def get_fingerprint(key):
        return hashlib.sha256(key.encode()).hexdigest()

    def __str__(self):
        return f"{self.display_name} ({self.username})"

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price_xmr = models.DecimalField(max_digits=20, decimal_places=12)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products', limit_choices_to={'role': 'VENDOR'})
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    PRODUCT_TYPES = (
        ('PHYSICAL', 'Physical Good'),
        ('DIGITAL', 'Digital Asset'),
        ('ACCOUNT', 'Access Credentials'),
        ('SERVICE', 'Professional Service'),
    )

    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='PHYSICAL')
    specifications = models.JSONField(default=dict, blank=True)
    digital_content = models.TextField(blank=True)
    usage_instructions = models.TextField(blank=True)
    contact_handle = models.CharField(max_length=100, blank=True)
    
    is_escrow = models.BooleanField(default=True)
    available_qty = models.IntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True)
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending Verification'),
        ('ACTIVE', 'Active / Online'),
        ('SUSPENDED', 'Suspended'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Awaiting Payment'),
        ('PAID', 'Paid in Escrow'),
        ('SHIPPED', 'Shipped / Active'),
        ('DISPUTED', 'Disputed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_price_xmr = models.DecimalField(max_digits=20, decimal_places=12)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Fulfillment
    shipping_address_encrypted = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    
    # Financials
    escrow_address = models.CharField(max_length=100, blank=True)
    payment_id = models.CharField(max_length=64, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    auto_finalize_at = models.DateTimeField(null=True, blank=True)

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    content = models.TextField() # Encouraged to be PGP encrypted by user
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    content = models.TextField()
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Feedback(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='feedback')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='feedbacks')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_feedback')
    rating = models.PositiveIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.product.name} by {self.buyer.username}"

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class ViewedProduct(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='view_history')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='viewed_by')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
