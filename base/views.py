# base/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
import uuid
from .models import CartItem
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django import forms


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
    """Checkout view - handles both GET (show form) and POST (process order)"""

    # Get site settings
    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings()  # Use defaults if no settings exist

    # Get cart items
    cart_items = []
    cart_total = 0

    if request.user.is_authenticated:
        # For authenticated users, get from database
        cart_items = CartItem.objects.filter(user=request.user).select_related('product')
        cart_total = sum(item.get_total_price() for item in cart_items)
    else:
        # For anonymous users, you might want to implement session-based cart
        # For now, redirect to cart page
        messages.warning(request, 'Please add items to your cart first.')
        return redirect('cart')

    # Calculate minimum delivery date based on notice required
    notice_hours = 24  # Default 24 hours
    try:
        if settings.minimum_order_notice:
            notice_text = settings.minimum_order_notice.lower()
            if 'hour' in notice_text:
                notice_hours = int(''.join(filter(str.isdigit, notice_text))) or 24
            elif 'day' in notice_text:
                notice_hours = (int(''.join(filter(str.isdigit, notice_text))) or 1) * 24
    except:
        notice_hours = 24

    min_delivery_date = (timezone.now() + timedelta(hours=notice_hours)).strftime('%Y-%m-%dT%H:%M')

    if request.method == 'POST':
        return process_checkout(request, cart_items, cart_total, settings)

    context = {
        'settings': settings,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'min_delivery_date': min_delivery_date,
    }

    return render(request, 'checkout.html', context)


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


# Add or update your cart view in views.py

def cart(request):
    """Display user's cart"""
    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings()  # Use defaults if no settings exist

    cart_items = []
    cart_total = 0

    if request.user.is_authenticated:
        # Get cart items for authenticated users
        cart_items = CartItem.objects.filter(user=request.user).select_related('product')
        cart_total = sum(item.get_total_price() for item in cart_items)
    else:
        # For anonymous users, you can implement session-based cart here
        # For now, show empty cart with login prompt
        messages.info(request, 'Please log in to view your cart or add items.')

    context = {
        'settings': settings,
        'cart_items': cart_items,
        'cart_total': cart_total,
    }

    return render(request, 'base/cart.html', context)


# Add these imports to your existing views.py


# Custom forms for better validation and styling
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for styling
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        # Customize help text
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['username'].help_text = None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for styling
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})


# Authentication view
def authenticate_view(request):
    """Handle both login and signup"""
    settings = SiteSettings.objects.first() or SiteSettings()

    login_form = CustomAuthenticationForm()
    signup_form = CustomUserCreationForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'login':
            login_form = CustomAuthenticationForm(data=request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)

                if user is not None:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.username}!')

                    # Redirect to next URL or cart/home
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    elif CartItem.objects.filter(user=user).exists():
                        return redirect('cart')
                    else:
                        return redirect('home')
                else:
                    messages.error(request, 'Invalid username or password.')
            else:
                messages.error(request, 'Please correct the errors below.')

        elif form_type == 'signup':
            signup_form = CustomUserCreationForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save()
                username = signup_form.cleaned_data.get('username')
                messages.success(request, f'Account created successfully for {username}!')

                # Auto-login the new user
                login(request, user)

                # Redirect to next URL or home
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('home')
            else:
                messages.error(request, 'Please correct the errors below.')

    context = {
        'settings': settings,
        'login_form': login_form,
        'signup_form': signup_form,
    }

    return render(request, 'authenticate.html', context)


# Logout view
def logout_view(request):
    """Handle user logout"""
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'Goodbye {username}! You have been logged out.')

    return redirect('home')


# Profile view (optional)
@login_required
def profile_view(request):
    """User profile page"""
    settings = SiteSettings.objects.first() or SiteSettings()

    # Get user's recent orders
    recent_orders = Order.objects.filter(
        customer_email=request.user.email
    ).order_by('-created_at')[:5]

    context = {
        'settings': settings,
        'user': request.user,
        'recent_orders': recent_orders,
    }

    return render(request, 'profile.html', context)


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


# Add this to your existing views.py


def process_checkout(request, cart_items, cart_total, settings):
    """Process the checkout form submission"""

    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    try:
        # Get form data
        customer_name = request.POST.get('customer_name', '').strip()
        customer_email = request.POST.get('customer_email', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        delivery_date_str = request.POST.get('delivery_date', '').strip()
        delivery_address = request.POST.get('delivery_address', '').strip()
        special_instructions = request.POST.get('special_instructions', '').strip()

        # Validate required fields
        if not all([customer_name, customer_email, customer_phone, delivery_date_str]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('checkout')

        # Parse delivery date
        try:
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%dT%H:%M')
            delivery_date = timezone.make_aware(delivery_date)
        except ValueError:
            messages.error(request, 'Invalid delivery date format.')
            return redirect('checkout')

        # Check if delivery date is far enough in the future
        notice_hours = 24  # Default
        try:
            if settings.minimum_order_notice:
                notice_text = settings.minimum_order_notice.lower()
                if 'hour' in notice_text:
                    notice_hours = int(''.join(filter(str.isdigit, notice_text))) or 24
                elif 'day' in notice_text:
                    notice_hours = (int(''.join(filter(str.isdigit, notice_text))) or 1) * 24
        except:
            notice_hours = 24

        min_delivery_time = timezone.now() + timedelta(hours=notice_hours)
        if delivery_date < min_delivery_time:
            messages.error(request, f'Delivery date must be at least {settings.minimum_order_notice} from now.')
            return redirect('checkout')

        # Create order in a transaction
        with transaction.atomic():
            # Generate unique order number
            order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

            # Create the order
            order = Order.objects.create(
                order_number=order_number,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                total_amount=cart_total,
                delivery_date=delivery_date,
                delivery_address=delivery_address,
                special_instructions=special_instructions,
                status='pending'
            )

            # Create order items
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.product.price,
                    customization_notes=''  # You can add this field to cart if needed
                )

                # Update stock if you want to track inventory
                # cart_item.product.stock_quantity -= cart_item.quantity
                # cart_item.product.save()

            # Clear the cart
            cart_items.delete()

            messages.success(
                request,
                f'Order placed successfully! Your order number is {order_number}. '
                f'We will contact you at {customer_phone} to confirm your order.'
            )

            # Redirect to order confirmation or home page
            return redirect('order_confirmation', order_number=order_number)

    except Exception as e:
        messages.error(request, 'An error occurred while processing your order. Please try again.')
        return redirect('checkout')


def order_confirmation(request, order_number):
    """Order confirmation page"""
    order = get_object_or_404(Order, order_number=order_number)
    settings = SiteSettings.objects.first() or SiteSettings()

    context = {
        'order': order,
        'settings': settings,
    }

    return render(request, 'order_confirmation.html', context)

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
    
