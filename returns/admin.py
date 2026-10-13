from decimal import Decimal

import razorpay

from django.conf import settings
from django.contrib import admin, messages
from django.db import transaction

from .models import ReturnRequest
from payments.models import Payment


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'order',
        'customer',
        'reason',
        'refund_amount',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'reason',
        'created_at',
    )

    search_fields = (
        'customer__username',
        'customer__email',
        'order__id',
        'razorpay_refund_id',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'razorpay_refund_id',
    )

    list_per_page = 25

    actions = (
        'approve_return_requests',
        'reject_return_requests',
        'process_razorpay_refunds',
    )

    fieldsets = (
        (
            'Return Information',
            {
                'fields': (
                    'order',
                    'customer',
                    'payment',
                    'reason',
                    'description',
                )
            },
        ),
        (
            'Return Status',
            {
                'fields': (
                    'status',
                    'admin_note',
                )
            },
        ),
        (
            'Refund Information',
            {
                'fields': (
                    'refund_amount',
                    'razorpay_refund_id',
                )
            },
        ),
        (
            'Timestamps',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                )
            },
        ),
    )

    @admin.action(description='Approve selected return requests')
    def approve_return_requests(self, request, queryset):

        approved_count = 0

        for return_request in queryset:

            with transaction.atomic():

                item = ReturnRequest.objects.select_for_update().get(
                    pk=return_request.pk
                )

                if item.status != 'PENDING':
                    self.message_user(
                        request,
                        f'Return #{item.pk} is not pending.',
                        level=messages.WARNING,
                    )
                    continue

                order = item.order

                if order.status != 'DELIVERED':
                    self.message_user(
                        request,
                        f'Return #{item.pk}: order is not delivered.',
                        level=messages.ERROR,
                    )
                    continue

                payment = Payment.objects.filter(
                    order=order,
                    status='PAID',
                ).first()

                if not payment:
                    self.message_user(
                        request,
                        f'Return #{item.pk}: no successful payment found.',
                        level=messages.ERROR,
                    )
                    continue

                # Prevent a second active or completed return
                # from being approved for the same order.
                another_return = ReturnRequest.objects.filter(
                    order=order,
                    status__in=[
                        'APPROVED',
                        'REFUND_PROCESSING',
                        'REFUNDED',
                    ],
                ).exclude(pk=item.pk).exists()

                if another_return:
                    self.message_user(
                        request,
                        f'Return #{item.pk}: another return is already active.',
                        level=messages.ERROR,
                    )
                    continue

                # This implementation supports full refunds.
                item.payment = payment
                item.refund_amount = payment.amount
                item.status = 'APPROVED'

                item.save(
                    update_fields=[
                        'payment',
                        'refund_amount',
                        'status',
                        'updated_at',
                    ]
                )

                approved_count += 1

        if approved_count:
            self.message_user(
                request,
                f'{approved_count} return request(s) approved. '
                'You can now process their refunds.',
                level=messages.SUCCESS,
            )

    @admin.action(description='Reject selected pending return requests')
    def reject_return_requests(self, request, queryset):

        rejected_count = 0

        for return_request in queryset:

            with transaction.atomic():

                item = ReturnRequest.objects.select_for_update().get(
                    pk=return_request.pk
                )

                if item.status != 'PENDING':
                    self.message_user(
                        request,
                        f'Return #{item.pk} is not pending and cannot be rejected.',
                        level=messages.WARNING,
                    )
                    continue

                item.status = 'REJECTED'
                item.admin_note = (
                    'Return request rejected by administrator.'
                )

                item.save(
                    update_fields=[
                        'status',
                        'admin_note',
                        'updated_at',
                    ]
                )

                rejected_count += 1

        if rejected_count:
            self.message_user(
                request,
                f'{rejected_count} return request(s) rejected.',
                level=messages.SUCCESS,
            )

    @admin.action(description='Process Razorpay refunds for approved returns')
    def process_razorpay_refunds(self, request, queryset):

        key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

        if not key_id or not key_secret:
            self.message_user(
                request,
                'Razorpay credentials are missing from Django settings.',
                level=messages.ERROR,
            )
            return

        client = razorpay.Client(
            auth=(key_id, key_secret)
        )

        for selected_item in queryset:

            # Lock and reserve the request before contacting Razorpay.
            with transaction.atomic():

                item = ReturnRequest.objects.select_for_update().get(
                    pk=selected_item.pk
                )

                if item.status != 'APPROVED':
                    self.message_user(
                        request,
                        f'Return #{item.pk} must be approved before refunding.',
                        level=messages.WARNING,
                    )
                    continue

                payment = Payment.objects.select_for_update().filter(
                    order=item.order,
                    status='PAID',
                ).first()

                if not payment:
                    self.message_user(
                        request,
                        f'Return #{item.pk}: a paid payment was not found.',
                        level=messages.ERROR,
                    )
                    continue

                if payment.provider != 'RAZORPAY':
                    self.message_user(
                        request,
                        f'Return #{item.pk}: payment was not made through Razorpay.',
                        level=messages.ERROR,
                    )
                    continue

                if not payment.provider_payment_id:
                    self.message_user(
                        request,
                        f'Return #{item.pk}: Razorpay payment ID is missing.',
                        level=messages.ERROR,
                    )
                    continue

                if item.razorpay_refund_id:
                    self.message_user(
                        request,
                        f'Return #{item.pk}: a refund ID already exists. '
                        'Check Razorpay before taking further action.',
                        level=messages.WARNING,
                    )
                    continue

                amount = Decimal(str(item.refund_amount))

                if amount <= 0 or amount > payment.amount:
                    self.message_user(
                        request,
                        f'Return #{item.pk}: refund amount is invalid.',
                        level=messages.ERROR,
                    )
                    continue

                # Reserve the request before making the external API call.
                # If the API result becomes ambiguous, do not automatically
                # retry because Razorpay might already have created a refund.
                item.status = 'REFUND_PROCESSING'

                item.save(
                    update_fields=[
                        'status',
                        'updated_at',
                    ]
                )

                payment_id = payment.provider_payment_id
                refund_amount_paise = int(amount * 100)
                return_id = item.pk
                order_id = item.order_id

            try:

                refund_response = client.payment.refund(
                    payment_id,
                    {
                        'amount': refund_amount_paise,
                        'notes': {
                            'return_request_id': str(return_id),
                            'order_id': str(order_id),
                        },
                    },
                )

                refund_id = refund_response.get('id')
                refund_status = refund_response.get('status', '').lower()

                if not refund_id:
                    self.message_user(
                        request,
                        f'Return #{return_id}: Razorpay returned no refund ID. '
                        'Check the Razorpay Dashboard before retrying.',
                        level=messages.ERROR,
                    )
                    continue

                with transaction.atomic():

                    item = ReturnRequest.objects.select_for_update().get(
                        pk=return_id
                    )

                    item.razorpay_refund_id = refund_id

                    if refund_status == 'processed':
                        item.status = 'REFUNDED'

                        Payment.objects.filter(
                            pk=payment.pk,
                            status='PAID',
                        ).update(status='REFUNDED')

                    else:
                        # Razorpay may process refunds asynchronously.
                        # Keep the payment marked PAID until processing
                        # is confirmed.
                        item.status = 'REFUND_PROCESSING'

                    item.save(
                        update_fields=[
                            'razorpay_refund_id',
                            'status',
                            'updated_at',
                        ]
                    )

                if refund_status == 'processed':
                    self.message_user(
                        request,
                        f'Return #{return_id}: refund processed successfully. '
                        f'Refund ID: {refund_id}',
                        level=messages.SUCCESS,
                    )
                else:
                    self.message_user(
                        request,
                        f'Return #{return_id}: Razorpay accepted the refund '
                        f'but its status is {refund_status or "unknown"}. '
                        f'Refund ID: {refund_id}. Check the Razorpay Dashboard.',
                        level=messages.WARNING,
                    )

            except Exception as exc:

                # Do not reset the status automatically. A network failure
                # can occur even when Razorpay has created the refund.
                # Check the Razorpay Dashboard before attempting recovery.
                self.message_user(
                    request,
                    f'Return #{return_id}: refund result could not be '
                    f'confirmed ({exc}). The request remains in '
                    'Refund Processing to prevent an accidental duplicate. '
                    'Check Razorpay before retrying.',
                    level=messages.ERROR,
                )