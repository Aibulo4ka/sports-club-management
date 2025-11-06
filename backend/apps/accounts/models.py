"""
Models for accounts app: Client, Trainer profiles
Extends Django's built-in User model
"""

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import RegexValidator


class UserRole(models.TextChoices):
    """User roles in the system"""
    CLIENT = 'CLIENT', 'Клиент'
    TRAINER = 'TRAINER', 'Тренер'
    ADMIN = 'ADMIN', 'Администратор'


class Profile(models.Model):
    """
    Extended user profile for all users (clients, trainers, admins)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.CLIENT,
        verbose_name='Роль'
    )

    # Contact information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+79991234567'"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name='Телефон'
    )
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Дата рождения')

    # Additional fields
    photo = models.ImageField(upload_to='profiles/', null=True, blank=True, verbose_name='Фото')
    address = models.TextField(blank=True, verbose_name='Адрес')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class Client(models.Model):
    """
    Client-specific information
    Extends Profile for clients only
    """
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='client_info')

    # Client-specific fields
    is_student = models.BooleanField(default=False, verbose_name='Студент')
    emergency_contact = models.CharField(max_length=100, blank=True, verbose_name='Экстренный контакт')
    emergency_phone = models.CharField(max_length=17, blank=True, verbose_name='Телефон экстренного контакта')

    # Medical information (optional)
    medical_notes = models.TextField(blank=True, verbose_name='Медицинские заметки')

    # Group members (for group discount)
    group_members = models.ManyToManyField('self', blank=True, symmetrical=True, verbose_name='Участники группы')

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        return self.profile.user.get_full_name() or self.profile.user.username


class Trainer(models.Model):
    """
    Trainer-specific information
    Extends Profile for trainers only
    """
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='trainer_info')

    # Trainer-specific fields
    specialization = models.CharField(max_length=200, verbose_name='Специализация')
    experience_years = models.PositiveIntegerField(default=0, verbose_name='Опыт работы (лет)')
    bio = models.TextField(blank=True, verbose_name='Биография')
    certifications = models.TextField(blank=True, verbose_name='Сертификаты')

    # Availability
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Тренер'
        verbose_name_plural = 'Тренеры'

    def __str__(self):
        return f"{self.profile.user.get_full_name()} - {self.specialization}"
