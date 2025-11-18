"""
Views для аналитики и dashboard
"""

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta, date
import json

from apps.accounts.models import Client, Trainer
from apps.memberships.models import Membership, MembershipStatus
from apps.bookings.models import Booking, BookingStatus
from apps.payments.models import Payment, PaymentStatus
from apps.classes.models import Class


@staff_member_required
def dashboard(request):
    """
    Dashboard для администратора с основной статистикой
    """

    # Общая статистика
    total_clients = Client.objects.count()
    total_trainers = Trainer.objects.filter(is_active=True).count()
    active_memberships = Membership.objects.filter(status=MembershipStatus.ACTIVE).count()
    total_classes = Class.objects.count()

    # Статистика за последние 30 дней
    last_30_days = timezone.now() - timedelta(days=30)

    new_clients_30d = Client.objects.filter(
        profile__created_at__gte=last_30_days
    ).count()

    completed_bookings_30d = Booking.objects.filter(
        status=BookingStatus.COMPLETED,
        class_instance__datetime__gte=last_30_days
    ).count()

    # Выручка за последние 30 дней
    revenue_30d = Payment.objects.filter(
        status=PaymentStatus.COMPLETED,
        completed_at__gte=last_30_days
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Общая выручка
    total_revenue = Payment.objects.filter(
        status=PaymentStatus.COMPLETED
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Топ-5 популярных типов занятий (по типам, не по конкретным занятиям)
    from django.db.models import Q
    from apps.classes.models import ClassType

    popular_classes = ClassType.objects.annotate(
        bookings_count=Count('class__bookings')
    ).filter(bookings_count__gt=0).order_by('-bookings_count')[:5]

    # Преобразуем для шаблона
    popular_classes_data = [
        {'class_type__name': ct.name, 'bookings_count': ct.bookings_count}
        for ct in popular_classes
    ]

    # Статистика по статусам бронирований
    booking_stats = {
        'confirmed': Booking.objects.filter(status=BookingStatus.CONFIRMED).count(),
        'completed': Booking.objects.filter(status=BookingStatus.COMPLETED).count(),
        'cancelled': Booking.objects.filter(status=BookingStatus.CANCELLED).count(),
        'no_show': Booking.objects.filter(status=BookingStatus.NO_SHOW).count(),
    }

    # Процент посещаемости
    total_bookings = Booking.objects.count()
    completed_bookings = Booking.objects.filter(status=BookingStatus.COMPLETED).count()
    attendance_rate = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0

    # Загрузка тренеров (количество занятий)
    trainer_load = Trainer.objects.filter(
        is_active=True
    ).annotate(
        classes_count=Count('classes')
    ).order_by('-classes_count')[:5]

    # Последние платежи
    recent_payments = Payment.objects.select_related(
        'client__profile__user',
        'membership__membership_type'
    ).order_by('-created_at')[:10]

    # Предстоящие занятия
    upcoming_classes = Class.objects.filter(
        datetime__gte=timezone.now()
    ).select_related(
        'class_type',
        'trainer__profile__user',
        'room'
    ).annotate(
        current_capacity=Count('bookings', filter=Q(bookings__status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED]))
    ).order_by('datetime')[:5]

    # Данные для графика выручки по дням (последние 30 дней)
    revenue_by_day = Payment.objects.filter(
        status=PaymentStatus.COMPLETED,
        completed_at__gte=last_30_days
    ).annotate(
        day=TruncDate('completed_at')
    ).values('day').annotate(
        total=Sum('amount')
    ).order_by('day')

    # Заполняем все дни (даже если нет данных)
    revenue_chart_labels = []
    revenue_chart_data = []
    revenue_dict = {item['day']: float(item['total']) for item in revenue_by_day}

    for i in range(30):
        day = (timezone.now() - timedelta(days=29-i)).date()
        revenue_chart_labels.append(day.strftime('%d.%m'))
        revenue_chart_data.append(revenue_dict.get(day, 0))

    # Данные для графика новых клиентов по дням
    clients_by_day = Client.objects.filter(
        profile__created_at__gte=last_30_days
    ).annotate(
        day=TruncDate('profile__created_at')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')

    clients_chart_data = []
    clients_dict = {item['day']: item['count'] for item in clients_by_day}

    for i in range(30):
        day = (timezone.now() - timedelta(days=29-i)).date()
        clients_chart_data.append(clients_dict.get(day, 0))

    # Данные для графика бронирований по дням
    bookings_by_day = Booking.objects.filter(
        booking_date__gte=last_30_days
    ).annotate(
        day=TruncDate('booking_date')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')

    bookings_chart_data = []
    bookings_dict = {item['day']: item['count'] for item in bookings_by_day}

    for i in range(30):
        day = (timezone.now() - timedelta(days=29-i)).date()
        bookings_chart_data.append(bookings_dict.get(day, 0))

    context = {
        # Основные метрики
        'total_clients': total_clients,
        'total_trainers': total_trainers,
        'active_memberships': active_memberships,
        'total_classes': total_classes,

        # Метрики за 30 дней
        'new_clients_30d': new_clients_30d,
        'completed_bookings_30d': completed_bookings_30d,
        'revenue_30d': revenue_30d,

        # Финансы
        'total_revenue': total_revenue,

        # Статистика
        'popular_classes': popular_classes_data,
        'booking_stats': booking_stats,
        'attendance_rate': round(attendance_rate, 1),
        'trainer_load': trainer_load,

        # Последние данные
        'recent_payments': recent_payments,
        'upcoming_classes': upcoming_classes,

        # Данные для графиков (преобразуем в JSON для JavaScript)
        'revenue_chart_labels': json.dumps(revenue_chart_labels),
        'revenue_chart_data': json.dumps(revenue_chart_data),
        'clients_chart_data': json.dumps(clients_chart_data),
        'bookings_chart_data': json.dumps(bookings_chart_data),
    }

    return render(request, 'analytics/dashboard.html', context)
