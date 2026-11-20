from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from app import models as m


class BangladeshDemoSeedTests(TestCase):
    def test_seed_is_owned_and_repeatable(self):
        user = get_user_model().objects.create_user(username='seed-owner')
        call_command('seed_bangladesh_demo', username=user.username, verbosity=0)
        business = m.Business.objects.get(slug='nokshi-bangladesh-demo')
        self.assertTrue(m.BusinessMembership.objects.filter(business=business, user=user, role='OWNER').exists())
        self.assertEqual(m.Product.objects.filter(business=business).count(), 20)
        self.assertEqual(m.Customer.objects.filter(business=business).count(), 100)
        self.assertEqual(m.Order.objects.filter(business=business).count(), 240)
        self.assertEqual(m.Payment.objects.filter(business=business).count(), 172)
        self.assertEqual(m.Shipment.objects.filter(business=business).count(), 138)
        self.assertEqual(m.ShipmentEvent.objects.filter(shipment__business=business).count(), 138)
        self.assertEqual(m.CustomerTimelineEvent.objects.filter(customer__business=business).count(), 240)
        self.assertGreaterEqual(m.OrderStatusHistory.objects.filter(order__business=business).count(), 240)
        self.assertEqual(m.CampaignMetric.objects.filter(campaign__business=business).count(), 120)
        self.assertEqual(m.Conversation.objects.filter(business=business).count(), 40)
        self.assertEqual(m.Call.objects.filter(business=business).count(), 12)
        self.assertEqual(m.WebsiteVisitor.objects.filter(business=business).count(), 60)
        self.assertEqual(m.WebsiteSession.objects.filter(business=business).count(), 60)
        self.assertEqual(m.WebsiteEvent.objects.filter(session__business=business).count(), 180)
        self.assertEqual(m.CampaignConversion.objects.filter(campaign__business=business).count(), 15)
        self.assertEqual(m.Conversation.objects.filter(business=business, status='RESOLVED', resolved_at__isnull=False).count(), 10)
        call = m.Call.objects.filter(business=business).select_related('conversation').first()
        self.assertEqual(call.customer_id, call.conversation.customer_id)
        self.assertGreater(call.started_at, call.conversation.started_at)
        conversion = m.CampaignConversion.objects.filter(campaign__business=business).select_related('order', 'campaign').first()
        self.assertEqual(conversion.converted_at, conversion.order.ordered_at)
        self.assertLess(conversion.campaign.started_at, conversion.converted_at)
        call_command('seed_bangladesh_demo', username=user.username, verbosity=0)
        self.assertEqual(m.Order.objects.filter(business=business).count(), 240)
        self.assertEqual(m.WebsiteEvent.objects.filter(session__business=business).count(), 180)
        self.assertEqual(m.CustomerTimelineEvent.objects.filter(customer__business=business).count(), 240)
