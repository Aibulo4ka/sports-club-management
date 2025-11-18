"""
Web URL configuration for accounts app (Django templates)
"""

from django.urls import path
from . import views_web, views_ai

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

    # Trainers
    path('trainers/', views_web.trainers_list, name='trainers_list'),
    path('trainer/dashboard/', views_web.trainer_dashboard, name='trainer_dashboard'),
    path('trainer/class/<int:class_id>/', views_web.trainer_class_detail, name='trainer_class_detail'),

    # AI Trainer
    path('ai-trainer/', views_ai.ai_trainer_home, name='ai_trainer_home'),
    path('ai-trainer/generate-workout/', views_ai.generate_workout, name='generate_workout'),
    path('ai-trainer/generate-nutrition/', views_ai.generate_nutrition, name='generate_nutrition'),
    path('ai-trainer/workout/<int:plan_id>/', views_ai.view_workout_plan, name='view_workout_plan'),
    path('ai-trainer/nutrition/<int:plan_id>/', views_ai.view_nutrition_plan, name='view_nutrition_plan'),
]
