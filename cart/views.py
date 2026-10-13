from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product

from .models import Cart, CartItem


# =========================================================
# ADD TO CART
# =========================================================

@login_required
def add_to_cart(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    # -----------------------------------------------------
    # CHECK PRODUCT ACTIVE
    # -----------------------------------------------------

    if not product.is_active:

        messages.error(
            request,
            f'{product.name} is currently unavailable.'
        )

        return redirect('product_list')

    # -----------------------------------------------------
    # CHECK STOCK
    # -----------------------------------------------------

    if product.stock_quantity <= 0:

        messages.error(
            request,
            f'{product.name} is out of stock.'
        )

        return redirect('product_list')

    # -----------------------------------------------------
    # GET / CREATE CART
    # -----------------------------------------------------

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    # -----------------------------------------------------
    # GET / CREATE CART ITEM
    # -----------------------------------------------------

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    # -----------------------------------------------------
    # NEW CART ITEM
    # -----------------------------------------------------

    if created:

        cart_item.quantity = 1
        cart_item.save()

    # -----------------------------------------------------
    # EXISTING CART ITEM
    # -----------------------------------------------------

    else:

        # Do not allow quantity above stock.
        if cart_item.quantity >= product.stock_quantity:

            messages.warning(
                request,
                f'Only {product.stock_quantity} unit(s) of '
                f'{product.name} are available.'
            )

            return redirect('cart_detail')

        cart_item.quantity += 1

        cart_item.save()

    return redirect('product_list')


# =========================================================
# CART DETAIL
# =========================================================

@login_required
def cart_detail(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_items = cart.items.select_related(
        'product'
    )

    total = sum(
        (
            item.product.discount_price
            or item.product.price
        ) * item.quantity
        for item in cart_items
    )

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': total,
    }

    return render(
        request,
        'cart/cart_detail.html',
        context
    )


# =========================================================
# INCREASE QUANTITY
# =========================================================

@login_required
def increase_quantity(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    product = cart_item.product

    # -----------------------------------------------------
    # CHECK PRODUCT ACTIVE
    # -----------------------------------------------------

    if not product.is_active:

        messages.error(
            request,
            f'{product.name} is currently unavailable.'
        )

        return redirect('cart_detail')

    # -----------------------------------------------------
    # CHECK STOCK
    # -----------------------------------------------------

    if cart_item.quantity >= product.stock_quantity:

        messages.warning(
            request,
            f'Only {product.stock_quantity} unit(s) of '
            f'{product.name} are available.'
        )

        return redirect('cart_detail')

    cart_item.quantity += 1

    cart_item.save()

    return redirect('cart_detail')


# =========================================================
# DECREASE QUANTITY
# =========================================================

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