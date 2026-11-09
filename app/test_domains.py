"""Domain behaviour and API security tests run only on Django's isolated test DB."""
from datetime import timedelta
from decimal import Decimal
import itertools
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, SimpleTestCase, TransactionTestCase
from django.db import connection, close_old_connections
from unittest import skipUnless
from django.utils import timezone
from rest_framework.test import APIClient
from app import models as m
from app.domains import data, identity, operations, projections
from app.domains.common import DomainError, create, money, normalize_contact


class NormalizationTests(SimpleTestCase):
    def test_bangladesh_phone_and_international_forms(self):
        for value in ['01712345678', '+8801712345678', '008801712345678', '+880 (1712) 345-678']:
            with self.subTest(value=value):
                self.assertEqual(normalize_contact('PHONE', value), '+8801712345678')

    def test_email(self):
        self.assertEqual(normalize_contact('EMAIL', '  Buyer@Example.COM '), 'buyer@example.com')

    def test_invalid_contacts(self):
        for value in ['', None, '0171', 'not-a-number', '+0000000000']:
            with self.subTest(value=value), self.assertRaises(DomainError):
                normalize_contact('PHONE', value)
        with self.assertRaises(DomainError):
            normalize_contact('EMAIL', 'bad@')

    def test_external_identifiers_remain_case_sensitive(self):
        self.assertEqual(normalize_contact('PSID', 'AbC'), 'AbC')

    def test_money_is_decimal(self):
        self.assertEqual(money('0.10') + money('0.20'), Decimal('0.30'))

    def test_invalid_money(self):
        for value in ['NaN', 'Infinity', '-1', '1.001', None, '10000000000000000']:
            with self.subTest(value=value), self.assertRaises(DomainError):
                money(value)


class DomainFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.manager = User.objects.create_user('manager', password='test-password-123')
        cls.operator = User.objects.create_user('operator', password='test-password-123')
        cls.viewer = User.objects.create_user('viewer', password='test-password-123')
        cls.stranger = User.objects.create_user('stranger', password='test-password-123')
        cls.business = create(m.Business, name='Demo', slug='demo')
        cls.other = create(m.Business, name='Other', slug='other')
        for user, role in [(cls.manager, 'MANAGER'), (cls.operator, 'OPERATOR'), (cls.viewer, 'VIEWER')]:
            m.BusinessMembership.objects.create(business=cls.business, user=user, role=role)
        m.BusinessMembership.objects.create(business=cls.other, user=cls.stranger, role='OWNER')
        source = create(m.IntegrationSource, key='mock-commerce', name='Mock', category='COMMERCE')
        cls.connection = create(m.IntegrationConnection, business=cls.business, integration_source=source)
        cls.other_connection = create(m.IntegrationConnection, business=cls.other, integration_source=source)
        cls.customer = create(m.Customer, business=cls.business, display_name='Customer')
        cls.other_customer = create(m.Customer, business=cls.other, display_name='Private')
        cls.product = create(m.Product, business=cls.business, name='Tea', sku='TEA', price=Decimal('10.00'))

    def setUp(self):
        self.sequence = itertools.count()
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def ingest(self, name, payload, **kwargs):
        return data.ingest(self.business, self.manager, name, payload,
                           key=kwargs.pop('key', 'test-' + str(next(self.sequence))), **kwargs)[0]

    def order(self, **extra):
        return self.ingest('orders', {'external_order_id': 'order-' + str(next(self.sequence)),
            'customer': self.customer.pk, 'items': [{'product': self.product.pk, 'quantity': 2, 'unit_price': '10.00'}], **extra}, connection_id=self.connection.pk)

    def payment(self, order=None, **extra):
        order = order or self.order()
        return self.ingest('payments', {'external_payment_id': 'pay-' + str(next(self.sequence)), 'order': order.pk,
            'customer': self.customer.pk, 'amount': '20.00', 'status': 'PAID', **extra}, connection_id=self.connection.pk)

    def conversation(self):
        return self.ingest('conversations', {'external_conversation_id': 'conv-' + str(next(self.sequence)),
            'channel': 'WHATSAPP', 'customer': self.customer.pk}, connection_id=self.connection.pk)

    def url(self, suffix, business=None):
        return f'/api/businesses/{(business or self.business).pk}/{suffix}'


class CanonicalDataTests(DomainFixture):
    def test_customer_contacts_tags_and_reference(self):
        customer = self.ingest('customers', {'display_name': 'Buyer', 'contacts': [{'contact_type': 'PHONE', 'value': '01712345678', 'is_primary': True}],
            'tags': ['VIP'], 'external_reference': {'external_customer_id': '52'}}, connection_id=self.connection.pk)
        self.assertEqual(customer.customercontact_set.get().normalized_value, '+8801712345678')
        self.assertFalse(customer.customercontact_set.get().is_verified)
        self.assertEqual(customer.customertag_set.get().tag, 'VIP')
        self.assertEqual(customer.customerexternalreference_set.get().external_customer_id, '52')

    def test_invalid_nested_contact_rolls_back_customer_and_receipt(self):
        before = m.Customer.objects.count()
        with self.assertRaises(DomainError):
            self.ingest('customers', {'display_name': 'Invalid', 'contacts': [{'contact_type': 'EMAIL', 'value': 'bad'}]})
        self.assertEqual(m.Customer.objects.count(), before)
        self.assertEqual(m.ProcessingReceipt.objects.count(), 0)

    def test_product_variants_and_external_reference(self):
        obj = self.ingest('products', {'name': 'Coffee', 'price': '15.50', 'variants': [{'name': 'Large', 'sku': 'L', 'attributes': {'size': 'L'}}],
            'external_reference': {'external_product_id': 'p52'}}, connection_id=self.connection.pk)
        self.assertEqual(obj.productvariant_set.get().sku, 'L')
        self.assertEqual(obj.productexternalreference_set.get().external_product_id, 'p52')

    def test_idempotent_retry(self):
        payload = {'name': 'Coffee'}
        one = self.ingest('products', payload, key='same')
        two = self.ingest('products', payload, key='same')
        self.assertEqual(one.pk, two.pk)
        self.assertEqual(m.ProcessingReceipt.objects.filter(key='manual:same').count(), 1)

    def test_key_payload_collision(self):
        self.ingest('products', {'name': 'Coffee'}, key='same')
        with self.assertRaisesMessage(DomainError, 'different input'):
            self.ingest('products', {'name': 'Tea'}, key='same')

    def test_keys_are_connection_scoped(self):
        other = create(m.IntegrationConnection, business=self.business, integration_source=self.connection.integration_source)
        a = self.ingest('products', {'name': 'A'}, key='same', connection_id=self.connection.pk)
        b = self.ingest('products', {'name': 'A'}, key='same', connection_id=other.pk)
        self.assertNotEqual(a.pk, b.pk)

    def test_external_customer_update_preserves_entity(self):
        payload = {'display_name': 'A', 'external_reference': {'external_customer_id': '52'}}
        a = self.ingest('customers', payload, connection_id=self.connection.pk)
        b = self.ingest('customers', {**payload, 'display_name': 'B'}, connection_id=self.connection.pk)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(b.display_name, 'B')

    def test_order_decimal_totals_and_snapshot(self):
        order = self.order(discount_amount='1.25', shipping_amount='2.00', tax_amount='0.25')
        self.assertEqual(order.subtotal, Decimal('20.00'))
        self.assertEqual(order.total_amount, Decimal('21.00'))
        self.product.name = 'Changed'
        self.product.save(update_fields=['name'])
        self.assertEqual(order.orderitem_set.get().product_name, 'Tea')
        self.assertEqual(order.orderstatushistory_set.get().to_status, 'PENDING')

    def test_invalid_item_rolls_back_entire_order(self):
        with self.assertRaises(DomainError):
            self.order(items=[{'product': self.product.pk, 'quantity': 0, 'unit_price': '10'}])
        self.assertEqual(m.Order.objects.count(), 0)
        self.assertEqual(m.OrderItem.objects.count(), 0)
        self.assertEqual(m.OrderStatusHistory.objects.count(), 0)

    def test_item_variant_must_belong_to_product(self):
        other = create(m.Product, business=self.business, name='Other')
        variant = create(m.ProductVariant, product=other, name='Variant')
        with self.assertRaises(DomainError):
            self.order(items=[{'product': self.product.pk, 'product_variant': variant.pk, 'unit_price': '10'}])

    def test_negative_excessive_and_fractional_amounts(self):
        for extra in [{'discount_amount': '21'}, {'shipping_amount': '-1'}, {'tax_amount': '0.001'}]:
            with self.subTest(extra=extra), self.assertRaises(DomainError):
                self.order(**extra)

    def test_transition_and_history(self):
        order = self.order()
        for state in ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']:
            data.transition(self.business, self.operator, 'orders', order.pk, state)
        self.assertEqual(order.orderstatushistory_set.count(), 5)
        self.assertEqual(order.customer.customertimelineevent_set.filter(entity_id=order.pk, entity_type='Order').count(), 5)

    def test_invalid_transition_does_not_change_history(self):
        order = self.order()
        with self.assertRaises(DomainError):
            data.transition(self.business, self.manager, 'orders', order.pk, 'DELIVERED')
        self.assertEqual(order.orderstatushistory_set.count(), 1)

    def test_optimistic_state_guard(self):
        order = self.order()
        with self.assertRaises(DomainError):
            data.transition(self.business, self.manager, 'orders', order.pk, 'CONFIRMED', expected_status='CANCELLED')

    def test_repeated_transition_is_noop(self):
        order = self.order()
        data.transition(self.business, self.manager, 'orders', order.pk, 'CONFIRMED')
        data.transition(self.business, self.manager, 'orders', order.pk, 'CONFIRMED')
        self.assertEqual(order.orderstatushistory_set.count(), 2)

    def test_cross_business_customer_rejected(self):
        with self.assertRaises(DomainError):
            self.order(customer=self.other_customer.pk)

    def test_cross_business_connection_rejected(self):
        with self.assertRaises(DomainError):
            self.ingest('products', {'name': 'A'}, connection_id=self.other_connection.pk)

    def test_partial_and_full_refunds(self):
        payment = self.payment()
        self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r1', 'amount': '5', 'status': 'COMPLETED'})
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'PARTIALLY_REFUNDED')
        self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r2', 'amount': '15', 'status': 'COMPLETED'})
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'REFUNDED')

    def test_pending_refunds_reserve_capacity(self):
        payment = self.payment()
        self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r1', 'amount': '15'})
        with self.assertRaises(DomainError):
            self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r2', 'amount': '6'})
        self.assertEqual(m.Refund.objects.count(), 1)

    def test_failed_refund_releases_capacity(self):
        payment = self.payment()
        refund = self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r1', 'amount': '20'})
        data.transition(self.business, self.manager, 'refunds', refund.pk, 'FAILED')
        self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r2', 'amount': '20', 'status': 'COMPLETED'})
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'REFUNDED')

    def test_refund_requires_paid_payment(self):
        payment = self.payment(status='PENDING')
        with self.assertRaises(DomainError):
            self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r1', 'amount': '1'})

    def test_refund_currency_and_order_must_match(self):
        payment = self.payment()
        for extra in [{'currency': 'USD'}, {'order': self.order().pk}]:
            with self.subTest(extra=extra), self.assertRaises(DomainError):
                self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r1', 'amount': '1', **extra})

    def test_old_product_event_cannot_overwrite(self):
        payload = {'name': 'New', 'external_reference': {'external_product_id': 'p1'}}
        now = timezone.now()
        obj = self.ingest('products', payload, occurred_at=now, connection_id=self.connection.pk)
        with self.assertRaises(DomainError):
            self.ingest('products', {**payload, 'name': 'Old'}, occurred_at=now-timedelta(hours=1), connection_id=self.connection.pk)
        obj.refresh_from_db()
        self.assertEqual(obj.name, 'New')

    def test_message_attachments_delivery_and_notes(self):
        conversation = self.conversation()
        message = self.ingest('messages', {'conversation': conversation.pk, 'external_message_id': 'm1',
            'direction': 'INCOMING', 'sender_type': 'CUSTOMER', 'content': 'Help',
            'attachments': [{'attachment_type': 'IMAGE', 'url': 'https://example.test/image.png'}]}, connection_id=self.connection.pk)
        self.assertEqual(message.messageattachment_set.count(), 1)
        for state in ['SENT', 'DELIVERED']:
            data.transition(self.business, self.operator, 'messages', message.pk, state)
        message.refresh_from_db()
        self.assertIsNotNone(message.delivered_at)
        self.ingest('notes', {'conversation': conversation.pk, 'content': 'Private'})
        self.assertEqual(m.Message.objects.count(), 1)
        self.assertEqual(m.ConversationNote.objects.get().author_id, self.manager.pk)
        conversation.refresh_from_db()
        self.assertIsNotNone(conversation.last_message_at)

    def test_invalid_channel_and_message_type(self):
        with self.assertRaises(DomainError):
            self.ingest('conversations', {'channel': 'UNKNOWN', 'external_conversation_id': 'x'})
        conversation = self.conversation()
        with self.assertRaises(DomainError):
            self.ingest('messages', {'conversation': conversation.pk, 'external_message_id': 'x', 'direction': 'INCOMING', 'sender_type': 'CUSTOMER', 'message_type': 'EXECUTABLE'})

    def test_shipment_lifecycle_and_delivery_events(self):
        obj = self.ingest('shipments', {'order': self.order().pk, 'customer': self.customer.pk, 'external_shipment_id': 's1', 'provider': 'MOCK'})
        for state in ['SUBMITTED', 'PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'FAILED', 'OUT_FOR_DELIVERY', 'DELIVERED']:
            data.transition(self.business, self.operator, 'shipments', obj.pk, state)
        self.assertEqual(obj.shipmentevent_set.count(), 7)

    def test_call_transcript_events_and_callback(self):
        obj = self.ingest('calls', {'external_call_id': 'c1', 'direction': 'INCOMING', 'customer': self.customer.pk, 'order': self.order().pk})
        for state in ['RINGING', 'ANSWERED', 'COMPLETED']:
            data.transition(self.business, self.operator, 'calls', obj.pk, state)
        self.ingest('transcripts', {'call': obj.pk, 'transcript': 'Approved source transcript', 'provider': 'MOCK'})
        callback = self.ingest('callbacks', {'customer': self.customer.pk, 'scheduled_at': (timezone.now()+timedelta(hours=1)).isoformat()})
        self.assertEqual(obj.callevent_set.count(), 3)
        self.assertEqual(obj.calltranscript_set.count(), 1)
        self.assertEqual(callback.status, 'PENDING')

    def test_campaign_hierarchy_metrics_and_conversions(self):
        account = self.ingest('ad-accounts', {'external_account_id': 'a1', 'name': 'Account'}, connection_id=self.connection.pk)
        campaign = self.ingest('campaigns', {'external_campaign_id': 'ca1', 'name': 'Summer', 'platform': 'META', 'ad_account': account.pk}, connection_id=self.connection.pk)
        adset = self.ingest('ad-sets', {'campaign': campaign.pk, 'external_id': 'as1', 'name': 'Set', 'audience': {'region': 'Dhaka'}})
        creative = self.ingest('creatives', {'external_id': 'cr1', 'content': {'title': 'Tea'}})
        self.ingest('ads', {'ad_set': adset.pk, 'creative': creative.pk, 'external_id': 'ad1', 'name': 'Ad'})
        metric = self.ingest('campaign-metrics', {'campaign': campaign.pk, 'metric_date': '2026-10-24', 'spend': '10', 'clicks': 5})
        self.ingest('campaign-metrics', {'campaign': campaign.pk, 'metric_date': '2026-10-24', 'spend': '20', 'clicks': 10})
        self.assertEqual(m.CampaignMetric.objects.count(), 1)
        metric.refresh_from_db()
        self.assertEqual(metric.spend, Decimal('20'))
        conversion = self.ingest('conversions', {'campaign': campaign.pk, 'external_conversion_id': 'co1', 'conversion_type': 'PURCHASE', 'converted_at': timezone.now().isoformat(), 'order': self.order().pk})
        self.assertEqual(conversion.campaign, campaign)
        self.assertEqual(m.CampaignAd.objects.count(), 1)

    def test_unknown_fields_and_missing_identifiers(self):
        for resource, payload in [('products', {'name': 'A', 'business': self.other.pk}), ('payments', {'amount': '1'}), ('products', {'name': 'A', 'price': 'NaN'})]:
            with self.subTest(resource=resource), self.assertRaises(DomainError):
                self.ingest(resource, payload)

    def test_database_active_owner_constraint(self):
        conversation = self.conversation()
        operations.assign(self.business, self.operator, conversation.pk, 'AGENT', self.operator.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            m.ConversationAssignment.objects.create(conversation=conversation, assignee_type='AI', assigned_at=timezone.now(), created_at=timezone.now())

    def test_database_external_order_uniqueness(self):
        order = self.order()
        with self.assertRaises(IntegrityError), transaction.atomic():
            m.Order.objects.create(business=self.business, integration_connection=self.connection, external_order_id=order.external_order_id, created_at=timezone.now(), updated_at=timezone.now())


class IdentityTests(DomainFixture):
    def external(self, kind='EMAIL', value='buyer@example.com', external_id='52', entity_type='CUSTOMER', verified=True, connection=None):
        return identity.register(self.business, self.manager, (connection or self.connection).pk, entity_type, kind, value, external_id=external_id, verified=verified)[0]

    def contact(self, customer=None, value='buyer@example.com', verified=True):
        return create(m.CustomerContact, customer=customer or self.customer, contact_type='EMAIL', value=value, normalized_value=value, is_verified=verified)

    def test_stable_registry(self):
        a = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        b = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(a.canonical_key, f'CUSTOMER-{self.customer.pk:08d}')

    def test_registry_rejects_missing_and_cross_tenant_entity(self):
        for pk in [999999, self.other_customer.pk]:
            with self.subTest(pk=pk), self.assertRaises(DomainError):
                identity.canonical(self.business, self.manager, 'CUSTOMER', pk)

    def test_source_scoped_registration_and_seen_times(self):
        one = self.external()
        other_source = create(m.IntegrationConnection, business=self.business, integration_source=self.connection.integration_source)
        two = self.external(connection=other_source)
        self.assertNotEqual(one.pk, two.pk)
        self.assertEqual(one.pk, self.external().pk)
        self.assertIsNotNone(one.first_seen_at)

    def test_external_id_collision_is_reviewable(self):
        one = self.external()
        again, conflict = identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', 'EMAIL', 'different@example.com', external_id='52')
        self.assertEqual(one.pk, again.pk)
        self.assertEqual(conflict.conflict_type, 'EXTERNAL_ID_COLLISION')
        one.refresh_from_db()
        self.assertEqual(one.normalized_value, 'buyer@example.com')

    def test_exact_verified_contact_resolution(self):
        self.contact()
        ext = self.external(value='BUYER@EXAMPLE.COM')
        link, issue = identity.resolve(self.business, self.manager, ext.pk)
        self.assertIsNone(issue)
        self.assertEqual(link.canonical_identity.entity_id, self.customer.pk)
        self.assertEqual(link.rule_key, 'VERIFIED_EXACT_CONTACT')
        self.assertTrue(m.IdentityHistory.objects.filter(action='LINKED', external_identity=ext).exists())

    def test_unverified_identifier_does_not_match(self):
        self.contact()
        ext = self.external(verified=False)
        self.assertEqual(identity.resolve(self.business, self.manager, ext.pk), (None, None))

    def test_unverified_contact_does_not_match(self):
        self.contact(verified=False)
        self.assertEqual(identity.resolve(self.business, self.manager, self.external().pk), (None, None))

    def test_manual_verification_is_authorized_and_audited(self):
        c = self.contact(verified=False)
        with self.assertRaises(DomainError):
            identity.verify_contact(self.business, self.operator, c.pk, 'Verified by caller')
        identity.verify_contact(self.business, self.manager, c.pk, 'Verified by caller')
        c.refresh_from_db()
        self.assertTrue(c.is_verified)
        self.assertTrue(m.IdentityHistory.objects.filter(action='CONTACT_VERIFIED').exists())

    def test_multiple_contact_matches_do_not_auto_merge(self):
        self.contact()
        customer = create(m.Customer, business=self.business, display_name='Duplicate')
        self.contact(customer)
        ext = self.external()
        link, issue = identity.resolve(self.business, self.manager, ext.pk)
        self.assertIsNone(link)
        self.assertEqual(issue.conflict_type, 'MULTIPLE_MATCHES')
        self.assertEqual(m.IdentityLink.objects.count(), 0)
        self.assertEqual(m.Customer.objects.filter(business=self.business).count(), 2)

    def test_contradictory_source_and_contact(self):
        self.contact()
        other = create(m.Customer, business=self.business, display_name='Other')
        create(m.CustomerExternalReference, customer=other, integration_connection=self.connection, external_customer_id='52')
        _, conflict = identity.resolve(self.business, self.manager, self.external().pk)
        self.assertEqual(conflict.conflict_type, 'CONTRADICTORY_IDENTIFIERS')

    def test_manual_link_unlink_relink_preserves_history(self):
        ext = self.external()
        target = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        first, _ = identity.link(self.business, self.manager, ext.pk, target.pk, 'Documented review')
        second, _ = identity.link(self.business, self.manager, ext.pk, target.pk, 'Repeated review')
        self.assertEqual(first.pk, second.pk)
        identity.unlink(self.business, self.manager, first.pk, 'Incorrect source')
        again, _ = identity.link(self.business, self.manager, ext.pk, target.pk, 'Corrected evidence')
        self.assertEqual(again.pk, first.pk)
        self.assertEqual(m.IdentityHistory.objects.filter(action='LINKED').count(), 2)
        self.assertEqual(m.IdentityHistory.objects.filter(action='UNLINKED').count(), 1)

    def test_conflicting_active_link_cannot_be_replaced(self):
        ext = self.external()
        a = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        duplicate = create(m.Customer, business=self.business, display_name='Duplicate')
        b = identity.canonical(self.business, self.manager, 'CUSTOMER', duplicate.pk)
        identity.link(self.business, self.manager, ext.pk, a.pk, 'Review')
        obj, issue = identity.link(self.business, self.manager, ext.pk, b.pk, 'Review')
        self.assertIsNone(obj)
        self.assertEqual(issue.conflict_type, 'MULTIPLE_CANONICAL_MATCHES')
        self.assertEqual(m.IdentityLink.objects.filter(status='ACTIVE').count(), 1)

    def test_database_active_link_constraint(self):
        ext = self.external()
        a = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        duplicate = create(m.Customer, business=self.business, display_name='Duplicate')
        b = identity.canonical(self.business, self.manager, 'CUSTOMER', duplicate.pk)
        identity.link(self.business, self.manager, ext.pk, a.pk, 'Review')
        with self.assertRaises(IntegrityError), transaction.atomic():
            m.IdentityLink.objects.create(canonical_identity=b, external_identity=ext, match_type='MANUAL', linked_at=timezone.now(), created_at=timezone.now())

    def test_entity_type_mismatch_rejected(self):
        ext = self.external()
        target = identity.canonical(self.business, self.manager, 'PRODUCT', self.product.pk)
        with self.assertRaises(DomainError):
            identity.link(self.business, self.manager, ext.pk, target.pk, 'Review')

    def test_cross_tenant_link_rejected(self):
        ext = self.external()
        target = create(m.CanonicalIdentity, business=self.other, entity_type='CUSTOMER', entity_id=self.other_customer.pk, canonical_key='OTHER')
        with self.assertRaises(DomainError):
            identity.link(self.business, self.manager, ext.pk, target.pk, 'Review')

    def test_product_and_order_source_matching(self):
        create(m.ProductExternalReference, product=self.product, integration_connection=self.connection, external_product_id='p1')
        ext = self.external(kind='EXTERNAL_PRODUCT_ID', value='p1', external_id='p1', entity_type='PRODUCT')
        link, _ = identity.resolve(self.business, self.manager, ext.pk)
        self.assertEqual(link.canonical_identity.entity_id, self.product.pk)
        order = self.order()
        ext = self.external(kind='EXTERNAL_ORDER_ID', value=order.external_order_id, external_id=order.external_order_id, entity_type='ORDER')
        link, _ = identity.resolve(self.business, self.manager, ext.pk)
        self.assertEqual(link.canonical_identity.entity_id, order.pk)

    def test_merge_candidate_review_and_blocked_execution(self):
        self.contact()
        duplicate = create(m.Customer, business=self.business, display_name='Duplicate')
        self.contact(duplicate)
        candidate = identity.detect_merges(self.business, self.manager)[0]
        self.assertEqual(identity.detect_merges(self.business, self.manager)[0].pk, candidate.pk)
        with self.assertRaises(DomainError):
            identity.execute_merge(self.business, self.manager, candidate.pk)
        identity.review_merge(self.business, self.manager, candidate.pk, 'APPROVED', 'Reviewed evidence')
        result = identity.execute_merge(self.business, self.manager, candidate.pk)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertTrue(m.Customer.objects.filter(pk=duplicate.pk).exists())
        self.assertTrue(m.IdentityHistory.objects.filter(action='MERGE_EXECUTION_BLOCKED').exists())

    def test_rejected_merge_cannot_execute(self):
        self.contact()
        self.contact(create(m.Customer, business=self.business, display_name='Duplicate'))
        candidate = identity.detect_merges(self.business, self.manager)[0]
        identity.review_merge(self.business, self.manager, candidate.pk, 'REJECTED', 'Shared household email')
        with self.assertRaises(DomainError):
            identity.execute_merge(self.business, self.manager, candidate.pk)

    def test_conflict_review_preserves_history(self):
        self.external()
        _, conflict = identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', 'EMAIL', 'new@example.com', external_id='52')
        identity.review_conflict(self.business, self.manager, conflict.pk, 'REVIEWING', 'Investigating')
        identity.review_conflict(self.business, self.manager, conflict.pk, 'RESOLVED', 'Wrong source record rejected')
        conflict.refresh_from_db()
        self.assertEqual(conflict.status, 'RESOLVED')
        self.assertEqual(m.IdentityHistory.objects.filter(action__startswith='CONFLICT_').count(), 3)

    def test_anonymous_purchase_links_historical_sessions_and_events(self):
        visitor = self.ingest('visitors', {'visitor_key': 'anon'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 'session1', 'started_at': timezone.now().isoformat()})
        early = self.ingest('website-events', {'session': session.pk, 'visitor': visitor.pk, 'event_type': 'PRODUCT_VIEW', 'product': self.product.pk, 'occurred_at': timezone.now().isoformat()})
        purchase = self.ingest('website-events', {'session': session.pk, 'visitor': visitor.pk, 'event_type': 'PURCHASE', 'order': self.order().pk, 'occurred_at': timezone.now().isoformat()})
        identity.link_anonymous(self.business, self.manager, visitor.pk, purchase.pk)
        identity.link_anonymous(self.business, self.manager, visitor.pk, purchase.pk)
        visitor.refresh_from_db(); session.refresh_from_db(); early.refresh_from_db()
        self.assertFalse(visitor.is_anonymous)
        self.assertEqual(session.customer_id, self.customer.pk)
        self.assertEqual(early.customer_id, self.customer.pk)
        self.assertEqual(m.IdentityHistory.objects.filter(action='ANONYMOUS_TO_KNOWN').count(), 1)

    def test_anonymous_link_requires_purchase_evidence(self):
        visitor = self.ingest('visitors', {'visitor_key': 'anon'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's1', 'started_at': timezone.now().isoformat()})
        event = self.ingest('website-events', {'session': session.pk, 'visitor': visitor.pk, 'event_type': 'PAGE_VIEW', 'occurred_at': timezone.now().isoformat()})
        with self.assertRaises(DomainError):
            identity.link_anonymous(self.business, self.manager, visitor.pk, event.pk)
        visitor.refresh_from_db()
        self.assertTrue(visitor.is_anonymous)


class SupportOperationTests(DomainFixture):
    def test_assignment_reassignment_release_history(self):
        obj = self.conversation()
        a = operations.assign(self.business, self.operator, obj.pk, 'AGENT', self.operator.pk)
        again = operations.assign(self.business, self.operator, obj.pk, 'AGENT', self.operator.pk)
        self.assertEqual(a.pk, again.pk)
        operations.assign(self.business, self.operator, obj.pk, 'AGENT', self.manager.pk)
        operations.assign(self.business, self.operator, obj.pk, 'UNASSIGNED')
        self.assertEqual(m.ConversationAssignment.objects.filter(status='ACTIVE').count(), 0)
        self.assertEqual(m.ConversationEvent.objects.filter(event_type='ASSIGNMENT').count(), 3)

    def test_agent_must_belong_to_business_and_be_support_capable(self):
        obj = self.conversation()
        for user in [self.stranger, self.viewer]:
            with self.subTest(user=user.pk), self.assertRaises(DomainError):
                operations.assign(self.business, self.operator, obj.pk, 'AGENT', user.pk)

    def test_team_assignment(self):
        obj = self.conversation()
        team = m.SupportTeam.objects.create(business=self.business, name='Support')
        team.members.add(self.operator)
        operations.assign(self.business, self.operator, obj.pk, 'TEAM', team.pk)
        self.client.force_authenticate(self.operator)
        response = self.client.get(self.url('support-queue/?assigned=team'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_ai_human_handover_preserves_context_and_ownership(self):
        obj = self.conversation()
        operations.handover(self.business, self.operator, obj.pk, 'AI', reason='Routine request')
        operations.handover(self.business, self.operator, obj.pk, 'HUMAN', self.manager.pk, 'Customer requested help', 'Order delayed')
        obj.refresh_from_db()
        self.assertEqual(obj.ai_handover_state, 'HUMAN')
        active = obj.conversationassignment_set.get(status='ACTIVE')
        self.assertEqual(active.assignee_id, self.manager.pk)
        self.assertEqual(obj.conversationevent_set.filter(event_type='HANDOVER').count(), 2)
        self.assertEqual(obj.conversationevent_set.filter(event_type='HANDOVER').last().context['summary'], 'Order delayed')

    def test_handover_without_reason_is_rejected(self):
        with self.assertRaises(DomainError):
            operations.handover(self.business, self.operator, self.conversation().pk, 'AI')

    def test_closed_conversation_cannot_be_assigned(self):
        obj = self.conversation()
        data.transition(self.business, self.operator, 'conversations', obj.pk, 'CLOSED')
        with self.assertRaises(DomainError):
            operations.assign(self.business, self.operator, obj.pk, 'AI')

    def test_viewer_cannot_mutate(self):
        with self.assertRaises(DomainError):
            operations.assign(self.business, self.viewer, self.conversation().pk, 'AI')

    def test_customer360_assembles_actual_relationships(self):
        order = self.order()
        self.payment(order)
        self.conversation()
        self.ingest('calls', {'external_call_id': 'c', 'direction': 'INCOMING', 'customer': self.customer.pk, 'order': order.pk})
        self.ingest('shipments', {'external_shipment_id': 's', 'provider': 'MOCK', 'order': order.pk, 'customer': self.customer.pk})
        result = projections.customer360(self.business, self.customer.pk)
        for name in ['orders', 'payments', 'conversations', 'calls', 'shipments']:
            self.assertEqual(result[name]['count'], 1)
        self.assertEqual(result['intelligence']['attribution_analysis']['status'], 'UNAVAILABLE')
        self.assertFalse(m.BusinessFact.objects.exists())

    def test_overview_does_not_invent_revenue_or_ai(self):
        self.order()
        result = projections.overview(self.business)
        self.assertEqual(result['canonical_counts']['orders'], 1)
        self.assertEqual(result['intelligence']['facts']['count'], 0)
        self.assertEqual(result['business_health']['status'], 'UNAVAILABLE')
        self.assertNotIn('revenue', result)

    def test_authoritative_verified_facts_only(self):
        for state in ['VERIFIED', 'INVALIDATED', 'EXPIRED', 'CANDIDATE']:
            create(m.BusinessFact, business=self.business, fact_type='TEST', statement=state, status=state, detected_at=timezone.now())
        result = projections.authority_context(self.business)
        self.assertEqual(result['facts']['count'], 1)
        self.assertEqual(result['facts']['results'][0]['statement'], 'VERIFIED')

    def test_action_review_records_approver_without_executing(self):
        recommendation = create(m.AiRecommendation, business=self.business, recommendation_type='DELIVERY', title='Review', description='Persisted authoritative recommendation', generated_at=timezone.now())
        fact = create(m.BusinessFact, business=self.business, fact_type='TEST', statement='Persisted fact', detected_at=timezone.now())
        create(m.AiRecommendationEvidence, ai_recommendation=recommendation, business_fact=fact, evidence_type='FACT')
        action = create(m.AiAction, business=self.business, ai_recommendation=recommendation, action_type='CONTACT_CUSTOMER')
        with self.assertRaises(DomainError):
            operations.review_action(self.business, self.operator, action.pk, 'APPROVED', 'Reviewed')
        operations.review_action(self.business, self.manager, action.pk, 'APPROVED', 'Reviewed')
        action.refresh_from_db()
        self.assertEqual(action.status, 'APPROVED')
        self.assertIsNone(action.executed_at)
        self.assertEqual(m.DomainAudit.objects.get(action='ACTION_APPROVED').actor_id, self.manager.pk)


class DomainAPITests(DomainFixture):
    def test_status_endpoint_remains_public(self):
        self.client.force_authenticate(None)
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Bizora API is running.')

    def test_authentication_required(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url('customers/')).status_code, [401, 403])

    def test_cross_business_list_detail_and_command(self):
        for path, method, payload in [('customers/', 'get', None), (f'customers/{self.other_customer.pk}/', 'get', None),
                                     ('customers/', 'post', {'data': {'display_name': 'X'}}), ('identity/detect-merges/', 'post', {})]:
            with self.subTest(path=path):
                response = getattr(self.client, method)(self.url(path, self.other), data=payload, format='json')
                self.assertEqual(response.status_code, 404)

    def test_viewer_can_read_but_cannot_write(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(self.url('customers/')).status_code, 200)
        response = self.client.post(self.url('customers/'), {'data': {'display_name': 'X'}}, format='json', HTTP_IDEMPOTENCY_KEY='x')
        self.assertEqual(response.status_code, 403)

    def test_nonmember_superuser_has_no_tenant_bypass(self):
        self.stranger.is_superuser = True
        self.stranger.save(update_fields=['is_superuser'])
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.get(self.url('customers/')).status_code, 404)

    def test_create_retry_and_validation(self):
        url = self.url('products/')
        body = {'data': {'name': 'Coffee', 'price': '12.50'}}
        first = self.client.post(url, body, format='json', HTTP_IDEMPOTENCY_KEY='create')
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(url, body, format='json', HTTP_IDEMPOTENCY_KEY='create')
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data['id'], second.data['id'])
        invalid = self.client.post(url, {'data': {'name': 'Bad', 'price': '-1'}}, format='json', HTTP_IDEMPOTENCY_KEY='bad')
        self.assertEqual(invalid.status_code, 400)

    def test_key_required_and_no_unrestricted_patch_delete(self):
        url = self.url(f'products/{self.product.pk}/')
        self.assertEqual(self.client.patch(url, {'status': 'ARCHIVED'}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(self.client.post(self.url('products/'), {'data': {'name': 'X'}}, format='json').status_code, 400)

    def test_pagination_filtering_search_and_invalid_filter(self):
        create(m.Product, business=self.business, name='Coffee', sku='COFFEE')
        response = self.client.get(self.url('products/?q=Coffee&page_size=1'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Coffee')
        self.assertEqual(self.client.get(self.url('products/?business=999')).status_code, 400)
        self.assertEqual(self.client.get(self.url('products/?since=bad')).status_code, 400)

    def test_cross_business_foreign_key_error(self):
        response = self.client.post(self.url('orders/'), {'connection_id': self.connection.pk, 'data': {'external_order_id': 'o1',
            'customer': self.other_customer.pk, 'items': [{'product': self.product.pk, 'unit_price': '10'}]}}, format='json', HTTP_IDEMPOTENCY_KEY='x')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(m.Order.objects.count(), 0)

    def test_identity_manager_only(self):
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.post(self.url('identity/detect-merges/'), {}, format='json').status_code, 403)
        self.assertEqual(self.client.get(self.url('identity/history/')).status_code, 403)

    def test_identity_registration_resolve_and_audit_api(self):
        contact = create(m.CustomerContact, customer=self.customer, contact_type='EMAIL', value='buyer@example.com', normalized_value='buyer@example.com')
        self.assertEqual(self.client.post(self.url('identity/verify-contact/'), {'contact_id': contact.pk, 'reason': 'Proof'}, format='json').status_code, 200)
        response = self.client.post(self.url('identity/register/'), {'connection_id': self.connection.pk, 'entity_type': 'CUSTOMER', 'identity_type': 'EMAIL', 'value': 'buyer@example.com', 'external_id': '52', 'verified': True}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        resolved = self.client.post(self.url('identity/resolve/'), {'external_identity_id': response.data['result']['id']}, format='json')
        self.assertEqual(resolved.status_code, 200, resolved.data)
        self.assertEqual(resolved.data['status'], 'RESOLVED')
        self.assertGreater(self.client.get(self.url('identity/history/')).data['count'], 0)

    def test_missing_identity_fields_return_validation_error(self):
        self.assertEqual(self.client.post(self.url('identity/register/'), {}, format='json').status_code, 400)

    def test_operational_detail_and_360_endpoints(self):
        order = self.order()
        payment = self.payment(order)
        conversation = self.conversation()
        for path in ['overview/', 'website-performance/', f'customers/{self.customer.pk}/360/', f'products/{self.product.pk}/',
                     f'orders/{order.pk}/', f'payments/{payment.pk}/', f'conversations/{conversation.pk}/']:
            with self.subTest(path=path):
                response = self.client.get(self.url(path))
                self.assertEqual(response.status_code, 200, response.data)

    def test_assignment_handover_and_queue_api(self):
        obj = self.conversation()
        response = self.client.post(self.url(f'conversations/{obj.pk}/assign/'), {'assignee_type': 'AGENT', 'assignee_id': self.manager.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(self.url('support-queue/?assigned=me'))
        self.assertEqual(response.data['count'], 1)
        response = self.client.post(self.url(f'conversations/{obj.pk}/handover/'), {'target': 'AI', 'reason': 'Routine'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get(self.url('support-queue/?assigned=unassigned')).data['count'], 0)

    def test_unknown_resource_and_missing_object(self):
        self.assertEqual(self.client.get(self.url('unknown/')).status_code, 404)
        self.assertEqual(self.client.get(self.url('products/999999/')).status_code, 404)

    def test_metadata_and_recording_transport_are_not_exposed(self):
        call = self.ingest('calls', {'external_call_id': 'c1', 'direction': 'INCOMING', 'recording_url': 'https://private.test/token', 'source_metadata': {'token': 'secret'}})
        result = self.client.get(self.url(f'calls/{call.pk}/'))
        self.assertEqual(result.status_code, 200)
        self.assertNotIn('recording_url', result.data['record'])
        self.assertNotIn('source_metadata', result.data['record'])
        self.assertEqual(result.data['recording_access']['status'], 'UNAVAILABLE')


class AdditionalIntegrityTests(DomainFixture):
    def test_mock_provider_payload_uses_canonical_processing(self):
        from app.domains.mock_transport import MockCommerceTransport
        adapter = MockCommerceTransport(self.business, self.manager, self.connection)
        raw = {'id': 17, 'name': 'Provider Tea', 'sku': 'PT', 'regular_price': '12.50'}
        first, made = adapter.receive('event17', 'product', raw)
        second, replay = adapter.receive('event17', 'product', raw)
        self.assertTrue(made)
        self.assertFalse(replay)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.price, Decimal('12.50'))
        self.assertEqual(first.source_metadata, raw)
        self.assertTrue(m.ProcessingReceipt.objects.filter(entity_id=first.pk, resource='products').exists())

    def test_mock_transport_rejects_live_connection(self):
        from app.domains.mock_transport import MockCommerceTransport
        self.connection.is_mock = False
        with self.assertRaises(DomainError):
            MockCommerceTransport(self.business, self.manager, self.connection)

    def test_outbound_message_mock_is_explicit_and_retry_safe(self):
        from app.domains.mock_transport import MockMessageTransport
        obj = self.ingest('messages', {'conversation': self.conversation().pk, 'external_message_id': 'm1',
             'direction': 'OUTGOING', 'sender_type': 'AGENT', 'content': 'Hello'}, connection_id=self.connection.pk)
        first = MockMessageTransport().send(self.business, self.operator, obj.pk)
        second = MockMessageTransport().send(self.business, self.operator, obj.pk)
        self.assertTrue(first['simulated'])
        self.assertEqual(first, second)
        obj.refresh_from_db()
        self.assertEqual(obj.delivery_status, 'SENT')

    def test_message_read_state_is_idempotent(self):
        obj = self.ingest('messages', {'conversation': self.conversation().pk, 'external_message_id': 'm1',
             'direction': 'INCOMING', 'sender_type': 'CUSTOMER', 'content': 'Hello'})
        operations.mark_read(self.business, self.operator, obj.pk)
        operations.mark_read(self.business, self.operator, obj.pk)
        obj.refresh_from_db()
        self.assertEqual(obj.read_status, 'READ')
        self.assertIsNotNone(obj.read_at)
        self.assertEqual(m.DomainAudit.objects.filter(action='MESSAGE_READ').count(), 1)

    def test_unknown_status_cannot_enter_canonical_layer(self):
        for name, payload in [('products', {'name': 'Bad', 'status': 'UNKNOWN'}),
             ('orders', {'external_order_id': 'o', 'status': 'UNKNOWN'}),
             ('shipments', {'external_shipment_id': 's', 'order': self.order().pk, 'provider': 'MOCK', 'status': 'UNKNOWN'})]:
            with self.subTest(name=name), self.assertRaises(DomainError):
                self.ingest(name, payload)

    def test_missing_related_object_does_not_create_record(self):
        with self.assertRaises(DomainError):
            self.ingest('contacts', {'customer': 999999, 'contact_type': 'EMAIL', 'value': 'a@example.test'})
        self.assertFalse(m.CustomerContact.objects.exists())

    def test_disconnected_connection_rejected(self):
        self.connection.status = 'DISCONNECTED'
        self.connection.save(update_fields=['status'])
        with self.assertRaises(DomainError):
            self.ingest('products', {'name': 'X'}, connection_id=self.connection.pk)

    def test_source_payment_amount_is_immutable(self):
        payment = self.payment()
        with self.assertRaises(DomainError):
            self.ingest('payments', {'external_payment_id': payment.external_payment_id, 'order': payment.order_id,
                'customer': self.customer.pk, 'amount': '1', 'status': 'PAID'}, connection_id=self.connection.pk)
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal('20'))

    def test_payment_currency_must_match_order(self):
        with self.assertRaises(DomainError):
            self.payment(currency='USD')

    def test_fractional_quantity_and_boolean_fk_rejected(self):
        with self.assertRaises(DomainError):
            self.order(items=[{'product': self.product.pk, 'quantity': 1.5, 'unit_price': '10'}])
        with self.assertRaises(DomainError):
            self.order(customer=True)

    def test_duplicate_external_delivery_under_new_event_key_is_noop(self):
        payload = {'external_order_id': 'o1', 'customer': self.customer.pk, 'items': [{'product': self.product.pk, 'unit_price': '10'}]}
        first = self.ingest('orders', payload, key='delivery1', connection_id=self.connection.pk)
        second = self.ingest('orders', payload, key='delivery2', connection_id=self.connection.pk)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(m.OrderItem.objects.count(), 1)
        self.assertEqual(m.OrderStatusHistory.objects.count(), 1)

    def test_no_order_snapshot_overwrite_on_product_update(self):
        order = self.order()
        self.ingest('products', {'name': 'Tea new', 'price': '50', 'external_reference': {'external_product_id': 'tea'}}, connection_id=self.connection.pk)
        item = order.orderitem_set.get()
        self.assertEqual(item.product_name, 'Tea')
        self.assertEqual(item.unit_price, Decimal('10'))

    def test_cross_tenant_campaign_conversion_session_rejected(self):
        visitor = create(m.WebsiteVisitor, business=self.other, visitor_key='private', first_seen_at=timezone.now())
        session = create(m.WebsiteSession, business=self.other, visitor=visitor, started_at=timezone.now())
        campaign = self.ingest('campaigns', {'external_campaign_id': 'ca', 'name': 'Test', 'platform': 'META'})
        with self.assertRaises(DomainError):
            self.ingest('conversions', {'campaign': campaign.pk, 'external_conversion_id': 'co', 'conversion_type': 'PURCHASE', 'converted_at': timezone.now().isoformat(), 'website_session_id': session.pk})

    def test_visitor_session_mismatch_rejected(self):
        visitor = self.ingest('visitors', {'visitor_key': 'one'})
        other = self.ingest('visitors', {'visitor_key': 'two'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's', 'started_at': timezone.now().isoformat()})
        with self.assertRaises(DomainError):
            self.ingest('website-events', {'session': session.pk, 'visitor': other.pk, 'event_type': 'PAGE_VIEW', 'occurred_at': timezone.now().isoformat()})

    def test_anonymous_transition_rejects_conflicting_customer(self):
        visitor = self.ingest('visitors', {'visitor_key': 'one'})
        duplicate = create(m.Customer, business=self.business, display_name='Another')
        session = self.ingest('sessions', {'visitor': visitor.pk, 'customer': duplicate.pk, 'external_session_id': 's', 'started_at': timezone.now().isoformat()})
        # Simulate an inconsistent legacy row to verify defensive linking, rather than bypassing intake validation.
        event = create(m.WebsiteEvent, visitor=visitor, session=session, order=self.order(), event_type='PURCHASE', occurred_at=timezone.now())
        with self.assertRaises(DomainError):
            identity.link_anonymous(self.business, self.manager, visitor.pk, event.pk)
        visitor.refresh_from_db()
        self.assertIsNone(visitor.customer_id)

    def test_action_without_fact_evidence_cannot_be_approved(self):
        recommendation = create(m.AiRecommendation, business=self.business, recommendation_type='TEST', title='Draft', description='Unsupported', generated_at=timezone.now())
        action = create(m.AiAction, business=self.business, ai_recommendation=recommendation, action_type='TEST')
        with self.assertRaises(DomainError):
            operations.review_action(self.business, self.manager, action.pk, 'APPROVED', 'Review')
        action.refresh_from_db()
        self.assertEqual(action.status, 'SUGGESTED')
        self.assertEqual(projections.authority_context(self.business)['recommendations']['count'], 0)

    def test_assignment_updates_handling_mode(self):
        obj = self.conversation()
        for kind, pk, expected in [('AI', None, 'AI'), ('AGENT', self.operator.pk, 'HUMAN'), ('UNASSIGNED', None, None)]:
            operations.assign(self.business, self.operator, obj.pk, kind, pk)
            obj.refresh_from_db()
            self.assertEqual(obj.ai_handover_state, expected)

    def test_attachment_javascript_url_rejected_atomically(self):
        obj = self.conversation()
        with self.assertRaises(DomainError):
            self.ingest('messages', {'conversation': obj.pk, 'external_message_id': 'm', 'direction': 'INCOMING',
                'sender_type': 'CUSTOMER', 'content': 'File', 'attachments': [{'attachment_type': 'FILE', 'url': 'javascript:alert(1)'}]})
        self.assertFalse(m.Message.objects.exists())
        self.assertFalse(m.MessageAttachment.objects.exists())

    def test_retroactive_callback_is_rejected(self):
        with self.assertRaises(DomainError):
            self.ingest('callbacks', {'customer': self.customer.pk, 'scheduled_at': (timezone.now()-timedelta(days=1)).isoformat()})

    def test_negative_variant_inventory_rejected_atomically(self):
        before = m.Product.objects.count()
        with self.assertRaises(DomainError):
            self.ingest('products', {'name': 'Invalid', 'variants': [{'name': 'Bad', 'inventory_quantity': -1}]})
        self.assertEqual(m.Product.objects.count(), before)

    def test_database_contact_uniqueness_and_primary(self):
        create(m.CustomerContact, customer=self.customer, contact_type='EMAIL', value='one@example.test', normalized_value='one@example.test', is_primary=True)
        for value, primary in [('one@example.test', False), ('two@example.test', True)]:
            with self.subTest(value=value), self.assertRaises(IntegrityError), transaction.atomic():
                m.CustomerContact.objects.create(customer=self.customer, contact_type='EMAIL', value=value, normalized_value=value, is_primary=primary, created_at=timezone.now(), updated_at=timezone.now())

    def test_existing_model_compatibility_and_registered_resources(self):
        from app.domains.registry import RESOURCES
        self.assertTrue(m.BusinessRelationship._meta.get_field('rule_key'))
        self.assertTrue(m.KnowledgeEmbedding._meta.get_field('embedding'))
        self.assertEqual(len(RESOURCES), 32)
        for name in RESOURCES:
            with self.subTest(resource=name):
                response = self.client.get(self.url(name + '/'))
                self.assertEqual(response.status_code, 200, response.data)


class AnonymousIdentityLinkTests(DomainFixture):
    def test_purchase_produces_traceable_external_to_customer_link(self):
        visitor = self.ingest('visitors', {'visitor_key': 'visitor52'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's52', 'started_at': timezone.now().isoformat()}, connection_id=self.connection.pk)
        event = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'PURCHASE', 'order': self.order().pk, 'occurred_at': timezone.now().isoformat()})
        identity.link_anonymous(self.business, self.manager, visitor.pk, event.pk)
        link = m.IdentityLink.objects.get(match_type='ANONYMOUS_TO_KNOWN')
        self.assertEqual(link.external_identity.integration_connection_id, self.connection.pk)
        self.assertEqual(link.external_identity.external_id, 'visitor52')
        self.assertEqual(link.canonical_identity.entity_id, self.customer.pk)
        self.assertEqual(link.metadata['purchase_event_id'], event.pk)

    def test_anonymous_external_conflict_rolls_back_customer_backfill(self):
        visitor = self.ingest('visitors', {'visitor_key': 'visitor52'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's52', 'started_at': timezone.now().isoformat()}, connection_id=self.connection.pk)
        event = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'PURCHASE', 'order': self.order().pk, 'occurred_at': timezone.now().isoformat()})
        duplicate = create(m.Customer, business=self.business, display_name='Other customer')
        target = identity.canonical(self.business, self.manager, 'CUSTOMER', duplicate.pk)
        ext, _ = identity.register(self.business, self.manager, self.connection.pk, 'VISITOR', 'CLIENT_ID', 'visitor52', external_id='visitor52')
        m.IdentityLink.objects.create(canonical_identity=target, external_identity=ext, match_type='ANONYMOUS_TO_KNOWN', linked_at=timezone.now(), created_at=timezone.now())
        with self.assertRaises(DomainError):
            identity.link_anonymous(self.business, self.manager, visitor.pk, event.pk)
        visitor.refresh_from_db(); session.refresh_from_db()
        self.assertIsNone(visitor.customer_id)
        self.assertIsNone(session.customer_id)


class MappingTests(DomainFixture):
    def test_multiple_variant_external_mappings_share_parent_id(self):
        variants = [create(m.ProductVariant, product=self.product, name=x) for x in ['Small', 'Large']]
        refs = []
        for i, variant in enumerate(variants):
            refs.append(self.ingest('product-references', {'product': self.product.pk, 'product_variant': variant.pk,
                'external_product_id': 'p52', 'external_variant_id': str(i)}, connection_id=self.connection.pk))
        self.assertNotEqual(refs[0].pk, refs[1].pk)
        self.assertEqual(m.ProductExternalReference.objects.filter(external_product_id='p52').count(), 2)

    def test_product_reference_cannot_reparent_existing_mapping(self):
        self.ingest('product-references', {'product': self.product.pk, 'external_product_id': 'p52'}, connection_id=self.connection.pk)
        other = create(m.Product, business=self.business, name='Other')
        with self.assertRaises(DomainError):
            self.ingest('product-references', {'product': other.pk, 'external_product_id': 'p52'}, connection_id=self.connection.pk)

    def test_product_operational_context_uses_purchase_relationships(self):
        order = self.order()
        self.ingest('shipments', {'order': order.pk, 'external_shipment_id': 's', 'provider': 'MOCK'})
        obj = projections.detail(self.business, 'products', self.product.pk)
        self.assertEqual(obj['customers']['count'], 1)
        self.assertEqual(obj['shipments']['count'], 1)
        self.assertEqual(obj['related_conversations']['count'], 0)


class DocumentationBoundaryTests(DomainFixture):
    def test_canonical_conversion_cannot_claim_internal_attribution(self):
        campaign = self.ingest('campaigns', {'external_campaign_id': 'ca', 'name': 'Campaign', 'platform': 'META'})
        with self.assertRaises(DomainError):
            self.ingest('conversions', {'campaign': campaign.pk, 'external_conversion_id': 'co', 'conversion_type': 'PURCHASE',
                'converted_at': timezone.now().isoformat(), 'attribution_type': 'LAST_TOUCH_ATTRIBUTION'})
        self.assertFalse(m.CampaignConversion.objects.exists())

    def test_imported_tags_cannot_impersonate_bi_classification(self):
        tag = self.ingest('tags', {'customer': self.customer.pk, 'tag': 'VIP', 'source': 'BUSINESS_INTELLIGENCE'})
        self.assertEqual(tag.source, 'MANUAL')

    @skipUnless(connection.vendor == 'sqlite', 'Local demo command intentionally accepts isolated SQLite only.')
    def test_demo_is_repeatable_and_uses_real_domain_processing(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('demo_domains', username=self.manager.username, stdout=out)
        before = {model.__name__: model.objects.count() for model in [m.Customer, m.Product, m.Order, m.Payment, m.Message, m.Shipment, m.ProcessingReceipt]}
        call_command('demo_domains', username=self.manager.username, stdout=out)
        after = {model.__name__: model.objects.count() for model in [m.Customer, m.Product, m.Order, m.Payment, m.Message, m.Shipment, m.ProcessingReceipt]}
        self.assertEqual(before, after)
        self.assertIn('Demo ready:', out.getvalue())

    def test_preflight_is_read_only(self):
        from django.core.management import call_command
        from io import StringIO
        self.order()
        before = m.Order.objects.count()
        out = StringIO()
        call_command('preflight_domains', stdout=out)
        self.assertIn('preflight passed', out.getvalue())
        self.assertEqual(m.Order.objects.count(), before)


@skipUnless(connection.vendor == 'postgresql', 'Row-lock concurrency requires PostgreSQL; SQLite does not implement SELECT FOR UPDATE.')
class PostgresConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user('concurrent')
        self.business = create(m.Business, name='Concurrency', slug='concurrency')
        m.BusinessMembership.objects.create(business=self.business, user=self.actor, role='MANAGER')

    def parallel(self, fn):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier = Barrier(2)

        def worker(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return fn(index)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, i) for i in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_concurrent_idempotent_event_creates_once(self):
        def event(index):
            obj, made = data.ingest(self.business, self.actor, 'products', {'name': 'One'}, 'same-key')
            return obj.pk, made
        results = self.parallel(event)
        self.assertEqual(results[0][0], results[1][0])
        self.assertEqual(sum(made for _, made in results), 1)
        self.assertEqual(m.Product.objects.count(), 1)
        self.assertEqual(m.ProcessingReceipt.objects.count(), 1)

    def test_concurrent_refunds_cannot_exceed_payment(self):
        payment = create(m.Payment, business=self.business, amount=Decimal('10'), status='PAID')
        def refund(index):
            try:
                data.ingest(self.business, self.actor, 'refunds',
                    {'payment': payment.pk, 'external_refund_id': str(index), 'amount': '8'}, f'refund-{index}')
                return 'ACCEPTED'
            except DomainError as exc:
                return exc.code
        self.assertCountEqual(self.parallel(refund), ['ACCEPTED', 'EXCESSIVE_REFUND'])
        self.assertEqual(m.Refund.objects.count(), 1)


    def test_concurrent_product_sku_intake_requires_review_instead_of_duplicate(self):
        def event(index):
            try:
                data.ingest(self.business,self.actor,'products',{'name':'One catalog product','sku':'NEW-SKU'},f'product-{index}')
                return 'CREATED'
            except DomainError as exc:
                return exc.code
        self.assertCountEqual(self.parallel(event),['CREATED','PRODUCT_REVIEW_REQUIRED'])
        self.assertEqual(m.Product.objects.count(),1)
        self.assertEqual(m.ProcessingReceipt.objects.count(),1)

    def test_concurrent_variant_events_upsert_one_parent_sku(self):
        product = create(m.Product, business=self.business, name='Concurrent product')
        def event(index):
            obj, _ = data.ingest(self.business, self.actor, 'variants',
                    {'product': product.pk, 'sku': 'S', 'name': 'Small', 'price': '10'}, f'variant-{index}')
            return obj.pk
        ids = self.parallel(event)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(m.ProductVariant.objects.count(), 1)

    def test_identity_deactivation_racing_resolution_leaves_no_active_link(self):
        source = create(m.IntegrationSource, key='concurrency-provider', name='Provider', category='COMMERCE')
        connection = create(m.IntegrationConnection, business=self.business, integration_source=source)
        customer = create(m.Customer, business=self.business, display_name='Concurrent customer')
        create(m.CustomerContact, customer=customer, contact_type='EMAIL', value='concurrent@example.test', normalized_value='concurrent@example.test', is_verified=True)
        external, _ = identity.register(self.business, self.actor, connection.pk, 'CUSTOMER', 'EMAIL', 'concurrent@example.test', external_id='c', verified=True)
        target = identity.canonical(self.business, self.actor, 'CUSTOMER', customer.pk)
        def action(index):
            if index:
                identity.set_status(self.business, self.actor, target.pk, 'INACTIVE', 'Concurrent review')
                return 'INACTIVE'
            try:
                identity.resolve(self.business, self.actor, external.pk)
                return 'RESOLVED'
            except DomainError as exc:
                return exc.code
        result = self.parallel(action)
        self.assertIn('INACTIVE', result)
        target.refresh_from_db()
        self.assertEqual(target.status, 'INACTIVE')
        self.assertFalse(m.IdentityLink.objects.filter(canonical_identity=target, status='ACTIVE').exists())


class CustomerReferenceContinuityTests(DomainFixture):
    def test_order_customer_is_inherited_by_payment_shipment_and_call(self):
        order = self.order()
        payloads = [
            ('payments', {'external_payment_id': 'p', 'order': order.pk, 'amount': '20', 'status': 'PAID'}),
            ('shipments', {'external_shipment_id': 's', 'order': order.pk, 'provider': 'MOCK'}),
            ('calls', {'external_call_id': 'c', 'order': order.pk, 'direction': 'INCOMING'}),
        ]
        for name, payload in payloads:
            with self.subTest(name=name):
                self.assertEqual(self.ingest(name, payload).customer_id, self.customer.pk)
        result = projections.customer360(self.business, self.customer.pk)
        self.assertEqual(result['payments']['count'], 1)
        self.assertEqual(result['shipments']['count'], 1)
        self.assertEqual(result['calls']['count'], 1)

    def test_order_conversation_customer_contradiction_is_rejected(self):
        conversation = self.conversation()
        other = create(m.Customer, business=self.business, display_name='Different')
        order = self.order(customer=other.pk)
        with self.assertRaises(DomainError):
            self.ingest('calls', {'external_call_id': 'c', 'conversation': conversation.pk,
                        'order': order.pk, 'direction': 'INCOMING'})


class InputShapeTests(DomainFixture):
    def test_invalid_nested_shapes_rejected_without_partial_writes(self):
        cases = [('customers', {'display_name': 'X', 'external_reference': []}),
                 ('customers', {'display_name': 'X', 'contacts': ['bad']}),
                 ('products', {'name': 'X', 'variants': [None]}),
                 ('products', {'name': 'X', 'external_reference': 'bad'})]
        for name, payload in cases:
            with self.subTest(name=name), self.assertRaises(DomainError):
                self.ingest(name, payload)
        self.assertFalse(m.ProcessingReceipt.objects.exists())

    def test_whitespace_identifiers_rejected(self):
        with self.assertRaises(DomainError):
            self.order(external_order_id='   ')
        with self.assertRaises(DomainError):
            self.ingest('products', {'name': 'X', 'external_reference': {'external_product_id': '   '}}, connection_id=self.connection.pk)

    def test_historical_source_order_can_import_observed_status(self):
        order = self.order(status='DELIVERED')
        history = order.orderstatushistory_set.get()
        self.assertIsNone(history.from_status)
        self.assertEqual(history.to_status, 'DELIVERED')
        self.assertEqual(history.source, 'INGESTION')
        self.assertEqual(order.orderstatushistory_set.count(), 1)


class CatalogAndFinancialProjectionTests(DomainFixture):
    def test_multiple_product_images_and_shared_url_are_supported(self):
        other = create(m.Product, business=self.business, name='Other')
        for product, url in [(self.product, 'https://example.test/a.png'), (self.product, 'https://example.test/b.png'), (other, 'https://example.test/a.png')]:
            self.ingest('product-images', {'product': product.pk, 'url': url})
        self.assertEqual(m.ProductImage.objects.count(), 3)
        result = projections.detail(self.business, 'products', self.product.pk)
        self.assertEqual(result['product-images']['count'], 2)

    def test_variant_update_preserves_order_snapshot(self):
        variant = self.ingest('variants', {'product': self.product.pk, 'name': 'Small', 'sku': 'SMALL', 'price': '10'})
        order = self.order(items=[{'product': self.product.pk, 'product_variant': variant.pk, 'unit_price': '10'}])
        response = self.client.post(self.url(f'variants/{variant.pk}/update/'), {'data': {'name': 'Renamed', 'sku': 'NEW', 'price': '12.50', 'inventory_quantity': 4}}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['sku'], 'NEW')
        self.assertEqual(order.orderitem_set.get().sku, 'SMALL')
        self.assertEqual(order.orderitem_set.get().unit_price, Decimal('10'))

    def test_variant_updates_reject_invalid_money_parent_and_duplicate_sku(self):
        variant = self.ingest('variants', {'product': self.product.pk, 'sku': 'SMALL', 'name': 'Small'})
        self.ingest('variants', {'product': self.product.pk, 'sku': 'LARGE', 'name': 'Large'})
        for changes in [{'price': '-1'}, {'product': self.product.pk}, {'sku': 'LARGE'}, {'inventory_quantity': -1}]:
            with self.subTest(changes=changes), self.assertRaises(DomainError):
                data.update_variant(self.business, self.manager, variant.pk, changes)

    def test_variant_optimistic_guard_and_viewer_authorization(self):
        variant = self.ingest('variants', {'product': self.product.pk, 'name': 'Small'})
        with self.assertRaises(DomainError):
            data.update_variant(self.business, self.manager, variant.pk, {'name': 'Changed'}, timezone.now()+timedelta(days=1))
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(self.url(f'variants/{variant.pk}/update/'), {'data': {'name': 'Changed'}}, format='json').status_code, 403)

    def test_financial_timeline_orders_payments_and_refunds_with_scope(self):
        payment = self.payment()
        self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r1', 'amount': '5', 'status': 'COMPLETED'})
        response = self.client.get(self.url(f'financial-timeline/?customer={self.customer.pk}&page_size=1'))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['entity_kind'], 'REFUND')
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(self.client.get(self.url(f'financial-timeline/?customer={self.other_customer.pk}')).status_code, 400)
        self.assertEqual(self.client.get(self.url('financial-timeline/', self.other)).status_code, 404)


class AuthenticationMechanismTests(DomainFixture):
    def test_real_basic_authentication_and_wrong_password(self):
        import base64
        self.client.force_authenticate(None)
        valid = base64.b64encode(b'manager:test-password-123').decode('ascii')
        response = self.client.get(self.url('customers/'), HTTP_AUTHORIZATION='Basic ' + valid)
        self.assertEqual(response.status_code, 200)
        invalid = base64.b64encode(b'manager:wrong-password').decode('ascii')
        self.assertIn(self.client.get(self.url('customers/'), HTTP_AUTHORIZATION='Basic ' + invalid).status_code, [401, 403])

    def test_session_writes_require_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username='manager', password='test-password-123'))
        self.assertEqual(client.get(self.url('customers/')).status_code, 200)
        response = client.post(self.url('products/'), {'data': {'name': 'Blocked without CSRF'}}, format='json', HTTP_IDEMPOTENCY_KEY='csrf')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(m.Product.objects.filter(name='Blocked without CSRF').exists())
