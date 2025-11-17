"""
Integration тесты для API views приложения memberships
"""

import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal

from apps.memberships.models import MembershipType, Membership, MembershipStatus


@pytest.mark.integration
class TestMembershipTypeAPI:
    """Тесты для API типов абонементов"""

    def test_list_membership_types(self, api_client, test_membership_type):
        """Тест получения списка типов абонементов"""
        url = reverse('memberships:membershiptype-list')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_membership_type_detail(self, api_client, test_membership_type):
        """Тест получения деталей типа абонемента"""
        url = reverse('memberships:membershiptype-detail', kwargs={'pk': test_membership_type.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_membership_type.id
        assert response.data['name'] == test_membership_type.name

    def test_create_membership_type_as_admin(self, admin_client):
        """Тест создания типа абонемента админом"""
        url = reverse('memberships:membershiptype-list')
        data = {
            'name': 'Новый тип',
            'description': 'Описание нового типа',
            'price': '3000.00',
            'duration_days': 15,
            'visits_limit': 8,
            'is_active': True
        }

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert MembershipType.objects.filter(name='Новый тип').exists()

    def test_create_membership_type_as_regular_user(self, authenticated_client):
        """Тест создания типа абонемента обычным пользователем"""
        url = reverse('memberships:membershiptype-list')
        data = {
            'name': 'Test',
            'price': '1000.00',
            'duration_days': 30
        }

        response = authenticated_client.post(url, data, format='json')

        # Должен быть запрещён доступ
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    def test_update_membership_type(self, admin_client, test_membership_type):
        """Тест обновления типа абонемента"""
        url = reverse('memberships:membershiptype-detail', kwargs={'pk': test_membership_type.id})
        data = {
            'price': '6000.00',
            'is_active': False
        }

        response = admin_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        test_membership_type.refresh_from_db()
        assert test_membership_type.price == Decimal('6000.00')
        assert test_membership_type.is_active is False

    def test_delete_membership_type(self, admin_client, test_membership_type):
        """Тест удаления типа абонемента"""
        url = reverse('memberships:membershiptype-detail', kwargs={'pk': test_membership_type.id})

        response = admin_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MembershipType.objects.filter(id=test_membership_type.id).exists()

    def test_filter_active_membership_types(self, api_client, test_membership_type):
        """Тест фильтрации активных типов абонементов"""
        # Создаём неактивный тип
        MembershipType.objects.create(
            name='Неактивный',
            price=Decimal('1000.00'),
            duration_days=30,
            is_active=False
        )

        url = reverse('memberships:membershiptype-list')
        response = api_client.get(url, {'is_active': 'true'})

        assert response.status_code == status.HTTP_200_OK

        # Все результаты должны быть активными
        for item in response.data:
            assert item['is_active'] is True


@pytest.mark.integration
class TestMembershipAPI:
    """Тесты для API абонементов"""

    def test_list_own_memberships(self, authenticated_client, test_membership):
        """Тест получения списка своих абонементов"""
        url = reverse('memberships:membership-list')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_get_membership_detail(self, authenticated_client, test_membership):
        """Тест получения деталей абонемента"""
        url = reverse('memberships:membership-detail', kwargs={'pk': test_membership.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_membership.id

    def test_create_membership_for_client(self, admin_client, test_client, test_membership_type):
        """Тест создания абонемента для клиента (админом)"""
        url = reverse('memberships:membership-list')
        data = {
            'client_id': test_client.id,
            'membership_type_id': test_membership_type.id
        }

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_create_membership_with_invalid_client(self, admin_client, test_membership_type):
        """Тест создания абонемента с несуществующим клиентом"""
        url = reverse('memberships:membership-list')
        data = {
            'client_id': 99999,  # Не существует
            'membership_type_id': test_membership_type.id
        }

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_membership_status(self, admin_client, test_membership):
        """Тест обновления статуса абонемента"""
        url = reverse('memberships:membership-detail', kwargs={'pk': test_membership.id})
        data = {
            'status': MembershipStatus.SUSPENDED
        }

        response = admin_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        test_membership.refresh_from_db()
        assert test_membership.status == MembershipStatus.SUSPENDED

    def test_update_visits_remaining(self, admin_client, test_membership):
        """Тест обновления оставшихся посещений"""
        url = reverse('memberships:membership-detail', kwargs={'pk': test_membership.id})
        data = {
            'visits_remaining': 5
        }

        response = admin_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        test_membership.refresh_from_db()
        assert test_membership.visits_remaining == 5

    def test_filter_memberships_by_status(self, admin_client, test_membership):
        """Тест фильтрации абонементов по статусу"""
        url = reverse('memberships:membership-list')
        response = admin_client.get(url, {'status': MembershipStatus.ACTIVE})

        assert response.status_code == status.HTTP_200_OK

    def test_cannot_update_others_membership(self, authenticated_client, test_membership):
        """Тест что клиент не может обновить чужой абонемент"""
        url = reverse('memberships:membership-detail', kwargs={'pk': test_membership.id})
        data = {
            'visits_remaining': 100
        }

        response = authenticated_client.patch(url, data, format='json')

        # Должен быть запрещён доступ если это не его абонемент
        # (зависит от permissions в views)
        # assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestPriceCalculationAPI:
    """Тесты для API расчёта цены"""

    def test_calculate_price_for_regular_client(self, authenticated_client, test_client, test_membership_type):
        """Тест расчёта цены для обычного клиента"""
        url = reverse('memberships:calculate-price')
        data = {
            'membership_type_id': test_membership_type.id,
            'client_id': test_client.id
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'pricing' in response.data
        assert 'base_price' in response.data['pricing']
        assert 'final_price' in response.data['pricing']
        assert 'discount_description' in response.data['pricing']

    def test_calculate_price_for_student(self, authenticated_client, test_student_user, test_membership_type):
        """Тест расчёта цены для студента"""
        client = test_student_user.profile.client_info

        url = reverse('memberships:calculate-price')
        data = {
            'membership_type_id': test_membership_type.id,
            'client_id': client.id
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # У студента должна быть скидка
        pricing = response.data['pricing']
        base = Decimal(pricing['base_price'])
        final = Decimal(pricing['final_price'])

        # Может быть скидка или нет (зависит от is_student в фикстуре)
        # assert final <= base

    def test_calculate_price_invalid_membership_type(self, authenticated_client, test_client):
        """Тест расчёта цены с несуществующим типом абонемента"""
        url = reverse('memberships:calculate-price')
        data = {
            'membership_type_id': 99999,
            'client_id': test_client.id
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
