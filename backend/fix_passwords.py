#!/usr/bin/env python
"""
Скрипт для исправления паролей тестовых пользователей
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth.models import User

print("=" * 60)
print("🔑 ИСПРАВЛЕНИЕ ПАРОЛЕЙ")
print("=" * 60)

users_to_fix = [
    ('admin', 'admin123'),
    ('client1', 'client123'),
    ('student1', 'student123'),
    ('trainer1', 'trainer123'),
]

for username, password in users_to_fix:
    try:
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
        print(f"✅ {username}: пароль установлен на '{password}'")
    except User.DoesNotExist:
        print(f"⚠️  {username}: пользователь не найден")

print("=" * 60)
print("✅ ГОТОВО! Теперь можно входить:")
print("-" * 60)
print("client1  / client123")
print("student1 / student123")
print("trainer1 / trainer123")
print("admin    / admin123")
print("=" * 60)
