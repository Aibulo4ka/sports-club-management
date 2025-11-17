#!/usr/bin/env python
"""
Скрипт для наполнения БД занятиями на конец недели и клиентами с бронированиями
Создает занятия на пятницу-воскресенье с разной заполненностью (30%, 50%, 70%)
"""

import os
import django
from datetime import datetime, timedelta, date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Profile, Client, Trainer, UserRole
from apps.memberships.models import MembershipType, Membership, MembershipStatus
from apps.classes.models import ClassType, Class, ClassStatus
from apps.facilities.models import Room
from apps.bookings.models import Booking, BookingStatus


def get_next_weekday(target_day):
    """
    Получить дату следующего дня недели
    target_day: 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
    """
    today = date.today()
    days_ahead = target_day - today.weekday()
    if days_ahead <= 0:  # Если день уже прошел на этой неделе
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def create_weekend_classes():
    """Создать занятия на пятницу, субботу, воскресенье"""
    print("\n=== Создание занятий на конец недели ===")

    # Получаем типы занятий, залы, тренеров
    yoga = ClassType.objects.get(name='Йога')
    fitness = ClassType.objects.get(name='Фитнес')
    boxing = ClassType.objects.get(name='Бокс')

    room1 = Room.objects.get(name='Зал №1 (Йога)')
    room2 = Room.objects.get(name='Зал №2 (Фитнес)')
    room3 = Room.objects.get(name='Зал №3 (Бокс)')

    trainer1 = Trainer.objects.filter(profile__user__username='trainer_anna').first()
    trainer2 = Trainer.objects.filter(profile__user__username='trainer_ivan').first()
    trainer3 = Trainer.objects.filter(profile__user__username='trainer_sergey').first()

    # Даты: пятница, суббота, воскресенье
    friday = get_next_weekday(4)  # 4 = Friday
    saturday = get_next_weekday(5)  # 5 = Saturday
    sunday = get_next_weekday(6)  # 6 = Sunday

    classes_to_create = [
        # Пятница
        {
            'class_type': yoga,
            'trainer': trainer1,
            'room': room1,
            'datetime': datetime.combine(friday, datetime.min.time()).replace(hour=10, minute=0),
            'duration': 60,
            'capacity': 20,  # Будет заполнено на 30% (6 из 20)
            'target_fill': 0.3
        },
        {
            'class_type': fitness,
            'trainer': trainer2,
            'room': room2,
            'datetime': datetime.combine(friday, datetime.min.time()).replace(hour=18, minute=0),
            'duration': 90,
            'capacity': 25,  # Будет заполнено на 50% (12-13 из 25)
            'target_fill': 0.5
        },
        {
            'class_type': boxing,
            'trainer': trainer3,
            'room': room3,
            'datetime': datetime.combine(friday, datetime.min.time()).replace(hour=19, minute=30),
            'duration': 60,
            'capacity': 15,  # Будет заполнено на 70% (10-11 из 15)
            'target_fill': 0.7
        },

        # Суббота
        {
            'class_type': yoga,
            'trainer': trainer1,
            'room': room1,
            'datetime': datetime.combine(saturday, datetime.min.time()).replace(hour=9, minute=0),
            'duration': 60,
            'capacity': 20,
            'target_fill': 0.5
        },
        {
            'class_type': fitness,
            'trainer': trainer2,
            'room': room2,
            'datetime': datetime.combine(saturday, datetime.min.time()).replace(hour=11, minute=0),
            'duration': 90,
            'capacity': 30,
            'target_fill': 0.3
        },
        {
            'class_type': boxing,
            'trainer': trainer3,
            'room': room3,
            'datetime': datetime.combine(saturday, datetime.min.time()).replace(hour=17, minute=0),
            'duration': 60,
            'capacity': 12,
            'target_fill': 0.7
        },

        # Воскресенье
        {
            'class_type': yoga,
            'trainer': trainer1,
            'room': room1,
            'datetime': datetime.combine(sunday, datetime.min.time()).replace(hour=10, minute=0),
            'duration': 60,
            'capacity': 18,
            'target_fill': 0.5
        },
        {
            'class_type': fitness,
            'trainer': trainer2,
            'room': room2,
            'datetime': datetime.combine(sunday, datetime.min.time()).replace(hour=12, minute=0),
            'duration': 90,
            'capacity': 25,
            'target_fill': 0.3
        },
        {
            'class_type': boxing,
            'trainer': trainer3,
            'room': room3,
            'datetime': datetime.combine(sunday, datetime.min.time()).replace(hour=18, minute=0),
            'duration': 60,
            'capacity': 15,
            'target_fill': 0.5
        },
    ]

    created_classes = []
    for class_data in classes_to_create:
        # Проверяем, нет ли уже такого занятия
        existing = Class.objects.filter(
            class_type=class_data['class_type'],
            datetime=class_data['datetime']
        ).first()

        if existing:
            print(f"  ⚠ Занятие уже существует: {class_data['class_type'].name} - {class_data['datetime']}")
            created_classes.append((existing, class_data['target_fill']))
            continue

        new_class = Class.objects.create(
            class_type=class_data['class_type'],
            trainer=class_data['trainer'],
            room=class_data['room'],
            datetime=class_data['datetime'],
            duration_minutes=class_data['duration'],
            max_capacity=class_data['capacity'],
            status=ClassStatus.SCHEDULED
        )
        print(f"  ✓ Создано: {new_class.class_type.name} - {new_class.datetime.strftime('%d.%m.%Y %H:%M')} (вместимость: {class_data['capacity']})")
        created_classes.append((new_class, class_data['target_fill']))

    return created_classes


def create_clients_with_memberships(count=20):
    """Создать клиентов с активными абонементами"""
    print(f"\n=== Создание {count} клиентов с активными абонементами ===")

    # Получаем типы абонементов
    membership_types = list(MembershipType.objects.filter(is_active=True))

    if not membership_types:
        print("  ⚠ Нет активных типов абонементов!")
        return []

    created_clients = []

    for i in range(count):
        username = f'client_{i+1}'

        # Проверяем, существует ли уже такой пользователь
        existing_user = User.objects.filter(username=username).first()
        if existing_user:
            # Проверяем, есть ли у него активный абонемент
            try:
                client = existing_user.profile.client_info
                active_membership = client.memberships.filter(status=MembershipStatus.ACTIVE).first()
                if active_membership:
                    created_clients.append(client)
                    continue
            except:
                pass

        # Создаём нового пользователя
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': f'Клиент{i+1}',
                'last_name': 'Тестовый'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()

        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'role': UserRole.CLIENT,
                'phone': f'+7999{i+1:07d}'
            }
        )

        client, _ = Client.objects.get_or_create(
            profile=profile,
            defaults={
                'is_student': (i % 3 == 0)  # Каждый третий - студент
            }
        )

        # Создаём активный абонемент
        membership_type = membership_types[i % len(membership_types)]
        membership = Membership.objects.create(
            client=client,
            membership_type=membership_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=membership_type.duration_days),
            status=MembershipStatus.ACTIVE,
            visits_remaining=membership_type.visits_limit
        )

        created_clients.append(client)

    print(f"  ✓ Создано {len(created_clients)} клиентов с активными абонементами")
    return created_clients


def create_bookings_with_fill_rate(classes_with_targets, clients):
    """Создать бронирования с заданной заполненностью"""
    print("\n=== Создание бронирований ===")

    import random

    total_bookings = 0

    for class_instance, target_fill in classes_with_targets:
        # Рассчитываем количество бронирований
        target_count = int(class_instance.max_capacity * target_fill)

        # Перемешиваем клиентов
        available_clients = list(clients)
        random.shuffle(available_clients)

        booked_count = 0
        for client in available_clients[:target_count]:
            # Проверяем, нет ли уже бронирования
            existing = Booking.objects.filter(
                client=client,
                class_instance=class_instance
            ).first()

            if existing:
                booked_count += 1
                continue

            # Создаём бронирование
            Booking.objects.create(
                client=client,
                class_instance=class_instance,
                status=BookingStatus.CONFIRMED
            )
            booked_count += 1
            total_bookings += 1

        fill_percentage = (booked_count / class_instance.max_capacity) * 100
        print(f"  ✓ {class_instance.class_type.name} ({class_instance.datetime.strftime('%d.%m %H:%M')}): "
              f"{booked_count}/{class_instance.max_capacity} мест ({fill_percentage:.0f}%)")

    print(f"\n  Всего создано бронирований: {total_bookings}")
    return total_bookings


def main():
    print("="*60)
    print("Наполнение БД занятиями на конец недели")
    print("="*60)

    # 1. Создаём занятия на пятницу-воскресенье
    classes = create_weekend_classes()

    # 2. Создаём клиентов с активными абонементами
    clients = create_clients_with_memberships(count=20)

    # 3. Создаём бронирования с разной заполненностью
    bookings_count = create_bookings_with_fill_rate(classes, clients)

    print("\n" + "="*60)
    print("✅ Готово!")
    print("="*60)
    print(f"Занятий создано: {len(classes)}")
    print(f"Клиентов с абонементами: {len(clients)}")
    print(f"Бронирований создано: {bookings_count}")
    print("\nТеперь можно проверить заполненность занятий на фронтенде:")
    print("  → Расписание: http://localhost:8000/classes/schedule/")
    print("  → Мои бронирования: http://localhost:8000/bookings/my/")


if __name__ == '__main__':
    main()
