from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from app.models import (AiRecommendation, AiRecommendationEvidence, BusinessFact, BusinessIssueEvidence,
                        GraphEdge, GraphNode, KnowledgeChunk, KnowledgeDocument,
                        KnowledgeSource, MonitoringConfigurationRevision, Order, SourceFreshness)
from app.tests.observability_helpers import NOW
from app.tests.overview_helpers import START, issue, metric, setup_overview, snapshot


@patch('app.overview.views.timezone.now', return_value=NOW)
class OverviewEdgeTests(TestCase):
    def setUp(self):
        setup_overview(self)

    def configure(self, **changes):
        response = self.client.put(self.base+'configuration/', changes, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_incomplete_source_cannot_make_metric_healthy(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition)
        SourceFreshness.objects.create(business=self.business, connection=self.connection, entity_type='ORDER',
            coverage_at=NOW, received_at=NOW, confirmed_at=NOW, complete=False)
        self.configure(domains=['sales'], kpis=[{'key': definition.key, 'target_min': '10',
            'sources': [{'connection_id': self.connection.pk, 'entity_type': 'ORDER'}]}])
        self.assertEqual(self.client.get(self.base+'health/').data['status'], 'UNKNOWN')
        card = self.client.get(self.base+'kpis/').data['results'][0]
        self.assertEqual(card['sources'][0]['complete'], False)
        self.assertNotEqual(card['status'], 'AVAILABLE')

    def test_hidden_issue_severity_does_not_hide_critical_health(self, _):
        row = issue(self.business, severity='CRITICAL')
        self.configure(issue_severities=['LOW'])
        self.assertEqual(self.client.get(self.base+'issues/').data['count'], 0)
        self.assertEqual(self.client.get(self.base+'health/').data['status'], 'CRITICAL')
        self.assertEqual(self.client.get(self.base+'health/').data['evidence'][0]['issue_id'], row.pk)

    def test_healthy_requires_explicit_rules_and_all_monitored_domains_have_evidence(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition)
        self.configure(domains=['sales'], kpis=[{'key': definition.key, 'target_min': '50', 'target_max': '150'}])
        self.assertEqual(self.client.get(self.base+'health/').data['status'], 'HEALTHY')
        self.configure(domains=['sales', 'support'])
        self.assertEqual(self.client.get(self.base+'health/').data['status'], 'UNKNOWN')

    def test_configuration_revision_keeps_prior_policy(self, _):
        self.configure(period='WEEK')
        self.configure(period='MONTH', version=1)
        revisions = list(MonitoringConfigurationRevision.objects.order_by('version').values_list('version', 'settings__period'))
        self.assertEqual(revisions, [(1, 'WEEK'), (2, 'MONTH')])

    def test_dimension_trends_can_be_compared_without_mixing_dimensions(self, _):
        definition = metric(self.business)
        for dimension, value in [('Gazipur', '20'), ('Dhaka', '100')]:
            snapshot(self.business, definition, value, dimension_type='region', dimension_value=dimension)
        response = self.client.get(self.base+'trends/', {'metric': definition.key, 'dimension_type': 'region', 'dimension_value': 'Gazipur'})
        self.assertEqual([p['value'] for p in response.data['results'][0]['points']], ['20.000000'])

    def test_mismatched_or_overlapping_trend_windows_cannot_imply_growth(self, _):
        definition = metric(self.business)
        snapshot(self.business, definition, '10', start=START-timedelta(days=2), end=START)
        snapshot(self.business, definition, '20')
        result = self.client.get(self.base+'trends/', {'metric': definition.key}).data['results'][0]
        self.assertEqual(result['comparison']['direction'], 'UNKNOWN')

    def test_invalid_or_foreign_nested_graph_and_memory_evidence_are_hidden(self, _):
        times = {'created_at': NOW, 'updated_at': NOW}
        local_order = Order.objects.create(business=self.business, **times)
        foreign_order = Order.objects.create(business=self.other_business, **times)
        local_node = GraphNode.objects.create(business=self.business, entity_type='order', entity_id=local_order.pk, node_type='ORDER', **times)
        foreign_node = GraphNode.objects.create(business=self.other_business, entity_type='order', entity_id=foreign_order.pk, node_type='ORDER', **times)
        # Historical corrupt rows must bypass today's model-level tenant guard.
        edge = GraphEdge.objects.bulk_create([GraphEdge(business=self.business, source_node=local_node,
            target_node=foreign_node, relationship_type='PRIVATE', **times)])[0]
        source = KnowledgeSource.objects.create(business=self.other_business, name='Private', source_type='FILE', **times)
        document = KnowledgeDocument.objects.bulk_create([KnowledgeDocument(business=self.business,
            knowledge_source=source, title='Private', **times)])[0]
        chunk = KnowledgeChunk.objects.bulk_create([KnowledgeChunk(business=self.business,
            knowledge_document=document, chunk_index=0, content='PRIVATE CONTENT', **times)])[0]
        recommendation = AiRecommendation.objects.create(business=self.business, title='Try', description='Try',
            recommendation_type='TEST', generated_at=NOW, **times)
        for kwargs in ({'graph_edge': edge}, {'knowledge_chunk': chunk}):
            AiRecommendationEvidence.objects.bulk_create([AiRecommendationEvidence(ai_recommendation=recommendation,
                evidence_type='CONTEXT', description='PRIVATE CONTENT', created_at=NOW, **kwargs)])
        result = self.client.get(self.base+f'recommendations/{recommendation.pk}/').data
        self.assertEqual(result['evidence'], [])
        self.assertNotIn('PRIVATE CONTENT', str(result))
        self.assertEqual(self.client.get(self.base+f'evidence/edges/{edge.pk}/').status_code, 404)
        self.assertEqual(self.client.get(self.base+f'evidence/knowledge/{chunk.pk}/').status_code, 404)

    def test_verified_facts_are_drillable_and_invalidated_facts_are_hidden(self, _):
        definition = metric(self.business)
        point = snapshot(self.business, definition)
        fact = BusinessFact.objects.create(business=self.business, fact_type='REVENUE', statement='Revenue increased',
            detected_at=NOW, created_at=NOW, updated_at=NOW)
        row = issue(self.business)
        BusinessIssueEvidence.objects.create(business_issue=row, business_fact=fact, metric_snapshot=point,
            evidence_type='FACT', created_at=NOW)
        result = self.client.get(self.base+f'issues/{row.pk}/').data
        self.assertEqual(len(result['evidence'][0]['references']), 2)
        fact.status = 'INVALIDATED'
        fact.save(update_fields=['status'])
        self.assertEqual(self.client.get(self.base+f'issues/{row.pk}/').data['evidence'], [])
        self.assertEqual(self.client.get(self.base+f'evidence/facts/{fact.pk}/').status_code, 404)

    def test_read_endpoints_never_write_or_call_ai(self, _):
        with CaptureQueriesContext(connection) as queries:
            for route in ['summary', 'kpis', 'trends', 'issues', 'recommendations', 'health', 'activity', 'cross-domain', 'catalog', 'configuration']:
                response = self.client.get(self.base+route+'/')
                self.assertEqual(response.status_code, 200)
        writes = [q['sql'] for q in queries if q['sql'].lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE'}]
        self.assertEqual(writes, [])

    def test_issue_list_entity_lookups_do_not_grow_per_row(self, _):
        order = Order.objects.create(business=self.business, created_at=NOW, updated_at=NOW)
        issue(self.business, subject_entity_type='order', subject_entity_id=order.pk)
        with CaptureQueriesContext(connection) as first:
            self.client.get(self.base+'issues/')
        for _i in range(15):
            order = Order.objects.create(business=self.business, created_at=NOW, updated_at=NOW)
            issue(self.business, subject_entity_type='order', subject_entity_id=order.pk)
        with CaptureQueriesContext(connection) as larger:
            self.client.get(self.base+'issues/')
        self.assertLessEqual(len(larger), len(first)+2)

    def test_malformed_upstream_metadata_does_not_break_monitoring(self, _):
        issue(self.business, metadata={'trend': ['bad'], 'domains': [{'bad': 1}], 'monitoring_scenarios': [{'bad': 1}]})
        for route in ('issues', 'health', 'cross-domain', 'summary'):
            response = self.client.get(self.base+route+'/')
            self.assertEqual(response.status_code, 200)
