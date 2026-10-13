from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect, get_object_or_404

from .models import User, Address


# =========================================================
# REGISTER
# =========================================================

def register(request):

    if request.method == 'POST':

        username = request.POST.get(
            'username', ''
        ).strip()

        email = request.POST.get(
            'email', ''
        ).strip()

        password = request.POST.get(
            'password', ''
        )

        confirm_password = request.POST.get(
            'confirm_password', ''
        )

        if not username or not email or not password:

            return render(
                request,
                'accounts/register.html',
                {
                    'error': 'Please fill in all required fields.'
                }
            )

        if password != confirm_password:

            return render(
                request,
                'accounts/register.html',
                {
                    'error': 'Passwords do not match.'
                }
            )

        if User.objects.filter(
            username=username
        ).exists():

            return render(
                request,
                'accounts/register.html',
                {
                    'error': 'Username already exists.'
                }
            )

        if User.objects.filter(
            email=email
        ).exists():

            return render(
                request,
                'accounts/register.html',
                {
                    'error': 'Email already exists.'
                }
            )

        # Public registration creates CUSTOMER accounts only.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='CUSTOMER'
        )

        login(request, user)

        messages.success(
            request,
            'Your ShopSphere account was created successfully!'
        )

        return redirect('product_list')

    return render(
        request,
        'accounts/register.html'
    )


# =========================================================
# ROLE-BASED LOGIN
# =========================================================

def user_login(request):

    if request.user.is_authenticated:

        # Already logged-in users go to their own destination.
        role = getattr(request.user, 'role', 'CUSTOMER')

        if role == 'ADMIN' or request.user.is_superuser:

            return redirect('/admin/')

        if role == 'SELLER':

            return redirect('seller_dashboard')

        if role == 'CUSTOMER':

            return redirect('product_list')

    if request.method == 'POST':

        username = request.POST.get(
            'username', ''
        ).strip()

        password = request.POST.get(
            'password', ''
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        # -------------------------------------------------
        # INVALID LOGIN
        # -------------------------------------------------

        if user is None:

            return render(
                request,
                'accounts/login.html',
                {
                    'error': 'Invalid username or password.'
                }
            )

        role = getattr(
            user,
            'role',
            'CUSTOMER'
        )

        # -------------------------------------------------
        # ADMIN LOGIN
        # -------------------------------------------------

        if role == 'ADMIN' or user.is_superuser:

            # Django Admin requires staff/superuser access.
            if not (user.is_staff or user.is_superuser):

                return render(
                    request,
                    'accounts/login.html',
                    {
                        'error': (
                            'This account cannot access the Admin Panel. '
                            'Please contact your administrator.'
                        )
                    }
                )

            login(request, user)

            return redirect('/admin/')

        # -------------------------------------------------
        # SELLER LOGIN
        # -------------------------------------------------

        if role == 'SELLER':

            login(request, user)

            return redirect('seller_dashboard')

        # -------------------------------------------------
        # CUSTOMER LOGIN
        # -------------------------------------------------

        if role == 'CUSTOMER':

            login(request, user)

            return redirect('product_list')

        # -------------------------------------------------
        # UNKNOWN ROLE
        # -------------------------------------------------

        return render(
            request,
            'accounts/login.html',
            {
                'error': 'Your account role is not configured correctly.'
            }
        )

    return render(
        request,
        'accounts/login.html'
    )


# =========================================================
# LOGOUT
# =========================================================

def user_logout(request):

    logout(request)

    return redirect('product_list')


# =========================================================
# MY PROFILE
# =========================================================

@login_required
def profile(request):

    user = request.user

    addresses = Address.objects.filter(
        user=user
    ).order_by(
        '-is_default',
        '-created_at'
    )

    context = {
        'profile_user': user,
        'addresses': addresses,
    }

    return render(
        request,
        'accounts/profile.html',
        context
    )


# =========================================================
# EDIT PROFILE
# =========================================================

@login_required
def edit_profile(request):

    user = request.user

    if request.method == 'POST':

        username = request.POST.get(
            'username', ''
        ).strip()

        first_name = request.POST.get(
            'first_name', ''
        ).strip()

        last_name = request.POST.get(
            'last_name', ''
        ).strip()

        email = request.POST.get(
            'email', ''
        ).strip()

        if not username or not email:

            return render(
                request,
                'accounts/edit_profile.html',
                {
                    'profile_user': user,
                    'error': 'Username and email are required.'
                }
            )

        username_exists = User.objects.filter(
            username=username
        ).exclude(
            id=user.id
        ).exists()

        if username_exists:

            return render(
                request,
                'accounts/edit_profile.html',
                {
                    'profile_user': user,
                    'error': 'This username is already taken.'
                }
            )

        email_exists = User.objects.filter(
            email=email
        ).exclude(
            id=user.id
        ).exists()

        if email_exists:

            return render(
                request,
                'accounts/edit_profile.html',
                {
                    'profile_user': user,
                    'error': 'This email address is already registered.'
                }
            )

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        user.save(
            update_fields=[
                'username',
                'first_name',
                'last_name',
                'email'
            ]
        )

        messages.success(
            request,
            'Your profile was updated successfully!'
        )

        return redirect('profile')

    return render(
        request,
        'accounts/edit_profile.html',
        {
            'profile_user': user,
        }
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@login_required
def change_password(request):

    if request.method == 'POST':

        form = PasswordChangeForm(
            user=request.user,
            data=request.POST
        )

        if form.is_valid():

            user = form.save()

            # Keep the current user logged in.
            update_session_auth_hash(
                request,
                user
            )

            messages.success(
                request,
                'Your password has been changed successfully!'
            )

            return redirect('profile')

    else:

        form = PasswordChangeForm(
            user=request.user
        )

    return render(
        request,
        'accounts/change_password.html',
        {
            'form': form
        }
    )


# =========================================================
# ADDRESS LIST
# =========================================================

@login_required
def address_list(request):

    addresses = Address.objects.filter(
        user=request.user
    ).order_by(
        '-is_default',
        '-created_at'
    )

    return render(
        request,
        'accounts/address_list.html',
        {
            'addresses': addresses
        }
    )


# =========================================================
# ADD ADDRESS
# =========================================================

@login_required
def add_address(request):

    if request.method == 'POST':

        full_name = request.POST.get(
            'full_name', ''
        ).strip()

        phone = request.POST.get(
            'phone', ''
        ).strip()

        address_line = request.POST.get(
            'address_line', ''
        ).strip()

        city = request.POST.get(
            'city', ''
        ).strip()

        state = request.POST.get(
            'state', ''
        ).strip()

        pincode = request.POST.get(
            'pincode', ''
        ).strip()

        is_default = (
            request.POST.get('is_default') == 'on'
        )

        if not all([
            full_name,
            phone,
            address_line,
            city,
            state,
            pincode
        ]):

            messages.error(
                request,
                'Please fill in all address fields.'
            )

            return redirect('add_address')

        if is_default:

            Address.objects.filter(
                user=request.user
            ).update(
                is_default=False
            )

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            address_line=address_line,
            city=city,
            state=state,
            pincode=pincode,
            is_default=is_default
        )

        messages.success(
            request,
            'Delivery address added successfully!'
        )

        return redirect('address_list')

    return render(
        request,
        'accounts/add_address.html'
    )


# =========================================================
# EDIT ADDRESS
# =========================================================

@login_required
def edit_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    if request.method == 'POST':

        full_name = request.POST.get(
            'full_name', ''
        ).strip()

        phone = request.POST.get(
            'phone', ''
        ).strip()

        address_line = request.POST.get(
            'address_line', ''
        ).strip()

        city = request.POST.get(
            'city', ''
        ).strip()

        state = request.POST.get(
            'state', ''
        ).strip()

        pincode = request.POST.get(
            'pincode', ''
        ).strip()

        is_default = (
            request.POST.get('is_default') == 'on'
        )

        if not all([
            full_name,
            phone,
            address_line,
            city,
            state,
            pincode
        ]):

            messages.error(
                request,
                'Please fill in all address fields.'
            )

            return redirect(
                'edit_address',
                address_id=address.id
            )

        if is_default:

            Address.objects.filter(
                user=request.user
            ).exclude(
                id=address.id
            ).update(
                is_default=False
            )

        address.full_name = full_name
        address.phone = phone
        address.address_line = address_line
        address.city = city
        address.state = state
        address.pincode = pincode
        address.is_default = is_default

        address.save()

        messages.success(
            request,
            'Delivery address updated successfully!'
        )

        return redirect('address_list')

    return render(
        request,
        'accounts/edit_address.html',
        {
            'address': address
        }
    )


# =========================================================
# DELETE ADDRESS
# =========================================================

@login_required
def delete_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    if request.method == 'POST':

        address.delete()

        messages.success(
            request,
            'Delivery address deleted successfully!'
        )

    return redirect('address_list')