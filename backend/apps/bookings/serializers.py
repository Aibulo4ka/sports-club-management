"""
Сериализаторы для моделей Booking и Visit
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Booking, Visit, BookingStatus
from apps.classes.models import Class
from apps.accounts.models import Client


class BookingSerializer(serializers.ModelSerializer):
    """
    Сериализатор для Booking с логикой валидации
    """
    # Дополнительные поля только для чтения
    class_name = serializers.CharField(source='class_instance.class_type.name', read_only=True)
    trainer_name = serializers.CharField(source='class_instance.trainer.profile.user.get_full_name', read_only=True)
    room_name = serializers.CharField(source='class_instance.room.name', read_only=True)
    class_datetime = serializers.DateTimeField(source='class_instance.datetime', read_only=True)
    client_name = serializers.CharField(source='client.profile.user.get_full_name', read_only=True)
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'client', 'client_name', 'class_instance',
            'class_name', 'trainer_name', 'room_name', 'class_datetime',
            'booking_date', 'status', 'cancelled_at', 'notes', 'can_cancel'
        ]
        read_only_fields = ['booking_date', 'cancelled_at']

    def get_can_cancel(self, obj):
        """Проверяет, можно ли отменить бронирование (за 24 часа до занятия)"""
        if obj.status != BookingStatus.CONFIRMED:
            return False
        time_until_class = obj.class_instance.datetime - timezone.now()
        return time_until_class > timedelta(hours=24)

    def validate_class_instance(self, value):
        """
        Проверяет наличие свободных мест на занятии
        """
        # Используем существующий метод available_spots из модели Class
        if value.available_spots <= 0:
            raise serializers.ValidationError("Нет свободных мест на это занятие")

        # Проверяем, что занятие ещё не прошло
        if value.datetime < timezone.now():
            raise serializers.ValidationError("Нельзя забронировать занятие в прошлом")

        return value

    def validate(self, attrs):
        """
        Дополнительная валидация:
        1. У клиента должен быть активный абонемент
        2. Проверяем остаток посещений (если абонемент лимитированный)
        """
        client = attrs.get('client') or self.instance.client
        class_instance = attrs.get('class_instance') or self.instance.class_instance

        # Получаем активный абонемент клиента на дату занятия
        active_membership = client.memberships.filter(
            status='ACTIVE',
            start_date__lte=class_instance.datetime.date(),
            end_date__gte=class_instance.datetime.date()
        ).first()

        if not active_membership:
            raise serializers.ValidationError({
                'client': 'У клиента нет активного абонемента на дату занятия'
            })

        # Проверяем остаток посещений для лимитированных абонементов
        if active_membership.visits_remaining is not None:
            if active_membership.visits_remaining <= 0:
                raise serializers.ValidationError({
                    'client': 'У абонемента закончились посещения'
                })

        return attrs


class VisitSerializer(serializers.ModelSerializer):
    """
    Сериализатор для Visit (отметки посещения)
    """
    booking_info = BookingSerializer(source='booking', read_only=True)
    checked_by_name = serializers.CharField(source='checked_by.get_full_name', read_only=True)

    class Meta:
        model = Visit
        fields = ['id', 'booking', 'booking_info', 'checked_in_at', 'checked_by', 'checked_by_name']
        read_only_fields = ['checked_in_at']


class BookingCreateSerializer(serializers.Serializer):
    """
    Упрощённый сериализатор для создания бронирований
    Используется в API для клиента (нужен только ID занятия)
    """
    class_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_class_id(self, value):
        """Проверяет существование занятия"""
        try:
            class_instance = Class.objects.get(id=value)
        except Class.DoesNotExist:
            raise serializers.ValidationError("Занятие не найдено")
        return value
