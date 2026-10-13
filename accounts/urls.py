from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from .views import (
    register,
    user_login,
    user_logout,
    profile,
    edit_profile,
    change_password,
    address_list,
    add_address,
    edit_address,
    delete_address,
)


urlpatterns = [

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    path(
        'register/',
        register,
        name='register'
    ),

    path(
        'login/',
        user_login,
        name='login'
    ),

    path(
        'login/',
        user_login,
        name='user_login'
    ),

    path(
        'logout/',
        user_logout,
        name='logout'
    ),


    # =====================================================
    # CUSTOMER PROFILE
    # =====================================================

    path(
        'profile/',
        profile,
        name='profile'
    ),

    path(
        'profile/edit/',
        edit_profile,
        name='edit_profile'
    ),


    # =====================================================
    # CHANGE PASSWORD
    # =====================================================

    path(
        'password/change/',
        change_password,
        name='change_password'
    ),


    # =====================================================
    # FORGOT PASSWORD
    # =====================================================

    # Step 1: Enter email address
    path(
        'password/reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset'
    ),

    # Step 2: Confirmation that the reset email was requested
    path(
        'password/reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done'
    ),

    # Step 3: Open the reset link and enter a new password
    path(
        'password/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm'
    ),

    # Step 4: Password successfully reset
    path(
        'password/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete'
    ),


    # =====================================================
    # DELIVERY ADDRESSES
    # =====================================================

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