from django.urls import path
from .views import (
    register,
    user_login,
    user_logout,
    address_list,
    add_address,
    edit_address,
    delete_address,
)

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),

    path(
        'addresses/',
        address_list,
        name='address_list'
    ),

    path(
        'addresses/add/',
        add_address,
        name='add_address'
    ),

    path(
        'addresses/edit/<int:address_id>/',
        edit_address,
        name='edit_address'
    ),

    path(
        'addresses/delete/<int:address_id>/',
        delete_address,
        name='delete_address'
    ),
]