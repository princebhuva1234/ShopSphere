from django.db import models
from categories.models import Category
from accounts.models import User


class Product(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )

    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='products',
        limit_choices_to={'role': 'SELLER'}
    )

    name = models.CharField(max_length=200)

    slug = models.SlugField(
        max_length=220,
        unique=True
    )

    description = models.TextField()

    brand = models.CharField(
        max_length=100,
        blank=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


# ADD ProductImage HERE
class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(
        upload_to='products/'
    )

    is_primary = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"{self.product.name} Image"