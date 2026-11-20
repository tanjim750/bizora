"""Settings for Gunicorn behind the deployment's Nginx reverse proxy."""

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403
from .settings import BASE_DIR, DATABASES, DEBUG, MIDDLEWARE

if DEBUG or DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Production requires DEBUG=False and PostgreSQL.')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MIDDLEWARE = [MIDDLEWARE[0], 'whitenoise.middleware.WhiteNoiseMiddleware', *MIDDLEWARE[1:]]
