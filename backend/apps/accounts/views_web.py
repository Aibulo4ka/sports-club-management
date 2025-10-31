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
        # TODO: Implement registration logic
        messages.info(request, 'Регистрация временно недоступна')

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
