"""Create or update a local demo user (and optionally the demo data) in an isolated local database."""
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


def require_isolated_local_database(databases, base_dir):
    """Refuse to touch anything but an isolated local SQLite file that is not the tracked db.sqlite3."""
    db = databases['default']
    if db['ENGINE'] != 'django.db.backends.sqlite3':
        raise CommandError('create_demo_user only works with an isolated local SQLite database.')
    if Path(str(db['NAME'])).resolve() == (Path(base_dir) / 'db.sqlite3').resolve():
        raise CommandError('create_demo_user must not use the tracked db.sqlite3.')


class Command(BaseCommand):
    help = (
        'Create or update a local demo user with a password and, with --with-demo-data, load the demo business for it. '
        'Idempotent. Only for an isolated local SQLite database (bizora.local_settings).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo-owner')
        parser.add_argument(
            '--password',
            default=None,
            help='Password to set. Default: the environment variable BIZORA_DEMO_PASSWORD, else a random one that is printed once.',
        )
        parser.add_argument('--with-demo-data', action='store_true', help='Also run demo_completion for this user.')

    def handle(self, *args, **options):
        require_isolated_local_database(settings.DATABASES, settings.BASE_DIR)
        username = (options['username'] or '').strip()
        if not username:
            raise CommandError('A username is required.')
        password = options['password'] or os.environ.get('BIZORA_DEMO_PASSWORD')
        generated = not password
        if generated:
            password = secrets.token_urlsafe(18)
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(f"{'Created' if created else 'Updated'} local user '{username}'.")
        if generated:
            self.stdout.write(f'Password (shown once): {password}')
        if options['with_demo_data']:
            call_command('demo_completion', username=username, stdout=self.stdout)
            self.stdout.write('Demo business and data are loaded.')
