from django.db import models
from accounts.models import User
from products.models import Product


class Cart(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.username}'s Cart"


class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    @property
    def subtotal(self):
        price = self.product.discount_price or self.product.price
        return price * self.quantity

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.product.name} × {self.quantity}"