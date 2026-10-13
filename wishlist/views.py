from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from products.models import Product
from cart.models import Cart, CartItem

from .models import Wishlist, WishlistItem


# =========================================================
# VIEW MY WISHLIST
# =========================================================

@login_required
def wishlist_view(request):

    # Get or create the current user's wishlist.
    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user
    )

    # Get wishlist products.
    wishlist_items = (
        wishlist.items
        .select_related(
            'product',
            'product__category'
        )
        .prefetch_related(
            'product__images'
        )
        .order_by('-added_at')
    )

    context = {
        'wishlist': wishlist,
        'wishlist_items': wishlist_items,
    }

    return render(
        request,
        'wishlist/wishlist.html',
        context
    )


# =========================================================
# ADD PRODUCT TO WISHLIST
# =========================================================

@login_required
@require_POST
def add_to_wishlist(request, product_id):

    # Only active products can be added.
    # Out-of-stock products may still be wishlisted.
    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user
    )

    wishlist_item, item_created = (
        WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product
        )
    )

    if item_created:

        messages.success(
            request,
            f'{product.name} was added to your wishlist.'
        )

    else:

        messages.info(
            request,
            f'{product.name} is already in your wishlist.'
        )

    next_url = request.POST.get('next', '')

    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):

        return redirect(next_url)

    return redirect('wishlist')


# =========================================================
# REMOVE PRODUCT FROM WISHLIST
# =========================================================

@login_required
@require_POST
def remove_from_wishlist(request, item_id):

    wishlist_item = get_object_or_404(
        WishlistItem,
        id=item_id,
        wishlist__user=request.user
    )

    product_name = wishlist_item.product.name

    wishlist_item.delete()

    messages.success(
        request,
        f'{product_name} was removed from your wishlist.'
    )

    return redirect('wishlist')


# =========================================================
# MOVE WISHLIST PRODUCT TO CART
# =========================================================

@login_required
@require_POST
def move_to_cart(request, item_id):

    wishlist_item = get_object_or_404(
        WishlistItem.objects.select_related(
            'product',
            'wishlist'
        ),
        id=item_id,
        wishlist__user=request.user
    )

    product_id = wishlist_item.product_id

    # Lock the product while validating stock.
    with transaction.atomic():

        try:

            product = (
                Product.objects
                .select_for_update()
                .get(
                    id=product_id
                )
            )

        except Product.DoesNotExist:

            messages.error(
                request,
                'This product is no longer available.'
            )

            return redirect('wishlist')

        # -------------------------------------------------
        # CHECK PRODUCT AVAILABILITY
        # -------------------------------------------------

        if not product.is_active:

            messages.error(
                request,
                f'{product.name} is currently unavailable.'
            )

            return redirect('wishlist')

        if product.stock_quantity <= 0:

            messages.warning(
                request,
                f'{product.name} is out of stock.'
            )

            return redirect('wishlist')

        # -------------------------------------------------
        # GET OR CREATE CART
        # -------------------------------------------------

        cart, created = Cart.objects.get_or_create(
            user=request.user
        )

        # -------------------------------------------------
        # CHECK EXISTING CART QUANTITY
        # -------------------------------------------------

        cart_item = (
            CartItem.objects
            .select_for_update()
            .filter(
                cart=cart,
                product=product
            )
            .first()
        )

        if cart_item:

            if (
                cart_item.quantity + 1
                > product.stock_quantity
            ):

                messages.warning(
                    request,
                    f'Only {product.stock_quantity} unit(s) of '
                    f'{product.name} are available. '
                    f'Your cart already contains '
                    f'{cart_item.quantity}.'
                )

                return redirect('wishlist')

            cart_item.quantity += 1

            cart_item.save(
                update_fields=['quantity']
            )

        else:

            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=1
            )

        # -------------------------------------------------
        # REMOVE FROM WISHLIST AFTER SUCCESSFUL MOVE
        # -------------------------------------------------

        product_name = product.name

        wishlist_item.delete()

    messages.success(
        request,
        f'{product_name} was moved to your cart.'
    )

    return redirect('wishlist') 