from django.contrib import admin

from .models import Order, OrderAddress, OrderItem


# =========================================================
# ORDER ITEM INLINE
# =========================================================

class OrderItemInline(admin.TabularInline):

    model = OrderItem

    extra = 0

    fields = (
        'product',
        'quantity',
        'price',
        'subtotal',
    )

    readonly_fields = (
        'subtotal',
    )


# =========================================================
# ORDER ADDRESS INLINE
# =========================================================

class OrderAddressInline(admin.StackedInline):

    model = OrderAddress

    extra = 0

    fields = (
        'full_name',
        'phone',
        'address_line',
        'city',
        'state',
        'pincode',
    )


# =========================================================
# ORDER ADMIN
# =========================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'total_amount',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__email',
    )

    ordering = (
        '-created_at',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    inlines = [
        OrderItemInline,
        OrderAddressInline,
    ]