from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from app.models import IntegrationError, MonitoringPolicy
from app.tests.observability_helpers import NOW, make_connection, observe, setup_businesses


class ObservabilityAPITests(APITestCase):
    def setUp(self):
        setup_businesses(self)
        self.root = f'/api/businesses/{self.business.pk}/observability/'
        self.client.force_authenticate(self.user)
        self.clock = patch('app.observability.views.timezone.now', return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def get(self, resource, **params):
        return self.client.get(self.root + resource + '/', params)

    def test_every_collection_is_available_paginated_and_empty_safely(self):
        for resource in ['connections', 'syncs', 'failed-records', 'webhooks', 'freshness', 'providers', 'errors']:
            with self.subTest(resource=resource):
                response = self.get(resource)
                self.assertEqual(response.status_code, 200)
                self.assertIn('results', response.data)
                self.assertIn('count', response.data)
        self.assertEqual(self.get('summary').data['status'], 'UNKNOWN')

    def test_anonymous_and_ungranted_users_cannot_read_any_business(self):
        for user in [None, get_user_model().objects.create_user(username='outsider')]:
            self.client.force_authenticate(user)
            for resource in ['summary', 'connections', 'syncs', 'failed-records', 'webhooks', 'freshness', 'providers', 'errors']:
                with self.subTest(user=user, resource=resource):
                    self.assertIn(self.get(resource).status_code, [401, 403])

    def test_reader_can_read_but_not_operate_or_change_policy(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.get('summary').status_code, 200)
        self.assertEqual(self.client.post(self.root + f'connections/{self.connection.pk}/test/',
                                         {'idempotency_key': 'test'}, format='json').status_code, 403)
        self.assertEqual(self.client.put(self.root + 'policies/', {'entity_type': 'ORDER'}, format='json').status_code, 403)

    def test_cross_business_route_detail_filter_and_policy_references_are_denied(self):
        other_root = f'/api/businesses/{self.other_business.pk}/observability/'
        self.assertEqual(self.client.get(other_root + 'connections/').status_code, 403)
        self.assertEqual(self.get(f'connections/{self.other_connection.pk}').status_code, 404)
        self.assertEqual(self.get('connections', connection=self.other_connection.pk).status_code, 400)
        response = self.client.put(self.root + 'policies/', {'connection_id': self.other_connection.pk,
                                    'entity_type': 'ORDER'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_connection_health_freshness_and_sensitive_config_are_separate(self):
        self.connection.config = {'access_token': 'top-secret'}
        self.connection.save()
        observe(self, 'connection_check', {'outcome': 'SUCCESS'})
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'source_at': NOW - timedelta(hours=1)}, key='data')
        response = self.get(f'connections/{self.connection.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['health']['status'], 'HEALTHY')
        self.assertEqual(response.data['freshness'][0]['status'], 'STALE')
        self.assertEqual(response.data['summary_status'], 'STALE')
        self.assertNotIn('top-secret', str(response.data))
        self.assertNotIn('config', response.data)

    def test_expired_and_disabled_lifecycle_and_old_observation_are_honest(self):
        observe(self, 'connection_check', {'outcome': 'SUCCESS'}, observed_at=NOW - timedelta(hours=2))
        self.assertEqual(self.get(f'connections/{self.connection.pk}').data['health']['status'], 'UNKNOWN')
        for lifecycle, expected in [('EXPIRED', 'ERROR'), ('DISABLED', 'DISCONNECTED'), ('DISCONNECTED', 'DISCONNECTED')]:
            self.connection.status = lifecycle
            self.connection.save()
            with self.subTest(lifecycle=lifecycle):
                self.assertEqual(self.get(f'connections/{self.connection.pk}').data['summary_status'], expected)

    def test_signature_failures_are_one_coherent_problem_and_grouped_error(self):
        observe(self, 'connection_check', {'outcome': 'SUCCESS'})
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'source_at': NOW - timedelta(minutes=52)}, key='data')
        for i in range(37):
            observe(self, 'webhook', {'event_id': f'event-{i}', 'event_type': 'order.created',
                    'entity_type': 'ORDER', 'validation': 'INVALID'}, key=f'webhook-{i}')
        response = self.get('summary')
        self.assertEqual(response.data['status'], 'DEGRADED')
        self.assertEqual(response.data['failed_webhooks'], 37)
        self.assertEqual(response.data['active_error_groups'], 1)
        self.assertEqual(response.data['problems'][0]['failed_events'], 37)
        self.assertEqual(IntegrationError.objects.get().occurrences, 37)

    def test_error_lifecycle_does_not_repair_connection_or_freshness(self):
        observe(self, 'connection_check', {'outcome': 'AUTH_ERROR'})
        error = IntegrationError.objects.get()
        for status in ['ACKNOWLEDGED', 'RESOLVED']:
            response = self.client.patch(self.root + f'errors/{error.pk}/',
                                          {'status': status, 'note': 'Investigated'}, format='json')
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get(f'connections/{self.connection.pk}').data['health']['status'], 'ERROR')

    def test_validated_filters_time_ranges_pagination_and_safe_errors(self):
        observe(self, 'integration_error', {'code': 'MAPPING_ERROR', 'category': 'MAPPING',
                'details': {'Access_Token': 'secret-value'}, 'entity_type': 'PRODUCT'})
        self.assertEqual(self.get('errors', entity_type='PRODUCT', page_size=1).data['count'], 1)
        self.assertEqual(self.get('errors', entity_type='ORDER').data['count'], 0)
        for params in [{'status': 'MADE_UP'}, {'provider': 'bad'}, {'ordering': 'config'},
                       {'from': 'not-a-time'}, {'from': NOW.isoformat(), 'to': (NOW - timedelta(days=1)).isoformat()},
                       {'page_size': 10000}, {'connection': 'wrong'}]:
            with self.subTest(params=params):
                self.assertEqual(self.get('errors', **params).status_code, 400)
        self.assertNotIn('secret-value', str(self.get('errors').data))

    def test_policy_defaults_overrides_missing_entity_and_invalid_thresholds(self):
        response = self.client.put(self.root + 'policies/', {'entity_type': 'ORDER', 'delayed_seconds': 30,
                                   'stale_seconds': 60}, format='json')
        self.assertEqual(response.status_code, 200)
        rows = self.get('freshness').data['results']
        self.assertEqual(rows[0]['status'], 'UNAVAILABLE')
        observe(self, 'data_confirmed', {'entity_type': 'ORDER', 'source_at': NOW - timedelta(seconds=61)})
        self.assertEqual(self.get('freshness').data['results'][0]['status'], 'STALE')
        MonitoringPolicy.objects.create(business=self.business, connection=self.connection,
                                       entity_type='ORDER', delayed_seconds=90, stale_seconds=120)
        self.assertEqual(self.get('freshness').data['results'][0]['status'], 'FRESH')
        bad = self.client.put(self.root + 'policies/', {'delayed_seconds': 100, 'stale_seconds': 50}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_provider_wide_diagnostics_require_explicit_privilege(self):
        self.assertEqual(self.get('providers', scope='global').status_code, 403)
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual(self.get('providers', scope='global').status_code, 200)

    def test_read_collections_do_not_make_network_calls(self):
        with patch('socket.create_connection', side_effect=AssertionError('GET attempted network')):
            self.assertEqual(self.get('connections').status_code, 200)
            self.assertEqual(self.get('providers').status_code, 200)

    def test_connection_collection_query_growth_is_bounded(self):
        observe(self, 'connection_check', {'outcome': 'SUCCESS'})
        with CaptureQueriesContext(connection) as small:
            self.get('connections')
        for _ in range(20):
            make_connection(self.business, self.source)
        with CaptureQueriesContext(connection) as large:
            response = self.get('connections')
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(large), len(small) + 2)

    def test_history_and_active_sync_filters_include_real_progress(self):
        start = observe(self, 'sync', {'entity_type': 'PRODUCT', 'status': 'RUNNING', 'records_received': 3,
                                      'records_succeeded': 2, 'cursor': {'access_token': 'hidden', 'page': 2}})
        response = self.get('syncs', active='true')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['records_processed'], 2)
        self.assertEqual(response.data['results'][0]['progress_percent'], None)
        self.assertNotIn('hidden', str(response.data))
        self.assertEqual(self.get(f'syncs/{start.object_id}').status_code, 200)

    def test_untrusted_http_cannot_publish_observations(self):
        self.assertIn(self.client.post(self.root + 'observations/', {'kind': 'data_confirmed'},
                                       format='json').status_code, [404, 405])

    def test_payload_diagnostic_requires_manager_redacts_and_audits_access(self):
        from app.integrations.payloads import capture_payload
        from app.models import ObservabilityAudit
        payload = capture_payload(self.connection.pk, 'diagnostic', {'id': 'p-1', 'name': 'Coffee',
            'api_key': 'private-source-key'}, received_at=NOW)
        path = self.root + f'payloads/{payload.pk}/'
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get(path).status_code, 403)
        self.client.force_authenticate(self.user)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['diagnostic_payload']['name'], 'Coffee')
        self.assertNotIn('private-source-key', str(response.data))
        self.assertEqual(payload.body['api_key'], 'private-source-key')
        self.assertTrue(ObservabilityAudit.objects.filter(target_type='payload', target_id=payload.pk,
                                                        action='DIAGNOSTIC_READ', actor=self.user).exists())
        self.assertIn(self.client.put(path, {'body': {}}, format='json').status_code, [403, 405])

    def test_payload_diagnostic_and_delivery_history_are_business_scoped(self):
        from app.integrations.payloads import capture_payload
        other = capture_payload(self.other_connection.pk, 'other', {'id': 'other'}, received_at=NOW)
        self.assertEqual(self.client.get(self.root + f'payloads/{other.pk}/').status_code, 404)
        data = {'event_id': 'delivery-history', 'event_type': 'product.updated', 'validation': 'VALID'}
        receipt = observe(self, 'webhook', data, key='delivery1')
        observe(self, 'webhook', data, key='delivery2')
        response = self.get(f'webhooks/{receipt.object_id}')
        self.assertEqual(len(response.data['deliveries']), 2)
        self.assertTrue(response.data['deliveries'][0]['duplicate'])
