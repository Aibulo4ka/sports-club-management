"""
Unit-тесты для моделей приложения memberships
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from apps.memberships.models import MembershipType, Membership, MembershipStatus


@pytest.mark.unit
class TestMembershipTypeModel:
    """Тесты для модели MembershipType"""

    def test_create_membership_type(self, test_membership_type):
        """Тест создания типа абонемента"""
        assert test_membership_type.name == 'Месячный абонемент'
        assert test_membership_type.price == Decimal('5000.00')
        assert test_membership_type.duration_days == 30
        assert test_membership_type.visits_limit == 12
        assert test_membership_type.is_active == True

    def test_str_representation(self, test_membership_type):
        """Тест строкового представления"""
        expected = "Месячный абонемент - 5000.00 руб."
        assert str(test_membership_type) == expected

    def test_unlimited_membership_type(self, test_unlimited_membership_type):
        """Тест безлимитного абонемента"""
        assert test_unlimited_membership_type.visits_limit is None

    def test_membership_type_ordering(self, create_membership_type):
        """Тест сортировки по цене"""
        mt1 = create_membership_type(name='Дешёвый', price=Decimal('1000.00'))
        mt2 = create_membership_type(name='Средний', price=Decimal('5000.00'))
        mt3 = create_membership_type(name='Дорогой', price=Decimal('10000.00'))

        types = list(MembershipType.objects.all())
        # Должны быть отсортированы по цене (от дешёвого к дорогому)
        assert types[0] == mt1
        assert types[1] == mt2
        assert types[2] == mt3

    def test_inactive_membership_type(self, test_membership_type):
        """Тест неактивного типа абонемента"""
        test_membership_type.is_active = False
        test_membership_type.save()

        assert test_membership_type.is_active == False


@pytest.mark.unit
class TestMembershipModel:
    """Тесты для модели Membership"""

    def test_create_membership(self, test_membership):
        """Тест создания абонемента"""
        assert test_membership.status == MembershipStatus.ACTIVE
        assert test_membership.visits_remaining == 12
        assert test_membership.start_date == date.today()
        assert test_membership.end_date == date.today() + timedelta(days=30)

    def test_str_representation(self, test_membership):
        """Тест строкового представления"""
        client_name = test_membership.client.profile.user.get_full_name()
        expected = f"{client_name} - Месячный абонемент (Активен)"
        assert str(test_membership) == expected

    def test_membership_statuses(self):
        """Тест всех статусов абонемента"""
        assert hasattr(MembershipStatus, 'ACTIVE')
        assert hasattr(MembershipStatus, 'EXPIRED')
        assert hasattr(MembershipStatus, 'SUSPENDED')

    def test_expired_membership(self, test_client, test_membership_type):
        """Тест истёкшего абонемента"""
        membership = Membership.objects.create(
            client=test_client,
            membership_type=test_membership_type,
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
            status=MembershipStatus.EXPIRED,
            visits_remaining=0
        )

        assert membership.status == MembershipStatus.EXPIRED
        assert membership.end_date < date.today()

    def test_suspended_membership(self, test_membership):
        """Тест приостановленного абонемента"""
        test_membership.status = MembershipStatus.SUSPENDED
        test_membership.save()

        assert test_membership.status == MembershipStatus.SUSPENDED

    def test_membership_with_no_visits_limit(self, test_client, test_unlimited_membership_type):
        """Тест безлимитного абонемента"""
        membership = Membership.objects.create(
            client=test_client,
            membership_type=test_unlimited_membership_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=MembershipStatus.ACTIVE,
            visits_remaining=None  # Безлимит
        )

        assert membership.visits_remaining is None

    def test_membership_ordering(self, test_client, test_membership_type):
        """Тест сортировки по дате покупки"""
        m1 = Membership.objects.create(
            client=test_client,
            membership_type=test_membership_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=MembershipStatus.ACTIVE
        )

        m2 = Membership.objects.create(
            client=test_client,
            membership_type=test_membership_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=MembershipStatus.ACTIVE
        )

        memberships = list(Membership.objects.all())
        # Новые должны быть первыми (ordering = ['-purchased_at'])
        assert memberships[0] == m2
        assert memberships[1] == m1

    def test_decrement_visits_remaining(self, test_membership):
        """Тест уменьшения оставшихся посещений"""
        initial_visits = test_membership.visits_remaining

        test_membership.visits_remaining -= 1
        test_membership.save()

        assert test_membership.visits_remaining == initial_visits - 1

    def test_membership_belongs_to_correct_client(self, test_client, test_membership):
        """Тест что абонемент принадлежит правильному клиенту"""
        assert test_membership.client == test_client
        assert test_membership in test_client.memberships.all()
