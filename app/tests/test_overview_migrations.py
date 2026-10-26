from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from app.tests.observability_helpers import NOW


class OverviewMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_bi_snapshots_and_does_not_create_default_policies(self):
        old_target = [('app', '0002_integration_data_observability')]
        new_target = [('app', '0003_overview_monitoring')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old = executor.loader.project_state(old_target).apps
            business = old.get_model('app', 'Business').objects.create(name='Legacy BI', slug='legacy-bi', created_at=NOW, updated_at=NOW)
            metric = old.get_model('app', 'BusinessMetric').objects.create(business=business, key='total_revenue',
                name='Total revenue', category='SALES', created_at=NOW, updated_at=NOW)
            point = old.get_model('app', 'MetricSnapshot').objects.create(business=business, metric=metric,
                value='123.45', period_start=NOW, period_end=NOW, calculated_at=NOW, created_at=NOW)
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            current = executor.loader.project_state(new_target).apps
            self.assertEqual(str(current.get_model('app', 'MetricSnapshot').objects.get(pk=point.pk).value), '123.450000')
            self.assertEqual(current.get_model('app', 'MonitoringConfiguration').objects.count(), 0)
            self.assertEqual(current.get_model('app', 'MonitoringConfigurationRevision').objects.count(), 0)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
