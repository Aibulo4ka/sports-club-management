"""
Production settings for АС УСК project.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Static files storage
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Allowed hosts must be specified in production
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Database connection pooling (optional, for better performance)
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes

# Logging to file in production
LOGGING['handlers']['file']['filename'] = '/var/log/sportclub/django.log'
LOGGING['root']['handlers'] = ['console', 'file']
