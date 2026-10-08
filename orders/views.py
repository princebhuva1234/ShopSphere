from decimal import Decimal
import uuid

import razorpay

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import Address
from cart.models import Cart
from payments.models import Payment

from .models import Order, OrderItem, OrderAddress


# =========================================================
# CHECKOUT
# =========================================================

@login_required
def checkout(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_items = cart.items.select_related(
        'product'
    )

    if not cart_items.exists():
        return redirect('cart_detail')

    addresses = Address.objects.filter(
        user=request.user
    ).order_by(
        '-is_default',
        '-created_at'
    )

    total = sum(
        (
            item.product.discount_price
            or item.product.price
        ) * item.quantity
        for item in cart_items
    )

    checkout_token = uuid.uuid4().hex

    return render(
        request,
        'orders/checkout.html',
        {
            'cart': cart,
            'cart_items': cart_items,
            'total': total,
            'addresses': addresses,
            'checkout_token': checkout_token,
        }
    )


# =========================================================
# START RAZORPAY PAYMENT
# =========================================================

@login_required
def start_payment(request):

    if request.method != 'POST':
        return redirect('checkout')

    payment_method = request.POST.get(
        'payment_method'
    )

    address_id = request.POST.get(
        'address_id'
    )

    checkout_token = request.POST.get(
        'checkout_token'
    )

    # -----------------------------------------------------
    # ONLY RAZORPAY
    # -----------------------------------------------------

    if payment_method != 'RAZORPAY':
        return redirect('checkout')

    if not checkout_token:
        return redirect('checkout')

    # -----------------------------------------------------
    # GET ADDRESS
    # -----------------------------------------------------

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    # =====================================================
    # LOCK CART
    # =====================================================

    with transaction.atomic():

        cart = Cart.objects.select_for_update().filter(
            user=request.user
        ).first()

        if not cart:
            return redirect('cart_detail')

        cart_items = cart.items.select_related(
            'product'
        )

        if not cart_items.exists():
            return redirect('cart_detail')

        # -------------------------------------------------
        # CHECK DUPLICATE CHECKOUT
        # -------------------------------------------------

        existing_payment = Payment.objects.filter(
            checkout_token=checkout_token,
            order__user=request.user
        ).select_related(
            'order'
        ).first()

        if existing_payment:

            existing_order = existing_payment.order

            # Already paid
            if existing_payment.status == 'PAID':

                return redirect(
                    'order_success',
                    order_id=existing_order.id
                )

            # Payment already created
            if (
                existing_payment.status == 'PENDING'
                and existing_payment.provider_order_id
            ):

                amount_paise = int(
                    existing_payment.amount
                    * Decimal('100')
                )

                return render(
                    request,
                    'orders/payment.html',
                    {
                        'order': existing_order,
                        'payment': existing_payment,
                        'razorpay_order_id':
                            existing_payment.provider_order_id,
                        'razorpay_key_id':
                            settings.RAZORPAY_KEY_ID,
                        'amount':
                            amount_paise,
                    }
                )

        # =================================================
        # CALCULATE TOTAL
        # =================================================

        total = sum(
            (
                item.product.discount_price
                or item.product.price
            ) * item.quantity
            for item in cart_items
        )

        if total <= 0:
            return redirect('cart_detail')

        # =================================================
        # CREATE ORDER
        # =================================================

        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            status='PENDING'
        )

        # =================================================
        # SAVE ADDRESS SNAPSHOT
        # =================================================

        OrderAddress.objects.create(
            order=order,
            full_name=address.full_name,
            phone=address.phone,
            address_line=address.address_line,
            city=address.city,
            state=address.state,
            pincode=address.pincode
        )

        # =================================================
        # SAVE ORDER ITEMS
        # =================================================

        for item in cart_items:

            price = (
                item.product.discount_price
                or item.product.price
            )

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=price
            )

        # =================================================
        # CREATE PAYMENT
        # =================================================

        payment = Payment.objects.create(
            order=order,
            checkout_token=checkout_token,
            amount=total,
            currency='INR',
            method='RAZORPAY',
            status='PENDING',
            provider='RAZORPAY'
        )

        # =================================================
        # RAZORPAY AMOUNT
        # =================================================

        amount_paise = int(
            total * Decimal('100')
        )

        # =================================================
        # RAZORPAY CLIENT
        # =================================================

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        # =================================================
        # CREATE RAZORPAY ORDER
        # =================================================

        razorpay_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'order_{order.id}',
        }

        try:

            razorpay_order = client.order.create(
                data=razorpay_data
            )

        except Exception:

            payment.status = 'FAILED'

            payment.save(
                update_fields=[
                    'status',
                    'updated_at'
                ]
            )

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message':
                        'Unable to create Razorpay payment order.'
                }
            )

        # =================================================
        # SAVE RAZORPAY ORDER ID
        # =================================================

        payment.provider_order_id = (
            razorpay_order['id']
        )

        payment.save(
            update_fields=[
                'provider_order_id',
                'updated_at'
            ]
        )

    # =====================================================
    # OPEN PAYMENT PAGE
    # =====================================================

    return render(
        request,
        'orders/payment.html',
        {
            'order': order,
            'payment': payment,
            'razorpay_order_id':
                razorpay_order['id'],
            'razorpay_key_id':
                settings.RAZORPAY_KEY_ID,
            'amount':
                amount_paise,
        }
    )


# =========================================================
# VERIFY RAZORPAY PAYMENT
# =========================================================

@login_required
def verify_payment(request):

    if request.method != 'POST':
        return redirect('my_orders')

    razorpay_payment_id = request.POST.get(
        'razorpay_payment_id'
    )

    razorpay_order_id = request.POST.get(
        'razorpay_order_id'
    )

    razorpay_signature = request.POST.get(
        'razorpay_signature'
    )

    # -----------------------------------------------------
    # VALIDATE REQUIRED DATA
    # -----------------------------------------------------

    if not all([
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature
    ]):
        return render(
            request,
            'orders/payment_failed.html',
            {
                'message': 'Payment information is incomplete.'
            }
        )

    # -----------------------------------------------------
    # FIND PAYMENT
    # -----------------------------------------------------

    payment = get_object_or_404(
        Payment,
        provider_order_id=razorpay_order_id,
        order__user=request.user
    )

    order = payment.order

    # =====================================================
    # IDEMPOTENCY CHECK
    # =====================================================

    # If this payment was already successfully processed,
    # do not process it again.
    if (
        payment.status == 'PAID'
        and payment.provider_payment_id
        == razorpay_payment_id
    ):
        return redirect(
            'order_success',
            order_id=order.id
        )

    # -----------------------------------------------------
    # RAZORPAY CLIENT
    # -----------------------------------------------------

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # =====================================================
    # VERIFY SIGNATURE
    # =====================================================

    try:

        client.utility.verify_payment_signature(
            {
                'razorpay_order_id':
                    razorpay_order_id,

                'razorpay_payment_id':
                    razorpay_payment_id,

                'razorpay_signature':
                    razorpay_signature,
            }
        )

    except razorpay.errors.SignatureVerificationError:

        payment.status = 'FAILED'

        payment.save(
            update_fields=[
                'status',
                'updated_at'
            ]
        )

        return render(
            request,
            'orders/payment_failed.html',
            {
                'order': order,
                'message': 'Payment verification failed.'
            }
        )

    # =====================================================
    # SAVE VERIFIED PAYMENT
    # =====================================================

    payment.status = 'PAID'

    payment.provider_payment_id = (
        razorpay_payment_id
    )

    payment.provider_signature = (
        razorpay_signature
    )

    # -----------------------------------------------------
    # GET ACTUAL RAZORPAY PAYMENT METHOD
    # -----------------------------------------------------

    try:

        razorpay_payment = client.payment.fetch(
            razorpay_payment_id
        )

        payment.gateway_method = (
            razorpay_payment.get('method')
        )

    except Exception:
        # Payment signature is already verified.
        # Optional gateway-method lookup failure should
        # not make the valid payment fail.
        pass

    payment.save()

    # =====================================================
    # CONFIRM ORDER ONLY IF NECESSARY
    # =====================================================

    if order.status != 'CONFIRMED':

        order.status = 'CONFIRMED'

        order.save(
            update_fields=[
                'status',
                'updated_at'
            ]
        )

    # =====================================================
    # CLEAR CART
    # =====================================================

    cart = Cart.objects.filter(
        user=request.user
    ).first()

    if cart:

        cart.items.all().delete()

    # =====================================================
    # SUCCESS
    # =====================================================

    return redirect(
        'order_success',
        order_id=order.id
    )


# =========================================================
# PAYMENT FAILED
# =========================================================

@login_required
def payment_failed(request):

    if request.method != 'POST':
        return redirect('my_orders')

    order_id = request.POST.get(
        'order_id'
    )

    error_message = request.POST.get(
        'error_message',
        'Payment failed.'
    )

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    payment = Payment.objects.filter(
        order=order
    ).first()

    if payment:

        payment.status = 'FAILED'

        payment.save(
            update_fields=[
                'status',
                'updated_at'
            ]
        )

    # Keep order pending so payment can be retried.
    if order.status != 'CANCELLED':

        order.status = 'PENDING'

        order.save(
            update_fields=[
                'status',
                'updated_at'
            ]
        )

    return render(
        request,
        'orders/payment_failed.html',
        {
            'order': order,
            'message': error_message,
        }
    )


# =========================================================
# RETRY RAZORPAY PAYMENT
# =========================================================

@login_required
def retry_payment(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    payment = get_object_or_404(
        Payment,
        order=order
    )

    # -----------------------------------------------------
    # CHECK PAYMENT STATUS
    # -----------------------------------------------------

    if payment.status not in [
        'FAILED',
        'PENDING'
    ]:

        return redirect(
            'order_detail',
            order_id=order.id
        )

    if order.status == 'CANCELLED':

        return redirect(
            'order_detail',
            order_id=order.id
        )

    # -----------------------------------------------------
    # CONVERT TO PAISE
    # -----------------------------------------------------

    amount_paise = int(
        payment.amount * Decimal('100')
    )

    # -----------------------------------------------------
    # RAZORPAY CLIENT
    # -----------------------------------------------------

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # -----------------------------------------------------
    # CREATE NEW RAZORPAY ORDER
    # -----------------------------------------------------

    razorpay_data = {
        'amount': amount_paise,
        'currency': payment.currency,
        'receipt': f'order_{order.id}_retry',
    }

    try:

        razorpay_order = client.order.create(
            data=razorpay_data
        )

    except Exception:

        return render(
            request,
            'orders/payment_failed.html',
            {
                'order': order,
                'message':
                    'Unable to start payment retry.'
            }
        )

    # =====================================================
    # RESET PAYMENT
    # =====================================================

    payment.status = 'PENDING'

    payment.provider = 'RAZORPAY'

    payment.provider_order_id = (
        razorpay_order['id']
    )

    payment.provider_payment_id = None

    payment.provider_signature = None

    payment.gateway_method = None

    payment.save()

    # -----------------------------------------------------
    # REOPEN RAZORPAY
    # -----------------------------------------------------

    return render(
        request,
        'orders/payment.html',
        {
            'order': order,
            'payment': payment,
            'razorpay_order_id':
                razorpay_order['id'],
            'razorpay_key_id':
                settings.RAZORPAY_KEY_ID,
            'amount':
                amount_paise,
        }
    )


# =========================================================
# ORDER SUCCESS
# =========================================================

@login_required
def order_success(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
        request,
        'orders/order_success.html',
        {
            'order': order
        }
    )


# =========================================================
# MY ORDERS
# =========================================================

@login_required
def my_orders(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'orders/my_orders.html',
        {
            'orders': orders
        }
    )


# =========================================================
# ORDER DETAIL
# =========================================================

@login_required
def order_detail(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
        request,
        'orders/order_detail.html',
        {
            'order': order
        }
    )


# =========================================================
# CANCEL ORDER
# =========================================================

@login_required
def cancel_order(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if request.method == 'POST':

        if order.status == 'PENDING':

            order.status = 'CANCELLED'

            order.save(
                update_fields=[
                    'status',
                    'updated_at'
                ]
            )

    return redirect(
        'order_detail',
        order_id=order.id
    )