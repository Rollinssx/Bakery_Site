# base/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import Product, Category, CartItem, ContactMessage, SiteSettings


from base.models import (
    Category, Product, NewsletterSubscriber, ContactMessage,
    Order, OrderItem, SiteSettings
)
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    NewsletterSubscriberSerializer, ContactMessageSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderItemSerializer,
    SiteSettingsSerializer, BestSellerProductSerializer,
    FeaturedCategorySerializer, NewsletterSubscriptionSerializer,
    ContactFormSerializer
)


# Template Views

def home(request):
    """Home page view"""
    context = {
        'site_settings': SiteSettings.objects.first(),
        'featured_products': Product.objects.filter(is_featured=True)[:6],
        'categories': Category.objects.all(),
    }
    return render(request, 'base/home.html', context)


def products(request):
    """Products page view with filtering"""
    category_filter = request.GET.get('category', 'all')
    search_query = request.GET.get('search', '')

    products = Product.objects.filter(is_active=True)

    # Filter by category
    if category_filter and category_filter != 'all':
        products = products.filter(category__slug=category_filter)

    # Filter by search query
    if search_query:
        products = products.filter(
            name__icontains=search_query
        ) | products.filter(
            description__icontains=search_query
        )

    context = {
        'site_settings': SiteSettings.objects.first(),
        'products': products,
        'categories': Category.objects.all(),
        'current_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'base/products.html', context)


def product_detail(request, pk):
    """Individual product detail page"""
    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    product = get_object_or_404(Product, pk=pk, is_available=True)

    # Get related products from the same category
    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(pk=product.pk)[:4]

    context = {
        'site_settings': site_settings,
        'product': product,
        'related_products': related_products,
    }

    return render(request, 'base/product_detail.html', context)


def category_products(request, pk):
    """Products filtered by specific category"""
    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    category = get_object_or_404(Category, pk=pk)

    products_queryset = Product.objects.filter(
        category=category,
        is_available=True
    ).select_related('category')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products_queryset = products_queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(products_queryset, 12)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    context = {
        'site_settings': site_settings,
        'category': category,
        'products': products_page,
        'search_query': search_query,
    }

    return render(request, 'base/category_products.html', context)


def contact(request):
    """Contact page view"""
    context = {
        'site_settings': SiteSettings.objects.first(),
    }
    return render(request, 'base/contact.html', context)


def checkout(request):
    return render(request, 'base/checkout.html')


def contact_submit(request):
    """Handle contact form submission"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Save to database
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        # Send email notification (optional)
        try:
            send_mail(
                subject=f'Contact Form: {subject}',
                message=f'From: {name} ({email})\n\n{message}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent successfully!')
        except Exception as e:
            messages.success(request, 'Your message has been saved. We will get back to you soon!')

        return redirect('contact')

    return redirect('contact')


def cart(request):
    """Cart page view"""
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
        subtotal = sum(item.get_total_price() for item in cart_items)
        shipping = 5.00 if subtotal > 0 else 0
        total = subtotal + shipping
    else:
        # Handle session-based cart for anonymous users
        cart = request.session.get('cart', {})
        cart_items = []
        for product_id, quantity in cart.items():
            try:
                product = Product.objects.get(id=product_id)
                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'total_price': product.price * quantity
                })
            except Product.DoesNotExist:
                continue

        subtotal = sum(item['total_price'] for item in cart_items)
        shipping = 5.00 if subtotal > 0 else 0
        total = subtotal + shipping

    context = {
        'site_settings': SiteSettings.objects.first(),
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'base/cart.html', context)


def newsletter_subscribe(request):
    """Handle newsletter subscriptions"""
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        if email:
            newsletter_subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True
                }
            )

            if created:
                messages.success(request, 'Successfully subscribed to our newsletter!')
            else:
                if newsletter_subscriber.is_active:
                    messages.info(request, 'You are already subscribed to our newsletter.')
                else:
                    newsletter_subscriber.is_active = True
                    newsletter_subscriber.save()
                    messages.success(request, 'Welcome back! You have been resubscribed to our newsletter.')
        else:
            messages.error(request, 'Please provide a valid email address.')

    return redirect('home')


def about(request):
    """About page view"""
    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        'site_settings': site_settings,
    }

    return render(request, 'base/about.html', context)


def tests(request):
    """Test page"""
    return render(request, 'base/tests.html')


# API ViewSets (keep existing ones)

class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product categories
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category_type', 'is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured categories with their products"""
        featured_categories = Category.objects.filter(is_featured=True).prefetch_related('products')
        serializer = FeaturedCategorySerializer(featured_categories, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products
    """
    queryset = Product.objects.select_related('category').all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_best_seller', 'is_available', 'is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-is_best_seller', 'name']

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_queryset(self):
        """Filter out unavailable products for non-authenticated users"""
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_available=True)
        return queryset

    @action(detail=False, methods=['get'])
    def best_sellers(self, request):
        """Get best selling products"""
        best_sellers = self.get_queryset().filter(is_best_seller=True, is_available=True)[:6]
        serializer = BestSellerProductSerializer(best_sellers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        featured = self.get_queryset().filter(is_featured=True, is_available=True)
        serializer = BestSellerProductSerializer(featured, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get products grouped by category"""
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response({'error': 'category_id parameter is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        products = self.get_queryset().filter(category_id=category_id, is_available=True)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search functionality"""
        query = request.query_params.get('q', '')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        category_id = request.query_params.get('category')

        queryset = self.get_queryset().filter(is_available=True)

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)


class NewsletterSubscriberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing newsletter subscribers
    """
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    permission_classes = [IsAuthenticated]  # Only authenticated users can manage subscribers
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['email', 'subscribed_at']
    ordering = ['-subscribed_at']

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def subscribe(self, request):
        """Public endpoint for newsletter subscription"""
        serializer = NewsletterSubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Successfully subscribed to newsletter!',
                'email': serializer.validated_data['email']
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def unsubscribe(self, request, pk=None):
        """Unsubscribe a user"""
        subscriber = get_object_or_404(NewsletterSubscriber, pk=pk)
        subscriber.is_active = False
        subscriber.save()
        return Response({'message': 'Successfully unsubscribed'})

    @action(detail=False, methods=['get'])
    def active_count(self, request):
        """Get count of active subscribers"""
        count = NewsletterSubscriber.objects.filter(is_active=True).count()
        return Response({'active_subscribers': count})


class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contact messages
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAuthenticated]  # Only authenticated users can view messages
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_read']
    search_fields = ['name', 'email', 'subject', 'message']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def submit(self, request):
        """Public endpoint for contact form submission"""
        serializer = ContactFormSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Your message has been sent successfully! We will get back to you soon.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark message as read"""
        message = get_object_or_404(ContactMessage, pk=pk)
        message.is_read = True
        message.save()
        return Response({'message': 'Message marked as read'})

    @action(detail=True, methods=['post'])
    def mark_as_unread(self, request, pk=None):
        """Mark message as unread"""
        message = get_object_or_404(ContactMessage, pk=pk)
        message.is_read = False
        message.save()
        return Response({'message': 'Message marked as unread'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread messages"""
        count = ContactMessage.objects.filter(is_read=False).count()
        return Response({'unread_messages': count})


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders
    """
    queryset = Order.objects.prefetch_related('items__product').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['order_number', 'customer_name', 'customer_email']
    ordering_fields = ['created_at', 'delivery_date', 'total_amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm an order"""
        order = get_object_or_404(Order, pk=pk)
        order.status = 'confirmed'
        order.save()
        return Response({'message': f'Order #{order.order_number} confirmed'})

    @action(detail=True, methods=['post'])
    def start_progress(self, request, pk=None):
        """Mark order as in progress"""
        order = get_object_or_404(Order, pk=pk)
        order.status = 'in_progress'
        order.save()
        return Response({'message': f'Order #{order.order_number} is now in progress'})

    @action(detail=True, methods=['post'])
    def mark_ready(self, request, pk=None):
        """Mark order as ready"""
        order = get_object_or_404(Order, pk=pk)
        order.status = 'ready'
        order.save()
        return Response({'message': f'Order #{order.order_number} is ready'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark order as completed"""
        order = get_object_or_404(Order, pk=pk)
        order.status = 'completed'
        order.save()
        return Response({'message': f'Order #{order.order_number} completed'})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get order statistics"""
        from django.db.models import Count, Sum

        stats = Order.objects.aggregate(
            total_orders=Count('id'),
            pending_orders=Count('id', filter=Q(status='pending')),
            completed_orders=Count('id', filter=Q(status='completed')),
            total_revenue=Sum('total_amount', filter=Q(status='completed'))
        )

        return Response(stats)


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing order items
    """
    queryset = OrderItem.objects.select_related('order', 'product').all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['order', 'product']


class SiteSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing site settings
    """
    queryset = SiteSettings.objects.all()
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def public(self, request):
        """Get public site settings (for frontend)"""
        try:
            settings = SiteSettings.objects.first()
            if settings:
                # Return only public fields
                public_data = {
                    'business_name': settings.business_name,
                    'hero_headline': settings.hero_headline,
                    'hero_subheadline': settings.hero_subheadline,
                    'about_title': settings.about_title,
                    'about_description': settings.about_description,
                    'address': settings.address,
                    'email': settings.email,
                    'phone': settings.phone,
                    'opening_hours': settings.opening_hours,
                    'facebook_url': settings.facebook_url,
                    'instagram_url': settings.instagram_url,
                    'twitter_url': settings.twitter_url,
                    'minimum_order_notice': settings.minimum_order_notice,
                }
                return Response(public_data)
            return Response({'error': 'Site settings not configured'},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Additional utility views

class DashboardStatsView(viewsets.ViewSet):
    """
    ViewSet for dashboard statistics
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get overview statistics for admin dashboard"""
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta

        # Get date ranges
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        stats = {
            'products': {
                'total': Product.objects.count(),
                'available': Product.objects.filter(is_available=True).count(),
                'best_sellers': Product.objects.filter(is_best_seller=True).count(),
                'low_stock': Product.objects.filter(stock_quantity__lte=5).count(),
            },
            'orders': {
                'total': Order.objects.count(),
                'pending': Order.objects.filter(status='pending').count(),
                'this_week': Order.objects.filter(created_at__date__gte=week_ago).count(),
                'this_month': Order.objects.filter(created_at__date__gte=month_ago).count(),
                'total_revenue': Order.objects.filter(status='completed').aggregate(
                    total=Sum('total_amount'))['total'] or 0,
            },
            'subscribers': {
                'total': NewsletterSubscriber.objects.count(),
                'active': NewsletterSubscriber.objects.filter(is_active=True).count(),
                'this_week': NewsletterSubscriber.objects.filter(
                    subscribed_at__date__gte=week_ago).count(),
            },
            'messages': {
                'total': ContactMessage.objects.count(),
                'unread': ContactMessage.objects.filter(is_read=False).count(),
                'this_week': ContactMessage.objects.filter(
                    created_at__date__gte=week_ago).count(),
            }
        }

        return Response(stats)
    
