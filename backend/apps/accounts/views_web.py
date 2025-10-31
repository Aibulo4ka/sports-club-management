"""
Web views for accounts app (Django templates)
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def home(request):
    """
    Home page / Landing page
    """
    return render(request, 'home.html')


def login_view(request):
    """
    Login page
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Вы успешно вошли в систему')
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')

    return render(request, 'accounts/login.html')


def register_view(request):
    """
    Registration page
    """
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone')

        # Basic validation
        if not all([username, email, password, password2, phone]):
            messages.error(request, 'Пожалуйста, заполните все обязательные поля')
            return render(request, 'accounts/register.html')

        if password != password2:
            messages.error(request, 'Пароли не совпадают')
            return render(request, 'accounts/register.html')

        # Check if username already exists
        from django.contrib.auth.models import User
        from .models import Profile, Client, UserRole

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            return render(request, 'accounts/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return render(request, 'accounts/register.html')

        if Profile.objects.filter(phone=phone).exists():
            messages.error(request, 'Пользователь с таким телефоном уже существует')
            return render(request, 'accounts/register.html')

        try:
            from django.db import transaction

            # Create user, profile and client in transaction
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )

                # Create profile
                profile = Profile.objects.create(
                    user=user,
                    phone=phone,
                    role=UserRole.CLIENT
                )

                # Create client
                Client.objects.create(profile=profile)

            # Log the user in
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.get_full_name() or user.username}! Ваш аккаунт успешно создан.')
            return redirect('accounts_web:profile')

        except Exception as e:
            messages.error(request, f'Ошибка при регистрации: {str(e)}')
            return render(request, 'accounts/register.html')

    return render(request, 'accounts/register.html')


def logout_view(request):
    """
    Logout user
    """
    logout(request)
    messages.success(request, 'Вы вышли из системы')
    return redirect('accounts_web:home')


@login_required
def profile_view(request):
    """
    User profile page
    """
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'profile': request.user.profile
    })
