from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = (
        ('CUSTOMER', 'Customer'),
        ('SELLER', 'Seller'),
        ('ADMIN', 'Admin'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CUSTOMER'
    )

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username


class Address(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses'
    )

    full_name = models.CharField(max_length=150)

    phone = models.CharField(max_length=15)

    address_line = models.CharField(max_length=255)

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    pincode = models.CharField(max_length=10)

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} - {self.city}"