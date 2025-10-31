"""
URL configuration for memberships web pages (Django templates)
"""

from django.urls import path
from . import views_web

app_name = 'memberships_web'

urlpatterns = [
    # Catalog page
    path('catalog/', views_web.catalog_view, name='catalog'),

    # My memberships page
    path('my/', views_web.my_memberships_view, name='my_memberships'),

    # Purchase membership
    path('purchase/<int:membership_type_id>/', views_web.purchase_view, name='purchase'),
]
