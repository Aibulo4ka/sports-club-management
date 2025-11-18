# Email Уведомления АС УСК

## Обзор

Система автоматических email уведомлений для клиентов спортивного клуба.

## Реализованные уведомления

### 1. Приветственное письмо (Welcome Email)

**Когда отправляется:** Сразу после успешной регистрации нового пользователя

**Содержание:**
- Приветствие пользователя
- Краткий обзор возможностей системы
- Инструкции по началу работы
- Упоминание AI Персонального Тренера

**Реализация:**
- Файл: `apps/accounts/tasks.py`
- Функция: `send_welcome_email(user_id)`
- Вызов: `apps/accounts/views_web.py:105` (после регистрации)

### 2. Напоминание об истечении абонемента

**Когда отправляется:** За 3 дня до окончания срока действия абонемента

**Содержание:**
- Информация об абонементе (тип, дата окончания)
- Оставшиеся посещения (если применимо)
- Инструкции по продлению
- Ссылка на личный кабинет

**Реализация:**
- Файл: `apps/memberships/tasks.py`
- Функция: `send_membership_expiry_reminders()`
- Расписание: Каждый день в 09:00

### 3. Автоматическая деактивация истекших абонементов

**Когда выполняется:** Каждый день в 01:00

**Действие:** Меняет статус всех истекших абонементов с `ACTIVE` на `EXPIRED`

**Реализация:**
- Файл: `apps/memberships/tasks.py`
- Функция: `deactivate_expired_memberships()`
- Расписание: Каждый день в 01:00

## Конфигурация

### Celery расписание

Настройки периодических задач в `config/celery.py`:

```python
app.conf.beat_schedule = {
    # Напоминания об истечении абонемента
    'send-membership-expiry-reminders': {
        'task': 'apps.memberships.tasks.send_membership_expiry_reminders',
        'schedule': crontab(hour=9, minute=0),  # 9 AM каждый день
    },
    # Деактивация истекших абонементов
    'deactivate-expired-memberships': {
        'task': 'apps.memberships.tasks.deactivate_expired_memberships',
        'schedule': crontab(hour=1, minute=0),  # 1 AM каждый день
    },
}
```

### Email настройки

**Development (config/settings/dev.py):**
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'АС УСК <Aibiy.2005@gmail.com>'
```
В режиме разработки письма выводятся в консоль.

**Production (config/settings/prod.py):**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'АС УСК <noreply@sportclub.com>'
```

## Запуск

### 1. Запустить Celery Worker

```bash
celery -A config worker --loglevel=info
```

### 2. Запустить Celery Beat (планировщик)

```bash
celery -A config beat --loglevel=info
```

### 3. Или оба процесса одновременно

```bash
celery -A config worker --beat --loglevel=info
```

## Тестирование

Запустите тестовый скрипт:

```bash
python test_email_notifications.py
```

Скрипт проверит:
- ✓ Отправку welcome email
- ✓ Поиск абонементов, истекающих через 3 дня
- ✓ Поиск истекших абонементов для деактивации
- ✓ Текущие настройки email

## Логирование

Все ошибки при отправке email логируются, но не прерывают обработку остальных сообщений:

```python
try:
    send_mail(...)
    sent_count += 1
except Exception as e:
    print(f"Ошибка при отправке: {e}")
    # Продолжаем обработку остальных
```

## Production Checklist

- [ ] Настроить SMTP в `config/settings/prod.py`
- [ ] Установить переменные окружения `EMAIL_HOST_USER` и `EMAIL_HOST_PASSWORD`
- [ ] Запустить Celery Worker в фоне (supervisor/systemd)
- [ ] Запустить Celery Beat в фоне (supervisor/systemd)
- [ ] Проверить отправку тестового письма
- [ ] Настроить мониторинг очереди Celery
- [ ] Настроить логирование ошибок (Sentry)

## Расширение функционала

### Добавление нового типа уведомлений

1. Создайте задачу в соответствующем `tasks.py`:

```python
@shared_task
def send_custom_notification(user_id):
    user = User.objects.get(id=user_id)
    send_mail(
        subject='Тема письма',
        message='Содержание...',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
```

2. Добавьте в расписание (если периодическое):

```python
app.conf.beat_schedule = {
    'custom-notification': {
        'task': 'apps.yourapp.tasks.send_custom_notification',
        'schedule': crontab(...),
    },
}
```

3. Вызовите асинхронно:

```python
from .tasks import send_custom_notification
send_custom_notification.delay(user_id)
```

## Шаблоны писем

Для более сложных HTML-писем можно использовать Django templates:

```python
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

html_content = render_to_string('emails/welcome.html', {'user': user})
text_content = render_to_string('emails/welcome.txt', {'user': user})

email = EmailMultiAlternatives(
    subject='Добро пожаловать!',
    body=text_content,
    from_email=settings.DEFAULT_FROM_EMAIL,
    to=[user.email]
)
email.attach_alternative(html_content, "text/html")
email.send()
```

## Мониторинг

Проверка состояния очереди Celery:

```bash
# Просмотр активных задач
celery -A config inspect active

# Просмотр расписания
celery -A config inspect scheduled

# Статистика
celery -A config inspect stats
```
