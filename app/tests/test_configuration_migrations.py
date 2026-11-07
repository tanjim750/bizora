from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from app.tests.observability_helpers import NOW


class ConfigurationMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_existing_profile_monitoring_policy_and_connection_settings(self):
        old_target = [('app', '0003_overview_monitoring')]
        new_target = [('app', '0004_business_configuration')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old = executor.loader.project_state(old_target).apps
            business = old.get_model('app', 'Business').objects.create(name='Existing', slug='existing-config',
                currency='USD', timezone='Europe/London', created_at=NOW, updated_at=NOW)
            source = old.get_model('app', 'IntegrationSource').objects.create(key='migration-provider', name='Provider', category='COMMERCE', created_at=NOW, updated_at=NOW)
            connection_row = old.get_model('app', 'IntegrationConnection').objects.create(business=business, integration_source=source,
                config={'mock': {'connection_outcome': 'AUTH_ERROR'}}, created_at=NOW, updated_at=NOW)
            monitoring = old.get_model('app', 'MonitoringConfiguration').objects.create(business=business, settings={'period': 'WEEK'}, version=4)
            freshness = old.get_model('app', 'MonitoringPolicy').objects.create(business=business, delayed_seconds=60, stale_seconds=120)
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            current = executor.loader.project_state(new_target).apps
            self.assertEqual(current.get_model('app', 'Business').objects.get(pk=business.pk).currency, 'USD')
            self.assertEqual(current.get_model('app', 'MonitoringConfiguration').objects.get(pk=monitoring.pk).version, 4)
            self.assertEqual(current.get_model('app', 'MonitoringPolicy').objects.get(pk=freshness.pk).stale_seconds, 120)
            self.assertEqual(current.get_model('app', 'IntegrationConnection').objects.get(pk=connection_row.pk).config['mock']['connection_outcome'], 'AUTH_ERROR')
            self.assertEqual(current.get_model('app', 'ConfigurationRecord').objects.count(), 0)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
