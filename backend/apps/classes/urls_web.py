"""
Web URL configuration for classes app (template-based views)
"""

from django.urls import path
from .views_web import schedule_view, class_detail_view

app_name = 'classes_web'

urlpatterns = [
    path('schedule/', schedule_view, name='schedule'),
    path('<int:class_id>/', class_detail_view, name='detail'),
]
