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
    """Исключение, возникающее при конфликте в расписании"""
    pass


class ClassFactory:
    """
    Фабрика для создания различных типов занятий с настройками по умолчанию
    Использует паттерн Factory для инкапсуляции логики создания занятий
    """

    # Длительность по умолчанию для разных типов занятий (в минутах)
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

    # Вместимость по умолчанию для разных типов занятий
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
        Создать экземпляр занятия с умными настройками по умолчанию на основе типа занятия

        Args:
            class_type: Тип занятия
            trainer: Назначенный тренер
            room: Зал, где проходит занятие
            datetime_obj: Дата и время занятия
            check_conflicts: Проверять ли конфликты в расписании
            save: Сохранять ли экземпляр в базу данных
            **kwargs: Переопределить настройки по умолчанию (duration_minutes, max_capacity, status, notes)

        Returns:
            Экземпляр занятия (Class)

        Raises:
            ClassConflictError: Если есть конфликт в расписании и check_conflicts=True
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
        """Получить длительность по умолчанию для типа занятия"""
        return cls.DEFAULT_DURATIONS.get(class_type_name, 60)

    @classmethod
    def _get_default_capacity(cls, class_type_name: str) -> int:
        """Получить вместимость по умолчанию для типа занятия"""
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
        Проверить конфликты в расписании тренера и зала

        Args:
            trainer: Тренер для проверки
            room: Зал для проверки
            datetime_obj: Время начала
            duration_minutes: Длительность в минутах
            exclude_id: ID занятия, которое нужно исключить из проверки (для обновлений)

        Raises:
            ClassConflictError: Если найден конфликт
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
        Проверить, свободны ли тренер и зал (версия без выброса исключений)

        Returns:
            Кортеж (доступно_ли, сообщение_о_конфликте)
        """
        try:
            cls._check_conflicts(trainer, room, datetime_obj, duration_minutes)
            return True, None
        except ClassConflictError as e:
            return False, str(e)

    @classmethod
    def create_yoga_class(cls, trainer: Trainer, room: Room, datetime_obj: datetime, **kwargs) -> Class:
        """Быстрое создание занятия йогой"""
        class_type = ClassType.objects.filter(name__iexact='yoga').first()
        if not class_type:
            raise ValueError("ClassType 'Yoga' не найден. Создайте его в админке.")
        return cls.create_class(class_type, trainer, room, datetime_obj, **kwargs)

    @classmethod
    def create_fitness_class(cls, trainer: Trainer, room: Room, datetime_obj: datetime, **kwargs) -> Class:
        """Быстрое создание занятия фитнесом"""
        class_type = ClassType.objects.filter(name__iexact='fitness').first()
        if not class_type:
            raise ValueError("ClassType 'Fitness' не найден. Создайте его в админке.")
        return cls.create_class(class_type, trainer, room, datetime_obj, **kwargs)

    @classmethod
    def create_boxing_class(cls, trainer: Trainer, room: Room, datetime_obj: datetime, **kwargs) -> Class:
        """Быстрое создание занятия боксом"""
        class_type = ClassType.objects.filter(name__iexact='boxing').first()
        if not class_type:
            raise ValueError("ClassType 'Boxing' не найден. Создайте его в админке.")
        return cls.create_class(class_type, trainer, room, datetime_obj, **kwargs)
