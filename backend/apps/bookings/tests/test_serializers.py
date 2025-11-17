"""
Unit-тесты для сериализаторов приложения bookings
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from apps.bookings.serializers import (
    BookingSerializer, VisitSerializer, BookingCreateSerializer
)
from apps.bookings.models import Booking, Visit, BookingStatus
from apps.classes.models import Class, ClassStatus
from apps.memberships.models import MembershipStatus


@pytest.mark.unit
class TestBookingSerializer:
    """Тесты для BookingSerializer"""

    def test_serialize_booking(self, test_booking):
        """Тест сериализации бронирования"""
        serializer = BookingSerializer(test_booking)

        data = serializer.data
        assert 'id' in data
        assert 'client_name' in data
        assert 'class_name' in data
        assert 'trainer_name' in data
        assert 'room_name' in data
        assert 'class_datetime' in data
        assert data['status'] == test_booking.status

    def test_can_cancel_property_true(self, test_client, test_class_type, test_trainer, test_room):
        """Тест can_cancel когда можно отменить (>24 часов)"""
        # Создаём занятие через 48 часов
        future_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() + timedelta(hours=48),
            duration_minutes=60,
            max_capacity=15,
            status=ClassStatus.SCHEDULED
        )

        booking = Booking.objects.create(
            client=test_client,
            class_instance=future_class,
            status=BookingStatus.CONFIRMED
        )

        serializer = BookingSerializer(booking)
        data = serializer.data

        assert data['can_cancel'] is True

    def test_can_cancel_property_false(self, test_client, test_class_type, test_trainer, test_room):
        """Тест can_cancel когда нельзя отменить (<24 часов)"""
        # Создаём занятие через 5 часов
        soon_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() + timedelta(hours=5),
            duration_minutes=60,
            max_capacity=15,
            status=ClassStatus.SCHEDULED
        )

        booking = Booking.objects.create(
            client=test_client,
            class_instance=soon_class,
            status=BookingStatus.CONFIRMED
        )

        serializer = BookingSerializer(booking)
        data = serializer.data

        assert data['can_cancel'] is False

    def test_validate_class_no_spots(self, test_client, test_class_type, test_trainer, test_room):
        """Тест валидации когда нет свободных мест"""
        # Создаём занятие с вместимостью 1
        full_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            max_capacity=1,
            status=ClassStatus.SCHEDULED
        )

        # Создаём первое бронирование (заполняем)
        Booking.objects.create(
            client=test_client,
            class_instance=full_class,
            status=BookingStatus.CONFIRMED
        )

        # Пытаемся создать второе
        data = {
            'client': test_client.id,
            'class_instance': full_class.id,
            'status': BookingStatus.CONFIRMED
        }

        serializer = BookingSerializer(data=data)
        assert not serializer.is_valid()
        assert 'class_instance' in serializer.errors

    def test_validate_class_in_past(self, test_client, test_class_type, test_trainer, test_room):
        """Тест валидации занятия в прошлом"""
        # Создаём занятие в прошлом
        past_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() - timedelta(days=1),  # Вчера
            duration_minutes=60,
            max_capacity=15,
            status=ClassStatus.COMPLETED
        )

        data = {
            'client': test_client.id,
            'class_instance': past_class.id,
            'status': BookingStatus.CONFIRMED
        }

        serializer = BookingSerializer(data=data)
        assert not serializer.is_valid()
        assert 'class_instance' in serializer.errors

    def test_validate_no_active_membership(self, test_client, test_class):
        """Тест валидации без активного абонемента"""
        # Приостанавливаем все абонементы клиента
        test_client.memberships.update(status=MembershipStatus.SUSPENDED)

        data = {
            'client': test_client.id,
            'class_instance': test_class.id,
            'status': BookingStatus.CONFIRMED
        }

        serializer = BookingSerializer(data=data)
        assert not serializer.is_valid()
        assert 'client' in serializer.errors

    def test_validate_no_visits_remaining(self, test_client, test_class, test_membership):
        """Тест валидации когда нет оставшихся посещений"""
        # Обнуляем оставшиеся посещения
        test_membership.visits_remaining = 0
        test_membership.save()

        data = {
            'client': test_client.id,
            'class_instance': test_class.id,
            'status': BookingStatus.CONFIRMED
        }

        serializer = BookingSerializer(data=data)
        assert not serializer.is_valid()
        assert 'client' in serializer.errors


@pytest.mark.unit
class TestVisitSerializer:
    """Тесты для VisitSerializer"""

    def test_serialize_visit(self, test_booking, test_admin_user):
        """Тест сериализации посещения"""
        visit = Visit.objects.create(
            booking=test_booking,
            checked_by=test_admin_user
        )

        serializer = VisitSerializer(visit)
        data = serializer.data

        assert 'id' in data
        assert 'booking' in data
        assert 'booking_info' in data
        assert 'checked_in_at' in data
        assert 'checked_by_name' in data

    def test_checked_by_name(self, test_booking, test_admin_user):
        """Тест отображения имени администратора"""
        visit = Visit.objects.create(
            booking=test_booking,
            checked_by=test_admin_user
        )

        serializer = VisitSerializer(visit)
        data = serializer.data

        expected_name = test_admin_user.get_full_name() or test_admin_user.username
        assert data['checked_by_name'] == expected_name

    def test_readonly_checked_in_at(self, test_booking, test_admin_user):
        """Тест что checked_in_at только для чтения"""
        custom_time = timezone.now() - timedelta(hours=2)

        data = {
            'booking': test_booking.id,
            'checked_by': test_admin_user.id,
            'checked_in_at': custom_time  # Должно игнорироваться
        }

        serializer = VisitSerializer(data=data)
        assert serializer.is_valid()

        visit = serializer.save()

        # checked_in_at должен быть установлен автоматически (не равен custom_time)
        assert visit.checked_in_at != custom_time


@pytest.mark.unit
class TestBookingCreateSerializer:
    """Тесты для BookingCreateSerializer"""

    def test_valid_class_id(self, test_class):
        """Тест с валидным class_id"""
        data = {
            'class_id': test_class.id,
            'notes': 'Тестовая заметка'
        }

        serializer = BookingCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_invalid_class_id(self):
        """Тест с несуществующим class_id"""
        data = {
            'class_id': 99999  # Не существует
        }

        serializer = BookingCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'class_id' in serializer.errors

    def test_notes_optional(self, test_class):
        """Тест что notes опциональное поле"""
        data = {
            'class_id': test_class.id
        }

        serializer = BookingCreateSerializer(data=data)
        assert serializer.is_valid()

        # notes должны быть пустыми по умолчанию
        assert serializer.validated_data['notes'] == ''

    def test_notes_can_be_blank(self, test_class):
        """Тест что notes может быть пустым"""
        data = {
            'class_id': test_class.id,
            'notes': ''
        }

        serializer = BookingCreateSerializer(data=data)
        assert serializer.is_valid()
