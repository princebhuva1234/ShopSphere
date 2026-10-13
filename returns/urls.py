from django.urls import path

from . import views


urlpatterns = [

    path(
        'request/<int:order_id>/',
        views.request_return,
        name='request_return',
    ),

    path(
        'my-returns/',
        views.my_returns,
        name='my_returns',
    ),

    path(
        'reject/<int:return_id>/',
        views.reject_return_request,
        name='reject_return_request',
    ),

]