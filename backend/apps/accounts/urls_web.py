"""
Web URL configuration for accounts app (Django templates)
"""

from django.urls import path
from . import views_web

app_name = 'accounts_web'

urlpatterns = [
    # Home page
    path('', views_web.home, name='home'),

    # Authentication pages
    path('login/', views_web.login_view, name='login'),
    path('register/', views_web.register_view, name='register'),
    path('logout/', views_web.logout_view, name='logout'),

    # Profile pages
    path('profile/', views_web.profile_view, name='profile'),
    path('profile/edit/', views_web.edit_profile_view, name='edit_profile'),
]
