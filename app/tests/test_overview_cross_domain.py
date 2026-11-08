from unittest.mock import patch

from django.test import TestCase

from app.models import (BusinessIssueEvidence, BusinessRelationship, Campaign, Conversation, Customer, Order, Product,
                        Shipment, WebsiteSession, WebsiteVisitor)
from app.overview.catalog import CROSS_DOMAIN
from app.tests.observability_helpers import NOW
from app.tests.overview_helpers import issue, setup_overview


@patch('app.overview.views.timezone.now', return_value=NOW)
class CrossDomainTests(TestCase):
    def setUp(self):
        setup_overview(self)

    def test_each_scenario_surfaces_only_existing_issue_with_verified_relationship_evidence(self, _):
        campaign = Campaign.objects.create(business=self.business, name='Campaign A', platform='META', created_at=NOW, updated_at=NOW)
        order = Order.objects.create(business=self.business, created_at=NOW, updated_at=NOW)
        shipment = Shipment.objects.create(business=self.business, order=order, provider='Courier X', created_at=NOW, updated_at=NOW)
        relationship = BusinessRelationship.objects.create(business=self.business, source_entity_type='CAMPAIGN',
            source_entity_id=campaign.pk, target_entity_type='SHIPMENT', target_entity_id=shipment.pk,
            relationship_type='ATTRIBUTED_DELIVERY', rule_key='attribution.v1', created_at=NOW, updated_at=NOW)
        row = issue(self.business, metadata={'domains': ['marketing', 'delivery'], 'monitoring_scenarios': ['marketing_delivery']})
        BusinessIssueEvidence.objects.create(business_issue=row, relationship=relationship, evidence_type='RELATIONSHIP', created_at=NOW)
        issue(self.business, issue_type='OTHER_SCENARIOS', metadata={'monitoring_scenarios': list(CROSS_DOMAIN)})
        result = self.client.get(self.base+'cross-domain/').data
        self.assertEqual(len(result['results']), 9)
        scenario = next(r for r in result['results'] if r['key'] == 'marketing_delivery')
        self.assertEqual(scenario['status'], 'REQUIRES_ATTENTION')
        self.assertEqual([r['id'] for r in scenario['issues']], [row.pk])
        self.assertTrue(all(r['status'] == 'NO_VERIFIED_FINDING' for r in result['results'] if r['key'] != 'marketing_delivery'))

    def test_foreign_relationship_endpoint_cannot_establish_cross_domain_signal(self, _):
        local = Order.objects.create(business=self.business, created_at=NOW, updated_at=NOW)
        foreign = Campaign.objects.create(business=self.other_business, name='Other', platform='META', created_at=NOW, updated_at=NOW)
        relationship = BusinessRelationship.objects.create(business=self.business, source_entity_type='campaign',
            source_entity_id=foreign.pk, target_entity_type='order', target_entity_id=local.pk,
            relationship_type='ATTRIBUTED_TO', created_at=NOW, updated_at=NOW)
        row = issue(self.business, metadata={'monitoring_scenarios': ['marketing_revenue']})
        BusinessIssueEvidence.objects.create(business_issue=row, relationship=relationship, evidence_type='RELATIONSHIP', created_at=NOW)
        result = self.client.get(self.base+'cross-domain/').data['results'][0]
        self.assertEqual(result['status'], 'NO_VERIFIED_FINDING')
        self.assertEqual(self.client.get(self.base+f'evidence/relationships/{relationship.pk}/').status_code, 404)

    def test_all_nine_scenarios_have_a_grounded_projection_path(self, _):
        times = {'created_at': NOW, 'updated_at': NOW}
        order = Order.objects.create(business=self.business, **times)
        visitor = WebsiteVisitor.objects.create(business=self.business, visitor_key='test', first_seen_at=NOW, **times)
        entities = {
            'order': order,
            'customer': Customer.objects.create(business=self.business, **times),
            'product': Product.objects.create(business=self.business, name='Coffee', **times),
            'campaign': Campaign.objects.create(business=self.business, name='Campaign', platform='META', **times),
            'shipment': Shipment.objects.create(business=self.business, order=order, provider='Courier X', **times),
            'conversation': Conversation.objects.create(business=self.business, channel='CHAT', started_at=NOW, **times),
            'website_session': WebsiteSession.objects.create(business=self.business, visitor=visitor, started_at=NOW, **times),
        }
        paths = {'marketing_revenue': ('campaign', 'order'), 'marketing_delivery': ('campaign', 'shipment'),
            'website_sales': ('website_session', 'order'), 'product_support': ('product', 'conversation'),
            'product_delivery': ('product', 'shipment'), 'customer_retention': ('customer', 'order'),
            'support_customer_outcome': ('conversation', 'customer'), 'courier_revenue': ('shipment', 'order'),
            'campaign_customer_quality': ('campaign', 'customer')}
        for key, (source, target) in paths.items():
            row = issue(self.business, issue_type=key.upper(), metadata={'monitoring_scenarios': [key]})
            relation = BusinessRelationship.objects.create(business=self.business, source_entity_type=source,
                source_entity_id=entities[source].pk, target_entity_type=target, target_entity_id=entities[target].pk,
                relationship_type=key.upper(), **times)
            BusinessIssueEvidence.objects.create(business_issue=row, relationship=relation, evidence_type='RELATIONSHIP', created_at=NOW)
        result = self.client.get(self.base+'cross-domain/').data['results']
        self.assertEqual({r['key'] for r in result}, set(CROSS_DOMAIN))
        self.assertTrue(all(len(r['issues']) == 1 and r['status'] == 'REQUIRES_ATTENTION' for r in result))
