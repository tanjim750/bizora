from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TransactionTestCase

from app.configuration.services import save_record
from app.models import ConfigurationEvent, ConfigurationRecord, ConfigurationRevision
from app.overview.configuration import ConfigurationConflict
from app.tests.observability_helpers import NOW, setup_businesses


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL transaction and row-lock suite.')
class ConfigurationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        setup_businesses(self)

    def race(self, callback):
        barrier = Barrier(3)
        def run(index):
            connections.close_all()
            try:
                actor = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait(timeout=15)
                return callback(index, actor)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=3) as executor:
            return list(executor.map(run, range(3)))

    def test_simultaneous_first_writes_keep_every_revision_and_event(self):
        self.race(lambda index, actor: save_record(self.business.pk, 'GENERAL', 'default',
            {'metadata': {f'change_{index}': True}}, actor, now=NOW))
        row = ConfigurationRecord.objects.get()
        self.assertEqual(row.version, 3)
        self.assertEqual(len(row.data['metadata']), 3)
        self.assertEqual(ConfigurationRevision.objects.count(), 3)
        self.assertEqual(ConfigurationEvent.objects.count(), 3)

    def test_expected_version_accepts_only_one_concurrent_write(self):
        def update(index, actor):
            try:
                save_record(self.business.pk, 'PROFILE', 'default', {'version': 0, 'name': f'Shop {index}'}, actor, now=NOW)
                return 'SAVED'
            except ConfigurationConflict:
                return 'CONFLICT'
        results = self.race(update)
        self.assertEqual(results.count('SAVED'), 1)
        self.assertEqual(results.count('CONFLICT'), 2)
        self.assertEqual(ConfigurationRevision.objects.count(), 1)

    def test_reprocessing_idempotency_is_serialized_across_simultaneous_requests(self):
        from app.configuration.knowledge import request_reprocessing, save_source
        from app.models import KnowledgeReprocessingRequest
        source = save_source(self.business.pk, self.user, {'name': 'Manual', 'status': 'ACTIVE',
            'source_type': 'MANUAL', 'knowledge_type': 'INTERNAL', 'source_reference': 'manual:1'}, NOW)
        body = {'idempotency_key': 'same-request', 'source_id': source.pk, 'action': 'REEMBED'}
        results = self.race(lambda _, actor: request_reprocessing(self.business.pk, actor, body, NOW)[0].pk)
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(KnowledgeReprocessingRequest.objects.count(), 1)

    def test_connection_updates_and_runtime_operations_can_progress_concurrently(self):
        from app.configuration.integrations import save_connection
        from app.observability.operations import execute_operation
        def run(index, actor):
            if index == 0:
                return save_connection(self.business.pk, actor, {'name': 'Configured store'}, NOW, self.connection.pk).pk
            return execute_operation(self.business.pk, 'connections', self.connection.pk,
                'connection_test', f'concurrent-runtime-{index}', actor, now=NOW).status
        results = self.race(run)
        self.assertEqual(results[1:], ['SUCCEEDED', 'SUCCEEDED'])
