"""
Management command to create test data for Sprint 3 demo
Creates ClassTypes, Rooms, Trainers, and Classes with schedule
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from decimal import Decimal

from apps.accounts.models import Profile, Trainer, Client, UserRole
from apps.classes.models import ClassType, Class
from apps.facilities.models import Room
from apps.memberships.models import MembershipType, Membership, MembershipStatus
from core.patterns.factory import ClassFactory


class Command(BaseCommand):
    help = 'Create test data for Sprint 3 demonstration'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('\n===== Создание тестовых данных для Спринта 3 =====\n'))

        # 1. Create ClassTypes
        self.stdout.write('Создание типов занятий...')
        class_types_data = [
            {'name': 'Йога', 'description': 'Расслабляющая йога для всех уровней', 'duration_minutes': 60},
            {'name': 'Фитнес', 'description': 'Силовые тренировки и кардио', 'duration_minutes': 90},
            {'name': 'Бокс', 'description': 'Тренировки по боксу для начинающих и продвинутых', 'duration_minutes': 60},
            {'name': 'Плавание', 'description': 'Групповые занятия в бассейне', 'duration_minutes': 45},
            {'name': 'Пилатес', 'description': 'Пилатес для укрепления мышц', 'duration_minutes': 60},
            {'name': 'Зумба', 'description': 'Танцевальная фитнес-программа', 'duration_minutes': 60},
        ]

        for data in class_types_data:
            class_type, created = ClassType.objects.get_or_create(
                name=data['name'],
                defaults={'description': data['description'], 'duration_minutes': data['duration_minutes']}
            )
            if created:
                self.stdout.write(f'  ✓ Создан: {class_type.name}')

        # 2. Create Rooms
        self.stdout.write('\nСоздание залов...')
        rooms_data = [
            {'name': 'Зал №1 (Йога)', 'capacity': 15, 'floor': 1, 'equipment': 'Коврики, блоки, ремни'},
            {'name': 'Зал №2 (Фитнес)', 'capacity': 20, 'floor': 1, 'equipment': 'Гантели, штанги, тренажеры'},
            {'name': 'Зал №3 (Бокс)', 'capacity': 10, 'floor': 2, 'equipment': 'Ринг, груши, перчатки'},
            {'name': 'Бассейн', 'capacity': 12, 'floor': 0, 'equipment': '25м бассейн, дорожки'},
        ]

        for data in rooms_data:
            room, created = Room.objects.get_or_create(
                name=data['name'],
                defaults={
                    'capacity': data['capacity'],
                    'floor': data['floor'],
                    'equipment': data['equipment']
                }
            )
            if created:
                self.stdout.write(f'  ✓ Создан: {room.name}')

        # 3. Create Trainers
        self.stdout.write('\nСоздание тренеров...')
        trainers_data = [
            {'username': 'trainer_anna', 'first_name': 'Анна', 'last_name': 'Иванова',
             'phone': '+79161234567', 'specialization': 'Йога и пилатес', 'experience_years': 5},
            {'username': 'trainer_ivan', 'first_name': 'Иван', 'last_name': 'Петров',
             'phone': '+79161234568', 'specialization': 'Фитнес и кроссфит', 'experience_years': 7},
            {'username': 'trainer_sergey', 'first_name': 'Сергей', 'last_name': 'Смирнов',
             'phone': '+79161234569', 'specialization': 'Бокс', 'experience_years': 10},
        ]

        for data in trainers_data:
            user, user_created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': f"{data['username']}@example.com"
                }
            )
            if user_created:
                user.set_password('password123')
                user.save()

            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={'phone': data['phone'], 'role': UserRole.TRAINER}
            )

            trainer, created = Trainer.objects.get_or_create(
                profile=profile,
                defaults={
                    'specialization': data['specialization'],
                    'experience_years': data['experience_years'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'  ✓ Создан: {trainer}')

        # 4. Create Classes (schedule for next 7 days)
        self.stdout.write('\nСоздание расписания занятий...')

        yoga_type = ClassType.objects.get(name='Йога')
        fitness_type = ClassType.objects.get(name='Фитнес')
        boxing_type = ClassType.objects.get(name='Бокс')

        yoga_room = Room.objects.get(name='Зал №1 (Йога)')
        fitness_room = Room.objects.get(name='Зал №2 (Фитнес)')
        boxing_room = Room.objects.get(name='Зал №3 (Бокс)')

        trainer_anna = Trainer.objects.get(profile__user__username='trainer_anna')
        trainer_ivan = Trainer.objects.get(profile__user__username='trainer_ivan')
        trainer_sergey = Trainer.objects.get(profile__user__username='trainer_sergey')

        # Schedule pattern for the week
        schedule_pattern = [
            # Monday
            (0, 9, 0, yoga_type, trainer_anna, yoga_room),
            (0, 11, 0, fitness_type, trainer_ivan, fitness_room),
            (0, 18, 0, boxing_type, trainer_sergey, boxing_room),
            # Tuesday
            (1, 10, 0, yoga_type, trainer_anna, yoga_room),
            (1, 14, 0, fitness_type, trainer_ivan, fitness_room),
            (1, 19, 0, boxing_type, trainer_sergey, boxing_room),
            # Wednesday
            (2, 9, 0, fitness_type, trainer_ivan, fitness_room),
            (2, 17, 0, yoga_type, trainer_anna, yoga_room),
            (2, 18, 30, boxing_type, trainer_sergey, boxing_room),
            # Thursday
            (3, 11, 0, yoga_type, trainer_anna, yoga_room),
            (3, 15, 0, fitness_type, trainer_ivan, fitness_room),
            (3, 19, 0, boxing_type, trainer_sergey, boxing_room),
            # Friday
            (4, 10, 0, yoga_type, trainer_anna, yoga_room),
            (4, 13, 0, fitness_type, trainer_ivan, fitness_room),
            (4, 18, 0, boxing_type, trainer_sergey, boxing_room),
        ]

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        classes_created = 0
        for day_offset, hour, minute, class_type, trainer, room in schedule_pattern:
            class_datetime = today_start + timedelta(days=day_offset, hours=hour, minutes=minute)

            # Skip past classes
            if class_datetime < now:
                continue

            try:
                class_instance = ClassFactory.create_class(
                    class_type=class_type,
                    trainer=trainer,
                    room=room,
                    datetime_obj=class_datetime,
                    check_conflicts=True,
                    save=True
                )
                classes_created += 1
                self.stdout.write(f'  ✓ Создано: {class_instance}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠ Пропущено: {e}'))

        # 5. Create membership types
        self.stdout.write('\nСоздание типов абонементов...')
        membership_types_data = [
            {'name': 'Разовое посещение', 'description': 'Одно посещение клуба', 'price': Decimal('500.00'), 'duration_days': 1, 'visits_limit': 1},
            {'name': '8 занятий', 'description': 'Абонемент на 8 посещений (30 дней)', 'price': Decimal('2400.00'), 'duration_days': 30, 'visits_limit': 8},
            {'name': '12 занятий', 'description': 'Абонемент на 12 посещений (30 дней)', 'price': Decimal('3200.00'), 'duration_days': 30, 'visits_limit': 12},
            {'name': 'Месячный безлимит', 'description': 'Безлимитный доступ на 30 дней', 'price': Decimal('4000.00'), 'duration_days': 30, 'visits_limit': None},
            {'name': '3 месяца безлимит', 'description': 'Безлимитный доступ на 90 дней', 'price': Decimal('10500.00'), 'duration_days': 90, 'visits_limit': None},
            {'name': 'Годовой безлимит', 'description': 'Безлимитный доступ на год', 'price': Decimal('36000.00'), 'duration_days': 365, 'visits_limit': None},
        ]

        for data in membership_types_data:
            membership_type, created = MembershipType.objects.get_or_create(
                name=data['name'],
                defaults={
                    'description': data['description'],
                    'price': data['price'],
                    'duration_days': data['duration_days'],
                    'visits_limit': data['visits_limit']
                }
            )
            if created:
                self.stdout.write(f'  ✓ Создан: {membership_type.name} - {membership_type.price} руб.')

        # 6. Create some clients with memberships
        self.stdout.write('\nСоздание клиентов и абонементов...')

        monthly_unlimited = MembershipType.objects.get(name='Месячный безлимит')

        clients_data = [
            {'username': 'client_maria', 'first_name': 'Мария', 'last_name': 'Сидорова', 'phone': '+79161234570', 'is_student': True},
            {'username': 'client_alex', 'first_name': 'Алексей', 'last_name': 'Кузнецов', 'phone': '+79161234571', 'is_student': False},
        ]

        for data in clients_data:
            user, user_created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': f"{data['username']}@example.com"
                }
            )
            if user_created:
                user.set_password('password123')
                user.save()

            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={'phone': data['phone'], 'role': UserRole.CLIENT}
            )

            client, client_created = Client.objects.get_or_create(
                profile=profile,
                defaults={'is_student': data['is_student']}
            )

            # Create active membership
            if client_created:
                Membership.objects.get_or_create(
                    client=client,
                    membership_type=membership_type,
                    defaults={
                        'start_date': now.date(),
                        'end_date': (now + timedelta(days=30)).date(),
                        'status': MembershipStatus.ACTIVE
                    }
                )
                self.stdout.write(f'  ✓ Создан: {client} с абонементом')

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n===== Готово! ====='))
        self.stdout.write(f'Типов занятий: {ClassType.objects.count()}')
        self.stdout.write(f'Залов: {Room.objects.count()}')
        self.stdout.write(f'Тренеров: {Trainer.objects.count()}')
        self.stdout.write(f'Занятий в расписании: {Class.objects.count()}')
        self.stdout.write(f'Клиентов: {Client.objects.count()}')
        self.stdout.write(self.style.SUCCESS('\nДанные успешно созданы! 🎉\n'))
