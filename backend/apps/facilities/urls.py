"""
URL configuration for facilities app API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'rooms', RoomViewSet, basename='room')

urlpatterns = [
    path('', include(router.urls)),
]
