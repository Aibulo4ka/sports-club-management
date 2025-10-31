"""
Observer Pattern - NotificationObserver
Используется для отправки уведомлений при изменении статусов (платежи, бронирования)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from django.core.mail import send_mail
from django.conf import settings


# Subject (Observable)
class Subject(ABC):
    """
    Subject that observers can subscribe to
    """

    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: 'Observer') -> None:
        """Attach an observer"""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: 'Observer') -> None:
        """Detach an observer"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: str, data: Dict[str, Any]) -> None:
        """Notify all observers about an event"""
        for observer in self._observers:
            observer.update(event, data)


# Observer Interface
class Observer(ABC):
    """
    Observer interface
    """

    @abstractmethod
    def update(self, event: str, data: Dict[str, Any]) -> None:
        """
        Receive update from subject

        Args:
            event: Name of the event
            data: Event data
        """
        pass


# Concrete Observers
class EmailNotifier(Observer):
    """
    Send email notifications
    """

    def update(self, event: str, data: Dict[str, Any]) -> None:
        """Send email based on event"""
        if event == 'payment_completed':
            self._send_payment_confirmation(data)
        elif event == 'booking_created':
            self._send_booking_confirmation(data)
        elif event == 'booking_reminder':
            self._send_booking_reminder(data)
        elif event == 'membership_expiring':
            self._send_membership_expiring(data)

    def _send_payment_confirmation(self, data: Dict[str, Any]) -> None:
        """Send payment confirmation email"""
        user_email = data.get('user_email')
        amount = data.get('amount')
        membership_type = data.get('membership_type')

        subject = 'Оплата прошла успешно'
        message = f"""
        Здравствуйте!

        Ваш платёж на сумму {amount} руб. успешно обработан.
        Абонемент "{membership_type}" активирован.

        Спасибо за покупку!
        Команда спортивного клуба
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=True
        )

    def _send_booking_confirmation(self, data: Dict[str, Any]) -> None:
        """Send booking confirmation email"""
        user_email = data.get('user_email')
        class_name = data.get('class_name')
        class_datetime = data.get('class_datetime')

        subject = 'Бронирование подтверждено'
        message = f"""
        Здравствуйте!

        Ваше бронирование подтверждено:
        Занятие: {class_name}
        Дата и время: {class_datetime}

        До встречи на занятии!
        Команда спортивного клуба
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=True
        )

    def _send_booking_reminder(self, data: Dict[str, Any]) -> None:
        """Send booking reminder (2 hours before)"""
        user_email = data.get('user_email')
        class_name = data.get('class_name')
        class_datetime = data.get('class_datetime')

        subject = 'Напоминание о занятии'
        message = f"""
        Здравствуйте!

        Напоминаем, что через 2 часа у вас занятие:
        Занятие: {class_name}
        Дата и время: {class_datetime}

        Ждём вас!
        Команда спортивного клуба
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=True
        )

    def _send_membership_expiring(self, data: Dict[str, Any]) -> None:
        """Send membership expiring notification"""
        user_email = data.get('user_email')
        days_remaining = data.get('days_remaining')

        subject = 'Ваш абонемент заканчивается'
        message = f"""
        Здравствуйте!

        Ваш абонемент заканчивается через {days_remaining} дней.
        Не забудьте продлить абонемент, чтобы продолжить занятия!

        Команда спортивного клуба
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=True
        )


class SMSNotifier(Observer):
    """
    Send SMS notifications (optional - requires SMS service integration)
    """

    def update(self, event: str, data: Dict[str, Any]) -> None:
        """Send SMS based on event"""
        # TODO: Implement SMS notifications using SMSC.ru or Twilio
        pass


class AnalyticsLogger(Observer):
    """
    Log events for analytics
    """

    def update(self, event: str, data: Dict[str, Any]) -> None:
        """Log event to analytics"""
        # TODO: Implement analytics logging
        import logging
        logger = logging.getLogger('analytics')
        logger.info(f"Event: {event}, Data: {data}")


# Concrete Subject Example
class PaymentSubject(Subject):
    """
    Subject for payment events
    """

    def __init__(self):
        super().__init__()
        # Attach default observers
        self.attach(EmailNotifier())
        self.attach(AnalyticsLogger())

    def payment_completed(self, user_email: str, amount: float, membership_type: str) -> None:
        """Notify about completed payment"""
        self.notify('payment_completed', {
            'user_email': user_email,
            'amount': amount,
            'membership_type': membership_type
        })


class BookingSubject(Subject):
    """
    Subject for booking events
    """

    def __init__(self):
        super().__init__()
        # Attach default observers
        self.attach(EmailNotifier())
        self.attach(AnalyticsLogger())

    def booking_created(self, user_email: str, class_name: str, class_datetime: str) -> None:
        """Notify about created booking"""
        self.notify('booking_created', {
            'user_email': user_email,
            'class_name': class_name,
            'class_datetime': class_datetime
        })

    def booking_reminder(self, user_email: str, class_name: str, class_datetime: str) -> None:
        """Send booking reminder"""
        self.notify('booking_reminder', {
            'user_email': user_email,
            'class_name': class_name,
            'class_datetime': class_datetime
        })
