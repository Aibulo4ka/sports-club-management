# Быстрый старт АС УСК

Руководство по запуску проекта для разработки.

## Предварительные требования

Убедитесь, что у вас установлено:
- Python 3.11 или выше
- PostgreSQL 15+
- Redis 7+
- Git

Или используйте Docker (рекомендуется).

## Запуск с Docker (Рекомендуется)

### 1. Клонируйте репозиторий и перейдите в директорию

```bash
cd "Курсовой_проект"
```

### 2. Создайте файл .env

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Отредактируйте `.env` и установите свои значения (для разработки можно оставить по умолчанию).

### 3. Запустите Docker Compose

```bash
docker-compose up -d
```

Это запустит:
- PostgreSQL на порту 5432
- Redis на порту 6379
- Django backend на порту 8000
- Celery worker
- Celery beat

### 4. Примените миграции

```bash
docker-compose exec backend python manage.py migrate
```

### 5. Создайте суперпользователя

```bash
docker-compose exec backend python manage.py createsuperuser
```

Следуйте инструкциям на экране.

### 6. Создайте профиль для суперпользователя (важно!)

Войдите в Django shell:

```bash
docker-compose exec backend python manage.py shell
```

Выполните:

```python
from django.contrib.auth.models import User
from apps.accounts.models import Profile, UserRole

user = User.objects.get(username='admin')  # Замените на ваш username
Profile.objects.create(
    user=user,
    phone='+79991234567',  # Укажите телефон
    role=UserRole.ADMIN
)
exit()
```

### 7. Откройте браузер

- **Главная страница:** http://localhost:8000
- **Админ-панель:** http://localhost:8000/admin

Войдите с учетными данными суперпользователя.

---

## Локальная установка (без Docker)

### 1. Создайте виртуальное окружение

```bash
cd backend
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Запустите PostgreSQL и Redis

Убедитесь, что PostgreSQL и Redis запущены локально.

**PostgreSQL:**
```bash
# Создайте базу данных
createdb sportclub_db
```

**Redis:**
```bash
redis-server
```

### 4. Создайте .env файл

Скопируйте `.env.example` в `backend/.env` и установите:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=sportclub_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Примените миграции

```bash
python manage.py migrate
```

### 6. Создайте суперпользователя

```bash
python manage.py createsuperuser
```

### 7. Создайте профиль для суперпользователя

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from apps.accounts.models import Profile, UserRole

user = User.objects.get(username='admin')
Profile.objects.create(
    user=user,
    phone='+79991234567',
    role=UserRole.ADMIN
)
exit()
```

### 8. Запустите сервер разработки

```bash
python manage.py runserver
```

### 9. В отдельном терминале запустите Celery

**Worker:**
```bash
celery -A config worker -l info
```

**Beat (в третьем терминале):**
```bash
celery -A config beat -l info
```

### 10. Откройте браузер

- http://localhost:8000
- http://localhost:8000/admin

---

## Создание тестовых данных

### Создание типов абонементов

Войдите в Django shell:

```bash
# Docker
docker-compose exec backend python manage.py shell

# Локально
python manage.py shell
```

Выполните:

```python
from apps.memberships.models import MembershipType
from decimal import Decimal

# Месячный абонемент
MembershipType.objects.create(
    name="Месячный абонемент",
    description="Безлимитное посещение в течение месяца",
    price=Decimal("5000.00"),
    duration_days=30,
    visits_limit=None
)

# Годовой абонемент
MembershipType.objects.create(
    name="Годовой абонемент",
    description="Безлимитное посещение в течение года",
    price=Decimal("50000.00"),
    duration_days=365,
    visits_limit=None
)

# Абонемент на 8 занятий
MembershipType.objects.create(
    name="8 занятий",
    description="8 занятий в течение месяца",
    price=Decimal("3000.00"),
    duration_days=30,
    visits_limit=8
)

print("Типы абонементов созданы!")
```

### Создание типов занятий

```python
from apps.classes.models import ClassType

class_types = [
    {"name": "Йога", "description": "Занятия йогой для начинающих и продвинутых", "duration_minutes": 60},
    {"name": "Фитнес", "description": "Силовые тренировки и кардио", "duration_minutes": 90},
    {"name": "Бокс", "description": "Бокс и кикбоксинг", "duration_minutes": 60},
    {"name": "Плавание", "description": "Плавание и аквааэробика", "duration_minutes": 45},
    {"name": "Пилатес", "description": "Пилатес для укрепления мышц", "duration_minutes": 60},
]

for ct in class_types:
    ClassType.objects.create(**ct)

print("Типы занятий созданы!")
```

### Создание залов

```python
from apps.facilities.models import Room

rooms = [
    {"name": "Главный зал", "description": "Большой зал для групповых занятий", "capacity": 25, "floor": 1},
    {"name": "Зал йоги", "description": "Уютный зал для занятий йогой", "capacity": 15, "floor": 2},
    {"name": "Боксерский ринг", "description": "Ринг для бокса и единоборств", "capacity": 10, "floor": 1},
    {"name": "Бассейн", "description": "25-метровый бассейн", "capacity": 8, "floor": -1},
]

for room in rooms:
    Room.objects.create(**room)

print("Залы созданы!")
exit()
```

---

## Полезные команды

### Django

```bash
# Создать миграции
python manage.py makemigrations

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Запустить сервер
python manage.py runserver

# Django shell
python manage.py shell
```

### Docker Compose

```bash
# Запустить контейнеры
docker-compose up -d

# Остановить контейнеры
docker-compose down

# Посмотреть логи
docker-compose logs -f backend

# Выполнить команду в контейнере
docker-compose exec backend python manage.py migrate
```

### Celery

```bash
# Запустить worker
celery -A config worker -l info

# Запустить beat
celery -A config beat -l info

# Очистить очередь задач
celery -A config purge
```

---

## Структура URL

### Веб-страницы (Django templates)

- `/` - Главная страница
- `/login/` - Вход
- `/register/` - Регистрация
- `/profile/` - Профиль пользователя
- `/admin/` - Админ-панель Django

### API endpoints

- `/api/auth/login/` - JWT авторизация
- `/api/auth/register/` - Регистрация через API
- `/api/auth/profile/` - Профиль пользователя
- `/api/memberships/` - Абонементы (Sprint 2)
- `/api/classes/` - Занятия и расписание (Sprint 3)
- `/api/bookings/` - Бронирования (Sprint 4)
- `/api/payments/` - Платежи (Sprint 5)
- `/api/analytics/` - Аналитика (Sprint 6)

---

## Следующие шаги

Теперь вы можете:

1. **Изучить админ-панель:** http://localhost:8000/admin
   - Создайте тренеров, залы, типы абонементов
   - Изучите все модели данных

2. **Начать Sprint 2:** Реализация управления абонементами
   - API endpoints для абонементов
   - Применение стратегии скидок
   - Страница каталога абонементов

3. **Читать документацию:**
   - [IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) - детальный план
   - [README.md](./README.md) - обзор проекта

---

## Troubleshooting

### Ошибка "relation does not exist"

Примените миграции:
```bash
docker-compose exec backend python manage.py migrate
```

### Ошибка "Cannot connect to PostgreSQL"

Убедитесь, что PostgreSQL запущен и параметры подключения в `.env` верны.

### Ошибка "Cannot connect to Redis"

Убедитесь, что Redis запущен:
```bash
redis-cli ping
# Должно вернуть: PONG
```

### Celery не запускается

Проверьте, что Redis доступен, и `CELERY_BROKER_URL` в `.env` указан правильно.

---

## Готово!

Теперь у вас есть полностью настроенная среда разработки для АС УСК.

**Хорошей разработки!** 🚀
