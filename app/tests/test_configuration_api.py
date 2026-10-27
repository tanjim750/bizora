from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from app.models import ConfigurationEvent, ConfigurationRecord, ConfigurationRevision, MonitoringConfiguration
from app.tests.configuration_helpers import setup_configuration
from app.tests.observability_helpers import NOW


@patch('app.configuration.views.timezone.now', return_value=NOW)
class ConfigurationApiTests(TestCase):
    def setUp(self):
        setup_configuration(self)

    def put(self, section, body):
        return self.client.put(self.base+section+'/', body, format='json')

    def test_read_defaults_does_not_write_configuration(self, _):
        with CaptureQueriesContext(connection) as queries:
            for route in ('profile', 'general', 'ai', 'knowledge', 'rules', 'policies', 'connections', 'sources', 'providers', 'effective', 'changes', 'monitoring', 'freshness', 'reprocessing'):
                response = self.client.get(self.base+route+'/')
                self.assertEqual(response.status_code, 200, (route, response.data))
        self.assertFalse(ConfigurationRecord.objects.exists())
        self.assertFalse(MonitoringConfiguration.objects.exists())
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in queries))

    def test_every_section_requires_business_access_and_manager_writes(self, _):
        for route in ('profile', 'general', 'ai', 'knowledge', 'rules', 'policies', 'connections', 'sources', 'providers', 'effective', 'changes', 'monitoring', 'freshness', 'reprocessing'):
            self.client.force_authenticate(None)
            self.assertIn(self.client.get(self.base+route+'/').status_code, (401, 403))
            self.client.force_authenticate(self.user)
            self.assertEqual(self.client.get(f'/api/businesses/{self.other_business.pk}/configuration/{route}/').status_code, 403)
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.put('profile', {'name': 'No permission'}).status_code, 403)
        self.assertEqual(self.client.post(self.base+'rules/', {}, format='json').status_code, 403)

    def test_profile_updates_canonical_identity_and_records_history(self, _):
        response = self.put('profile', {'version': 0, 'name': 'Example Store', 'description': 'Coffee retailer',
            'industry': 'RETAIL', 'currency': 'USD', 'timezone': 'America/New_York',
            'contact': {'email': 'help@example.com', 'phone': '+8801000000000', 'website': 'https://example.com'},
            'location': {'country': 'BD', 'city': 'Dhaka'}, 'operating_regions': ['Dhaka', 'Gazipur'],
            'channels': ['WEBSITE', 'SOCIAL_COMMERCE'], 'metadata': {'store_type': 'online'}})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['version'], 1)
        self.business.refresh_from_db()
        self.assertEqual((self.business.name, self.business.currency, self.business.timezone), ('Example Store', 'USD', 'America/New_York'))
        self.assertEqual(ConfigurationRevision.objects.get().actor_id, self.user.pk)
        self.assertEqual(ConfigurationEvent.objects.count(), 1)
        self.assertEqual(self.put('profile', {'version': 0, 'name': 'Stale update'}).status_code, 409)
        self.assertEqual(self.put('profile', {'version': 1, 'name': 'Renamed'}).status_code, 200)
        history = self.client.get(self.base+'profile/history/').data
        self.assertEqual(history['count'], 2)
        self.assertEqual(history['results'][1]['settings']['name'], 'Example Store')

    def test_profile_and_general_share_currency_and_timezone(self, _):
        self.put('profile', {'currency': 'USD'})
        result = self.put('general', {'currency': 'EUR', 'timezone': 'Europe/Paris', 'locale': 'fr-FR',
            'language': 'fr', 'date_format': 'DD/MM/YYYY', 'time_format': '24H', 'decimal_places': 2,
            'decimal_separator': ',', 'thousands_separator': ' ', 'currency_display': 'CODE',
            'reporting_period': 'WEEK', 'week_start': 6, 'operational_defaults': {'order_status': 'PENDING'},
            'features': {'calling': False}, 'metadata': {'region': 'EU'}})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(self.client.get(self.base+'profile/').data['settings']['currency'], 'EUR')
        self.assertEqual(self.client.get(self.base+'profile/').data['settings']['timezone'], 'Europe/Paris')
        overview = self.client.get(f'/api/businesses/{self.business.pk}/overview/configuration/').data
        self.assertEqual(overview['period'], 'WEEK')
        self.assertEqual(overview['week_start'], 6)

    def test_invalid_settings_are_atomic_and_do_not_create_history(self, _):
        bodies = [('profile', {'timezone': 'Invalid/Zone'}), ('profile', {'currency': 'money'}),
            ('profile', {'contact': {'email': 'not-an-email'}}), ('profile', {'metadata': {'access_token': 'private'}}),
            ('general', {'decimal_places': -1}), ('general', {'week_start': 8}),
            ('general', {'features': {'grant_superuser': True}}), ('general', {'decimal_separator': ',', 'thousands_separator': ','}),
            ('ai', {'guardrails': {'require_evidence': False}}), ('ai', {'execution': {'approval_required': False}}),
            ('knowledge', {'chunk_size': 100, 'chunk_overlap': 100}), ('knowledge', {'hybrid': {'vector_weight': 0.8, 'keyword_weight': 0.8}})]
        for route, body in bodies:
            with self.subTest(route=route, body=body):
                self.assertEqual(self.put(route, body).status_code, 400)
        self.assertEqual(ConfigurationRevision.objects.count(), 0)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, 'Shop')

    def test_monitoring_uses_existing_records_and_legacy_endpoint(self, _):
        result = self.put('monitoring', {'period': 'ROLLING_7D', 'comparison_mode': 'TARGET',
            'kpis': [{'key': 'delivery_failure_rate', 'direction': 'LOWER', 'target_value': '9',
                      'warning': '10', 'critical': '20', 'warning_severity': 'HIGH'}]})
        self.assertEqual(result.status_code, 200, result.data)
        legacy = self.client.get(f'/api/businesses/{self.business.pk}/overview/configuration/').data
        self.assertEqual(legacy['version'], result.data['version'])
        self.assertEqual(legacy['period'], 'ROLLING_7D')
        self.assertEqual(MonitoringConfiguration.objects.count(), 1)
        self.assertFalse(ConfigurationRecord.objects.filter(kind='MONITORING').exists())

    def test_ai_settings_are_restrictive_and_return_effective_guardrails(self, _):
        response = self.put('ai', {'enabled': True, 'provider': 'mock', 'models': {'business_assistant': 'mock-business'},
            'features': {'business_assistant': True, 'customer_support': True, 'recommendations': False},
            'context_categories': ['profile', 'facts', 'approved_policies'], 'response': {'language': 'bn', 'detail': 'DETAILED'},
            'confidence_threshold': '0.8', 'escalation': {'on_low_confidence': True, 'topics': ['refund']},
            'allowed_actions': ['PROPOSE_COURIER_CHANGE'], 'execution': {'approval_required': True, 'disabled_actions': []},
            'parameters': {'temperature': '0.2', 'max_output_tokens': 1000}})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['settings']['guardrails']['external_execution_requires_approval'])
        self.assertFalse(response.data['settings']['guardrails']['ai_may_create_verified_facts'])
        self.assertEqual(self.put('ai', {'confidence_threshold': '0.1'}).status_code, 400)
        self.assertEqual(self.put('ai', {'models': {'business_assistant': 'unregistered-model'}}).status_code, 400)

    def test_knowledge_retrieval_configuration_is_validated(self, _):
        result = self.put('knowledge', {'knowledge_types': ['POLICY', 'PRODUCT', 'SUPPORT'],
            'ingestion': {'allowed_types': ['MANUAL', 'UPLOAD'], 'max_document_bytes': 1000000},
            'chunk_size': 500, 'chunk_overlap': 50, 'embedding_model': 'mock-embedding',
            'vector': {'enabled': True, 'limit': 8, 'minimum_similarity': '0.7'},
            'keyword': {'enabled': True, 'limit': 8}, 'hybrid': {'enabled': True, 'vector_weight': '0.6', 'keyword_weight': '0.4'},
            'retrieval_limit': 10, 'workflow_scopes': {'customer_support': ['POLICY', 'SUPPORT']}, 'include_archived_for_history': True})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['settings']['chunk_size'], 500)

    def test_ai_workflow_preferences_can_only_narrow_business_permissions(self, _):
        from app.configuration.selectors import ai_configuration
        result = self.put('ai', {'enabled': True, 'features': {'customer_support': True},
            'models': {'customer_support': 'mock-support'}, 'context_categories': ['profile', 'facts', 'approved_policies'],
            'allowed_actions': ['CREATE_SUPPORT_DRAFT'], 'workflows': {'customer_support': {
                'enabled': True, 'context_categories': ['approved_policies'], 'confidence_threshold': '0.9',
                'allowed_actions': ['CREATE_SUPPORT_DRAFT'], 'response': {'language': 'bn', 'detail': 'BRIEF'}}}})
        self.assertEqual(result.status_code, 200, result.data)
        effective = ai_configuration(self.business.pk, workflow='customer_support')
        self.assertEqual(effective['effective_context_categories'], ['approved_policies'])
        self.assertEqual(effective['confidence_threshold'], '0.9000')
        self.assertEqual(effective['response']['language'], 'bn')
        self.assertTrue(effective['workflow_enabled'])
        invalid = self.put('ai', {'workflows': {'customer_support': {'context_categories': ['graph']}}})
        self.assertEqual(invalid.status_code, 400)
