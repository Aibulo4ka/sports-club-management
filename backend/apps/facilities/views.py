"""
API views for facilities app (REST API)
"""

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import Room
from .serializers import RoomSerializer, RoomDetailSerializer, RoomCreateUpdateSerializer


class RoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Room CRUD operations

    Provides:
    - list: GET /api/facilities/rooms/
    - create: POST /api/facilities/rooms/ (admin only)
    - retrieve: GET /api/facilities/rooms/{id}/
    - update: PUT/PATCH /api/facilities/rooms/{id}/ (admin only)
    - destroy: DELETE /api/facilities/rooms/{id}/ (admin only - deactivate)
    """
    queryset = Room.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'floor']
    search_fields = ['name', 'description', 'equipment']
    ordering_fields = ['name', 'floor', 'capacity']
    ordering = ['floor', 'name']

    def get_permissions(self):
        """
        Admin for create/update/delete
        Read operations are public
        """
        if self.action in ['list', 'retrieve', 'active', 'available']:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'retrieve':
            return RoomDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RoomCreateUpdateSerializer
        return RoomSerializer

    def perform_destroy(self, instance):
        """Soft delete: deactivate instead of deleting"""
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def active(self, request):
        """
        Get only active rooms
        GET /api/facilities/rooms/active/
        """
        active_rooms = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_rooms, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def available(self, request):
        """
        Get rooms available at specific datetime
        GET /api/facilities/rooms/available/?datetime=2025-11-05T10:00:00Z&duration=60

        Query params:
        - datetime: ISO format datetime
        - duration: duration in minutes (default: 60)
        """
        from django.utils import timezone
        from datetime import datetime, timedelta
        from apps.classes.models import Class, ClassStatus

        datetime_str = request.query_params.get('datetime')
        duration = int(request.query_params.get('duration', 60))

        if not datetime_str:
            return Response(
                {'error': 'Параметр datetime обязателен'},
                status=400
            )

        try:
            datetime_obj = timezone.make_aware(datetime.fromisoformat(datetime_str.replace('Z', '+00:00')))
        except ValueError:
            return Response(
                {'error': 'Неверный формат datetime. Используйте ISO формат'},
                status=400
            )

        end_time = datetime_obj + timedelta(minutes=duration)

        # Find rooms that are occupied during this time
        occupied_room_ids = []
        classes = Class.objects.filter(
            status__in=[ClassStatus.SCHEDULED, ClassStatus.IN_PROGRESS],
            datetime__lt=end_time
        ).select_related('room')

        for class_obj in classes:
            class_end = class_obj.datetime + timedelta(minutes=class_obj.duration_minutes)
            # Check if time ranges overlap
            if not (end_time <= class_obj.datetime or datetime_obj >= class_end):
                occupied_room_ids.append(class_obj.room.id)

        # Get available rooms
        available_rooms = self.queryset.filter(
            is_active=True
        ).exclude(id__in=occupied_room_ids)

        serializer = self.get_serializer(available_rooms, many=True)
        return Response({
            'datetime': datetime_obj.isoformat(),
            'duration_minutes': duration,
            'available_rooms': serializer.data,
            'total_available': available_rooms.count()
        })

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def schedule(self, request, pk=None):
        """
        Get schedule for specific room
        GET /api/facilities/rooms/{id}/schedule/?days=7

        Query params:
        - days: number of days to show (default: 7)
        """
        from django.utils import timezone
        from datetime import timedelta
        from apps.classes.models import Class, ClassStatus
        from apps.classes.serializers import ClassSerializer

        room = self.get_object()
        days = int(request.query_params.get('days', 7))

        now = timezone.now()
        end_date = now + timedelta(days=days)

        schedule = Class.objects.filter(
            room=room,
            datetime__gte=now,
            datetime__lt=end_date,
            status=ClassStatus.SCHEDULED
        ).select_related('class_type', 'trainer__profile__user').order_by('datetime')

        serializer = ClassSerializer(schedule, many=True)
        return Response({
            'room': RoomSerializer(room).data,
            'schedule': serializer.data,
            'total_classes': schedule.count()
        })
