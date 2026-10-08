from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product
from .models import Cart, CartItem


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('product_list')


@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_items = cart.items.select_related('product')

    total = sum(
        (item.product.discount_price or item.product.price) * item.quantity
        for item in cart_items
    )

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': total,
    }

    return render(request, 'cart/cart_detail.html', context)

@login_required
def increase_quantity(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart_item.quantity += 1
    cart_item.save()

    return redirect('cart_detail')

@login_required
def decrease_quantity(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart_item.quantity -= 1

    if cart_item.quantity <= 0:
        cart_item.delete()
    else:
        cart_item.save()

    return redirect('cart_detail')