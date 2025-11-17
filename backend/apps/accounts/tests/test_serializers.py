"""
Unit-тесты для сериализаторов приложения accounts
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError

from apps.accounts.serializers import (
    RegisterSerializer, ProfileSerializer, ClientSerializer,
    ClientCreateSerializer, ClientUpdateSerializer
)
from apps.accounts.models import Profile, Client, UserRole


@pytest.mark.unit
class TestRegisterSerializer:
    """Тесты для RegisterSerializer"""

    def test_valid_registration_data(self):
        """Тест с валидными данными регистрации"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+79001234567'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()

    def test_password_mismatch(self):
        """Тест с несовпадающими паролями"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password2': 'DifferentPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+79001234567'
        }
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors

    def test_create_user_with_profile_and_client(self):
        """Тест создания пользователя с профилем и клиентом"""
        data = {
            'username': 'testuser123',
            'email': 'test123@example.com',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+79009999999'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()

        user = serializer.save()

        # Проверяем что пользователь создан
        assert user.username == 'testuser123'
        assert user.email == 'test123@example.com'

        # Проверяем что профиль создан
        assert hasattr(user, 'profile')
        assert user.profile.phone == '+79009999999'
        assert user.profile.role == UserRole.CLIENT

        # Проверяем что клиент создан
        assert hasattr(user.profile, 'client_info')
        assert user.profile.client_info is not None


@pytest.mark.unit
class TestProfileSerializer:
    """Тесты для ProfileSerializer"""

    def test_serialize_profile(self, test_client_user):
        """Тест сериализации профиля"""
        profile = test_client_user.profile
        serializer = ProfileSerializer(profile)

        data = serializer.data
        assert data['username'] == test_client_user.username
        assert data['email'] == test_client_user.email
        assert data['role'] == profile.role

    def test_readonly_fields(self, test_client_user):
        """Тест что username и role только для чтения"""
        profile = test_client_user.profile

        data = {
            'username': 'changedusername',  # Должно игнорироваться
            'role': UserRole.ADMIN,  # Должно игнорироваться
            'email': 'newemail@example.com',
            'first_name': 'NewName',
            'phone': '+79001111111'
        }

        serializer = ProfileSerializer(profile, data=data, partial=True)
        assert serializer.is_valid()

        updated_profile = serializer.save()

        # username и role не должны измениться
        assert updated_profile.user.username == test_client_user.username
        assert updated_profile.role == UserRole.CLIENT


@pytest.mark.unit
class TestClientSerializer:
    """Тесты для ClientSerializer"""

    def test_serialize_client(self, test_client):
        """Тест сериализации клиента"""
        serializer = ClientSerializer(test_client)

        data = serializer.data
        assert 'id' in data
        assert 'profile' in data
        assert 'full_name' in data
        assert 'email' in data
        assert data['is_student'] == test_client.is_student

    def test_full_name_method(self, test_client):
        """Тест метода get_full_name"""
        serializer = ClientSerializer(test_client)
        data = serializer.data

        expected_name = test_client.profile.user.get_full_name()
        if not expected_name:
            expected_name = test_client.profile.user.username

        assert data['full_name'] == expected_name


@pytest.mark.unit
class TestClientCreateSerializer:
    """Тесты для ClientCreateSerializer"""

    def test_create_client_valid_data(self):
        """Тест создания клиента с валидными данными"""
        data = {
            'username': 'newclient123',
            'email': 'newclient@example.com',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'Client',
            'phone': '+79005555555',
            'is_student': True,
            'emergency_contact': 'John Doe',
            'emergency_phone': '+79006666666'
        }

        serializer = ClientCreateSerializer(data=data)
        assert serializer.is_valid()

        client = serializer.save()

        # Проверяем что всё создано
        assert client.profile.user.username == 'newclient123'
        assert client.profile.phone == '+79005555555'
        assert client.is_student is True
        assert client.emergency_contact == 'John Doe'

    def test_duplicate_username_validation(self, test_user):
        """Тест валидации дубликата username"""
        data = {
            'username': test_user.username,  # Уже существует
            'email': 'another@example.com',
            'password': 'SecurePass123!',
            'phone': '+79007777777'
        }

        serializer = ClientCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors

    def test_duplicate_phone_validation(self, test_client_user):
        """Тест валидации дубликата телефона"""
        data = {
            'username': 'uniqueuser',
            'email': 'unique@example.com',
            'password': 'SecurePass123!',
            'phone': test_client_user.profile.phone  # Уже существует
        }

        serializer = ClientCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'phone' in serializer.errors


@pytest.mark.unit
class TestClientUpdateSerializer:
    """Тесты для ClientUpdateSerializer"""

    def test_update_client_info(self, test_client):
        """Тест обновления информации о клиенте"""
        data = {
            'email': 'updated@example.com',
            'first_name': 'UpdatedName',
            'phone': '+79008888888',
            'is_student': True,
            'emergency_contact': 'Jane Doe'
        }

        serializer = ClientUpdateSerializer(test_client, data=data, partial=True)
        assert serializer.is_valid()

        updated_client = serializer.save()

        # Проверяем обновления
        assert updated_client.profile.user.email == 'updated@example.com'
        assert updated_client.profile.user.first_name == 'UpdatedName'
        assert updated_client.profile.phone == '+79008888888'
        assert updated_client.is_student is True
        assert updated_client.emergency_contact == 'Jane Doe'

    def test_partial_update(self, test_client):
        """Тест частичного обновления"""
        original_email = test_client.profile.user.email

        data = {
            'emergency_contact': 'Emergency Person'
        }

        serializer = ClientUpdateSerializer(test_client, data=data, partial=True)
        assert serializer.is_valid()

        updated_client = serializer.save()

        # Email не должен измениться
        assert updated_client.profile.user.email == original_email
        # emergency_contact должен обновиться
        assert updated_client.emergency_contact == 'Emergency Person'
