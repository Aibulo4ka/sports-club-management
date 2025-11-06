"""
Signals для автоматического создания связанных объектов
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile, Client, Trainer, UserRole


@receiver(post_save, sender=Profile)
def create_role_specific_profile(sender, instance, created, **kwargs):
    """
    Автоматически создаёт Client или Trainer запись при создании Profile
    в зависимости от роли
    """
    if created:
        if instance.role == UserRole.CLIENT:
            # Создаём запись Client, если её ещё нет
            if not hasattr(instance, 'client_info'):
                Client.objects.create(profile=instance)
        elif instance.role == UserRole.TRAINER:
            # Создаём запись Trainer, если её ещё нет
            if not hasattr(instance, 'trainer_info'):
                Trainer.objects.create(
                    profile=instance,
                    specialization='Не указано',
                    experience_years=0
                )
    else:
        # Если роль изменилась, создаём соответствующую запись
        if instance.role == UserRole.CLIENT and not hasattr(instance, 'client_info'):
            Client.objects.create(profile=instance)
        elif instance.role == UserRole.TRAINER and not hasattr(instance, 'trainer_info'):
            Trainer.objects.create(
                profile=instance,
                specialization='Не указано',
                experience_years=0
            )
