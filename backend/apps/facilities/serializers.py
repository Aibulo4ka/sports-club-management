"""
Serializers for facilities app
"""

from rest_framework import serializers
from .models import Room


class RoomSerializer(serializers.ModelSerializer):
    """
    Serializer for Room model
    """

    class Meta:
        model = Room
        fields = [
            'id', 'name', 'description', 'capacity', 'floor',
            'equipment', 'photo', 'is_active'
        ]
        read_only_fields = ['id']


class RoomDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Room with schedule information
    """
    upcoming_classes_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id', 'name', 'description', 'capacity', 'floor',
            'equipment', 'photo', 'is_active', 'upcoming_classes_count'
        ]
        read_only_fields = ['id']

    def get_upcoming_classes_count(self, obj):
        """Get count of upcoming classes in this room"""
        from django.utils import timezone
        from apps.classes.models import Class, ClassStatus

        return obj.classes.filter(
            status=ClassStatus.SCHEDULED,
            datetime__gte=timezone.now()
        ).count()


class RoomCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating Room
    """

    class Meta:
        model = Room
        fields = [
            'name', 'description', 'capacity', 'floor',
            'equipment', 'photo', 'is_active'
        ]

    def validate_capacity(self, value):
        """Ensure capacity is reasonable"""
        if value < 1:
            raise serializers.ValidationError("Вместимость должна быть минимум 1")
        if value > 200:
            raise serializers.ValidationError("Вместимость не может превышать 200")
        return value

    def validate_floor(self, value):
        """Ensure floor is reasonable"""
        if value < 1:
            raise serializers.ValidationError("Этаж должен быть минимум 1")
        if value > 50:
            raise serializers.ValidationError("Этаж не может превышать 50")
        return value
