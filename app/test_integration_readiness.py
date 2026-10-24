"""Final domain increment: UI behavior, deterministic intake and external owner contracts."""
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from app.test_domains import DomainFixture
from app import models as m
from app.domains import data, identity
from app.domains.common import create, DomainError
from app.domains.catalog import assess_product
from app.domains.boundaries import exchange, FixtureAdapter, CAPABILITIES, MERGE_OWNERS, VERSION, OUTPUTS
from app.domains.merge import plan, dry_run
from app.operations_ui import SECTIONS

class ProductIntakeReviewTests(DomainFixture):

    def test_shared_sku_requires_review_without_creating_product_or_receipt(self):
        before = m.ProcessingReceipt.objects.count()
        payload = {'name': 'Source Tea', 'sku': 'TEA', 'external_reference': {'external_product_id': 'remote'}}
        self.assertEqual(assess_product(self.business, self.manager, payload, self.connection)['decision'], 'REVIEW')
        with self.assertRaises(DomainError) as error:
            self.ingest('products', payload, connection_id=self.connection.pk)
        self.assertEqual(error.exception.code, 'PRODUCT_REVIEW_REQUIRED')
        self.assertEqual(m.Product.objects.filter(business=self.business).count(), 1)
        self.assertEqual(m.ProcessingReceipt.objects.count(), before)

    def test_reviewed_source_identity_reuses_existing_authoritative_product(self):
        target = identity.canonical(self.business, self.manager, 'PRODUCT', self.product.pk)
        external, _ = identity.register(self.business, self.manager, self.connection.pk, 'PRODUCT', 'EXTERNAL_PRODUCT_ID', 'remote', external_id='remote')
        identity.link(self.business, self.manager, external.pk, target.pk, 'Reviewed supplier SKU/source evidence')
        payload = {'name': 'Source Tea', 'sku': 'TEA', 'external_reference': {'external_product_id': 'remote'}}
        first = self.ingest('products', payload, connection_id=self.connection.pk, key='source-review')
        replay = self.ingest('products', payload, connection_id=self.connection.pk, key='source-review')
        self.assertEqual(first.pk, self.product.pk)
        self.assertEqual(replay.pk, first.pk)
        self.assertEqual(m.Product.objects.filter(business=self.business).count(), 1)
        self.assertTrue(first.productexternalreference_set.filter(external_product_id='remote').exists())

    def test_ambiguous_sku_does_not_pick_first_candidate(self):
        create(m.Product, business=self.business, name='Other Tea', sku='TEA')
        result = assess_product(self.business, self.manager, {'sku': 'TEA'})
        self.assertEqual(result['decision'], 'REVIEW')
        self.assertEqual(len(result['candidate_ids']), 2)

    def test_distinct_product_requires_manager_evidence_and_is_audited(self):
        payload = {'name': 'Distinct Tea', 'sku': 'TEA', 'deduplication': {'decision': 'CREATE_DISTINCT', 'reason': 'Supplier intentionally reused a SKU'}}
        with self.assertRaises(DomainError):
            data.ingest(self.business, self.operator, 'products', payload, 'operator-distinct')
        product = self.ingest('products', payload, key='distinct')
        audit = m.DomainAudit.objects.get(entity_id=product.pk, entity_type='Product', action='INGESTED')
        self.assertEqual(audit.evidence['deduplication']['rule'], 'AUTHORIZED_DISTINCT_PRODUCT')
        self.assertIn('Supplier', audit.evidence['deduplication']['reason'])
        self.assertEqual(self.ingest('products', payload, key='distinct').pk, product.pk)

    def test_product_assessment_api_enforces_tenant_and_role(self):
        response = self.client.post(self.url('products/assess/'), {'data': {'sku': 'TEA'}}, format='json')
        self.assertEqual(response.data['decision'], 'REVIEW')
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(self.url('products/assess/'), {'data': {'sku': 'TEA'}}, format='json').status_code, 403)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(self.url('products/assess/'), {'connection_id': self.other_connection.pk, 'data': {}}, format='json').status_code, 400)

    def test_other_business_sku_is_not_a_candidate(self):
        with self.assertRaises(DomainError):
            assess_product(self.business,self.manager,{'external_reference':[]})
        with self.assertRaises(DomainError):
            assess_product(self.business,self.manager,{'sku':'TEA'},self.other_connection)
        self.assertEqual(assess_product(self.other, self.stranger, {'sku': 'TEA'})['decision'], 'CREATE')

class AttachmentContractTests(DomainFixture):

    def test_metadata_mime_filename_and_size_normalization(self):
        conversation = self.conversation()
        message = self.ingest('messages', {'conversation': conversation.pk, 'external_message_id': 'file', 'direction': 'INCOMING', 'sender_type': 'CUSTOMER', 'attachments': [{'attachment_type': ' image ', 'url': 'https://example.test/p.png', 'mime_type': 'IMAGE/PNG; charset=utf-8', 'file_name': 'p.png', 'size_bytes': 12, 'metadata': {'width': 4}}]})
        attachment = message.messageattachment_set.get()
        self.assertEqual(attachment.attachment_type, 'IMAGE')
        self.assertEqual(attachment.mime_type, 'image/png')
        self.assertEqual(attachment.metadata, {'width': 4})

    def test_unsafe_attachment_metadata_rolls_back_entire_message(self):
        conversation = self.conversation()
        base = {'attachment_type': 'FILE', 'url': 'https://example.test/f'}
        for values in [{'metadata': []}, {'size_bytes': -1}, {'file_name': '../x'}, {'mime_type': 'invalid'}, {'mime_type': 'text/plain\r\nX: y'}, {'url': 'https://user:password@example.test/file'}, {'attachment_type': 'IMAGE', 'mime_type': 'text/html'}]:
            with self.subTest(values=values), self.assertRaises(DomainError):
                self.ingest('messages', {'conversation': conversation.pk, 'external_message_id': 'invalid', 'direction': 'INCOMING', 'sender_type': 'CUSTOMER', 'attachments': [{**base, **values}]})
        self.assertFalse(m.Message.objects.exists())

class ExternalBoundaryContractTests(DomainFixture):

    def inputs(self, owner):
        if owner=='Integrations':
            message=self.ingest('messages',{'conversation':self.conversation().pk,'external_message_id':'contract-'+str(next(self.sequence)),'direction':'OUTGOING','sender_type':'AGENT','content':'Pending fixture'},connection_id=self.connection.pk)
            return {'operation':'MESSAGE_SEND','entity_type':'MESSAGE','entity_id':message.pk}
        if owner in ('Business Intelligence', 'Business Graph', 'AI Intelligence'):
            return {'entity_type': 'CUSTOMER', 'entity_id': self.customer.pk}
        return {'operation': 'MESSAGE_SEND', 'entity_type': 'CUSTOMER', 'entity_id': self.customer.pk, 'query': 'refund policy', 'policy_key': 'support-response', 'resource': 'orders'}

    def test_all_seven_owner_contracts_have_explicit_unavailable_and_fixture_paths(self):
        for owner, capabilities in CAPABILITIES.items():
            capability = next(iter(capabilities))
            with self.subTest(owner=owner):
                absent = exchange(self.business, self.manager, owner, capability, self.inputs(owner), 'request-1')
                self.assertEqual(absent['status'], 'UNAVAILABLE')
                fixture = exchange(self.business, self.manager, owner, capability, self.inputs(owner), 'request-1', FixtureAdapter({**{key: kind() for key, kind in OUTPUTS[owner].items()}, **({'execution': 'NOT_EXECUTED'} if owner == 'Integrations' else {})}))
                self.assertTrue(fixture['simulated'])
                self.assertEqual(fixture['version'], VERSION)

    def test_adapter_scope_version_and_request_mismatch_fail_closed(self):
        for key, value in [('business_id', self.other.pk), ('business_id', True), ('version', 'future.v99'), ('request_id', 'wrong'), ('owner', 'Other')]:

            class BadAdapter(FixtureAdapter):

                def exchange(adapter, envelope):
                    result = super().exchange(envelope)
                    result[key] = value
                    return result
            with self.subTest(key=key), self.assertRaises(DomainError):
                exchange(self.business, self.manager, 'Business Intelligence', 'entity_context', self.inputs('Business Intelligence'), 'request', BadAdapter())

    def test_missing_fields_foreign_entity_and_unsupported_capabilities_rejected(self):
        for owner, cap, payload in [('Monitoring', 'freshness', {}), ('Business Graph', 'entity_context', {'entity_type': 'CUSTOMER', 'entity_id': self.other_customer.pk}), ('AI Intelligence', 'invent_result', {}),('Integrations','prepare_operation',{'operation':'MESSAGE_SEND','entity_type':'CUSTOMER','entity_id':self.customer.pk})]:
            with self.subTest(owner=owner), self.assertRaises(DomainError):
                exchange(self.business, self.manager, owner, cap, payload, 'request')
        with self.assertRaises(DomainError):
            exchange(self.business, self.stranger, 'Monitoring', 'freshness', {'resource': 'orders'}, 'request')

    def test_fixture_cannot_claim_live_provenance(self):

        class FakeLive(FixtureAdapter):

            def exchange(adapter, envelope):
                result = super().exchange(envelope)
                result['simulated'] = False
                return result
        with self.assertRaises(DomainError):
            exchange(self.business, self.manager, 'Monitoring', 'freshness', {'resource': 'orders'}, 'request', FakeLive())

class MergeReadinessTests(DomainFixture):

    def candidate(self, approved=True):
        primary = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        duplicate = create(m.Customer, business=self.business, display_name='Duplicate')
        other = identity.canonical(self.business, self.manager, 'CUSTOMER', duplicate.pk)
        return create(m.IdentityMergeCandidate, business=self.business, primary_identity=primary, candidate_identity=other, match_reason='Manual documented evidence', status='APPROVED' if approved else 'PENDING', detected_at=timezone.now())

    def adapters(self, fingerprint, decision='PREPARED'):
        return {owner: FixtureAdapter({'fingerprint': fingerprint, 'decision': decision, 'preserves_relationships': decision == 'PREPARED', 'notes': 'Fixture reconciliation; no writes'}) for owner in MERGE_OWNERS}

    def test_plan_inventories_local_and_downstream_relations_without_mutation(self):
        candidate = self.candidate()
        self.order()
        create(m.BusinessFact, business=self.business, subject_entity_type='CUSTOMER', subject_entity_id=self.customer.pk, fact_type='REFERENCE', statement='Fixture reference', detected_at=timezone.now())
        counts = (m.IdentityHistory.objects.count(), m.DomainAudit.objects.count(), m.Customer.objects.count())
        result = plan(self.business, self.manager, candidate.pk)
        inventory = {x['model']: x for x in result['relationships']}
        self.assertEqual(inventory['Order']['count'], 1)
        self.assertEqual(inventory['BusinessFact']['owner'], 'Business Intelligence')
        self.assertEqual(inventory['BusinessFact']['count'], 1)
        self.assertEqual(result['execution'], 'BLOCKED')
        self.assertEqual(plan(self.business, self.manager, candidate.pk)['fingerprint'], result['fingerprint'])
        self.assertEqual(counts, (m.IdentityHistory.objects.count(), m.DomainAudit.objects.count(), m.Customer.objects.count()))

    def test_successful_fixture_acknowledgements_never_execute_a_merge(self):
        candidate = self.candidate()
        fingerprint = plan(self.business, self.manager, candidate.pk)['fingerprint']
        result = dry_run(self.business, self.manager, candidate.pk, self.adapters(fingerprint))
        self.assertEqual(result['readiness'], 'SIMULATED_PREPARED')
        self.assertEqual(result['execution'], 'BLOCKED')
        self.assertFalse(result['executed'])
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'APPROVED')
        self.assertTrue(m.Customer.objects.filter(pk=candidate.candidate_identity.entity_id).exists())

    def test_rejected_missing_or_unsafe_owner_acknowledgements_block_readiness(self):
        candidate = self.candidate()
        fingerprint = plan(self.business, self.manager, candidate.pk)['fingerprint']
        self.assertEqual(dry_run(self.business, self.manager, candidate.pk)['readiness'], 'WAITING_FOR_OWNERS')
        self.assertEqual(dry_run(self.business, self.manager, candidate.pk, self.adapters(fingerprint, 'REJECTED'))['readiness'], 'REJECTED')
        pending = self.candidate(False)
        self.assertEqual(dry_run(self.business, self.manager, pending.pk)['readiness'], 'UNSAFE')

    def test_stale_plan_and_wrong_fingerprint_are_rejected(self):
        candidate = self.candidate()
        fingerprint = plan(self.business, self.manager, candidate.pk)['fingerprint']
        self.order()
        with self.assertRaises(DomainError):
            dry_run(self.business, self.manager, candidate.pk, expected_fingerprint=fingerprint)
        with self.assertRaises(DomainError):
            dry_run(self.business, self.manager, candidate.pk, self.adapters('wrong'))

    def test_cross_tenant_relationship_marks_plan_unsafe(self):
        candidate = self.candidate()
        create(m.Order, business=self.other, customer=self.customer, external_order_id='corrupt', ordered_at=timezone.now())
        result = plan(self.business, self.manager, candidate.pk)
        self.assertTrue(any((x['code'] == 'CROSS_TENANT_RELATIONSHIP' for x in result['safety_errors'])))

    def test_dry_run_api_enforces_manager_scope_and_rejects_client_ack_injection(self):
        candidate = self.candidate()
        url = self.url(f'identity/merge-candidates/{candidate.pk}/dry-run/')
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 200)
        self.assertEqual(self.client.post(url, {'adapters': {}}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, [], format='json').status_code, 400)
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 403)

class OperationsUITests(DomainFixture):

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.manager)

    def section_url(self, key):
        return reverse('ops-section', args=[self.business.pk, key])

    def detail_url(self, name, pk):
        return reverse('ops-detail', args=[self.business.pk, name, pk])

    def command_url(self, name, pk, command):
        return reverse('ops-command', args=[self.business.pk, name, pk, command])

    def test_all_thirteen_operational_sections_and_identity_review_render(self):
        for section in SECTIONS:
            with self.subTest(section=section):
                response = self.client.get(self.section_url(section))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Skip to content')
        self.assertContains(self.client.get('/ops/'), 'Demo')

    def test_every_canonical_resource_list_has_authenticated_empty_state(self):
        from app.domains.registry import RESOURCES
        for resource in RESOURCES:
            with self.subTest(resource=resource):
                self.assertEqual(self.client.get(reverse('ops-resources', args=[self.business.pk, resource])).status_code, 200)

    def test_authentication_membership_and_manager_only_review(self):
        self.client.logout()
        self.assertEqual(self.client.get('/ops/').status_code, 302)
        self.assertEqual(self.client.get('/ops/login/').status_code, 200)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.section_url('overview')).status_code, 404)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.section_url('identity')).status_code, 404)
        self.assertEqual(self.client.get(self.section_url('overview')).status_code, 200)

    def test_customer_product_order_payment_and_conversation_details(self):
        order = self.order()
        payment = self.payment(order=order)
        conversation = self.conversation()
        for name, pk in [('customers', self.customer.pk), ('products', self.product.pk), ('orders', order.pk), ('payments', payment.pk), ('conversations', conversation.pk)]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(self.detail_url(name, pk)).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url('customers', self.other_customer.pk)).status_code, 404)

    def test_status_priority_assignment_handover_and_private_note_workflows(self):
        conversation = self.conversation()
        commands = [('priority', {'priority': 'URGENT', 'reason': 'Review'}), ('assign', {'assignee_type': 'AGENT', 'assignee_id': self.operator.pk, 'reason': 'Queue'}), ('handover', {'target': 'AI', 'reason': 'Routine', 'summary': 'Human summary'}), ('note', {'content': 'Private <script>alert(1)</script>', 'submission_id': 'a' * 32}), ('transition', {'status': 'RESOLVED', 'reason': 'Customer confirmed'})]
        for command, body in commands:
            with self.subTest(command=command):
                self.assertEqual(self.client.post(self.command_url('conversations', conversation.pk, command), body).status_code, 302)
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, 'RESOLVED')
        self.assertEqual(conversation.priority, 'URGENT')
        response = self.client.get(self.detail_url('conversations', conversation.pk))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert')
        self.assertNotContains(response, 'id="id_reason"')
        self.assertContains(response, 'id="id_note_content"')
        self.assertEqual(self.client.get(self.command_url('conversations', conversation.pk, 'priority')).status_code, 405)

    def test_pending_reply_and_note_replay_do_not_duplicate_or_send(self):
        conversation = self.conversation()
        for command, content in [('reply', 'A pending reply'), ('note', 'Private business note')]:
            body = {'content': content, 'submission_id': ('a' if command == 'reply' else 'b') * 32}
            for _ in range(2):
                self.assertEqual(self.client.post(self.command_url('conversations', conversation.pk, command), body).status_code, 302)
        self.assertEqual(m.Message.objects.count(), 1)
        self.assertEqual(m.ConversationNote.objects.count(), 1)
        self.assertEqual(m.Message.objects.get().delivery_status, 'PENDING')
        self.assertNotIn('Private business note', str(m.Message.objects.values().first()))

    def test_viewer_cannot_mutate_and_invalid_forms_show_feedback(self):
        conversation = self.conversation()
        url = self.command_url('conversations', conversation.pk, 'priority')
        self.assertEqual(self.client.post(url, {'priority': 'INVALID', 'reason': 'review'}).status_code, 400)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.post(url, {'priority': 'URGENT', 'reason': 'review'}).status_code, 403)
        self.assertNotContains(self.client.get(self.detail_url('conversations', conversation.pk)), 'Authorized commands')

    def test_session_command_requires_csrf_and_logout_is_post_only(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.manager)
        conversation = self.conversation()
        url = self.command_url('conversations', conversation.pk, 'priority')
        self.assertEqual(client.post(url, {'priority': 'HIGH', 'reason': 'review'}).status_code, 403)
        client.get(self.detail_url('conversations', conversation.pk))
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(url, {'priority': 'HIGH', 'reason': 'review'}, HTTP_X_CSRFTOKEN=token).status_code, 302)
        self.assertEqual(client.get('/ops/logout/').status_code, 405)
        self.assertEqual(client.post('/ops/logout/', HTTP_X_CSRFTOKEN=token).status_code, 302)

    def test_filters_pagination_empty_states_and_escaped_customer_values(self):
        create(m.Customer, business=self.business, display_name='<img src=x onerror=alert(1)>')
        response = self.client.get(self.section_url('customers'), {'page_size': 1})
        self.assertContains(response, 'Next page')
        self.assertContains(self.client.get(self.section_url('customers'), {'q': 'missing', 'status': ''}), 'No records found')
        self.assertContains(self.client.get(self.section_url('customers')), '&lt;img')
        self.assertEqual(self.client.get(self.section_url('customers'), {'unsupported': 'x'}).status_code, 400)

    def test_refund_and_callback_workflows(self):
        payment = self.payment()
        self.assertEqual(self.client.post(self.command_url('payments', payment.pk, 'refund'), {'amount': '2.00', 'reason': 'Return', 'submission_id': 'c' * 32}).status_code, 302)
        self.assertEqual(m.Refund.objects.get().amount, 2)
        call = self.ingest('calls', {'external_call_id': 'call', 'direction': 'INCOMING', 'customer': self.customer.pk})
        self.assertEqual(self.client.post(self.command_url('calls', call.pk, 'callback'), {'reason': 'Follow up', 'submission_id': 'd' * 32}).status_code, 302)
        self.assertEqual(m.CallbackRequest.objects.count(), 1)
        self.assertEqual(self.client.get(self.detail_url('calls', call.pk)).status_code, 200)

class FinalCorrectnessTests(DomainFixture):

    def test_nested_external_identifiers_reject_objects_booleans_and_empty_values(self):
        for name, field in [('products', 'external_product_id'), ('customers', 'external_customer_id')]:
            for value in [False, {}, [], None, '  ']:
                with self.subTest(name=name, value=value), self.assertRaises(DomainError):
                    self.ingest(name, {'external_reference': {field: value}}, connection_id=self.connection.pk)

    def test_manual_identity_link_retains_unknown_confidence_without_invented_score(self):
        target = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        external, _ = identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', 'PSID', 'psid', external_id='psid')
        link, _ = identity.link(self.business, self.manager, external.pk, target.pk, 'Customer verified by agent evidence')
        self.assertIsNone(link.confidence)
        replay, _ = identity.link(self.business, self.manager, external.pk, target.pk, 'Same reviewed evidence')
        self.assertEqual(link.pk, replay.pk)
        self.assertEqual(m.IdentityHistory.objects.filter(action='LINKED').count(), 1)

    def test_order_refunded_command_requires_completed_full_refund_ledger(self):
        order = self.order()
        payment = self.payment(order=order)
        for state in ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']:
            data.transition(self.business, self.manager, 'orders', order.pk, state)
        with self.assertRaises(DomainError):
            data.transition(self.business, self.manager, 'orders', order.pk, 'REFUNDED')
        refund = self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'full', 'amount': '20'})
        with self.assertRaises(DomainError):
            data.transition(self.business, self.manager, 'orders', order.pk, 'REFUNDED')
        data.transition(self.business, self.manager, 'refunds', refund.pk, 'COMPLETED')
        self.assertEqual(data.transition(self.business, self.manager, 'orders', order.pk, 'REFUNDED').status, 'REFUNDED')

    def test_fixture_ingress_is_versioned_replay_safe_and_never_accepts_live_source(self):
        from app.domains.mock_transport import MockCanonicalTransport
        adapter = MockCanonicalTransport(self.business, self.manager, self.connection)
        event = {'version': 'bizora.ingest.v1', 'business_id': self.business.pk, 'connection_id': self.connection.pk, 'event_id': 'fixture-call', 'resource': 'calls', 'data': {'external_call_id': 'fixture', 'direction': 'INCOMING'}}
        first, second = (adapter.receive(event), adapter.receive(event))
        self.assertTrue(first['simulated'])
        self.assertTrue(first['created'])
        self.assertFalse(second['created'])
        self.assertEqual(first['record']['id'], second['record']['id'])
        for changed in [{**event, 'business_id': self.other.pk}, {**event, 'version': 'unsupported'}, {**event, 'data': {**event['data'], 'direction': 'OUTGOING'}}]:
            with self.subTest(changed=changed), self.assertRaises(DomainError):
                adapter.receive(changed)
        self.connection.is_mock = False
        self.connection.save(update_fields=['is_mock'])
        with self.assertRaises(DomainError):
            MockCanonicalTransport(self.business, self.manager, self.connection)

    def test_nested_foreign_result_and_invalid_output_schema_are_rejected(self):
        for result in [{'facts': [], 'metrics': [], 'issues': [], 'evidence': [{'business_id': self.other.pk}]}, {'facts': [], 'metrics': [], 'issues': [], 'evidence': [{'entity_type': 'CUSTOMER', 'entity_id': self.other_customer.pk}]}, {'anything': 'not the schema'}]:
            with self.subTest(result=result), self.assertRaises(DomainError):
                exchange(self.business, self.manager, 'Business Intelligence', 'entity_context', {'entity_type': 'CUSTOMER', 'entity_id': self.customer.pk}, 'request', FixtureAdapter(result))

class AdditionalUIWorkflowTests(DomainFixture):

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.manager)
    section_url = OperationsUITests.section_url
    detail_url = OperationsUITests.detail_url
    command_url = OperationsUITests.command_url

    def test_variant_creation_edit_and_source_mapping_reuse_services(self):
        response = self.client.post(self.command_url('products', self.product.pk, 'add-variant'), {'name': 'Small', 'sku': 'SMALL', 'price': '9.50', 'inventory_quantity': 2, 'submission_id': 'e' * 32})
        self.assertEqual(response.status_code, 302)
        variant = m.ProductVariant.objects.get()
        self.assertEqual(self.client.post(self.command_url('variants', variant.pk, 'variant'), {'name': 'Small edit', 'price': '11.00', 'inventory_quantity': 5}).status_code, 302)
        variant.refresh_from_db()
        self.assertEqual(variant.inventory_quantity, 5)
        self.assertEqual(self.client.post(self.command_url('products', self.product.pk, 'map-product'), {'connection_id': self.connection.pk, 'external_product_id': 'reviewed', 'submission_id': 'f' * 32}).status_code, 302)
        self.assertTrue(m.ProductExternalReference.objects.filter(product=self.product, external_product_id='reviewed').exists())
        self.assertEqual(self.client.post(self.command_url('products', self.product.pk, 'map-product'), {'connection_id': self.other_connection.pk, 'external_product_id': 'private', 'submission_id': '1' * 32}).status_code, 400)

    def test_identity_review_and_dry_run_workflows_and_operator_denial(self):
        conflict = identity.conflict(self.business, self.manager, 'MULTIPLE_MATCHES')
        self.assertEqual(self.client.get(self.detail_url('conflicts', conflict.pk)).status_code, 200)
        self.assertEqual(self.client.post(self.command_url('conflicts', conflict.pk, 'review-conflict'), {'decision': 'REVIEWING', 'reason': 'Investigating'}).status_code, 302)
        target = identity.canonical(self.business, self.manager, 'PRODUCT', self.product.pk)
        other = create(m.Product, business=self.business, name='Other product')
        duplicate = identity.canonical(self.business, self.manager, 'PRODUCT', other.pk)
        candidate = create(m.IdentityMergeCandidate, business=self.business, primary_identity=target, candidate_identity=duplicate, match_reason='Review', detected_at=timezone.now())
        self.assertEqual(self.client.post(self.command_url('merge-candidates', candidate.pk, 'review-merge'), {'decision': 'APPROVED', 'reason': 'Reviewed evidence'}).status_code, 302)
        self.assertContains(self.client.post(self.command_url('merge-candidates', candidate.pk, 'merge-plan'), {}), 'WAITING_FOR_OWNERS')
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(self.detail_url('conflicts', conflict.pk)).status_code, 404)

    def test_channel_priority_assignment_filters_and_invalid_login_redirect(self):
        conversation = self.conversation()
        response = self.client.get(self.section_url('inbox'), {'channel': 'WHATSAPP', 'priority': 'NORMAL'})
        self.assertContains(response, conversation.external_conversation_id)
        self.assertNotContains(self.client.get(self.section_url('queue'), {'assigned': 'unassigned', 'priority': 'URGENT'}), conversation.external_conversation_id)
        self.client.logout()
        response = self.client.post('/ops/login/?next=https://attacker.example/', {'username': 'manager', 'password': 'test-password-123'})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('attacker.example', response.url)

class FinalProjectionSecurityTests(DomainFixture):

    def test_ui_never_exposes_provider_credentials_recording_url_or_other_tenant_notes(self):
        from app.domains.contracts import prepare_operation
        conversation = self.conversation()
        self.ingest('notes', {'conversation': conversation.pk, 'content': 'Internal-only-secret'})
        message = self.ingest('messages', {'conversation': conversation.pk, 'external_message_id': 'pending', 'direction': 'OUTGOING', 'sender_type': 'AGENT', 'content': 'Public pending reply'}, connection_id=self.connection.pk)
        self.assertNotIn('Internal-only-secret', str(prepare_operation(self.business, self.manager, 'MESSAGE_SEND', message.pk)))
        call = self.ingest('calls', {'external_call_id': 'c', 'direction': 'INCOMING', 'recording_url': 'https://private.example/token', 'source_metadata': {'credential': 'private-credential'}})
        client = Client()
        client.force_login(self.viewer)
        response = client.get(reverse('ops-detail', args=[self.business.pk, 'calls', call.pk]))
        self.assertNotContains(response, 'private-credential')
        self.assertNotContains(response, 'https://private.example/token')
        client.force_login(self.stranger)
        self.assertEqual(client.get(reverse('ops-detail', args=[self.business.pk, 'conversations', conversation.pk])).status_code, 404)

class ConfiguredMonitoringFixture(FixtureAdapter):

    def __init__(self):
        super().__init__({'freshness': {'status': 'FIXTURE_ONLY'}})

class AdapterConfigurationTests(DomainFixture):

    def test_team_lead_can_swap_a_configured_adapter_without_rewriting_services(self):
        from django.test import override_settings
        path = 'app.test_integration_readiness.ConfiguredMonitoringFixture'
        url = self.url('contracts/monitoring/freshness/')
        body = {'request_id': 'freshness-1', 'payload': {'resource': 'orders'}}
        self.assertEqual(self.client.post(url, body, format='json').data['status'], 'UNAVAILABLE')
        with override_settings(BIZORA_DOMAIN_ADAPTERS={'Monitoring': path}, BIZORA_ALLOW_FIXTURE_ADAPTERS=True):
            response = self.client.post(url, body, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data['simulated'])
            self.assertEqual(response.data['result']['freshness']['status'], 'FIXTURE_ONLY')
        with override_settings(BIZORA_DOMAIN_ADAPTERS={'Monitoring': path}, BIZORA_ALLOW_FIXTURE_ADAPTERS=False):
            self.assertEqual(self.client.post(url, body, format='json').status_code, 400)

    def test_timeout_is_explicit_unavailable_without_leaking_exception_secrets(self):

        class TimeoutFixture(FixtureAdapter):

            def exchange(adapter, envelope):
                raise TimeoutError('provider-password-must-not-leak')
        response = exchange(self.business, self.manager, 'Monitoring', 'freshness', {'resource': 'orders'}, 'request', TimeoutFixture())
        self.assertEqual(response['status'], 'UNAVAILABLE')
        self.assertNotIn('password', str(response))

    def test_contract_api_rejects_client_adapter_injection_and_merge_bypass(self):
        self.assertEqual(self.client.post(self.url('contracts/monitoring/freshness/'), {'request_id': 'x', 'payload': {'resource': 'orders'}, 'adapter': 'evil'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url('contracts/bi/prepare_merge/'), {'request_id': 'x', 'payload': {}}, format='json').status_code, 400)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(self.url('contracts/integrations/prepare_operation/'), {'request_id': 'x', 'payload': {}}, format='json').status_code, 403)

class SourceContradictionAndMergeRaceTests(DomainFixture):

    def test_source_mapping_and_reviewed_identity_contradiction_does_not_overwrite(self):
        create(m.ProductExternalReference, product=self.product, integration_connection=self.connection, external_product_id='same')
        other = create(m.Product, business=self.business, name='Different product')
        canonical = identity.canonical(self.business, self.manager, 'PRODUCT', other.pk)
        external, _ = identity.register(self.business, self.manager, self.connection.pk, 'PRODUCT', 'EXTERNAL_PRODUCT_ID', 'same', external_id='same')
        identity.link(self.business, self.manager, external.pk, canonical.pk, 'Conflicting legacy source evidence')
        with self.assertRaises(DomainError) as error:
            self.ingest('products', {'name': 'Must not overwrite', 'external_reference': {'external_product_id': 'same'}}, connection_id=self.connection.pk)
        self.assertEqual(error.exception.code, 'IDENTITY_CONFLICT')
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Tea')

    def test_relationship_change_during_adapter_reconciliation_rejects_stale_plan(self):
        target = identity.canonical(self.business, self.manager, 'CUSTOMER', self.customer.pk)
        other = create(m.Customer, business=self.business, display_name='Other')
        source = identity.canonical(self.business, self.manager, 'CUSTOMER', other.pk)
        candidate = create(m.IdentityMergeCandidate, business=self.business, primary_identity=target, candidate_identity=source, match_reason='Review', status='APPROVED', detected_at=timezone.now())
        original = plan(self.business, self.manager, candidate.pk)
        test = self

        class MutatingFixture(FixtureAdapter):

            def exchange(adapter, envelope):
                test.order()
                return super().exchange(envelope)
        adapters = {owner: FixtureAdapter({'fingerprint': original['fingerprint'], 'decision': 'PREPARED', 'preserves_relationships': True, 'notes': 'Fixture'}) for owner in MERGE_OWNERS}
        adapters['Integrations'] = MutatingFixture({'fingerprint': original['fingerprint'], 'decision': 'PREPARED', 'preserves_relationships': True, 'notes': 'Fixture changed local data'})
        with self.assertRaises(DomainError) as error:
            dry_run(self.business, self.manager, candidate.pk, adapters)
        self.assertEqual(error.exception.code, 'STALE_PLAN')

class OwnerUIConnectionTests(DomainFixture):

    def test_configured_owner_adapter_result_is_labelled_and_visible_in_replaceable_ui(self):
        from django.test import override_settings
        client = Client()
        client.force_login(self.manager)
        with override_settings(BIZORA_DOMAIN_ADAPTERS={'Monitoring': 'app.test_integration_readiness.ConfiguredMonitoringFixture'}, BIZORA_ALLOW_FIXTURE_ADAPTERS=True):
            response = client.get(reverse('ops-detail', args=[self.business.pk, 'customers', self.customer.pk]))
            self.assertContains(response, 'FIXTURE_ONLY')
            self.assertContains(response, 'simulated')

class FinancialAndActionUITests(DomainFixture):

    def test_financial_chronology_has_scoped_links_and_pagination(self):
        payment = self.payment()
        self.ingest('refunds', {'payment': payment.pk, 'external_refund_id': 'part', 'amount': '2'})
        client = Client()
        client.force_login(self.manager)
        url = reverse('ops-financial-timeline', args=[self.business.pk])
        response = client.get(url, {'page_size': 1})
        self.assertContains(response, 'Next page')
        self.assertContains(client.get(url), 'PAYMENT')
        self.assertContains(client.get(url), 'REFUND')
        self.assertEqual(client.get(url, {'customer': self.other_customer.pk}).status_code, 400)
        client.force_login(self.stranger)
        self.assertEqual(client.get(url).status_code, 404)

    def test_manager_reviews_actual_evidence_backed_action_without_execution(self):
        recommendation = create(m.AiRecommendation, business=self.business, recommendation_type='MARKETING', title='Owner proposal', description='Stored authoritative proposal', generated_at=timezone.now())
        fact = create(m.BusinessFact, business=self.business, fact_type='OBSERVED', statement='Verified fixture evidence', detected_at=timezone.now())
        create(m.AiRecommendationEvidence, ai_recommendation=recommendation, business_fact=fact, evidence_type='FACT')
        action = create(m.AiAction, business=self.business, ai_recommendation=recommendation, action_type='REVIEW_CAMPAIGN')
        client = Client()
        client.force_login(self.manager)
        self.assertContains(client.get(reverse('ops-section', args=[self.business.pk, 'marketing'])), 'REVIEW_CAMPAIGN')
        self.assertEqual(client.get(reverse('ops-detail', args=[self.business.pk, 'actions', action.pk])).status_code, 200)
        command = reverse('ops-command', args=[self.business.pk, 'actions', action.pk, 'review-action'])
        self.assertEqual(client.post(command, {'decision': 'APPROVED', 'reason': 'Reviewed current evidence'}).status_code, 302)
        action.refresh_from_db()
        self.assertEqual(action.status, 'APPROVED')
        self.assertIsNone(action.executed_at)
        client.force_login(self.operator)
        self.assertEqual(client.get(reverse('ops-detail', args=[self.business.pk, 'actions', action.pk])).status_code, 404)

    def test_observed_website_error_signal_and_product_event_filter_are_visible(self):
        visitor = self.ingest('visitors', {'visitor_key': 'error-visitor'})
        session = self.ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 'error-session', 'started_at': timezone.now().isoformat()})
        self.ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'ERROR', 'properties': {'error_code': 'CHECKOUT_500', 'message': 'Observed checkout failure'}, 'occurred_at': timezone.now().isoformat()})
        client = Client()
        client.force_login(self.manager)
        self.assertContains(client.get(reverse('ops-section', args=[self.business.pk, 'website'])), 'CHECKOUT_500')

class IdentifierWhitespaceTests(DomainFixture):

    def test_sku_review_cannot_be_bypassed_by_whitespace(self):
        self.assertEqual(assess_product(self.business, self.manager, {'sku': ' TEA '})['decision'], 'REVIEW')
        with self.assertRaises(DomainError):
            self.ingest('products', {'name': 'Duplicate', 'sku': ' TEA '})
        variant = self.ingest('variants', {'product': self.product.pk, 'sku': ' SMALL ', 'name': 'Small'})
        self.assertEqual(variant.sku, 'SMALL')
        with self.assertRaises(DomainError):
            self.ingest('product-references', {'product': self.product.pk, 'external_product_id': 'remote', 'external_variant_id': '  '}, connection_id=self.connection.pk)
        first, _ = identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', 'PSID', 'UserID', external_id=' 123 ')
        replay, _ = identity.register(self.business, self.manager, self.connection.pk, 'CUSTOMER', 'PSID', 'UserID', external_id='123')
        self.assertEqual(first.pk, replay.pk)


class MediaReplyUITests(DomainFixture):
    def test_media_reference_is_pending_replay_safe_and_validated(self):
        conversation=self.conversation()
        client=Client();client.force_login(self.manager)
        url=reverse('ops-command',args=[self.business.pk,'conversations',conversation.pk,'media-reply'])
        payload={'attachment_type':'IMAGE','url':'https://example.test/photo.png','mime_type':'image/png','file_name':'photo.png','submission_id':'2'*32}
        for _ in range(2): self.assertEqual(client.post(url,payload).status_code,302)
        message=m.Message.objects.get()
        self.assertEqual(message.delivery_status,'PENDING')
        self.assertEqual(m.MessageAttachment.objects.count(),1)
        self.assertEqual(message.message_type,'IMAGE')
        response=client.get(reverse('ops-detail',args=[self.business.pk,'messages',message.pk]))
        self.assertContains(response,'Open stored file reference')
        self.assertEqual(client.post(url,{**payload,'url':'javascript:alert(1)','submission_id':'3'*32}).status_code,400)
        self.assertEqual(m.Message.objects.count(),1)


class ProductRelationshipContextTests(DomainFixture):
    def test_product_context_includes_owned_current_verified_nonpurchase_customer_relations(self):
        from app.domains import projections
        from datetime import timedelta
        linked=create(m.Customer,business=self.business,display_name='Verified non-purchase relationship')
        future=create(m.Customer,business=self.business,display_name='Future relationship')
        for customer,extra in [(linked,{}),(future,{'valid_from':timezone.now()+timedelta(days=1)}),(self.other_customer,{})]:
            create(m.BusinessRelationship,business=self.business,source_entity_type='PRODUCT',source_entity_id=self.product.pk,
                target_entity_type='CUSTOMER',target_entity_id=customer.pk,relationship_type='HAS_CUSTOMER',**extra)
        result=projections.detail(self.business,'products',self.product.pk)
        self.assertEqual([x['id'] for x in result['customers']['results']],[linked.pk])
        client=Client();client.force_login(self.manager)
        self.assertContains(client.get(reverse('ops-detail',args=[self.business.pk,'products',self.product.pk])),linked.display_name)
