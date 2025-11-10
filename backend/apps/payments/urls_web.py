"""
URL configuration для веб-страниц payments (Django templates)
"""

from django.urls import path
from . import views_web

app_name = 'payments_web'

urlpatterns = [
    # История платежей
    path('my/', views_web.my_payments_view, name='my_payments'),

    # Страница успешной оплаты
    path('success/<int:payment_id>/', views_web.payment_success_view, name='payment_success'),

    # Страница неудачной оплаты
    path('failed/<int:payment_id>/', views_web.payment_failed_view, name='payment_failed'),
]
