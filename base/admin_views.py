# base/admin_views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
import json

from base.models import Order, Product, NewsletterSubscriber, ContactMessage, SiteSettings


@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard view"""
    # Get statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    stats = {
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'confirmed_orders': Order.objects.filter(status='confirmed').count(),
        'completed_orders': Order.objects.filter(status='completed').count(),
        'cancelled_orders': Order.objects.filter(status='cancelled').count(),
        'total_revenue': Order.objects.filter(status='completed').aggregate(
            total=Sum('total_amount'))['total'] or 0,
        'this_week_orders': Order.objects.filter(created_at__date__gte=week_ago).count(),
        'this_month_orders': Order.objects.filter(created_at__date__gte=month_ago).count(),
        'total_products': Product.objects.count(),
        'active_products': Product.objects.filter(is_active=True).count(),
        'newsletter_subscribers': NewsletterSubscriber.objects.filter(is_active=True).count(),
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
    }

    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        'stats': stats,
        'site_settings': site_settings,
    }

    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def admin_orders(request):
    """Orders management view"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Base queryset
    orders = Order.objects.select_related().prefetch_related('items__product').all()

    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_email__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )

    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)

    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    # Order by newest first
    orders = orders.order_by('-created_at')

    # Pagination
    paginator = Paginator(orders, 25)  # 25 orders per page
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    # Get statistics for the filtered results
    stats = {
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'confirmed_orders': orders.filter(status='confirmed').count(),
        'completed_orders': orders.filter(status='completed').count(),
        'total_revenue': orders.filter(status='completed').aggregate(
            total=Sum('total_amount'))['total'] or 0,
    }

    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        'orders': orders_page,
        'stats': stats,
        'site_settings': site_settings,
        'current_filters': {
            'status': status_filter,
            'search': search_query,
            'date_from': date_from,
            'date_to': date_to,
        }
    }

    return render(request, 'admin/orders.html', context)


@staff_member_required
def admin_order_detail(request, order_id):
    """Order detail API endpoint"""
    try:
        order = get_object_or_404(Order, id=order_id)

        # Prepare order data
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'customer_name': order.customer_name,
            'customer_email': order.customer_email,
            'customer_phone': order.customer_phone,
            'total_amount': float(order.total_amount),
            'delivery_address': order.delivery_address,
            'special_instructions': order.special_instructions,
            'created_at': order.created_at.isoformat(),
            'delivery_date': order.delivery_date.isoformat(),
            'is_delivery': order.is_delivery,
            'items': []
        }

        # Add order items
        for item in order.items.all():
            order_data['items'].append({
                'id': item.id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price),
                'customization_notes': item.customization_notes,
            })

        return JsonResponse(order_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@staff_member_required
def admin_update_order_status(request, order_id):
    """Update order status"""
    if request.method == 'PATCH':
        try:
            order = get_object_or_404(Order, id=order_id)
            data = json.loads(request.body)
            new_status = data.get('status')

            if new_status in dict(Order.ORDER_STATUS_CHOICES):
                order.status = new_status
                order.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Order status updated to {new_status}',
                    'order_id': order.id,
                    'new_status': new_status
                })
            else:
                return JsonResponse({'error': 'Invalid status'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@staff_member_required
def admin_products(request):
    """Products management view"""
    # Get filter parameters
    category_filter = request.GET.get('category', '')
    availability_filter = request.GET.get('availability', '')
    search_query = request.GET.get('search', '')

    # Base queryset
    products = Product.objects.select_related('category').all()

    # Apply filters
    if category_filter:
        products = products.filter(category_id=category_filter)

    if availability_filter == 'available':
        products = products.filter(is_available=True)
    elif availability_filter == 'unavailable':
        products = products.filter(is_available=False)

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Order by name
    products = products.order_by('name')

    # Pagination
    paginator = Paginator(products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        'products': products_page,
        'site_settings': site_settings,
        'current_filters': {
            'category': category_filter,
            'availability': availability_filter,
            'search': search_query,
        }
    }

    return render(request, 'admin/products.html', context)


@staff_member_required
def admin_customers(request):
    """Customers management view"""
    # Get unique customers from orders
    customers = Order.objects.values(
        'customer_name',
        'customer_email',
        'customer_phone'
    ).annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount', filter=Q(status='completed')),
        last_order=timezone.now()
    ).order_by('-total_orders')

    # Pagination
    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    customers_page = paginator.get_page(page_number)

    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        'customers': customers_page,
        'site_settings': site_settings,
    }

    return render(request, 'admin/customers.html', context)


@staff_member_required
def admin_messages(request):
    """Messages management view"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')

    # Base queryset
    messages = ContactMessage.objects.all()

    # Apply filters
    if status_filter == 'read':
        messages = messages.filter(is_read=True)
    elif status_filter == 'unread':
        messages = messages.filter(is_read=False)

    if search_query:
        messages = messages.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query)
        )

    # Order by newest first
    messages = messages.order_by('-created_at')

    # Pagination
    paginator = Paginator(messages, 25)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)

    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        'messages': messages_page,
        'site_settings': site_settings,
        'current_filters': {
            'status': status_filter,
            'search': search_query,
        }
    }

    return render(request, 'admin/messages.html', context)


@staff_member_required
def admin_settings(request):
    """Settings management view"""
    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    if request.method == 'POST':
        # Handle settings update
        # This would typically use Django forms for better validation
        if site_settings:
            site_settings.business_name = request.POST.get('business_name', site_settings.business_name)
            site_settings.hero_headline = request.POST.get('hero_headline', site_settings.hero_headline)
            site_settings.hero_subheadline = request.POST.get('hero_subheadline', site_settings.hero_subheadline)
            site_settings.about_title = request.POST.get('about_title', site_settings.about_title)
            site_settings.about_description = request.POST.get('about_description', site_settings.about_description)
            site_settings.address = request.POST.get('address', site_settings.address)
            site_settings.email = request.POST.get('email', site_settings.email)
            site_settings.phone = request.POST.get('phone', site_settings.phone)
            site_settings.opening_hours = request.POST.get('opening_hours', site_settings.opening_hours)
            site_settings.facebook_url = request.POST.get('facebook_url', site_settings.facebook_url)
            site_settings.instagram_url = request.POST.get('instagram_url', site_settings.instagram_url)
            site_settings.twitter_url = request.POST.get('twitter_url', site_settings.twitter_url)
            site_settings.save()
        else:
            # Create new settings
            site_settings = SiteSettings.objects.create(
                business_name=request.POST.get('business_name', 'Sweet Delights'),
                hero_headline=request.POST.get('hero_headline', 'Pastries baked with love'),
                hero_subheadline=request.POST.get('hero_subheadline', 'The one-stop shop for all your bakery needs'),
                about_title=request.POST.get('about_title', 'About us'),
                about_description=request.POST.get('about_description', ''),
                address=request.POST.get('address', '123 Bakery Street\nNairobi, Kenya'),
                email=request.POST.get('email', 'contact@sweetdelights.com'),
                phone=request.POST.get('phone', '+254 700 123 456'),
                opening_hours=request.POST.get('opening_hours', 'Mon-Fri: 7AM-8PM\nSat-Sun: 8AM-9PM'),
                facebook_url=request.POST.get('facebook_url', ''),
                instagram_url=request.POST.get('instagram_url', ''),
                twitter_url=request.POST.get('twitter_url', ''),
            )

    context = {
        'site_settings': site_settings,
    }

    return render(request, 'admin/settings.html', context)

