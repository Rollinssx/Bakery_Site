# forms.py - Create this file in your base app
from django import forms
from django.http import JsonResponse
from django.utils.text import slugify
from base.models import Product, Category


class ProductForm(forms.ModelForm):
    """Form for creating and editing products"""

    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price',
            'stock_quantity', 'is_active', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your product...'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control price-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make category queryset only active categories
        self.fields['category'].queryset = Category.objects.filter(is_active=True)

        # Set default values
        if not self.instance.pk:  # Only for new products
            self.fields['is_active'].initial = True
            self.fields['stock_quantity'].initial = 0

    def clean_name(self):
        name = self.cleaned_data['name']
        # Check for duplicate names (excluding current instance if editing)
        queryset = Product.objects.filter(name__iexact=name)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("A product with this name already exists.")

        return name

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Auto-generate slug from name
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1

            # Ensure unique slug
            while Product.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            instance.slug = slug

        if commit:
            instance.save()

        return instance


