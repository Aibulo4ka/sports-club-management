"""
Celery задачи для системы бронирований
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from .models import Booking, BookingStatus
from core.patterns.observer import BookingSubject


@shared_task
def send_booking_reminders():
    """
    Отправляет email напоминания за 2 часа до занятия

    Запускается каждые 30 минут (настроено в config/celery.py)

    Логика:
    - Находит все подтверждённые бронирования
    - Которые начнутся через 1.5-2.5 часа (окно 1 час для точности)
    - Отправляет напоминание через Observer pattern
    """
    now = timezone.now()

    # Временное окно: от 1.5 до 2.5 часов
    # (чтобы не отправить дважды, если задача запускается каждые 30 мин)
    time_start = now + timedelta(hours=1, minutes=30)
    time_end = now + timedelta(hours=2, minutes=30)

    # Находим бронирования в этом временном окне
    bookings = Booking.objects.select_related(
        'client__profile__user',
        'class_instance__class_type',
        'class_instance__room'
    ).filter(
        status=BookingStatus.CONFIRMED,
        class_instance__datetime__gte=time_start,
        class_instance__datetime__lt=time_end
    )

    # Используем Observer pattern для отправки уведомлений
    booking_subject = BookingSubject()

    sent_count = 0
    for booking in bookings:
        try:
            # Получаем email и телефон клиента
            user_email = booking.client.profile.user.email
            phone = booking.client.profile.phone
            class_name = booking.class_instance.class_type.name
            class_datetime = booking.class_instance.datetime.strftime('%d.%m.%Y %H:%M')

            # Отправляем напоминание через Observer (email + SMS)
            booking_subject.booking_reminder(
                user_email=user_email,
                phone=phone,
                class_name=class_name,
                class_datetime=class_datetime
            )

            sent_count += 1

        except Exception as e:
            # Логируем ошибку, но продолжаем обработку остальных
            print(f"Ошибка при отправке напоминания для бронирования {booking.id}: {e}")

    return f"Отправлено {sent_count} напоминаний"


@shared_task
def cancel_unconfirmed_bookings():
    """
    Автоматически отменяет неподтверждённые бронирования за 30 минут до занятия

    Запускается каждые 15 минут (настроено в config/celery.py)

    Примечание: В текущей реализации все бронирования создаются сразу как CONFIRMED.
    Эта задача нужна для будущего функционала "временное бронирование",
    когда клиент должен подтвердить присутствие за N часов.

    Сейчас эта задача отменяет бронирования со статусом CONFIRMED,
    если до занятия осталось менее 30 минут и клиент не отметился (нет Visit).
    """
    now = timezone.now()
    cutoff_time = now + timedelta(minutes=30)

    # Находим подтверждённые бронирования, которые скоро начнутся
    # и у которых нет отметки посещения
    bookings_to_cancel = Booking.objects.select_related(
        'class_instance',
        'client__profile__user'
    ).filter(
        status=BookingStatus.CONFIRMED,
        class_instance__datetime__lte=cutoff_time,
        class_instance__datetime__gt=now
    ).exclude(
        visit__isnull=False  # Исключаем те, где уже есть отметка посещения
    )

    cancelled_count = 0

    with transaction.atomic():
        for booking in bookings_to_cancel:
            # Отменяем бронирование
            booking.status = BookingStatus.NO_SHOW
            booking.cancelled_at = now
            booking.notes += "\n[Авто-отмена: не подтверждено за 30 мин до начала]"
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

            cancelled_count += 1

    return f"Автоматически отменено {cancelled_count} бронирований"


@shared_task
def cleanup_old_bookings():
    """
    Очищает старые бронирования (меняет статус на COMPLETED для прошедших занятий)

    Запускается раз в день (можно добавить в config/celery.py)

    Логика:
    - Находит все бронирования со статусом CONFIRMED
    - У которых занятие уже прошло
    - Меняет статус на COMPLETED или NO_SHOW (в зависимости от наличия Visit)
    """
    now = timezone.now()

    # Находим бронирования прошедших занятий
    old_bookings = Booking.objects.select_related('class_instance').filter(
        status=BookingStatus.CONFIRMED,
        class_instance__datetime__lt=now
    )

    completed_count = 0
    no_show_count = 0

    with transaction.atomic():
        for booking in old_bookings:
            # Если есть отметка посещения - COMPLETED
            if hasattr(booking, 'visit'):
                booking.status = BookingStatus.COMPLETED
                completed_count += 1
            else:
                # Если нет отметки - NO_SHOW
                booking.status = BookingStatus.NO_SHOW
                no_show_count += 1

            booking.save()

    return f"Обработано: {completed_count} завершённых, {no_show_count} неявок"


@shared_task
def send_booking_confirmation_email(booking_id):
    """
    Отправляет подтверждение бронирования (вызывается сразу после создания)

    Args:
        booking_id: ID бронирования
    """
    try:
        booking = Booking.objects.select_related(
            'client__profile__user',
            'class_instance__class_type',
            'class_instance__room',
            'class_instance__trainer__profile__user'
        ).get(id=booking_id)

        # Используем Observer pattern
        booking_subject = BookingSubject()

        user_email = booking.client.profile.user.email
        phone = booking.client.profile.phone
        class_name = booking.class_instance.class_type.name
        class_datetime = booking.class_instance.datetime.strftime('%d.%m.%Y %H:%M')

        booking_subject.booking_created(
            user_email=user_email,
            phone=phone,
            class_name=class_name,
            class_datetime=class_datetime
        )

        return f"Отправлено подтверждение для бронирования {booking_id}"

    except Booking.DoesNotExist:
        return f"Бронирование {booking_id} не найдено"
    except Exception as e:
        return f"Ошибка при отправке подтверждения: {e}"
