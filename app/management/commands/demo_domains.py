"""Repeatable local demonstration through real canonical services."""
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from app import models as m
from app.domains.common import create, DomainError, authorize
from app.domains.data import ingest
from app.domains.mock_transport import MockCommerceTransport
from app.domains import identity, operations


class Command(BaseCommand):
    help = 'Run an idempotent simulated domain demo in an isolated database; requires an existing local username.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        if db['ENGINE'] != 'django.db.backends.sqlite3' or Path(str(db['NAME'])).resolve() == (settings.BASE_DIR / 'db.sqlite3').resolve():
            raise CommandError('Demo requires an isolated local SQLite database.')
        user = get_user_model().objects.filter(username=options['username'], is_active=True).first()
        if user is None:
            raise CommandError('Create a local user first with createsuperuser.')
        business = m.Business.objects.filter(slug='bizora-domains-demo').first()
        if business:
            try:
                authorize(user, business, manager=True)
            except DomainError as exc:
                raise CommandError(exc.message)
        else:
            business = create(m.Business, name='Bizora Domains Demo', slug='bizora-domains-demo')
            m.BusinessMembership.objects.create(business=business, user=user, role='OWNER')
        source = m.IntegrationSource.objects.filter(key='bizora-domain-demo').first()
        if source is None:
            source = create(m.IntegrationSource, key='bizora-domain-demo', name='Simulated commerce', category='COMMERCE')
        connection = m.IntegrationConnection.objects.filter(business=business, integration_source=source, is_mock=True).first()
        if connection is None:
            connection = create(m.IntegrationConnection, business=business, integration_source=source, is_mock=True)
        adapter = MockCommerceTransport(business, user, connection)
        customer, _ = adapter.receive('demo-customer', 'customer', {'id': 52, 'first_name': 'Demo', 'last_name': 'Buyer', 'email': 'demo@example.test', 'billing': {'phone': '01712345678'}})
        product, _ = adapter.receive('demo-product', 'product', {'id': 101, 'name': 'Demo Tea', 'sku': 'DEMO-TEA', 'regular_price': '125.00'})

        def receive(name, key, payload):
            return ingest(business, user, name, payload, 'demo-' + key, connection_id=connection.pk)[0]

        order = receive('orders', 'order', {'external_order_id': '1001', 'customer': customer.pk,
                        'items': [{'product': product.pk, 'quantity': 2, 'unit_price': '125.00'}]})
        payment = receive('payments', 'payment', {'external_payment_id': 'p1001', 'order': order.pk,
                          'customer': customer.pk, 'amount': '250.00', 'status': 'PAID', 'payment_method': 'COD'})
        conversation = receive('conversations', 'conversation', {'external_conversation_id': 'conv52', 'channel': 'WHATSAPP', 'customer': customer.pk})
        receive('messages', 'message', {'external_message_id': 'msg52', 'conversation': conversation.pk,
                'customer': customer.pk, 'direction': 'INCOMING', 'sender_type': 'CUSTOMER', 'content': 'Where is my order?'})
        operations.assign(business, user, conversation.pk, 'AGENT', user.pk, 'Demo assignment')
        operations.handover(business, user, conversation.pk, 'HUMAN', user.pk, 'Customer asks for an agent', 'Order status inquiry')
        shipment = receive('shipments', 'shipment', {'external_shipment_id': 'ship1001', 'order': order.pk,
                           'customer': customer.pk, 'provider': 'MOCK', 'cod_amount': '250.00'})
        ext, _ = identity.register(business, user, connection.pk, 'CUSTOMER', 'EXTERNAL_CUSTOMER_ID', '52', external_id='52')
        link, conflict = identity.resolve(business, user, ext.pk)
        if conflict:
            raise CommandError('Unexpected demo identity conflict.')
        self.stdout.write(self.style.SUCCESS(f'Demo ready: business={business.pk}, customer={customer.pk}, order={order.pk}, payment={payment.pk}, shipment={shipment.pk}, identity_link={link.pk}'))
        self.stdout.write(f'/api/businesses/{business.pk}/customers/{customer.pk}/360/')
        self.stdout.write('Provider execution, AI answers and BI attribution remain explicitly unavailable.')
