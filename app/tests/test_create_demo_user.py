import os
from io import StringIO
from unittest import mock

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.management.commands.create_demo_user import require_isolated_local_database
from app.models import BusinessMembership


class CreateDemoUserTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command('create_demo_user', *args, stdout=out)
        return out.getvalue()

    def test_creates_a_superuser_that_can_log_in(self):
        output = self.run_command('--username', 'demo-owner', '--password', 'local-demo-pass-1')
        self.assertIn("Created local user 'demo-owner'", output)
        user = authenticate(username='demo-owner', password='local-demo-pass-1')
        self.assertIsNotNone(user)
        self.assertTrue(user.is_superuser and user.is_staff and user.is_active)
        self.assertIsNone(authenticate(username='demo-owner', password='wrong'))

    def test_running_again_updates_the_same_user(self):
        self.run_command('--username', 'demo-owner', '--password', 'first-pass-123')
        output = self.run_command('--username', 'demo-owner', '--password', 'second-pass-123')
        self.assertIn("Updated local user 'demo-owner'", output)
        self.assertEqual(get_user_model().objects.filter(username='demo-owner').count(), 1)
        self.assertIsNone(authenticate(username='demo-owner', password='first-pass-123'))
        self.assertIsNotNone(authenticate(username='demo-owner', password='second-pass-123'))

    def test_password_comes_from_the_environment_and_is_not_printed(self):
        with mock.patch.dict('os.environ', {'BIZORA_DEMO_PASSWORD': 'env-pass-456'}):
            output = self.run_command('--username', 'env-user')
        self.assertNotIn('env-pass-456', output)
        self.assertNotIn('Password (shown once)', output)
        self.assertIsNotNone(authenticate(username='env-user', password='env-pass-456'))

    def test_a_random_password_is_generated_and_printed_once(self):
        with mock.patch.dict('os.environ'):
            os.environ.pop('BIZORA_DEMO_PASSWORD', None)
            output = self.run_command('--username', 'random-user')
        line = next(l for l in output.splitlines() if l.startswith('Password (shown once): '))
        password = line.split(': ', 1)[1]
        self.assertGreaterEqual(len(password), 16)
        self.assertIsNotNone(authenticate(username='random-user', password=password))

    def test_with_demo_data_gives_the_user_a_business(self):
        output = self.run_command('--username', 'demo-owner', '--password', 'local-demo-pass-1', '--with-demo-data')
        self.assertIn('Demo business and data are loaded.', output)
        user = get_user_model().objects.get(username='demo-owner')
        self.assertTrue(BusinessMembership.objects.filter(user=user, role='OWNER').exists())

    def test_blank_username_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_command('--username', '   ', '--password', 'x-pass-12345')

    def test_database_guard(self):
        sqlite = 'django.db.backends.sqlite3'
        base = '/srv/project'
        require_isolated_local_database({'default': {'ENGINE': sqlite, 'NAME': '/home/dev/.bizora-dev-data/development.sqlite3'}}, base)
        with self.assertRaises(CommandError):
            require_isolated_local_database({'default': {'ENGINE': sqlite, 'NAME': '/srv/project/db.sqlite3'}}, base)
        with self.assertRaises(CommandError):
            require_isolated_local_database({'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'bizora'}}, base)
