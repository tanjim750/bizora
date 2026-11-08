"""Isolated local/test configuration; never opens the checked-in database."""
import os
import secrets
from pathlib import Path

os.environ.setdefault('SECRET_KEY', os.environ.get('DJANGO_SECRET_KEY') or secrets.token_urlsafe(48))
os.environ.setdefault('DEBUG', '1' if os.environ.get('DJANGO_DEBUG', '1') == '1' else '0')

from .settings import *  # noqa: F403

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or __import__('secrets').token_urlsafe(48)
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
_data_dir = Path(os.environ.get('BIZORA_DATA_DIR', '/tmp/bizora-local'))
_data_dir.mkdir(parents=True, exist_ok=True)
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': _data_dir / 'development.sqlite3',
    'TEST': {'NAME': ':memory:'},
}}
if DATABASES['default']['NAME'].resolve() == (BASE_DIR / 'db.sqlite3').resolve():
    raise RuntimeError('The tracked database must not be used by local settings.')
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticated',
], 'DEFAULT_AUTHENTICATION_CLASSES': [
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework.authentication.BasicAuthentication',
], 'TEST_REQUEST_DEFAULT_FORMAT': 'json'}
