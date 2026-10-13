from django.db import models
from django.conf import settings
from orders.models import Order
from payments.models import Payment


class ReturnRequest(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REFUND_PROCESSING', 'Refund Processing'),
        ('REFUNDED', 'Refunded'),
    ]

    REASON_CHOICES = [
        ('DAMAGED', 'Product arrived damaged'),
        ('DEFECTIVE', 'Product is defective'),
        ('WRONG_ITEM', 'Wrong product received'),
        ('NOT_AS_DESCRIBED', 'Product not as described'),
        ('SIZE_ISSUE', 'Size or fit issue'),
        ('OTHER', 'Other'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='return_requests'
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='return_requests'
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='return_requests',
        null=True,
        blank=True
    )

    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES
    )

    description = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    razorpay_refund_id = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    admin_note = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Return Request'
        verbose_name_plural = 'Return Requests'

    def __str__(self):
        return (
            f'Return #{self.pk} - '
            f'Order #{self.order_id} - '
            f'{self.get_status_display()}'
        )