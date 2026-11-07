from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase

from app.models import (AiAction, AiRecommendation, Call, CallEvent, Campaign, CampaignConversion, Conversation,
                        ConversationAssignment, Customer, CustomerTimelineEvent, Order, OrderStatusHistory,
                        Payment, Refund, Shipment, ShipmentEvent, WebsiteEvent, WebsiteSession, WebsiteVisitor)
from app.tests.observability_helpers import NOW
from app.tests.overview_helpers import issue, setup_overview


@patch('app.overview.views.timezone.now', return_value=NOW)
class ActivityTests(TestCase):
    def setUp(self):
        setup_overview(self)
        self.at = NOW-timedelta(minutes=1)

    def test_feed_projects_all_documented_domains_and_filters(self, _):
        times = {'created_at': self.at, 'updated_at': self.at}
        customer = Customer.objects.create(business=self.business, display_name='PRIVATE CUSTOMER', **times)
        CustomerTimelineEvent.objects.create(customer=customer, event_type='REPEAT_PURCHASE', event_at=self.at, created_at=self.at)
        order = Order.objects.create(business=self.business, order_number='O-1', **times)
        OrderStatusHistory.objects.create(order=order, to_status='COMPLETED', changed_at=self.at, created_at=self.at)
        payment = Payment.objects.create(business=self.business, amount='100', paid_at=self.at, status='SUCCESS', **times)
        Refund.objects.create(payment=payment, amount='10', refunded_at=self.at, **times)
        conversation = Conversation.objects.create(business=self.business, channel='MESSENGER', started_at=self.at, **times)
        ConversationAssignment.objects.create(conversation=conversation, assignee_type='USER', assigned_at=self.at, created_at=self.at)
        shipment = Shipment.objects.create(business=self.business, order=order, provider='Courier X', **times)
        ShipmentEvent.objects.create(shipment=shipment, event_type='DELIVERY_FAILED', occurred_at=self.at, created_at=self.at)
        campaign = Campaign.objects.create(business=self.business, name='Campaign A', platform='META', **times)
        CampaignConversion.objects.create(campaign=campaign, conversion_type='PURCHASE', converted_at=self.at, created_at=self.at)
        visitor = WebsiteVisitor.objects.create(business=self.business, visitor_key='PRIVATE', first_seen_at=self.at, **times)
        session = WebsiteSession.objects.create(business=self.business, visitor=visitor, started_at=self.at, **times)
        WebsiteEvent.objects.create(session=session, visitor=visitor, event_type='CHECKOUT_COMPLETED', occurred_at=self.at, created_at=self.at)
        call = Call.objects.create(business=self.business, direction='INBOUND', status='ENDED', caller_number='PRIVATE PHONE', **times)
        CallEvent.objects.create(call=call, event_type='ENDED', event_at=self.at, created_at=self.at)
        issue(self.business)
        rec = AiRecommendation.objects.create(business=self.business, recommendation_type='TEST', title='Try',
            description='Try', generated_at=self.at, **times)
        AiAction.objects.create(business=self.business, ai_recommendation=rec, action_type='TEST', status='APPROVED',
                                approved_at=self.at, **times)
        result = self.client.get(self.base+'activity/', {'page_size': 100})
        self.assertEqual(result.status_code, 200)
        domains = {r['domain'] for r in result.data['results']}
        self.assertEqual(domains, {'sales', 'payments', 'customers', 'support', 'delivery', 'marketing', 'website', 'calling', 'issues', 'ai'})
        self.assertNotIn('PRIVATE PHONE', str(result.data))
        self.assertNotIn('PRIVATE CUSTOMER', str(result.data))
        filtered = self.client.get(self.base+'activity/', {'domain': 'delivery', 'severity': 'HIGH'}).data
        self.assertEqual(len(filtered['results']), 1)
        self.assertEqual(filtered['results'][0]['event'], 'DELIVERY_FAILED')
        by_entity = self.client.get(self.base+'activity/', {'entity_type': 'order', 'entity_id': order.pk}).data
        self.assertTrue(by_entity['results'])
        self.assertTrue(all(r['entity']['id'] == order.pk for r in by_entity['results']))

    def test_feed_is_paginated_stable_and_excludes_foreign_and_future_events(self, _):
        for business, at in [(self.business, self.at)]*6 + [(self.other_business, self.at), (self.business, NOW+timedelta(seconds=1))]:
            Order.objects.create(business=business, created_at=at, updated_at=at)
        first = self.client.get(self.base+'activity/', {'page_size': 2}).data
        second = self.client.get(self.base+'activity/', {'page_size': 2, 'page': 2}).data
        self.assertEqual(first['count'], 6)
        self.assertEqual(len(first['results']), 2)
        self.assertTrue(set(r['id'] for r in first['results']).isdisjoint(r['id'] for r in second['results']))
        self.assertEqual(self.client.get(self.base+'activity/', {'page': 100}).status_code, 404)

    def test_activity_time_filter_uses_half_open_bounds(self, _):
        Order.objects.create(business=self.business, created_at=self.at, updated_at=self.at)
        result = self.client.get(self.base+'activity/', {'from': self.at.isoformat(), 'to': NOW.isoformat()})
        self.assertEqual(result.data['count'], 1)
        result = self.client.get(self.base+'activity/', {'from': (self.at-timedelta(seconds=1)).isoformat(), 'to': self.at.isoformat()})
        self.assertEqual(result.data['count'], 0)
