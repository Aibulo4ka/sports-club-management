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
        avatar = request.POST.get('avatar', 'avatar1.png')

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
                    role=UserRole.CLIENT,
                    avatar=avatar
                )

                # Create client
                Client.objects.create(profile=profile)

            # Send welcome email асинхронно
            from .tasks import send_welcome_email
            send_welcome_email.delay(user.id)

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


@login_required
def edit_profile_view(request):
    """
    Редактирование профиля пользователя
    """
    profile = request.user.profile

    if request.method == 'POST':
        # Получаем данные из формы
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        date_of_birth = request.POST.get('date_of_birth', '')
        address = request.POST.get('address', '')
        avatar = request.POST.get('avatar', profile.avatar)

        # Валидация email на уникальность (если изменился)
        from django.contrib.auth.models import User
        if email != request.user.email:
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.error(request, 'Пользователь с таким email уже существует')
                return render(request, 'accounts/edit_profile.html', {
                    'user': request.user,
                    'profile': profile
                })

        try:
            from django.db import transaction

            with transaction.atomic():
                # Обновляем данные пользователя
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.save()

                # Обновляем профиль
                profile.phone = phone
                profile.address = address
                profile.avatar = avatar

                # Обновляем дату рождения (если указана)
                if date_of_birth:
                    from datetime import datetime
                    try:
                        profile.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                    except ValueError:
                        pass  # Игнорируем неправильный формат

                profile.save()

            messages.success(request, 'Профиль успешно обновлён!')
            return redirect('accounts_web:profile')

        except Exception as e:
            messages.error(request, f'Ошибка при обновлении профиля: {str(e)}')

    return render(request, 'accounts/edit_profile.html', {
        'user': request.user,
        'profile': profile
    })


def trainers_list(request):
    """
    Страница со списком тренеров
    """
    from .models import Trainer

    # Получаем всех активных тренеров
    trainers = Trainer.objects.filter(
        is_active=True
    ).select_related(
        'profile__user'
    ).order_by('-experience_years')

    return render(request, 'accounts/trainers_list.html', {
        'trainers': trainers
    })


@login_required
def trainer_dashboard(request):
    """
    Личный кабинет тренера
    - Расписание занятий
    - Список клиентов на занятиях
    - Отметка посещений
    """
    from .models import Trainer, UserRole
    from apps.classes.models import Class
    from apps.bookings.models import Booking, BookingStatus
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta

    # Проверяем, что пользователь - тренер
    if not hasattr(request.user, 'profile') or request.user.profile.role != UserRole.TRAINER:
        messages.error(request, 'Доступ запрещён. Эта страница только для тренеров.')
        return redirect('accounts_web:home')

    try:
        trainer = request.user.profile.trainer_info
    except Trainer.DoesNotExist:
        messages.error(request, 'Профиль тренера не найден')
        return redirect('accounts_web:home')

    # Получаем занятия тренера
    now = timezone.now()

    # Предстоящие занятия (следующие 7 дней)
    upcoming_classes = Class.objects.filter(
        trainer=trainer,
        datetime__gte=now,
        datetime__lte=now + timedelta(days=7)
    ).select_related(
        'class_type',
        'room'
    ).annotate(
        booked_count=Count('bookings', filter=Q(bookings__status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED]))
    ).order_by('datetime')

    # Прошедшие занятия (последние 7 дней)
    past_classes = Class.objects.filter(
        trainer=trainer,
        datetime__lt=now,
        datetime__gte=now - timedelta(days=7)
    ).select_related(
        'class_type',
        'room'
    ).annotate(
        booked_count=Count('bookings', filter=Q(bookings__status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED]))
    ).order_by('-datetime')[:10]

    # Статистика
    total_classes = Class.objects.filter(trainer=trainer).count()
    upcoming_count = upcoming_classes.count()

    # Клиенты на ближайшем занятии
    next_class = upcoming_classes.first()
    next_class_clients = None
    if next_class:
        next_class_clients = Booking.objects.filter(
            class_instance=next_class,
            status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED]
        ).select_related(
            'client__profile__user'
        ).order_by('booking_date')

    # Уникальные клиенты тренера (за последние 30 дней)
    unique_clients = Booking.objects.filter(
        class_instance__trainer=trainer,
        class_instance__datetime__gte=now - timedelta(days=30),
        status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED]
    ).values('client').distinct().count()

    context = {
        'trainer': trainer,
        'upcoming_classes': upcoming_classes,
        'past_classes': past_classes,
        'total_classes': total_classes,
        'upcoming_count': upcoming_count,
        'unique_clients': unique_clients,
        'next_class': next_class,
        'next_class_clients': next_class_clients,
    }

    return render(request, 'accounts/trainer_dashboard.html', context)


@login_required
def trainer_class_detail(request, class_id):
    """
    Детали занятия для тренера с возможностью отметки посещений
    """
    from .models import Trainer, UserRole
    from apps.classes.models import Class
    from apps.bookings.models import Booking, BookingStatus, Visit
    from django.shortcuts import get_object_or_404

    # Проверяем, что пользователь - тренер
    if not hasattr(request.user, 'profile') or request.user.profile.role != UserRole.TRAINER:
        messages.error(request, 'Доступ запрещён')
        return redirect('accounts_web:home')

    try:
        trainer = request.user.profile.trainer_info
    except Trainer.DoesNotExist:
        messages.error(request, 'Профиль тренера не найден')
        return redirect('accounts_web:home')

    # Получаем занятие
    class_instance = get_object_or_404(Class, id=class_id, trainer=trainer)

    # Обработка отметки посещения
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        action = request.POST.get('action')

        if booking_id and action:
            try:
                booking = Booking.objects.get(id=booking_id, class_instance=class_instance)

                if action == 'mark_completed':
                    # Отмечаем посещение
                    booking.status = BookingStatus.COMPLETED
                    booking.save()

                    # Создаём запись о посещении, если её нет
                    Visit.objects.get_or_create(
                        booking=booking,
                        defaults={'checked_by': request.user}
                    )

                    # Уменьшаем счётчик посещений в абонементе
                    if booking.client.memberships.filter(status='ACTIVE').exists():
                        active_membership = booking.client.memberships.filter(status='ACTIVE').first()
                        if active_membership.visits_remaining is not None and active_membership.visits_remaining > 0:
                            active_membership.visits_remaining -= 1
                            active_membership.save()

                    messages.success(request, f'Посещение отмечено для {booking.client.profile.user.get_full_name()}')

                elif action == 'mark_no_show':
                    # Отмечаем неявку
                    booking.status = BookingStatus.NO_SHOW
                    booking.save()
                    messages.warning(request, f'Отмечена неявка для {booking.client.profile.user.get_full_name()}')

            except Booking.DoesNotExist:
                messages.error(request, 'Бронирование не найдено')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')

            return redirect('accounts_web:trainer_class_detail', class_id=class_id)

    # Получаем всех клиентов на занятии
    bookings = Booking.objects.filter(
        class_instance=class_instance
    ).select_related(
        'client__profile__user'
    ).prefetch_related(
        'visit'
    ).order_by('status', 'booking_date')

    # Подсчитываем только активные бронирования (CONFIRMED и COMPLETED)
    active_bookings_count = bookings.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED]
    ).count()

    context = {
        'class_instance': class_instance,
        'bookings': bookings,
        'active_bookings_count': active_bookings_count,
        'trainer': trainer,
    }

    return render(request, 'accounts/trainer_class_detail.html', context)
