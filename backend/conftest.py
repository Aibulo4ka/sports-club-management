"""
Pytest configuration and fixtures
Общие фикстуры для всех тестов
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from decimal import Decimal

from apps.accounts.models import Profile, Client, Trainer, UserRole
from apps.memberships.models import MembershipType, Membership, MembershipStatus
from apps.classes.models import ClassType, Class, ClassStatus
from apps.facilities.models import Room
from apps.bookings.models import Booking, BookingStatus
from apps.payments.models import Payment, PaymentStatus, PaymentMethod


# ============================================================================
# Database and Client Fixtures
# ============================================================================

@pytest.fixture(scope='function')
def api_client():
    """APIClient для тестирования REST API"""
    return APIClient()


@pytest.fixture(scope='function')
def authenticated_client(api_client, test_client_user):
    """APIClient с авторизованным клиентом"""
    api_client.force_authenticate(user=test_client_user)
    return api_client


@pytest.fixture(scope='function')
def admin_client(api_client, test_admin_user):
    """APIClient с авторизованным администратором"""
    api_client.force_authenticate(user=test_admin_user)
    return api_client


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user():
    """Базовый пользователь"""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )
    return user


@pytest.fixture
def test_client_user(test_user):
    """Пользователь-клиент с профилем"""
    profile, _ = Profile.objects.get_or_create(
        user=test_user,
        defaults={
            'role': UserRole.CLIENT,
            'phone': '+79991234567'
        }
    )
    client, _ = Client.objects.get_or_create(
        profile=profile,
        defaults={'is_student': False}
    )
    return test_user


@pytest.fixture
def test_student_user():
    """Пользователь-студент"""
    user, _ = User.objects.get_or_create(
        username='student',
        defaults={
            'email': 'student@example.com',
            'first_name': 'Student',
            'last_name': 'Test'
        }
    )
    if not user.has_usable_password():
        user.set_password('testpass123')
        user.save()

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            'role': UserRole.CLIENT,
            'phone': '+79991234568'
        }
    )
    client, _ = Client.objects.get_or_create(
        profile=profile,
        defaults={'is_student': True}
    )
    return user


@pytest.fixture
def test_trainer_user():
    """Пользователь-тренер"""
    user, _ = User.objects.get_or_create(
        username='trainer',
        defaults={
            'email': 'trainer@example.com',
            'first_name': 'Trainer',
            'last_name': 'Pro'
        }
    )
    if not user.has_usable_password():
        user.set_password('testpass123')
        user.save()

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            'role': UserRole.TRAINER,
            'phone': '+79991234569'
        }
    )
    trainer, _ = Trainer.objects.get_or_create(
        profile=profile,
        defaults={
            'specialization': 'Йога',
            'experience_years': 5
        }
    )
    return user


@pytest.fixture
def test_admin_user():
    """Пользователь-администратор"""
    user, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True
        }
    )
    if not user.has_usable_password():
        user.set_password('adminpass123')
        user.save()

    Profile.objects.get_or_create(
        user=user,
        defaults={
            'role': UserRole.ADMIN,
            'phone': '+79991234570'
        }
    )
    return user


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def test_client(test_client_user):
    """Client instance"""
    try:
        return test_client_user.profile.client_info
    except Client.DoesNotExist:
        # Если не существует, создаём
        return Client.objects.create(profile=test_client_user.profile)


@pytest.fixture
def test_trainer(test_trainer_user):
    """Trainer instance"""
    try:
        return test_trainer_user.profile.trainer_info
    except Trainer.DoesNotExist:
        # Если не существует, создаём
        return Trainer.objects.create(
            profile=test_trainer_user.profile,
            specialization='Йога',
            experience_years=5
        )


@pytest.fixture
def test_membership_type():
    """Тип абонемента"""
    return MembershipType.objects.create(
        name='Месячный абонемент',
        description='Абонемент на 1 месяц',
        price=Decimal('5000.00'),
        duration_days=30,
        visits_limit=12,
        is_active=True
    )


@pytest.fixture
def test_unlimited_membership_type():
    """Безлимитный абонемент"""
    return MembershipType.objects.create(
        name='Безлимит',
        description='Безлимитный абонемент',
        price=Decimal('10000.00'),
        duration_days=30,
        visits_limit=None,  # Безлимит
        is_active=True
    )


@pytest.fixture
def test_membership(test_client, test_membership_type):
    """Активный абонемент"""
    from datetime import date, timedelta

    return Membership.objects.create(
        client=test_client,
        membership_type=test_membership_type,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status=MembershipStatus.ACTIVE,
        visits_remaining=12
    )


@pytest.fixture
def test_room():
    """Зал/помещение"""
    return Room.objects.create(
        name='Зал йоги',
        capacity=20,
        description='Просторный зал для занятий йогой'
    )


@pytest.fixture
def test_class_type():
    """Тип занятия"""
    return ClassType.objects.create(
        name='Йога для начинающих',
        description='Занятие йогой для новичков',
        duration_minutes=60,
        is_active=True
    )


@pytest.fixture
def test_class(test_class_type, test_trainer, test_room):
    """Занятие в расписании"""
    from datetime import datetime, timedelta

    return Class.objects.create(
        class_type=test_class_type,
        trainer=test_trainer,
        room=test_room,
        datetime=datetime.now() + timedelta(days=1),  # Завтра
        duration_minutes=60,
        max_capacity=15,
        status=ClassStatus.SCHEDULED
    )


@pytest.fixture
def test_booking(test_client, test_class):
    """Бронирование"""
    return Booking.objects.create(
        client=test_client,
        class_instance=test_class,
        status=BookingStatus.CONFIRMED
    )


@pytest.fixture
def test_payment(test_client, test_membership):
    """Платёж"""
    return Payment.objects.create(
        client=test_client,
        membership=test_membership,
        amount=Decimal('5000.00'),
        status=PaymentStatus.PENDING,
        payment_method=PaymentMethod.YOOKASSA
    )


# ============================================================================
# Factory Fixtures (для создания множества объектов)
# ============================================================================

@pytest.fixture
def create_user():
    """Фабрика для создания пользователей"""
    def _create_user(**kwargs):
        defaults = {
            'username': f'user_{User.objects.count() + 1}',
            'email': f'user{User.objects.count() + 1}@example.com',
            'password': 'testpass123'
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)
    return _create_user


@pytest.fixture
def create_client():
    """Фабрика для создания клиентов"""
    counter = {'value': 0}

    def _create_client(**kwargs):
        counter['value'] += 1
        user = User.objects.create_user(
            username=f'client_{counter["value"]}',
            email=f'client{counter["value"]}@example.com',
            password='testpass123',
            first_name=f'Client{counter["value"]}',
            last_name='Test'
        )
        profile = Profile.objects.create(
            user=user,
            role=UserRole.CLIENT,
            phone=f'+7999{counter["value"]:07d}'
        )
        client_defaults = {'is_student': False}
        client_defaults.update(kwargs)
        return Client.objects.create(profile=profile, **client_defaults)
    return _create_client


@pytest.fixture
def create_membership_type():
    """Фабрика для создания типов абонементов"""
    def _create_membership_type(**kwargs):
        defaults = {
            'name': f'Абонемент {MembershipType.objects.count() + 1}',
            'price': Decimal('5000.00'),
            'duration_days': 30,
            'is_active': True
        }
        defaults.update(kwargs)
        return MembershipType.objects.create(**defaults)
    return _create_membership_type


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_yookassa_response():
    """Mock ответ от ЮKassa API"""
    return {
        'payment_id': '2d96e1b2-000f-5000-8000-18db351245c7',
        'confirmation_url': 'https://yoomoney.ru/checkout/payments/v2/contract?orderId=test',
        'status': 'pending',
        'test': True
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Автоматически включает доступ к БД для всех тестов
    Можно убрать autouse=True если нужно явно помечать тесты через @pytest.mark.django_db
    """
    pass
