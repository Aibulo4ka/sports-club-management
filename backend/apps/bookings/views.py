"""
Views (ViewSets) для бронирований и посещений
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction

from .models import Booking, Visit, BookingStatus
from .serializers import BookingSerializer, VisitSerializer, BookingCreateSerializer
from apps.classes.models import Class
from apps.accounts.models import Client
from .tasks import send_booking_confirmation_email


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления бронированиями

    Endpoints:
    - GET /api/bookings/ - список всех бронирований (для админа)
    - GET /api/bookings/my/ - мои бронирования (для клиента)
    - POST /api/bookings/ - создать бронирование
    - DELETE /api/bookings/{id}/cancel/ - отменить бронирование
    """
    queryset = Booking.objects.select_related(
        'client__profile__user',
        'class_instance__class_type',
        'class_instance__trainer__profile__user',
        'class_instance__room'
    ).all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Фильтруем queryset в зависимости от роли пользователя
        Клиенты видят только свои бронирования
        """
        user = self.request.user

        # Если пользователь - клиент, показываем только его бронирования
        if hasattr(user, 'profile') and user.profile.role == 'CLIENT':
            try:
                client = user.profile.client
                return self.queryset.filter(client=client)
            except Client.DoesNotExist:
                return self.queryset.none()

        # Для админов и тренеров - все бронирования
        return self.queryset

    @action(detail=False, methods=['get'])
    def my(self, request):
        """
        Получить мои бронирования (для текущего клиента)
        GET /api/bookings/my/
        """
        if not hasattr(request.user, 'profile'):
            return Response(
                {'error': 'Пользователь не имеет профиля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = request.user.profile.client
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Фильтруем по статусу если указан в query params
        bookings = self.queryset.filter(client=client)
        booking_status = request.query_params.get('status')
        if booking_status:
            bookings = bookings.filter(status=booking_status)

        # Сортировка: предстоящие первыми
        bookings = bookings.order_by('class_instance__datetime')

        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Создать новое бронирование
        POST /api/bookings/

        Использует упрощённый сериализатор, клиент передаёт только:
        {
            "class_id": 123,
            "notes": "опционально"
        }
        """
        # Используем упрощённый сериализатор для входных данных
        create_serializer = BookingCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        # Получаем клиента из профиля текущего пользователя
        if not hasattr(request.user, 'profile'):
            return Response(
                {'error': 'Пользователь не имеет профиля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = request.user.profile.client
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Получаем занятие
        class_id = create_serializer.validated_data['class_id']
        class_instance = Class.objects.get(id=class_id)

        # Создаём данные для полного сериализатора
        booking_data = {
            'client': client.id,
            'class_instance': class_instance.id,
            'notes': create_serializer.validated_data.get('notes', ''),
            'status': BookingStatus.CONFIRMED
        }

        # Валидируем и сохраняем через основной сериализатор
        serializer = self.get_serializer(data=booking_data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Уменьшаем количество оставшихся посещений в абонементе
        active_membership = client.memberships.filter(
            status='ACTIVE',
            start_date__lte=class_instance.datetime.date(),
            end_date__gte=class_instance.datetime.date()
        ).first()

        if active_membership and active_membership.visits_remaining is not None:
            active_membership.visits_remaining -= 1
            active_membership.save()

        # Отправляем email подтверждение асинхронно через Celery
        send_booking_confirmation_email.delay(booking.id)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Отменить бронирование
        POST /api/bookings/{id}/cancel/

        Правила отмены:
        - Можно отменить только за 24 часа до занятия
        - Бронирование должно быть в статусе CONFIRMED
        """
        booking = self.get_object()

        # Проверяем, что бронирование принадлежит текущему клиенту
        if hasattr(request.user, 'profile'):
            try:
                client = request.user.profile.client
                if booking.client != client and request.user.profile.role != 'ADMIN':
                    return Response(
                        {'error': 'Вы не можете отменить чужое бронирование'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Client.DoesNotExist:
                pass

        # Проверяем статус
        if booking.status != BookingStatus.CONFIRMED:
            return Response(
                {'error': 'Можно отменить только подтверждённое бронирование'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем время до занятия (минимум 24 часа)
        time_until_class = booking.class_instance.datetime - timezone.now()
        if time_until_class < timezone.timedelta(hours=24):
            return Response(
                {'error': 'Отмена возможна не менее чем за 24 часа до начала занятия'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Отменяем бронирование
        with transaction.atomic():
            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = timezone.now()
            booking.save()

            # Возвращаем посещение в абонемент (если лимитированный)
            active_membership = booking.client.memberships.filter(
                status='ACTIVE',
                start_date__lte=booking.class_instance.datetime.date(),
                end_date__gte=booking.class_instance.datetime.date()
            ).first()

            if active_membership and active_membership.visits_remaining is not None:
                active_membership.visits_remaining += 1
                active_membership.save()

        serializer = self.get_serializer(booking)
        return Response({
            'message': 'Бронирование успешно отменено',
            'booking': serializer.data
        })


class VisitViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления посещениями (check-in)

    Используется администраторами и тренерами для отметки фактического посещения
    """
    queryset = Visit.objects.select_related(
        'booking__client__profile__user',
        'booking__class_instance',
        'checked_by'
    ).all()
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Отметить посещение клиента
        POST /api/visits/

        Body: {"booking": <booking_id>}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = serializer.validated_data['booking']

        # Проверяем, что бронирование в статусе CONFIRMED
        if booking.status != BookingStatus.CONFIRMED:
            return Response(
                {'error': 'Можно отметить только подтверждённое бронирование'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, что посещение ещё не отмечено
        if hasattr(booking, 'visit'):
            return Response(
                {'error': 'Посещение уже отмечено'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Создаём отметку посещения
        visit = serializer.save(checked_by=request.user)

        # Обновляем статус бронирования
        booking.status = BookingStatus.COMPLETED
        booking.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
