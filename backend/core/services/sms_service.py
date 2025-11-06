"""
SMS сервис для отправки уведомлений через SMSC.ru

Документация API: https://smsc.ru/api/http/
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """
    Сервис для отправки SMS через SMSC.ru
    """

    def __init__(self):
        self.api_url = "https://smsc.ru/sys/send.php"
        self.login = getattr(settings, 'SMSC_LOGIN', None)
        self.password = getattr(settings, 'SMSC_PASSWORD', None)
        self.enabled = getattr(settings, 'SMS_ENABLED', False)

    def send_sms(self, phone: str, message: str) -> dict:
        """
        Отправить SMS на указанный номер

        Args:
            phone: Номер телефона в формате +79991234567
            message: Текст сообщения (до 160 символов)

        Returns:
            dict: Результат отправки
        """
        if not self.enabled:
            logger.info(f"SMS отключены. Сообщение для {phone}: {message}")
            return {'success': False, 'message': 'SMS disabled in settings'}

        if not self.login or not self.password:
            logger.error("SMSC credentials не настроены")
            return {'success': False, 'message': 'SMSC credentials not configured'}

        # Очищаем номер телефона (убираем +)
        phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')

        # Параметры запроса
        params = {
            'login': self.login,
            'psw': self.password,
            'phones': phone_clean,
            'mes': message,
            'charset': 'utf-8',
            'fmt': 3  # Формат ответа JSON
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()

            result = response.json()

            if 'error' in result:
                logger.error(f"Ошибка отправки SMS: {result}")
                return {
                    'success': False,
                    'message': result.get('error', 'Unknown error')
                }

            logger.info(f"SMS успешно отправлено на {phone}")
            return {
                'success': True,
                'message': 'SMS sent successfully',
                'data': result
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке SMS: {e}")
            return {
                'success': False,
                'message': str(e)
            }


# Singleton instance
sms_service = SMSService()


# Вспомогательные функции для разных типов уведомлений
def send_booking_confirmation_sms(phone: str, class_name: str, class_datetime: str) -> dict:
    """Отправить SMS подтверждения бронирования"""
    message = (
        f"Вы записаны на {class_name} {class_datetime}. "
        f"Отмена возможна за 24ч. АС УСК"
    )
    return sms_service.send_sms(phone, message)


def send_booking_reminder_sms(phone: str, class_name: str, class_datetime: str) -> dict:
    """Отправить SMS напоминание за 2 часа"""
    message = (
        f"Напоминание: через 2 часа у вас занятие {class_name}. "
        f"Ждём вас! АС УСК"
    )
    return sms_service.send_sms(phone, message)


def send_booking_cancelled_sms(phone: str, class_name: str, class_datetime: str) -> dict:
    """Отправить SMS об отмене бронирования"""
    message = (
        f"Ваше бронирование на {class_name} {class_datetime} отменено. "
        f"АС УСК"
    )
    return sms_service.send_sms(phone, message)


def send_membership_expiring_sms(phone: str, days_remaining: int) -> dict:
    """Отправить SMS о скором окончании абонемента"""
    message = (
        f"Ваш абонемент заканчивается через {days_remaining} дн. "
        f"Продлите на сайте или в клубе. АС УСК"
    )
    return sms_service.send_sms(phone, message)
