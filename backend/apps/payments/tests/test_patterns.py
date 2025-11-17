"""
Тесты для паттерна Singleton в YooKassaService
"""

import pytest
from unittest.mock import patch, MagicMock

from apps.payments.yookassa_service import YooKassaService, get_yookassa_service


@pytest.mark.patterns
class TestSingletonPattern:
    """Тесты для паттерна Singleton в YooKassaService"""

    def test_singleton_returns_same_instance(self):
        """Тест что get_yookassa_service всегда возвращает один и тот же экземпляр"""
        # Получаем первый экземпляр
        service1 = get_yookassa_service()

        # Получаем второй экземпляр
        service2 = get_yookassa_service()

        # Должны быть одним и тем же объектом
        assert service1 is service2
        assert id(service1) == id(service2)

    def test_singleton_multiple_calls(self):
        """Тест что множественные вызовы возвращают тот же экземпляр"""
        instances = [get_yookassa_service() for _ in range(10)]

        # Все должны быть одним объектом
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

    def test_singleton_instance_type(self):
        """Тест что singleton возвращает правильный тип"""
        service = get_yookassa_service()

        assert isinstance(service, YooKassaService)

    @patch('apps.payments.yookassa_service.Configuration')
    def test_singleton_initialized_once(self, mock_config):
        """Тест что инициализация происходит только один раз"""
        # Сбрасываем singleton для чистого теста
        import apps.payments.yookassa_service as yks_module
        yks_module._yookassa_service = None

        # Первый вызов - должен инициализироваться
        service1 = get_yookassa_service()

        # Второй вызов - НЕ должен инициализироваться заново
        service2 = get_yookassa_service()

        # Оба вызова вернули тот же экземпляр
        assert service1 is service2

        # Восстанавливаем singleton
        yks_module._yookassa_service = None

    def test_singleton_has_required_methods(self):
        """Тест что singleton имеет все необходимые методы"""
        service = get_yookassa_service()

        required_methods = [
            'create_payment',
            'check_payment_status',
            'process_webhook',
            'cancel_payment',
            'create_refund'
        ]

        for method_name in required_methods:
            assert hasattr(service, method_name)
            assert callable(getattr(service, method_name))

    def test_singleton_state_persistence(self):
        """Тест что состояние singleton сохраняется между вызовами"""
        service1 = get_yookassa_service()

        # Добавляем кастомный атрибут (для теста)
        service1.test_attribute = 'test_value'

        # Получаем "новый" экземпляр
        service2 = get_yookassa_service()

        # Атрибут должен сохраниться (это тот же объект)
        assert hasattr(service2, 'test_attribute')
        assert service2.test_attribute == 'test_value'

        # Очищаем после теста
        delattr(service2, 'test_attribute')

    def test_singleton_pattern_benefits(self):
        """
        Тест демонстрирующий преимущества Singleton:
        - Один экземпляр для всего приложения
        - Экономия ресурсов (нет повторной инициализации)
        - Единая точка доступа к сервису
        """
        # Симулируем множественные запросы к сервису из разных частей приложения
        from apps.payments.yookassa_service import get_yookassa_service

        # Модуль 1 получает сервис
        service_from_module1 = get_yookassa_service()

        # Модуль 2 получает сервис
        service_from_module2 = get_yookassa_service()

        # Модуль 3 получает сервис
        service_from_module3 = get_yookassa_service()

        # Все модули работают с одним экземпляром
        assert service_from_module1 is service_from_module2
        assert service_from_module2 is service_from_module3

        # Это экономит память и обеспечивает консистентность


@pytest.mark.patterns
@pytest.mark.yookassa
class TestYooKassaServiceMethods:
    """Тесты методов YooKassaService с mock'ами"""

    @patch('apps.payments.yookassa_service.YooPayment')
    def test_create_payment_method(self, mock_payment):
        """Тест метода create_payment"""
        from decimal import Decimal

        # Настраиваем mock
        mock_payment_instance = MagicMock()
        mock_payment_instance.id = 'test-payment-id-123'
        mock_payment_instance.status = 'pending'
        mock_payment_instance.test = True
        mock_payment_instance.confirmation.confirmation_url = 'https://test.url'

        mock_payment.create.return_value = mock_payment_instance

        # Вызываем метод
        service = get_yookassa_service()
        result = service.create_payment(
            amount=Decimal('1000.00'),
            description='Test payment',
            client_email='test@test.com',
            return_url='https://return.url',
            metadata={'test': 'data'}
        )

        # Проверяем результат
        assert result['payment_id'] == 'test-payment-id-123'
        assert result['status'] == 'pending'
        assert result['test'] is True
        assert 'confirmation_url' in result

        # Проверяем что метод был вызван
        mock_payment.create.assert_called_once()

    @patch('apps.payments.yookassa_service.YooPayment')
    def test_check_payment_status_method(self, mock_payment):
        """Тест метода check_payment_status"""
        from decimal import Decimal
        from datetime import datetime

        # Настраиваем mock
        mock_payment_instance = MagicMock()
        mock_payment_instance.status = 'succeeded'
        mock_payment_instance.paid = True
        mock_payment_instance.amount.value = '1000.00'
        mock_payment_instance.created_at = datetime.now()
        mock_payment_instance.metadata = {'client_id': '123'}

        mock_payment.find_one.return_value = mock_payment_instance

        # Вызываем метод
        service = get_yookassa_service()
        result = service.check_payment_status('test-payment-id')

        # Проверяем результат
        assert result['status'] == 'succeeded'
        assert result['paid'] is True
        assert result['amount'] == Decimal('1000.00')
        assert 'metadata' in result

        # Проверяем что метод был вызван с правильным ID
        mock_payment.find_one.assert_called_once_with('test-payment-id')

    def test_process_webhook_method(self):
        """Тест метода process_webhook"""
        from decimal import Decimal

        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'webhook-payment-id',
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': '5000.00',
                    'currency': 'RUB'
                },
                'metadata': {
                    'payment_id': '456'
                }
            }
        }

        service = get_yookassa_service()
        result = service.process_webhook(webhook_data)

        # Проверяем результат
        assert result['payment_id'] == 'webhook-payment-id'
        assert result['status'] == 'succeeded'
        assert result['paid'] is True
        assert result['amount'] == Decimal('5000.00')
        assert result['metadata']['payment_id'] == '456'
        assert result['event_type'] == 'payment.succeeded'

    def test_process_webhook_invalid_data(self):
        """Тест process_webhook с невалидными данными"""
        webhook_data = {
            'event': 'payment.succeeded',
            # Отсутствует 'object'
        }

        service = get_yookassa_service()

        # Должно выбросить исключение
        with pytest.raises(Exception) as exc_info:
            service.process_webhook(webhook_data)

        assert 'не содержит объект' in str(exc_info.value)

    @patch('apps.payments.yookassa_service.YooPayment')
    def test_cancel_payment_method(self, mock_payment):
        """Тест метода cancel_payment"""
        service = get_yookassa_service()
        result = service.cancel_payment('test-payment-id')

        # Должен вернуть True
        assert result is True

        # Проверяем что метод cancel был вызван
        mock_payment.cancel.assert_called_once()

    @patch('apps.payments.yookassa_service.YooPayment')
    def test_cancel_payment_error(self, mock_payment):
        """Тест cancel_payment при ошибке"""
        # Настраиваем mock для выброса ошибки
        mock_payment.cancel.side_effect = Exception('Cancel error')

        service = get_yookassa_service()
        result = service.cancel_payment('test-payment-id')

        # Должен вернуть False при ошибке
        assert result is False

    @patch('apps.payments.yookassa_service.Refund')
    def test_create_refund_method(self, mock_refund):
        """Тест метода create_refund"""
        from decimal import Decimal

        # Настраиваем mock
        mock_refund_instance = MagicMock()
        mock_refund_instance.id = 'refund-id-123'
        mock_refund_instance.status = 'pending'
        mock_refund_instance.amount.value = '1000.00'

        mock_refund.create.return_value = mock_refund_instance

        service = get_yookassa_service()
        result = service.create_refund(
            payment_id='payment-id-123',
            amount=Decimal('1000.00'),
            reason='Test refund'
        )

        # Проверяем результат
        assert result['refund_id'] == 'refund-id-123'
        assert result['status'] == 'pending'
        assert result['amount'] == Decimal('1000.00')

        # Проверяем что метод был вызван
        mock_refund.create.assert_called_once()


@pytest.mark.patterns
class TestSingletonPatternComparison:
    """Тесты демонстрирующие разницу между Singleton и обычным классом"""

    def test_regular_class_creates_multiple_instances(self):
        """Демонстрация: обычный класс создаёт новые экземпляры"""

        class RegularService:
            def __init__(self):
                self.value = 0

        # Каждый вызов создаёт новый экземпляр
        service1 = RegularService()
        service2 = RegularService()

        # Это РАЗНЫЕ объекты
        assert service1 is not service2
        assert id(service1) != id(service2)

        # Изменения в одном не влияют на другой
        service1.value = 10
        assert service2.value == 0

    def test_singleton_maintains_single_instance(self):
        """Демонстрация: Singleton поддерживает единственный экземпляр"""

        # Множественные вызовы
        service1 = get_yookassa_service()
        service2 = get_yookassa_service()

        # Это ОДИН И ТОТ ЖЕ объект
        assert service1 is service2
        assert id(service1) == id(service2)

    def test_singleton_use_case_explanation(self):
        """
        Объяснение зачем нужен Singleton для YooKassaService:

        1. YooKassaService требует инициализации с credentials (shop_id, secret_key)
        2. Нам не нужно создавать множество экземпляров
        3. Один экземпляр экономит ресурсы
        4. Гарантирует единую точку доступа к API
        5. Упрощает управление конфигурацией
        """

        # Получаем сервис из разных мест приложения
        service_from_view = get_yookassa_service()
        service_from_serializer = get_yookassa_service()
        service_from_webhook = get_yookassa_service()

        # Все работают с ОДНИМ экземпляром
        # Это значит одна инициализация, одна конфигурация, один API клиент
        assert service_from_view is service_from_serializer
        assert service_from_serializer is service_from_webhook

        # Преимущества:
        # ✅ Экономия памяти
        # ✅ Единая конфигурация
        # ✅ Предсказуемое поведение
        # ✅ Упрощённое тестирование (один mock для всех)
        assert True  # Test passes demonstrating the pattern
