# base/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views, cart_views, admin_views, admin_urls
from .admin_views import admin_toggle_product_availability, admin_update_order_status, admin_order_detail

# API Router for ViewSets
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'newsletter', views.NewsletterSubscriberViewSet)
router.register(r'contact-messages', views.ContactMessageViewSet)
router.register(r'orders', views.OrderViewSet)
router.register(r'order-items', views.OrderItemViewSet)
router.register(r'site-settings', views.SiteSettingsViewSet)
router.register(r'dashboard', views.DashboardStatsView, basename='dashboard')

urlpatterns = [
    # Template views
    path('', views.home, name='home'),
    path('products/', views.products, name='products'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<int:pk>/', views.category_products, name='category_products'),
    path('contact/', views.contact, name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('about/', views.about, name='about'),
    path('cart/', views.cart, name='cart'),
    path('tests/', views.tests, name='tests'),

    # Checkout and order URLs
    path('checkout/', views.checkout, name='checkout'),
    path('order/confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),

    # Authentication URLs
    path('account/', views.authenticate_view, name='authenticate'),
    path('login/', views.authenticate_view, name='login'),
    path('signup/', views.authenticate_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),  # Optional

    # Admin panel URLs
    path('admin-panel/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/orders/', admin_views.admin_orders, name='admin_orders'),
    path('admin-panel/orders/<int:order_id>/', admin_views.admin_order_detail, name='admin_order_detail'),
    path('admin-panel/orders/<int:order_id>/update/', admin_views.admin_update_order_status, name='admin_update_order_status'),
    path('admin-panel/products/', admin_views.admin_products, name='admin_products'),
    path('admin-panel/products/edit/<int:product_id>/', admin_views.admin_edit_product, name='admin_edit_product'),
    path('admin-panel/products/add/', admin_views.admin_add_product, name='admin_add_product'),
    path('admin-panel/customers/', admin_views.admin_customers, name='admin_customers'),
    path('admin-panel/messages/', admin_views.admin_messages, name='admin_messages'),
    path('admin-panel/messages/<int:message_id>/mark-read/', admin_views.admin_mark_message_read, name='admin_mark_message_read'),
    path('admin-panel/messages/<int:message_id>/delete/', admin_views.admin_delete_message, name='admin_delete_message'),
    path('admin-panel/settings/', admin_views.admin_settings, name='admin_settings'),

    # Cart AJAX operations
    path('cart/add/<int:product_id>/', cart_views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', cart_views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/remove/<int:product_id>/', cart_views.remove_from_cart, name='remove_from_cart'),
    path('cart/count/', cart_views.cart_count, name='cart_count'),

    # Additional pages (add as needed)

    # API endpoints
    path('api/', include(router.urls)),
    path('api/products/<int:product_id>/toggle/', admin_toggle_product_availability, name='admin_toggle_product'),
    path('api/orders/<int:order_id>/status/', admin_update_order_status, name='admin_update_order_status'),
    path('admin/orders/<int:order_id>/detail/', admin_order_detail, name='admin_order_detail'),
]

# If you're including this in your main project urls.py, use:
# 
# # myproject/urls.py
# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('base.urls')),
# ]
# 
# # Serve media files during development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

