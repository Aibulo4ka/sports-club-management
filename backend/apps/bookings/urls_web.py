"""
Web URL configuration для bookings app (template-based views)
"""

from django.urls import path
from .views_web import my_bookings_view, create_booking_view, cancel_booking_view

app_name = 'bookings_web'

urlpatterns = [
    path('my/', my_bookings_view, name='my_bookings'),
    path('create/<int:class_id>/', create_booking_view, name='create'),
    path('cancel/<int:booking_id>/', cancel_booking_view, name='cancel'),
]
