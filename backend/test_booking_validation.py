#!/usr/bin/env python
"""
Тест валидации бронирований
"""

import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.core.exceptions import ValidationError
from apps.accounts.models import Client
from apps.bookings.models import Booking
from apps.classes.models import Class
from apps.memberships.models import Membership

print("="*60)
print("Тест валидации бронирований")
print("="*60)

# Находим клиента с абонементом
client = Client.objects.filter(memberships__isnull=False).first()
if not client:
    print("❌ Нет клиентов с абонементами")
    exit(1)

membership = client.memberships.first()
print(f"\n📋 Клиент: {client}")
print(f"📅 Абонемент действует: {membership.start_date} - {membership.end_date}")
print(f"✅ Статус: {membership.get_status_display()}")

# Находим занятие ЗА ПРЕДЕЛАМИ срока действия абонемента
future_class = Class.objects.filter(
    datetime__date__gt=membership.end_date
).order_by('datetime').first()

if not future_class:
    print("\n⚠ Нет занятий за пределами срока действия абонемента")
    exit(0)

print(f"\n🎯 Попытка забронировать занятие:")
print(f"   Занятие: {future_class.class_type.name}")
print(f"   Дата: {future_class.datetime.date()}")
print(f"   (За пределами абонемента: {future_class.datetime.date()} > {membership.end_date})")

# Пытаемся создать бронирование
try:
    booking = Booking(
        client=client,
        class_instance=future_class,
        status='CONFIRMED'
    )
    # Вызываем валидацию
    booking.full_clean()  # Это вызовет метод clean()
    booking.save()
    print("\n❌ ОШИБКА: Бронирование создано без валидации!")
    print(f"   Booking ID: {booking.id}")
except ValidationError as e:
    print("\n✅ УСПЕХ: Валидация сработала!")
    print(f"   Ошибка: {e.message_dict}")
except Exception as e:
    print(f"\n❓ Неожиданная ошибка: {e}")

# Проверяем, что бронирование НЕ создано
booking_exists = Booking.objects.filter(
    client=client,
    class_instance=future_class
).exists()

if booking_exists:
    print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Бронирование создалось в БД!")
else:
    print("\n✅ Подтверждено: Бронирование НЕ создано в БД")

print("\n" + "="*60)
print("Тест завершён")
print("="*60)
