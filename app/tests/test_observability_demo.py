import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.models import MockExpectedResult, ObservationReceipt, OperationAttempt, Product, SourceFreshness
from app.tests.observability_helpers import NOW


class DemoTests(TestCase):
    def run_demo(self):
        output = StringIO()
        call_command('simulate_observability', seed=75001, at=NOW.isoformat(), stdout=output)
        return json.loads(output.getvalue())

    def test_demo_is_deterministic_runs_real_pipeline_and_validates_every_scenario(self):
        first = self.run_demo()
        self.assertTrue(first['passed'])
        self.assertGreaterEqual(len(first['checks']), 8)
        self.assertTrue(Product.objects.exists())
        self.assertTrue(ObservationReceipt.objects.exists())
        self.assertTrue(OperationAttempt.objects.filter(status='SUCCEEDED').exists())
        self.assertEqual(MockExpectedResult.objects.count(), len(first['checks']))
        counts = [Product.objects.count(), ObservationReceipt.objects.count(), OperationAttempt.objects.count()]
        again = self.run_demo()
        self.assertEqual(first, again)
        self.assertEqual(counts, [Product.objects.count(), ObservationReceipt.objects.count(), OperationAttempt.objects.count()])

    def test_demo_validates_current_state_and_exits_with_failure_after_corruption(self):
        self.run_demo()
        SourceFreshness.objects.filter(connection__name='Healthy').update(coverage_at=None)
        with self.assertRaises(CommandError):
            self.run_demo()

    def test_demo_rejects_naive_time_and_unsafe_business_scope(self):
        with self.assertRaises(CommandError):
            call_command('simulate_observability', seed=1, at='2026-10-25T12:00:00', stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command('simulate_observability', seed=1, at=NOW.isoformat(), business_slug='existing-production-shop', stdout=StringIO())
