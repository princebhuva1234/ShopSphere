import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order
from payments.models import Payment
from returns.models import ReturnRequest

from orders.views import reduce_stock_for_order


@csrf_exempt
def razorpay_webhook(request):

    # Only accept POST requests.
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    # Get webhook secret.
    webhook_secret = getattr(
        settings,
        'RAZORPAY_WEBHOOK_SECRET',
        '',
    )

    if not webhook_secret:
        return HttpResponse(
            'Webhook secret not configured',
            status=500,
        )

    # Get Razorpay signature.
    received_signature = request.headers.get(
        'X-Razorpay-Signature',
        '',
    )

    if not received_signature:
        return HttpResponse('Missing signature', status=400)

    # Verify webhook signature.
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        received_signature,
        expected_signature,
    ):
        return HttpResponse('Invalid signature', status=400)

    # Parse JSON.
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse('Invalid JSON', status=400)

    event = payload.get('event', '')

    entities = payload.get('payload', {})

    # =====================================================
    # ORDER PAID
    # =====================================================

    if event == 'order.paid':

        order_entity = (
            entities.get('order', {}).get('entity', {})
        )

        payment_entity = (
            entities.get('payment', {}).get('entity', {})
        )

        provider_order_id = order_entity.get('id')
        razorpay_payment_id = payment_entity.get('id')
        gateway_method = payment_entity.get('method')

        razorpay_amount = order_entity.get('amount_paid')

        if not provider_order_id:
            return JsonResponse(
                {'status': 'missing_order_id'},
                status=400,
            )

        payment = (
            Payment.objects
            .select_related('order')
            .filter(provider_order_id=provider_order_id)
            .first()
        )

        if not payment:
            return JsonResponse(
                {'status': 'payment_not_found'},
                status=200,
            )

        with transaction.atomic():

            payment = (
                Payment.objects
                .select_for_update()
                .get(id=payment.id)
            )

            order = (
                Order.objects
                .select_for_update()
                .get(id=payment.order_id)
            )

            # Idempotency: do not process an already-paid payment.
            if payment.status == 'PAID':
                return JsonResponse(
                    {'status': 'already_processed'},
                    status=200,
                )

            expected_amount = int(payment.amount * 100)

            if (
                razorpay_amount is not None
                and int(razorpay_amount) != expected_amount
            ):
                payment.status = 'FAILED'
                payment.save(
                    update_fields=['status', 'updated_at']
                )

                return JsonResponse(
                    {'status': 'amount_mismatch'},
                    status=400,
                )

            # Reduce stock only after a successful payment.
            stock_reduced = reduce_stock_for_order(order)

            if not stock_reduced:
                payment.status = 'FAILED'
                payment.save(
                    update_fields=['status', 'updated_at']
                )

                order.status = 'CANCELLED'
                order.save(
                    update_fields=['status', 'updated_at']
                )

                return JsonResponse(
                    {'status': 'insufficient_stock'},
                    status=409,
                )

            payment.status = 'PAID'
            payment.provider_payment_id = razorpay_payment_id
            payment.gateway_method = gateway_method

            payment.save(
                update_fields=[
                    'status',
                    'provider_payment_id',
                    'gateway_method',
                    'updated_at',
                ]
            )

            if order.status != 'CONFIRMED':
                order.status = 'CONFIRMED'
                order.save(
                    update_fields=['status', 'updated_at']
                )

        return JsonResponse({'status': 'success'}, status=200)

    # =====================================================
    # PAYMENT FAILED
    # =====================================================

    if event == 'payment.failed':

        payment_entity = (
            entities.get('payment', {}).get('entity', {})
        )

        provider_order_id = payment_entity.get('order_id')
        razorpay_payment_id = payment_entity.get('id')
        gateway_method = payment_entity.get('method')

        payment = None

        if provider_order_id:
            payment = Payment.objects.filter(
                provider_order_id=provider_order_id,
            ).first()

        if not payment and razorpay_payment_id:
            payment = Payment.objects.filter(
                provider_payment_id=razorpay_payment_id,
            ).first()

        if not payment:
            return JsonResponse(
                {'status': 'payment_not_found'},
                status=200,
            )

        with transaction.atomic():

            payment = (
                Payment.objects
                .select_for_update()
                .get(id=payment.id)
            )

            # Never change a successful payment to FAILED.
            if payment.status in ('PAID', 'REFUNDED'):
                return JsonResponse(
                    {'status': 'already_paid_or_refunded'},
                    status=200,
                )

            payment.status = 'FAILED'

            if razorpay_payment_id:
                payment.provider_payment_id = razorpay_payment_id

            if gateway_method:
                payment.gateway_method = gateway_method

            payment.save(
                update_fields=[
                    'status',
                    'provider_payment_id',
                    'gateway_method',
                    'updated_at',
                ]
            )

        return JsonResponse(
            {'status': 'payment_failed'},
            status=200,
        )

    # =====================================================
    # REFUND PROCESSED
    # =====================================================

    if event == 'refund.processed':

        refund_entity = (
            entities.get('refund', {}).get('entity', {})
        )

        refund_id = refund_entity.get('id')
        razorpay_payment_id = refund_entity.get('payment_id')
        refund_amount_paise = refund_entity.get('amount')

        if not refund_id or not razorpay_payment_id:
            return JsonResponse(
                {'status': 'missing_refund_information'},
                status=400,
            )

        with transaction.atomic():

            payment = (
                Payment.objects
                .select_for_update()
                .filter(
                    provider_payment_id=razorpay_payment_id,
                    provider='RAZORPAY',
                )
                .first()
            )

            if not payment:
                return JsonResponse(
                    {'status': 'payment_not_found'},
                    status=200,
                )

            # Match this gateway refund to a ShopSphere return request.
            return_request = (
                ReturnRequest.objects
                .select_for_update()
                .filter(
                    payment=payment,
                    razorpay_refund_id=refund_id,
                )
                .first()
            )

            if not return_request:
                return JsonResponse(
                    {'status': 'return_request_not_found'},
                    status=200,
                )

            # Validate the reported refund amount.
            expected_refund_paise = int(
                return_request.refund_amount * 100
            )

            if (
                refund_amount_paise is not None
                and int(refund_amount_paise) != expected_refund_paise
            ):
                return JsonResponse(
                    {'status': 'refund_amount_mismatch'},
                    status=400,
                )

            # A refund is final only after Razorpay confirms processing.
            return_request.status = 'REFUNDED'

            return_request.save(
                update_fields=['status', 'updated_at']
            )

            # This implementation supports full refunds only.
            # Do not mark the whole payment refunded for a partial refund.
            if return_request.refund_amount == payment.amount:
                payment.status = 'REFUNDED'
                payment.save(
                    update_fields=['status', 'updated_at']
                )

        return JsonResponse(
            {'status': 'refund_processed'},
            status=200,
        )

    # =====================================================
    # REFUND FAILED
    # =====================================================

    if event == 'refund.failed':

        refund_entity = (
            entities.get('refund', {}).get('entity', {})
        )

        refund_id = refund_entity.get('id')
        razorpay_payment_id = refund_entity.get('payment_id')

        if not refund_id or not razorpay_payment_id:
            return JsonResponse(
                {'status': 'missing_refund_information'},
                status=400,
            )

        with transaction.atomic():

            payment = (
                Payment.objects
                .select_for_update()
                .filter(
                    provider_payment_id=razorpay_payment_id,
                    provider='RAZORPAY',
                )
                .first()
            )

            if not payment:
                return JsonResponse(
                    {'status': 'payment_not_found'},
                    status=200,
                )

            return_request = (
                ReturnRequest.objects
                .select_for_update()
                .filter(
                    payment=payment,
                    razorpay_refund_id=refund_id,
                    status='REFUND_PROCESSING',
                )
                .first()
            )

            if not return_request:
                return JsonResponse(
                    {'status': 'return_request_not_found_or_already_updated'},
                    status=200,
                )

            # Do not automatically retry a failed refund.
            # The administrator must review the failure first.
            return_request.status = 'APPROVED'
            return_request.admin_note = (
                f'{return_request.admin_note}\n'
                f'Razorpay reported refund {refund_id} as failed. '
                'Review the Razorpay Dashboard before retrying.'
            ).strip()

            return_request.save(
                update_fields=[
                    'status',
                    'admin_note',
                    'updated_at',
                ]
            )

        return JsonResponse(
            {'status': 'refund_failed'},
            status=200,
        )

    # =====================================================
    # OTHER EVENTS
    # =====================================================

    return JsonResponse(
        {
            'status': 'ignored',
            'event': event,
        },
        status=200,
    )