"""
Models for bookings app: Booking, Visit
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import Client
from apps.classes.models import Class


class BookingStatus(models.TextChoices):
    CONFIRMED = 'CONFIRMED', 'Подтверждено'
    CANCELLED = 'CANCELLED', 'Отменено'
    COMPLETED = 'COMPLETED', 'Завершено'
    NO_SHOW = 'NO_SHOW', 'Не пришел'


class Booking(models.Model):
    """
    Client's booking for a class
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='bookings')
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата бронирования')
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.CONFIRMED,
        verbose_name='Статус'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отмены')
    notes = models.TextField(blank=True, verbose_name='Заметки')

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-booking_date']
        unique_together = ('client', 'class_instance')

    def __str__(self):
        return f"{self.client} - {self.class_instance} ({self.get_status_display()})"

    def clean(self):
        """
        Валидация на уровне модели
        Проверяет, что у клиента есть активный абонемент на дату занятия
        """
        super().clean()

        # Пропускаем валидацию для обновления существующих записей
        if self.pk:
            return

        # Проверяем активный абонемент на дату занятия
        from apps.memberships.models import MembershipStatus

        active_membership = self.client.memberships.filter(
            status=MembershipStatus.ACTIVE,
            start_date__lte=self.class_instance.datetime.date(),
            end_date__gte=self.class_instance.datetime.date()
        ).first()

        if not active_membership:
            raise ValidationError({
                'class_instance': f'У клиента {self.client} нет активного абонемента на дату занятия '
                                f'{self.class_instance.datetime.date()}. '
                                f'Абонемент должен быть активен с {self.class_instance.datetime.date()}.'
            })

        # Проверяем остаток посещений
        if active_membership.visits_remaining is not None:
            if active_membership.visits_remaining <= 0:
                raise ValidationError({
                    'client': f'У абонемента {active_membership} закончились посещения'
                })

    @property
    def can_cancel(self):
        """
        Проверяет, можно ли отменить бронирование
        Правила: статус CONFIRMED и до занятия >= 24 часов
        """
        if self.status != BookingStatus.CONFIRMED:
            return False
        time_until_class = self.class_instance.datetime - timezone.now()
        return time_until_class > timedelta(hours=24)


class Visit(models.Model):
    """
    Actual visit/attendance record
    """
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='visit')
    checked_in_at = models.DateTimeField(auto_now_add=True, verbose_name='Время отметки')
    checked_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Отметил'
    )

    class Meta:
        verbose_name = 'Посещение'
        verbose_name_plural = 'Посещения'
        ordering = ['-checked_in_at']

    def __str__(self):
        return f"Visit: {self.booking}"
