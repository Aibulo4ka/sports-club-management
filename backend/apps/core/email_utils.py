"""
Утилиты для отправки email уведомлений
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_template_email(subject, template_name, context, recipient_email):
    """
    Отправка email с использованием HTML шаблона

    Args:
        subject: Тема письма
        template_name: Имя шаблона (без расширения, например 'emails/payment_success')
        context: Контекст для шаблона
        recipient_email: Email получателя

    Returns:
        bool: True если отправлено успешно, False иначе
    """
    try:
        # Рендерим HTML версию
        html_content = render_to_string(f'{template_name}.html', context)

        # Создаём письмо
        email = EmailMultiAlternatives(
            subject=subject,
            body=html_content,  # Fallback текстовая версия
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )

        # Добавляем HTML версию
        email.attach_alternative(html_content, "text/html")

        # Отправляем
        email.send(fail_silently=False)

        logger.info(f"Email успешно отправлен на {recipient_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Ошибка отправки email на {recipient_email}: {str(e)}")
        return False


def send_payment_success_email(payment):
    """
    Отправка письма об успешной оплате

    Args:
        payment: Объект Payment
    """
    subject = f"Оплата №{payment.id} успешно выполнена - АС УСК"

    context = {
        'payment': payment,
        'user': payment.client.profile.user,
        'membership': payment.membership,
    }

    recipient = payment.client.profile.user.email

    return send_template_email(
        subject=subject,
        template_name='emails/payment_success',
        context=context,
        recipient_email=recipient
    )


def send_booking_reminder_email(booking):
    """
    Отправка напоминания о занятии

    Args:
        booking: Объект Booking
    """
    subject = f"Напоминание о занятии - {booking.class_session.class_type.name}"

    context = {
        'booking': booking,
        'user': booking.client.profile.user,
        'class': booking.class_session,
    }

    recipient = booking.client.profile.user.email

    return send_template_email(
        subject=subject,
        template_name='emails/booking_reminder',
        context=context,
        recipient_email=recipient
    )


def send_membership_activated_email(membership):
    """
    Отправка уведомления об активации абонемента

    Args:
        membership: Объект Membership
    """
    subject = f"Абонемент активирован - {membership.membership_type.name}"

    context = {
        'membership': membership,
        'user': membership.client.profile.user,
    }

    recipient = membership.client.profile.user.email

    return send_template_email(
        subject=subject,
        template_name='emails/membership_activated',
        context=context,
        recipient_email=recipient
    )
