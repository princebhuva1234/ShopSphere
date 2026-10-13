from django.contrib import admin
from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):

    list_display = (
        'code',
        'discount_type',
        'discount_value',
        'minimum_order_amount',
        'used_count',
        'usage_limit',
        'start_date',
        'expiry_date',
        'is_active',
    )

    list_filter = (
        'discount_type',
        'is_active',
        'one_use_per_customer',
    )

    search_fields = (
        'code',
        'description',
    )

    readonly_fields = (
        'used_count',
        'created_at',
        'updated_at',
    )

    ordering = ('-created_at',)

    fieldsets = (
        ('Coupon Information', {
            'fields': (
                'code',
                'description',
                'is_active',
            )
        }),

        ('Discount Configuration', {
            'fields': (
                'discount_type',
                'discount_value',
                'minimum_order_amount',
                'maximum_discount',
            )
        }),

        ('Validity', {
            'fields': (
                'start_date',
                'expiry_date',
            )
        }),

        ('Usage Restrictions', {
            'fields': (
                'usage_limit',
                'used_count',
                'one_use_per_customer',
            )
        }),

        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )