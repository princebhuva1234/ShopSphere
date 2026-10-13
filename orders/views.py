
from decimal import Decimal
import uuid

import razorpay

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import Address
from cart.models import Cart
from payments.models import Payment
from products.models import Product

from .models import Order, OrderItem, OrderAddress
from coupons.models import Coupon, CouponRedemption
from .email_service import (
    send_order_confirmation_email,
    send_payment_confirmation_email,
    send_order_status_email,
)


# =========================================================
# CHECKOUT
# =========================================================

@login_required
def checkout(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_items = cart.items.select_related('product')

    if not cart_items.exists():
        request.session.pop('applied_coupon_code', None)
        return redirect('cart_detail')

    # Check product availability and stock.
    for item in cart_items:

        product = item.product

        if not product.is_active:
            messages.error(
                request,
                f'{product.name} is no longer available.'
            )
            return redirect('cart_detail')

        if item.quantity > product.stock_quantity:
            messages.error(
                request,
                f'Only {product.stock_quantity} unit(s) of '
                f'{product.name} are available.'
            )
            return redirect('cart_detail')

    addresses = Address.objects.filter(
        user=request.user
    ).order_by(
        '-is_default',
        '-created_at'
    )

    # Calculate subtotal using the current selling prices.
    subtotal = calculate_cart_subtotal(cart_items)

    # Default values when no coupon is applied.
    coupon = None
    discount = Decimal('0.00')
    total = subtotal

    # Retrieve the coupon stored in the customer's session.
    coupon_code = request.session.get(
        'applied_coupon_code'
    )

    if coupon_code:

        coupon = Coupon.objects.filter(
            code__iexact=coupon_code
        ).first()

        if coupon:

            calculated_discount, error = validate_coupon_for_user(
                coupon,
                request.user,
                subtotal
            )

            # A coupon must leave a positive payable amount
            # because this checkout uses Razorpay.
            if not error and calculated_discount < subtotal:

                discount = calculated_discount
                total = subtotal - discount

            else:

                request.session.pop(
                    'applied_coupon_code',
                    None
                )

                request.session.modified = True

                coupon = None

                if error:
                    messages.warning(
                        request,
                        f'Your coupon is no longer applicable: {error}'
                    )
                else:
                    messages.warning(
                        request,
                        'This coupon would make the order total zero. '
                        'Please use a different coupon.'
                    )

        else:

            request.session.pop(
                'applied_coupon_code',
                None
            )

            request.session.modified = True

    checkout_token = uuid.uuid4().hex

    return render(
        request,
        'orders/checkout.html',
        {
            'cart': cart,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'discount': discount,
            'coupon': coupon,
            'total': total,
            'addresses': addresses,
            'checkout_token': checkout_token,
        }
    )
# =========================================================
# START RAZORPAY PAYMENT WITH COUPON SUPPORT
# =========================================================

@login_required
def start_payment(request):

    if request.method != 'POST':
        return redirect('checkout')

    payment_method = request.POST.get('payment_method')
    address_id = request.POST.get('address_id')
    checkout_token = request.POST.get('checkout_token')

    if payment_method != 'RAZORPAY':
        messages.error(
            request,
            'Please select Razorpay as your payment method.'
        )
        return redirect('checkout')

    if not checkout_token:
        messages.error(
            request,
            'Your checkout session has expired. Please try again.'
        )
        return redirect('checkout')

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    # Prevent duplicate checkout submissions.
    existing_payment = Payment.objects.filter(
        checkout_token=checkout_token,
        order__user=request.user
    ).select_related('order').first()

    if existing_payment:

        existing_order = existing_payment.order

        if existing_payment.status == 'PAID':
            return redirect(
                'order_success',
                order_id=existing_order.id
            )

        if (
            existing_payment.status == 'PENDING'
            and existing_payment.provider_order_id
        ):

            amount_paise = int(
                existing_payment.amount * Decimal('100')
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
                    'amount': amount_paise,
                }
            )

    razorpay_client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # Create the order and payment record atomically.
    with transaction.atomic():

        cart = Cart.objects.select_for_update().filter(
            user=request.user
        ).first()

        if not cart:
            messages.error(request, 'Your cart is empty.')
            return redirect('cart_detail')

        cart_items = list(
            cart.items.select_related('product')
        )

        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('cart_detail')

        # Check product availability and stock.
        for item in cart_items:

            product = item.product

            if not product.is_active:
                messages.error(
                    request,
                    f'{product.name} is no longer available.'
                )
                return redirect('cart_detail')

            if item.quantity > product.stock_quantity:
                messages.error(
                    request,
                    f'Only {product.stock_quantity} unit(s) of '
                    f'{product.name} are available.'
                )
                return redirect('cart_detail')

        # Calculate the subtotal on the server.
        subtotal = calculate_cart_subtotal(cart_items)

        if subtotal <= Decimal('0.00'):
            messages.error(
                request,
                'The order subtotal must be greater than zero.'
            )
            return redirect('checkout')

        # Validate the applied coupon again on the server.
        coupon = None
        discount = Decimal('0.00')

        coupon_code = request.session.get(
            'applied_coupon_code'
        )

        if coupon_code:

            coupon = Coupon.objects.filter(
                code__iexact=coupon_code
            ).first()

            if coupon:

                discount, coupon_error = validate_coupon_for_user(
                    coupon,
                    request.user,
                    subtotal
                )

                if coupon_error:

                    coupon = None
                    discount = Decimal('0.00')

                    request.session.pop(
                        'applied_coupon_code',
                        None
                    )

                    request.session.modified = True

                    messages.warning(
                        request,
                        f'Your coupon could not be applied: '
                        f'{coupon_error}'
                    )

            else:

                request.session.pop(
                    'applied_coupon_code',
                    None
                )

                request.session.modified = True

        # Prevent a zero-value or negative-value payment.
        if discount >= subtotal:
            coupon = None
            discount = Decimal('0.00')

            request.session.pop(
                'applied_coupon_code',
                None
            )

            request.session.modified = True

            messages.warning(
                request,
                'The coupon was removed because it would make '
                'the payable amount zero.'
            )

        # Calculate the final payable amount.
        total = (subtotal - discount).quantize(
            Decimal('0.01')
        )

        if total <= Decimal('0.00'):
            messages.error(
                request,
                'The final order amount must be greater than zero.'
            )
            return redirect('checkout')

        # Create the order with coupon details.
        order = Order.objects.create(
            user=request.user,
            subtotal_amount=subtotal,
            discount_amount=discount,
            coupon=coupon,
            coupon_code=coupon.code if coupon else '',
            total_amount=total,
            status='PENDING'
        )

        # Save a snapshot of the shipping address.
        OrderAddress.objects.create(
            order=order,
            full_name=address.full_name,
            phone=address.phone,
            address_line=address.address_line,
            city=address.city,
            state=address.state,
            pincode=address.pincode
        )

        # Save the ordered products and their prices.
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

        # Create the payment for the discounted total.
        payment = Payment.objects.create(
            order=order,
            checkout_token=checkout_token,
            amount=total,
            currency='INR',
            method='RAZORPAY',
            status='PENDING',
            provider='RAZORPAY'
        )

        # Razorpay expects the amount in paise.
        amount_paise = int(
            total * Decimal('100')
        )

        razorpay_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'order_{order.id}',
        }

        try:

            razorpay_order = razorpay_client.order.create(
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

        # Save the Razorpay order ID.
        payment.provider_order_id = razorpay_order['id']

        payment.save(
            update_fields=[
                'provider_order_id',
                'updated_at'
            ]
        )

    return render(
        request,
        'orders/payment.html',
        {
            'order': order,
            'payment': payment,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': amount_paise,
        }
    )

# =========================================================
# REDUCE PRODUCT STOCK
# =========================================================

def reduce_stock_for_order(order):
    """
    Reduce product stock after successful payment.

    Returns:
        True  - stock successfully reduced
        False - insufficient stock or unavailable product
    """

    order_items = list(
        order.items.select_related('product')
    )

    product_ids = [
        item.product_id
        for item in order_items
    ]

    products = {
        product.id: product
        for product in Product.objects.select_for_update().filter(
            id__in=product_ids
        )
    }

    # Check all products before changing any stock.
    for item in order_items:

        product = products.get(item.product_id)

        if not product:
            return False

        if not product.is_active:
            return False

        if product.stock_quantity < item.quantity:
            return False

    # Reduce stock.
    for item in order_items:

        product = products[item.product_id]

        product.stock_quantity -= item.quantity

        product.save(
            update_fields=[
                'stock_quantity',
                'updated_at'
            ]
        )

    return True


# =========================================================
# VERIFY RAZORPAY PAYMENT WITH COUPON REDEMPTION
# =========================================================

@login_required
def verify_payment(request):

    if request.method != 'POST':
        return redirect('my_orders')

    razorpay_payment_id = request.POST.get(
        'razorpay_payment_id',
        ''
    ).strip()

    razorpay_order_id = request.POST.get(
        'razorpay_order_id',
        ''
    ).strip()

    razorpay_signature = request.POST.get(
        'razorpay_signature',
        ''
    ).strip()

    # -----------------------------------------------------
    # VALIDATE SUBMITTED PAYMENT INFORMATION
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

    # Only retrieve a payment belonging to this customer.
    payment = get_object_or_404(
        Payment.objects.select_related('order'),
        provider_order_id=razorpay_order_id,
        order__user=request.user
    )

    order = payment.order

    # -----------------------------------------------------
    # HANDLE REPEATED VERIFICATION
    # -----------------------------------------------------

    if payment.status == 'PAID':

        if payment.provider_payment_id == razorpay_payment_id:
            return redirect(
                'order_success',
                order_id=order.id
            )

        return render(
            request,
            'orders/payment_failed.html',
            {
                'order': order,
                'message': (
                    'This order has already been paid. '
                    'The submitted payment does not match '
                    'the recorded payment.'
                )
            }
        )

    # Do not accept payments for cancelled orders.
    if order.status == 'CANCELLED':

        return render(
            request,
            'orders/payment_failed.html',
            {
                'order': order,
                'message': (
                    'This order has been cancelled. '
                    'Please contact support if a payment '
                    'was captured.'
                )
            }
        )

    # -----------------------------------------------------
    # INITIALIZE RAZORPAY CLIENT
    # -----------------------------------------------------

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # -----------------------------------------------------
    # VERIFY RAZORPAY SIGNATURE
    # -----------------------------------------------------

    try:

        client.utility.verify_payment_signature(
            {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
        )

    except razorpay.errors.SignatureVerificationError:

        return render(
            request,
            'orders/payment_failed.html',
            {
                'order': order,
                'message': 'Payment signature verification failed.'
            }
        )

    # -----------------------------------------------------
    # VERIFY PAYMENT STATUS, AMOUNT AND CURRENCY
    # -----------------------------------------------------

    try:

        gateway_payment = client.payment.fetch(
            razorpay_payment_id
        )

        gateway_order_id = gateway_payment.get('order_id')
        gateway_amount = gateway_payment.get('amount')
        gateway_currency = gateway_payment.get('currency')
        gateway_status = gateway_payment.get('status')

        expected_amount_paise = int(
            Decimal(str(payment.amount)) * Decimal('100')
        )

        if gateway_order_id != razorpay_order_id:

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'The payment does not match '
                        'the expected Razorpay order.'
                    )
                }
            )

        if gateway_amount != expected_amount_paise:

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'The payment amount does not match '
                        'your order total.'
                    )
                }
            )

        if gateway_currency != payment.currency:

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'The payment currency does not match '
                        'your order currency.'
                    )
                }
            )

        # The payment must be captured before it is marked paid.
        if gateway_status != 'captured':

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'Your payment has not been captured yet. '
                        'Please wait and check your payment status.'
                    )
                }
            )

    except Exception:

        return render(
            request,
            'orders/payment_failed.html',
            {
                'order': order,
                'message': (
                    'We could not verify the payment status '
                    'with Razorpay. Please check your payment '
                    'before attempting another payment.'
                )
            }
        )

    # -----------------------------------------------------
    # UPDATE PAYMENT, STOCK, ORDER AND COUPON ATOMICALLY
    # -----------------------------------------------------

    with transaction.atomic():

        payment = Payment.objects.select_for_update().get(
            id=payment.id
        )

        order = Order.objects.select_for_update().get(
            id=order.id
        )

        # Another request may already have processed payment.
        if payment.status == 'PAID':

            if payment.provider_payment_id == razorpay_payment_id:
                return redirect(
                    'order_success',
                    order_id=order.id
                )

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'This order has already been paid.'
                    )
                }
            )

        if order.status == 'CANCELLED':

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'This order has been cancelled.'
                    )
                }
            )

        # Recheck the stored payment amount.
        if Decimal(str(payment.amount)) != Decimal(
            str(order.total_amount)
        ):

            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'The saved payment amount does not '
                        'match the order total. Please contact support.'
                    )
                }
            )

        # -------------------------------------------------
        # CHECK AND REDUCE STOCK
        # -------------------------------------------------

        stock_reduced = reduce_stock_for_order(order)

        if not stock_reduced:

            # The gateway has already captured the payment.
            # Do not silently mark the order unpaid.
            # Manual resolution or a refund may be necessary.
            return render(
                request,
                'orders/payment_failed.html',
                {
                    'order': order,
                    'message': (
                        'Your payment was captured, but one or '
                        'more products are no longer available. '
                        'Please contact support for assistance '
                        'with your order or refund.'
                    )
                }
            )

        # -------------------------------------------------
        # RECORD VERIFIED PAYMENT DETAILS
        # -------------------------------------------------

        payment.status = 'PAID'
        payment.provider_payment_id = razorpay_payment_id
        payment.provider_signature = razorpay_signature
        payment.gateway_method = gateway_payment.get('method')

        payment.save(
            update_fields=[
                'status',
                'provider_payment_id',
                'provider_signature',
                'gateway_method',
                'updated_at'
            ]
        )

        # -------------------------------------------------
        # CONFIRM THE ORDER
        # -------------------------------------------------

        order.status = 'CONFIRMED'

        order.save(
            update_fields=[
                'status',
                'updated_at'
            ]
        )

        # -------------------------------------------------
        # RECORD COUPON REDEMPTION
        # -------------------------------------------------

        if order.coupon_id:

            # Lock the coupon row to reduce concurrent usage races.
            coupon = Coupon.objects.select_for_update().get(
                id=order.coupon_id
            )

            # The OneToOneField on CouponRedemption ensures
            # an order cannot have multiple redemption records.
            redemption, created = CouponRedemption.objects.get_or_create(
                order=order,
                defaults={
                    'coupon': coupon,
                    'user': order.user,
                    'discount_amount': order.discount_amount,
                }
            )

            if created:

                coupon.used_count += 1

                coupon.save(
                    update_fields=[
                        'used_count',
                        'updated_at'
                    ]
                )

    # -----------------------------------------------------
    # CLEAR CART AFTER SUCCESSFUL PAYMENT
    # -----------------------------------------------------

    cart = Cart.objects.filter(
        user=request.user
    ).first()

    if cart:
        cart.items.all().delete()

    # -----------------------------------------------------
    # SEND EMAIL NOTIFICATIONS
    # -----------------------------------------------------

    try:
        send_order_confirmation_email(order)
    except Exception:
        pass

    try:
        send_payment_confirmation_email(order, payment)
    except Exception:
        pass

    # -----------------------------------------------------
    # REDIRECT TO ORDER SUCCESS PAGE
    # -----------------------------------------------------

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

    order_id = request.POST.get('order_id')

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
            update_fields=['status', 'updated_at']
        )

    # Keep the order pending so payment can be retried.
    if order.status != 'CANCELLED':

        order.status = 'PENDING'

        order.save(
            update_fields=['status', 'updated_at']
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

    if payment.status not in ['FAILED', 'PENDING']:
        return redirect(
            'order_detail',
            order_id=order.id
        )

    if order.status == 'CANCELLED':
        return redirect(
            'order_detail',
            order_id=order.id
        )

    # Check inventory before allowing a retry.
    order_items = order.items.select_related('product')

    for item in order_items:

        product = item.product

        if not product.is_active:

            messages.error(
                request,
                f'{product.name} is no longer available.'
            )

            return redirect(
                'order_detail',
                order_id=order.id
            )

        if product.stock_quantity < item.quantity:

            messages.error(
                request,
                f'Only {product.stock_quantity} unit(s) of '
                f'{product.name} are available.'
            )

            return redirect(
                'order_detail',
                order_id=order.id
            )

    amount_paise = int(
        payment.amount * Decimal('100')
    )

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

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
                'message': 'Unable to start payment retry.'
            }
        )

    # Reset the existing payment record for the new attempt.
    payment.status = 'PENDING'
    payment.provider = 'RAZORPAY'
    payment.provider_order_id = razorpay_order['id']
    payment.provider_payment_id = None
    payment.provider_signature = None
    payment.gateway_method = None

    payment.save()

    return render(
        request,
        'orders/payment.html',
        {
            'order': order,
            'payment': payment,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': amount_paise,
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
    ).order_by('-created_at')

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
    # Fetch the logged-in customer's order.
    order = get_object_or_404(
        Order.objects.select_related("user"),
        id=order_id,
        user=request.user,
    )

    # Fetch all products associated with this order.
    order_items = order.items.select_related("product").all()

    # Calculate the total number of units.
    total_items = sum(
        item.quantity for item in order_items
    )

    # Calculate the saved order-item subtotal.
    calculated_total = sum(
        (
            Decimal(str(item.price)) * item.quantity
            for item in order_items
        ),
        Decimal("0.00"),
    )

    # Fetch the actual payment associated with this order.
    # Prefer a successful payment when multiple records exist.
    payment = (
        Payment.objects.filter(
            order=order,
            status="PAID",
        )
        .order_by("-id")
        .first()
    )

    # If no successful payment exists, fetch the latest payment.
    if payment is None:
        payment = (
            Payment.objects.filter(order=order)
            .order_by("-id")
            .first()
        )

    # Fetch the saved shipping address.
    shipping_address = getattr(
        order,
        "shipping_address",
        None,
    )

    context = {
        "order": order,
        "order_items": order_items,
        "total_items": total_items,
        "calculated_total": calculated_total,
        "payment": payment,
        "shipping_address": shipping_address,
    }

    return render(
        request,
        "orders/order_detail.html",
        context,
    )


@login_required
def track_order(request, order_id):
    """
    Display the tracking progress of an order
    belonging to the logged-in customer.
    """

    order = get_object_or_404(
        Order.objects.select_related("user"),
        id=order_id,
        user=request.user,
    )

    # Retrieve ordered products.
    order_items = order.items.select_related("product").all()

    # Retrieve the shipping address.
    shipping_address = getattr(
        order,
        "shipping_address",
        None,
    )

    # Define the delivery progress stages.
    tracking_steps = [
        {
            "status": "PENDING",
            "title": "Order Placed",
            "description": "Your order has been placed successfully.",
        },
        {
            "status": "CONFIRMED",
            "title": "Order Confirmed",
            "description": "Your order has been confirmed.",
        },
        {
            "status": "PROCESSING",
            "title": "Processing",
            "description": "Your order is being prepared.",
        },
        {
            "status": "SHIPPED",
            "title": "Shipped",
            "description": "Your order is on its way.",
        },
        {
            "status": "DELIVERED",
            "title": "Delivered",
            "description": "Your order has been delivered successfully.",
        },
    ]

    # Determine the current progress stage.
    status_order = [
        "PENDING",
        "CONFIRMED",
        "PROCESSING",
        "SHIPPED",
        "DELIVERED",
    ]

    if order.status == "CANCELLED":
        current_step = -1
    else:
        current_step = status_order.index(order.status)

    context = {
        "order": order,
        "order_items": order_items,
        "shipping_address": shipping_address,
        "tracking_steps": tracking_steps,
        "current_step": current_step,
    }

    return render(
        request,
        "orders/track_order.html",
        context,
    )


# =========================================================
# CANCEL ORDER
# =========================================================

@login_required
def cancel_order(request, order_id):
    if request.method != 'POST':
        return redirect('order_detail', order_id=order_id)

    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(),
            id=order_id,
            user=request.user
        )

        # Only pending orders can be cancelled using this view.
        if order.status != 'PENDING':
            messages.error(
                request,
                'This order cannot be cancelled because it is no longer pending.'
            )
            return redirect('order_detail', order_id=order.id)

        # Lock and check the associated payment record.
        try:
            payment = Payment.objects.select_for_update().get(
                order=order
            )
        except Payment.DoesNotExist:
            payment = None

        # Never cancel a paid order without handling its refund.
        if payment and payment.status == 'PAID':
            messages.error(
                request,
                'This order has been paid. Please contact support to request cancellation and a refund.'
            )
            return redirect('order_detail', order_id=order.id)

        # Stock is deducted after successful payment verification.
        # Therefore, do not restore stock for this pending order.
        order.status = 'CANCELLED'
        order.save(update_fields=['status', 'updated_at'])

    # Email failure should not undo a successful cancellation.
    try:
        send_order_status_email(order, 'CANCELLED')
    except Exception:
        pass

    messages.success(
        request,
        f'Order #{order.id} has been cancelled successfully.'
    )

    return redirect('order_detail', order_id=order.id)
# =========================================================
# SELLER DASHBOARD / ORDERS
# =========================================================

@login_required
def seller_orders(request):

    # Only sellers may access the seller dashboard.
    if getattr(request.user, 'role', None) != 'SELLER':
        return redirect('my_orders')

    if request.method == 'POST':

        action = request.POST.get('action')

        # -------------------------------------------------
        # UPDATE PRODUCT STOCK
        # -------------------------------------------------

        if action == 'update_stock':

            product_id = request.POST.get('product_id')

            stock_value = request.POST.get(
                'stock_quantity',
                ''
            ).strip()

            try:

                new_stock = int(stock_value)

                if new_stock < 0:
                    raise ValueError

            except (TypeError, ValueError):

                messages.error(
                    request,
                    'Please enter a valid stock quantity of 0 or more.'
                )

                return redirect('seller_dashboard')

            product = get_object_or_404(
                Product,
                id=product_id,
                seller=request.user
            )

            product.stock_quantity = new_stock

            product.save(
                update_fields=['stock_quantity', 'updated_at']
            )

            messages.success(
                request,
                f'Stock for "{product.name}" was updated to '
                f'{new_stock}.'
            )

            return redirect('seller_dashboard')

        # -------------------------------------------------
        # UPDATE ORDER STATUS
        # -------------------------------------------------

        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')

        order = get_object_or_404(
            Order.objects.filter(
                items__product__seller=request.user
            ).distinct(),
            id=order_id
        )

        total_items = order.items.count()

        seller_items = order.items.filter(
            product__seller=request.user
        ).count()

        # Do not permit a seller to update a mixed-seller order.
        if total_items == 0 or seller_items != total_items:

            messages.error(
                request,
                'This order contains products from another seller. '
                'You cannot change the full order status.'
            )

            return redirect('seller_dashboard')

        allowed_transitions = {
            'CONFIRMED': ['PROCESSING'],
            'PROCESSING': ['SHIPPED'],
            'SHIPPED': ['DELIVERED'],
        }

        allowed_statuses = allowed_transitions.get(
            order.status,
            []
        )

        if new_status not in allowed_statuses:

            messages.error(
                request,
                f'Invalid status change from '
                f'{order.get_status_display()} to {new_status}.'
            )

            return redirect('seller_dashboard')

        order.status = new_status

        order.save(
            update_fields=['status', 'updated_at']
        )

        # Notify the customer after a valid status change.
        send_order_status_email(order, new_status)

        messages.success(
            request,
            f'Order #{order.id} updated to '
            f'{order.get_status_display()}.'
        )

        return redirect('seller_dashboard')

    # Seller inventory.
    seller_products = Product.objects.filter(
        seller=request.user
    ).select_related(
        'category'
    ).prefetch_related(
        'images'
    ).order_by('name')

    # Seller orders.
    orders = (
        Order.objects
        .filter(
            items__product__seller=request.user
        )
        .distinct()
        .prefetch_related(
            'items__product__images'
        )
        .select_related('payment')
        .order_by('-created_at')
    )

    # Determine whether the seller may change each order's status.
    for order in orders:

        total_items = order.items.count()

        seller_items = order.items.filter(
            product__seller=request.user
        ).count()

        order.can_update_status = (
            total_items > 0
            and seller_items == total_items
        )

    return render(
        request,
        'orders/seller_orders.html',
        {
            'seller_products': seller_products,
            'orders': orders,
        }
    )


# =========================================================
# DOWNLOAD ORDER INVOICE AS PDF
# =========================================================
@login_required
def download_order_invoice(request, order_id):
    """
    Generate a PDF invoice for the logged-in customer's own order.
    Includes subtotal, coupon discount, and final order total.
    """

    from io import BytesIO
    from html import escape
    from decimal import Decimal

    from django.http import HttpResponse

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
        KeepTogether,
    )

    # -----------------------------------------------------
    # FETCH ORDER SECURELY
    # -----------------------------------------------------

    order = get_object_or_404(
        Order.objects.select_related('user', 'coupon'),
        id=order_id,
        user=request.user,
    )

    order_items = list(
        OrderItem.objects.filter(
            order=order
        ).select_related('product')
    )

    payment = Payment.objects.filter(
        order=order
    ).first()

    # OrderAddress has a OneToOneField to Order.
    try:
        shipping_address = order.shipping_address
    except OrderAddress.DoesNotExist:
        shipping_address = None

    # -----------------------------------------------------
    # CREATE PDF DOCUMENT
    # -----------------------------------------------------

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f'ShopSphere Invoice - Order {order.id}',
        author='ShopSphere',
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name='ShopSphereInvoiceTitle',
            parent=styles['Title'],
            fontName='Helvetica-Bold',
            fontSize=25,
            leading=30,
            textColor=colors.HexColor('#2874F0'),
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name='ShopSphereInvoiceHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=17,
            leading=21,
            textColor=colors.HexColor('#222222'),
            alignment=TA_RIGHT,
            spaceAfter=3,
        )
    )

    styles.add(
        ParagraphStyle(
            name='ShopSphereInvoiceSection',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#222222'),
            spaceBefore=2,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name='ShopSphereInvoiceSmall',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#555555'),
        )
    )

    styles.add(
        ParagraphStyle(
            name='ShopSphereInvoiceTableText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#222222'),
            wordWrap='CJK',
        )
    )

    styles.add(
        ParagraphStyle(
            name='ShopSphereInvoiceRight',
            parent=styles['ShopSphereInvoiceTableText'],
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name='ShopSphereInvoiceFooter',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#2874F0'),
        )
    )

    story = []

    # -----------------------------------------------------
    # HELPER FUNCTIONS
    # -----------------------------------------------------

    def safe_text(value):
        if value is None or value == '':
            return 'Not available'

        return escape(str(value))

    def paragraph(value, style='ShopSphereInvoiceTableText'):
        return Paragraph(
            safe_text(value),
            styles[style],
        )

    def bold_paragraph(
        value,
        style='ShopSphereInvoiceTableText',
    ):
        return Paragraph(
            f'<b>{safe_text(value)}</b>',
            styles[style],
        )

    def money(value):
        if value is None:
            value = Decimal('0.00')

        return f'INR {Decimal(str(value)):,.2f}'

    # -----------------------------------------------------
    # CALCULATE SUBTOTAL, DISCOUNT AND FINAL TOTAL
    # -----------------------------------------------------

    calculated_subtotal = Decimal('0.00')

    for item in order_items:
        unit_price = Decimal(str(item.price or 0))
        quantity = int(item.quantity or 0)

        calculated_subtotal += unit_price * quantity

    # Prefer the subtotal stored on the order.
    # Fall back to the sum of order items for older orders.
    stored_subtotal = getattr(order, 'subtotal_amount', None)

    if (
        stored_subtotal is not None
        and Decimal(str(stored_subtotal)) > Decimal('0.00')
    ):
        invoice_subtotal = Decimal(str(stored_subtotal))
    else:
        invoice_subtotal = calculated_subtotal

    # The discount must come from the saved order,
    # not from the customer's current session.
    stored_discount = getattr(
        order,
        'discount_amount',
        Decimal('0.00'),
    )

    invoice_discount = Decimal(str(stored_discount or '0.00'))

    if invoice_discount < Decimal('0.00'):
        invoice_discount = Decimal('0.00')

    # Do not display a discount larger than the subtotal.
    if invoice_discount > invoice_subtotal:
        invoice_discount = invoice_subtotal

    # The saved order total is authoritative.
    if order.total_amount is not None:
        invoice_total = Decimal(str(order.total_amount))
    else:
        invoice_total = invoice_subtotal - invoice_discount

    coupon_code = (
        getattr(order, 'coupon_code', '') or
        (
            order.coupon.code
            if getattr(order, 'coupon_id', None)
            else ''
        )
    )

    # -----------------------------------------------------
    # INVOICE HEADER
    # -----------------------------------------------------

    order_number = f'SS-{order.id:06d}'

    header_data = [
        [
            Paragraph(
                'ShopSphere',
                styles['ShopSphereInvoiceTitle'],
            ),
            Paragraph(
                '<b>ORDER INVOICE</b>',
                styles['ShopSphereInvoiceHeading'],
            ),
        ],
        [
            Paragraph(
                'Your trusted online shopping destination',
                styles['ShopSphereInvoiceSmall'],
            ),
            Paragraph(
                f'<b>Invoice No:</b> {safe_text(order_number)}',
                styles['ShopSphereInvoiceSmall'],
            ),
        ],
    ]

    header_table = Table(
        header_data,
        colWidths=[95 * mm, 77 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 5 * mm))

    story.append(
        HRFlowable(
            width='100%',
            thickness=1.2,
            color=colors.HexColor('#2874F0'),
        )
    )

    story.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------
    # ORDER INFORMATION
    # -----------------------------------------------------

    order_date = (
        order.created_at.strftime('%d %B %Y, %I:%M %p')
        if order.created_at
        else 'Not available'
    )

    order_information = [
        [
            bold_paragraph('Order Number'),
            paragraph(order_number),
            bold_paragraph('Order Date'),
            paragraph(order_date),
        ],
        [
            bold_paragraph('Order Status'),
            paragraph(order.get_status_display()),
            bold_paragraph('Customer ID'),
            paragraph(order.user_id),
        ],
    ]

    order_information_table = Table(
        order_information,
        colWidths=[29 * mm, 48 * mm, 26 * mm, 69 * mm],
    )

    order_information_table.setStyle(
        TableStyle(
            [
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, -1),
                    colors.HexColor('#F5F7FB'),
                ),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor('#E1E5ED'),
                ),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(order_information_table)
    story.append(Spacer(1, 7 * mm))

    # -----------------------------------------------------
    # CUSTOMER INFORMATION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            'CUSTOMER INFORMATION',
            styles['ShopSphereInvoiceSection'],
        )
    )

    customer_name = (
        order.user.get_full_name()
        or order.user.get_username()
    )

    customer_rows = [
        [
            bold_paragraph('Customer Name'),
            paragraph(customer_name),
        ],
        [
            bold_paragraph('Email'),
            paragraph(order.user.email or 'Not available'),
        ],
    ]

    customer_table = Table(
        customer_rows,
        colWidths=[42 * mm, 130 * mm],
    )

    customer_table.setStyle(
        TableStyle(
            [
                (
                    'LINEBELOW',
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor('#E5E7EB'),
                ),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(customer_table)
    story.append(Spacer(1, 7 * mm))

    # -----------------------------------------------------
    # DELIVERY ADDRESS
    # -----------------------------------------------------

    story.append(
        Paragraph(
            'DELIVERY ADDRESS',
            styles['ShopSphereInvoiceSection'],
        )
    )

    if shipping_address:

        address_rows = [
            [
                bold_paragraph('Recipient'),
                paragraph(shipping_address.full_name),
            ],
            [
                bold_paragraph('Phone'),
                paragraph(shipping_address.phone),
            ],
            [
                bold_paragraph('Address'),
                paragraph(shipping_address.address_line),
            ],
            [
                bold_paragraph('City'),
                paragraph(shipping_address.city),
            ],
            [
                bold_paragraph('State'),
                paragraph(shipping_address.state),
            ],
            [
                bold_paragraph('PIN Code'),
                paragraph(shipping_address.pincode),
            ],
        ]

        address_table = Table(
            address_rows,
            colWidths=[42 * mm, 130 * mm],
        )

        address_table.setStyle(
            TableStyle(
                [
                    (
                        'GRID',
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor('#E1E5ED'),
                    ),
                    (
                        'BACKGROUND',
                        (0, 0),
                        (0, -1),
                        colors.HexColor('#F5F7FB'),
                    ),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]
            )
        )

        story.append(address_table)

    else:

        story.append(
            paragraph(
                'Shipping address information is unavailable.',
                'ShopSphereInvoiceSmall',
            )
        )

    story.append(Spacer(1, 7 * mm))

    # -----------------------------------------------------
    # ORDER ITEMS
    # -----------------------------------------------------

    story.append(
        Paragraph(
            'ORDER ITEMS',
            styles['ShopSphereInvoiceSection'],
        )
    )

    item_rows = [
        [
            bold_paragraph('#'),
            bold_paragraph('Product'),
            bold_paragraph('Unit Price', 'ShopSphereInvoiceRight'),
            bold_paragraph('Qty', 'ShopSphereInvoiceRight'),
            bold_paragraph('Subtotal', 'ShopSphereInvoiceRight'),
        ]
    ]

    for index, item in enumerate(order_items, start=1):

        unit_price = Decimal(str(item.price or 0))
        quantity = int(item.quantity or 0)
        line_total = unit_price * quantity

        product_name = (
            item.product.name
            if item.product_id
            else 'Product unavailable'
        )

        item_rows.append(
            [
                paragraph(index),
                paragraph(product_name),
                paragraph(
                    money(unit_price),
                    'ShopSphereInvoiceRight',
                ),
                paragraph(
                    quantity,
                    'ShopSphereInvoiceRight',
                ),
                paragraph(
                    money(line_total),
                    'ShopSphereInvoiceRight',
                ),
            ]
        )

    if not order_items:

        item_rows.append(
            [
                paragraph(''),
                paragraph('No order items found'),
                paragraph(''),
                paragraph(''),
                paragraph(''),
            ]
        )

    products_table = Table(
        item_rows,
        colWidths=[
            10 * mm,
            62 * mm,
            35 * mm,
            17 * mm,
            48 * mm,
        ],
        repeatRows=1,
        hAlign='LEFT',
    )

    products_table.setStyle(
        TableStyle(
            [
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, 0),
                    colors.HexColor('#2874F0'),
                ),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor('#DDE2E8'),
                ),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor('#F8FAFC'),
                    ],
                ),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ]
        )
    )

    story.append(products_table)
    story.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------
    # SUBTOTAL, COUPON DISCOUNT AND FINAL TOTAL
    # -----------------------------------------------------

    total_rows = [
        [
            paragraph('Subtotal'),
            paragraph(
                money(invoice_subtotal),
                'ShopSphereInvoiceRight',
            ),
        ]
    ]

    # Show the coupon line only when a coupon was saved
    # against this order and a positive discount was recorded.
    if coupon_code and invoice_discount > Decimal('0.00'):

        total_rows.append(
            [
                paragraph(f'Coupon Applied: {coupon_code}'),
                paragraph(
                    f'- {money(invoice_discount)}',
                    'ShopSphereInvoiceRight',
                ),
            ]
        )

    elif invoice_discount > Decimal('0.00'):

        total_rows.append(
            [
                paragraph('Discount'),
                paragraph(
                    f'- {money(invoice_discount)}',
                    'ShopSphereInvoiceRight',
                ),
            ]
        )

    total_rows.append(
        [
            bold_paragraph('ORDER TOTAL'),
            bold_paragraph(
                money(invoice_total),
                'ShopSphereInvoiceRight',
            ),
        ]
    )

    totals_table = Table(
        total_rows,
        colWidths=[132 * mm, 40 * mm],
        hAlign='RIGHT',
    )

    totals_table.setStyle(
        TableStyle(
            [
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, -2),
                    colors.white,
                ),
                (
                    'BACKGROUND',
                    (0, -1),
                    (-1, -1),
                    colors.HexColor('#EAF1FF'),
                ),
                (
                    'BOX',
                    (0, -1),
                    (-1, -1),
                    0.8,
                    colors.HexColor('#2874F0'),
                ),
                (
                    'LINEBELOW',
                    (0, 0),
                    (-1, -2),
                    0.4,
                    colors.HexColor('#E1E5ED'),
                ),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 9),
                ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ]
        )
    )

    story.append(totals_table)
    story.append(Spacer(1, 7 * mm))

    # -----------------------------------------------------
    # PAYMENT INFORMATION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            'PAYMENT INFORMATION',
            styles['ShopSphereInvoiceSection'],
        )
    )

    if payment:

        payment_status = (
            payment.get_status_display()
            if payment.status
            else 'Not recorded'
        )

        payment_method = (
            payment.get_method_display()
            if payment.method
            else 'Not recorded'
        )

        gateway_method = (
            payment.gateway_method
            or 'Not provided by gateway'
        )

        payment_rows = [
            [
                bold_paragraph('Payment Status'),
                paragraph(payment_status),
            ],
            [
                bold_paragraph('Payment Method'),
                paragraph(payment_method),
            ],
            [
                bold_paragraph('Payment Provider'),
                paragraph(payment.get_provider_display()),
            ],
            [
                bold_paragraph('Gateway Instrument'),
                paragraph(gateway_method),
            ],
            [
                bold_paragraph('Payment Amount'),
                paragraph(money(payment.amount)),
            ],
            [
                bold_paragraph('Currency'),
                paragraph(payment.currency or 'INR'),
            ],
            [
                bold_paragraph('Razorpay Order ID'),
                paragraph(payment.provider_order_id or 'Not available'),
            ],
            [
                bold_paragraph('Razorpay Payment ID'),
                paragraph(payment.provider_payment_id or 'Not available'),
            ],
        ]

    else:

        payment_rows = [
            [
                bold_paragraph('Payment Status'),
                paragraph('No payment record found'),
            ],
        ]

    payment_table = Table(
        payment_rows,
        colWidths=[48 * mm, 124 * mm],
    )

    payment_table.setStyle(
        TableStyle(
            [
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor('#E1E5ED'),
                ),
                (
                    'BACKGROUND',
                    (0, 0),
                    (0, -1),
                    colors.HexColor('#F5F7FB'),
                ),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(payment_table)
    story.append(Spacer(1, 10 * mm))

    # -----------------------------------------------------
    # FOOTER
    # -----------------------------------------------------

    story.append(
        HRFlowable(
            width='100%',
            thickness=0.7,
            color=colors.HexColor('#DDE2E8'),
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        KeepTogether(
            [
                Paragraph(
                    '<b>Thank you for shopping with ShopSphere!</b>',
                    styles['ShopSphereInvoiceFooter'],
                ),
                Spacer(1, 2 * mm),
                Paragraph(
                    'This invoice was generated electronically by ShopSphere.',
                    styles['ShopSphereInvoiceSmall'],
                ),
            ]
        )
    )

    # -----------------------------------------------------
    # BUILD AND DOWNLOAD PDF
    # -----------------------------------------------------

    document.build(story)

    pdf_data = buffer.getvalue()
    buffer.close()

    response = HttpResponse(
        pdf_data,
        content_type='application/pdf',
    )

    response['Content-Disposition'] = (
        f'attachment; filename="ShopSphere_Invoice_{order.id}.pdf"'
    )

    response['Content-Length'] = str(len(pdf_data))

    return response

# =========================================================
# COUPON HELPERS
# =========================================================

def calculate_cart_subtotal(cart_items):
    """
    Calculate the cart subtotal using the current selling prices.
    """

    return sum(
        (
            Decimal(
                str(
                    item.product.discount_price
                    or item.product.price
                )
            ) * item.quantity
            for item in cart_items
        ),
        Decimal('0.00')
    )


def validate_coupon_for_user(coupon, user, subtotal):
    """
    Validate a coupon for a customer and calculate its discount.

    Returns:
        (discount_amount, error_message)

    A valid coupon returns an empty error message.
    """

    subtotal = Decimal(str(subtotal))

    if not coupon.is_valid:
        return Decimal('0.00'), (
            'This coupon is inactive, expired, '
            'not yet available, or has reached its usage limit.'
        )

    if subtotal < coupon.minimum_order_amount:
        return Decimal('0.00'), (
            f'Minimum order amount for this coupon is '
            f'₹{coupon.minimum_order_amount}.'
        )

    if (
        coupon.one_use_per_customer
        and CouponRedemption.objects.filter(
            coupon=coupon,
            user=user
        ).exists()
    ):
        return Decimal('0.00'), (
            'You have already used this coupon.'
        )

    discount = coupon.calculate_discount(subtotal)

    if discount <= Decimal('0.00'):
        return Decimal('0.00'), (
            'This coupon does not provide a discount for this order.'
        )

    return discount, ''

# =========================================================
# APPLY COUPON
# =========================================================

@login_required
def apply_coupon(request):

    if request.method != 'POST':
        return redirect('checkout')

    code = request.POST.get('coupon_code', '').strip()

    if not code:
        messages.error(request, 'Please enter a coupon code.')
        return redirect('checkout')

    cart = Cart.objects.filter(user=request.user).first()

    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart_detail')

    cart_items = cart.items.select_related('product')

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart_detail')

    subtotal = calculate_cart_subtotal(cart_items)

    coupon = Coupon.objects.filter(
        code__iexact=code
    ).first()

    if not coupon:
        request.session.pop('applied_coupon_code', None)

        messages.error(
            request,
            'Invalid coupon code.'
        )

        return redirect('checkout')

    discount, error = validate_coupon_for_user(
        coupon,
        request.user,
        subtotal
    )

    if error:
        request.session.pop('applied_coupon_code', None)

        messages.error(request, error)

        return redirect('checkout')

    request.session['applied_coupon_code'] = coupon.code
    request.session.modified = True

    messages.success(
        request,
        f'Coupon {coupon.code} applied successfully! '
        f'You saved ₹{discount:.2f}.'
    )

    return redirect('checkout')


# =========================================================
# REMOVE COUPON
# =========================================================

@login_required
def remove_coupon(request):

    if request.method != 'POST':
        return redirect('checkout')

    request.session.pop('applied_coupon_code', None)
    request.session.modified = True

    messages.success(
        request,
        'Coupon removed successfully.'
    )

    return redirect('checkout')