"""Opt-in local PostgreSQL verification only; credentials use a separate namespace."""
import os
from .local_settings import *  # noqa: F403

_pg_name = os.environ['BIZORA_PG_DATABASE']
_pg_host = os.environ.get('BIZORA_PG_HOST', '127.0.0.1')
if _pg_host not in ('127.0.0.1', 'localhost') or not _pg_name.startswith('bizora_verify_'):
    raise RuntimeError('PostgreSQL verification requires a local bizora_verify_ database.')
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql', 'HOST': _pg_host,
    'PORT': os.environ['BIZORA_PG_PORT'], 'NAME': _pg_name,
    'USER': os.environ['BIZORA_PG_USER'], 'PASSWORD': os.environ['BIZORA_PG_PASSWORD'],
}}
