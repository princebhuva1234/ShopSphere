from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    F,
    Q,
    When,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from categories.models import Category
from .forms import ProductForm
from .models import Product, ProductImage


# ============================================================
# PRODUCT LIST
# Search, category, price filtering, sorting, and review ratings
# ============================================================

def product_list(request):
    """
    Display active products with search, filters, sorting,
    product images, and customer review ratings.
    """

    # Start with active products.
    products = (
        Product.objects
        .filter(is_active=True)
        .select_related("category", "seller")
        .prefetch_related("images")
    )

    # Calculate the effective selling price.
    # Use discount_price when it is available and greater than zero.
    products = products.annotate(
        effective_price=Case(
            When(
                discount_price__isnull=False,
                discount_price__gt=0,
                then=F("discount_price"),
            ),
            default=F("price"),
            output_field=DecimalField(
                max_digits=12,
                decimal_places=2,
            ),
        )
    )

    # --------------------------------------------------------
    # SEARCH BY PRODUCT NAME OR BRAND
    # --------------------------------------------------------

    search_query = request.GET.get("q", "").strip()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(brand__icontains=search_query)
        )

    # --------------------------------------------------------
    # CATEGORY FILTER
    # --------------------------------------------------------

    category_id = request.GET.get("category", "").strip()

    if category_id:
        try:
            category_id = int(category_id)

            products = products.filter(
                category_id=category_id
            )

        except (TypeError, ValueError):
            category_id = ""

    # --------------------------------------------------------
    # MINIMUM PRICE FILTER
    # --------------------------------------------------------

    min_price_input = request.GET.get("min_price", "").strip()

    if min_price_input:
        try:
            min_price = Decimal(min_price_input)

            if min_price >= 0:
                products = products.filter(
                    effective_price__gte=min_price
                )

        except (InvalidOperation, TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # MAXIMUM PRICE FILTER
    # --------------------------------------------------------

    max_price_input = request.GET.get("max_price", "").strip()

    if max_price_input:
        try:
            max_price = Decimal(max_price_input)

            if max_price >= 0:
                products = products.filter(
                    effective_price__lte=max_price
                )

        except (InvalidOperation, TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # PRODUCT REVIEW RATINGS
    # --------------------------------------------------------
    #
    # Your Review model uses:
    #   related_name="reviews" on the Product foreign key.
    #
    # Therefore:
    #   Avg("reviews__rating") calculates average rating.
    #   Count("reviews", distinct=True) calculates review count.
    #
    # These annotations are available directly in the template.
    # --------------------------------------------------------

    products = products.annotate(
        average_rating_value=Avg("reviews__rating"),
        review_count_value=Count(
            "reviews",
            distinct=True,
        ),
    )

    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    sort_option = request.GET.get("sort", "").strip()

    if sort_option == "price_low":
        products = products.order_by(
            "effective_price",
            "-created_at",
        )

    elif sort_option == "price_high":
        products = products.order_by(
            "-effective_price",
            "-created_at",
        )

    elif sort_option == "name":
        products = products.order_by("name")

    else:
        products = products.order_by("-created_at")

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    categories = Category.objects.all().order_by("name")

    context = {
        "products": products,
        "categories": categories,
    }

    return render(
        request,
        "products/product_list.html",
        context,
    )


# ============================================================
# PRODUCT DETAIL
# ============================================================

def product_detail(request, slug):
    """
    Display an individual active product and its customer reviews.
    """

    product = get_object_or_404(
        Product.objects
        .select_related("category", "seller")
        .prefetch_related(
            "images",
            "reviews__user",
        ),
        slug=slug,
        is_active=True,
    )

    context = {
        "product": product,
    }

    return render(
        request,
        "products/product_detail.html",
        context,
    )


# ============================================================
# SELLER ACCESS CHECK
# ============================================================

def seller_access_allowed(request):
    """
    Return True when the current user has the SELLER role.
    """

    if getattr(request.user, "role", None) != "SELLER":
        messages.error(
            request,
            "Only seller accounts can manage products.",
        )

        return False

    return True


# ============================================================
# GENERATE A UNIQUE PRODUCT SLUG
# ============================================================

def make_unique_slug(name, exclude_id=None):
    """
    Generate a unique URL slug from a product name.
    """

    base_slug = slugify(name) or "product"
    slug = base_slug
    counter = 1

    while True:
        queryset = Product.objects.filter(slug=slug)

        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)

        if not queryset.exists():
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1


# ============================================================
# VALIDATE UPLOADED PRODUCT IMAGES
# ============================================================

def validate_product_images(image_files):
    """
    Validate uploaded files as images.

    Returns a list of error messages. An empty list means that
    all uploaded files passed validation.
    """

    errors = []
    image_field = forms.ImageField()

    for image in image_files:
        try:
            image_field.clean(image)

        except ValidationError as exc:
            errors.extend(exc.messages)

    return errors


# ============================================================
# SAVE PRODUCT IMAGES
# ============================================================

def save_product_images(product, image_files):
    """
    Save uploaded images for a product.

    The first image is marked as the primary image when the
    product does not already have any images.
    """

    for image in image_files:
        is_first_image = not product.images.exists()

        ProductImage.objects.create(
            product=product,
            image=image,
            is_primary=is_first_image,
        )


# ============================================================
# SELLER: ADD PRODUCT
# ============================================================

@login_required
def seller_add_product(request):
    """
    Allow a seller to create a product and upload multiple images.
    """

    if not seller_access_allowed(request):
        return redirect("product_list")

    form = ProductForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and form.is_valid():

        image_files = request.FILES.getlist("images")

        # Validate uploaded images before saving the product.
        image_errors = validate_product_images(image_files)

        if image_errors:
            for error in image_errors:
                messages.error(request, error)

            return render(
                request,
                "products/seller_product_form.html",
                {
                    "form": form,
                    "is_edit": False,
                    "product": None,
                },
            )

        try:
            with transaction.atomic():

                product = form.save(commit=False)

                product.seller = request.user

                product.slug = make_unique_slug(
                    product.name
                )

                product.save()

                save_product_images(
                    product,
                    image_files,
                )

            messages.success(
                request,
                "Product added successfully.",
            )

            return redirect("seller_dashboard")

        except Exception:
            messages.error(
                request,
                "The product could not be saved. "
                "Please check the product details and uploaded images.",
            )

    return render(
        request,
        "products/seller_product_form.html",
        {
            "form": form,
            "is_edit": False,
            "product": None,
        },
    )


# ============================================================
# SELLER: EDIT PRODUCT
# ============================================================

@login_required
def seller_edit_product(request, product_id):
    """
    Allow a seller to edit their own product and add more images.
    """

    if not seller_access_allowed(request):
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        pk=product_id,
        seller=request.user,
    )

    original_name = product.name

    if request.method == "POST":

        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product,
        )

        if form.is_valid():

            image_files = request.FILES.getlist("images")

            image_errors = validate_product_images(
                image_files
            )

            if image_errors:
                for error in image_errors:
                    messages.error(request, error)

                return render(
                    request,
                    "products/seller_product_form.html",
                    {
                        "form": form,
                        "is_edit": True,
                        "product": product,
                    },
                )

            try:
                with transaction.atomic():

                    updated_product = form.save(
                        commit=False
                    )

                    updated_product.seller = request.user

                    # Regenerate the slug when the product name changes.
                    if (
                        updated_product.name != original_name
                    ):
                        updated_product.slug = make_unique_slug(
                            updated_product.name,
                            exclude_id=updated_product.pk,
                        )

                    updated_product.save()

                    # New uploads are added without deleting old images.
                    save_product_images(
                        updated_product,
                        image_files,
                    )

                messages.success(
                    request,
                    "Product updated successfully.",
                )

                return redirect("seller_dashboard")

            except Exception:
                messages.error(
                    request,
                    "The product could not be updated. "
                    "Please check the form and uploaded images.",
                )

    else:

        form = ProductForm(
            instance=product
        )

    return render(
        request,
        "products/seller_product_form.html",
        {
            "form": form,
            "is_edit": True,
            "product": product,
        },
    )


# ============================================================
# SELLER: ACTIVATE OR DEACTIVATE PRODUCT
# ============================================================

@login_required
@require_POST
def seller_toggle_product(request, product_id):
    """
    Allow a seller to activate or deactivate their own product.
    """

    if not seller_access_allowed(request):
        return redirect("product_list")

    product = get_object_or_404(
        Product,
        pk=product_id,
        seller=request.user,
    )

    product.is_active = not product.is_active
    product.save()

    if product.is_active:
        messages.success(
            request,
            f'"{product.name}" is now active.',
        )

    else:
        messages.success(
            request,
            f'"{product.name}" has been deactivated.',
        )

    return redirect("seller_dashboard")