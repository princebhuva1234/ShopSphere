from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from products.models import Product
from orders.models import OrderItem

from .models import Review
from .forms import ReviewForm


@login_required
def add_review(request, product_slug):
    """
    Allow an eligible customer to review a delivered product.
    """

    # Find the product.
    product = get_object_or_404(
        Product,
        slug=product_slug,
        is_active=True
    )

    # Only customers can submit reviews.
    if getattr(request.user, 'role', None) != 'CUSTOMER':
        messages.error(
            request,
            'Only customer accounts can submit product reviews.'
        )

        return redirect(
            'product_detail',
            slug=product.slug
        )

    # Check whether the customer has already reviewed this product.
    existing_review = Review.objects.filter(
        user=request.user,
        product=product
    ).exists()

    if existing_review:
        messages.warning(
            request,
            'You have already reviewed this product.'
        )

        return redirect(
            'product_detail',
            slug=product.slug
        )

    # Check whether the customer has received the product.
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__status='DELIVERED'
    ).exists()

    if not has_purchased:
        messages.error(
            request,
            'You can review this product after your order is delivered.'
        )

        return redirect(
            'product_detail',
            slug=product.slug
        )

    # Process the review form.
    if request.method == 'POST':

        form = ReviewForm(request.POST)

        if form.is_valid():

            review = form.save(commit=False)

            # Assign the customer and product on the server.
            review.user = request.user
            review.product = product

            review.save()

            messages.success(
                request,
                'Thank you! Your product review was submitted successfully.'
            )

            return redirect(
                'product_detail',
                slug=product.slug
            )

    else:
        form = ReviewForm()

    context = {
        'product': product,
        'form': form,
    }

    return render(
        request,
        'reviews/add_review.html',
        context
    )


from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import Review
from .forms import ReviewForm


@login_required
def edit_review(request, review_id):
    """
    Allow a customer to edit their own review.
    """

    review = get_object_or_404(
        Review,
        id=review_id,
        user=request.user
    )

    if request.method == 'POST':
        form = ReviewForm(
            request.POST,
            instance=review
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Your review has been updated successfully.'
            )

            return redirect(
                'product_detail',
                slug=review.product.slug
            )

    else:
        form = ReviewForm(instance=review)

    return render(
        request,
        'reviews/edit_review.html',
        {
            'form': form,
            'review': review,
            'product': review.product,
        }
    )


@login_required
@require_POST
def delete_review(request, review_id):
    """
    Allow a customer to delete their own review.
    """

    review = get_object_or_404(
        Review,
        id=review_id,
        user=request.user
    )

    product_slug = review.product.slug

    review.delete()

    messages.success(
        request,
        'Your review has been deleted successfully.'
    )

    return redirect(
        'product_detail',
        slug=product_slug
    )