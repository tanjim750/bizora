"""Deterministic continuation demo using the existing isolated domain demo business."""
from datetime import datetime, timezone as dt_timezone
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from app import models as m
from app.domains import data, identity, operations, projections


class Command(BaseCommand):
    help = 'Demonstrate verified matching, login journey recovery and support context on the existing local demo.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        call_command('demo_domains', username=options['username'], stdout=self.stdout)
        user = get_user_model().objects.get(username=options['username'])
        business = m.Business.objects.get(slug='bizora-domains-demo')
        connection = m.IntegrationConnection.objects.get(business=business, integration_source__key='bizora-domain-demo', is_mock=True)
        customer = m.CustomerExternalReference.objects.get(integration_connection=connection, external_customer_id='52').customer
        contacts = customer.customercontact_set.filter(contact_type__in=['EMAIL', 'PHONE'])
        ids = []
        for contact in contacts:
            identity.verify_contact(business, user, contact.pk, 'Simulated identity evidence in isolated demo')
            external, conflict = identity.register(business, user, connection.pk, 'CUSTOMER', contact.contact_type,
                        contact.normalized_value, external_id='completion-' + contact.contact_type, verified=True)
            if conflict:
                raise RuntimeError('Demo source identity changed; review the isolated scenario.')
            ids.append(external.pk)
        canonical, conflict = identity.resolve_many(business, user, ids)
        if conflict or canonical is None:
            raise RuntimeError('Deterministic demo matching did not resolve as expected.')
        anchor = datetime(2026, 10, 24, 9, tzinfo=dt_timezone.utc)

        def ingest(name, payload, key):
            return data.ingest(business, user, name, payload, 'completion-' + key, connection_id=connection.pk)[0]

        visitor = ingest('visitors', {'visitor_key': 'completion-visitor'}, 'visitor')
        session = ingest('sessions', {'visitor': visitor.pk, 'external_session_id': 'completion-session', 'started_at': anchor.isoformat()}, 'session')
        email = customer.customercontact_set.get(contact_type='EMAIL')
        proof = m.ExternalIdentity.objects.get(pk=next(pk for pk in ids if m.ExternalIdentity.objects.get(pk=pk).identity_type == 'EMAIL'))
        event = ingest('website-events', {'visitor': visitor.pk, 'session': session.pk, 'event_type': 'LOGIN',
                       'occurred_at': anchor.isoformat(), 'properties': {'identity_value': email.normalized_value}}, 'login')
        identity.link_anonymous(business, user, visitor.pk, event.pk, proof.pk)
        conversation = ingest('conversations', {'external_conversation_id': 'completion-support', 'channel': 'WHATSAPP', 'customer': customer.pk}, 'conversation')
        operations.set_priority(business, user, conversation.pk, 'URGENT', 'Isolated demo priority review')
        context = projections.support_context(business, conversation.pk)
        self.stdout.write(self.style.SUCCESS(f'Completion demo verified: identity={canonical.pk}; visitor={visitor.pk}; support={conversation.pk}'))
        self.stdout.write(f'/api/businesses/{business.pk}/conversations/{conversation.pk}/context/')
        self.stdout.write(f'/api/businesses/{business.pk}/visitors/{visitor.pk}/journey/')
        self.stdout.write('Suggested reply: ' + context['suggested_reply']['status'] + '; policies: ' + context['policy_context']['status'])
