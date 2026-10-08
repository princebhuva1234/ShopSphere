from django.db import models

from orders.models import Order


class Payment(models.Model):

    # =====================================================
    # PAYMENT METHOD
    # =====================================================

    # Razorpay is the only payment option shown by ShopSphere.
    # Razorpay Checkout will provide the actual supported
    # payment instruments such as UPI, cards, EMI, wallets,
    # Net Banking, Pay Later, etc.
    PAYMENT_METHOD_CHOICES = (
        ('RAZORPAY', 'Razorpay'),
    )

    # =====================================================
    # PAYMENT STATUS
    # =====================================================

    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )

    # =====================================================
    # PAYMENT PROVIDER
    # =====================================================

    PROVIDER_CHOICES = (
        ('RAZORPAY', 'Razorpay'),
        ('INTERNAL', 'Internal'),
    )

    # =====================================================
    # ORDER
    # =====================================================

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment'
    )

    checkout_token = models.CharField(
    max_length=64,
    blank=True,
    null=True,
    unique=True
)

    # =====================================================
    # AMOUNT
    # =====================================================

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default='INR'
    )

    # =====================================================
    # PAYMENT METHOD
    # =====================================================

    method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )

    # =====================================================
    # PAYMENT STATUS
    # =====================================================

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )

    # =====================================================
    # PAYMENT PROVIDER
    # =====================================================

    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='RAZORPAY'
    )

    # =====================================================
    # RAZORPAY DETAILS
    # =====================================================

    provider_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    provider_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    provider_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # =====================================================
    # ACTUAL GATEWAY PAYMENT METHOD
    # =====================================================
    # Examples returned by Razorpay can include:
    # upi
    # card
    # netbanking
    # wallet
    # emi
    # etc.

    gateway_method = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # STRING REPRESENTATION
    # =====================================================

    def __str__(self):
        return (
            f"Payment #{self.id} - "
            f"Order #{self.order.id}"
        )