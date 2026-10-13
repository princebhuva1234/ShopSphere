from django.urls import path

from .views import (
    wishlist_view,
    add_to_wishlist,
    remove_from_wishlist,
    move_to_cart,
)


urlpatterns = [

    # View wishlist
    path(
        '',
        wishlist_view,
        name='wishlist'
    ),

    # Add product
    path(
        'add/<int:product_id>/',
        add_to_wishlist,
        name='add_to_wishlist'
    ),

    # Remove product
    path(
        'remove/<int:item_id>/',
        remove_from_wishlist,
        name='remove_from_wishlist'
    ),

    # Move product to cart
    path(
        'move-to-cart/<int:item_id>/',
        move_to_cart,
        name='move_to_cart'
    ),

]