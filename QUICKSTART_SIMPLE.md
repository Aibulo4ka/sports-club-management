# 🚀 Простой запуск проекта (БЕЗ Docker, БЕЗ PostgreSQL)

Упрощённая версия для быстрого старта разработки.

**Что используется:**
- ✅ SQLite (встроенная БД Django) - установка не нужна
- ✅ Dummy Cache (без Redis) - установка не нужна
- ✅ Только Python

---

## Шаг 1: Проверьте Python

```powershell
python --version
```

Должно быть **Python 3.11** или выше.

Если нет - скачайте с https://www.python.org/downloads/

---

## Шаг 2: Перейдите в папку backend

```powershell
cd "C:\Users\Admin\Documents\3 курс\Семестр 1\ПИ\Курсовой_проект\backend"
```

---

## Шаг 3: Создайте виртуальное окружение

```powershell
python -m venv venv
```

Активируйте его:

```powershell
venv\Scripts\activate
```

После активации в начале строки появится `(venv)`.

---

## Шаг 4: Установите зависимости

```powershell
pip install django djangorestframework django-cors-headers django-filter djangorestframework-simplejwt python-decouple pillow
```

Это установит только необходимые пакеты (без PostgreSQL, Redis, Celery).

---

## Шаг 5: Примените миграции

```powershell
python manage.py migrate
```

Вы должны увидеть что-то вроде:
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, accounts, memberships, classes, bookings, payments, facilities
Running migrations:
  Applying contenttypes.0001_initial... OK
  ...
```

Будет создан файл `db.sqlite3` - это ваша база данных.

---

## Шаг 6: Создайте суперпользователя

```powershell
python manage.py createsuperuser
```

Введите:
- **Username:** admin (или любое другое)
- **Email:** admin@example.com (или оставьте пустым)
- **Password:** admin123 (или любой другой, минимум 8 символов)

---

## Шаг 7: Создайте профиль для суперпользователя

```powershell
python manage.py shell
```

В открывшемся shell выполните:

```python
from django.contrib.auth.models import User
from apps.accounts.models import Profile, UserRole

user = User.objects.first()
Profile.objects.create(
    user=user,
    phone='+79991234567',
    role=UserRole.ADMIN
)
print("Профиль создан!")
exit()
```

---

## Шаг 8: Запустите сервер

```powershell
python manage.py runserver
```

Вы должны увидеть:

```
Django version 4.2.x, using settings 'config.settings.dev'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

---

## Шаг 9: Откройте браузер

### Главная страница:
http://127.0.0.1:8000/

### Админ-панель:
http://127.0.0.1:8000/admin

Войдите с учётными данными суперпользователя (admin / admin123).

---

## 🎉 Готово!

Теперь вы можете:

1. **Изучить админ-панель:**
   - Создать типы абонементов
   - Создать залы
   - Создать типы занятий
   - Добавить тренеров

2. **Создать тестовые данные** (см. ниже)

3. **Начать разработку Sprint 2**

---

## Создание тестовых данных

### Через Django shell:

```powershell
python manage.py shell
```

### 1. Создать типы абонементов:

```python
from apps.memberships.models import MembershipType
from decimal import Decimal

MembershipType.objects.create(
    name="Месячный абонемент",
    description="Безлимитное посещение в течение месяца",
    price=Decimal("5000.00"),
    duration_days=30,
    visits_limit=None
)

MembershipType.objects.create(
    name="Годовой абонемент",
    description="Безлимитное посещение в течение года",
    price=Decimal("50000.00"),
    duration_days=365,
    visits_limit=None
)

MembershipType.objects.create(
    name="8 занятий",
    description="8 занятий в течение месяца",
    price=Decimal("3000.00"),
    duration_days=30,
    visits_limit=8
)

print("✅ Типы абонементов созданы!")
```

### 2. Создать типы занятий:

```python
from apps.classes.models import ClassType

ClassType.objects.create(name="Йога", description="Йога для начинающих", duration_minutes=60)
ClassType.objects.create(name="Фитнес", description="Силовые тренировки", duration_minutes=90)
ClassType.objects.create(name="Бокс", description="Бокс и кикбоксинг", duration_minutes=60)
ClassType.objects.create(name="Плавание", description="Плавание в бассейне", duration_minutes=45)

print("✅ Типы занятий созданы!")
```

### 3. Создать залы:

```python
from apps.facilities.models import Room

Room.objects.create(name="Главный зал", description="Большой зал", capacity=25, floor=1)
Room.objects.create(name="Зал йоги", description="Уютный зал для йоги", capacity=15, floor=2)
Room.objects.create(name="Боксерский ринг", description="Ринг для бокса", capacity=10, floor=1)
Room.objects.create(name="Бассейн", description="25-метровый бассейн", capacity=8, floor=-1)

print("✅ Залы созданы!")
```

### 4. Создать тренера:

```python
from django.contrib.auth.models import User
from apps.accounts.models import Profile, Trainer, UserRole

# Создать пользователя для тренера
trainer_user = User.objects.create_user(
    username='trainer1',
    email='trainer@sportclub.com',
    password='trainer123',
    first_name='Иван',
    last_name='Петров'
)

# Создать профиль
trainer_profile = Profile.objects.create(
    user=trainer_user,
    phone='+79991234568',
    role=UserRole.TRAINER
)

# Создать информацию о тренере
Trainer.objects.create(
    profile=trainer_profile,
    specialization='Йога и пилатес',
    experience_years=5,
    bio='Сертифицированный инструктор по йоге'
)

print("✅ Тренер создан!")
exit()
```

---

## Полезные команды

### Запуск сервера:
```powershell
python manage.py runserver
```

### Остановка сервера:
`Ctrl+C` в терминале

### Открыть Django shell:
```powershell
python manage.py shell
```

### Создать новые миграции (после изменения моделей):
```powershell
python manage.py makemigrations
python manage.py migrate
```

### Посмотреть все URL:
```powershell
python manage.py show_urls
```

---

## Что НЕ работает в упрощённой версии

❌ **Celery задачи** (напоминания, периодические задачи)
- Для этого нужен Redis + Celery worker
- Можно добавить позже

❌ **Кеширование**
- Используется Dummy Cache (всё работает, просто без кеша)
- Можно добавить Redis позже

❌ **Real-time обновления**
- Для этого нужны WebSockets (Django Channels)

✅ **Всё остальное работает полностью!**
- Аутентификация
- Админ-панель
- Модели данных
- API endpoints (будут в Sprint 2)
- Frontend страницы

---

## Переход на PostgreSQL + Redis (потом)

Когда захотите перейти на полный стек:

1. Установите PostgreSQL и Redis
2. Измените `backend/config/settings/dev.py`:
   - Раскомментируйте настройки PostgreSQL
   - Раскомментируйте настройки Redis
3. Запустите Celery worker

Или используйте Docker (см. QUICKSTART.md).

---

## Troubleshooting

### Ошибка "No module named 'apps'"

Убедитесь что вы в папке `backend/`:
```powershell
cd backend
```

### Ошибка "table already exists"

Удалите файл `db.sqlite3` и повторите миграции:
```powershell
del db.sqlite3
python manage.py migrate
```

### Виртуальное окружение не активируется

Попробуйте:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\activate
```

### Забыли пароль суперпользователя

Создайте нового:
```powershell
python manage.py createsuperuser
```

---

## 🎓 Для курсового проекта этого достаточно!

SQLite отлично подходит для:
- ✅ Разработки
- ✅ Тестирования
- ✅ Демонстрации функционала
- ✅ Защиты курсового проекта

PostgreSQL нужен только для production деплоя на реальный сервер.

---

**Хорошей разработки!** 🚀
