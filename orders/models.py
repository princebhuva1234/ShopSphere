from django.db import models

from accounts.models import User
from products.models import Product


class Order(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    # Final amount the customer must pay.
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Total before applying a coupon.
    subtotal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Amount deducted by the coupon.
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Coupon used for this order.
    coupon = models.ForeignKey(
        'coupons.Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    # Preserve the code even if the coupon relationship is removed.
    coupon_code = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    @property
    def calculated_subtotal(self):
        """
        Calculate the subtotal from the order items.
        Useful for displaying historical orders created
        before subtotal_amount was introduced.
        """
        return sum(
            (item.subtotal for item in self.items.all()),
            start=0
        )


class OrderAddress(models.Model):

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='shipping_address'
    )

    full_name = models.CharField(
        max_length=150
    )

    phone = models.CharField(
        max_length=15
    )

    address_line = models.CharField(
        max_length=255
    )

    city = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100
    )

    pincode = models.CharField(
        max_length=10
    )

    def __str__(self):
        return f"Shipping Address for Order #{self.order.id}"


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    @property
    def subtotal(self):
        return (self.price or 0) * self.quantity