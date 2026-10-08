from django.shortcuts import render, get_object_or_404
from .models import Product


def product_list(request):
    products = Product.objects.filter(is_active=True)

    context = {
        'products': products
    }

    return render(request, 'products/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True
    )

    context = {
        'product': product
    }

    return render(
        request,
        'products/product_detail.html',
        context
    )