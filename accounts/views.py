from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import User, Address

def register(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(
                request,
                'accounts/register.html',
                {'error': 'Passwords do not match.'}
            )

        if User.objects.filter(username=username).exists():
            return render(
                request,
                'accounts/register.html',
                {'error': 'Username already exists.'}
            )

        if User.objects.filter(email=email).exists():
            return render(
                request,
                'accounts/register.html',
                {'error': 'Email already exists.'}
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='CUSTOMER'
        )

        login(request, user)

        return redirect('product_list')

    return render(request, 'accounts/register.html')

def user_login(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect('product_list')

        else:

            return render(
                request,
                'accounts/login.html',
                {'error': 'Invalid username or password.'}
            )

    return render(request, 'accounts/login.html')

def user_logout(request):

    logout(request)

    return redirect('product_list')

@login_required
def address_list(request):
    addresses = Address.objects.filter(
        user=request.user
    ).order_by('-is_default', '-created_at')

    return render(
        request,
        'accounts/address_list.html',
        {'addresses': addresses}
    )

@login_required
def add_address(request):

    if request.method == 'POST':

        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        address_line = request.POST.get('address_line')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        is_default = request.POST.get('is_default') == 'on'

        if is_default:
            Address.objects.filter(
                user=request.user
            ).update(is_default=False)

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

        return redirect('address_list')

    return render(
        request,
        'accounts/add_address.html'
    )

@login_required
def edit_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    if request.method == 'POST':

        address.full_name = request.POST.get('full_name')
        address.phone = request.POST.get('phone')
        address.address_line = request.POST.get('address_line')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.pincode = request.POST.get('pincode')

        is_default = request.POST.get('is_default') == 'on'

        if is_default:
            Address.objects.filter(
                user=request.user
            ).exclude(
                id=address.id
            ).update(is_default=False)

        address.is_default = is_default
        address.save()

        return redirect('address_list')

    return render(
        request,
        'accounts/edit_address.html',
        {'address': address}
    )

@login_required
def delete_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    if request.method == 'POST':
        address.delete()

    return redirect('address_list')

    