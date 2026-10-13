from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from orders.models import Order
from payments.models import Payment

from .models import ReturnRequest


@login_required
def request_return(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if request.method == 'POST':

        reason = request.POST.get('reason', '').strip()
        description = request.POST.get('description', '').strip()

        valid_reasons = dict(
            ReturnRequest.REASON_CHOICES
        )

        if order.status != 'DELIVERED':
            messages.error(
                request,
                'Only delivered orders are eligible for a return request.'
            )

        elif reason not in valid_reasons:
            messages.error(
                request,
                'Please select a valid return reason.'
            )

        elif ReturnRequest.objects.filter(
            order=order,
            customer=request.user,
            status__in=[
                'PENDING',
                'APPROVED',
                'REFUND_PROCESSING',
                'REFUNDED',
            ]
        ).exists():
            messages.error(
                request,
                'A return request already exists for this order.'
            )

        else:

            payment = Payment.objects.filter(
                order=order,
                status='PAID'
            ).first()

            if not payment:
                messages.error(
                    request,
                    'A successful payment was not found for this order.'
                )

            else:

                ReturnRequest.objects.create(
                    order=order,
                    customer=request.user,
                    payment=payment,
                    reason=reason,
                    description=description,
                    refund_amount=Decimal('0.00'),
                    status='PENDING',
                )

                messages.success(
                    request,
                    'Your return request has been submitted successfully.'
                )

                return redirect('my_returns')

    return render(
        request,
        'returns/request_return.html',
        {
            'order': order,
            'return_reasons': ReturnRequest.REASON_CHOICES,
        }
    )


@login_required
def my_returns(request):

    return_requests = (
        ReturnRequest.objects
        .filter(customer=request.user)
        .select_related('order', 'payment')
        .order_by('-created_at')
    )

    return render(
        request,
        'returns/my_returns.html',
        {
            'return_requests': return_requests,
        }
    )


@require_POST
@login_required
def reject_return_request(request, return_id):

    if not request.user.is_staff:
        messages.error(
            request,
            'You do not have permission to perform this action.'
        )
        return redirect('my_returns')

    with transaction.atomic():

        return_request = get_object_or_404(
            ReturnRequest.objects.select_for_update(),
            id=return_id
        )

        if return_request.status != 'PENDING':

            messages.error(
                request,
                'Only pending return requests can be rejected.'
            )

        else:

            return_request.status = 'REJECTED'
            return_request.admin_note = (
                request.POST.get('admin_note', '').strip()
            )

            return_request.save(
                update_fields=[
                    'status',
                    'admin_note',
                    'updated_at',
                ]
            )

            messages.success(
                request,
                'The return request was rejected.'
            )

    return redirect('admin:returns_returnrequest_changelist')