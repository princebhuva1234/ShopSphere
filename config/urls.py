from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from dashboard import views as dashboard_views


urlpatterns = [

    # =====================================================
    # SHOPSPHERE SALES DASHBOARD INSIDE DJANGO ADMIN
    # IMPORTANT: Keep this ABOVE admin.site.urls
    # =====================================================

    path(
        'admin/sales-dashboard/',
        admin.site.admin_view(
            dashboard_views.admin_dashboard
        ),
        name='admin_sales_dashboard',
    ),

    # =====================================================
    # DJANGO ADMIN PANEL
    # =====================================================

    path(
        'admin/',
        admin.site.urls,
    ),

    # =====================================================
    # PRODUCTS
    # =====================================================

    path(
        '',
        include('products.urls'),
    ),

    # =====================================================
    # SHOPPING CART
    # =====================================================

    path(
        'cart/',
        include('cart.urls'),
    ),

    # =====================================================
    # ORDERS, PAYMENTS, COUPONS, AND INVOICES
    # =====================================================

    path(
        'orders/',
        include('orders.urls'),
    ),

    # =====================================================
    # ACCOUNTS
    # =====================================================

    path(
        'accounts/',
        include('accounts.urls'),
    ),

    # =====================================================
    # RAZORPAY WEBHOOKS
    # =====================================================

    path(
        'payments/',
        include('payments.urls'),
    ),

    # =====================================================
    # WISHLIST
    # =====================================================

    path(
        'wishlist/',
        include('wishlist.urls'),
    ),

    # =====================================================
    # PRODUCT REVIEWS
    # =====================================================

    path(
        'reviews/',
        include('reviews.urls'),
    ),

    # =====================================================
    # PRODUCT RETURNS
    # =====================================================

    path(
        'returns/',
        include('returns.urls'),
    ),

]


# =========================================================
# MEDIA FILES DURING DEVELOPMENT
# =========================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )