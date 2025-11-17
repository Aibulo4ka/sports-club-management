"""
Тесты для паттерна Observer в приложении accounts
Паттерн Observer реализован через Django signals
"""

import pytest
from django.contrib.auth.models import User

from apps.accounts.models import Profile, Client, Trainer, UserRole


@pytest.mark.patterns
class TestObserverPattern:
    """Тесты для паттерна Observer через Django signals"""

    def test_signal_creates_client_on_profile_creation(self):
        """Тест что при создании Profile с ролью CLIENT автоматически создаётся Client"""
        # Создаём пользователя
        user = User.objects.create_user(
            username='newclient',
            email='newclient@test.com',
            password='testpass123'
        )

        # Создаём профиль с ролью CLIENT
        profile = Profile.objects.create(
            user=user,
            role=UserRole.CLIENT,
            phone='+79001112233'
        )

        # Проверяем что Client был создан автоматически (Observer pattern)
        assert hasattr(profile, 'client_info')
        assert profile.client_info is not None
        assert isinstance(profile.client_info, Client)

    def test_signal_creates_trainer_on_profile_creation(self):
        """Тест что при создании Profile с ролью TRAINER автоматически создаётся Trainer"""
        user = User.objects.create_user(
            username='newtrainer',
            email='newtrainer@test.com',
            password='testpass123'
        )

        profile = Profile.objects.create(
            user=user,
            role=UserRole.TRAINER,
            phone='+79002223344'
        )

        # Проверяем что Trainer был создан автоматически
        assert hasattr(profile, 'trainer_info')
        assert profile.trainer_info is not None
        assert isinstance(profile.trainer_info, Trainer)

        # Проверяем дефолтные значения
        assert profile.trainer_info.specialization == 'Не указано'
        assert profile.trainer_info.experience_years == 0

    def test_signal_does_not_create_for_admin(self):
        """Тест что для ADMIN роли не создаются дополнительные объекты"""
        user = User.objects.create_user(
            username='newadmin',
            email='newadmin@test.com',
            password='testpass123'
        )

        profile = Profile.objects.create(
            user=user,
            role=UserRole.ADMIN,
            phone='+79003334455'
        )

        # Не должно быть ни Client, ни Trainer
        assert not hasattr(profile, 'client_info') or not Client.objects.filter(profile=profile).exists()
        assert not hasattr(profile, 'trainer_info') or not Trainer.objects.filter(profile=profile).exists()

    def test_signal_on_role_change_to_client(self):
        """Тест что при изменении роли на CLIENT создаётся Client"""
        user = User.objects.create_user(
            username='rolechange1',
            email='rolechange1@test.com',
            password='testpass123'
        )

        # Создаём профиль с ролью ADMIN
        profile = Profile.objects.create(
            user=user,
            role=UserRole.ADMIN,
            phone='+79004445566'
        )

        # Меняем роль на CLIENT
        profile.role = UserRole.CLIENT
        profile.save()

        # Должен создаться Client
        assert Client.objects.filter(profile=profile).exists()

    def test_signal_on_role_change_to_trainer(self):
        """Тест что при изменении роли на TRAINER создаётся Trainer"""
        user = User.objects.create_user(
            username='rolechange2',
            email='rolechange2@test.com',
            password='testpass123'
        )

        profile = Profile.objects.create(
            user=user,
            role=UserRole.ADMIN,
            phone='+79005556677'
        )

        # Меняем роль на TRAINER
        profile.role = UserRole.TRAINER
        profile.save()

        # Должен создаться Trainer
        assert Trainer.objects.filter(profile=profile).exists()

    def test_signal_does_not_duplicate_client(self):
        """Тест что signal не создаёт дублирующих Client записей"""
        user = User.objects.create_user(
            username='nodupe1',
            email='nodupe1@test.com',
            password='testpass123'
        )

        profile = Profile.objects.create(
            user=user,
            role=UserRole.CLIENT,
            phone='+79006667788'
        )

        # Первый Client уже создан
        first_client = profile.client_info

        # Обновляем профиль
        profile.phone = '+79006667799'
        profile.save()

        # Client должен остаться тем же (не создался новый)
        assert Client.objects.filter(profile=profile).count() == 1
        assert profile.client_info.id == first_client.id

    def test_signal_does_not_duplicate_trainer(self):
        """Тест что signal не создаёт дублирующих Trainer записей"""
        user = User.objects.create_user(
            username='nodupe2',
            email='nodupe2@test.com',
            password='testpass123'
        )

        profile = Profile.objects.create(
            user=user,
            role=UserRole.TRAINER,
            phone='+79007778899'
        )

        first_trainer = profile.trainer_info

        # Обновляем профиль
        profile.phone = '+79007778800'
        profile.save()

        # Trainer должен остаться тем же
        assert Trainer.objects.filter(profile=profile).count() == 1
        assert profile.trainer_info.id == first_trainer.id

    def test_observer_pattern_multiple_profiles(self):
        """Тест Observer pattern для нескольких профилей одновременно"""
        # Создаём несколько профилей с разными ролями
        profiles = []

        for i in range(3):
            user = User.objects.create_user(
                username=f'multiuser{i}',
                email=f'multiuser{i}@test.com',
                password='testpass123'
            )
            profile = Profile.objects.create(
                user=user,
                role=UserRole.CLIENT,
                phone=f'+7900{i}{i}{i}{i}{i}{i}{i}'
            )
            profiles.append(profile)

        # Все должны иметь Client объекты
        for profile in profiles:
            assert hasattr(profile, 'client_info')
            assert profile.client_info is not None

    def test_signal_workflow_registration(self):
        """Тест полного workflow регистрации (как в реальном приложении)"""
        # Симулируем процесс регистрации
        # 1. Создаём User
        user = User.objects.create_user(
            username='registration_test',
            email='regtest@test.com',
            password='securepass123',
            first_name='Test',
            last_name='User'
        )

        # 2. Создаём Profile (триггерит signal)
        profile = Profile.objects.create(
            user=user,
            role=UserRole.CLIENT,
            phone='+79998887766'
        )

        # 3. Client должен быть создан автоматически
        assert Client.objects.filter(profile=profile).exists()
        client = profile.client_info

        # 4. Проверяем связи
        assert client.profile == profile
        assert client.profile.user == user
        assert client.profile.user.username == 'registration_test'
