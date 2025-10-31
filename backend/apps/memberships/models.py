"""
Models for memberships app: MembershipType, Membership
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.accounts.models import Client


class MembershipType(models.Model):
    """
    Type of membership (monthly, annual, unlimited, etc.)
    """
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Цена'
    )
    duration_days = models.PositiveIntegerField(verbose_name='Длительность (дней)')
    visits_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Лимит посещений (None = безлимит)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Тип абонемента'
        verbose_name_plural = 'Типы абонементов'
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.price} руб."


class MembershipStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Активен'
    EXPIRED = 'EXPIRED', 'Истёк'
    SUSPENDED = 'SUSPENDED', 'Приостановлен'


class Membership(models.Model):
    """
    Client's purchased membership
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='memberships')
    membership_type = models.ForeignKey(MembershipType, on_delete=models.PROTECT)
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE
    )
    visits_remaining = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Осталось посещений'
    )
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата покупки')

    class Meta:
        verbose_name = 'Абонемент'
        verbose_name_plural = 'Абонементы'
        ordering = ['-purchased_at']

    def __str__(self):
        return f"{self.client} - {self.membership_type.name} ({self.status})"
