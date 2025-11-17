"""
URL-маршруты для приложения payments (API)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet

# API Router для DRF
router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')

app_name = 'payments'

urlpatterns = [
    # Explicit webhook endpoint (for easier access)
    path('webhook/', PaymentViewSet.as_view({'post': 'webhook'}), name='yookassa-webhook'),

    # API endpoints (уже вложены в /api/payments/ из главного urls.py)
    path('', include(router.urls)),
]

