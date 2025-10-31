"""
Celery configuration for АС УСК project.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('sportclub')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Periodic tasks (Celery Beat schedule)
app.conf.beat_schedule = {
    # Send booking reminders 2 hours before class
    'send-booking-reminders': {
        'task': 'apps.bookings.tasks.send_booking_reminders',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    # Cancel unconfirmed bookings 30 minutes before class
    'cancel-unconfirmed-bookings': {
        'task': 'apps.bookings.tasks.cancel_unconfirmed_bookings',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    # Clean up expired memberships daily
    'cleanup-expired-memberships': {
        'task': 'apps.memberships.tasks.cleanup_expired_memberships',
        'schedule': crontab(hour=2, minute=0),  # 2 AM every day
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
