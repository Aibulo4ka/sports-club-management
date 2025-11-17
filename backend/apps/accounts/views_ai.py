"""
Django views для AI Персонального тренера
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime

from apps.core.ai_fitness_agent import generate_workout_plan, generate_nutrition_plan
from .models_ai import WorkoutPlan, NutritionPlan, FitnessGoal, FitnessLevel
from .models import Client


@login_required
def ai_trainer_home(request):
    """
    Главная страница AI тренера
    """
    try:
        client = Client.objects.get(profile__user=request.user)
    except Client.DoesNotExist:
        messages.error(request, 'Только клиенты могут использовать AI тренера')
        return redirect('accounts_web:home')

    # Получаем последние планы
    latest_workout = client.workout_plans.filter(is_active=True).first()
    latest_nutrition = client.nutrition_plans.filter(is_active=True).first()

    # Получаем историю планов
    workout_history = client.workout_plans.all()[:5]
    nutrition_history = client.nutrition_plans.all()[:5]

    context = {
        'client': client,
        'latest_workout': latest_workout,
        'latest_nutrition': latest_nutrition,
        'workout_history': workout_history,
        'nutrition_history': nutrition_history,
        'fitness_goals': FitnessGoal.choices,
        'fitness_levels': FitnessLevel.choices,
    }

    return render(request, 'accounts/ai_trainer_home.html', context)


@login_required
def generate_workout(request):
    """
    Генерация программы тренировок
    """
    try:
        client = Client.objects.get(profile__user=request.user)
    except Client.DoesNotExist:
        messages.error(request, 'Только клиенты могут использовать AI тренера')
        return redirect('accounts_web:home')

    if request.method == 'POST':
        goal = request.POST.get('goal', FitnessGoal.GENERAL_FITNESS)
        fitness_level = request.POST.get('fitness_level', FitnessLevel.BEGINNER)
        additional_info = request.POST.get('additional_info', '')

        # Получаем данные клиента
        age = (timezone.now().date() - client.profile.date_of_birth).days // 365 if client.profile.date_of_birth else 25

        # Получаем активный абонемент (правильный related_name - 'memberships')
        active_membership = client.memberships.filter(status='ACTIVE').first()
        membership_type = active_membership.membership_type.name if active_membership else 'Базовый'

        client_data = {
            'age': age,
            'sex': 'не указан',
            'fitness_level': dict(FitnessLevel.choices).get(fitness_level, 'Начальный'),
            'goal': dict(FitnessGoal.choices).get(goal, 'Общая физическая подготовка'),
            'membership_type': membership_type,
            'additional_info': additional_info,
        }

        # Генерируем программу
        try:
            workout_content = generate_workout_plan(client_data)

            # Деактивируем старые планы
            client.workout_plans.update(is_active=False)

            # Создаём новый план
            workout_plan = WorkoutPlan.objects.create(
                client=client,
                goal=goal,
                fitness_level=fitness_level,
                additional_info=additional_info,
                workout_content=workout_content,
                is_active=True
            )

            messages.success(request, 'Программа тренировок успешно сгенерирована!')
            return redirect('accounts_web:ai_trainer_home')

        except Exception as e:
            messages.error(request, f'Ошибка при генерации программы: {str(e)}')
            return redirect('accounts_web:ai_trainer_home')

    return redirect('accounts_web:ai_trainer_home')


@login_required
def generate_nutrition(request):
    """
    Генерация плана питания
    """
    try:
        client = Client.objects.get(profile__user=request.user)
    except Client.DoesNotExist:
        messages.error(request, 'Только клиенты могут использовать AI тренера')
        return redirect('accounts_web:home')

    if request.method == 'POST':
        goal = request.POST.get('goal', FitnessGoal.GENERAL_FITNESS)
        dietary_preferences = request.POST.get('dietary_preferences', '')

        # Получаем данные клиента
        age = (timezone.now().date() - client.profile.date_of_birth).days // 365 if client.profile.date_of_birth else 25

        client_data = {
            'age': age,
            'sex': 'не указан',
            'goal': dict(FitnessGoal.choices).get(goal, 'Поддержание формы'),
            'activity_level': 'средний',
            'dietary_preferences': dietary_preferences,
        }

        # Генерируем план питания
        try:
            nutrition_content = generate_nutrition_plan(client_data)

            # Деактивируем старые планы
            client.nutrition_plans.update(is_active=False)

            # Создаём новый план
            nutrition_plan = NutritionPlan.objects.create(
                client=client,
                goal=goal,
                dietary_preferences=dietary_preferences,
                nutrition_content=nutrition_content,
                is_active=True
            )

            messages.success(request, 'План питания успешно сгенерирован!')
            return redirect('accounts_web:ai_trainer_home')

        except Exception as e:
            messages.error(request, f'Ошибка при генерации плана питания: {str(e)}')
            return redirect('accounts_web:ai_trainer_home')

    return redirect('accounts_web:ai_trainer_home')


@login_required
def view_workout_plan(request, plan_id):
    """
    Просмотр программы тренировок
    """
    try:
        client = Client.objects.get(profile__user=request.user)
        workout_plan = get_object_or_404(WorkoutPlan, id=plan_id, client=client)
    except Client.DoesNotExist:
        messages.error(request, 'Доступ запрещён')
        return redirect('accounts_web:home')

    context = {
        'workout_plan': workout_plan,
        'client': client,
    }

    return render(request, 'accounts/view_workout_plan.html', context)


@login_required
def view_nutrition_plan(request, plan_id):
    """
    Просмотр плана питания
    """
    try:
        client = Client.objects.get(profile__user=request.user)
        nutrition_plan = get_object_or_404(NutritionPlan, id=plan_id, client=client)
    except Client.DoesNotExist:
        messages.error(request, 'Доступ запрещён')
        return redirect('accounts_web:home')

    context = {
        'nutrition_plan': nutrition_plan,
        'client': client,
    }

    return render(request, 'accounts/view_nutrition_plan.html', context)
