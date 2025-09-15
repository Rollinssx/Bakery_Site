# cart_views.py - Add these views to handle cart operations
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Product, CartItem


@require_POST
def add_to_cart(request, product_id):
    """Add product to cart via AJAX"""
    try:
        product = get_object_or_404(Product, id=product_id)

        if not product.is_in_stock:
            return JsonResponse({'success': False, 'message': 'Product is out of stock'})

        if request.user.is_authenticated:
            # For authenticated users, use database
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user,
                product=product,
                defaults={'quantity': 1}
            )

            if not created:
                if cart_item.quantity < product.stock_quantity:
                    cart_item.quantity += 1
                    cart_item.save()
                else:
                    return JsonResponse({'success': False, 'message': 'Not enough stock available'})

            cart_count = CartItem.objects.filter(user=request.user).count()
        else:
            # For anonymous users, use session
            cart = request.session.get('cart', {})
            product_id_str = str(product_id)

            if product_id_str in cart:
                if cart[product_id_str] < product.stock_quantity:
                    cart[product_id_str] += 1
                else:
                    return JsonResponse({'success': False, 'message': 'Not enough stock available'})
            else:
                cart[product_id_str] = 1

            request.session['cart'] = cart
            cart_count = len(cart)

        return JsonResponse({
            'success': True,
            'message': 'Product added to cart successfully',
            'cart_count': cart_count
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def update_cart_quantity(request, product_id):
    """Update cart item quantity via AJAX"""
    try:
        data = json.loads(request.body)
        change = int(data.get('change', 0))

        product = get_object_or_404(Product, id=product_id)

        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, user=request.user, product=product)
            new_quantity = max(0, cart_item.quantity + change)

            if new_quantity > product.stock_quantity:
                return JsonResponse({'success': False, 'message': 'Not enough stock available'})

            if new_quantity == 0:
                cart_item.delete()
            else:
                cart_item.quantity = new_quantity
                cart_item.save()

            # Calculate totals
            cart_items = CartItem.objects.filter(user=request.user)
            subtotal = sum(item.get_total_price() for item in cart_items)

        else:
            cart = request.session.get('cart', {})
            product_id_str = str(product_id)

            if product_id_str in cart:
                new_quantity = max(0, cart[product_id_str] + change)

                if new_quantity > product.stock_quantity:
                    return JsonResponse({'success': False, 'message': 'Not enough stock available'})

                if new_quantity == 0:
                    del cart[product_id_str]
                else:
                    cart[product_id_str] = new_quantity

                request.session['cart'] = cart
            else:
                return JsonResponse({'success': False, 'message': 'Item not found in cart'})

            # Calculate totals for session cart
            subtotal = 0
            for pid, quantity in cart.items():
                try:
                    p = Product.objects.get(id=pid)
                    subtotal += p.price * quantity
                except Product.DoesNotExist:
                    continue

        shipping = 5.00 if subtotal > 0 else 0
        total = subtotal + shipping
        item_total = product.price * new_quantity if new_quantity > 0 else 0
        cart_count = len(cart) if not request.user.is_authenticated else CartItem.objects.filter(
            user=request.user).count()

        return JsonResponse({
            'success': True,
            'new_quantity': new_quantity,
            'item_total': float(item_total),
            'subtotal': float(subtotal),
            'shipping': float(shipping),
            'total': float(total),
            'cart_count': cart_count
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def remove_from_cart(request, product_id):
    """Remove item from cart completely"""
    try:
        product = get_object_or_404(Product, id=product_id)

        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, user=request.user, product=product)
            cart_item.delete()
            cart_count = CartItem.objects.filter(user=request.user).count()
        else:
            cart = request.session.get('cart', {})
            product_id_str = str(product_id)

            if product_id_str in cart:
                del cart[product_id_str]
                request.session['cart'] = cart
                cart_count = len(cart)
            else:
                return JsonResponse({'success': False, 'message': 'Item not found in cart'})

        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_count': cart_count
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def cart_count(request):
    """Get current cart count"""
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user).count()
    else:
        cart = request.session.get('cart', {})
        count = len(cart)

    return JsonResponse({'count': count})

