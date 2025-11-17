"""
Models for payments app: Payment
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.accounts.models import Client
from apps.memberships.models import Membership


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Ожидает оплаты'
    COMPLETED = 'COMPLETED', 'Оплачено'
    FAILED = 'FAILED', 'Ошибка'
    REFUNDED = 'REFUNDED', 'Возвращено'


class PaymentMethod(models.TextChoices):
    CARD = 'CARD', 'Банковская карта'
    CASH = 'CASH', 'Наличные'
    YOOKASSA = 'YOOKASSA', 'ЮKassa'


class Payment(models.Model):
    """
    Payment transaction
    """
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='payments')
    membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Сумма'
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name='Статус'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.YOOKASSA,
        verbose_name='Способ оплаты'
    )

    # External payment system fields
    transaction_id = models.CharField(max_length=255, blank=True, verbose_name='ID транзакции')
    payment_url = models.URLField(blank=True, verbose_name='URL оплаты')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершен')

    notes = models.TextField(blank=True, verbose_name='Заметки')

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.amount} руб. ({self.get_status_display()})"
