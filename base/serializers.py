# styles/serializers.py
from rest_framework import serializers
from base.models import (
    Category, Product, NewsletterSubscriber, ContactMessage,
    Order, OrderItem, SiteSettings
)


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.ReadOnlyField(source='products.count')

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'category_type', 'description', 'image_url',
            'is_featured', 'product_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'product_count']


class ProductListSerializer(serializers.ModelSerializer):
    """Simplified serializer for product lists"""
    category_name = serializers.ReadOnlyField(source='category.name')
    formatted_price = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'formatted_price', 'image_url',
            'category', 'category_name', 'is_best_seller', 'is_available'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual products"""
    category_name = serializers.ReadOnlyField(source='category.name')
    formatted_price = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'formatted_price',
            'image_url', 'category', 'category_name', 'is_best_seller',
            'is_available', 'is_featured', 'stock_quantity', 'is_in_stock',
            'order_lead_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'formatted_price', 'is_in_stock']


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = NewsletterSubscriber
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'subscribed_at'
        ]
        read_only_fields = ['id', 'subscribed_at', 'full_name']

    def validate_email(self, value):
        """Custom email validation"""
        if NewsletterSubscriber.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already subscribed.")
        return value


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_message(self, value):
        """Ensure message is not empty or too short"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    total_price = serializers.ReadOnlyField()
    formatted_total = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_price',
            'total_price', 'formatted_total', 'customization_notes'
        ]
        read_only_fields = ['id', 'total_price', 'formatted_total']

    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order lists"""
    items_count = serializers.ReadOnlyField(source='items.count')
    is_delivery = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'status', 'total_amount',
            'delivery_date', 'is_delivery', 'items_count', 'created_at'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual orders"""
    items = OrderItemSerializer(many=True, read_only=True)
    is_delivery = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'customer_email', 'customer_phone',
            'status', 'total_amount', 'delivery_date', 'delivery_address',
            'is_delivery', 'special_instructions', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at', 'is_delivery']

    def create(self, validated_data):
        """Generate order number on creation"""
        import uuid
        validated_data['order_number'] = f"BWL{str(uuid.uuid4())[:8].upper()}"
        return super().create(validated_data)

    def validate_delivery_date(self, value):
        """Ensure delivery date is in the future"""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Delivery date must be in the future.")
        return value


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            'id', 'about_title', 'about_description', 'owner_image_url',
            'hero_headline', 'hero_subheadline', 'hero_image_url',
            'business_name', 'address', 'email', 'phone', 'opening_hours',
            'facebook_url', 'instagram_url', 'twitter_url',
            'minimum_order_notice', 'site_description'
        ]
        read_only_fields = ['id']


# Custom serializers for specific use cases

class BestSellerProductSerializer(serializers.ModelSerializer):
    """Serializer specifically for best seller products"""
    category_name = serializers.ReadOnlyField(source='category.name')
    formatted_price = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'formatted_price', 'image_url', 'category_name']


class FeaturedCategorySerializer(serializers.ModelSerializer):
    """Serializer for featured categories with their products"""
    products = BestSellerProductSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'image_url', 'products']


class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    """Simple serializer for newsletter subscription endpoint"""

    class Meta:
        model = NewsletterSubscriber
        fields = ['email']

    def validate_email(self, value):
        if NewsletterSubscriber.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already subscribed to newsletter.")
        return value

    def create(self, validated_data):
        validated_data['is_active'] = True
        return super().create(validated_data)


class ContactFormSerializer(serializers.ModelSerializer):
    """Simple serializer for contact form submission"""

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']

    def validate(self, data):
        """Cross-field validation"""
        if not data.get('phone') and not data.get('email'):
            raise serializers.ValidationError("Either phone or email must be provided.")
        return data