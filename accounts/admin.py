from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Address


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ('ShopSphere Information', {
            'fields': ('role',),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('ShopSphere Information', {
            'fields': ('email', 'role'),
        }),
    )

    list_display = (
        'username',
        'email',
        'role',
        'is_staff',
        'is_active',
    )

    list_filter = (
        'role',
        'is_staff',
        'is_active',
    )

    search_fields = (
        'username',
        'email',
    )

    @admin.register(Address)
    class AddressAdmin(admin.ModelAdmin):
        list_display = (
        'full_name',
        'user',
        'phone',
        'city',
        'state',
        'pincode',
        'is_default',
    )

        list_filter = (
        'state',
        'city',
        'is_default',
    )

        search_fields = (
        'full_name',
        'user__username',
        'user__email',
        'phone',
        'city',
        'pincode',
    )