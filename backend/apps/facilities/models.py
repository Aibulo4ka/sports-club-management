"""
Models for facilities app: Room
"""

from django.db import models


class Room(models.Model):
    """
    Room/hall in the sports club
    """
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    capacity = models.PositiveIntegerField(verbose_name='Вместимость')
    floor = models.PositiveIntegerField(default=1, verbose_name='Этаж')
    equipment = models.TextField(blank=True, verbose_name='Оборудование')
    photo = models.ImageField(upload_to='rooms/', null=True, blank=True, verbose_name='Фото')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Зал'
        verbose_name_plural = 'Залы'
        ordering = ['floor', 'name']

    def __str__(self):
        return f"{self.name} (этаж {self.floor})"
