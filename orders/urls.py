from django.urls import path

from .views import (
    checkout,
    start_payment,
    verify_payment,
    payment_failed,
    retry_payment,
    order_success,
    my_orders,
    order_detail,
    cancel_order,
)


urlpatterns = [

    # Checkout
    path(
        'checkout/',
        checkout,
        name='checkout'
    ),

    # Start Razorpay payment
    path(
        'start-payment/',
        start_payment,
        name='start_payment'
    ),

    # Verify Razorpay payment
    path(
        'verify-payment/',
        verify_payment,
        name='verify_payment'
    ),

    # Payment failed
    path(
        'payment-failed/',
        payment_failed,
        name='payment_failed'
    ),

    # Retry payment
    path(
        'retry-payment/<int:order_id>/',
        retry_payment,
        name='retry_payment'
    ),

    # Order success
    path(
        'success/<int:order_id>/',
        order_success,
        name='order_success'
    ),

    # My orders
    path(
        'my-orders/',
        my_orders,
        name='my_orders'
    ),

    # Order detail
    path(
        'detail/<int:order_id>/',
        order_detail,
        name='order_detail'
    ),

    # Cancel order
    path(
        'cancel/<int:order_id>/',
        cancel_order,
        name='cancel_order'
    ),
]