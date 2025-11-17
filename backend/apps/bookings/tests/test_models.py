"""
Unit-тесты для моделей приложения bookings
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone
from apps.bookings.models import Booking, BookingStatus, Visit


@pytest.mark.unit
class TestBookingModel:
    """Тесты для модели Booking"""

    def test_create_booking(self, test_booking):
        """Тест создания бронирования"""
        assert test_booking.status == BookingStatus.CONFIRMED
        assert test_booking.class_instance is not None
        assert test_booking.client is not None

    def test_str_representation(self, test_booking):
        """Тест строкового представления"""
        result = str(test_booking)
        assert test_booking.client.profile.user.get_full_name() in result
        assert test_booking.get_status_display() in result

    def test_booking_statuses(self):
        """Тест всех статусов бронирования"""
        assert hasattr(BookingStatus, 'CONFIRMED')
        assert hasattr(BookingStatus, 'CANCELLED')
        assert hasattr(BookingStatus, 'COMPLETED')
        assert hasattr(BookingStatus, 'NO_SHOW')

    def test_unique_together_constraint(self, test_client, test_class):
        """Тест уникальности (клиент + занятие)"""
        from django.db import IntegrityError

        # Создаём первое бронирование
        Booking.objects.create(
            client=test_client,
            class_instance=test_class,
            status=BookingStatus.CONFIRMED
        )

        # Попытка создать дубликат должна вызвать ошибку
        with pytest.raises(IntegrityError):
            Booking.objects.create(
                client=test_client,
                class_instance=test_class,
                status=BookingStatus.CONFIRMED
            )

    def test_booking_ordering(self, test_client, test_class):
        """Тест сортировки по дате бронирования"""
        b1 = Booking.objects.create(
            client=test_client,
            class_instance=test_class,
            status=BookingStatus.CONFIRMED
        )

        b2 = Booking.objects.create(
            client=test_client,
            class_instance=test_class,
            status=BookingStatus.CANCELLED
        )

        bookings = list(Booking.objects.all())
        # Новые первыми (ordering = ['-booking_date'])
        assert bookings[0] == b2
        assert bookings[1] == b1

    def test_can_cancel_property_valid(self, test_client, test_class_type, test_trainer, test_room):
        """Тест свойства can_cancel - можно отменить"""
        from apps.classes.models import Class

        # Создаём занятие через 25 часов
        future_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() + timedelta(hours=25),
            duration_minutes=60,
            max_capacity=15
        )

        booking = Booking.objects.create(
            client=test_client,
            class_instance=future_class,
            status=BookingStatus.CONFIRMED
        )

        # Должно быть можно отменить (> 24 часов)
        assert booking.can_cancel == True

    def test_can_cancel_property_too_late(self, test_client, test_class_type, test_trainer, test_room):
        """Тест свойства can_cancel - слишком поздно"""
        from apps.classes.models import Class

        # Создаём занятие через 2 часа
        soon_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() + timedelta(hours=2),
            duration_minutes=60,
            max_capacity=15
        )

        booking = Booking.objects.create(
            client=test_client,
            class_instance=soon_class,
            status=BookingStatus.CONFIRMED
        )

        # Нельзя отменить (< 24 часов)
        assert booking.can_cancel == False

    def test_can_cancel_property_already_cancelled(self, test_booking):
        """Тест can_cancel для уже отменённого бронирования"""
        test_booking.status = BookingStatus.CANCELLED
        test_booking.save()

        assert test_booking.can_cancel == False

    def test_cancelled_at_field(self, test_booking):
        """Тест поля cancelled_at при отмене"""
        test_booking.status = BookingStatus.CANCELLED
        test_booking.cancelled_at = timezone.now()
        test_booking.save()

        assert test_booking.cancelled_at is not None


@pytest.mark.unit
class TestVisitModel:
    """Тесты для модели Visit"""

    def test_create_visit(self, test_booking, test_admin_user):
        """Тест создания посещения"""
        visit = Visit.objects.create(
            booking=test_booking,
            checked_by=test_admin_user
        )

        assert visit.booking == test_booking
        assert visit.checked_by == test_admin_user
        assert visit.checked_in_at is not None

    def test_str_representation(self, test_booking, test_admin_user):
        """Тест строкового представления"""
        visit = Visit.objects.create(
            booking=test_booking,
            checked_by=test_admin_user
        )

        expected = f"Visit: {test_booking}"
        assert str(visit) == expected

    def test_one_to_one_relationship(self, test_booking, test_admin_user):
        """Тест что у бронирования только одно посещение"""
        from django.db import IntegrityError

        # Создаём первое посещение
        Visit.objects.create(booking=test_booking, checked_by=test_admin_user)

        # Попытка создать второе должна вызвать ошибку
        with pytest.raises(IntegrityError):
            Visit.objects.create(booking=test_booking, checked_by=test_admin_user)

    def test_visit_ordering(self, test_client, test_class, test_admin_user):
        """Тест сортировки посещений"""
        b1 = Booking.objects.create(
            client=test_client,
            class_instance=test_class,
            status=BookingStatus.CONFIRMED
        )
        b2 = Booking.objects.create(
            client=test_client,
            class_instance=test_class,
            status=BookingStatus.CANCELLED
        )

        v1 = Visit.objects.create(booking=b1, checked_by=test_admin_user)
        v2 = Visit.objects.create(booking=b2, checked_by=test_admin_user)

        visits = list(Visit.objects.all())
        # Новые первыми
        assert visits[0] == v2
        assert visits[1] == v1

    def test_visit_accessible_from_booking(self, test_booking, test_admin_user):
        """Тест доступа к visit через booking"""
        visit = Visit.objects.create(booking=test_booking, checked_by=test_admin_user)

        assert test_booking.visit == visit
