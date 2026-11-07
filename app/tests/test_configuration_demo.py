import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.models import ConfigurationRecord, ConfigurationRevision, MockExpectedResult
from app.tests.observability_helpers import NOW


class ConfigurationDemoTests(TestCase):
    def run_demo(self):
        output = StringIO()
        call_command('simulate_configuration', seed=77001, at=NOW.isoformat(), stdout=output)
        return json.loads(output.getvalue())

    def test_all_configuration_areas_are_validated_through_real_apis(self):
        first = self.run_demo()
        self.assertTrue(first['passed'])
        self.assertGreaterEqual(len(first['checks']), 16)
        count = ConfigurationRevision.objects.count()
        self.assertEqual(self.run_demo(), first)
        self.assertEqual(ConfigurationRevision.objects.count(), count)
        self.assertEqual(MockExpectedResult.objects.count(), len(first['checks']))

    def test_demo_revalidates_and_detects_current_configuration_corruption(self):
        self.run_demo()
        row = ConfigurationRecord.objects.get(kind='GENERAL')
        row.data['reporting_period'] = 'MONTH'
        row.save(update_fields=['data'])
        with self.assertRaises(CommandError):
            self.run_demo()

    def test_demo_rejects_unsafe_scope_and_bad_inputs(self):
        for changes in ({'business_slug': 'production'}, {'seed': -1}, {'at': '2026-10-25'}, {'at': '2026-99-01T12:00:00+00:00'}):
            with self.assertRaises(CommandError):
                call_command('simulate_configuration', **{'seed': 1, 'at': NOW.isoformat(), **changes}, stdout=StringIO())
