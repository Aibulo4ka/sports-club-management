"""
Models for classes app: ClassType, Class, Schedule
"""

from django.db import models
from apps.accounts.models import Trainer
from apps.facilities.models import Room


class ClassType(models.Model):
    """
    Type of class (yoga, fitness, boxing, swimming, etc.)
    """
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name='Длительность (минут)')
    icon = models.ImageField(upload_to='class_types/', null=True, blank=True, verbose_name='Иконка')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Тип занятия'
        verbose_name_plural = 'Типы занятий'
        ordering = ['name']

    def __str__(self):
        return self.name


class ClassStatus(models.TextChoices):
    SCHEDULED = 'SCHEDULED', 'Запланировано'
    IN_PROGRESS = 'IN_PROGRESS', 'Идёт'
    COMPLETED = 'COMPLETED', 'Завершено'
    CANCELLED = 'CANCELLED', 'Отменено'


class Class(models.Model):
    """
    Specific class instance in schedule
    """
    class_type = models.ForeignKey(ClassType, on_delete=models.PROTECT, verbose_name='Тип занятия')
    trainer = models.ForeignKey(Trainer, on_delete=models.PROTECT, related_name='classes', verbose_name='Тренер')
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='classes', verbose_name='Зал')

    datetime = models.DateTimeField(verbose_name='Дата и время')
    duration_minutes = models.PositiveIntegerField(verbose_name='Длительность (минут)')
    max_capacity = models.PositiveIntegerField(verbose_name='Максимум мест')
    status = models.CharField(
        max_length=20,
        choices=ClassStatus.choices,
        default=ClassStatus.SCHEDULED,
        verbose_name='Статус'
    )

    notes = models.TextField(blank=True, verbose_name='Заметки')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Занятие'
        verbose_name_plural = 'Занятия'
        ordering = ['datetime']

    def __str__(self):
        return f"{self.class_type.name} - {self.datetime.strftime('%d.%m.%Y %H:%M')}"

    @property
    def available_spots(self):
        """Calculate available spots"""
        booked_count = self.bookings.filter(status='CONFIRMED').count()
        return self.max_capacity - booked_count
