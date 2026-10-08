import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import razorpay

from .models import Payment


# =========================================================
# RAZORPAY WEBHOOK
# =========================================================

@csrf_exempt
def razorpay_webhook(request):

    # -----------------------------------------------------
    # ONLY POST IS ALLOWED
    # -----------------------------------------------------

    if request.method != 'POST':

        return JsonResponse(
            {
                'error': 'Method not allowed'
            },
            status=405
        )

    # -----------------------------------------------------
    # GET WEBHOOK SECRET
    # -----------------------------------------------------

    webhook_secret = getattr(
        settings,
        'RAZORPAY_WEBHOOK_SECRET',
        None
    )

    if not webhook_secret:

        return JsonResponse(
            {
                'error':
                    'Webhook secret is not configured.'
            },
            status=500
        )

    # -----------------------------------------------------
    # GET RAZORPAY SIGNATURE
    # -----------------------------------------------------

    received_signature = request.headers.get(
        'X-Razorpay-Signature'
    )

    if not received_signature:

        return JsonResponse(
            {
                'error':
                    'Missing Razorpay signature.'
            },
            status=400
        )

    # =====================================================
    # VERIFY HMAC SIGNATURE
    # =====================================================

    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        request.body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        received_signature,
        expected_signature
    ):

        return JsonResponse(
            {
                'error':
                    'Invalid webhook signature.'
            },
            status=400
        )

    # =====================================================
    # PARSE JSON
    # =====================================================

    try:

        payload = json.loads(
            request.body.decode('utf-8')
        )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError
    ):

        return JsonResponse(
            {
                'error':
                    'Invalid JSON payload.'
            },
            status=400
        )

    # -----------------------------------------------------
    # EVENT
    # -----------------------------------------------------

    event = payload.get('event')

    # =====================================================
    # ORDER PAID
    # =====================================================

    if event == 'order.paid':

        order_entity = (
            payload
            .get('payload', {})
            .get('order', {})
            .get('entity', {})
        )

        payment_entity = (
            payload
            .get('payload', {})
            .get('payment', {})
            .get('entity', {})
        )

        razorpay_order_id = order_entity.get(
            'id'
        )

        razorpay_payment_id = payment_entity.get(
            'id'
        )

        gateway_method = payment_entity.get(
            'method'
        )

        # -------------------------------------------------
        # FIND OUR PAYMENT
        # -------------------------------------------------

        if not razorpay_order_id:

            return JsonResponse(
                {
                    'error':
                        'Razorpay order ID missing.'
                },
                status=400
            )

        payment = Payment.objects.filter(
            provider_order_id=razorpay_order_id
        ).select_related(
            'order'
        ).first()

        if not payment:

            # Return 200 so Razorpay does not keep retrying
            # an event for an order that does not belong
            # to this application.
            return JsonResponse(
                {
                    'status':
                        'ignored'
                },
                status=200
            )

        # =================================================
        # IDEMPOTENCY
        # =================================================

        with transaction.atomic():

            payment = Payment.objects.select_for_update().get(
                id=payment.id
            )

            order = payment.order

            # If we already processed this payment,
            # do nothing.
            if (
                payment.status == 'PAID'
                and (
                    not razorpay_payment_id
                    or
                    payment.provider_payment_id
                    == razorpay_payment_id
                )
            ):

                return JsonResponse(
                    {
                        'status':
                            'already_processed'
                    },
                    status=200
                )

            # -------------------------------------------------
            # OPTIONAL AMOUNT CHECK
            # -------------------------------------------------

            razorpay_amount_paid = order_entity.get(
                'amount_paid'
            )

            expected_amount = int(
                payment.amount * 100
            )

            if (
                razorpay_amount_paid is not None
                and int(razorpay_amount_paid)
                != expected_amount
            ):

                return JsonResponse(
                    {
                        'error':
                            'Payment amount mismatch.'
                    },
                    status=400
                )

            # -------------------------------------------------
            # UPDATE PAYMENT
            # -------------------------------------------------

            payment.status = 'PAID'

            if razorpay_payment_id:

                payment.provider_payment_id = (
                    razorpay_payment_id
                )

            if gateway_method:

                payment.gateway_method = (
                    gateway_method
                )

            payment.save(
                update_fields=[
                    'status',
                    'provider_payment_id',
                    'gateway_method',
                    'updated_at'
                ]
            )

            # -------------------------------------------------
            # UPDATE ORDER
            # -------------------------------------------------

            if order.status != 'CONFIRMED':

                order.status = 'CONFIRMED'

                order.save(
                    update_fields=[
                        'status',
                        'updated_at'
                    ]
                )

        return JsonResponse(
            {
                'status':
                    'processed'
            },
            status=200
        )

    # =====================================================
    # PAYMENT FAILED
    # =====================================================

    if event == 'payment.failed':

        payment_entity = (
            payload
            .get('payload', {})
            .get('payment', {})
            .get('entity', {})
        )

        razorpay_payment_id = payment_entity.get(
            'id'
        )

        razorpay_order_id = payment_entity.get(
            'order_id'
        )

        gateway_method = payment_entity.get(
            'method'
        )

        # -------------------------------------------------
        # FIND PAYMENT
        # -------------------------------------------------

        payment = None

        if razorpay_order_id:

            payment = Payment.objects.filter(
                provider_order_id=razorpay_order_id
            ).select_related(
                'order'
            ).first()

        if (
            not payment
            and razorpay_payment_id
        ):

            payment = Payment.objects.filter(
                provider_payment_id=
                    razorpay_payment_id
            ).select_related(
                'order'
            ).first()

        if not payment:

            return JsonResponse(
                {
                    'status':
                        'ignored'
                },
                status=200
            )

        # =================================================
        # IDEMPOTENT FAILURE HANDLING
        # =================================================

        with transaction.atomic():

            payment = Payment.objects.select_for_update().get(
                id=payment.id
            )

            # Never change an already successful payment
            # back to FAILED.
            if payment.status == 'PAID':

                return JsonResponse(
                    {
                        'status':
                            'already_paid'
                    },
                    status=200
                )

            payment.status = 'FAILED'

            if razorpay_payment_id:

                payment.provider_payment_id = (
                    razorpay_payment_id
                )

            if gateway_method:

                payment.gateway_method = (
                    gateway_method
                )

            payment.save(
                update_fields=[
                    'status',
                    'provider_payment_id',
                    'gateway_method',
                    'updated_at'
                ]
            )

        return JsonResponse(
            {
                'status':
                    'processed'
            },
            status=200
        )

    # =====================================================
    # OTHER / UNKNOWN EVENT
    # =====================================================

    return JsonResponse(
        {
            'status':
                'ignored'
        },
        status=200
    )