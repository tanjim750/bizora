from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase

from app.configuration.selectors import effective_policies, effective_rules, evaluate_rule
from app.models import BusinessFact, BusinessIssue, ConfigurationRevision, Product
from app.tests.configuration_helpers import setup_configuration
from app.tests.observability_helpers import NOW


@patch('app.configuration.views.timezone.now', return_value=NOW)
class RulesAndPoliciesTests(TestCase):
    def setUp(self):
        setup_configuration(self)

    def rule(self, key='high_delivery_failure', **changes):
        body = {'key': key, 'status': 'ACTIVE', 'category': 'DELIVERY', 'priority': 10,
            'conditions': {'all': [{'field': 'delivery_failure_rate', 'operator': 'gt', 'value': '15'}]},
            'sample_metric': 'shipment_count', 'min_samples': 20, 'window_days': 30,
            'scope': {'courier': 'Courier X', 'region': 'Gazipur'},
            'outcome': {'type': 'ALERT', 'code': 'HIGH_DELIVERY_FAILURE', 'severity': 'HIGH'}, **changes}
        return self.client.post(self.base+'rules/', body, format='json')

    def policy(self, key='returns', **changes):
        return self.client.post(self.base+'policies/', {'key': key, 'status': 'ACTIVE', 'category': 'RETURN',
            'title': 'Returns', 'terms': 'Unused products may be returned.', 'ai_available': True,
            'parameters': {'window_days': 7, 'eligibility': ['UNUSED'], 'procedure': 'Contact support'}, **changes}, format='json')

    def test_rule_evaluation_is_deterministic_scoped_and_does_not_create_findings(self, _):
        response = self.rule()
        self.assertEqual(response.status_code, 201, response.data)
        rules = effective_rules(self.business.pk, category='DELIVERY', scope={'courier': 'Courier X', 'region': 'Gazipur'}, at=NOW)
        self.assertEqual(len(rules), 1)
        self.assertEqual(evaluate_rule(rules[0], {'delivery_failure_rate': '17', 'shipment_count': 25})['status'], 'MATCH')
        self.assertEqual(evaluate_rule(rules[0], {'delivery_failure_rate': '17', 'shipment_count': 10})['status'], 'INSUFFICIENT_SAMPLE')
        self.assertEqual(evaluate_rule(rules[0], {})['status'], 'UNKNOWN')
        self.assertEqual(effective_rules(self.business.pk, category='DELIVERY', scope={'region': 'Dhaka'}, at=NOW), [])
        self.assertEqual(effective_rules(self.other_business.pk, category='DELIVERY', scope={}, at=NOW), [])
        self.assertFalse(BusinessIssue.objects.exists())
        self.assertFalse(BusinessFact.objects.exists())
        self.assertIn(':v1', rules[0]['rule_reference'])

    def test_disabled_rule_does_not_resurrect_old_active_version(self, _):
        self.rule(scope={})
        response = self.client.patch(self.base+'rules/high_delivery_failure/', {'version': 1, 'status': 'DISABLED'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(effective_rules(self.business.pk, category='DELIVERY', scope={}, at=NOW), [])
        self.assertEqual(ConfigurationRevision.objects.count(), 2)

    def test_rules_validate_dsl_thresholds_scope_and_unknown_fields(self, _):
        for changes in ({'conditions': {'eval': 'delete_all()'}}, {'conditions': {'all': []}},
                        {'conditions': {'all': [{'field': 'revenue', 'operator': 'execute', 'value': '1'}]}},
                        {'min_samples': 0}, {'scope': {'product_id': 999999}}, {'window_days': -1}):
            self.assertEqual(self.rule(**changes).status_code, 400)
        self.assertFalse(ConfigurationRevision.objects.exists())

    def test_policy_active_draft_scheduled_expiry_and_history(self, _):
        result = self.policy()
        self.assertEqual(result.status_code, 201, result.data)
        update = self.client.patch(self.base+'policies/returns/', {'version': 1, 'status': 'DRAFT',
            'parameters': {'window_days': 14}}, format='json')
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(effective_policies(self.business.pk, scope={}, at=NOW)[0]['settings']['parameters']['window_days'], 7)
        scheduled = self.client.patch(self.base+'policies/returns/', {'version': 2, 'status': 'ACTIVE',
            'valid_from': (NOW+timedelta(days=1)).isoformat(), 'valid_to': (NOW+timedelta(days=2)).isoformat()}, format='json')
        self.assertEqual(scheduled.status_code, 200, scheduled.data)
        self.assertEqual(effective_policies(self.business.pk, scope={}, at=NOW)[0]['version'], 1)
        self.assertEqual(effective_policies(self.business.pk, scope={}, at=NOW+timedelta(days=1))[0]['version'], 3)
        self.assertEqual(effective_policies(self.business.pk, scope={}, at=NOW+timedelta(days=3)), [])
        history = self.client.get(self.base+'policies/returns/history/').data
        self.assertEqual(history['count'], 3)

    def test_policy_scope_and_ai_availability_are_enforced(self, _):
        product = Product.objects.create(business=self.other_business, name='Private', created_at=NOW, updated_at=NOW)
        self.assertEqual(self.policy(scope={'product_id': product.pk}).status_code, 400)
        result = self.policy(scope={'region': 'Gazipur'}, ai_available=False)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(effective_policies(self.business.pk, scope={}, at=NOW), [])
        self.assertEqual(effective_policies(self.business.pk, scope={'region': 'Gazipur'}, at=NOW, for_ai=True), [])
        self.assertEqual(len(effective_policies(self.business.pk, scope={'region': 'Gazipur'}, at=NOW)), 1)

    def test_policy_activation_requires_complete_terms_and_valid_dates(self, _):
        for changes in ({'terms': ''}, {'parameters': {}}, {'parameters': {'window_days': 7, 'procedure': 'Contact'}},
                        {'valid_from': NOW.isoformat(), 'valid_to': NOW.isoformat()}):
            self.assertEqual(self.policy(**changes).status_code, 400)

    def test_incomplete_draft_can_be_saved_but_requires_completion_before_activation(self, _):
        result = self.policy(status='DRAFT', terms='', parameters={})
        self.assertEqual(result.status_code, 201, result.data)
        result = self.client.patch(self.base+'policies/returns/', {'version': 1, 'status': 'ACTIVE'}, format='json')
        self.assertEqual(result.status_code, 400)
        self.assertEqual(effective_policies(self.business.pk, at=NOW), [])

    def test_expired_policy_can_be_archived_without_reactivating_old_versions(self, _):
        self.policy(valid_to=(NOW+timedelta(days=1)).isoformat())
        with patch('app.configuration.views.timezone.now', return_value=NOW+timedelta(days=2)):
            response = self.client.patch(self.base+'policies/returns/', {'status': 'ARCHIVED'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(effective_policies(self.business.pk, at=NOW+timedelta(days=2)), [])
