"""
Serializers for classes app
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import ClassType, Class, ClassStatus
from apps.accounts.models import Trainer
from apps.facilities.models import Room
from core.patterns.factory import ClassFactory, ClassConflictError


class ClassTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for ClassType model
    """

    class Meta:
        model = ClassType
        fields = [
            'id', 'name', 'description', 'duration_minutes',
            'icon', 'is_active'
        ]
        read_only_fields = ['id']


class TrainerMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Trainer (for nested representation)
    """
    full_name = serializers.CharField(source='profile.user.get_full_name', read_only=True)
    email = serializers.EmailField(source='profile.user.email', read_only=True)
    photo = serializers.ImageField(source='profile.photo', read_only=True)

    class Meta:
        model = Trainer
        fields = ['id', 'full_name', 'email', 'specialization', 'photo']


class RoomMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for Room (for nested representation)
    """
    from apps.facilities.models import Room

    class Meta:
        model = Room
        fields = ['id', 'name', 'capacity', 'floor']


class ClassSerializer(serializers.ModelSerializer):
    """
    Serializer for Class model - for list/retrieve
    """
    class_type_details = ClassTypeSerializer(source='class_type', read_only=True)
    trainer_details = TrainerMinimalSerializer(source='trainer', read_only=True)
    room_details = RoomMinimalSerializer(source='room', read_only=True)

    # Computed fields
    available_spots = serializers.IntegerField(read_only=True)
    end_time = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = [
            'id', 'class_type', 'class_type_details',
            'trainer', 'trainer_details',
            'room', 'room_details',
            'datetime', 'duration_minutes', 'max_capacity',
            'status', 'notes', 'created_at', 'updated_at',
            'available_spots', 'end_time', 'is_full', 'is_past'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'available_spots',
                           'class_type_details', 'trainer_details', 'room_details']

    def get_end_time(self, obj):
        """Calculate end time of the class"""
        end_time = obj.datetime + timedelta(minutes=obj.duration_minutes)
        return end_time.isoformat()

    def get_is_full(self, obj):
        """Check if class is fully booked"""
        return obj.available_spots <= 0

    def get_is_past(self, obj):
        """Check if class is in the past"""
        return obj.datetime < timezone.now()


class ClassCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new class using ClassFactory
    """
    class_type_id = serializers.IntegerField()
    trainer_id = serializers.IntegerField()
    room_id = serializers.IntegerField()
    datetime = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(required=False, min_value=15, max_value=180)
    max_capacity = serializers.IntegerField(required=False, min_value=1, max_value=100)
    status = serializers.ChoiceField(choices=ClassStatus.choices, default=ClassStatus.SCHEDULED, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    check_conflicts = serializers.BooleanField(default=True, required=False)

    def validate_class_type_id(self, value):
        """Validate that class type exists and is active"""
        try:
            class_type = ClassType.objects.get(id=value)
            if not class_type.is_active:
                raise serializers.ValidationError("Этот тип занятия неактивен")
        except ClassType.DoesNotExist:
            raise serializers.ValidationError("Тип занятия с таким ID не найден")
        return value

    def validate_trainer_id(self, value):
        """Validate that trainer exists and is active"""
        try:
            trainer = Trainer.objects.get(id=value)
            if not trainer.is_active:
                raise serializers.ValidationError("Этот тренер неактивен")
        except Trainer.DoesNotExist:
            raise serializers.ValidationError("Тренер с таким ID не найден")
        return value

    def validate_room_id(self, value):
        """Validate that room exists"""
        try:
            Room.objects.get(id=value)
        except Room.DoesNotExist:
            raise serializers.ValidationError("Зал с таким ID не найден")
        return value

    def validate_datetime(self, value):
        """Validate that datetime is in the future"""
        if value < timezone.now():
            raise serializers.ValidationError("Нельзя создать занятие в прошлом")
        return value

    def create(self, validated_data):
        """Create class using ClassFactory"""
        class_type = ClassType.objects.get(id=validated_data['class_type_id'])
        trainer = Trainer.objects.get(id=validated_data['trainer_id'])
        room = Room.objects.get(id=validated_data['room_id'])

        check_conflicts = validated_data.pop('check_conflicts', True)

        # Remove IDs from kwargs
        validated_data.pop('class_type_id')
        validated_data.pop('trainer_id')
        validated_data.pop('room_id')
        datetime_obj = validated_data.pop('datetime')

        try:
            # Use ClassFactory to create the class
            class_instance = ClassFactory.create_class(
                class_type=class_type,
                trainer=trainer,
                room=room,
                datetime_obj=datetime_obj,
                check_conflicts=check_conflicts,
                save=True,
                **validated_data
            )
            return class_instance
        except ClassConflictError as e:
            raise serializers.ValidationError({'conflict': str(e)})

    def to_representation(self, instance):
        """Use ClassSerializer for output"""
        return ClassSerializer(instance).data


class ClassUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a class
    """
    check_conflicts = serializers.BooleanField(default=True, required=False, write_only=True)

    class Meta:
        model = Class
        fields = [
            'class_type', 'trainer', 'room', 'datetime',
            'duration_minutes', 'max_capacity', 'status', 'notes',
            'check_conflicts'
        ]

    def validate_datetime(self, value):
        """Validate that datetime is in the future (unless already past)"""
        instance = self.instance
        if instance and instance.datetime < timezone.now():
            # Allow updating past classes without datetime validation
            return value

        if value < timezone.now():
            raise serializers.ValidationError("Нельзя изменить время занятия на прошлое")
        return value

    def update(self, instance, validated_data):
        """Update class with conflict checking"""
        check_conflicts = validated_data.pop('check_conflicts', True)

        # If changing datetime, trainer, room, or duration - check conflicts
        if check_conflicts and any(field in validated_data for field in
                                  ['datetime', 'trainer', 'room', 'duration_minutes']):
            trainer = validated_data.get('trainer', instance.trainer)
            room = validated_data.get('room', instance.room)
            datetime_obj = validated_data.get('datetime', instance.datetime)
            duration = validated_data.get('duration_minutes', instance.duration_minutes)

            try:
                ClassFactory._check_conflicts(
                    trainer=trainer,
                    room=room,
                    datetime_obj=datetime_obj,
                    duration_minutes=duration,
                    exclude_id=instance.id
                )
            except ClassConflictError as e:
                raise serializers.ValidationError({'conflict': str(e)})

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class ClassAvailabilitySerializer(serializers.Serializer):
    """
    Serializer for checking class availability
    """
    trainer_id = serializers.IntegerField()
    room_id = serializers.IntegerField()
    datetime = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(default=60)

    def validate(self, attrs):
        """Validate that trainer and room exist"""
        try:
            Trainer.objects.get(id=attrs['trainer_id'])
        except Trainer.DoesNotExist:
            raise serializers.ValidationError("Тренер не найден")

        try:
            Room.objects.get(id=attrs['room_id'])
        except Room.DoesNotExist:
            raise serializers.ValidationError("Зал не найден")

        return attrs

    def check(self):
        """Check availability and return result"""
        trainer = Trainer.objects.get(id=self.validated_data['trainer_id'])
        room = Room.objects.get(id=self.validated_data['room_id'])

        is_available, conflict_message = ClassFactory.check_availability(
            trainer=trainer,
            room=room,
            datetime_obj=self.validated_data['datetime'],
            duration_minutes=self.validated_data['duration_minutes']
        )

        return {
            'is_available': is_available,
            'conflict_message': conflict_message,
            'trainer': TrainerMinimalSerializer(trainer).data,
            'room': RoomMinimalSerializer(room).data,
            'datetime': self.validated_data['datetime'].isoformat(),
            'duration_minutes': self.validated_data['duration_minutes']
        }
