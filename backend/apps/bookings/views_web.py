"""
Web views (template-based) для бронирований
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from .models import Booking, BookingStatus
from apps.classes.models import Class
from apps.accounts.models import Client
from .tasks import send_booking_confirmation_email


@login_required
def my_bookings_view(request):
    """
    Страница "Мои бронирования"
    GET /bookings/my/
    """
    # Получаем клиента текущего пользователя
    try:
        client = request.user.profile.client_info
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Профиль клиента не найден')
        return redirect('accounts_web:home')

    # Получаем бронирования клиента
    now = timezone.now()

    # Предстоящие бронирования (подтверждённые)
    upcoming_bookings = Booking.objects.select_related(
        'class_instance__class_type',
        'class_instance__trainer__profile__user',
        'class_instance__room'
    ).filter(
        client=client,
        status=BookingStatus.CONFIRMED,
        class_instance__datetime__gte=now
    ).order_by('class_instance__datetime')

    # Прошедшие бронирования
    past_bookings = Booking.objects.select_related(
        'class_instance__class_type',
        'class_instance__trainer__profile__user',
        'class_instance__room'
    ).filter(
        client=client,
        class_instance__datetime__lt=now
    ).order_by('-class_instance__datetime')[:10]  # Последние 10

    # Отменённые бронирования
    cancelled_bookings = Booking.objects.select_related(
        'class_instance__class_type',
        'class_instance__trainer__profile__user',
        'class_instance__room'
    ).filter(
        client=client,
        status=BookingStatus.CANCELLED
    ).order_by('-cancelled_at')[:5]  # Последние 5

    context = {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'cancelled_bookings': cancelled_bookings,
    }

    return render(request, 'bookings/my_bookings.html', context)


@login_required
@transaction.atomic
def create_booking_view(request, class_id):
    """
    Создать бронирование
    POST /bookings/create/<class_id>/
    """
    # Получаем занятие
    class_instance = get_object_or_404(Class, id=class_id)

    # Получаем клиента
    try:
        client = request.user.profile.client_info
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Профиль клиента не найден')
        return redirect('classes_web:schedule')

    # Проверка: занятие уже прошло
    if class_instance.datetime < timezone.now():
        messages.error(request, 'Нельзя забронировать занятие в прошлом')
        return redirect('classes_web:detail', class_id=class_id)

    # Проверка: есть свободные места
    if class_instance.available_spots <= 0:
        messages.error(request, 'Нет свободных мест на это занятие')
        return redirect('classes_web:detail', class_id=class_id)

    # Проверка: нет дубликата бронирования
    existing_booking = Booking.objects.filter(
        client=client,
        class_instance=class_instance
    ).first()

    if existing_booking:
        if existing_booking.status == BookingStatus.CONFIRMED:
            messages.warning(request, 'Вы уже забронировали это занятие')
        elif existing_booking.status == BookingStatus.CANCELLED:
            messages.info(request, 'Вы ранее отменили это бронирование')
        return redirect('classes_web:detail', class_id=class_id)

    # Проверка: есть активный абонемент
    active_membership = client.memberships.filter(
        status='ACTIVE',
        start_date__lte=class_instance.datetime.date(),
        end_date__gte=class_instance.datetime.date()
    ).first()

    if not active_membership:
        messages.error(
            request,
            'У вас нет активного абонемента на дату занятия. '
            'Пожалуйста, приобретите абонемент.'
        )
        return redirect('memberships_web:catalog')

    # Проверка: остаток посещений
    if active_membership.visits_remaining is not None:
        if active_membership.visits_remaining <= 0:
            messages.error(request, 'У вашего абонемента закончились посещения')
            return redirect('memberships_web:catalog')

    # Создаём бронирование
    booking = Booking.objects.create(
        client=client,
        class_instance=class_instance,
        status=BookingStatus.CONFIRMED,
        notes=request.POST.get('notes', '')
    )

    # Уменьшаем количество оставшихся посещений
    if active_membership.visits_remaining is not None:
        active_membership.visits_remaining -= 1
        active_membership.save()

    # Отправляем email подтверждение асинхронно
    send_booking_confirmation_email.delay(booking.id)

    messages.success(
        request,
        f'Бронирование на занятие "{class_instance.class_type.name}" '
        f'{class_instance.datetime.strftime("%d.%m.%Y в %H:%M")} успешно создано!'
    )

    return redirect('bookings_web:my_bookings')


@login_required
@transaction.atomic
def cancel_booking_view(request, booking_id):
    """
    Отменить бронирование
    POST /bookings/cancel/<booking_id>/
    """
    booking = get_object_or_404(Booking, id=booking_id)

    # Проверка: бронирование принадлежит текущему клиенту
    try:
        client = request.user.profile.client_info
        if booking.client != client:
            messages.error(request, 'Вы не можете отменить чужое бронирование')
            return redirect('bookings_web:my_bookings')
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Профиль клиента не найден')
        return redirect('accounts_web:home')

    # Проверка: статус
    if booking.status != BookingStatus.CONFIRMED:
        messages.error(request, 'Можно отменить только подтверждённое бронирование')
        return redirect('bookings_web:my_bookings')

    # Проверка: время до занятия (минимум 24 часа)
    time_until_class = booking.class_instance.datetime - timezone.now()
    if time_until_class < timedelta(hours=24):
        messages.error(
            request,
            'Отмена возможна не менее чем за 24 часа до начала занятия'
        )
        return redirect('bookings_web:my_bookings')

    # Отменяем бронирование
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.save()

    # Возвращаем посещение в абонемент (если лимитированный)
    active_membership = booking.client.memberships.filter(
        status='ACTIVE',
        start_date__lte=booking.class_instance.datetime.date(),
        end_date__gte=booking.class_instance.datetime.date()
    ).first()

    if active_membership and active_membership.visits_remaining is not None:
        active_membership.visits_remaining += 1
        active_membership.save()

    messages.success(request, 'Бронирование успешно отменено')
    return redirect('bookings_web:my_bookings')
