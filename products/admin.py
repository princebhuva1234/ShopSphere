from django.contrib import admin
from .models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'category',
        'seller',
        'price',
        'discount_price',
        'stock_quantity',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
        'category',
        'seller',
    )

    search_fields = (
        'name',
        'brand',
        'slug',
    )

    prepopulated_fields = {
        'slug': ('name',)
    }

    inlines = [
        ProductImageInline
    ]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):

    list_display = (
        'product',
        'is_primary',
        'created_at',
    )

    list_filter = (
        'is_primary',
    )