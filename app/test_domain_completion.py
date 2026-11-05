"""Continuation: executable acceptance evidence for remaining local capabilities and seams."""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import connection
from unittest import skipUnless
from app import models as m
from app.test_domains import DomainFixture
from app.domains import data, identity, operations, projections
from app.domains.common import create, DomainError
from app.domains.contracts import prepare_operation


class CanonicalCompletionTests(DomainFixture):
    def test_transition_rejects_corrupt_legacy_customer_reference(self):
        order = self.order()
        m.Order.objects.filter(pk=order.pk).update(customer=self.other_customer)
        before = m.OrderStatusHistory.objects.filter(order=order).count()
        with self.assertRaises(DomainError):
            data.transition(self.business, self.operator, 'orders', order.pk, 'CONFIRMED')
        order.refresh_from_db()
        self.assertEqual(order.status, 'PENDING')
        self.assertEqual(m.OrderStatusHistory.objects.filter(order=order).count(), before)

    def test_scalar_and_boolean_shape_validation(self):
        for payload in [{'name': {'nested': 'bad'}}, {'name': ['bad']}, {'name': True}]:
            with self.subTest(payload=payload), self.assertRaises(DomainError):
                self.ingest('products', payload)
        with self.assertRaises(DomainError):
            self.ingest('customers', {'contacts': [{'contact_type': 'EMAIL', 'value': 'a@example.test', 'is_primary': 'false'}]})

    def test_source_connection_must_match_parent(self):
        other_source = create(m.IntegrationConnection, business=self.business, integration_source=self.connection.integration_source)
        with self.assertRaises(DomainError):
            self.ingest('messages', {'conversation': self.conversation().pk, 'external_message_id': 'm', 'direction': 'INCOMING',
                        'sender_type': 'CUSTOMER', 'content': 'Hi'}, connection_id=other_source.pk)

    def test_null_source_payload_rejected_cleanly(self):
        response = self.client.post(self.url('calls/'), {'connection_id': self.connection.pk, 'data': {
            'integration_connection': None, 'external_call_id': 'c', 'direction': 'INCOMING'}}, format='json', HTTP_IDEMPOTENCY_KEY='null')
        self.assertEqual(response.status_code, 400)

    def test_corrupt_legacy_parent_graph_rejected(self):
        visitor = create(m.WebsiteVisitor, business=self.other, visitor_key='foreign', first_seen_at=timezone.now())
        session = create(m.WebsiteSession, business=self.business, visitor=visitor, started_at=timezone.now())
        with self.assertRaises(DomainError):
            self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'PAGE_VIEW', 'occurred_at': timezone.now().isoformat()})
        self.assertEqual(self.client.get(self.url(f'sessions/{session.pk}/')).status_code, 400)

    def test_payment_method_normalization(self):
        cases = {'cash': 'CASH', 'cash on delivery': 'COD', 'card': 'CARD', 'mobile banking': 'MOBILE_BANKING',
                 'bank-transfer': 'BANK_TRANSFER', 'wallet': 'WALLET', 'other': 'OTHER'}
        for original, expected in cases.items():
            with self.subTest(method=original):
                self.assertEqual(self.payment(payment_method=original).payment_method, expected)
        with self.assertRaises(DomainError):
            self.payment(payment_method='arbitrary-gateway-schema')

    def test_refund_state_cannot_be_imported_without_ledger(self):
        for status in ['PARTIALLY_REFUNDED', 'REFUNDED']:
            with self.subTest(status=status), self.assertRaises(DomainError):
                self.payment(status=status)

    def test_refund_currency_inherits_payment_currency(self):
        product = create(m.Product, business=self.business, name='USD product', currency='USD')
        order = self.order(currency='USD', items=[{'product': product.pk, 'unit_price': '10'}])
        payment = self.ingest('payments', {'external_payment_id': 'usd', 'order': order.pk, 'amount': '10', 'status': 'PAID'})
        refund = self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'r', 'amount': '3'})
        self.assertEqual(payment.currency, 'USD')
        self.assertEqual(refund.currency, 'USD')
        self.assertTrue(self.customer.customertimelineevent_set.filter(entity_type='Refund', entity_id=refund.pk).exists())

    def test_shipment_completion_and_refund_transition_timestamps(self):
        shipment = self.ingest('shipments', {'order': self.order().pk, 'external_shipment_id': 's', 'provider': 'MOCK'})
        for status in ['SUBMITTED', 'PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED']:
            data.transition(self.business, self.operator, 'shipments', shipment.pk, status)
        shipment.refresh_from_db()
        self.assertIsNotNone(shipment.submitted_at)
        self.assertIsNotNone(shipment.picked_up_at)
        self.assertIsNotNone(shipment.delivered_at)
        refund = self.ingest('refunds', {'payment': self.payment().pk, 'external_refund_id': 'r', 'amount': '1'})
        data.transition(self.business, self.operator, 'refunds', refund.pk, 'COMPLETED')
        refund.refresh_from_db()
        self.assertIsNotNone(refund.refunded_at)

    def test_call_answer_and_end_timestamps(self):
        call = self.ingest('calls', {'external_call_id': 'c', 'direction': 'incoming'})
        for status in ['RINGING', 'ANSWERED', 'COMPLETED']:
            data.transition(self.business, self.operator, 'calls', call.pk, status)
        call.refresh_from_db()
        self.assertIsNotNone(call.answered_at)
        self.assertIsNotNone(call.ended_at)

    def test_performance_and_experience_signal_contracts(self):
        visitor = self.ingest('visitors', {'visitor_key': 'v'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's', 'started_at': timezone.now().isoformat()})
        base = {'session': session.pk, 'visitor': visitor.pk, 'occurred_at': timezone.now().isoformat()}
        for kind, props in [('PERFORMANCE', {'latency_ms': 125.5}), ('EXPERIENCE', {'signal': 'RAGE_CLICK'})]:
            self.assertEqual(self.ingest('website-events', {**base, 'event_type': kind, 'properties': props}).properties, props)
        for kind, props in [('PERFORMANCE', {'latency_ms': -1}), ('PERFORMANCE', {'latency_ms': True}), ('EXPERIENCE', {'signal': 'INVENTED'})]:
            with self.subTest(props=props), self.assertRaises(DomainError):
                self.ingest('website-events', {**base, 'event_type': kind, 'properties': props})

    def test_known_visitor_reobservation_preserves_resolved_identity(self):
        visitor = self.ingest('visitors', {'visitor_key': 'v'})
        visitor.customer, visitor.is_anonymous = self.customer, False
        visitor.save(update_fields=['customer', 'is_anonymous'])
        observed = self.ingest('visitors', {'visitor_key': 'v'})
        self.assertEqual(observed.customer_id, self.customer.pk)
        self.assertFalse(observed.is_anonymous)


class IdentityCompletionTests(DomainFixture):
    def test_provider_user_identifiers_are_preserved_without_contact_matching(self):
        for kind in ('TELEGRAM_USER_ID', 'INSTAGRAM_USER_ID', 'PSID'):
            with self.subTest(kind=kind):
                external, conflict = identity.register(self.business, self.manager, self.connection.pk,
                    'CUSTOMER', kind, ' 000AbC ', external_id=kind)
                self.assertIsNone(conflict)
                self.assertEqual(external.normalized_value, '000AbC')
                self.assertEqual(identity.resolve(self.business, self.manager, external.pk), (None, None))

    def verified(self, customer, kind, value, source_id):
        create(m.CustomerContact, customer=customer, contact_type=kind, value=value, normalized_value=value, is_verified=True)
        return identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', kind, value,
                                 external_id=source_id, verified=True)[0]

    def test_identity_availability_lifecycle_and_history(self):
        ext = self.verified(self.customer, 'EMAIL', 'a@example.test', 'a')
        linked, _ = identity.resolve(self.business, self.manager, ext.pk)
        identity.set_status(self.business, self.manager, linked.canonical_identity_id, 'SUPERSEDED', 'Source retired')
        linked.refresh_from_db()
        self.assertEqual(linked.status, 'INVALIDATED')
        self.assertTrue(m.IdentityHistory.objects.filter(action='STATUS_CHANGED').exists())
        with self.assertRaises(DomainError):
            identity.resolve(self.business, self.manager, ext.pk)
        identity.set_status(self.business, self.manager, linked.canonical_identity_id, 'ACTIVE', 'Reviewed')
        self.assertIsNotNone(identity.resolve(self.business, self.manager, ext.pk)[0])

    def test_status_change_cannot_fake_merge_or_bypass_permissions(self):
        target = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        for actor, status in [(self.operator, 'INACTIVE'), (self.manager, 'MERGED')]:
            with self.subTest(status=status), self.assertRaises(DomainError):
                identity.set_status(self.business, actor, target.pk, status, 'Reason')

    def test_external_enrichment_tracks_seen_bounds_and_verified_review(self):
        ext, _ = identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', 'EMAIL', 'a@example.test', external_id='a')
        first = ext.first_seen_at
        identity.enrich_external(self.business, self.manager, ext.pk, {'region': 'Dhaka'}, first-timedelta(days=1), 'Observed source history', verified=True)
        identity.enrich_external(self.business, self.manager, ext.pk, {}, first-timedelta(days=2), 'Older observation')
        ext.refresh_from_db()
        self.assertEqual(ext.first_seen_at, first-timedelta(days=2))
        self.assertGreaterEqual(ext.last_seen_at, first)
        self.assertIs(ext.metadata['verified'], True)
        self.assertEqual(ext.metadata['region'], 'Dhaka')
        with self.assertRaises(DomainError):
            identity.enrich_external(self.business, self.manager, ext.pk, {'verified': True}, first, 'Spoof')

    def test_multiple_verified_identifiers_resolve_atomically(self):
        email = self.verified(self.customer, 'EMAIL', 'a@example.test', 'a')
        phone = self.verified(self.customer, 'PHONE', '+8801712345678', 'b')
        result, issue = identity.resolve_many(self.business, self.manager, [email.pk, phone.pk])
        self.assertIsNone(issue)
        self.assertEqual(result.entity_id, self.customer.pk)
        self.assertEqual(m.IdentityLink.objects.filter(rule_key='MULTI_FIELD_CORROBORATION').count(), 2)

    def test_contradictory_multi_field_evidence_creates_no_new_links(self):
        other = create(m.Customer, business=self.business, display_name='Other')
        email = self.verified(self.customer, 'EMAIL', 'a@example.test', 'a')
        phone = self.verified(other, 'PHONE', '+8801712345678', 'b')
        result, issue = identity.resolve_many(self.business, self.manager, [email.pk, phone.pk])
        self.assertIsNone(result)
        self.assertEqual(issue.conflict_type, 'CONTRADICTORY_IDENTIFIERS')
        self.assertFalse(m.IdentityLink.objects.exists())
        self.assertFalse(m.CanonicalIdentity.objects.exists())

    def test_insufficient_multi_field_evidence_rolls_back_partial_match(self):
        email = self.verified(self.customer, 'EMAIL', 'a@example.test', 'a')
        phone, _ = identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', 'PHONE', '+8801712345678', external_id='b', verified=False)
        self.assertEqual(identity.resolve_many(self.business, self.manager, [email.pk, phone.pk]), (None, None))
        self.assertFalse(m.IdentityLink.objects.exists())

    def test_invalid_link_review_is_idempotent(self):
        ext = self.verified(self.customer, 'EMAIL', 'a@example.test', 'a')
        link, _ = identity.resolve(self.business, self.manager, ext.pk)
        link.canonical_identity.status = 'INACTIVE'
        link.canonical_identity.save(update_fields=['status'])
        a = identity.validate_links(self.business, self.manager)
        b = identity.validate_links(self.business, self.manager)
        self.assertEqual(a[0].pk, b[0].pk)
        self.assertEqual(m.IdentityConflict.objects.filter(conflict_type='INVALID_LINK').count(), 1)

    def test_login_and_form_recovery_require_verified_matching_identity(self):
        ext = self.verified(self.customer, 'EMAIL', 'a@example.test', 'a')
        identity.resolve(self.business, self.manager, ext.pk)
        for event_type in ['LOGIN', 'SIGNUP', 'FORM_SUBMISSION']:
            visitor = self.ingest('visitors', {'visitor_key': event_type})
            session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': event_type, 'started_at': timezone.now().isoformat()})
            event = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': event_type,
                        'properties': {'identity_value': 'a@example.test'}, 'occurred_at': timezone.now().isoformat()})
            identity.link_anonymous(self.business, self.manager, visitor.pk, event.pk, ext.pk)
            visitor.refresh_from_db()
            self.assertEqual(visitor.customer_id, self.customer.pk)
        self.assertEqual(m.IdentityHistory.objects.filter(action='ANONYMOUS_TO_KNOWN', rule_key='VERIFIED_IDENTIFIER_VISITOR').count(), 3)

    def test_login_mismatched_identifier_rejected(self):
        ext = self.verified(self.customer, 'EMAIL', 'a@example.test', 'a')
        identity.resolve(self.business, self.manager, ext.pk)
        visitor = self.ingest('visitors', {'visitor_key': 'v'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's', 'started_at': timezone.now().isoformat()})
        event = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'LOGIN',
                'properties': {'identity_value': 'wrong@example.test'}, 'occurred_at': timezone.now().isoformat()})
        with self.assertRaises(DomainError):
            identity.link_anonymous(self.business, self.manager, visitor.pk, event.pk, ext.pk)
        visitor.refresh_from_db()
        self.assertIsNone(visitor.customer_id)


class OperationalCompletionTests(DomainFixture):
    def test_customer_lookup_by_normalized_contact_tag_and_source(self):
        customer = self.ingest('customers', {'display_name': 'VIP', 'contacts': [{'contact_type': 'PHONE', 'value': '01712345678'}],
                  'tags': ['VIP'], 'external_reference': {'external_customer_id': '52'}}, connection_id=self.connection.pk)
        for query in ['contact=01712345678&contact_type=PHONE', 'tag=vip', f'external_id=52&connection_id={self.connection.pk}']:
            response = self.client.get(self.url('customers/?'+query))
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual([r['id'] for r in response.data['results']], [customer.pk])
        self.assertEqual(self.client.get(self.url(f'customers/?external_id=52&connection_id={self.other_connection.pk}')).status_code, 400)

    def test_product_source_lookup_does_not_mix_connections(self):
        self.ingest('product-references', {'product': self.product.pk, 'external_product_id': 'p1'}, connection_id=self.connection.pk)
        response = self.client.get(self.url(f'products/?external_id=p1&connection_id={self.connection.pk}'))
        self.assertEqual(response.data['results'][0]['id'], self.product.pk)
        self.assertEqual(self.client.get(self.url('products/?external_id=p1')).status_code, 400)

    def test_inbox_search_uses_messages_but_not_internal_notes(self):
        conversation = self.conversation()
        self.ingest('messages', {'conversation': conversation.pk, 'external_message_id': 'm', 'direction': 'incoming',
                    'sender_type': 'customer', 'content': 'parcel missing'})
        self.ingest('notes', {'conversation': conversation.pk, 'content': 'secret routing note'})
        self.assertEqual(self.client.get(self.url('conversations/?q=parcel')).data['count'], 1)
        self.assertEqual(self.client.get(self.url('conversations/?q=secret')).data['count'], 0)
        self.assertEqual(self.client.get(self.url('messages/?q=parcel')).data['count'], 1)

    def test_support_context_composes_canonical_data_and_explicit_fallbacks(self):
        conversation = self.conversation()
        order = self.order()
        self.payment(order)
        self.ingest('notes', {'conversation': conversation.pk, 'content': 'Internal context'})
        response = self.client.get(self.url(f'conversations/{conversation.pk}/context/?order={order.pk}'))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['order']['record']['id'], order.pk)
        self.assertEqual(response.data['customer']['payments']['count'], 1)
        self.assertEqual(response.data['internal_notes']['count'], 1)
        self.assertEqual(response.data['suggested_reply']['status'], 'UNAVAILABLE')
        self.assertEqual(response.data['policy_context']['status'], 'UNAVAILABLE')

    def test_context_rejects_unrelated_order_even_inside_same_business(self):
        conversation = self.conversation()
        other = create(m.Customer, business=self.business, display_name='Another')
        order = self.order(customer=other.pk)
        self.assertEqual(self.client.get(self.url(f'conversations/{conversation.pk}/context/?order={order.pk}')).status_code, 400)
        self.assertEqual(self.client.get(self.url(f'conversations/{conversation.pk}/context/', self.other)).status_code, 404)

    def test_priority_command_validated_authorized_and_audited(self):
        conversation = self.conversation()
        url = self.url(f'conversations/{conversation.pk}/priority/')
        for _ in range(2):
            self.assertEqual(self.client.post(url, {'priority': 'URGENT', 'reason': 'Customer waiting'}, format='json').status_code, 200)
        self.assertEqual(conversation.conversationevent_set.filter(event_type='PRIORITY').count(), 1)
        self.assertEqual(self.client.get(self.url('support-queue/?priority=URGENT')).data['count'], 1)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(url, {'priority': 'LOW', 'reason': 'No'}, format='json').status_code, 403)

    def test_journey_is_chronological_across_sessions_and_paginated(self):
        visitor = self.ingest('visitors', {'visitor_key': 'v'})
        now = timezone.now()
        for key, date in [('late', now), ('early', now-timedelta(hours=1))]:
            session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': key, 'started_at': date.isoformat()})
            self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'PAGE_VIEW', 'occurred_at': date.isoformat(), 'page_title': key})
        response = self.client.get(self.url(f'visitors/{visitor.pk}/journey/?page_size=1'))
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['page_title'], 'early')
        self.assertIsNotNone(response.data['next'])

    def test_retargeting_context_is_observed_data_not_recommendation(self):
        response = self.client.get(self.url(f'customers/{self.customer.pk}/retargeting-context/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['kind'], 'OBSERVED_SIGNALS')
        self.assertEqual(response.data['audience_recommendation']['status'], 'UNAVAILABLE')
        self.assertEqual(response.data['events']['count'], 0)

    def test_identity_commands_available_with_manager_permissions(self):
        target = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        url = self.url('identity/set-status/')
        response = self.client.post(url, {'canonical_identity_id': target.pk, 'status': 'INACTIVE', 'reason': 'Retired'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.post(url, {'canonical_identity_id': target.pk, 'status': 'ACTIVE', 'reason': 'Retry'}, format='json').status_code, 403)


class ExternalContractTests(DomainFixture):
    def recommendation(self, *, expired=False, foreign=False):
        rec = create(m.AiRecommendation, business=self.business, recommendation_type='DELIVERY', title='Observed proposal',
                     description='Stored by AI owner', generated_at=timezone.now())
        fact = create(m.BusinessFact, business=self.other if foreign else self.business, fact_type='TEST', statement='Observed fact',
                      detected_at=timezone.now(), valid_to=timezone.now()-timedelta(days=1) if expired else None)
        create(m.AiRecommendationEvidence, ai_recommendation=rec, business_fact=fact, evidence_type='FACT')
        action = create(m.AiAction, business=self.business, ai_recommendation=rec, action_type='CONTACT_CUSTOMER')
        return rec, fact, action

    def test_expired_fact_cannot_approve_action_or_surface_recommendation(self):
        rec, _, action = self.recommendation(expired=True)
        with self.assertRaises(DomainError):
            operations.review_action(self.business, self.manager, action.pk, 'APPROVED', 'Review')
        self.assertEqual(projections.authority_context(self.business)['recommendations']['count'], 0)

    def test_mixed_foreign_evidence_cannot_leak_or_approve(self):
        rec, _, action = self.recommendation()
        foreign = create(m.BusinessFact, business=self.other, fact_type='PRIVATE', statement='Foreign private fact', detected_at=timezone.now())
        create(m.AiRecommendationEvidence, ai_recommendation=rec, business_fact=foreign, evidence_type='FACT')
        self.assertEqual(projections.authority_context(self.business)['recommendations']['count'], 0)
        with self.assertRaises(DomainError):
            operations.review_action(self.business, self.manager, action.pk, 'APPROVED', 'Review')

    def test_unsupported_or_expired_proposal_can_still_be_rejected(self):
        rec = create(m.AiRecommendation, business=self.business, recommendation_type='TEST', title='Invalid proposal',
                     description='No evidence', generated_at=timezone.now(), expires_at=timezone.now()-timedelta(days=1))
        action = create(m.AiAction, business=self.business, ai_recommendation=rec, action_type='TEST')
        operations.review_action(self.business, self.manager, action.pk, 'REJECTED', 'Unsupported/expired')
        action.refresh_from_db()
        self.assertEqual(action.status, 'REJECTED')
        self.assertIsNone(action.executed_at)

    def test_foreign_generic_entity_in_fact_is_filtered(self):
        create(m.BusinessFact, business=self.business, subject_entity_type='CUSTOMER', subject_entity_id=self.other_customer.pk,
               fact_type='BAD_REFERENCE', statement='Private reference', detected_at=timezone.now())
        self.assertEqual(projections.authority_context(self.business)['facts']['count'], 0)

    def test_shipment_preparation_returns_contract_without_execution(self):
        shipment = self.ingest('shipments', {'external_shipment_id': 's', 'order': self.order().pk, 'provider': 'MOCK',
                         'recipient_phone': '+8801712345678', 'delivery_address': 'Demo address'}, connection_id=self.connection.pk)
        response = self.client.post(self.url(f'operations/shipment_submit/{shipment.pk}/prepare/'), {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'UNAVAILABLE')
        self.assertEqual(response.data['execution'], 'NOT_EXECUTED')
        self.assertEqual(response.data['request']['payload']['order_id'], shipment.order_id)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, 'PENDING')

    def test_call_and_message_preparation_preserve_canonical_state(self):
        call = self.ingest('calls', {'external_call_id': 'c', 'direction': 'OUTGOING', 'receiver_number': '+8801712345678'}, connection_id=self.connection.pk)
        message = self.ingest('messages', {'external_message_id': 'm', 'conversation': self.conversation().pk, 'direction': 'OUTGOING',
                         'sender_type': 'AGENT', 'content': 'Hello'}, connection_id=self.connection.pk)
        for kind, obj in [('CALL_INITIATE', call), ('MESSAGE_SEND', message)]:
            result = prepare_operation(self.business, self.operator, kind, obj.pk)
            self.assertFalse(result['authoritative'])
            self.assertEqual(result['execution'], 'NOT_EXECUTED')
        call.refresh_from_db(); message.refresh_from_db()
        self.assertEqual(call.status, 'INITIATED')
        self.assertEqual(message.delivery_status, 'PENDING')

    def test_outbound_preparation_rejects_viewer_and_payload_overrides(self):
        shipment = self.ingest('shipments', {'external_shipment_id': 's', 'order': self.order().pk, 'provider': 'MOCK'}, connection_id=self.connection.pk)
        url = self.url(f'operations/shipment_cancel/{shipment.pk}/prepare/')
        self.assertEqual(self.client.post(url, {'tracking_code': 'forged'}, format='json').status_code, 400)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 403)


class ProductDeduplicationTests(DomainFixture):
    def test_variant_reobservation_upserts_by_parent_sku(self):
        a = self.ingest('variants', {'product': self.product.pk, 'sku': 'SMALL', 'name': 'Small', 'price': '10'})
        b = self.ingest('variants', {'product': self.product.pk, 'sku': 'SMALL', 'name': 'Small', 'price': '12'})
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(b.price, Decimal('12'))
        self.assertEqual(m.ProductVariant.objects.count(), 1)

    def test_nested_source_variant_replay_updates_without_duplicates(self):
        payload = {'name': 'Catalog product', 'external_reference': {'external_product_id': 'p'},
                   'variants': [{'sku': 'S', 'name': 'Small', 'price': '10'}]}
        a = self.ingest('products', payload, connection_id=self.connection.pk)
        payload['variants'][0]['price'] = '12'
        b = self.ingest('products', payload, connection_id=self.connection.pk)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(a.productvariant_set.count(), 1)
        self.assertEqual(a.productvariant_set.get().price, Decimal('12'))

    def test_verified_sku_rule_is_opt_in_and_rejects_ambiguity(self):
        ext, _ = identity.register(self.business, self.manager, self.connection.pk, 'PRODUCT', 'SKU', 'TEA', external_id='remote', verified=True)
        self.assertEqual(identity.resolve(self.business, self.manager, ext.pk), (None, None))
        identity.enrich_external(self.business, self.manager, ext.pk, {'sku_match_rule': 'EXPLICIT_VERIFIED_SKU_V1'}, timezone.now(), 'Approved catalog SKU rule')
        link, issue = identity.resolve(self.business, self.manager, ext.pk)
        self.assertIsNone(issue)
        self.assertEqual(link.canonical_identity.entity_id, self.product.pk)
        identity.unlink(self.business, self.manager, link.pk, 'Review ambiguity')
        create(m.Product, business=self.business, name='Duplicate SKU', sku='TEA')
        link, issue = identity.resolve(self.business, self.manager, ext.pk)
        self.assertIsNone(link)
        self.assertEqual(issue.conflict_type, 'MULTIPLE_MATCHES')

    def test_product_merge_candidates_remain_review_only(self):
        duplicate = create(m.Product, business=self.business, name='Possible duplicate', sku='TEA')
        candidate = identity.detect_merges(self.business, self.manager)[0]
        self.assertEqual(candidate.match_reason, 'SHARED_SKU_REVIEW')
        self.assertIsNone(candidate.confidence)
        self.assertTrue(m.Product.objects.filter(pk=duplicate.pk).exists())
        identity.review_merge(self.business, self.manager, candidate.pk, 'APPROVED', 'Reviewed')
        self.assertEqual(identity.execute_merge(self.business, self.manager, candidate.pk)['status'], 'BLOCKED')

    def test_variant_sku_database_constraint(self):
        from django.db import transaction, IntegrityError
        create(m.ProductVariant, product=self.product, sku='S', name='Small')
        with self.assertRaises(IntegrityError), transaction.atomic():
            m.ProductVariant.objects.create(product=self.product, sku='S', created_at=timezone.now(), updated_at=timezone.now())


class PersistedGraphContractTests(DomainFixture):
    def test_future_relationship_is_not_current_context(self):
        order, conversation = self.order(), self.conversation()
        relationship = create(m.BusinessRelationship, business=self.business,
            source_entity_type='ORDER', source_entity_id=order.pk,
            target_entity_type='CONVERSATION', target_entity_id=conversation.pk,
            relationship_type='HAS_CONVERSATION', valid_from=timezone.now()+timedelta(days=1))
        self.assertEqual(projections.authority_context(self.business)['relationships']['count'], 0)
        self.assertEqual(projections.detail(self.business, 'orders', order.pk)['related_conversations']['count'], 0)
        relationship.valid_from = timezone.now()-timedelta(days=1)
        relationship.save(update_fields=['valid_from'])
        self.assertEqual(projections.authority_context(self.business)['relationships']['count'], 1)
        self.assertEqual(projections.detail(self.business, 'orders', order.pk)['related_conversations']['count'], 1)

    def test_graph_context_uses_persisted_owned_nodes_and_edges(self):
        order = self.order()
        customer_node = create(m.GraphNode, business=self.business, entity_type='CUSTOMER', entity_id=self.customer.pk, node_type='CUSTOMER')
        order_node = create(m.GraphNode, business=self.business, entity_type='ORDER', entity_id=order.pk, node_type='ORDER')
        create(m.GraphEdge, business=self.business, source_node=customer_node, target_node=order_node, relationship_type='PLACED_ORDER')
        result = self.client.get(self.url(f'graph-context/customer/{self.customer.pk}/'))
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['nodes']['count'], 2)
        self.assertEqual(result.data['edges']['count'], 1)
        self.assertEqual(result.data['generation']['status'], 'UNAVAILABLE')

    def test_foreign_neighbor_and_edge_are_not_exposed(self):
        node = create(m.GraphNode, business=self.business, entity_type='CUSTOMER', entity_id=self.customer.pk, node_type='CUSTOMER')
        foreign = create(m.GraphNode, business=self.other, entity_type='CUSTOMER', entity_id=self.other_customer.pk, node_type='CUSTOMER')
        create(m.GraphEdge, business=self.business, source_node=node, target_node=foreign, relationship_type='BAD')
        result = projections.graph_context(self.business, 'CUSTOMER', self.customer.pk)
        self.assertEqual(result['edges']['count'], 0)
        self.assertEqual(result['nodes']['count'], 1)
        self.assertEqual(self.client.get(self.url(f'graph-context/customer/{self.other_customer.pk}/')).status_code, 400)

    def test_missing_projection_returns_unavailable_without_building_graph(self):
        result = projections.graph_context(self.business, 'PRODUCT', self.product.pk)
        self.assertEqual(result['status'], 'UNAVAILABLE')
        self.assertFalse(m.GraphNode.objects.exists())

    def test_identity_history_is_filterable_within_business(self):
        a = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        identity.set_status(self.business, self.manager, a.pk, 'INACTIVE', 'Review')
        response = self.client.get(self.url(f'identity/history/?canonical_identity={a.pk}'))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['action'], 'STATUS_CHANGED')
        self.assertEqual(self.client.get(self.url('identity/history/?arbitrary=1')).status_code, 400)


class CrossSourceAndQueueContractTests(DomainFixture):
    def test_payment_courier_and_call_may_use_different_source_from_commerce(self):
        source = create(m.IntegrationSource, key='other-provider', name='Provider', category='OTHER')
        connection = create(m.IntegrationConnection, business=self.business, integration_source=source)
        order = self.order()
        cases = [('payments', {'external_payment_id': 'p', 'order': order.pk, 'amount': '20', 'status': 'PAID'}),
                 ('shipments', {'external_shipment_id': 's', 'order': order.pk, 'provider': 'MOCK'}),
                 ('calls', {'external_call_id': 'c', 'order': order.pk, 'direction': 'INCOMING'})]
        for name, payload in cases:
            with self.subTest(name=name):
                obj = self.ingest(name, payload, connection_id=connection.pk)
                self.assertEqual(obj.integration_connection_id, connection.pk)
                self.assertEqual(obj.order_id, order.pk)
                self.assertEqual(obj.customer_id, self.customer.pk)

    def test_queue_declares_unavailable_external_policies(self):
        self.conversation()
        response = self.client.get(self.url('support-queue/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        for key in ['overdue_detection', 'ai_escalation', 'analytical_queue_metrics']:
            self.assertEqual(response.data['capabilities'][key]['status'], 'UNAVAILABLE')


class ContinuationDemoTests(DomainFixture):
    @skipUnless(connection.vendor == 'sqlite', 'Completion demo intentionally uses isolated SQLite only.')
    def test_verified_demo_replays_without_duplicate_canonical_data(self):
        from django.core.management import call_command
        from io import StringIO
        output = StringIO()
        call_command('demo_completion', username=self.manager.username, stdout=output)
        before = {model.__name__: model.objects.count() for model in [m.Customer, m.Product, m.Order, m.WebsiteVisitor, m.WebsiteSession, m.WebsiteEvent, m.Conversation]}
        call_command('demo_completion', username=self.manager.username, stdout=output)
        after = {model.__name__: model.objects.count() for model in [m.Customer, m.Product, m.Order, m.WebsiteVisitor, m.WebsiteSession, m.WebsiteEvent, m.Conversation]}
        self.assertEqual(before, after)
        self.assertIn('Completion demo verified:', output.getvalue())
        self.assertIn('Suggested reply: UNAVAILABLE', output.getvalue())


class DocumentedRepresentationTests(DomainFixture):
    def test_customer_status_management_and_profile_fields(self):
        customer = self.ingest('customers', {'first_name': 'Demo', 'last_name': 'Buyer', 'display_name': 'Buyer', 'customer_type': 'KNOWN', 'notes': 'Customer profile'})
        for status in ['INACTIVE', 'ACTIVE', 'BLOCKED', 'ACTIVE']:
            data.transition(self.business, self.operator, 'customers', customer.pk, status)
        customer.refresh_from_db()
        self.assertEqual(customer.status, 'ACTIVE')
        self.assertEqual(customer.first_name, 'Demo')
        self.assertEqual(customer.notes, 'Customer profile')

    def test_resolution_status_priority_and_support_timeline(self):
        conversation = self.conversation()
        operations.set_priority(self.business, self.operator, conversation.pk, 'HIGH', 'Review urgency')
        data.transition(self.business, self.operator, 'conversations', conversation.pk, 'PENDING', 'Awaiting customer')
        data.transition(self.business, self.operator, 'conversations', conversation.pk, 'RESOLVED', 'Answered order query')
        conversation.refresh_from_db()
        self.assertIsNotNone(conversation.resolved_at)
        self.assertEqual(conversation.conversationevent_set.filter(event_type='STATUS').last().reason, 'Answered order query')
        data.transition(self.business, self.operator, 'conversations', conversation.pk, 'OPEN', 'Customer followed up')
        conversation.refresh_from_db()
        self.assertIsNone(conversation.resolved_at)

    def test_imported_transcript_and_summary_are_preserved_without_generation(self):
        call = self.ingest('calls', {'external_call_id': 'c', 'direction': 'INCOMING', 'recording_url': 'https://example.test/recording'})
        transcript = self.ingest('transcripts', {'call': call.pk, 'transcript': 'Customer requested delivery update', 'summary': 'Delivery inquiry',
                   'provider': 'SIMULATED_SOURCE', 'confidence': '0.95', 'generated_at': timezone.now().isoformat()})
        self.assertEqual(transcript.summary, 'Delivery inquiry')
        result = self.client.get(self.url(f'calls/{call.pk}/'))
        self.assertEqual(result.data['transcripts']['results'][0]['summary'], 'Delivery inquiry')
        self.assertNotIn('recording_url', result.data['record'])
        with self.assertRaises(DomainError):
            self.ingest('transcripts', {'call': call.pk, 'transcript': 'Invalid confidence', 'confidence': '1.1'})

    def test_website_events_and_device_utm_context_are_preserved(self):
        visitor = self.ingest('visitors', {'visitor_key': 'v'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's', 'started_at': timezone.now().isoformat(),
            'utm_source': 'social', 'utm_campaign': 'spring', 'device_type': 'MOBILE', 'browser': 'Example', 'operating_system': 'ExampleOS'})
        for kind in ['PAGE_VIEW', 'PRODUCT_VIEW', 'SEARCH', 'ADD_TO_CART', 'REMOVE_FROM_CART', 'CHECKOUT_START', 'PURCHASE', 'FORM_SUBMISSION']:
            event = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': kind, 'product': self.product.pk,
                                'occurred_at': timezone.now().isoformat()})
            self.assertEqual(event.product_id, self.product.pk)
        response = self.client.get(self.url('sessions/?utm_campaign=spring&device_type=MOBILE'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['browser'], 'Example')

    def test_location_message_has_validated_canonical_coordinates(self):
        conversation = self.conversation()
        base = {'external_message_id': 'location', 'conversation': conversation.pk, 'direction': 'INCOMING', 'sender_type': 'CUSTOMER', 'message_type': 'LOCATION'}
        obj = self.ingest('messages', {**base, 'location': {'latitude': 23.8, 'longitude': 90.4, 'label': 'Delivery location'}})
        self.assertEqual(obj.location['latitude'], 23.8)
        for location in [None, {'latitude': 200, 'longitude': 90}, {'latitude': True, 'longitude': 90}]:
            with self.subTest(location=location), self.assertRaises(DomainError):
                self.ingest('messages', {**base, 'external_message_id': 'invalid', 'location': location})


class RecoveredTimelineTests(DomainFixture):
    def test_anonymous_activity_recovers_original_customer_timeline_dates(self):
        visitor = self.ingest('visitors', {'visitor_key': 'recover'})
        before = timezone.now()-timedelta(days=1)
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 'recover', 'started_at': before.isoformat()})
        early = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'PAGE_VIEW', 'occurred_at': before.isoformat()})
        purchase = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'PURCHASE', 'order': self.order().pk, 'occurred_at': timezone.now().isoformat()})
        identity.link_anonymous(self.business, self.manager, visitor.pk, purchase.pk)
        identity.link_anonymous(self.business, self.manager, visitor.pk, purchase.pk)
        event = self.customer.customertimelineevent_set.get(entity_type='WebsiteEvent', entity_id=early.pk)
        self.assertEqual(event.event_at, before)
        self.assertEqual(self.customer.customertimelineevent_set.filter(entity_type='WebsiteEvent').count(), 2)

    def test_corrupt_cross_business_session_blocks_backfill_without_mutation(self):
        visitor = self.ingest('visitors', {'visitor_key': 'recover'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 'recover', 'started_at': timezone.now().isoformat()})
        bad = create(m.WebsiteSession, business=self.other, visitor=visitor, started_at=timezone.now())
        purchase = self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'PURCHASE', 'order': self.order().pk, 'occurred_at': timezone.now().isoformat()})
        with self.assertRaises(DomainError):
            identity.link_anonymous(self.business, self.manager, visitor.pk, purchase.pk)
        visitor.refresh_from_db(); bad.refresh_from_db()
        self.assertIsNone(visitor.customer_id)
        self.assertIsNone(bad.customer_id)


class CallbackAndConversionTests(DomainFixture):
    def test_requested_callback_can_be_scheduled_without_starting_a_call(self):
        callback = self.ingest('callbacks', {'customer': self.customer.pk, 'reason': 'Customer requested callback'})
        self.assertIsNone(callback.scheduled_at)
        at = timezone.now()+timedelta(hours=1)
        for _ in range(2):
            response = self.client.post(self.url(f'callbacks/{callback.pk}/schedule/'), {'scheduled_at': at.isoformat()}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(m.DomainAudit.objects.filter(action='CALLBACK_SCHEDULED').count(), 1)
        self.assertFalse(m.Call.objects.exists())
        data.transition(self.business, self.manager, 'callbacks', callback.pk, 'CANCELLED')
        with self.assertRaises(DomainError):
            operations.schedule_callback(self.business, self.manager, callback.pk, at+timedelta(hours=1))

    def test_conversion_session_customer_cannot_disagree_with_order(self):
        other = create(m.Customer, business=self.business, display_name='Different')
        visitor = create(m.WebsiteVisitor, business=self.business, customer=other, is_anonymous=False, visitor_key='known', first_seen_at=timezone.now())
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 's', 'started_at': timezone.now().isoformat()})
        campaign = self.ingest('campaigns', {'external_campaign_id': 'ca', 'name': 'Campaign', 'platform': 'META'})
        with self.assertRaises(DomainError):
            self.ingest('conversions', {'campaign': campaign.pk, 'order': self.order().pk, 'website_session_id': session.pk,
                   'external_conversion_id': 'co', 'conversion_type': 'PURCHASE', 'converted_at': timezone.now().isoformat()})

    def test_source_metadata_and_reported_metrics_remain_source_data(self):
        campaign = self.ingest('campaigns', {'external_campaign_id': 'ca', 'name': 'Campaign', 'platform': 'META', 'source_metadata': {'provider_objective': 'SALES'}})
        metric = self.ingest('campaign-metrics', {'campaign': campaign.pk, 'metric_date': '2026-10-24', 'impressions': 100,
               'clicks': 10, 'spend': '20', 'ctr': '0.10', 'cpc': '2.0000', 'roas': '1.5000'})
        self.assertEqual(campaign.source_metadata['provider_objective'], 'SALES')
        self.assertEqual(metric.roas, Decimal('1.5000'))
        self.assertFalse(m.BusinessFact.objects.exists())

    def test_primary_product_url_cannot_contain_executable_scheme(self):
        with self.assertRaises(DomainError):
            self.ingest('products', {'name': 'Bad image', 'image_url': 'javascript:alert(1)'})
