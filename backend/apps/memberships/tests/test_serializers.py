"""
Unit-тесты для сериализаторов приложения memberships
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from apps.memberships.serializers import (
    MembershipTypeSerializer, MembershipSerializer,
    MembershipCreateSerializer, MembershipUpdateSerializer,
    MembershipTypeWithPriceSerializer, PriceCalculationSerializer
)
from apps.memberships.models import MembershipType, Membership, MembershipStatus


@pytest.mark.unit
class TestMembershipTypeSerializer:
    """Тесты для MembershipTypeSerializer"""

    def test_serialize_membership_type(self, test_membership_type):
        """Тест сериализации типа абонемента"""
        serializer = MembershipTypeSerializer(test_membership_type)

        data = serializer.data
        assert data['name'] == test_membership_type.name
        assert Decimal(data['price']) == test_membership_type.price
        assert data['duration_days'] == test_membership_type.duration_days
        assert data['visits_limit'] == test_membership_type.visits_limit
        assert data['is_active'] is True

    def test_create_membership_type(self):
        """Тест создания типа абонемента"""
        data = {
            'name': 'Новый абонемент',
            'description': 'Тестовый абонемент',
            'price': '3000.00',
            'duration_days': 15,
            'visits_limit': 8,
            'is_active': True
        }

        serializer = MembershipTypeSerializer(data=data)
        assert serializer.is_valid()

        membership_type = serializer.save()
        assert membership_type.name == 'Новый абонемент'
        assert membership_type.price == Decimal('3000.00')


@pytest.mark.unit
class TestMembershipTypeWithPriceSerializer:
    """Тесты для MembershipTypeWithPriceSerializer с расчётом скидок"""

    def test_price_calculation_for_regular_client(self, test_membership_type, test_client):
        """Тест расчёта цены для обычного клиента"""
        serializer = MembershipTypeWithPriceSerializer(
            test_membership_type,
            context={'client': test_client}
        )

        data = serializer.data
        assert 'calculated_price' in data

        price_info = data['calculated_price']
        assert 'base_price' in price_info
        assert 'final_price' in price_info
        assert 'discount_amount' in price_info
        assert 'discount_description' in price_info

    def test_price_calculation_for_student(self, test_membership_type, test_student_user):
        """Тест расчёта цены для студента (со скидкой)"""
        client = test_student_user.profile.client_info

        serializer = MembershipTypeWithPriceSerializer(
            test_membership_type,
            context={'client': client}
        )

        data = serializer.data
        price_info = data['calculated_price']

        # У студента должна быть скидка
        base_price = Decimal(price_info['base_price'])
        final_price = Decimal(price_info['final_price'])

        assert final_price < base_price
        assert Decimal(price_info['discount_amount']) > 0

    def test_no_client_in_context(self, test_membership_type):
        """Тест без клиента в контексте"""
        serializer = MembershipTypeWithPriceSerializer(test_membership_type)

        data = serializer.data
        price_info = data['calculated_price']

        # Без клиента скидки нет
        assert price_info['discount_amount'] == '0.00'
        assert price_info['base_price'] == price_info['final_price']


@pytest.mark.unit
class TestMembershipSerializer:
    """Тесты для MembershipSerializer"""

    def test_serialize_membership(self, test_membership):
        """Тест сериализации абонемента"""
        serializer = MembershipSerializer(test_membership)

        data = serializer.data
        assert 'id' in data
        assert 'client_name' in data
        assert 'membership_type_details' in data
        assert data['status'] == test_membership.status
        assert data['visits_remaining'] == test_membership.visits_remaining

    def test_is_expired_property(self, test_client, test_membership_type):
        """Тест свойства is_expired"""
        # Создаём истёкший абонемент
        expired_membership = Membership.objects.create(
            client=test_client,
            membership_type=test_membership_type,
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),  # Истёк 30 дней назад
            status=MembershipStatus.EXPIRED,
            visits_remaining=0
        )

        serializer = MembershipSerializer(expired_membership)
        data = serializer.data

        assert data['is_expired'] is True
        assert data['days_remaining'] == 0

    def test_days_remaining_calculation(self, test_membership):
        """Тест расчёта оставшихся дней"""
        serializer = MembershipSerializer(test_membership)
        data = serializer.data

        expected_days = (test_membership.end_date - date.today()).days
        assert data['days_remaining'] == expected_days


@pytest.mark.unit
class TestMembershipCreateSerializer:
    """Тесты для MembershipCreateSerializer"""

    def test_create_membership_valid_data(self, test_client, test_membership_type):
        """Тест создания абонемента с валидными данными"""
        data = {
            'client_id': test_client.id,
            'membership_type_id': test_membership_type.id,
            'start_date': date.today()
        }

        serializer = MembershipCreateSerializer(data=data)
        assert serializer.is_valid()

        membership = serializer.save()

        assert membership.client == test_client
        assert membership.membership_type == test_membership_type
        assert membership.status == MembershipStatus.ACTIVE
        assert membership.visits_remaining == test_membership_type.visits_limit

        # Проверяем автоматический расчёт end_date
        expected_end_date = data['start_date'] + timedelta(days=test_membership_type.duration_days)
        assert membership.end_date == expected_end_date

    def test_default_start_date(self, test_client, test_membership_type):
        """Тест автоматической установки start_date"""
        data = {
            'client_id': test_client.id,
            'membership_type_id': test_membership_type.id
        }

        serializer = MembershipCreateSerializer(data=data)
        assert serializer.is_valid()

        membership = serializer.save()

        # start_date должен быть сегодня
        assert membership.start_date == date.today()

    def test_invalid_client_id(self, test_membership_type):
        """Тест с несуществующим client_id"""
        data = {
            'client_id': 99999,  # Не существует
            'membership_type_id': test_membership_type.id
        }

        serializer = MembershipCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'client_id' in serializer.errors

    def test_inactive_membership_type(self, test_client):
        """Тест с неактивным типом абонемента"""
        inactive_type = MembershipType.objects.create(
            name='Неактивный',
            price=Decimal('1000.00'),
            duration_days=30,
            is_active=False  # Неактивен
        )

        data = {
            'client_id': test_client.id,
            'membership_type_id': inactive_type.id
        }

        serializer = MembershipCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'membership_type_id' in serializer.errors


@pytest.mark.unit
class TestMembershipUpdateSerializer:
    """Тесты для MembershipUpdateSerializer"""

    def test_update_status(self, test_membership):
        """Тест обновления статуса абонемента"""
        data = {
            'status': MembershipStatus.SUSPENDED
        }

        serializer = MembershipUpdateSerializer(test_membership, data=data, partial=True)
        assert serializer.is_valid()

        updated_membership = serializer.save()
        assert updated_membership.status == MembershipStatus.SUSPENDED

    def test_update_visits_remaining(self, test_membership):
        """Тест обновления оставшихся посещений"""
        data = {
            'visits_remaining': 5
        }

        serializer = MembershipUpdateSerializer(test_membership, data=data, partial=True)
        assert serializer.is_valid()

        updated_membership = serializer.save()
        assert updated_membership.visits_remaining == 5

    def test_negative_visits_validation(self, test_membership):
        """Тест валидации отрицательных посещений"""
        data = {
            'visits_remaining': -5
        }

        serializer = MembershipUpdateSerializer(test_membership, data=data, partial=True)
        assert not serializer.is_valid()
        assert 'visits_remaining' in serializer.errors


@pytest.mark.unit
class TestPriceCalculationSerializer:
    """Тесты для PriceCalculationSerializer"""

    def test_calculate_price_for_regular_client(self, test_client, test_membership_type):
        """Тест расчёта цены для обычного клиента"""
        data = {
            'membership_type_id': test_membership_type.id,
            'client_id': test_client.id
        }

        serializer = PriceCalculationSerializer(data=data)
        assert serializer.is_valid()

        result = serializer.calculate()

        assert 'membership_type' in result
        assert 'client' in result
        assert 'pricing' in result

        pricing = result['pricing']
        assert 'base_price' in pricing
        assert 'final_price' in pricing
        assert 'discount_description' in pricing

    def test_calculate_price_for_student(self, test_student_user, test_membership_type):
        """Тест расчёта цены для студента"""
        client = test_student_user.profile.client_info

        data = {
            'membership_type_id': test_membership_type.id,
            'client_id': client.id
        }

        serializer = PriceCalculationSerializer(data=data)
        assert serializer.is_valid()

        result = serializer.calculate()
        pricing = result['pricing']

        # У студента должна быть скидка
        base_price = Decimal(pricing['base_price'])
        final_price = Decimal(pricing['final_price'])
        assert final_price < base_price

    def test_invalid_membership_type(self, test_client):
        """Тест с несуществующим типом абонемента"""
        data = {
            'membership_type_id': 99999,
            'client_id': test_client.id
        }

        serializer = PriceCalculationSerializer(data=data)
        assert not serializer.is_valid()

    def test_invalid_client(self, test_membership_type):
        """Тест с несуществующим клиентом"""
        data = {
            'membership_type_id': test_membership_type.id,
            'client_id': 99999
        }

        serializer = PriceCalculationSerializer(data=data)
        assert not serializer.is_valid()
