from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from app.events import DomainEvent, dispatch
from app.models import (BusinessAccess, ConnectionCheck, FailedRecord, IntegrationError,
                        IntegrationSyncLog, MonitoringPolicy, ObservationReceipt, SourceFreshness,
                        WebhookObservation)
from app.observability.services import record_observation
from app.tests.observability_helpers import NOW, observe, setup_businesses


class RecordingTests(TestCase):
    def setUp(self):
        setup_businesses(self)

    def test_connection_observation_is_persisted_once(self):
        receipt = observe(self, 'connection_check', {'outcome': 'SUCCESS', 'latency_ms': 10})
        again = observe(self, 'connection_check', {'outcome': 'SUCCESS', 'latency_ms': 10})
        self.assertEqual(receipt.pk, again.pk)
        self.assertEqual(ConnectionCheck.objects.count(), 1)
        self.assertEqual(ConnectionCheck.objects.get().observed_at, NOW)

    def test_reusing_observation_key_for_different_data_is_rejected(self):
        observe(self, 'connection_check', {'outcome': 'SUCCESS'})
        with self.assertRaises(ValidationError):
            observe(self, 'connection_check', {'outcome': 'AUTH_ERROR'})

    def test_cross_business_connection_and_sync_references_are_rejected_atomically(self):
        with self.assertRaises(ValidationError):
            record_observation(self.business.pk, self.other_connection.pk, 'bad', 'connection_check',
                               {'outcome': 'SUCCESS'}, NOW)
        sync = IntegrationSyncLog.objects.create(integration_connection=self.other_connection,
                                                 status='RUNNING', started_at=NOW, created_at=NOW)
        with self.assertRaises(ValidationError):
            observe(self, 'failed_record', {'entity_type': 'PRODUCT', 'external_id': '1',
                                            'stage': 'MAPPING', 'code': 'BAD_MAPPING', 'sync_id': sync.pk})
        self.assertEqual(ObservationReceipt.objects.count(), 0)
        self.assertEqual(FailedRecord.objects.count(), 0)

    def test_invalid_observation_kind_status_timing_and_counter_are_rejected(self):
        cases = [('unknown', {}), ('connection_check', {'outcome': 'MADE_UP'}),
                 ('connection_check', {'outcome': 'SUCCESS', 'latency_ms': -1}),
                 ('provider_request', {'outcome': 'SUCCESS', 'http_status': 999}),
                 ('sync', {'entity_type': 'PRODUCT', 'status': 'RUNNING', 'records_received': -1})]
        for i, (kind, data) in enumerate(cases):
            with self.subTest(kind=kind, data=data), self.assertRaises(ValidationError):
                observe(self, kind, data, key=f'bad-{i}')
        with self.assertRaises(ValidationError):
            observe(self, 'connection_check', {'outcome': 'SUCCESS'}, observed_at=NOW.replace(tzinfo=None))
        self.assertFalse(ObservationReceipt.objects.exists())

    def test_real_dispatch_and_repeated_startup_do_not_duplicate_handler(self):
        from django.apps import apps
        apps.get_app_config('app').ready()
        apps.get_app_config('app').ready()
        dispatch(DomainEvent('integration.observation', dict(business_id=self.business.pk,
            connection_id=self.connection.pk, key='dispatch', kind='connection_check',
            data={'outcome': 'SUCCESS'}, observed_at=NOW, received_at=NOW)))
        self.assertEqual(ConnectionCheck.objects.count(), 1)

    def test_outer_transaction_rollback_removes_accepted_observation(self):
        try:
            with transaction.atomic():
                observe(self, 'connection_check', {'outcome': 'SUCCESS'})
                raise RuntimeError('rollback')
        except RuntimeError:
            pass
        self.assertFalse(ConnectionCheck.objects.exists())
        self.assertFalse(ObservationReceipt.objects.exists())

    def test_grouped_errors_count_distinct_occurrences_and_reopen(self):
        data = {'code': 'INVALID_PRODUCT_REFERENCE', 'category': 'VALIDATION', 'severity': 'HIGH',
                'entity_type': 'ORDER', 'message': 'Some orders contain an unknown product.'}
        observe(self, 'integration_error', data, key='err-1')
        observe(self, 'integration_error', data, key='err-1')
        error = IntegrationError.objects.get()
        self.assertEqual(error.occurrences, 1)
        error.status = 'RESOLVED'
        error.save()
        observe(self, 'integration_error', data, key='err-2', observed_at=NOW + timedelta(seconds=1))
        error.refresh_from_db()
        self.assertEqual(error.occurrences, 2)
        self.assertEqual(error.status, 'ACTIVE')
        self.assertEqual(error.first_seen_at, NOW)
        self.assertEqual(error.last_seen_at, NOW + timedelta(seconds=1))

    def test_freshness_is_monotonic_and_old_replay_cannot_refresh_it(self):
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'source_at': NOW - timedelta(minutes=10)})
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'source_at': NOW - timedelta(hours=2)}, key='late')
        row = SourceFreshness.objects.get()
        self.assertEqual(row.coverage_at, NOW - timedelta(minutes=10))
        self.assertEqual(row.confirmed_at, NOW)
        with self.assertRaises(ValidationError):
            observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'source_at': NOW + timedelta(hours=1)}, key='future')

    def test_missing_source_time_uses_original_reception_not_processing_time(self):
        observe(self, 'data_confirmed', {'entity_type': 'PRODUCT', 'original_received_at': NOW - timedelta(days=1)})
        self.assertEqual(SourceFreshness.objects.get().coverage_at, NOW - timedelta(days=1))

    def test_source_timestamp_cannot_be_newer_than_original_reception(self):
        with self.assertRaises(ValidationError):
            observe(self, 'data_confirmed', {'entity_type': 'PRODUCT', 'source_at': NOW,
                'original_received_at': NOW - timedelta(hours=1)})
        self.assertFalse(SourceFreshness.objects.exists())

    def test_partial_sync_progress_terminal_state_and_retry_accounting(self):
        start = observe(self, 'sync', {'entity_type': 'PRODUCT', 'status': 'PENDING', 'sync_type': 'INCREMENTAL',
                                      'trigger': 'SCHEDULED'})
        sync_id = start.object_id
        observe(self, 'sync', {'sync_id': sync_id, 'status': 'RUNNING', 'records_received': 10,
                               'discovered': 10}, key='running')
        done = {'sync_id': sync_id, 'status': 'PARTIAL', 'records_received': 10,
                'records_succeeded': 8, 'records_skipped': 1, 'records_failed': 1}
        observe(self, 'sync', done, key='complete', observed_at=NOW + timedelta(seconds=10))
        observe(self, 'sync', done, key='complete', observed_at=NOW + timedelta(seconds=10))
        run = IntegrationSyncLog.objects.get(pk=sync_id)
        self.assertEqual(run.records_processed, 10)
        self.assertEqual(run.records_failed, 1)
        self.assertEqual(run.trigger, 'SCHEDULED')
        self.assertEqual(run.sync_type, 'INCREMENTAL')
        self.assertEqual(run.completed_at, NOW + timedelta(seconds=10))
        self.assertFalse(SourceFreshness.objects.exists())
        with self.assertRaises(ValidationError):
            observe(self, 'sync', {'sync_id': sync_id, 'status': 'RUNNING'}, key='illegal',
                    observed_at=NOW + timedelta(seconds=20))

    def test_out_of_order_sync_progress_does_not_overwrite_newer_counts(self):
        run = observe(self, 'sync', {'entity_type': 'ORDER', 'status': 'RUNNING', 'records_received': 3,
                                    'records_succeeded': 2})
        observe(self, 'sync', {'sync_id': run.object_id, 'status': 'RUNNING', 'records_received': 1},
                key='older', observed_at=NOW - timedelta(seconds=5))
        self.assertEqual(IntegrationSyncLog.objects.get().records_received, 3)

    def test_pending_queue_time_is_not_counted_as_sync_execution_duration(self):
        receipt = observe(self, 'sync', {'entity_type': 'PRODUCT', 'status': 'PENDING'},
                          observed_at=NOW - timedelta(minutes=5))
        self.assertIsNone(IntegrationSyncLog.objects.get(pk=receipt.object_id).started_at)
        observe(self, 'sync', {'sync_id': receipt.object_id, 'status': 'RUNNING'}, key='running',
                observed_at=NOW - timedelta(minutes=1))
        observe(self, 'sync', {'sync_id': receipt.object_id, 'status': 'COMPLETED'}, key='done')
        row = IntegrationSyncLog.objects.get(pk=receipt.object_id)
        self.assertEqual((row.completed_at - row.started_at).total_seconds(), 60)

    def test_invalid_signature_captures_failure_once_and_never_advances_freshness(self):
        data = {'event_id': 'ext-1', 'event_type': 'order.created', 'entity_type': 'ORDER',
                'validation': 'INVALID', 'status': 'REJECTED'}
        observe(self, 'webhook', data)
        observe(self, 'webhook', data)
        self.assertEqual(WebhookObservation.objects.get().status, 'REJECTED')
        self.assertEqual(IntegrationError.objects.get().occurrences, 1)
        self.assertEqual(FailedRecord.objects.get().code, 'WEBHOOK_SIGNATURE_INVALID')
        self.assertFalse(SourceFreshness.objects.exists())

    def test_duplicate_delivery_tracks_delivery_without_duplicate_processing(self):
        data = {'event_id': 'external-event', 'event_type': 'product.updated', 'entity_type': 'PRODUCT',
                'validation': 'VALID', 'status': 'PROCESSED'}
        observe(self, 'webhook', data)
        observe(self, 'webhook', data, key='delivery-2')
        row = WebhookObservation.objects.get()
        self.assertEqual(row.delivery_count, 2)
        self.assertEqual(row.status, 'PROCESSED')
        self.assertEqual(row.processed_at, NOW)

    def test_policy_relationships_and_thresholds_are_validated(self):
        for kwargs in [{'connection': self.other_connection}, {'delayed_seconds': 100, 'stale_seconds': 50}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                MonitoringPolicy(business=self.business, **kwargs).full_clean()

    def test_grants_are_unique_and_policy_database_constraints_apply(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            BusinessAccess.objects.create(business=self.business, user=self.user, role='READER')
        with self.assertRaises(IntegrityError), transaction.atomic():
            MonitoringPolicy.objects.create(business=self.business, delayed_seconds=100, stale_seconds=50)
