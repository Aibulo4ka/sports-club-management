#!/usr/bin/env python
"""
Скрипт для тестирования интеграции с ЮKassa

Использование:
    python test_yookassa_integration.py

Требования:
    - Запущенный сервер Django
    - Настроенные YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY в .env
    - Созданный тестовый клиент
"""

import os
import sys
import django
import requests
from decimal import Decimal

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.payments.yookassa_service import get_yookassa_service
from apps.payments.models import Payment, PaymentStatus
from apps.accounts.models import Client
from apps.memberships.models import MembershipType


def test_yookassa_service():
    """
    Тест 1: Проверка работы YooKassaService
    """
    print("\n" + "="*60)
    print("ТЕСТ 1: Проверка YooKassaService")
    print("="*60)

    try:
        yookassa = get_yookassa_service()
        print("✅ YooKassaService инициализирован")

        # Тестируем создание платежа
        test_payment = yookassa.create_payment(
            amount=Decimal('1000.00'),
            description="Тестовый платёж",
            client_email="test@example.com",
            return_url="http://localhost:8000/payments/success/",
            metadata={"test": "true"}
        )

        print(f"✅ Платёж создан в YooKassa:")
        print(f"   - Payment ID: {test_payment['payment_id']}")
        print(f"   - URL: {test_payment['confirmation_url'][:50]}...")
        print(f"   - Status: {test_payment['status']}")
        print(f"   - Test mode: {test_payment['test']}")

        # Проверяем статус
        status_info = yookassa.check_payment_status(test_payment['payment_id'])
        print(f"✅ Статус проверен:")
        print(f"   - Status: {status_info['status']}")
        print(f"   - Paid: {status_info['paid']}")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        return False


def test_payment_creation_api():
    """
    Тест 2: Создание платежа через API
    """
    print("\n" + "="*60)
    print("ТЕСТ 2: Создание платежа через API")
    print("="*60)

    try:
        # Проверяем наличие тестового клиента
        client = Client.objects.select_related('profile__user').first()
        if not client:
            print("❌ Не найден тестовый клиент. Создайте клиента командой:")
            print("   python manage.py create_test_client")
            return False

        print(f"✅ Тестовый клиент: {client.profile.user.get_full_name()}")

        # Проверяем наличие типа абонемента
        membership_type = MembershipType.objects.filter(is_active=True).first()
        if not membership_type:
            print("❌ Не найден активный тип абонемента")
            return False

        print(f"✅ Тип абонемента: {membership_type.name} - {membership_type.price} руб.")

        # Создаём платёж напрямую через сериализатор (эмулируя API)
        from apps.payments.serializers import PaymentCreateSerializer

        serializer = PaymentCreateSerializer(
            data={
                'membership_type_id': membership_type.id,
                'payment_method': 'YOOKASSA'
            },
            context={'client': client}
        )

        if serializer.is_valid():
            payment = serializer.save()
            print(f"✅ Платёж создан:")
            print(f"   - ID: {payment.id}")
            print(f"   - Сумма: {payment.amount} руб.")
            print(f"   - YooKassa ID: {payment.transaction_id}")
            print(f"   - URL для оплаты: {payment.payment_url[:60]}...")
            print(f"   - Статус: {payment.get_status_display()}")
            return True
        else:
            print(f"❌ Ошибка валидации: {serializer.errors}")
            return False

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_webhook_simulation():
    """
    Тест 3: Симуляция webhook от YooKassa
    """
    print("\n" + "="*60)
    print("ТЕСТ 3: Симуляция webhook")
    print("="*60)

    try:
        # Находим последний созданный платёж
        payment = Payment.objects.filter(
            payment_method='YOOKASSA',
            status=PaymentStatus.PENDING
        ).first()

        if not payment:
            print("❌ Не найден платёж со статусом PENDING")
            return False

        print(f"✅ Платёж для теста: {payment.id}")

        # Симулируем webhook данные от YooKassa
        webhook_data = {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": payment.transaction_id,
                "status": "succeeded",
                "paid": True,
                "amount": {
                    "value": str(payment.amount),
                    "currency": "RUB"
                },
                "metadata": {
                    "payment_id": str(payment.id),
                    "client_id": str(payment.client.id),
                    "membership_id": str(payment.membership.id) if payment.membership else None
                }
            }
        }

        # Обрабатываем webhook
        from apps.payments.yookassa_service import get_yookassa_service
        yookassa = get_yookassa_service()
        result = yookassa.process_webhook(webhook_data)

        print(f"✅ Webhook обработан:")
        print(f"   - Payment ID: {result['payment_id']}")
        print(f"   - Status: {result['status']}")
        print(f"   - Paid: {result['paid']}")

        # Проверяем, что статус обновился в БД
        payment.refresh_from_db()
        print(f"✅ Статус платежа обновлён: {payment.get_status_display()}")

        if payment.membership:
            payment.membership.refresh_from_db()
            print(f"✅ Статус абонемента: {payment.membership.get_status_display()}")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def print_summary():
    """
    Вывод статистики по платежам
    """
    print("\n" + "="*60)
    print("СТАТИСТИКА ПЛАТЕЖЕЙ")
    print("="*60)

    total = Payment.objects.count()
    pending = Payment.objects.filter(status=PaymentStatus.PENDING).count()
    completed = Payment.objects.filter(status=PaymentStatus.COMPLETED).count()
    failed = Payment.objects.filter(status=PaymentStatus.FAILED).count()

    print(f"Всего платежей: {total}")
    print(f"  - Ожидают оплаты: {pending}")
    print(f"  - Завершённых: {completed}")
    print(f"  - Ошибок: {failed}")

    # Последние платежи
    recent_payments = Payment.objects.select_related(
        'client__profile__user'
    ).order_by('-created_at')[:5]

    if recent_payments:
        print("\nПоследние 5 платежей:")
        for p in recent_payments:
            print(f"  {p.id}. {p.client.profile.user.get_full_name()} - "
                  f"{p.amount} руб. - {p.get_status_display()}")


def main():
    """
    Главная функция
    """
    print("\n" + "🚀 " + "="*56)
    print("  ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С ЮKASSA")
    print("="*58)

    # Проверяем переменные окружения
    from django.conf import settings

    if not settings.YOOKASSA_SHOP_ID or settings.YOOKASSA_SHOP_ID == 'your-shop-id':
        print("\n❌ ОШИБКА: Не настроен YOOKASSA_SHOP_ID в .env файле")
        print("   Получите тестовые данные на https://yookassa.ru/")
        return

    if not settings.YOOKASSA_SECRET_KEY or settings.YOOKASSA_SECRET_KEY == 'your-secret-key':
        print("\n❌ ОШИБКА: Не настроен YOOKASSA_SECRET_KEY в .env файле")
        return

    print(f"\n✅ Shop ID: {settings.YOOKASSA_SHOP_ID[:10]}***")

    # Запускаем тесты
    results = []

    results.append(("YooKassaService", test_yookassa_service()))
    results.append(("API создание платежа", test_payment_creation_api()))
    results.append(("Webhook симуляция", test_webhook_simulation()))

    # Итоги
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("="*60)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30} {status}")

    print_summary()

    passed = sum(1 for _, result in results if result)
    total_tests = len(results)

    print(f"\n{'='*60}")
    print(f"Пройдено: {passed}/{total_tests} тестов")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
