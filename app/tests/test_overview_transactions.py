from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TransactionTestCase

from app.models import MonitoringConfiguration, MonitoringConfigurationRevision
from app.overview.metrics import compare
from app.overview.configuration import ConfigurationConflict, save_configuration
from app.tests.observability_helpers import NOW, setup_businesses


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL locking test; SQLite does not implement select_for_update.')
class OverviewConcurrencyTests(TransactionTestCase):
    def setUp(self):
        setup_businesses(self)

    def race(self, callback):
        barrier = Barrier(3)
        def run(index):
            connections.close_all()
            try:
                actor = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait(timeout=15)
                return callback(actor, index)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=3) as executor:
            return list(executor.map(run, range(3)))

    def test_simultaneous_first_writes_preserve_every_revision(self):
        self.race(lambda actor, _: save_configuration(self.business.pk, actor, {'period': 'WEEK'}, NOW))
        self.assertEqual(MonitoringConfiguration.objects.get().version, 3)
        self.assertEqual(list(MonitoringConfigurationRevision.objects.order_by('version').values_list('version', flat=True)), [1, 2, 3])

    def test_optimistic_version_allows_only_one_matching_write(self):
        def update(actor, _):
            try:
                save_configuration(self.business.pk, actor, {'version': 0, 'period': 'MONTH'}, NOW)
                return 'SAVED'
            except ConfigurationConflict:
                return 'CONFLICT'
        results = self.race(update)
        self.assertEqual(results.count('SAVED'), 1)
        self.assertEqual(results.count('CONFLICT'), 2)

    def test_full_precision_decimal_snapshot_and_extreme_comparison(self):
        from decimal import Decimal
        from app.tests.overview_helpers import metric, snapshot
        definition = metric(self.business)
        point = snapshot(self.business, definition, '999999999999999999.999999')
        point.refresh_from_db()
        self.assertEqual(point.value, Decimal('999999999999999999.999999'))
        comparison = compare(point.value, Decimal('.000001'))
        self.assertIsNotNone(comparison['percent_change'])
