#!/usr/bin/env python
"""
Скрипт для создания тестовых данных для проверки системы платежей
Запуск: python3 manage.py shell < create_test_data.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Profile, Client, Trainer, UserRole
from apps.memberships.models import MembershipType, Membership, MembershipStatus
from apps.facilities.models import Room
from apps.classes.models import ClassType, Class
from apps.payments.models import Payment, PaymentStatus, PaymentMethod
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.utils import timezone

print("🚀 Создание тестовых данных для системы платежей...")
print("=" * 60)

# 1. Создаем суперпользователя (если не существует)
print("\n1️⃣ Создание суперпользователя...")
if not User.objects.filter(username='admin').exists():
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@sportclub.ru',
        password='admin123',
        first_name='Администратор',
        last_name='Системы'
    )
    Profile.objects.create(
        user=admin_user,
        role=UserRole.ADMIN,
        phone='+79991234567'
    )
    print("✅ Суперпользователь создан: admin / admin123")
else:
    print("ℹ️  Суперпользователь уже существует")

# 2. Создаем тестового клиента (обычный)
print("\n2️⃣ Создание тестового клиента...")
if not User.objects.filter(username='client1').exists():
    client_user = User.objects.create_user(
        username='client1',
        email='client1@example.com',
        password='client123',
        first_name='Иван',
        last_name='Иванов'
    )
    profile = Profile.objects.create(
        user=client_user,
        role=UserRole.CLIENT,
        phone='+79991234568',
        date_of_birth=date(1995, 5, 15)
    )
    client = Client.objects.create(
        profile=profile,
        is_student=False,
        emergency_contact='Мария Иванова',
        emergency_phone='+79991234569'
    )
    print("✅ Клиент создан: client1 / client123 (обычный)")
else:
    print("ℹ️  Клиент client1 уже существует")

# 3. Создаем тестового студента (для скидки)
print("\n3️⃣ Создание тестового студента...")
if not User.objects.filter(username='student1').exists():
    student_user = User.objects.create_user(
        username='student1',
        email='student1@example.com',
        password='student123',
        first_name='Петр',
        last_name='Петров'
    )
    profile = Profile.objects.create(
        user=student_user,
        role=UserRole.CLIENT,
        phone='+79991234570',
        date_of_birth=date(2003, 8, 20)
    )
    student = Client.objects.create(
        profile=profile,
        is_student=True,  # Студент - получит скидку 15%
        emergency_contact='Анна Петрова',
        emergency_phone='+79991234571'
    )
    print("✅ Студент создан: student1 / student123 (студент, скидка 15%)")
else:
    print("ℹ️  Студент student1 уже существует")

# 4. Создаем тренера
print("\n4️⃣ Создание тестового тренера...")
if not User.objects.filter(username='trainer1').exists():
    trainer_user = User.objects.create_user(
        username='trainer1',
        email='trainer1@sportclub.ru',
        password='trainer123',
        first_name='Сергей',
        last_name='Тренеров'
    )
    profile = Profile.objects.create(
        user=trainer_user,
        role=UserRole.TRAINER,
        phone='+79991234572'
    )
    trainer = Trainer.objects.create(
        profile=profile,
        specialization='Фитнес, Йога',
        experience_years=5,
        bio='Опытный тренер по фитнесу и йоге',
        is_active=True
    )
    print("✅ Тренер создан: trainer1 / trainer123")
else:
    print("ℹ️  Тренер trainer1 уже существует")

# 5. Создаем типы абонементов
print("\n5️⃣ Создание типов абонементов...")
membership_types = [
    {
        'name': 'Месячный',
        'description': 'Абонемент на 1 месяц, 12 посещений',
        'price': Decimal('3000.00'),
        'duration_days': 30,
        'visits_limit': 12,
    },
    {
        'name': 'Квартальный',
        'description': 'Абонемент на 3 месяца, 36 посещений (скидка 10%)',
        'price': Decimal('8100.00'),
        'duration_days': 90,
        'visits_limit': 36,
    },
    {
        'name': 'Полугодовой',
        'description': 'Абонемент на 6 месяцев, безлимит (скидка 15%)',
        'price': Decimal('15300.00'),
        'duration_days': 180,
        'visits_limit': None,  # Безлимит
    },
    {
        'name': 'Годовой',
        'description': 'Абонемент на 1 год, безлимит (скидка 20%)',
        'price': Decimal('28800.00'),
        'duration_days': 365,
        'visits_limit': None,  # Безлимит
    },
]

for mt_data in membership_types:
    mt, created = MembershipType.objects.get_or_create(
        name=mt_data['name'],
        defaults=mt_data
    )
    if created:
        print(f"  ✅ {mt.name}: {mt.price} руб. ({mt.duration_days} дней)")
    else:
        print(f"  ℹ️  {mt.name} уже существует")

# 6. Создаем залы
print("\n6️⃣ Создание залов...")
rooms_data = [
    {'name': 'Фитнес-зал №1', 'capacity': 20, 'description': 'Просторный зал с современным оборудованием'},
    {'name': 'Йога-студия', 'capacity': 15, 'description': 'Уютная студия для занятий йогой'},
]

for room_data in rooms_data:
    room, created = Room.objects.get_or_create(
        name=room_data['name'],
        defaults=room_data
    )
    if created:
        print(f"  ✅ {room.name} (вместимость: {room.capacity})")
    else:
        print(f"  ℹ️  {room.name} уже существует")

# 7. Создаем типы занятий
print("\n7️⃣ Создание типов занятий...")
class_types_data = [
    {'name': 'Фитнес', 'description': 'Групповые фитнес-тренировки', 'duration_minutes': 60},
    {'name': 'Йога', 'description': 'Занятия йогой для всех уровней', 'duration_minutes': 90},
]

for ct_data in class_types_data:
    ct, created = ClassType.objects.get_or_create(
        name=ct_data['name'],
        defaults=ct_data
    )
    if created:
        print(f"  ✅ {ct.name} ({ct.duration_minutes} мин.)")
    else:
        print(f"  ℹ️  {ct.name} уже существует")

# 8. Создаем пример активного абонемента (если нужен для тестирования бронирований)
print("\n8️⃣ Создание примера активного абонемента...")
client1 = Client.objects.get(profile__user__username='client1')
monthly_type = MembershipType.objects.get(name='Месячный')

if not Membership.objects.filter(client=client1, status=MembershipStatus.ACTIVE).exists():
    active_membership = Membership.objects.create(
        client=client1,
        membership_type=monthly_type,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        status=MembershipStatus.ACTIVE,
        visits_remaining=12
    )
    print(f"  ✅ Активный абонемент для client1: {monthly_type.name}")
else:
    print("  ℹ️  Активный абонемент для client1 уже существует")

# 9. Создаем пример платежа
print("\n9️⃣ Создание примера платежа...")
if not Payment.objects.filter(client=client1).exists():
    payment = Payment.objects.create(
        client=client1,
        membership=active_membership,
        amount=monthly_type.price,
        status=PaymentStatus.COMPLETED,
        payment_method=PaymentMethod.CARD,
        completed_at=timezone.now(),
        notes="Тестовый платеж - месячный абонемент без скидки"
    )
    print(f"  ✅ Платеж создан: {payment.amount} руб. (статус: {payment.status})")
else:
    print("  ℹ️  Платеж для client1 уже существует")

print("\n" + "=" * 60)
print("✨ Тестовые данные успешно созданы!")
print("=" * 60)
print("\n📋 Учетные данные для тестирования:")
print("-" * 60)
print("👤 Администратор:")
print("   Login:    admin")
print("   Password: admin123")
print("   URL:      http://localhost:8000/admin")
print()
print("👤 Клиент (обычный):")
print("   Login:    client1")
print("   Password: client123")
print("   Скидка:   Нет")
print()
print("👤 Клиент (студент):")
print("   Login:    student1")
print("   Password: student123")
print("   Скидка:   15% (студенческая)")
print()
print("👤 Тренер:")
print("   Login:    trainer1")
print("   Password: trainer123")
print("-" * 60)
print("\n🎯 Что тестировать:")
print("1. Регистрация/вход: http://localhost:8000/login")
print("2. Каталог абонементов: http://localhost:8000/memberships/")
print("3. Покупка абонемента (проверка скидок)")
print("4. История платежей: http://localhost:8000/payments/my/")
print("5. API: http://localhost:8000/api/payments/")
print()
