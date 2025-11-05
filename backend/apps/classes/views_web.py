"""
Web views for Classes app (Django template-based views)
"""

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Class, ClassType, ClassStatus


def schedule_view(request):
    """
    Display schedule page with list of upcoming classes
    """
    # Get filter parameters
    class_type_id = request.GET.get('type')
    date_filter = request.GET.get('date', 'upcoming')

    # Base queryset
    classes = Class.objects.filter(
        status=ClassStatus.SCHEDULED
    ).select_related(
        'class_type', 'trainer__profile__user', 'room'
    ).order_by('datetime')

    # Apply filters
    now = timezone.now()

    if date_filter == 'today':
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        classes = classes.filter(datetime__gte=today_start, datetime__lt=today_end)
        page_title = 'Расписание на сегодня'
    elif date_filter == 'tomorrow':
        tomorrow_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        classes = classes.filter(datetime__gte=tomorrow_start, datetime__lt=tomorrow_end)
        page_title = 'Расписание на завтра'
    elif date_filter == 'week':
        week_end = now + timedelta(days=7)
        classes = classes.filter(datetime__gte=now, datetime__lte=week_end)
        page_title = 'Расписание на неделю'
    else:  # upcoming
        classes = classes.filter(datetime__gte=now)
        page_title = 'Предстоящие занятия'

    # Filter by class type
    if class_type_id:
        classes = classes.filter(class_type_id=class_type_id)

    # Get all class types for filter
    class_types = ClassType.objects.filter(is_active=True)

    # Group classes by date
    classes_by_date = {}
    for class_obj in classes[:50]:  # Limit to 50 for performance
        date_key = class_obj.datetime.date()
        if date_key not in classes_by_date:
            classes_by_date[date_key] = []
        classes_by_date[date_key].append(class_obj)

    context = {
        'classes_by_date': classes_by_date,
        'class_types': class_types,
        'selected_type': class_type_id,
        'selected_filter': date_filter,
        'page_title': page_title,
    }

    return render(request, 'classes/schedule.html', context)


def class_detail_view(request, class_id):
    """
    Display detailed information about a specific class
    """
    class_obj = get_object_or_404(
        Class.objects.select_related(
            'class_type', 'trainer__profile__user', 'room'
        ),
        id=class_id
    )

    # Check if user is authenticated and already booked
    is_booked = False
    if request.user.is_authenticated:
        # TODO: Check if user has a booking for this class
        # from apps.bookings.models import Booking
        # is_booked = Booking.objects.filter(
        #     user=request.user,
        #     class_instance=class_obj
        # ).exists()
        pass

    context = {
        'class': class_obj,
        'is_booked': is_booked,
    }

    return render(request, 'classes/class_detail.html', context)
