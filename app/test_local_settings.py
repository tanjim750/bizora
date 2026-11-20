"""Local HTTP sign-in must be able to return session and CSRF cookies."""

from django.conf import settings
from django.test import SimpleTestCase


class LocalCookieSettingsTests(SimpleTestCase):
    def test_local_debug_cookies_work_over_http(self):
        if settings.SETTINGS_MODULE != 'bizora.local_settings':
            self.skipTest('Only applies to the local HTTP development server.')
        self.assertFalse(settings.CSRF_COOKIE_SECURE)
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
