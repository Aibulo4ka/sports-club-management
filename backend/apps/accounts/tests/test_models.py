"""
Unit-тесты для моделей приложения accounts
"""

import pytest
from django.contrib.auth.models import User
from apps.accounts.models import Profile, Client, Trainer, UserRole


@pytest.mark.unit
class TestProfileModel:
    """Тесты для модели Profile"""

    def test_create_profile(self, test_user):
        """Тест создания профиля"""
        profile = Profile.objects.create(
            user=test_user,
            role=UserRole.CLIENT,
            phone='+79991234567'
        )

        assert profile.user == test_user
        assert profile.role == UserRole.CLIENT
        assert profile.phone == '+79991234567'
        assert str(profile) == f"{test_user.get_full_name()} (Клиент)"

    def test_profile_default_role(self, test_user):
        """Тест роли по умолчанию"""
        profile = Profile.objects.create(user=test_user)
        assert profile.role == UserRole.CLIENT

    def test_profile_str_with_username(self):
        """Тест __str__ когда нет полного имени"""
        user = User.objects.create_user(username='testuser', email='test@test.com')
        profile = Profile.objects.create(user=user, role=UserRole.ADMIN)

        assert str(profile) == "testuser (Администратор)"

    def test_profile_ordering(self, create_user):
        """Тест сортировки профилей по дате создания"""
        user1 = create_user(username='user1')
        user2 = create_user(username='user2')
        user3 = create_user(username='user3')

        Profile.objects.create(user=user1, role=UserRole.CLIENT)
        Profile.objects.create(user=user2, role=UserRole.TRAINER)
        Profile.objects.create(user=user3, role=UserRole.ADMIN)

        profiles = list(Profile.objects.all())
        # Должны быть отсортированы по -created_at (новые первыми)
        assert profiles[0].user == user3
        assert profiles[2].user == user1


@pytest.mark.unit
class TestClientModel:
    """Тесты для модели Client"""

    def test_create_client(self, test_client_user):
        """Тест создания клиента"""
        client = test_client_user.profile.client_info

        assert client.profile.user == test_client_user
        assert client.is_student == False
        assert str(client) == test_client_user.get_full_name()

    def test_client_student_flag(self, test_student_user):
        """Тест флага студента"""
        client = test_student_user.profile.client_info
        assert client.is_student == True

    def test_client_with_medical_notes(self, test_client):
        """Тест клиента с медицинскими заметками"""
        test_client.medical_notes = "Аллергия на латекс"
        test_client.save()

        assert test_client.medical_notes == "Аллергия на латекс"

    def test_client_emergency_contact(self, test_client):
        """Тест экстренного контакта"""
        test_client.emergency_contact = "Иван Иванов"
        test_client.emergency_phone = "+79991111111"
        test_client.save()

        assert test_client.emergency_contact == "Иван Иванов"
        assert test_client.emergency_phone == "+79991111111"

    def test_client_group_members(self, create_client):
        """Тест групповых членов (для групповых скидок)"""
        client1 = create_client()
        client2 = create_client()
        client3 = create_client()

        # Добавляем в группу
        client1.group_members.add(client2, client3)

        assert client1.group_members.count() == 2
        assert client2 in client1.group_members.all()
        assert client3 in client1.group_members.all()

        # Проверяем симметричность (M2M symmetrical=True)
        assert client1 in client2.group_members.all()


@pytest.mark.unit
class TestTrainerModel:
    """Тесты для модели Trainer"""

    def test_create_trainer(self, test_trainer_user):
        """Тест создания тренера"""
        trainer = test_trainer_user.profile.trainer_info

        assert trainer.profile.user == test_trainer_user
        assert trainer.specialization == 'Йога'
        assert trainer.experience_years == 5
        assert trainer.is_active == True

    def test_trainer_str_representation(self, test_trainer):
        """Тест строкового представления"""
        expected = f"{test_trainer.profile.user.get_full_name()} - {test_trainer.specialization}"
        assert str(test_trainer) == expected

    def test_trainer_with_bio_and_certifications(self, test_trainer):
        """Тест тренера с биографией и сертификатами"""
        test_trainer.bio = "Опытный тренер по йоге с 10-летним стажем"
        test_trainer.certifications = "RYT-200, RYT-500"
        test_trainer.save()

        assert "Опытный тренер" in test_trainer.bio
        assert "RYT-200" in test_trainer.certifications

    def test_trainer_can_be_deactivated(self, test_trainer):
        """Тест деактивации тренера"""
        test_trainer.is_active = False
        test_trainer.save()

        assert test_trainer.is_active == False


@pytest.mark.unit
class TestUserRoles:
    """Тесты для ролей пользователей"""

    def test_all_roles_exist(self):
        """Проверка что все роли определены"""
        assert hasattr(UserRole, 'CLIENT')
        assert hasattr(UserRole, 'TRAINER')
        assert hasattr(UserRole, 'ADMIN')

    def test_role_choices(self):
        """Проверка выбора ролей"""
        roles = [choice[0] for choice in UserRole.choices]

        assert 'CLIENT' in roles
        assert 'TRAINER' in roles
        assert 'ADMIN' in roles

    def test_role_display_names(self):
        """Проверка отображаемых имён ролей"""
        assert UserRole.CLIENT.label == 'Клиент'
        assert UserRole.TRAINER.label == 'Тренер'
        assert UserRole.ADMIN.label == 'Администратор'
