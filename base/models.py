# models.py - Updated SiteSettings model
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class SiteSettings(models.Model):
    """Model for site-wide settings and content"""

    # About section content
    about_title = models.CharField(max_length=200, default="About us")
    about_description = models.TextField(
        default="Lorem Ipsum is simply dummy text of the printing and typesetting industry..."
    )
    owner_image_url = models.URLField(max_length=500, blank=True)

    # Hero section content
    hero_headline = models.CharField(max_length=200, default="Pastries baked with love")
    hero_subheadline = models.CharField(
        max_length=200,
        default="The one-stop shop for all your bakery needs"
    )
    hero_image_url = models.URLField(max_length=500, blank=True)

    # Contact information
    business_name = models.CharField(max_length=200, default="Pastries with Love")
    address = models.TextField(default="123 Bakery Lane\nNairobi, Kenya")
    email = models.EmailField(default="contact@pastries.com")
    phone = models.CharField(max_length=20, default="+254 700 123 456")

    # Social media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)

    # Business hours and policies
    opening_hours = models.TextField(
        default="Monday - Saturday: 8:00 AM - 6:00 PM\nSunday: 10:00 AM - 4:00 PM"
    )
    minimum_order_notice = models.CharField(
        max_length=100,
        default="24 hours",
        help_text="Minimum notice required for orders"
    )

    # SEO
    site_description = models.TextField(
        default="Premium bakery in Nairobi offering custom cakes, pastries, and desserts for all occasions."
    )

    # Add these timestamp fields that the admin expects
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return f"Settings for {self.business_name}"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError("Only one SiteSettings instance is allowed")
        super().save(*args, **kwargs)


# Keep your existing Category, Product, CartItem, and ContactMessage models
class Category(models.Model):
    """Product categories"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products') + f'?category={self.slug}'


from django.db.models import Sum


class Product(models.Model):
    """Product model"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_best_seller = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def stock_status(self):
        if self.stock_quantity > 10:
            return "In Stock"
        elif self.stock_quantity > 0:
            return f"Only {self.stock_quantity} left"
        else:
            return "Out of Stock"

    @property
    def total_sold(self):
        """Total units sold across all completed orders."""
        return self.order_items.filter(order__status='completed').aggregate(
            total=Sum('quantity')
        )['total'] or 0

    @classmethod
    def best_sellers(cls, limit=3):
        """
        Return the top-selling products.
        """
        return (
            cls.objects.annotate(total_sales=Sum('order_items__quantity'))
            .filter(order_items__order__status='completed')
            .order_by('-total_sales')[:limit]
        )

    @property
    def is_best_seller(self):
        """Check if this product is among the top 3 sellers."""
        return self in Product.best_sellers(limit=3)


class CartItem(models.Model):
    """Shopping cart items for authenticated users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} (x{self.quantity})"

    def get_total_price(self):
        return self.product.price * self.quantity


class NewsletterSubscriber(models.Model):
    """Model for newsletter subscribers from the subscription form"""
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Order(models.Model):
    """Model for customer orders"""

    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Customer information
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)

    # Order details
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Delivery/pickup
    delivery_date = models.DateTimeField()
    delivery_address = models.TextField(blank=True, help_text="Leave blank for pickup")
    special_instructions = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} - {self.customer_name}"

    def get_absolute_url(self):
        return reverse('order_detail', kwargs={'order_number': self.order_number})

    @property
    def is_delivery(self):
        return bool(self.delivery_address.strip())


class OrderItem(models.Model):
    """Model for individual items in an order"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')  # ✅ add related_name
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    customization_notes = models.TextField(blank=True, help_text="Special requests for this item")

    class Meta:
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.name} for Order #{self.order.order_number}"

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    @property
    def formatted_total(self):
        return f"KES {self.total_price:,.2f}"


class ContactMessage(models.Model):
    """Contact form messages"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"