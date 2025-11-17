"""
Integration тесты для API views приложения accounts
"""

import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User

from apps.accounts.models import Profile, Client, UserRole


@pytest.mark.integration
class TestRegistrationAPI:
    """Тесты для API регистрации"""

    def test_register_new_user_success(self, api_client):
        """Тест успешной регистрации нового пользователя"""
        url = reverse('accounts:register')
        data = {
            'username': 'newuser123',
            'email': 'newuser@test.com',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+79001234567'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert 'username' in response.data

        # Проверяем что пользователь создан
        assert User.objects.filter(username='newuser123').exists()

        # Проверяем что профиль и клиент созданы
        user = User.objects.get(username='newuser123')
        assert hasattr(user, 'profile')
        assert user.profile.role == UserRole.CLIENT

    def test_register_password_mismatch(self, api_client):
        """Тест регистрации с несовпадающими паролями"""
        url = reverse('accounts:register')
        data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'Pass123!',
            'password2': 'DifferentPass123!',
            'phone': '+79001111111'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_register_duplicate_username(self, api_client, test_user):
        """Тест регистрации с существующим username"""
        url = reverse('accounts:register')
        data = {
            'username': test_user.username,  # Уже существует
            'email': 'newemail@test.com',
            'password': 'Pass123!',
            'password2': 'Pass123!',
            'phone': '+79002222222'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        """Тест регистрации со слабым паролем"""
        url = reverse('accounts:register')
        data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': '123',  # Слишком простой
            'password2': '123',
            'phone': '+79003333333'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestProfileAPI:
    """Тесты для API профиля"""

    def test_get_own_profile(self, authenticated_client, test_client_user):
        """Тест получения своего профиля"""
        url = reverse('accounts:profile-detail')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == test_client_user.username
        assert response.data['email'] == test_client_user.email

    def test_get_profile_unauthorized(self, api_client):
        """Тест получения профиля без авторизации"""
        url = reverse('accounts:profile-detail')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_own_profile(self, authenticated_client, test_client_user):
        """Тест обновления своего профиля"""
        url = reverse('accounts:profile-detail')
        data = {
            'email': 'updated@test.com',
            'first_name': 'UpdatedName',
            'phone': '+79009999999'
        }

        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Проверяем что данные обновились
        test_client_user.refresh_from_db()
        assert test_client_user.email == 'updated@test.com'
        assert test_client_user.first_name == 'UpdatedName'


@pytest.mark.integration
class TestClientAPI:
    """Тесты для API клиентов (только для админов)"""

    def test_list_clients_as_admin(self, admin_client):
        """Тест получения списка клиентов админом"""
        url = reverse('accounts:client-list')

        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_clients_as_regular_user(self, authenticated_client):
        """Тест получения списка клиентов обычным пользователем"""
        url = reverse('accounts:client-list')

        response = authenticated_client.get(url)

        # Должен быть запрещён доступ
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    def test_create_client_as_admin(self, admin_client):
        """Тест создания клиента админом"""
        url = reverse('accounts:client-list')
        data = {
            'username': 'admincreated',
            'email': 'admincreated@test.com',
            'password': 'AdminPass123!',
            'first_name': 'Admin',
            'last_name': 'Created',
            'phone': '+79008888888',
            'is_student': True
        }

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Client.objects.filter(profile__user__username='admincreated').exists()

    def test_get_client_detail(self, admin_client, test_client):
        """Тест получения деталей клиента"""
        url = reverse('accounts:client-detail', kwargs={'pk': test_client.id})

        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_client.id

    def test_update_client_as_admin(self, admin_client, test_client):
        """Тест обновления клиента админом"""
        url = reverse('accounts:client-detail', kwargs={'pk': test_client.id})
        data = {
            'is_student': True,
            'emergency_contact': 'Emergency Person'
        }

        response = admin_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        test_client.refresh_from_db()
        assert test_client.is_student is True
        assert test_client.emergency_contact == 'Emergency Person'


@pytest.mark.integration
class TestLoginAPI:
    """Тесты для API авторизации (JWT)"""

    def test_login_with_valid_credentials(self, api_client, test_user):
        """Тест входа с валидными credentials"""
        url = reverse('accounts:token_obtain_pair')
        data = {
            'username': test_user.username,
            'password': 'testpass123'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_with_invalid_password(self, api_client, test_user):
        """Тест входа с неверным паролем"""
        url = reverse('accounts:token_obtain_pair')
        data = {
            'username': test_user.username,
            'password': 'wrongpassword'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_with_nonexistent_user(self, api_client):
        """Тест входа с несуществующим пользователем"""
        url = reverse('accounts:token_obtain_pair')
        data = {
            'username': 'nonexistent',
            'password': 'somepass'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, test_user):
        """Тест обновления access token через refresh token"""
        # Сначала получаем токены
        login_url = reverse('accounts:token_obtain_pair')
        login_data = {
            'username': test_user.username,
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']

        # Обновляем access token
        refresh_url = reverse('accounts:token_refresh')
        refresh_data = {
            'refresh': refresh_token
        }

        response = api_client.post(refresh_url, refresh_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
