from django.urls import path
from . import views


urlpatterns = [

    # =====================================================
    # CHECKOUT
    # =====================================================

    path(
        'checkout/',
        views.checkout,
        name='checkout',
    ),

    # =====================================================
    # RAZORPAY PAYMENTS
    # =====================================================

    path(
        'start-payment/',
        views.start_payment,
        name='start_payment',
    ),

    path(
        'verify-payment/',
        views.verify_payment,
        name='verify_payment',
    ),

    path(
        'payment-failed/',
        views.payment_failed,
        name='payment_failed',
    ),

    path(
        'retry-payment/<int:order_id>/',
        views.retry_payment,
        name='retry_payment',
    ),

    # =====================================================
    # CUSTOMER ORDERS
    # =====================================================

    path(
        'success/<int:order_id>/',
        views.order_success,
        name='order_success',
    ),

    path(
        'my-orders/',
        views.my_orders,
        name='my_orders',
    ),

    path(
        'detail/<int:order_id>/',
        views.order_detail,
        name='order_detail',
    ),

    path(
        'cancel/<int:order_id>/',
        views.cancel_order,
        name='cancel_order',
    ),

    # =====================================================
    # ORDER TRACKING
    # =====================================================

    path(
        'track/<int:order_id>/',
        views.track_order,
        name='track_order',
    ),

    # =====================================================
    # PDF INVOICE
    # =====================================================

    path(
        'invoice/<int:order_id>/download/',
        views.download_order_invoice,
        name='download_order_invoice',
    ),

    # =====================================================
    # COUPONS
    # =====================================================

    path(
        'apply-coupon/',
        views.apply_coupon,
        name='apply_coupon',
    ),

    path(
        'remove-coupon/',
        views.remove_coupon,
        name='remove_coupon',
    ),

    # =====================================================
    # SELLER DASHBOARD
    # =====================================================

    path(
        'seller-dashboard/',
        views.seller_orders,
        name='seller_dashboard',
    ),

]