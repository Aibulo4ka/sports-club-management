"""
Celery задачи для аккаунтов и уведомлений
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_welcome_email(user_id):
    """
    Отправляет приветственное письмо новому пользователю

    Args:
        user_id: ID пользователя
    """
    from django.contrib.auth.models import User

    try:
        user = User.objects.get(id=user_id)

        subject = 'Добро пожаловать в АС УСК!'
        message = f"""
Здравствуйте, {user.get_full_name() or user.username}!

Добро пожаловать в нашу систему управления спортивным клубом АС УСК!

Мы рады видеть вас среди наших клиентов. Теперь вы можете:

✓ Просматривать расписание занятий
✓ Бронировать занятия онлайн
✓ Покупать абонементы
✓ Отслеживать свои посещения
✓ Использовать AI Персонального Тренера для создания планов тренировок и питания

Для начала работы:
1. Войдите в личный кабинет
2. Выберите подходящий абонемент
3. Забронируйте первое занятие

Если у вас возникнут вопросы, наша команда всегда готова помочь!

С уважением,
Команда АС УСК

---
Это автоматическое письмо. Пожалуйста, не отвечайте на него.
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return f"Welcome email отправлен пользователю {user.email}"

    except User.DoesNotExist:
        return f"Пользователь с ID {user_id} не найден"
    except Exception as e:
        return f"Ошибка при отправке welcome email: {e}"
