"""
Модели для AI Персонального тренера
"""
from django.db import models
from django.utils import timezone


class FitnessGoal(models.TextChoices):
    """Цели тренировок"""
    WEIGHT_LOSS = 'WEIGHT_LOSS', 'Похудение'
    MUSCLE_GAIN = 'MUSCLE_GAIN', 'Набор мышечной массы'
    ENDURANCE = 'ENDURANCE', 'Выносливость'
    FLEXIBILITY = 'FLEXIBILITY', 'Гибкость'
    GENERAL_FITNESS = 'GENERAL_FITNESS', 'Общая физическая подготовка'
    STRENGTH = 'STRENGTH', 'Силовые показатели'


class FitnessLevel(models.TextChoices):
    """Уровень физической подготовки"""
    BEGINNER = 'BEGINNER', 'Начальный'
    INTERMEDIATE = 'INTERMEDIATE', 'Средний'
    ADVANCED = 'ADVANCED', 'Продвинутый'


class WorkoutPlan(models.Model):
    """
    Программа тренировок, сгенерированная AI
    """
    client = models.ForeignKey(
        'accounts.Client',
        on_delete=models.CASCADE,
        related_name='workout_plans',
        verbose_name='Клиент'
    )

    # Параметры генерации
    goal = models.CharField(
        'Цель',
        max_length=50,
        choices=FitnessGoal.choices,
        default=FitnessGoal.GENERAL_FITNESS
    )
    fitness_level = models.CharField(
        'Уровень подготовки',
        max_length=20,
        choices=FitnessLevel.choices,
        default=FitnessLevel.BEGINNER
    )
    additional_info = models.TextField(
        'Дополнительная информация',
        blank=True,
        help_text='Ограничения, предпочтения, заболевания'
    )

    # Сгенерированный контент
    workout_content = models.TextField(
        'Программа тренировок',
        help_text='Сгенерированная AI программа в формате Markdown'
    )

    # Метаданные
    created_at = models.DateTimeField('Создан', default=timezone.now)
    is_active = models.BooleanField('Активный', default=True)

    class Meta:
        verbose_name = 'Программа тренировок'
        verbose_name_plural = 'Программы тренировок'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"План для {self.client.profile.user.get_full_name()} от {self.created_at.strftime('%d.%m.%Y')}"


class NutritionPlan(models.Model):
    """
    План питания, сгенерированный AI
    """
    client = models.ForeignKey(
        'accounts.Client',
        on_delete=models.CASCADE,
        related_name='nutrition_plans',
        verbose_name='Клиент'
    )

    # Параметры генерации
    goal = models.CharField(
        'Цель',
        max_length=50,
        choices=FitnessGoal.choices,
        default=FitnessGoal.GENERAL_FITNESS
    )
    dietary_preferences = models.TextField(
        'Диетические предпочтения',
        blank=True,
        help_text='Вегетарианство, аллергии, предпочтения'
    )

    # Сгенерированный контент
    nutrition_content = models.TextField(
        'План питания',
        help_text='Сгенерированный AI план в формате Markdown'
    )

    # Метаданные
    created_at = models.DateTimeField('Создан', default=timezone.now)
    is_active = models.BooleanField('Активный', default=True)

    class Meta:
        verbose_name = 'План питания'
        verbose_name_plural = 'Планы питания'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"План питания для {self.client.profile.user.get_full_name()} от {self.created_at.strftime('%d.%m.%Y')}"


class AIChat(models.Model):
    """
    История вопросов и ответов AI тренера
    """
    client = models.ForeignKey(
        'accounts.Client',
        on_delete=models.CASCADE,
        related_name='ai_chats',
        verbose_name='Клиент'
    )

    question = models.TextField('Вопрос')
    answer = models.TextField('Ответ AI')

    # Контекст (опционально - для связи с планом)
    workout_plan = models.ForeignKey(
        WorkoutPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_messages',
        verbose_name='Программа тренировок'
    )

    created_at = models.DateTimeField('Создан', default=timezone.now)

    class Meta:
        verbose_name = 'AI диалог'
        verbose_name_plural = 'AI диалоги'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['client', 'created_at']),
        ]

    def __str__(self):
        return f"Вопрос от {self.client.profile.user.get_full_name()} в {self.created_at.strftime('%d.%m.%Y %H:%M')}"
