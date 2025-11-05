"""
URL configuration for classes app API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClassTypeViewSet, ClassViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'types', ClassTypeViewSet, basename='classtype')
router.register(r'', ClassViewSet, basename='class')

urlpatterns = [
    path('', include(router.urls)),
]
