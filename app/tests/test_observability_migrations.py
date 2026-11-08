import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase

from app.tests.observability_helpers import NOW


class DatabaseConfigurationTests(SimpleTestCase):
    def settings(self, **variables):
        env = {**os.environ, **variables}
        result = subprocess.run([sys.executable, '-c',
            'import json; from bizora.settings import DATABASES; print(json.dumps(DATABASES, default=str))'],
            env=env, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)['default']

    def test_disposable_sqlite_path_is_configurable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'disposable.sqlite3')
            self.assertEqual(self.settings(BIZORA_DATABASE='sqlite', BIZORA_DB_PATH=path)['NAME'], path)

    def test_postgresql_environment_is_used_explicitly(self):
        config = self.settings(BIZORA_DATABASE='postgresql', POSTGRES_DB='observability_test',
                               POSTGRES_USER='test', POSTGRES_PASSWORD='test-only', POSTGRES_HOST='127.0.0.1',
                               POSTGRES_PORT='55439', POSTGRES_TEST_TEMPLATE='template1', DATABASE_URL='')
        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'observability_test')
        self.assertEqual(config['PORT'], '55439')

    def test_database_url_configures_postgresql_with_encoded_credentials_and_ssl(self):
        config = self.settings(BIZORA_DATABASE='postgresql',
                               DATABASE_URL='postgresql://postgres.project:p%40ss%23word@pooler.example.com:5432/postgres?sslmode=require',
                               POSTGRES_HOST='127.0.0.1')
        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'postgres')
        self.assertEqual(config['USER'], 'postgres.project')
        self.assertEqual(config['PASSWORD'], 'p@ss#word')
        self.assertEqual(config['HOST'], 'pooler.example.com')
        self.assertEqual(config['PORT'], '5432')
        self.assertEqual(config['OPTIONS']['sslmode'], 'require')

    def test_database_url_selects_postgresql_without_backend_override(self):
        config = self.settings(BIZORA_DATABASE='', DATABASE_URL='postgres://test:secret@localhost:5432/bizora')
        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'bizora')

    def test_postgresql_parameters_apply_sslmode(self):
        config = self.settings(BIZORA_DATABASE='postgresql', DATABASE_URL='', POSTGRES_SSLMODE='require')
        self.assertEqual(config['OPTIONS']['sslmode'], 'require')

    def test_explicit_sqlite_ignores_database_url(self):
        config = self.settings(BIZORA_DATABASE='sqlite', DATABASE_URL='postgresql://test:secret@localhost/test')
        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')


class ObservabilityMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_existing_integration_and_legacy_counter_meaning(self):
        old_target = [('app', '0001_initial')]
        new_target = [('app', '0002_integration_data_observability')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old = executor.loader.project_state(old_target).apps
            business = old.get_model('app', 'Business').objects.create(name='Legacy', slug='legacy', created_at=NOW, updated_at=NOW)
            source = old.get_model('app', 'IntegrationSource').objects.create(key='legacy', name='Legacy',
                category='COMMERCE', created_at=NOW, updated_at=NOW)
            conn = old.get_model('app', 'IntegrationConnection').objects.create(business=business,
                integration_source=source, created_at=NOW, updated_at=NOW)
            sync = old.get_model('app', 'IntegrationSyncLog').objects.create(integration_connection=conn,
                status='FAILED', records_received=10, records_processed=8, records_failed=2, started_at=NOW, created_at=NOW)
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            current = executor.loader.project_state(new_target).apps
            upgraded = current.get_model('app', 'IntegrationSyncLog').objects.get(pk=sync.pk)
            self.assertEqual(upgraded.records_processed, 8)
            self.assertEqual(upgraded.records_failed, 2)
            self.assertEqual(upgraded.counter_schema, 'LEGACY')
            self.assertEqual(upgraded.last_observed_at, NOW)
            self.assertEqual(current.get_model('app', 'IntegrationConnection').objects.get(pk=conn.pk).business_id, business.pk)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
