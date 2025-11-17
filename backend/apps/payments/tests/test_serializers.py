"""
Unit-тесты для сериализаторов приложения payments
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.payments.serializers import (
    PaymentListSerializer, PaymentSerializer,
    PaymentCreateSerializer, PaymentUpdateSerializer
)
from apps.payments.models import Payment, PaymentStatus, PaymentMethod
from apps.memberships.models import MembershipStatus


@pytest.mark.unit
class TestPaymentListSerializer:
    """Тесты для PaymentListSerializer"""

    def test_serialize_payment(self, test_payment):
        """Тест сериализации платежа"""
        serializer = PaymentListSerializer(test_payment)

        data = serializer.data
        assert 'id' in data
        assert 'client_name' in data
        assert data['amount'] == str(test_payment.amount)
        assert data['status'] == test_payment.status
        assert 'status_display' in data
        assert 'method_display' in data

    def test_client_name_display(self, test_payment):
        """Тест отображения имени клиента"""
        serializer = PaymentListSerializer(test_payment)
        data = serializer.data

        expected_name = test_payment.client.profile.user.get_full_name()
        if not expected_name:
            expected_name = test_payment.client.profile.user.username

        assert data['client_name'] == expected_name

    def test_readonly_fields(self, test_payment):
        """Тест что поля только для чтения"""
        serializer = PaymentListSerializer(test_payment)
        meta = serializer.Meta

        readonly_fields = meta.read_only_fields
        assert 'client_name' in readonly_fields
        assert 'status_display' in readonly_fields
        assert 'method_display' in readonly_fields


@pytest.mark.unit
class TestPaymentSerializer:
    """Тесты для PaymentSerializer (полная версия)"""

    def test_serialize_payment_with_membership(self, test_payment):
        """Тест сериализации платежа с абонементом"""
        serializer = PaymentSerializer(test_payment)

        data = serializer.data
        assert 'id' in data
        assert 'client_name' in data
        assert 'client_email' in data
        assert 'client_phone' in data
        assert 'membership_type_name' in data
        assert data['amount'] == str(test_payment.amount)

    def test_serialize_payment_without_membership(self, test_client):
        """Тест сериализации платежа без абонемента"""
        payment = Payment.objects.create(
            client=test_client,
            membership=None,  # Без абонемента
            amount=Decimal('500.00'),
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CASH
        )

        serializer = PaymentSerializer(payment)
        data = serializer.data

        assert data['membership'] is None
        assert data['membership_type_name'] is None

    def test_client_details_fields(self, test_payment):
        """Тест полей с деталями клиента"""
        serializer = PaymentSerializer(test_payment)
        data = serializer.data

        assert data['client_email'] == test_payment.client.profile.user.email
        assert data['client_phone'] == test_payment.client.profile.phone


@pytest.mark.unit
class TestPaymentCreateSerializer:
    """Тесты для PaymentCreateSerializer"""

    def test_valid_data_cash(self, test_client, test_membership_type):
        """Тест создания платежа наличными"""
        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.CASH
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': test_client}
        )
        assert serializer.is_valid()

    def test_valid_data_yookassa(self, test_client, test_membership_type):
        """Тест создания платежа через ЮKassa"""
        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.YOOKASSA
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': test_client}
        )
        assert serializer.is_valid()

    def test_invalid_membership_type(self, test_client):
        """Тест с несуществующим типом абонемента"""
        data = {
            'membership_type_id': 99999,  # Не существует
            'payment_method': PaymentMethod.CASH
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': test_client}
        )
        assert not serializer.is_valid()
        assert 'membership_type_id' in serializer.errors

    def test_inactive_membership_type(self, test_client):
        """Тест с неактивным типом абонемента"""
        from apps.memberships.models import MembershipType

        inactive_type = MembershipType.objects.create(
            name='Неактивный',
            price=Decimal('1000.00'),
            duration_days=30,
            is_active=False
        )

        data = {
            'membership_type_id': inactive_type.id,
            'payment_method': PaymentMethod.CASH
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': test_client}
        )
        assert not serializer.is_valid()
        assert 'membership_type_id' in serializer.errors

    def test_missing_client_in_context(self, test_membership_type):
        """Тест без клиента в контексте"""
        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.CASH
        }

        serializer = PaymentCreateSerializer(data=data)
        assert not serializer.is_valid()

    @patch('apps.payments.serializers.get_yookassa_service')
    def test_create_payment_cash(self, mock_yookassa, test_client, test_membership_type):
        """Тест создания платежа наличными"""
        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.CASH
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': test_client}
        )
        assert serializer.is_valid()

        payment = serializer.save()

        # Проверяем созданный платёж
        assert payment.client == test_client
        assert payment.membership is not None
        assert payment.payment_method == PaymentMethod.CASH
        assert payment.status == PaymentStatus.PENDING
        assert payment.amount > 0

        # ЮKassa не должна вызываться для CASH
        mock_yookassa.assert_not_called()

    @patch('apps.payments.serializers.get_yookassa_service')
    def test_create_payment_yookassa_success(self, mock_yookassa, test_client, test_membership_type, mock_yookassa_response):
        """Тест успешного создания платежа через ЮKassa"""
        # Настраиваем mock
        mock_service = MagicMock()
        mock_service.create_payment.return_value = mock_yookassa_response
        mock_yookassa.return_value = mock_service

        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.YOOKASSA
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': test_client}
        )
        assert serializer.is_valid()

        payment = serializer.save()

        # Проверяем что ЮKassa вызвана
        mock_yookassa.assert_called_once()
        mock_service.create_payment.assert_called_once()

        # Проверяем что данные сохранены
        assert payment.transaction_id == mock_yookassa_response['payment_id']
        assert payment.payment_url == mock_yookassa_response['confirmation_url']
        assert payment.payment_method == PaymentMethod.YOOKASSA

    @patch('apps.payments.serializers.get_yookassa_service')
    def test_create_payment_yookassa_failure(self, mock_yookassa, test_client, test_membership_type):
        """Тест неудачного создания платежа в ЮKassa"""
        # Настраиваем mock для выброса ошибки
        mock_service = MagicMock()
        mock_service.create_payment.side_effect = Exception("YooKassa API error")
        mock_yookassa.return_value = mock_service

        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.YOOKASSA
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': test_client}
        )
        assert serializer.is_valid()

        # Должна быть ValidationError
        with pytest.raises(Exception):
            serializer.save()

    def test_price_calculation_with_discount(self, test_student_user, test_membership_type):
        """Тест расчёта цены со скидкой для студента"""
        client = test_student_user.profile.client_info

        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.CASH
        }

        serializer = PaymentCreateSerializer(
            data=data,
            context={'client': client}
        )
        assert serializer.is_valid()

        payment = serializer.save()

        # Цена должна быть меньше базовой (студенческая скидка)
        assert payment.amount < test_membership_type.price
        assert 'Скидка' in payment.notes


@pytest.mark.unit
class TestPaymentUpdateSerializer:
    """Тесты для PaymentUpdateSerializer"""

    def test_update_status_to_completed(self, test_payment):
        """Тест обновления статуса на COMPLETED"""
        data = {
            'status': PaymentStatus.COMPLETED
        }

        serializer = PaymentUpdateSerializer(test_payment, data=data, partial=True)
        assert serializer.is_valid()

        updated_payment = serializer.save()

        assert updated_payment.status == PaymentStatus.COMPLETED
        assert updated_payment.completed_at is not None

        # Абонемент должен активироваться
        assert updated_payment.membership.status == MembershipStatus.ACTIVE

    def test_update_status_to_failed(self, test_payment):
        """Тест обновления статуса на FAILED"""
        data = {
            'status': PaymentStatus.FAILED,
            'notes': 'Ошибка оплаты'
        }

        serializer = PaymentUpdateSerializer(test_payment, data=data, partial=True)
        assert serializer.is_valid()

        updated_payment = serializer.save()

        assert updated_payment.status == PaymentStatus.FAILED
        assert 'Ошибка оплаты' in updated_payment.notes

        # Абонемент НЕ должен активироваться
        assert updated_payment.membership.status != MembershipStatus.ACTIVE

    def test_update_transaction_id(self, test_payment):
        """Тест обновления transaction_id"""
        data = {
            'transaction_id': 'new-transaction-id-123'
        }

        serializer = PaymentUpdateSerializer(test_payment, data=data, partial=True)
        assert serializer.is_valid()

        updated_payment = serializer.save()
        assert updated_payment.transaction_id == 'new-transaction-id-123'

    def test_completed_at_auto_set(self, test_payment):
        """Тест автоматической установки completed_at при завершении"""
        original_status = test_payment.status

        data = {
            'status': PaymentStatus.COMPLETED
        }

        serializer = PaymentUpdateSerializer(test_payment, data=data, partial=True)
        assert serializer.is_valid()

        updated_payment = serializer.save()

        # completed_at должен быть установлен автоматически
        assert updated_payment.completed_at is not None

    def test_no_double_activation(self, test_payment):
        """Тест что абонемент не активируется повторно"""
        # Сначала завершаем платёж
        test_payment.status = PaymentStatus.COMPLETED
        test_payment.membership.status = MembershipStatus.ACTIVE
        test_payment.save()
        test_payment.membership.save()

        # Пытаемся обновить ещё раз
        data = {
            'notes': 'Дополнительная информация'
        }

        serializer = PaymentUpdateSerializer(test_payment, data=data, partial=True)
        assert serializer.is_valid()

        updated_payment = serializer.save()

        # Статус не должен измениться
        assert updated_payment.status == PaymentStatus.COMPLETED
        assert updated_payment.membership.status == MembershipStatus.ACTIVE
