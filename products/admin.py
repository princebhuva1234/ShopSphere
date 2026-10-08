from django.contrib import admin
from .models import Product, ProductImage


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'seller',
        'brand',
        'price',
        'discount_price',
        'is_active',
        'created_at'
    )

    list_filter = (
        'category',
        'brand',
        'is_active',
        'created_at'
    )

    search_fields = (
        'name',
        'brand',
        'description'
    )

    prepopulated_fields = {
        'slug': ('name',)
    }

    ordering = ('-created_at',)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'is_primary',
        'created_at'
    )

    list_filter = (
        'is_primary',
        'created_at'
    )

    search_fields = (
        'product__name',
    )