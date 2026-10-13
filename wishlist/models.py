from django.conf import settings
from django.db import models

from products.models import Product


# =========================================================
# WISHLIST
# =========================================================

class Wishlist(models.Model):

    # Each user has one wishlist.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f"{self.user.username}'s Wishlist"


# =========================================================
# WISHLIST ITEMS
# =========================================================

class WishlistItem(models.Model):

    # The wishlist containing this product.
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # The saved product.
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )

    added_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ['-added_at']

        # Prevent the same product appearing twice
        # in the same user's wishlist.
        constraints = [
            models.UniqueConstraint(
                fields=['wishlist', 'product'],
                name='unique_wishlist_product'
            )
        ]

        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'

    def __str__(self):
        return (
            f"{self.product.name} "
            f"in {self.wishlist.user.username}'s Wishlist"
        )