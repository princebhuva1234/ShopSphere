from django.urls import path
from . import views


urlpatterns = [
    path(
        'products/<slug:product_slug>/add/',
        views.add_review,
        name='add_review'
    ),

    path(
        '<int:review_id>/edit/',
        views.edit_review,
        name='edit_review'
    ),

    path(
        '<int:review_id>/delete/',
        views.delete_review,
        name='delete_review'
    ),
]