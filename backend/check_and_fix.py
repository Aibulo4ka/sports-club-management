#!/usr/bin/env python
"""
Скрипт для проверки и исправления данных
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Profile, Client, UserRole

print("=" * 60)
print("🔍 ДИАГНОСТИКА ПРОБЛЕМ")
print("=" * 60)

# 1. Проверка пользователя client1
print("\n1️⃣ Проверка пользователя client1:")
print("-" * 60)
try:
    user = User.objects.get(username='client1')
    print(f"✅ User найден: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Активен: {user.is_active}")
    print(f"   Проверка пароля с 'client123':", user.check_password('client123'))

    # Проверка профиля
    try:
        profile = user.profile
        print(f"✅ Profile найден: {profile.role}")
        print(f"   Телефон: {profile.phone}")

        # Проверка клиента
        try:
            client = profile.client_info
            print(f"✅ Client найден!")
            print(f"   Студент: {client.is_student}")
        except Exception as e:
            print(f"❌ Client не найден: {e}")
            print("   Создаю Client...")
            client = Client.objects.create(profile=profile, is_student=False)
            print("   ✅ Client создан!")

    except Exception as e:
        print(f"❌ Profile не найден: {e}")

except User.DoesNotExist:
    print("❌ Пользователь client1 не найден!")
    print("   Запустите create_test_data.py для создания тестовых данных")

# 2. Проверка пользователя student1
print("\n2️⃣ Проверка пользователя student1:")
print("-" * 60)
try:
    user = User.objects.get(username='student1')
    print(f"✅ User найден: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Активен: {user.is_active}")
    print(f"   Проверка пароля с 'student123':", user.check_password('student123'))

    # Проверка профиля
    try:
        profile = user.profile
        print(f"✅ Profile найден: {profile.role}")
        print(f"   Телефон: {profile.phone}")

        # Проверка клиента
        try:
            client = profile.client_info
            print(f"✅ Client найден!")
            print(f"   🎓 Студент: {client.is_student}")

            if not client.is_student:
                print("   ⚠️  is_student = False! Исправляю...")
                client.is_student = True
                client.save()
                print("   ✅ is_student установлен в True")

        except Exception as e:
            print(f"❌ Client не найден: {e}")
            print("   Создаю Client со статусом студента...")
            client = Client.objects.create(profile=profile, is_student=True)
            print("   ✅ Client создан!")

    except Exception as e:
        print(f"❌ Profile не найден: {e}")

except User.DoesNotExist:
    print("❌ Пользователь student1 не найден!")
    print("   Запустите create_test_data.py для создания тестовых данных")

# 3. Проверка связей в модели
print("\n3️⃣ Проверка модели Client:")
print("-" * 60)
from apps.accounts.models import Client as ClientModel
field = ClientModel._meta.get_field('profile')
print(f"Related name: {field.remote_field.related_name}")
if field.remote_field.related_name == 'client_info':
    print("✅ related_name правильный (client_info)")
else:
    print(f"⚠️  related_name = {field.remote_field.related_name}, ожидается 'client_info'")

# 4. Проверка типов абонементов
print("\n4️⃣ Проверка типов абонементов:")
print("-" * 60)
from apps.memberships.models import MembershipType
types = MembershipType.objects.filter(is_active=True)
if types.exists():
    print(f"✅ Найдено {types.count()} активных типов абонементов:")
    for mt in types:
        print(f"   - {mt.name}: {mt.price} руб. ({mt.duration_days} дней)")
else:
    print("❌ Типы абонементов не найдены!")
    print("   Запустите create_test_data.py")

# 5. Тест расчета скидки
print("\n5️⃣ Тест расчета скидки для студента:")
print("-" * 60)
try:
    user = User.objects.get(username='student1')
    client = user.profile.client_info

    from apps.memberships.pricing import get_best_discount_strategy, PriceCalculator
    from decimal import Decimal

    # Тест на месячном абонементе
    base_price = Decimal('3000.00')
    duration_days = 30

    print(f"Базовая цена: {base_price} руб.")
    print(f"Клиент - студент: {client.is_student}")
    print(f"Длительность: {duration_days} дней")

    strategy = get_best_discount_strategy(
        is_student=client.is_student,
        duration_days=duration_days
    )

    print(f"Выбранная стратегия: {strategy.__class__.__name__}")
    print(f"Описание: {strategy.get_description()}")

    calculator = PriceCalculator(strategy)
    price_info = calculator.calculate_final_price(
        base_price=base_price,
        duration_days=duration_days,
        is_student=client.is_student
    )

    print(f"\n💰 Результат расчета:")
    print(f"   Базовая цена: {price_info['base_price']} руб.")
    print(f"   Скидка: {price_info['discount_amount']} руб. ({price_info['discount_percentage']}%)")
    print(f"   Итого к оплате: {price_info['final_price']} руб.")
    print(f"   Описание: {price_info['discount_description']}")

    if price_info['final_price'] == Decimal('2550.00'):
        print("\n✅ СКИДКА РАБОТАЕТ ПРАВИЛЬНО!")
    else:
        print(f"\n❌ ОШИБКА! Ожидалось 2550 руб., получено {price_info['final_price']} руб.")

except Exception as e:
    print(f"❌ Ошибка при тесте: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
print("=" * 60)
