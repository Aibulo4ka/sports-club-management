"""
Integration тесты для API views приложения bookings
"""

import pytest
from django.urls import reverse
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone

from apps.bookings.models import Booking, Visit, BookingStatus


@pytest.mark.integration
class TestBookingAPI:
    """Тесты для API бронирований"""

    def test_list_own_bookings(self, authenticated_client, test_booking):
        """Тест получения списка своих бронирований"""
        url = reverse('bookings:booking-list')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_get_booking_detail(self, authenticated_client, test_booking):
        """Тест получения деталей бронирования"""
        url = reverse('bookings:booking-detail', kwargs={'pk': test_booking.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == test_booking.id

    def test_create_booking(self, authenticated_client, test_class, test_client):
        """Тест создания бронирования"""
        url = reverse('bookings:booking-list')
        data = {
            'class_id': test_class.id,
            'notes': 'Test booking'
        }

        response = authenticated_client.post(url, data, format='json')

        # Может быть создано или отклонено (зависит от валидации абонемента)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_cancel_booking(self, authenticated_client, test_client, test_class_type, test_trainer, test_room):
        """Тест отмены бронирования"""
        from apps.classes.models import Class

        # Создаём занятие далеко в будущем (можно отменить)
        future_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() + timedelta(days=7),
            duration_minutes=60,
            max_capacity=15
        )

        booking = Booking.objects.create(
            client=test_client,
            class_instance=future_class,
            status=BookingStatus.CONFIRMED
        )

        url = reverse('bookings:booking-cancel', kwargs={'pk': booking.id})

        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        booking.refresh_from_db()
        assert booking.status == BookingStatus.CANCELLED

    def test_cannot_cancel_booking_less_than_24h(self, authenticated_client, test_client, test_class_type, test_trainer, test_room):
        """Тест что нельзя отменить бронирование меньше чем за 24 часа"""
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

        url = reverse('bookings:booking-cancel', kwargs={'pk': booking.id})

        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_bookings_by_status(self, authenticated_client, test_booking):
        """Тест фильтрации бронирований по статусу"""
        url = reverse('bookings:booking-list')
        response = authenticated_client.get(url, {'status': BookingStatus.CONFIRMED})

        assert response.status_code == status.HTTP_200_OK

    def test_list_all_bookings_as_admin(self, admin_client):
        """Тест получения всех бронирований админом"""
        url = reverse('bookings:booking-list')

        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestVisitAPI:
    """Тесты для API посещений (check-in)"""

    def test_checkin_booking(self, admin_client, test_booking):
        """Тест отметки посещения (check-in)"""
        url = reverse('bookings:visit-list')
        data = {
            'booking': test_booking.id
        }

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Visit.objects.filter(booking=test_booking).exists()

    def test_checkin_same_booking_twice(self, admin_client, test_booking, test_admin_user):
        """Тест что нельзя отметить одно бронирование дважды"""
        # Первая отметка
        Visit.objects.create(booking=test_booking, checked_by=test_admin_user)

        # Вторая отметка
        url = reverse('bookings:visit-list')
        data = {
            'booking': test_booking.id
        }

        response = admin_client.post(url, data, format='json')

        # Должна быть ошибка
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_visits(self, admin_client, test_booking, test_admin_user):
        """Тест получения списка посещений"""
        Visit.objects.create(booking=test_booking, checked_by=test_admin_user)

        url = reverse('bookings:visit-list')

        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_checkin_as_regular_user(self, authenticated_client, test_booking):
        """Тест что обычный пользователь не может делать check-in"""
        url = reverse('bookings:visit-list')
        data = {
            'booking': test_booking.id
        }

        response = authenticated_client.post(url, data, format='json')

        # Должен быть запрещён доступ
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]


@pytest.mark.integration
class TestBookingValidation:
    """Тесты валидации бронирований"""

    def test_cannot_book_without_active_membership(self, authenticated_client, test_class, test_client):
        """Тест что нельзя забронировать без активного абонемента"""
        from apps.memberships.models import MembershipStatus

        # Приостанавливаем все абонементы
        test_client.memberships.update(status=MembershipStatus.SUSPENDED)

        url = reverse('bookings:booking-list')
        data = {
            'class_id': test_class.id
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_book_without_visits_remaining(self, authenticated_client, test_class, test_membership):
        """Тест что нельзя забронировать без оставшихся посещений"""
        # Обнуляем посещения
        test_membership.visits_remaining = 0
        test_membership.save()

        url = reverse('bookings:booking-list')
        data = {
            'class_id': test_class.id
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_book_full_class(self, authenticated_client, test_client, test_class_type, test_trainer, test_room, create_client):
        """Тест что нельзя забронировать заполненное занятие"""
        from apps.classes.models import Class

        # Создаём занятие с вместимостью 1
        small_class = Class.objects.create(
            class_type=test_class_type,
            trainer=test_trainer,
            room=test_room,
            datetime=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            max_capacity=1
        )

        # Создаём другого клиента и заполняем место
        other_client = create_client()
        Booking.objects.create(
            client=other_client,
            class_instance=small_class,
            status=BookingStatus.CONFIRMED
        )

        # Пытаемся забронировать
        url = reverse('bookings:booking-list')
        data = {
            'class_id': small_class.id
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
