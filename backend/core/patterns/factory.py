"""
Factory Pattern - ClassFactory
Создание разных типов занятий с предустановленными настройками
Включает проверку конфликтов расписания
"""

from typing import Dict, Any, Optional, Tuple
from apps.classes.models import Class, ClassType, ClassStatus
from apps.accounts.models import Trainer
from apps.facilities.models import Room
from datetime import datetime, timedelta
from django.db.models import Q


class ClassConflictError(Exception):
    """Exception raised when there's a scheduling conflict"""
    pass


class ClassFactory:
    """
    Factory for creating different types of classes with default settings
    Uses Factory pattern to encapsulate class creation logic
    """

    # Default durations for different class types (in minutes)
    DEFAULT_DURATIONS: Dict[str, int] = {
        'yoga': 60,
        'йога': 60,
        'fitness': 90,
        'фитнес': 90,
        'boxing': 60,
        'бокс': 60,
        'swimming': 45,
        'плавание': 45,
        'pilates': 60,
        'пилатес': 60,
        'zumba': 60,
        'зумба': 60,
        'spinning': 45,
        'сайклинг': 45,
        'stretching': 60,
        'стретчинг': 60,
    }

    # Default capacities for different class types
    DEFAULT_CAPACITIES: Dict[str, int] = {
        'yoga': 15,
        'йога': 15,
        'fitness': 20,
        'фитнес': 20,
        'boxing': 10,
        'бокс': 10,
        'swimming': 8,
        'плавание': 8,
        'pilates': 12,
        'пилатес': 12,
        'zumba': 25,
        'зумба': 25,
        'spinning': 15,
        'сайклинг': 15,
        'stretching': 15,
        'стретчинг': 15,
    }

    @classmethod
    def create_class(
        cls,
        class_type: ClassType,
        trainer: Trainer,
        room: Room,
        datetime_obj: datetime,
        check_conflicts: bool = True,
        save: bool = False,
        **kwargs
    ) -> Class:
        """
        Create a class instance with smart defaults based on class type

        Args:
            class_type: Type of the class
            trainer: Assigned trainer
            room: Room where class takes place
            datetime_obj: Date and time of the class
            check_conflicts: Whether to check for scheduling conflicts
            save: Whether to save the instance to database
            **kwargs: Override default settings (duration_minutes, max_capacity, status, notes)

        Returns:
            Class instance

        Raises:
            ClassConflictError: If there's a scheduling conflict and check_conflicts=True
        """
        # Determine default duration
        class_type_name = class_type.name.lower()
        duration = kwargs.get('duration_minutes')
        if duration is None:
            duration = cls._get_default_duration(class_type_name)
            # Fallback to class_type.duration_minutes if set
            if hasattr(class_type, 'duration_minutes') and class_type.duration_minutes:
                duration = class_type.duration_minutes

        # Determine default capacity (min of room capacity and type default)
        type_capacity = cls._get_default_capacity(class_type_name)
        max_capacity = kwargs.get('max_capacity')
        if max_capacity is None:
            max_capacity = min(room.capacity, type_capacity)

        # Check for conflicts before creating
        if check_conflicts:
            cls._check_conflicts(trainer, room, datetime_obj, duration, kwargs.get('exclude_id'))

        # Create class instance
        class_instance = Class(
            class_type=class_type,
            trainer=trainer,
            room=room,
            datetime=datetime_obj,
            duration_minutes=duration,
            max_capacity=max_capacity,
            status=kwargs.get('status', ClassStatus.SCHEDULED),
            notes=kwargs.get('notes', '')
        )

        if save:
            class_instance.save()

        return class_instance

    @classmethod
    def _get_default_duration(cls, class_type_name: str) -> int:
        """Get default duration for class type"""
        return cls.DEFAULT_DURATIONS.get(class_type_name, 60)

    @classmethod
    def _get_default_capacity(cls, class_type_name: str) -> int:
        """Get default capacity for class type"""
        return cls.DEFAULT_CAPACITIES.get(class_type_name, 15)

    @classmethod
    def _check_conflicts(
        cls,
        trainer: Trainer,
        room: Room,
        datetime_obj: datetime,
        duration_minutes: int,
        exclude_id: Optional[int] = None
    ) -> None:
        """
        Check for scheduling conflicts with trainer and room

        Args:
            trainer: Trainer to check
            room: Room to check
            datetime_obj: Start time
            duration_minutes: Duration in minutes
            exclude_id: Class ID to exclude from check (for updates)

        Raises:
            ClassConflictError: If conflict is found
        """
        end_time = datetime_obj + timedelta(minutes=duration_minutes)

        # Build base queryset
        queryset = Class.objects.filter(
            status__in=[ClassStatus.SCHEDULED, ClassStatus.IN_PROGRESS]
        )

        # Exclude current class if updating
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        # Check trainer conflicts
        trainer_conflicts = queryset.filter(
            trainer=trainer,
            datetime__lt=end_time,
            datetime__gte=datetime_obj - timedelta(hours=24)  # Search within 24h window
        )

        for conflict in trainer_conflicts:
            conflict_end = conflict.datetime + timedelta(minutes=conflict.duration_minutes)
            # Check if time ranges overlap
            if not (end_time <= conflict.datetime or datetime_obj >= conflict_end):
                raise ClassConflictError(
                    f"Тренер {trainer.profile.user.get_full_name()} уже занят в это время. "
                    f"Конфликт с занятием: {conflict.class_type.name} "
                    f"({conflict.datetime.strftime('%H:%M')}-"
                    f"{conflict_end.strftime('%H:%M')})"
                )

        # Check room conflicts
        room_conflicts = queryset.filter(
            room=room,
            datetime__lt=end_time,
            datetime__gte=datetime_obj - timedelta(hours=24)
        )

        for conflict in room_conflicts:
            conflict_end = conflict.datetime + timedelta(minutes=conflict.duration_minutes)
            if not (end_time <= conflict.datetime or datetime_obj >= conflict_end):
                raise ClassConflictError(
                    f"Зал '{room.name}' уже занят в это время. "
                    f"Конфликт с занятием: {conflict.class_type.name} "
                    f"({conflict.datetime.strftime('%H:%M')}-"
                    f"{conflict_end.strftime('%H:%M')})"
                )

    @classmethod
    def check_availability(
        cls,
        trainer: Trainer,
        room: Room,
        datetime_obj: datetime,
        duration_minutes: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if trainer and room are available (non-throwing version)

        Returns:
            Tuple of (is_available, conflict_message)
        """
        try:
            cls._check_conflicts(trainer, room, datetime_obj, duration_minutes)
            return True, None
        except ClassConflictError as e:
            return False, str(e)

    @classmethod
    def create_yoga_class(cls, trainer: Trainer, room: Room, datetime_obj: datetime, **kwargs) -> Class:
        """Quick create yoga class"""
        class_type = ClassType.objects.filter(name__iexact='yoga').first()
        if not class_type:
            raise ValueError("ClassType 'Yoga' не найден. Создайте его в админке.")
        return cls.create_class(class_type, trainer, room, datetime_obj, **kwargs)

    @classmethod
    def create_fitness_class(cls, trainer: Trainer, room: Room, datetime_obj: datetime, **kwargs) -> Class:
        """Quick create fitness class"""
        class_type = ClassType.objects.filter(name__iexact='fitness').first()
        if not class_type:
            raise ValueError("ClassType 'Fitness' не найден. Создайте его в админке.")
        return cls.create_class(class_type, trainer, room, datetime_obj, **kwargs)

    @classmethod
    def create_boxing_class(cls, trainer: Trainer, room: Room, datetime_obj: datetime, **kwargs) -> Class:
        """Quick create boxing class"""
        class_type = ClassType.objects.filter(name__iexact='boxing').first()
        if not class_type:
            raise ValueError("ClassType 'Boxing' не найден. Создайте его в админке.")
        return cls.create_class(class_type, trainer, room, datetime_obj, **kwargs)
