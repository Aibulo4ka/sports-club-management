"""
Celery задачи для абонементов
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_membership_expiry_reminders():
    """
    Отправляет уведомления об истечении абонемента за 3 дня

    Запускается раз в день (можно настроить в config/celery.py)

    Логика:
    - Находит все активные абонементы
    - У которых осталось 3 дня до истечения
    - Отправляет email клиенту
    """
    from .models import Membership

    today = timezone.now().date()
    target_date = today + timedelta(days=3)

    # Находим абонементы, которые истекают через 3 дня
    expiring_memberships = Membership.objects.select_related(
        'client__profile__user',
        'membership_type'
    ).filter(
        status='ACTIVE',
        end_date=target_date
    )

    sent_count = 0

    for membership in expiring_memberships:
        try:
            user = membership.client.profile.user
            user_email = user.email

            # Проверяем, есть ли email
            if not user_email:
                continue

            subject = 'Ваш абонемент скоро истекает'

            visits_info = ""
            if membership.visits_remaining is not None:
                visits_info = f"\nОставшиеся посещения: {membership.visits_remaining}"

            message = f"""
Здравствуйте, {user.get_full_name() or user.username}!

Напоминаем, что ваш абонемент "{membership.membership_type.name}" истекает через 3 дня.

Детали абонемента:
- Тип: {membership.membership_type.name}
- Дата окончания: {membership.end_date.strftime('%d.%m.%Y')}{visits_info}

Чтобы продолжить заниматься в нашем клубе, пожалуйста, продлите абонемент.

Вы можете:
1. Войти в личный кабинет
2. Перейти в раздел "Абонементы"
3. Выбрать подходящий абонемент и оплатить онлайн

Если у вас возникнут вопросы, мы всегда готовы помочь!

С уважением,
Команда АС УСК

---
Это автоматическое письмо. Пожалуйста, не отвечайте на него.
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )

            sent_count += 1

        except Exception as e:
            # Логируем ошибку, но продолжаем обработку остальных
            print(f"Ошибка при отправке напоминания об истечении абонемента {membership.id}: {e}")

    return f"Отправлено {sent_count} напоминаний об истечении абонементов"


@shared_task
def deactivate_expired_memberships():
    """
    Деактивирует истекшие абонементы

    Запускается раз в день

    Логика:
    - Находит все активные абонементы с истекшей датой
    - Меняет статус на EXPIRED
    """
    from .models import Membership

    today = timezone.now().date()

    # Находим истекшие абонементы
    expired_memberships = Membership.objects.filter(
        status='ACTIVE',
        end_date__lt=today
    )

    count = expired_memberships.update(status='EXPIRED')

    return f"Деактивировано {count} истекших абонементов"
