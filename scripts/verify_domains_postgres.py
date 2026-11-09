#!/usr/bin/env python3
"""Create, verify and remove only our own disposable PostgreSQL container.

Run with the project's virtualenv Python. Docker must be available. No named
volumes, existing containers, production environment variables or databases are used.
"""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

IMAGE = 'pgvector/pgvector:0.8.7-pg16'
ROOT = Path(__file__).resolve().parent.parent


def command(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def main():
    suffix = secrets.token_hex(6)
    name = 'bizora-verify-' + suffix
    db = 'bizora_verify_' + suffix
    password = secrets.token_urlsafe(32)
    env = {**os.environ, 'POSTGRES_PASSWORD': password}
    started = False
    try:
        command(['docker', 'run', '--detach', '--name', name, '--label', 'bizora.purpose=domain-verification',
                 '--tmpfs', '/var/lib/postgresql/data', '--publish', '127.0.0.1::5432',
                 '--env', 'POSTGRES_PASSWORD', '--env', 'POSTGRES_USER=bizora_verify',
                 '--env', 'POSTGRES_DB=' + db, IMAGE], env=env, stdout=subprocess.DEVNULL)
        started = True
        for _ in range(60):
            # The entrypoint briefly starts a socket-only initialization server.
            # Wait for TCP, which is enabled only by the final PostgreSQL server.
            result = subprocess.run(['docker', 'exec', name, 'pg_isready', '-h', '127.0.0.1', '-U', 'bizora_verify', '-d', db],
                                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('Disposable PostgreSQL did not become ready.')
        # Baseline 0001 contains vector columns. Bootstrap before migration; template1
        # also supplies the extension to Django-created isolated test databases.
        for database in (db, 'template1'):
            command(['docker', 'exec', name, 'psql', '-U', 'bizora_verify', '-d', database,
                     '-v', 'ON_ERROR_STOP=1', '-c', 'CREATE EXTENSION IF NOT EXISTS vector;'])
        port = command(['docker', 'port', name, '5432/tcp'], capture_output=True).stdout.strip().rsplit(':', 1)[1]
        verify_env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'bizora.postgres_test_settings',
            'BIZORA_PG_HOST': '127.0.0.1', 'BIZORA_PG_PORT': port, 'BIZORA_PG_DATABASE': db,
            'BIZORA_PG_USER': 'bizora_verify', 'BIZORA_PG_PASSWORD': password}
        for args in (['check'], ['migrate', '--noinput'], ['makemigrations', '--check', '--dry-run'],
                     ['preflight_domains'], ['test', '--noinput']):
            command([sys.executable, str(ROOT / 'manage.py'), *args], env=verify_env, cwd=ROOT)
    finally:
        if started:
            command(['docker', 'rm', '--force', '--volumes', name], stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
