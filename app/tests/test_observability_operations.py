from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from app.integrations.payloads import capture_payload
from app.models import (FailedRecord, IntegrationError, IntegrationPayload, IntegrationSyncLog,
                        MonitoringPolicy, OperationAttempt, Product, ProductExternalReference,
                        SourceFreshness, WebhookObservation)
from app.tests.observability_helpers import NOW, observe, setup_businesses


class OperationTests(APITestCase):
    def setUp(self):
        setup_businesses(self)
        self.root = f'/api/businesses/{self.business.pk}/observability/'
        self.client.force_authenticate(self.user)
        self.clock = patch('django.utils.timezone.now', return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def payload(self, key='payload', body=None, verified=True, source_at=None):
        source_at = source_at or NOW - timedelta(hours=2)
        return capture_payload(self.connection.pk, key, body or {'id': 'p-1', 'name': 'Coffee', 'sku': 'C'},
                               signature_verified=verified, received_at=max(NOW - timedelta(hours=1), source_at),
                               source_at=source_at)

    def failed(self, payload=None, **overrides):
        payload = payload or self.payload()
        data = dict(entity_type='PRODUCT', external_id='p-1', stage='MAPPING', code='MAPPING_ERROR',
                    payload_id=payload.pk)
        data.update(overrides)
        receipt = observe(self, 'failed_record', data)
        return FailedRecord.objects.get(pk=receipt.object_id)

    def post(self, path, key='operation'):
        return self.client.post(self.root + path + '/', {'idempotency_key': key}, format='json')

    def test_mock_connectivity_check_runs_and_is_idempotent(self):
        first = self.post(f'connections/{self.connection.pk}/test')
        again = self.post(f'connections/{self.connection.pk}/test')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['status'], 'SUCCEEDED')
        self.assertEqual(first.data['id'], again.data['id'])
        self.assertTrue(first.data['result']['is_mock'])
        self.assertEqual(OperationAttempt.objects.count(), 1)

    def test_failed_record_retry_really_persists_product_preserves_history_and_old_freshness(self):
        row = self.failed()
        response = self.post(f'failed-records/{row.pk}/retry')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'SUCCEEDED')
        self.assertEqual(Product.objects.get().name, 'Coffee')
        self.assertEqual(ProductExternalReference.objects.get().external_product_id, 'p-1')
        row.refresh_from_db()
        self.assertEqual(row.status, 'RESOLVED')
        self.assertEqual(row.resolution_method, 'PROCESSING')
        self.assertEqual(SourceFreshness.objects.get().coverage_at, NOW - timedelta(hours=2))
        self.assertTrue(self.client.get(self.root + f'failed-records/{row.pk}/').data['history'])
        again = self.post(f'failed-records/{row.pk}/retry')
        self.assertEqual(again.data['id'], response.data['id'])
        self.assertEqual(Product.objects.count(), 1)

    def test_failed_retry_is_visible_then_mapping_fix_allows_safe_retry(self):
        payload = self.payload(body={'id': 'p-1', 'title': 'Coffee'})
        row = self.failed(payload)
        response = self.post(f'failed-records/{row.pk}/retry')
        self.assertEqual(response.data['status'], 'FAILED')
        self.assertFalse(Product.objects.exists())
        self.assertFalse(SourceFreshness.objects.exists())
        row.refresh_from_db()
        self.assertEqual(row.status, 'OPEN')
        self.assertIsNotNone(OperationAttempt.objects.get().next_retry_at)
        self.assertEqual(self.post(f'failed-records/{row.pk}/retry', 'too-soon').status_code, 400)
        self.connection.config = {'mock': {'product_name_field': 'title'}}
        self.connection.save()
        with patch('django.utils.timezone.now', return_value=NOW + timedelta(minutes=1)):
            response = self.post(f'failed-records/{row.pk}/retry', 'retry-after-fix')
        self.assertEqual(response.data['status'], 'SUCCEEDED')
        self.assertEqual(Product.objects.get().name, 'Coffee')
        self.assertEqual(IntegrationPayload.objects.get().body, {'id': 'p-1', 'title': 'Coffee'})

    def test_invalid_signature_replay_and_record_retry_are_rejected(self):
        payload = self.payload(verified=False)
        receipt = observe(self, 'webhook', {'event_id': 'bad-signature', 'event_type': 'product.updated',
                        'entity_type': 'PRODUCT', 'validation': 'INVALID', 'payload_id': payload.pk})
        self.assertEqual(self.post(f'webhooks/{receipt.object_id}/replay').status_code, 400)
        failed = FailedRecord.objects.get()
        self.assertEqual(self.post(f'failed-records/{failed.pk}/retry', 'record').status_code, 400)
        self.assertFalse(Product.objects.exists())
        self.assertFalse(SourceFreshness.objects.exists())

    def test_valid_failed_webhook_replay_routes_through_real_processor_once(self):
        payload = self.payload()
        receipt = observe(self, 'webhook', {'event_id': 'good-signature', 'event_type': 'product.updated',
            'entity_type': 'PRODUCT', 'validation': 'VALID', 'status': 'FAILED', 'payload_id': payload.pk})
        response = self.post(f'webhooks/{receipt.object_id}/replay')
        self.assertEqual(response.data['status'], 'SUCCEEDED')
        row = WebhookObservation.objects.get()
        self.assertEqual(row.status, 'PROCESSED')
        self.assertEqual(row.delivery_count, 1)
        self.assertEqual(row.processed_at, NOW)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(FailedRecord.objects.get().status, 'RESOLVED')
        self.assertEqual(self.post(f'webhooks/{row.pk}/replay').data['id'], response.data['id'])
        self.assertEqual(self.post(f'webhooks/{row.pk}/replay', 'another').status_code, 400)

    def test_live_capabilities_are_explicitly_unsupported_without_false_success(self):
        self.connection.is_mock = False
        self.connection.save()
        row = self.failed()
        for path in [f'connections/{self.connection.pk}/test', f'failed-records/{row.pk}/retry']:
            with self.subTest(path=path):
                response = self.post(path, path)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.data['status'], 'UNSUPPORTED')
        self.assertFalse(Product.objects.exists())
        self.assertFalse(SourceFreshness.objects.exists())

    def test_missing_payload_and_unsupported_entity_do_not_claim_recovery(self):
        receipt = observe(self, 'failed_record', {'entity_type': 'ORDER', 'external_id': 'o-1',
            'stage': 'NORMALIZATION', 'code': 'BAD_ORDER'})
        response = self.post(f'failed-records/{receipt.object_id}/retry')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(SourceFreshness.objects.exists())

    def test_retry_limit_and_idempotency_binding(self):
        MonitoringPolicy.objects.create(business=self.business, max_retries=1)
        row = self.failed(self.payload(body={'id': 'p-1', 'title': 'Coffee'}))
        self.assertEqual(self.post(f'failed-records/{row.pk}/retry').data['status'], 'FAILED')
        with patch('django.utils.timezone.now', return_value=NOW + timedelta(hours=1)):
            self.assertEqual(self.post(f'failed-records/{row.pk}/retry', 'over-limit').status_code, 400)
        self.assertEqual(self.post(f'connections/{self.connection.pk}/test').status_code, 400)

    def test_retry_sync_creates_new_run_and_keeps_original_failure(self):
        payload = self.payload()
        original = observe(self, 'sync', {'status': 'FAILED', 'entity_type': 'PRODUCT', 'sync_type': 'INCREMENTAL',
            'records_received': 1, 'records_failed': 1, 'metadata': {'payload_ids': [payload.pk]}})
        response = self.post(f'syncs/{original.object_id}/retry')
        self.assertEqual(response.data['status'], 'SUCCEEDED')
        parent = IntegrationSyncLog.objects.get(pk=original.object_id)
        child = parent.retries.get()
        self.assertEqual(parent.status, 'FAILED')
        self.assertEqual(child.status, 'COMPLETED')
        self.assertEqual(child.records_succeeded, 1)
        self.assertEqual(child.trigger, 'RETRY')
        self.assertEqual(child.initiated_by, self.user)

    def test_sync_retry_counts_a_late_duplicate_as_skipped(self):
        newer = self.payload('newer', {'id': 'p-1', 'name': 'Newer'}, source_at=NOW - timedelta(minutes=10))
        older = self.payload('older', {'id': 'p-1', 'name': 'Older'}, source_at=NOW - timedelta(hours=2))
        original = observe(self, 'sync', {'status': 'FAILED', 'entity_type': 'PRODUCT', 'records_received': 2,
            'records_failed': 2, 'metadata': {'payload_ids': [newer.pk, older.pk]}})
        response = self.post(f'syncs/{original.object_id}/retry')
        self.assertEqual(response.data['status'], 'SUCCEEDED')
        run = IntegrationSyncLog.objects.get(parent_id=original.object_id)
        self.assertEqual(run.records_succeeded, 1)
        self.assertEqual(run.records_skipped, 1)
        self.assertEqual(run.records_processed, 2)
        self.assertEqual(Product.objects.get().name, 'Newer')

    def test_payload_is_immutable_and_cannot_be_rebound(self):
        payload = self.payload()
        again = self.payload()
        self.assertEqual(payload.pk, again.pk)
        payload.body['name'] = 'Changed'
        with self.assertRaises(ValidationError):
            payload.save()
        with self.assertRaises(ValidationError):
            self.payload(body={'id': 'p-1', 'name': 'Changed'})

    def test_payload_connection_cannot_be_injected_into_retry(self):
        other_payload = capture_payload(self.other_connection.pk, 'other', {'id': 'p-2', 'name': 'Other'})
        with self.assertRaises(ValidationError):
            self.failed(other_payload)
        self.assertFalse(OperationAttempt.objects.exists())

    def test_reader_and_cross_business_action_attempts_are_denied(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.post(f'connections/{self.connection.pk}/test').status_code, 403)
        self.client.force_authenticate(self.user)
        self.assertIn(self.post(f'connections/{self.other_connection.pk}/test').status_code, [400, 404])
        self.assertFalse(OperationAttempt.objects.exists())

    def test_newer_product_source_data_is_not_overwritten_by_old_replay(self):
        latest = self.payload('new', {'id': 'p-1', 'name': 'New'}, source_at=NOW - timedelta(minutes=10))
        row = self.failed(latest)
        self.post(f'failed-records/{row.pk}/retry', 'new')
        old = self.payload('old', {'id': 'p-1', 'name': 'Old'})
        receipt = observe(self, 'failed_record', {'entity_type': 'PRODUCT', 'external_id': 'p-1',
            'stage': 'MAPPING', 'code': 'MAPPING_ERROR', 'payload_id': old.pk}, key='old-failure')
        self.assertEqual(self.post(f'failed-records/{receipt.object_id}/retry', 'old').data['status'], 'SUCCEEDED')
        self.assertEqual(Product.objects.get().name, 'New')
        self.assertEqual(SourceFreshness.objects.get().coverage_at, NOW - timedelta(minutes=10))

    def test_operation_request_cannot_replace_payload_or_force_status(self):
        row = self.failed()
        response = self.client.post(self.root + f'failed-records/{row.pk}/retry/',
            {'idempotency_key': 'injection', 'payload': {'name': 'Injected'}, 'status': 'SUCCEEDED'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Product.objects.exists())

    def test_registered_processing_owner_can_confirm_another_canonical_domain(self):
        from app.integrations.operations import ProcessingResult, _adapters
        from app.models import Order
        self.connection.is_mock = False
        self.connection.save()
        payload = self.payload('order', {'id': 'o-1'})
        row = self.failed(payload, entity_type='ORDER', external_id='o-1')
        class OrderOwnerAdapter:
            def __init__(adapter, connection):
                adapter.connection = connection

            def process(adapter, payload, entity_type, now):
                order = Order.objects.create(business_id=adapter.connection.business_id,
                    integration_connection=adapter.connection, external_order_id='o-1', created_at=now, updated_at=now)
                return ProcessingResult('ORDER', 'o-1', order.pk, payload.source_at, payload.received_at)

            def confirm_processing(adapter, result):
                return Order.objects.filter(pk=result.canonical_id, business_id=adapter.connection.business_id,
                    integration_connection=adapter.connection, external_order_id=result.external_id).exists()
        with patch.dict(_adapters, {self.source.key: OrderOwnerAdapter}):
            response = self.post(f'failed-records/{row.pk}/retry')
        self.assertEqual(response.data['status'], 'SUCCEEDED')
        self.assertEqual(SourceFreshness.objects.get().entity_type, 'ORDER')
        self.assertTrue(Order.objects.filter(business=self.business).exists())

    def test_processing_owner_rejection_rolls_back_without_false_freshness(self):
        from app.integrations.operations import MockIntegrationOperations
        row = self.failed()
        with patch.object(MockIntegrationOperations, 'confirm_processing', return_value=False, create=True):
            response = self.post(f'failed-records/{row.pk}/retry')
        self.assertEqual(response.data['status'], 'FAILED')
        self.assertFalse(Product.objects.exists())
        self.assertFalse(SourceFreshness.objects.exists())
