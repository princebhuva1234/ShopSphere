from django.urls import path
from .views import (
    add_to_cart,
    cart_detail,
    increase_quantity,
    decrease_quantity,
)

urlpatterns = [
    path('add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('', cart_detail, name='cart_detail'),

    path(
        'increase/<int:item_id>/',
        increase_quantity,
        name='increase_quantity'
    ),

    path(
        'decrease/<int:item_id>/',
        decrease_quantity,
        name='decrease_quantity'
    ),
]