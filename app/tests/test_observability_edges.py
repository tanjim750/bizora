from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APITestCase

from app.integrations.payloads import capture_payload
from app.models import (BusinessAccess, BusinessIssue, FailedRecord, IntegrationError,
                        MonitoringPolicy, Product, SourceFreshness, WebhookObservation)
from app.observability.services import publish_after_commit, record_observation
from app.tests.observability_helpers import NOW, observe, setup_businesses


class EdgeCaseTests(APITestCase):
    def setUp(self):
        setup_businesses(self)
        self.root = f'/api/businesses/{self.business.pk}/observability/'
        self.client.force_authenticate(self.user)
        patcher = patch('django.utils.timezone.now', return_value=NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_invalid_role_is_not_a_read_grant(self):
        BusinessAccess.objects.filter(user=self.user).update(role='INVALID')
        self.assertEqual(self.client.get(self.root + 'summary/').status_code, 403)

    def test_malformed_event_identifiers_are_validation_errors(self):
        for business_id, connection_id in [('invalid', self.connection.pk), (self.business.pk, True),
                                            (self.business.pk, 'not-an-id')]:
            with self.subTest(business_id=business_id, connection_id=connection_id), self.assertRaises(ValidationError):
                record_observation(business_id, connection_id, 'bad', 'connection_check', {'outcome': 'SUCCESS'}, NOW)

    def test_provider_status_uses_cross_connection_evidence_without_tenant_details(self):
        for i, connection in enumerate([self.connection, self.other_connection, self.other_connection]):
            record_observation(connection.business_id, connection.pk, f'provider-{i}', 'provider_request',
                {'outcome': 'PROVIDER_ERROR', 'target': 'GLOBAL', 'capability': 'products', 'http_status': 503}, NOW, NOW)
        response = self.client.get(self.root + 'providers/')
        provider = response.data['results'][0]
        self.assertEqual(provider['status'], 'UNAVAILABLE')
        self.assertEqual(provider['capabilities'][0]['local_sample_count'], 1)
        self.assertNotIn('sample_count', provider['capabilities'][0])
        self.assertNotIn('connection_id', str(provider))
        self.assertNotIn(self.other_business.name, str(provider))

    def test_connection_rate_limit_does_not_declare_provider_outage(self):
        for i, connection in enumerate([self.connection, self.other_connection, self.other_connection]):
            record_observation(connection.business_id, connection.pk, f'quota-{i}', 'provider_request',
                {'outcome': 'RATE_LIMIT', 'target': 'GLOBAL', 'quota_scope': 'CONNECTION', 'http_status': 429}, NOW, NOW)
        self.assertEqual(self.client.get(self.root + 'providers/').data['results'][0]['status'], 'UNKNOWN')

    def test_provider_old_evidence_expires_and_new_evidence_recovers(self):
        for prefix, offset, outcome in [('old', -1000, 'PROVIDER_ERROR'), ('new', 0, 'SUCCESS')]:
            for i, connection in enumerate([self.connection, self.other_connection, self.other_connection]):
                record_observation(connection.business_id, connection.pk, f'{prefix}-{i}', 'provider_request',
                    {'outcome': outcome, 'target': 'GLOBAL', 'latency_ms': 10}, NOW + timedelta(seconds=offset), NOW)
        self.assertEqual(self.client.get(self.root + 'providers/').data['results'][0]['status'], 'HEALTHY')

    def test_webhook_latency_missing_and_skewed_times_are_explained(self):
        for key, provider_at, reason, latency in [('missing', None, 'NO_PROVIDER_TIME', None),
            ('skewed', NOW + timedelta(seconds=2), 'CLOCK_SKEW', None),
            ('normal', NOW - timedelta(seconds=4), 'AVAILABLE', 4)]:
            data = {'event_id': key, 'event_type': 'product.updated', 'validation': 'VALID', 'status': 'PROCESSED'}
            if provider_at:
                data['provider_event_at'] = provider_at
            receipt = observe(self, 'webhook', data, key=key)
            response = self.client.get(self.root + f'webhooks/{receipt.object_id}/')
            self.assertEqual(response.data['latency_reason'], reason)
            self.assertEqual(response.data['transport_latency_seconds'], latency)

    def test_validated_webhook_cannot_claim_unverified_captured_payload(self):
        payload = capture_payload(self.connection.pk, 'unverified', {'id': 'p-1', 'name': 'Coffee'})
        with self.assertRaises(ValidationError):
            observe(self, 'webhook', {'event_id': 'event', 'event_type': 'product.updated',
                'validation': 'VALID', 'status': 'PROCESSED', 'payload_id': payload.pk})
        self.assertFalse(WebhookObservation.objects.exists())

    def test_failed_record_groups_and_review_history_are_inspectable(self):
        for i in range(3):
            observe(self, 'failed_record', {'entity_type': 'PRODUCT', 'external_id': str(i),
                    'stage': 'MAPPING', 'code': 'BAD_PRODUCT'}, key=f'failure-{i}')
        grouped = self.client.get(self.root + 'failed-records/groups/', {'group_by': 'code'})
        self.assertEqual(grouped.status_code, 200)
        self.assertEqual(grouped.data['results'][0]['count'], 3)
        row = FailedRecord.objects.first()
        self.assertEqual(self.client.patch(self.root + f'failed-records/{row.pk}/',
            {'status': 'REVIEWING', 'note': 'Checking mapping'}, format='json').status_code, 200)
        history = self.client.get(self.root + f'failed-records/{row.pk}/').data['history']
        self.assertIsInstance(history[0]['created_at'], str)
        self.assertNotEqual(history[0]['created_at'], '[UNSUPPORTED]')
        self.assertEqual(self.client.patch(self.root + f'failed-records/{row.pk}/',
            {'status': 'RESOLVED'}, format='json').status_code, 400)

    def test_sync_statistics_and_business_local_daily_duration_history(self):
        start_at = NOW - timedelta(minutes=5)
        run = observe(self, 'sync', {'entity_type': 'PRODUCT', 'status': 'RUNNING'},
                      observed_at=start_at)
        observe(self, 'sync', {'sync_id': run.object_id, 'status': 'COMPLETED'}, key='complete')
        response = self.client.get(self.root + 'syncs/statistics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['runs'], 1)
        self.assertEqual(response.data['average_duration_seconds'], 300)
        self.assertEqual(response.data['daily'][0]['runs'], 1)
        self.assertEqual(response.data['timezone'], 'Asia/Dhaka')

    def test_partial_sync_retry_preserves_success_but_marks_entity_incomplete(self):
        good = capture_payload(self.connection.pk, 'good', {'id': 'p-1', 'name': 'Coffee'}, received_at=NOW)
        bad = capture_payload(self.connection.pk, 'bad', {'id': 'p-2'}, received_at=NOW)
        receipt = observe(self, 'sync', {'entity_type': 'PRODUCT', 'status': 'FAILED',
            'records_received': 2, 'records_failed': 2, 'metadata': {'payload_ids': [good.pk, bad.pk]}})
        response = self.client.post(self.root + f'syncs/{receipt.object_id}/retry/',
                                    {'idempotency_key': 'retry'}, format='json')
        self.assertEqual(response.data['status'], 'FAILED')
        self.assertEqual(response.data['result']['sync_status'], 'PARTIAL')
        self.assertEqual(Product.objects.count(), 1)
        self.assertFalse(SourceFreshness.objects.get().complete)
        self.assertTrue(self.client.get(self.root + 'freshness/').data['results'][0]['warning'])

    def test_unexpected_processing_failure_rolls_back_and_keeps_safe_attempt(self):
        payload = capture_payload(self.connection.pk, 'good', {'id': 'p-1', 'name': 'Coffee'}, received_at=NOW)
        receipt = observe(self, 'failed_record', {'entity_type': 'PRODUCT', 'external_id': 'p-1',
            'stage': 'PERSISTENCE', 'code': 'PROCESSING_FAILED', 'payload_id': payload.pk})
        def broken_processor(*args):
            Product.objects.create(business=self.business, name='Partial', created_at=NOW, updated_at=NOW)
            raise RuntimeError('access_token=should-not-leak')
        with patch('app.integrations.operations.MockIntegrationOperations.process', side_effect=broken_processor), self.assertLogs(
                'app.observability.operations', level='ERROR'):
            response = self.client.post(self.root + f'failed-records/{receipt.object_id}/retry/',
                                        {'idempotency_key': 'failure'}, format='json')
        self.assertEqual(response.data['status'], 'FAILED')
        self.assertEqual(response.data['result']['code'], 'INTERNAL_PROCESSING_ERROR')
        self.assertNotIn('should-not-leak', str(response.data))
        self.assertFalse(Product.objects.exists())
        self.assertFalse(SourceFreshness.objects.exists())

    def test_filters_not_supported_by_resource_are_rejected(self):
        for resource, params in [('connections', {'category': 'AUTHENTICATION'}),
            ('connections', {'ordering': 'config'}), ('providers', {'active': 'true'})]:
            with self.subTest(resource=resource, params=params):
                self.assertEqual(self.client.get(self.root + resource + '/', params).status_code, 400)

    def test_freshness_status_filter_and_disabled_monitoring(self):
        observe(self, 'data_confirmed', {'entity_type': 'PRODUCT', 'source_at': NOW - timedelta(hours=1)})
        self.assertEqual(self.client.get(self.root + 'freshness/', {'status': 'STALE'}).data['results'][0]['status'], 'STALE')
        self.assertEqual(self.client.get(self.root + 'freshness/', {'status': 'FRESH'}).data['results'], [])
        MonitoringPolicy.objects.create(business=self.business, enabled=False)
        self.assertEqual(self.client.get(self.root + 'summary/').data['status'], 'UNKNOWN')

    def test_configuration_rejects_boolean_and_fractional_intervals(self):
        for value in [True, 1.5]:
            response = self.client.put(self.root + 'policies/', {'delayed_seconds': value}, format='json')
            with self.subTest(value=value):
                self.assertEqual(response.status_code, 400)

    def test_disconnection_is_visible_but_explicit_disable_suppresses_alerts(self):
        self.connection.status = 'DISCONNECTED'
        self.connection.save()
        summary = self.client.get(self.root + 'summary/').data
        self.assertEqual(summary['status'], 'DISCONNECTED')
        self.assertEqual(len(summary['problems']), 1)
        self.connection.status = 'DISABLED'
        self.connection.save()
        self.assertEqual(self.client.get(self.root + 'summary/').data['problems'], [])

    def test_entity_monitoring_disable_suppresses_stale_summary_without_falsifying_data(self):
        observe(self, 'connection_check', {'outcome': 'SUCCESS'})
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'source_at': NOW - timedelta(hours=2)}, key='old')
        MonitoringPolicy.objects.create(business=self.business, connection=self.connection, entity_type='ORDER', enabled=False)
        self.assertEqual(self.client.get(self.root + 'summary/').data['status'], 'HEALTHY')
        freshness = self.client.get(self.root + 'freshness/').data['results'][0]
        self.assertEqual(freshness['status'], 'STALE')
        self.assertFalse(freshness['monitoring_enabled'])

    def test_unknown_and_incomplete_entity_data_produce_explained_reliability_warnings(self):
        observe(self, 'connection_check', {'outcome': 'SUCCESS'})
        MonitoringPolicy.objects.create(business=self.business, entity_type='ORDER')
        self.assertEqual(self.client.get(self.root + 'summary/').data['status'], 'UNKNOWN')
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'complete': False}, key='partial')
        summary = self.client.get(self.root + 'summary/').data
        self.assertEqual(summary['status'], 'DEGRADED')
        self.assertEqual(summary['problems'][0]['reason'], 'INCOMPLETE_OR_DELAYED_DATA')

    def test_downstream_context_warns_on_incomplete_data_without_business_issues(self):
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'complete': False})
        result = self.client.get(self.root + 'freshness/').data['results'][0]
        self.assertEqual(result['status'], 'FRESH')
        self.assertTrue(result['warning'])
        self.assertIn('as_of', result)
        self.assertFalse(BusinessIssue.objects.exists())

    def test_stalled_sync_and_empty_poll_do_not_fabricate_valid_data(self):
        receipt = observe(self, 'sync', {'entity_type': 'PRODUCT', 'status': 'RUNNING'},
                          observed_at=NOW - timedelta(hours=2))
        self.assertTrue(self.client.get(self.root + f'syncs/{receipt.object_id}/').data['stalled'])
        observe(self, 'sync', {'entity_type': 'ORDER', 'status': 'COMPLETED'}, key='empty')
        self.assertFalse(SourceFreshness.objects.exists())

    def test_rate_limit_approaching_and_exhaustion_are_visible_for_own_connection(self):
        for i, (remaining, expected) in enumerate([(9, 'APPROACHING'), (0, 'EXHAUSTED')]):
            observe(self, 'provider_request', {'outcome': 'SUCCESS', 'rate_limit_remaining': remaining,
                    'retry_after_seconds': 30}, key=f'quota-{i}', observed_at=NOW + timedelta(seconds=i))
            with patch('django.utils.timezone.now', return_value=NOW + timedelta(seconds=i)):
                response = self.client.get(self.root + f'connections/{self.connection.pk}/')
            self.assertEqual(response.data['rate_limit']['status'], expected)
            self.assertEqual(response.data['rate_limit']['remaining'], remaining)
            self.assertEqual(response.data['health']['status'], 'DEGRADED')

    def test_recent_error_rate_and_stalled_sync_degrade_connection(self):
        for i, outcome in enumerate(['PROVIDER_ERROR', 'TIMEOUT', 'SUCCESS']):
            observe(self, 'provider_request', {'outcome': outcome}, key=f'pattern-{i}',
                    observed_at=NOW - timedelta(seconds=3-i))
        response = self.client.get(self.root + f'connections/{self.connection.pk}/')
        self.assertEqual(response.data['health']['status'], 'DEGRADED')
        self.assertEqual(response.data['health']['reason'], 'ELEVATED_REQUEST_ERROR_RATE')

    def test_every_documented_failure_stage_and_error_classification_accepts_valid_input(self):
        stages = ['RETRIEVAL', 'MAPPING', 'NORMALIZATION', 'VALIDATION', 'IDENTITY_INPUT', 'PERSISTENCE']
        for stage in stages:
            observe(self, 'failed_record', {'entity_type': 'PRODUCT', 'external_id': stage,
                    'stage': stage, 'code': f'{stage}_FAILED'}, key=stage)
        categories = ['AUTHENTICATION', 'CONNECTIVITY', 'PROVIDER_API', 'RATE_LIMIT', 'WEBHOOK', 'SYNC',
                      'MAPPING', 'NORMALIZATION', 'VALIDATION', 'INTERNAL']
        for category in categories:
            for severity in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
                observe(self, 'integration_error', {'code': f'{category}_{severity}', 'category': category,
                        'severity': severity}, key=f'{category}-{severity}')
        self.assertEqual(FailedRecord.objects.count(), len(stages))
        self.assertTrue(IntegrationError.objects.filter(category='RATE_LIMIT', severity='CRITICAL').exists())


class PublicationTests(TestCase):
    def setUp(self):
        setup_businesses(self)

    def test_publication_waits_until_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            publish_after_commit(business_id=self.business.pk, connection_id=self.connection.pk, key='post-commit',
                                 kind='data_confirmed', data={'entity_type': 'ORDER'}, observed_at=NOW, received_at=NOW)
            self.assertFalse(SourceFreshness.objects.exists())
        self.assertTrue(SourceFreshness.objects.exists())

    def test_rollback_does_not_publish_a_success(self):
        from django.db import transaction
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    publish_after_commit(business_id=self.business.pk, connection_id=self.connection.pk, key='rollback',
                                         kind='data_confirmed', data={'entity_type': 'ORDER'}, observed_at=NOW, received_at=NOW)
                    raise RuntimeError('rollback')
            except RuntimeError:
                pass
        self.assertFalse(SourceFreshness.objects.exists())
