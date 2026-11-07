import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.models import Business, MetricSnapshot, MockExpectedResult, MonitoringConfiguration
from app.tests.observability_helpers import NOW


class OverviewDemoTests(TestCase):
    def run_demo(self):
        output = StringIO()
        call_command('simulate_overview', seed=76001, at=NOW.isoformat(), stdout=output)
        return json.loads(output.getvalue())

    def test_demo_runs_apis_and_revalidates_deterministically(self):
        first = self.run_demo()
        self.assertTrue(first['passed'])
        self.assertGreaterEqual(len(first['checks']), 12)
        counts = [Business.objects.count(), MetricSnapshot.objects.count(), MonitoringConfiguration.objects.count()]
        self.assertEqual(self.run_demo(), first)
        self.assertEqual(counts, [Business.objects.count(), MetricSnapshot.objects.count(), MonitoringConfiguration.objects.count()])
        self.assertEqual(MockExpectedResult.objects.count(), len(first['checks']))

    def test_demo_detects_tampering_in_upstream_snapshot(self):
        self.run_demo()
        MetricSnapshot.objects.filter(metric__key='order_count').update(value=0)
        with self.assertRaises(CommandError):
            self.run_demo()

    def test_demo_rejects_unsafe_scope_naive_time_and_negative_seed(self):
        for arguments in ({'business_slug': 'shop'}, {'at': '2026-10-25T12:00:00'},
                          {'at': '2026-99-25T12:00:00+00:00'}, {'seed': -1}):
            with self.assertRaises(CommandError):
                call_command('simulate_overview', **{'seed': 1, 'at': NOW.isoformat(), **arguments}, stdout=StringIO())

    def test_demo_handles_offset_times_and_midnight(self):
        for at in ['2026-10-25T06:00:00+06:00', '2026-10-25T00:00:00+00:00']:
            output = StringIO()
            call_command('simulate_overview', seed=76002, at=at, stdout=output)
            self.assertTrue(json.loads(output.getvalue())['passed'])
