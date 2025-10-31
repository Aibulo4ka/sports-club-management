"""
Factory Pattern - ClassFactory
Создание разных типов занятий с предустановленными настройками
"""

from typing import Dict, Any
from apps.classes.models import Class, ClassType
from apps.accounts.models import Trainer
from apps.facilities.models import Room
from datetime import datetime


class ClassFactory:
    """
    Factory for creating different types of classes with default settings
    """

    # Default durations for different class types (in minutes)
    DEFAULT_DURATIONS: Dict[str, int] = {
        'yoga': 60,
        'fitness': 90,
        'boxing': 60,
        'swimming': 45,
        'pilates': 60,
        'zumba': 60,
        'spinning': 45,
    }

    # Default capacities for different class types
    DEFAULT_CAPACITIES: Dict[str, int] = {
        'yoga': 15,
        'fitness': 20,
        'boxing': 10,
        'swimming': 8,
        'pilates': 12,
        'zumba': 25,
        'spinning': 15,
    }

    @classmethod
    def create_class(
        cls,
        class_type: ClassType,
        trainer: Trainer,
        room: Room,
        datetime: datetime,
        **kwargs
    ) -> Class:
        """
        Create a class instance with smart defaults based on class type

        Args:
            class_type: Type of the class
            trainer: Assigned trainer
            room: Room where class takes place
            datetime: Date and time of the class
            **kwargs: Override default settings

        Returns:
            Class instance (not saved to database)
        """
        # Determine default duration
        class_type_name = class_type.name.lower()
        duration = kwargs.get('duration_minutes') or cls._get_default_duration(class_type_name)

        # Determine default capacity (min of room capacity and type default)
        type_capacity = cls._get_default_capacity(class_type_name)
        max_capacity = kwargs.get('max_capacity') or min(room.capacity, type_capacity)

        # Create class instance
        class_instance = Class(
            class_type=class_type,
            trainer=trainer,
            room=room,
            datetime=datetime,
            duration_minutes=duration,
            max_capacity=max_capacity,
            status=kwargs.get('status', 'SCHEDULED'),
            notes=kwargs.get('notes', '')
        )

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
    def create_yoga_class(cls, trainer: Trainer, room: Room, datetime: datetime) -> Class:
        """Quick create yoga class"""
        class_type = ClassType.objects.get_or_create(name='Yoga')[0]
        return cls.create_class(class_type, trainer, room, datetime)

    @classmethod
    def create_fitness_class(cls, trainer: Trainer, room: Room, datetime: datetime) -> Class:
        """Quick create fitness class"""
        class_type = ClassType.objects.get_or_create(name='Fitness')[0]
        return cls.create_class(class_type, trainer, room, datetime)

    @classmethod
    def create_boxing_class(cls, trainer: Trainer, room: Room, datetime: datetime) -> Class:
        """Quick create boxing class"""
        class_type = ClassType.objects.get_or_create(name='Boxing')[0]
        return cls.create_class(class_type, trainer, room, datetime)
