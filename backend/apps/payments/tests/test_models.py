"""
Unit-тесты для моделей приложения payments
"""

import pytest
from decimal import Decimal
from apps.payments.models import Payment, PaymentStatus, PaymentMethod


@pytest.mark.unit
class TestPaymentModel:
    """Тесты для модели Payment"""

    def test_create_payment(self, test_payment):
        """Тест создания платежа"""
        assert test_payment.amount == Decimal('5000.00')
        assert test_payment.status == PaymentStatus.PENDING
        assert test_payment.payment_method == PaymentMethod.YOOKASSA
        assert test_payment.client is not None
        assert test_payment.membership is not None

    def test_str_representation(self, test_payment):
        """Тест строкового представления"""
        result = str(test_payment)
        assert f"Payment #{test_payment.id}" in result
        assert "5000.00 руб." in result
        assert test_payment.get_status_display() in result

    def test_payment_statuses(self):
        """Тест всех статусов платежа"""
        assert hasattr(PaymentStatus, 'PENDING')
        assert hasattr(PaymentStatus, 'COMPLETED')
        assert hasattr(PaymentStatus, 'FAILED')
        assert hasattr(PaymentStatus, 'REFUNDED')

    def test_payment_methods(self):
        """Тест всех методов оплаты"""
        assert hasattr(PaymentMethod, 'CARD')
        assert hasattr(PaymentMethod, 'CASH')
        assert hasattr(PaymentMethod, 'YOOKASSA')

    def test_payment_with_yookassa_data(self, test_client, test_membership):
        """Тест платежа с данными ЮKassa"""
        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.YOOKASSA,
            transaction_id='2d96e1b2-000f-5000-8000-18db351245c7',
            payment_url='https://yoomoney.ru/checkout/...'
        )

        assert payment.transaction_id == '2d96e1b2-000f-5000-8000-18db351245c7'
        assert payment.payment_url.startswith('https://yoomoney.ru')

    def test_completed_payment(self, test_client, test_membership):
        """Тест завершённого платежа"""
        from django.utils import timezone

        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CARD,
            completed_at=timezone.now()
        )

        assert payment.status == PaymentStatus.COMPLETED
        assert payment.completed_at is not None

    def test_failed_payment(self, test_client, test_membership):
        """Тест неудачного платежа"""
        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.FAILED,
            payment_method=PaymentMethod.YOOKASSA,
            notes='Ошибка: недостаточно средств'
        )

        assert payment.status == PaymentStatus.FAILED
        assert 'недостаточно средств' in payment.notes

    def test_refunded_payment(self, test_client, test_membership):
        """Тест возвращённого платежа"""
        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.REFUNDED,
            payment_method=PaymentMethod.YOOKASSA
        )

        assert payment.status == PaymentStatus.REFUNDED

    def test_payment_ordering(self, test_client, test_membership):
        """Тест сортировки по дате создания"""
        p1 = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('1000.00'),
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CASH
        )

        p2 = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('2000.00'),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.YOOKASSA
        )

        payments = list(Payment.objects.all())
        # Новые первыми
        assert payments[0] == p2
        assert payments[1] == p1

    def test_payment_belongs_to_correct_client(self, test_client, test_payment):
        """Тест что платёж принадлежит правильному клиенту"""
        assert test_payment.client == test_client
        assert test_payment in test_client.payments.all()

    def test_payment_without_membership(self, test_client):
        """Тест платежа без привязки к абонементу (например, разовый платёж)"""
        payment = Payment.objects.create(
            client=test_client,
            membership=None,  # Без абонемента
            amount=Decimal('500.00'),
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CASH,
            notes='Разовый платёж за занятие'
        )

        assert payment.membership is None
        assert payment.amount == Decimal('500.00')

    def test_payment_amount_validation(self, test_client, test_membership):
        """Тест валидации минимальной суммы платежа"""
        from django.core.exceptions import ValidationError

        payment = Payment(
            client=test_client,
            membership=test_membership,
            amount=Decimal('0.00'),  # Недопустимая сумма
            payment_method=PaymentMethod.CASH
        )

        with pytest.raises(ValidationError):
            payment.full_clean()

    def test_payment_with_notes(self, test_payment):
        """Тест платежа с заметками"""
        test_payment.notes = 'Применена студенческая скидка 20%'
        test_payment.save()

        assert 'студенческая скидка' in test_payment.notes

    def test_cash_payment(self, test_client, test_membership):
        """Тест платежа наличными"""
        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CASH
        )

        assert payment.payment_method == PaymentMethod.CASH
        assert payment.transaction_id == ''
        assert payment.payment_url == ''
