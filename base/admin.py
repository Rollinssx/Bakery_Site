# admin.py - Updated to match your SiteSettings model
from django.contrib import admin
from .models import SiteSettings, Category, Product, CartItem, ContactMessage

# admin.py - Clean version that matches your exact model
from django.contrib import admin
from .models import SiteSettings, Category, Product, CartItem, ContactMessage
from .models import Order, OrderItem, NewsletterSubscriber


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'email', 'phone', 'updated_at']

    fieldsets = (
        ('Hero Section', {
            'fields': ('hero_headline', 'hero_subheadline', 'hero_image_url')
        }),
        ('Business Information', {
            'fields': ('business_name', 'about_title', 'about_description', 'owner_image_url')
        }),
        ('Contact Details', {
            'fields': ('phone', 'email', 'address', 'opening_hours')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url'),
            'classes': ('collapse',)
        }),
        ('Business Settings', {
            'fields': ('minimum_order_notice', 'site_description'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        # Only allow one SiteSettings instance
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of site settings
        return False

# Only add the other admin classes if you have those models
# Comment these out if you don't have these models yet
"""
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)  
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity']
    prepopulated_fields = {'slug': ('name',)}
"""


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('products')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity', 'is_active', 'is_featured', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'stock_quantity', 'is_active', 'is_featured']

    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock_quantity')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'get_total_price', 'created_at']
    list_filter = ['created_at', 'product__category']
    search_fields = ['user__username', 'product__name']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'subject')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f'{queryset.count()} messages marked as read.')

    mark_as_read.short_description = 'Mark selected messages as read'

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f'{queryset.count()} messages marked as unread.')

    mark_as_unread.short_description = 'Mark selected messages as unread'


# Add these imports to your existing admin.py


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']

    def total_price(self, obj):
        return obj.total_price

    total_price.short_description = 'Total Price'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_name', 'customer_phone',
        'status', 'total_amount', 'delivery_date', 'is_delivery', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'delivery_date']
    search_fields = ['order_number', 'customer_name', 'customer_email', 'customer_phone']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    list_editable = ['status']
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status', 'total_amount', 'created_at', 'updated_at')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Delivery/Pickup', {
            'fields': ('delivery_date', 'delivery_address', 'special_instructions')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items')

    actions = ['mark_confirmed', 'mark_ready', 'mark_completed']

    def mark_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f'{queryset.count()} orders marked as confirmed.')

    mark_confirmed.short_description = 'Mark selected orders as confirmed'

    def mark_ready(self, request, queryset):
        queryset.update(status='ready')
        self.message_user(request, f'{queryset.count()} orders marked as ready.')

    mark_ready.short_description = 'Mark selected orders as ready'

    def mark_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f'{queryset.count()} orders marked as completed.')

    mark_completed.short_description = 'Mark selected orders as completed'


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'is_active', 'subscribed_at']
    list_filter = ['is_active', 'subscribed_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['subscribed_at']
    list_editable = ['is_active']

    fieldsets = (
        ('Subscriber Information', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Status', {
            'fields': ('is_active', 'subscribed_at')
        }),
    )

    actions = ['activate_subscribers', 'deactivate_subscribers']

    def activate_subscribers(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} subscribers activated.')

    activate_subscribers.short_description = 'Activate selected subscribers'

    def deactivate_subscribers(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} subscribers deactivated.')

    deactivate_subscribers.short_description = 'Deactivate selected subscribers'

