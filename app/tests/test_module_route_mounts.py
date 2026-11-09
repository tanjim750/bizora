from django.test import SimpleTestCase
from django.urls import resolve


class ModuleRouteMountTests(SimpleTestCase):
    def test_business_modules_are_mounted(self):
        for path, name in (
            ('overview/summary/', 'overview-summary'),
            ('configuration/profile/', None),
            ('observability/summary/', 'observability-summary'),
        ):
            with self.subTest(path=path):
                match = resolve(f'/api/businesses/1/{path}')
                self.assertEqual(match.url_name, name)
                self.assertEqual(match.kwargs['business_id'], 1)
