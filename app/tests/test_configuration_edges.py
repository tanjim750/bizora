from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from app.configuration.selectors import action_policy, ai_configuration, effective_policies
from app.models import ConfigurationEvent, ConfigurationRecord, ConfigurationRevision, IntegrationConnection, KnowledgeSource
from app.tests.configuration_helpers import setup_configuration
from app.tests.observability_helpers import NOW


@patch('app.configuration.views.timezone.now', return_value=NOW)
class ConfigurationEdgeTests(TestCase):
    def setUp(self):
        setup_configuration(self)

    def test_legacy_provider_secrets_never_appear_in_setup_reads(self, _):
        self.connection.config = {'provider_settings': {'api_key': 'private-key-value'},
            'mock': {'password': 'private-password-value'}, 'sync': {'mode': 'MANUAL', 'password': 'private-sync-value'}}
        self.connection.save(update_fields=['config'])
        response = self.client.get(self.base+f'connections/{self.connection.pk}/')
        self.assertEqual(response.status_code, 200)
        for secret in ('private-key-value', 'private-password-value', 'private-sync-value'):
            self.assertNotIn(secret, str(response.data))

    def test_platform_confidence_floor_remains_effective_after_settings_change(self, _):
        self.client.put(self.base+'ai/', {'enabled': True, 'confidence_threshold': '0.7',
            'allowed_actions': ['PROPOSE_COURIER_CHANGE']}, format='json')
        with override_settings(BIZORA_AI_MIN_CONFIDENCE='0.9'):
            self.assertEqual(ai_configuration(self.business.pk)['confidence_threshold'], '0.9')
        self.assertTrue(action_policy(self.business.pk, 'PROPOSE_COURIER_CHANGE')['may_propose'])
        self.client.put(self.base+'ai/', {'execution': {'disabled_actions': ['PROPOSE_COURIER_CHANGE']}}, format='json')
        self.assertFalse(action_policy(self.business.pk, 'PROPOSE_COURIER_CHANGE')['may_propose'])

    def test_sources_require_enabled_ingestion_types_before_approval(self, _):
        response = self.client.post(self.base+'sources/', {'name': 'Website', 'source_type': 'WEBSITE',
            'source_reference': 'https://example.com/knowledge', 'knowledge_type': 'INTERNAL', 'status': 'ACTIVE'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(KnowledgeSource.objects.exists())

    def test_each_policy_category_has_a_validated_activation_path(self, _):
        examples = {
            'DELIVERY': {'coverage_regions': ['Dhaka'], 'estimated_days': 3, 'charge': '70', 'cod_enabled': True},
            'RETURN': {'window_days': 7, 'eligibility': ['UNUSED'], 'procedure': 'Contact support'},
            'REFUND': {'window_days': 7, 'methods': ['ORIGINAL_PAYMENT'], 'approval_required': True,
                       'eligibility': ['RETURN_ACCEPTED'], 'procedure': 'Contact support'},
            'CANCELLATION': {'allowed_statuses': ['PENDING'], 'cutoff_hours': 24, 'procedure': 'Contact support'},
            'SUPPORT': {'response_time_seconds': 3600, 'escalation_conditions': ['COMPLAINT'], 'instructions': 'Escalate to manager'},
            'PRODUCT': {'constraints': ['No opened food returns'], 'instructions': 'Apply per product category'},
        }
        for category, parameters in examples.items():
            response = self.client.post(self.base+'policies/', {'key': category.lower(), 'status': 'ACTIVE',
                'category': category, 'title': category.title(), 'terms': 'Approved business policy', 'parameters': parameters}, format='json')
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(effective_policies(self.business.pk, at=NOW)), 6)

    def test_history_and_events_are_read_only_and_isolated(self, _):
        self.client.put(self.base+'profile/', {'description': 'Configured'}, format='json')
        self.assertEqual(self.client.patch(self.base+'profile/history/', {'settings': {}}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(self.base+'profile/').status_code, 405)
        self.assertEqual(self.client.get(f'/api/businesses/{self.other_business.pk}/configuration/changes/').status_code, 403)
        self.assertEqual(ConfigurationRevision.objects.count(), 1)
        self.assertEqual(ConfigurationEvent.objects.count(), 1)

    def test_connection_list_queries_are_bounded_by_page_not_row_count(self, _):
        with CaptureQueriesContext(connection) as first:
            self.client.get(self.base+'connections/')
        for _i in range(15):
            IntegrationConnection.objects.create(business=self.business, integration_source=self.source, created_at=NOW, updated_at=NOW)
        with CaptureQueriesContext(connection) as larger:
            self.client.get(self.base+'connections/')
        self.assertLessEqual(len(larger), len(first)+2)

    def test_bad_envelopes_filters_and_credentials_are_rejected_without_writes(self, _):
        for body in ([], {'version': True}, {'status': 'DISABLED'}, {'valid_from': NOW.isoformat()}, {'not_a_setting': True}):
            self.assertEqual(self.client.put(self.base+'profile/', body, format='json').status_code, 400)
        for params in ({'page_size': 1000}, {'page': 0}, {'status': 'unknown'}, {'ignored': 'x'}):
            self.assertEqual(self.client.get(self.base+'rules/', params).status_code, 400)
        self.assertFalse(ConfigurationRecord.objects.exists())

    def test_effective_api_uses_scope_and_current_platform_limits(self, _):
        self.client.post(self.base+'policies/', {'key': 'regional_returns', 'status': 'ACTIVE', 'category': 'RETURN',
            'title': 'Regional return policy', 'terms': 'Approved terms', 'scope': {'region': 'Gazipur'},
            'parameters': {'window_days': 7, 'eligibility': ['UNUSED'], 'procedure': 'Contact support'}}, format='json')
        with override_settings(BIZORA_AI_MIN_CONFIDENCE='0.9'):
            result = self.client.get(self.base+'effective/', {'region': 'Gazipur', 'workflow': 'customer_support'})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(len(result.data['policies']), 1)
        self.assertEqual(result.data['sections']['ai']['settings']['confidence_threshold'], '0.9')
        self.assertEqual(self.client.get(self.base+'effective/', {'workflow': 'unknown'}).status_code, 400)
