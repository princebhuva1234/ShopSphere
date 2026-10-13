from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Coupon(models.Model):

    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Example: WELCOME10"
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPES,
        default='PERCENTAGE'
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    maximum_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount for percentage coupons."
    )

    start_date = models.DateTimeField(
        default=timezone.now
    )

    expiry_date = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Leave empty for unlimited uses."
    )

    used_count = models.PositiveIntegerField(
        default=0,
        editable=False
    )

    one_use_per_customer = models.BooleanField(
        default=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        now = timezone.now()

        if not self.is_active:
            return False

        if now < self.start_date:
            return False

        if now > self.expiry_date:
            return False

        if (
            self.usage_limit is not None
            and self.used_count >= self.usage_limit
        ):
            return False

        return True

    def calculate_discount(self, subtotal):
        """
        Calculate the discount for an order subtotal.
        Returns a Decimal amount.
        """

        subtotal = Decimal(str(subtotal))

        if not self.is_valid:
            return Decimal('0.00')

        if subtotal < self.minimum_order_amount:
            return Decimal('0.00')

        if self.discount_type == 'PERCENTAGE':
            discount = (
                subtotal
                * self.discount_value
                / Decimal('100')
            )

            if self.maximum_discount is not None:
                discount = min(
                    discount,
                    self.maximum_discount
                )

        else:
            discount = self.discount_value

        discount = min(discount, subtotal)

        return max(
            Decimal('0.00'),
            discount.quantize(Decimal('0.01'))
        )


class CouponRedemption(models.Model):
    """
    Records a coupon that was successfully redeemed
    for an order after payment verification.
    """

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.PROTECT,
        related_name='redemptions'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='coupon_redemptions'
    )

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='coupon_redemption'
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    redeemed_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-redeemed_at']
        verbose_name = 'Coupon Redemption'
        verbose_name_plural = 'Coupon Redemptions'

    def __str__(self):
        return (
            f"{self.coupon.code} - "
            f"Order #{self.order_id}"
        )