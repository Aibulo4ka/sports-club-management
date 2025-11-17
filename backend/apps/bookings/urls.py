"""
URL-маршруты для приложения bookings
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, VisitViewSet

# API Router для DRF
router = DefaultRouter()
router.register(r'', BookingViewSet, basename='booking')
router.register(r'visits', VisitViewSet, basename='visit')

app_name = 'bookings'

urlpatterns = [
    # API endpoints (уже вложены в /api/bookings/ из главного urls.py)
    path('', include(router.urls)),
]

