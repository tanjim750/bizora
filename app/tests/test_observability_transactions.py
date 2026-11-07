from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase

from app.integrations.payloads import capture_payload
from app.models import ConnectionCheck, FailedRecord, IntegrationError, OperationAttempt, Product
from app.observability.operations import execute_operation
from app.observability.services import record_observation
from app.tests.observability_helpers import NOW, observe, setup_businesses


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL transactional suite; run with BIZORA_DATABASE=postgresql.')
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        setup_businesses(self)

    def concurrent(self, callback, workers=4):
        barrier = Barrier(workers)
        def run(index):
            connections.close_all()
            try:
                barrier.wait(timeout=15)
                return callback(index)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(run, range(workers)))

    def test_simultaneous_duplicate_observation_is_persisted_once(self):
        results = self.concurrent(lambda _: record_observation(self.business.pk, self.connection.pk,
            'same-event', 'connection_check', {'outcome': 'SUCCESS'}, NOW, NOW).pk)
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(ConnectionCheck.objects.count(), 1)

    def test_simultaneous_error_occurrences_do_not_lose_increments(self):
        self.concurrent(lambda index: [record_observation(self.business.pk, self.connection.pk,
            f'failure-{index}-{i}', 'integration_error', {'code': 'PROVIDER_TIMEOUT', 'category': 'CONNECTIVITY'}, NOW, NOW)
            for i in range(3)])
        self.assertEqual(IntegrationError.objects.get().occurrences, 12)

    def failed(self):
        payload = capture_payload(self.connection.pk, 'product', {'id': 'p-1', 'name': 'Coffee'}, received_at=NOW)
        receipt = observe(self, 'failed_record', {'entity_type': 'PRODUCT', 'external_id': 'p-1',
            'stage': 'MAPPING', 'code': 'MAPPING_ERROR', 'payload_id': payload.pk})
        return receipt.object_id

    def test_simultaneous_same_operation_processes_canonical_record_once(self):
        row_id = self.failed()
        def operate(_):
            actor = get_user_model().objects.get(pk=self.user.pk)
            return execute_operation(self.business.pk, 'failed-records', row_id, 'record_retry', 'same-operation', actor).pk
        results = self.concurrent(operate)
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(OperationAttempt.objects.count(), 1)
        self.assertEqual(Product.objects.count(), 1)

    def test_simultaneous_different_requests_cannot_retry_resolved_record_twice(self):
        row_id = self.failed()
        def operate(index):
            actor = get_user_model().objects.get(pk=self.user.pk)
            try:
                return execute_operation(self.business.pk, 'failed-records', row_id,
                                         'record_retry', f'operation-{index}', actor).status
            except ValidationError:
                return 'DENIED'
        results = self.concurrent(operate)
        self.assertEqual(results.count('SUCCEEDED'), 1)
        self.assertEqual(results.count('DENIED'), 3)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(FailedRecord.objects.get(pk=row_id).status, 'RESOLVED')
