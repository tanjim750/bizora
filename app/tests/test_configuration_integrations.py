import os
from unittest.mock import patch

from django.test import TestCase

from app.configuration.integrations import resolve_credentials
from app.models import ConfigurationRevision, IntegrationConnection, IntegrationSyncLog
from app.tests.configuration_helpers import setup_configuration
from app.tests.observability_helpers import NOW


@patch('app.configuration.views.timezone.now', return_value=NOW)
class IntegrationConfigurationTests(TestCase):
    def setUp(self):
        setup_configuration(self)

    def create(self, **changes):
        return self.client.post(self.base+'connections/', {'provider_id': self.source.pk, 'name': 'Store',
            'is_mock': True, 'enabled': True, 'entities': ['PRODUCT', 'ORDER'], 'scopes': ['READ_PRODUCTS', 'READ_ORDERS'],
            'sync': {'mode': 'INCREMENTAL', 'interval_seconds': 900},
            'webhooks': {'enabled': True, 'events': ['product.updated'], 'endpoint': 'https://example.com/hooks'},
            'provider_settings': {'base_url': 'https://store.example.com'},
            'mock': {'connection_outcome': 'SUCCESS', 'product_name_field': 'name'}, **changes}, format='json')

    def test_create_connection_configures_existing_integration_owner(self, _):
        result = self.create()
        self.assertEqual(result.status_code, 201, result.data)
        connection = IntegrationConnection.objects.get(pk=result.data['id'])
        self.assertEqual(connection.business_id, self.business.pk)
        self.assertEqual(connection.config['sync']['interval_seconds'], 900)
        self.assertEqual(connection.status, 'CONNECTED')
        self.assertFalse(IntegrationSyncLog.objects.exists())
        test = self.client.post(self.base+f'connections/{connection.pk}/test/', {'idempotency_key': 'check-1'}, format='json')
        self.assertEqual(test.status_code, 200, test.data)
        self.assertEqual(test.data['status'], 'SUCCEEDED')
        disable = self.client.patch(self.base+f'connections/{connection.pk}/', {'version': 1, 'enabled': False}, format='json')
        self.assertEqual(disable.status_code, 200, disable.data)
        connection.refresh_from_db()
        self.assertEqual(connection.status, 'DISABLED')
        self.assertEqual(connection.config['sync']['interval_seconds'], 900)

    def test_credentials_are_scoped_secret_references_never_values_or_history_leaks(self, _):
        ref = f'env:BIZORA_BUSINESS_{self.business.pk}_COMMERCE_TOKEN'
        response = self.create(credentials={'api_key': ref})
        self.assertEqual(response.status_code, 201, response.data)
        row = IntegrationConnection.objects.get(pk=response.data['id'])
        with patch.dict(os.environ, {ref[4:]: 'very-private-secret'}):
            self.assertEqual(resolve_credentials(row)['api_key'], 'very-private-secret')
            for path in (f'connections/{row.pk}/', f'connections/{row.pk}/history/'):
                result = self.client.get(self.base+path)
                self.assertEqual(result.status_code, 200)
                self.assertNotIn(ref, str(result.data))
                self.assertNotIn('very-private-secret', str(result.data))
        self.assertTrue(response.data['settings']['credentials']['configured'])
        self.assertNotIn('very-private-secret', str(list(ConfigurationRevision.objects.values_list('data', flat=True))))
        self.assertEqual(self.create(credentials={'api_key': 'literal-secret'}).status_code, 400)
        self.assertEqual(self.create(credentials={'api_key': f'env:BIZORA_BUSINESS_{self.other_business.pk}_TOKEN'}).status_code, 400)

    def test_steadfast_secret_key_uses_business_scoped_reference(self, _):
        prefix = f'env:BIZORA_BUSINESS_{self.business.pk}_'
        result = self.create(credentials={'api_key': prefix + 'STEADFAST_API',
                                          'secret_key': prefix + 'STEADFAST_SECRET'})
        self.assertEqual(result.status_code, 201, result.data)
        row = IntegrationConnection.objects.get(pk=result.data['id'])
        with patch.dict(os.environ, {prefix[4:] + 'STEADFAST_API': 'api-value',
                                          prefix[4:] + 'STEADFAST_SECRET': 'secret-value'}):
            self.assertEqual(resolve_credentials(row)['secret_key'], 'secret-value')
        self.assertNotIn('secret-value', str(row.config))

    def test_provider_scope_entity_and_unknown_secret_settings_are_rejected(self, _):
        for changes in ({'provider_id': 999999}, {'entities': ['DOCUMENT']}, {'scopes': ['DELETE_ALL']},
                        {'entities': ['PRODUCT'], 'scopes': ['READ_ORDERS']},
                        {'provider_settings': {'api_key': 'literal-secret'}}, {'mock': {'connection_outcome': 'UNKNOWN'}},
                        {'sync': {'mode': 'SCHEDULED', 'interval_seconds': 0}}):
            self.assertEqual(self.create(**changes).status_code, 400)

    def test_foreign_connections_and_history_cannot_be_modified(self, _):
        for path in (f'connections/{self.other_connection.pk}/', f'connections/{self.other_connection.pk}/history/'):
            self.assertEqual(self.client.get(self.base+path).status_code, 404)
        self.assertEqual(self.client.patch(self.base+f'connections/{self.other_connection.pk}/', {'name': 'Changed'}, format='json').status_code, 404)

    def test_legacy_connection_can_be_adopted_without_overwriting_runtime_health(self, _):
        self.connection.status = 'ERROR'
        self.connection.save(update_fields=['status'])
        result = self.client.patch(self.base+f'connections/{self.connection.pk}/', {'name': 'Renamed'}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, 'ERROR')
        self.assertEqual(result.data['version'], 1)

    def test_entity_selection_is_enforced_by_existing_retry_pipeline(self, _):
        from app.integrations.payloads import capture_payload
        from app.observability.services import record_observation
        from app.models import Product
        response = self.create(entities=['ORDER'], scopes=['READ_ORDERS'])
        self.assertEqual(response.status_code, 201)
        connection_id = response.data['id']
        payload = capture_payload(connection_id, 'product-1', {'id': 'p1', 'name': 'Coffee'}, received_at=NOW)
        receipt = record_observation(self.business.pk, connection_id, 'failed-product', 'failed_record',
            {'entity_type': 'PRODUCT', 'external_id': 'p1', 'stage': 'MAPPING', 'code': 'MAPPING_ERROR', 'payload_id': payload.pk}, NOW, NOW)
        result = self.client.post(f'/api/businesses/{self.business.pk}/observability/failed-records/{receipt.object_id}/retry/',
            {'idempotency_key': 'restricted-retry'}, format='json')
        self.assertEqual(result.status_code, 400)
        self.assertFalse(Product.objects.exists())
