from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    slug = models.SlugField(max_length=120, unique=True)

    description = models.TextField(blank=True)

    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name