# context_processors.py - Create this file in your app directory
from .models import SiteSettings, Category, CartItem


def site_settings(request):
    """Make site settings available in all templates"""
    try:
        settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        settings = None

    return {
        'site_settings': settings
    }


def cart_count(request):
    """Make cart count available in all templates"""
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user).count()
    else:
        cart = request.session.get('cart', {})
        count = len(cart)

    return {
        'cart_count': count
    }


def categories(request):
    """Make categories available in all templates"""
    return {
        'global_categories': Category.objects.filter(is_active=True)
    }

