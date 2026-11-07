from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase

from app.models import (AiAction, AiRecommendation, AiRecommendationEvidence, BusinessIssueEvidence,
                        MonitoringConfiguration, Order)
from app.tests.observability_helpers import NOW
from app.tests.overview_helpers import issue, metric, setup_overview, snapshot


@patch('app.overview.views.timezone.now', return_value=NOW)
class OverviewApiTests(TestCase):
    def setUp(self):
        setup_overview(self)

    def rec(self, business=None, **kwargs):
        return AiRecommendation.objects.create(business=business or self.business, title='Try another courier',
            description='Test a smaller allocation', recommendation_type='COURIER_ALLOCATION',
            generated_at=NOW-timedelta(minutes=10), created_at=NOW, updated_at=NOW, **kwargs)

    def test_authentication_and_tenant_permissions_apply_to_every_resource(self, _):
        paths = ['summary/', 'kpis/', 'trends/', 'issues/', 'health/', 'activity/', 'recommendations/',
                 'cross-domain/', 'configuration/']
        for path in paths:
            self.client.force_authenticate(None)
            self.assertIn(self.client.get(self.base+path).status_code, (401, 403))
            self.client.force_authenticate(self.user)
            foreign = f'/api/businesses/{self.other_business.pk}/overview/{path}'
            self.assertEqual(self.client.get(foreign).status_code, 403)

    def test_configuration_requires_manager_is_validated_and_versioned(self, _):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.put(self.base+'configuration/', {}, format='json').status_code, 403)
        self.client.force_authenticate(self.user)
        for body in ({'kpis': [{'key': 'total_revenue', 'direction': 'HIGHER', 'warning': '10', 'critical': '50'}]},
                     {'kpis': [{'key': 'not_registered'}]}, {'domains': ['bad']}, {'unknown': 1},
                     {'kpis': [{'key': 'total_revenue', 'sources': [
                         {'connection_id': self.other_connection.pk, 'entity_type': 'ORDER'}]}]}):
            self.assertEqual(self.client.put(self.base+'configuration/', body, format='json').status_code, 400)
        result = self.client.put(self.base+'configuration/', {'kpis': [
            {'key': 'total_revenue', 'direction': 'HIGHER', 'target_min': '100', 'goal': 'Sustainable revenue'}]}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['version'], 1)
        self.assertEqual(MonitoringConfiguration.objects.get().updated_by_id, self.user.pk)
        self.assertEqual(self.client.put(self.base+'configuration/', {'version': 0}, format='json').status_code, 409)
        self.assertEqual(self.client.put(self.base+'configuration/', {'version': 1, 'period': 'WEEK'},
                                        format='json').data['version'], 2)

    def test_issues_are_ranked_and_historical_lifecycle_is_available(self, _):
        high = issue(self.business)
        critical = issue(self.business, severity='CRITICAL', title='Critical')
        resolved = issue(self.business, status='RESOLVED', resolved_at=NOW)
        issue(self.other_business, severity='CRITICAL', title='Other tenant')
        result = self.client.get(self.base+'issues/').data
        self.assertEqual([r['id'] for r in result['results']], [critical.pk, high.pk])
        self.assertEqual(result['results'][0]['confidence'], '1.0000')
        history = self.client.get(self.base+'issues/', {'status': 'RESOLVED'}).data
        self.assertEqual([r['id'] for r in history['results']], [resolved.pk])
        self.assertEqual(self.client.post(self.base+f'issues/{high.pk}/', {}).status_code, 405)

    def test_foreign_evidence_and_actions_are_not_exposed(self, _):
        row = issue(self.business)
        foreign = metric(self.other_business)
        foreign_snapshot = snapshot(self.other_business, foreign)
        BusinessIssueEvidence.objects.create(business_issue=row, metric_snapshot=foreign_snapshot,
            evidence_type='METRIC', description='FOREIGN SECRET', created_at=NOW)
        recommendation = self.rec(business_issue=row)
        AiRecommendationEvidence.objects.create(ai_recommendation=recommendation, metric_snapshot=foreign_snapshot,
            evidence_type='METRIC', description='FOREIGN SECRET', created_at=NOW)
        AiAction.objects.create(business=self.other_business, ai_recommendation=recommendation,
            action_type='PRIVATE', action_payload={'secret': 'PRIVATE'}, created_at=NOW, updated_at=NOW)
        for path in [f'issues/{row.pk}/', f'recommendations/{recommendation.pk}/']:
            response = self.client.get(self.base+path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('FOREIGN SECRET', str(response.data))
            self.assertNotIn('PRIVATE', str(response.data))
            self.assertEqual(response.data['evidence'], [])

    def test_recommendations_include_evidence_action_preview_goals_and_history(self, _):
        row = issue(self.business)
        rec = self.rec(business_issue=row, priority='HIGH', metadata={'goals': ['Reduce delivery loss']})
        old = self.rec(status='REJECTED')
        self.rec(expires_at=NOW-timedelta(seconds=1))
        AiAction.objects.create(business=self.business, ai_recommendation=rec, action_type='ALLOCATE_COURIER',
            action_payload={'allocation': '10%', 'api_token': 'secret-value'}, status='APPROVED',
            approved_at=NOW, created_at=NOW, updated_at=NOW)
        result = self.client.get(self.base+'recommendations/').data
        self.assertEqual([r['id'] for r in result['results']], [rec.pk])
        detail = self.client.get(self.base+f'recommendations/{rec.pk}/').data
        self.assertEqual(detail['goals'], ['Reduce delivery loss'])
        self.assertEqual(detail['actions'][0]['status'], 'APPROVED')
        self.assertNotIn('secret-value', str(detail))
        self.assertEqual(self.client.get(self.base+'recommendations/', {'status': 'REJECTED'}).data['results'][0]['id'], old.pk)

    def test_health_is_explainable_and_separate_from_integration_reliability(self, _):
        row = issue(self.business, severity='CRITICAL')
        result = self.client.get(self.base+'health/').data
        self.assertEqual(result['status'], 'CRITICAL')
        self.assertEqual(result['domains']['delivery']['evidence'][0]['issue_id'], row.pk)
        self.assertIn('reliability', result)
        self.assertEqual(result['trend'], 'DECLINING')

    def test_health_targets_and_lower_is_better_thresholds(self, _):
        definition = metric(self.business, 'delivery_failure_rate', 'DELIVERY')
        snapshot(self.business, definition, '20')
        self.client.put(self.base+'configuration/', {'kpis': [{'key': definition.key, 'direction': 'LOWER',
            'warning': '10', 'critical': '25', 'target_max': '9', 'goal': 'Delivery success'}]}, format='json')
        result = self.client.get(self.base+'health/').data
        self.assertEqual(result['status'], 'WARNING')
        evidence = result['domains']['delivery']['evidence'][0]
        self.assertEqual(evidence['goal'], 'Delivery success')
        self.assertEqual(evidence['status'], 'WARNING')

    def test_entity_drilldown_is_scoped_and_does_not_dump_private_fields(self, _):
        order = Order.objects.create(business=self.business, order_number='ORD-1', source_metadata={'token': 'secret'},
                                     created_at=NOW, updated_at=NOW)
        foreign = Order.objects.create(business=self.other_business, created_at=NOW, updated_at=NOW)
        result = self.client.get(self.base+f'entities/order/{order.pk}/')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['label'], 'ORD-1')
        self.assertNotIn('source_metadata', result.data)
        self.assertEqual(self.client.get(self.base+f'entities/order/{foreign.pk}/').status_code, 404)

    def test_summary_priority_starts_with_critical_issues(self, _):
        critical = issue(self.business, severity='CRITICAL')
        self.rec(priority='HIGH')
        result = self.client.get(self.base+'summary/').data
        self.assertEqual(result['attention'][0]['kind'], 'ISSUE')
        self.assertEqual(result['attention'][0]['id'], critical.pk)
        self.assertEqual(result['business_status'], 'REQUIRES_ATTENTION')

    def test_expired_recommendations_are_available_in_historical_feed(self, _):
        expired = self.rec(expires_at=NOW-timedelta(seconds=1))
        result = self.client.get(self.base+'recommendations/', {'status': 'EXPIRED'})
        self.assertEqual([r['id'] for r in result.data['results']], [expired.pk])
        self.assertEqual(result.data['results'][0]['effective_status'], 'EXPIRED')

    def test_evidence_and_action_status_summaries_are_in_the_feed(self, _):
        definition = metric(self.business)
        point = snapshot(self.business, definition)
        row = issue(self.business)
        BusinessIssueEvidence.objects.create(business_issue=row, metric_snapshot=point, evidence_type='METRIC', created_at=NOW)
        rec = self.rec(business_issue=row)
        AiRecommendationEvidence.objects.create(ai_recommendation=rec, metric_snapshot=point, evidence_type='METRIC', created_at=NOW)
        AiAction.objects.create(business=self.business, ai_recommendation=rec, action_type='TEST', status='UNDER_REVIEW', created_at=NOW, updated_at=NOW)
        self.assertTrue(self.client.get(self.base+'issues/').data['results'][0]['evidence_summary'])
        result = self.client.get(self.base+'recommendations/').data['results'][0]
        self.assertTrue(result['evidence_summary'])
        self.assertEqual(result['action_summary'][0]['status'], 'UNDER_REVIEW')
