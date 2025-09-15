"""
URL configuration for Bakery_Site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.documentation import include_docs_urls
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls
from base import views
import coreapi

# Create a router and register our viewsets
router = DefaultRouter()

# Register all ViewSets
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'newsletter-subscribers', views.NewsletterSubscriberViewSet, basename='newsletter-subscriber')
router.register(r'contact-messages', views.ContactMessageViewSet, basename='contact-message')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-items', views.OrderItemViewSet, basename='order-item')
router.register(r'site-settings', views.SiteSettingsViewSet, basename='site-settings')
router.register(r'dashboard', views.DashboardStatsView, basename='dashboard')


import base

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('base.urls')),
    # Additional custom endpoints (if needed)
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),

    # API documentation (optional)
    path('docs/', include_docs_urls(title='Pastries with Love API'))
]
