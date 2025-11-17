"""
Тестовый скрипт для проверки отправки email
Запуск: python test_email_send.py
"""

import os
import django

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("=" * 60)
print("ТЕСТИРОВАНИЕ ОТПРАВКИ EMAIL")
print("=" * 60)

print(f"\nEmail Backend: {settings.EMAIL_BACKEND}")
print(f"Email Host: {settings.EMAIL_HOST}")
print(f"Email Port: {settings.EMAIL_PORT}")
print(f"Email User: {settings.EMAIL_HOST_USER}")
print(f"Email Password: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'НЕ УСТАНОВЛЕН'}")
print(f"Default From: {settings.DEFAULT_FROM_EMAIL}")

print("\n" + "=" * 60)
print("ОТПРАВКА ТЕСТОВОГО ПИСЬМА")
print("=" * 60)

try:
    recipient = input("\nВведите email получателя (или Enter для Aibiy.2005@gmail.com): ").strip()
    if not recipient:
        recipient = "Aibiy.2005@gmail.com"

    print(f"\nОтправка тестового письма на {recipient}...")

    send_mail(
        subject='Тест email от АС УСК',
        message='Это тестовое письмо. Если вы его получили, значит email настроен правильно!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )

    print("✓ Письмо успешно отправлено!")
    print(f"Проверьте почту {recipient}")

except Exception as e:
    print(f"✗ Ошибка при отправке: {str(e)}")
    print("\nВозможные причины:")
    print("1. EMAIL_HOST_PASSWORD не установлен в .env файле")
    print("2. Не создан App Password в Gmail")
    print("3. Неверные настройки SMTP")
    print("\nИнструкция:")
    print("1. Зайди на https://myaccount.google.com/security")
    print("2. Включи двухфакторную аутентификацию")
    print("3. Создай App Password для Mail")
    print("4. Добавь пароль в .env: EMAIL_HOST_PASSWORD=твой_пароль")
