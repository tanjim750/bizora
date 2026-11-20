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
        self.assertEqual(m.CampaignMetric.objects.filter(campaign__business=business).count(), 120)
        self.assertEqual(m.Conversation.objects.filter(business=business).count(), 40)
        call_command('seed_bangladesh_demo', username=user.username, verbosity=0)
        self.assertEqual(m.Order.objects.filter(business=business).count(), 240)
