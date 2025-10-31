"""
URL Configuration for АС УСК project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/auth/', include('apps.accounts.urls')),
    path('api/memberships/', include('apps.memberships.urls')),
    path('api/classes/', include('apps.classes.urls')),
    path('api/bookings/', include('apps.bookings.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/facilities/', include('apps.facilities.urls')),
    path('api/analytics/', include('apps.analytics.urls')),

    # Web pages (Django templates)
    path('', include('apps.accounts.urls_web')),  # Home, login, register
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Django Debug Toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Customize admin site
admin.site.site_header = "АС УСК Администрирование"
admin.site.site_title = "АС УСК Admin"
admin.site.index_title = "Добро пожаловать в панель управления"
