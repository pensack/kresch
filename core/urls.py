from django.urls import path
from . import views

handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('browse/', views.browse, name='index'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('checkout/1/<int:product_id>/', views.checkout_step1, name='checkout_step1'),
    path('checkout/2/<int:order_id>/', views.checkout_step2, name='checkout_step2'),
    path('checkout/3/<int:order_id>/', views.checkout_step3, name='checkout_step3'),
    path('product/<int:product_id>/feedback/', views.add_feedback, name='add_feedback'),
    path('seller/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/settings/', views.update_vendor_settings, name='update_vendor_settings'),
    path('buyer/', views.buyer_dashboard, name='buyer_dashboard'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('bookmark/toggle/<int:product_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('mod/', views.mod_dashboard, name='mod_dashboard'),
    path('mod/category/', views.manage_category, name='manage_category'),
    path('mod/dispute/<int:order_id>/', views.resolve_dispute, name='resolve_dispute'),
    path('sysadmin/', views.admin_dashboard, name='admin_dashboard'),
    path('sysadmin/users/', views.admin_users, name='admin_users'),
    path('sysadmin/users/<int:user_id>/', views.admin_user_manage, name='admin_user_manage'),
    path('sysadmin/orders/', views.admin_orders, name='admin_orders'),
    path('sysadmin/orders/<int:order_id>/', views.admin_order_manage, name='admin_order_manage'),
    path('sysadmin/products/', views.admin_products, name='admin_products'),
    path('sysadmin/products/<int:product_id>/', views.admin_product_manage, name='admin_product_manage'),
    path('sysadmin/categories/', views.admin_categories, name='admin_categories'),
    path('messages/send/', views.send_message, name='send_message'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/<int:note_id>/', views.mark_read, name='mark_read'),
    path('sysadmin/role/<int:user_id>/', views.change_role, name='change_role'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
]
