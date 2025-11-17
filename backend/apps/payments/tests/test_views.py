"""
Integration тесты для API views приложения payments
"""

import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.payments.models import Payment, PaymentStatus, PaymentMethod


@pytest.mark.integration
class TestPaymentAPI:
    """Тесты для API платежей"""

    def test_list_own_payments(self, authenticated_client, test_payment):
        """Тест получения списка своих платежей"""
        url = reverse('payments:payment-list')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_get_payment_detail(self, authenticated_client, test_payment):
        """Тест получения деталей платежа"""
        url = reverse('payments:payment-detail', kwargs={'pk': test_payment.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_payment.id

    @patch('apps.payments.serializers.get_yookassa_service')
    def test_create_payment_yookassa(self, mock_yookassa, authenticated_client, test_membership_type, test_client_user, mock_yookassa_response):
        """Тест создания платежа через ЮKassa"""
        # Настраиваем mock
        mock_service = MagicMock()
        mock_service.create_payment.return_value = mock_yookassa_response
        mock_yookassa.return_value = mock_service

        url = reverse('payments:payment-list')
        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.YOOKASSA
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert 'payment_url' in response.data

    def test_create_payment_cash(self, authenticated_client, test_membership_type):
        """Тест создания платежа наличными"""
        url = reverse('payments:payment-list')
        data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.CASH
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_payment_invalid_membership_type(self, authenticated_client):
        """Тест создания платежа с несуществующим типом абонемента"""
        url = reverse('payments:payment-list')
        data = {
            'membership_type_id': 99999,
            'payment_method': PaymentMethod.CASH
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_payments_by_status(self, authenticated_client, test_payment):
        """Тест фильтрации платежей по статусу"""
        url = reverse('payments:payment-list')
        response = authenticated_client.get(url, {'status': PaymentStatus.PENDING})

        assert response.status_code == status.HTTP_200_OK

    def test_list_all_payments_as_admin(self, admin_client):
        """Тест получения всех платежей админом"""
        url = reverse('payments:payment-list')

        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestPaymentStatusCheckAPI:
    """Тесты для API проверки статуса платежа"""

    @patch('apps.payments.views.get_yookassa_service')
    def test_check_payment_status_success(self, mock_yookassa, authenticated_client, test_payment):
        """Тест проверки статуса платежа (успешный)"""
        # Настраиваем mock
        mock_service = MagicMock()
        mock_service.check_payment_status.return_value = {
            'status': 'succeeded',
            'paid': True,
            'amount': Decimal('5000.00'),
            'metadata': {}
        }
        mock_yookassa.return_value = mock_service

        test_payment.transaction_id = 'test-transaction-id'
        test_payment.payment_method = PaymentMethod.YOOKASSA
        test_payment.save()

        url = reverse('payments:payment-status', kwargs={'pk': test_payment.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data

    def test_check_status_cash_payment(self, authenticated_client, test_client, test_membership):
        """Тест проверки статуса наличного платежа"""
        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CASH
        )

        url = reverse('payments:payment-status', kwargs={'pk': payment.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.yookassa
class TestYooKassaWebhookAPI:
    """Тесты для webhook endpoint ЮKassa"""

    def test_webhook_payment_succeeded(self, api_client, test_client, test_membership):
        """Тест webhook при успешной оплате"""
        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.YOOKASSA,
            transaction_id='yookassa-payment-id-123'
        )

        url = reverse('payments:yookassa-webhook')
        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'yookassa-payment-id-123',
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': '5000.00',
                    'currency': 'RUB'
                },
                'metadata': {
                    'payment_id': str(payment.id)
                }
            }
        }

        response = api_client.post(url, webhook_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Проверяем что платёж обновлён
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.COMPLETED

        # Проверяем что абонемент активирован
        payment.membership.refresh_from_db()
        from apps.memberships.models import MembershipStatus
        assert payment.membership.status == MembershipStatus.ACTIVE

    def test_webhook_payment_canceled(self, api_client, test_client, test_membership):
        """Тест webhook при отмене платежа"""
        payment = Payment.objects.create(
            client=test_client,
            membership=test_membership,
            amount=Decimal('5000.00'),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.YOOKASSA,
            transaction_id='yookassa-payment-id-456'
        )

        url = reverse('payments:yookassa-webhook')
        webhook_data = {
            'event': 'payment.canceled',
            'object': {
                'id': 'yookassa-payment-id-456',
                'status': 'canceled',
                'paid': False,
                'amount': {
                    'value': '5000.00',
                    'currency': 'RUB'
                },
                'metadata': {
                    'payment_id': str(payment.id)
                }
            }
        }

        response = api_client.post(url, webhook_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        payment.refresh_from_db()
        assert payment.status == PaymentStatus.FAILED

    def test_webhook_invalid_payment_id(self, api_client):
        """Тест webhook с несуществующим payment_id"""
        url = reverse('payments:yookassa-webhook')
        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'some-id',
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': '1000.00',
                    'currency': 'RUB'
                },
                'metadata': {
                    'payment_id': '99999'  # Не существует
                }
            }
        }

        response = api_client.post(url, webhook_data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_webhook_malformed_data(self, api_client):
        """Тест webhook с неправильными данными"""
        url = reverse('payments:yookassa-webhook')
        webhook_data = {
            'event': 'payment.succeeded',
            # Отсутствует 'object'
        }

        response = api_client.post(url, webhook_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestPaymentPermissions:
    """Тесты прав доступа для платежей"""

    def test_client_can_see_only_own_payments(self, authenticated_client, test_payment, create_client):
        """Тест что клиент видит только свои платежи"""
        # Создаём платёж другого клиента
        other_client = create_client()
        from apps.memberships.models import MembershipType, Membership, MembershipStatus
        from datetime import date, timedelta

        membership_type = MembershipType.objects.create(
            name='Test Type',
            price=Decimal('1000.00'),
            duration_days=30
        )
        membership = Membership.objects.create(
            client=other_client,
            membership_type=membership_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=MembershipStatus.ACTIVE
        )
        other_payment = Payment.objects.create(
            client=other_client,
            membership=membership,
            amount=Decimal('1000.00'),
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CASH
        )

        # Пытаемся получить чужой платёж
        url = reverse('payments:payment-detail', kwargs={'pk': other_payment.id})

        response = authenticated_client.get(url)

        # Должен быть запрещён доступ
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_admin_can_see_all_payments(self, admin_client, test_payment):
        """Тест что админ видит все платежи"""
        url = reverse('payments:payment-list')

        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestPaymentWorkflow:
    """Тесты полного workflow оплаты"""

    @patch('apps.payments.serializers.get_yookassa_service')
    def test_full_payment_workflow(self, mock_yookassa, authenticated_client, test_membership_type, test_client_user, mock_yookassa_response):
        """Тест полного процесса оплаты: создание -> проверка -> webhook -> активация"""
        # Настраиваем mock
        mock_service = MagicMock()
        mock_service.create_payment.return_value = mock_yookassa_response
        mock_yookassa.return_value = mock_service

        # 1. Создаём платёж
        create_url = reverse('payments:payment-list')
        create_data = {
            'membership_type_id': test_membership_type.id,
            'payment_method': PaymentMethod.YOOKASSA
        }

        create_response = authenticated_client.post(create_url, create_data, format='json')
        assert create_response.status_code == status.HTTP_201_CREATED

        payment_id = create_response.data['id']
        payment = Payment.objects.get(id=payment_id)

        # 2. Симулируем webhook от ЮKassa
        webhook_url = reverse('payments:yookassa-webhook')
        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': payment.transaction_id,
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': str(payment.amount),
                    'currency': 'RUB'
                },
                'metadata': {
                    'payment_id': str(payment.id)
                }
            }
        }

        webhook_response = authenticated_client.post(webhook_url, webhook_data, format='json')
        assert webhook_response.status_code == status.HTTP_200_OK

        # 3. Проверяем что платёж завершён и абонемент активен
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.COMPLETED

        payment.membership.refresh_from_db()
        from apps.memberships.models import MembershipStatus
        assert payment.membership.status == MembershipStatus.ACTIVE
