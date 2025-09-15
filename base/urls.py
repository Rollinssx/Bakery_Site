# base/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views, cart_views

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

    # Cart AJAX operations
    path('cart/add/<int:product_id>/', cart_views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', cart_views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/remove/<int:product_id>/', cart_views.remove_from_cart, name='remove_from_cart'),
    path('cart/count/', cart_views.cart_count, name='cart_count'),

    # Additional pages (add as needed)
    path('checkout/', views.checkout, name='checkout'),

    # API endpoints
    path('api/', include(router.urls)),
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

