"""
API views for classes app (REST API)
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime, timedelta

from .models import ClassType, Class, ClassStatus
from .serializers import (
    ClassTypeSerializer,
    ClassSerializer, ClassCreateSerializer, ClassUpdateSerializer,
    ClassAvailabilitySerializer
)


class ClassTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ClassType CRUD operations

    Provides:
    - list: GET /api/classes/types/
    - create: POST /api/classes/types/ (admin only)
    - retrieve: GET /api/classes/types/{id}/
    - update: PUT/PATCH /api/classes/types/{id}/ (admin only)
    - destroy: DELETE /api/classes/types/{id}/ (admin only - deactivate)
    """
    queryset = ClassType.objects.all()
    serializer_class = ClassTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'duration_minutes']
    ordering = ['name']

    def get_permissions(self):
        """
        Admin only for create/update/delete
        Read operations are public
        """
        if self.action in ['list', 'retrieve', 'active']:
            return [AllowAny()]
        return [IsAdminUser()]

    def perform_destroy(self, instance):
        """Soft delete: deactivate instead of deleting"""
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def active(self, request):
        """
        Get only active class types
        GET /api/classes/types/active/
        """
        active_types = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_types, many=True)
        return Response(serializer.data)


class ClassViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Class operations with smart filtering

    Provides:
    - list: GET /api/classes/
    - create: POST /api/classes/ (admin only)
    - retrieve: GET /api/classes/{id}/
    - update: PUT/PATCH /api/classes/{id}/ (admin only)
    - destroy: DELETE /api/classes/{id}/ (admin only - cancel)
    """
    queryset = Class.objects.select_related(
        'class_type', 'trainer__profile__user', 'room'
    ).all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'trainer', 'room', 'class_type']
    search_fields = ['class_type__name', 'trainer__profile__user__first_name',
                    'trainer__profile__user__last_name', 'room__name']
    ordering_fields = ['datetime', 'max_capacity']
    ordering = ['datetime']

    def get_permissions(self):
        """
        Admin for create/update/delete
        Authenticated users can view
        """
        if self.action in ['list', 'retrieve', 'today', 'week', 'upcoming', 'by_date']:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ClassCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClassUpdateSerializer
        return ClassSerializer

    def perform_destroy(self, instance):
        """Soft delete: cancel class instead of deleting"""
        instance.status = ClassStatus.CANCELLED
        instance.save()

    @action(detail=False, methods=['get'])
    def today(self, request):
        """
        Get today's classes
        GET /api/classes/today/
        """
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        today_classes = self.queryset.filter(
            datetime__gte=today_start,
            datetime__lt=today_end,
            status=ClassStatus.SCHEDULED
        ).order_by('datetime')

        serializer = self.get_serializer(today_classes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def week(self, request):
        """
        Get this week's classes
        GET /api/classes/week/
        """
        today = timezone.now()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        week_classes = self.queryset.filter(
            datetime__gte=week_start,
            datetime__lt=week_end,
            status=ClassStatus.SCHEDULED
        ).order_by('datetime')

        serializer = self.get_serializer(week_classes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming classes (next 30 days)
        GET /api/classes/upcoming/?days=30
        """
        days = int(request.query_params.get('days', 30))
        now = timezone.now()
        end_date = now + timedelta(days=days)

        upcoming_classes = self.queryset.filter(
            datetime__gte=now,
            datetime__lt=end_date,
            status=ClassStatus.SCHEDULED
        ).order_by('datetime')

        serializer = self.get_serializer(upcoming_classes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_date(self, request):
        """
        Get classes for specific date
        GET /api/classes/by_date/?date=2025-11-05
        """
        date_str = request.query_params.get('date')
        if not date_str:
            return Response(
                {'error': 'Параметр date обязателен (формат: YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        date_start = timezone.make_aware(datetime.combine(date_obj, datetime.min.time()))
        date_end = date_start + timedelta(days=1)

        date_classes = self.queryset.filter(
            datetime__gte=date_start,
            datetime__lt=date_end
        ).order_by('datetime')

        serializer = self.get_serializer(date_classes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def cancel(self, request, pk=None):
        """
        Cancel a class
        POST /api/classes/{id}/cancel/
        """
        class_instance = self.get_object()

        if class_instance.status == ClassStatus.CANCELLED:
            return Response(
                {'error': 'Занятие уже отменено'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if class_instance.status == ClassStatus.COMPLETED:
            return Response(
                {'error': 'Нельзя отменить завершённое занятие'},
                status=status.HTTP_400_BAD_REQUEST
            )

        class_instance.status = ClassStatus.CANCELLED
        class_instance.save()

        serializer = self.get_serializer(class_instance)
        return Response({
            'message': 'Занятие отменено',
            'class': serializer.data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def complete(self, request, pk=None):
        """
        Mark class as completed
        POST /api/classes/{id}/complete/
        """
        class_instance = self.get_object()

        if class_instance.status == ClassStatus.COMPLETED:
            return Response(
                {'error': 'Занятие уже завершено'},
                status=status.HTTP_400_BAD_REQUEST
            )

        class_instance.status = ClassStatus.COMPLETED
        class_instance.save()

        serializer = self.get_serializer(class_instance)
        return Response({
            'message': 'Занятие завершено',
            'class': serializer.data
        })

    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        """
        Check if trainer and room are available for specific time
        POST /api/classes/check_availability/

        Body:
        {
            "trainer_id": 1,
            "room_id": 2,
            "datetime": "2025-11-05T10:00:00Z",
            "duration_minutes": 60
        }
        """
        serializer = ClassAvailabilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Check availability
        availability = serializer.check()

        return Response(availability)
