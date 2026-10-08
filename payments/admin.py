from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'order',
        'amount',
        'currency',
        'method',
        'status',
        'provider',
        'gateway_method',
        'created_at',
    )

    list_filter = (
        'method',
        'status',
        'provider',
        'gateway_method',
        'created_at',
    )

    search_fields = (
        'order__id',
        'order__user__username',
        'order__user__email',
        'provider_order_id',
        'provider_payment_id',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    ordering = (
        '-created_at',
    )