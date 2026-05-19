from django.contrib import admin
from .models import User, Product, Category, Order, Feedback, Bookmark, ViewedProduct

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'display_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')
    search_fields = ('username', 'display_name')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'price_xmr', 'product_type', 'created_at')
    list_filter = ('product_type', 'is_escrow')
    search_fields = ('name', 'description')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'product', 'total_price_xmr', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'buyer__username', 'product__name')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('product', 'buyer', 'rating', 'created_at')
    list_filter = ('rating',)

admin.site.register(Bookmark)
admin.site.register(ViewedProduct)
