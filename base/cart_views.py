# cart_views.py - Add these views to handle cart operations
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Product, CartItem

# cart_views.py - Updated with proper error handling and responses

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Product, CartItem
import json


@login_required
@require_POST
def add_to_cart(request, product_id):
    """Add product to cart"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)

        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': 1}
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        # Calculate cart totals
        cart_items = CartItem.objects.filter(user=request.user)
        cart_total = sum(item.get_total_price() for item in cart_items)
        cart_count = sum(item.quantity for item in cart_items)

        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_count': cart_count,
            'cart_total': float(cart_total),
            'item_quantity': cart_item.quantity
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Error adding item to cart'
        }, status=500)


@login_required
@require_POST
def update_cart_quantity(request, product_id):
    """Update cart item quantity"""
    try:
        data = json.loads(request.body)
        new_quantity = int(data.get('quantity', 1))

        if new_quantity < 1:
            return remove_from_cart(request, product_id)

        cart_item = get_object_or_404(
            CartItem,
            user=request.user,
            product_id=product_id
        )

        cart_item.quantity = new_quantity
        cart_item.save()

        # Calculate totals
        cart_items = CartItem.objects.filter(user=request.user)
        cart_total = sum(item.get_total_price() for item in cart_items)
        cart_count = sum(item.quantity for item in cart_items)
        item_total = cart_item.get_total_price()

        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': float(cart_total),
            'item_total': float(item_total),
            'item_quantity': cart_item.quantity
        })

    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cart item not found'
        }, status=404)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid quantity'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Error updating cart'
        }, status=500)


@login_required
@require_POST
def remove_from_cart(request, product_id):
    """Remove item from cart"""
    try:
        cart_item = get_object_or_404(
            CartItem,
            user=request.user,
            product_id=product_id
        )

        cart_item.delete()

        # Calculate remaining totals
        cart_items = CartItem.objects.filter(user=request.user)
        cart_total = sum(item.get_total_price() for item in cart_items)
        cart_count = sum(item.quantity for item in cart_items)

        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_count': cart_count,
            'cart_total': float(cart_total)
        })

    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cart item not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Error removing item from cart'
        }, status=500)


@login_required
def cart_count(request):
    """Get current cart count"""
    try:
        cart_items = CartItem.objects.filter(user=request.user)
        cart_count = sum(item.quantity for item in cart_items)
        cart_total = sum(item.get_total_price() for item in cart_items)

        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': float(cart_total)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Error getting cart count'
        }, status=500)


@login_required
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

