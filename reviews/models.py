from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):

    RATING_CHOICES = [
        (1, '⭐ 1 - Poor'),
        (2, '⭐⭐ 2 - Fair'),
        (3, '⭐⭐⭐ 3 - Good'),
        (4, '⭐⭐⭐⭐ 4 - Very Good'),
        (5, '⭐⭐⭐⭐⭐ 5 - Excellent'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_reviews'
    )

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    title = models.CharField(
        max_length=150
    )

    comment = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-created_at']

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product_review'
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.rating}/5 by {self.user}"