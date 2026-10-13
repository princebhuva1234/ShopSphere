
# Register your models here.
from django.contrib import admin

from .models import Wishlist, WishlistItem


# =========================================================
# WISHLIST ITEM INLINE
# =========================================================

class WishlistItemInline(admin.TabularInline):

    model = WishlistItem

    extra = 0

    autocomplete_fields = ['product']

    readonly_fields = [
        'added_at'
    ]


# =========================================================
# WISHLIST ADMIN
# =========================================================

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'user__username',
        'user__email',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    inlines = [
        WishlistItemInline
    ]


# =========================================================
# WISHLIST ITEM ADMIN
# =========================================================

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'wishlist',
        'product',
        'added_at',
    )

    list_filter = (
        'added_at',
    )

    search_fields = (
        'wishlist__user__username',
        'product__name',
    )

    readonly_fields = (
        'added_at',
    )

    autocomplete_fields = [
        'wishlist',
        'product',
    ]