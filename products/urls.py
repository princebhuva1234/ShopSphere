from django.urls import path

from .views import (
    product_list,
    product_detail,
    seller_add_product,
    seller_edit_product,
    seller_toggle_product,
)


urlpatterns = [

    # =====================================================
    # CUSTOMER STORE
    # =====================================================

    path(
        '',
        product_list,
        name='product_list'
    ),

    path(
        'products/<slug:slug>/',
        product_detail,
        name='product_detail'
    ),


    # =====================================================
    # SELLER PRODUCT MANAGEMENT
    # =====================================================

    path(
        'seller/products/add/',
        seller_add_product,
        name='seller_add_product'
    ),

    path(
        'seller/products/<int:product_id>/edit/',
        seller_edit_product,
        name='seller_edit_product'
    ),

    path(
        'seller/products/<int:product_id>/toggle/',
        seller_toggle_product,
        name='seller_toggle_product'
    ),

]