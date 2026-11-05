"""Explicit simulation seam, not a live Integrations implementation.

A provider adapter can implement the same canonical envelope. No network calls,
credentials, webhook reception or provider success claims are made here.
"""
from .common import require
from .data import ingest


class MockCommerceTransport:
    def __init__(self, business, actor, connection):
        require(connection.business_id == business.pk and connection.is_mock,
                'INVALID_SOURCE', 'Mock transport requires this business\'s simulated connection.')
        self.business, self.actor, self.connection = business, actor, connection

    def receive(self, event_id, entity, payload, occurred_at=None):
        require(isinstance(payload, dict) and payload.get('id') is not None, 'INVALID_IDENTIFIER', 'Provider record ID is required.')
        external = str(payload['id'])
        if entity == 'product':
            canonical = {'name': payload.get('name'), 'sku': payload.get('sku'),
                         'price': payload.get('regular_price'),
                         'external_reference': {'external_product_id': external}, 'source_metadata': payload}
            name = 'products'
        elif entity == 'customer':
            contacts = []
            if payload.get('email'):
                contacts.append({'contact_type': 'EMAIL', 'value': payload['email']})
            if payload.get('billing', {}).get('phone'):
                contacts.append({'contact_type': 'PHONE', 'value': payload['billing']['phone']})
            canonical = {'first_name': payload.get('first_name'), 'last_name': payload.get('last_name'),
                         'contacts': contacts, 'external_reference': {'external_customer_id': external}, 'source_metadata': payload}
            name = 'customers'
        else:
            require(False, 'UNSUPPORTED_MOCK_EVENT', 'Only documented mock product/customer adapter mappings are registered.')
        return ingest(self.business, self.actor, name, canonical, event_id, occurred_at, self.connection.pk)


class MockMessageTransport:
    """Simulated outbound transport only. Never claims a real provider accepted a message."""
    def send(self, business, actor, message_id):
        from .common import related, authorize
        from .data import transition
        from app import models as m
        authorize(actor, business, write=True)
        message = related(m.Message, message_id, business)
        require(message.integration_connection and message.integration_connection.is_mock,
                'PROVIDER_UNAVAILABLE', 'Live messaging must use the Integrations contract.')
        require(message.direction == 'OUTGOING', 'INVALID_DIRECTION', 'Only outgoing messages can be sent.')
        transition(business, actor, 'messages', message.pk, 'SENT', 'Mock transport accepted message')
        return {'simulated': True, 'status': 'SENT', 'message_id': message.pk,
                'provider_reference': f'mock-message-{message.pk}'}


class MockCanonicalTransport:
    """Versioned fixture ingress for all canonical resources; never a provider webhook."""
    version = 'bizora.ingest.v1'

    def __init__(self,business,actor,connection):
        from .common import authorize, ensure_owned
        authorize(actor,business,write=True)
        ensure_owned(connection,business)
        require(connection.is_mock,'INVALID_SOURCE','Fixture intake requires an explicitly simulated source.')
        self.business,self.actor,self.connection=business,actor,connection

    def receive(self,envelope):
        from django.utils.dateparse import parse_datetime
        from .projections import serialize
        require(isinstance(envelope,dict) and set(envelope)<={'version','business_id','connection_id','event_id','resource','data','occurred_at'},
            'INVALID_CONTRACT','Unsupported canonical fixture envelope.')
        require(envelope.get('version')==self.version and type(envelope.get('business_id')) is int and envelope['business_id']==self.business.pk
            and type(envelope.get('connection_id')) is int and envelope['connection_id']==self.connection.pk,
            'INVALID_SOURCE','Fixture envelope scope/version differs.')
        require(all(key in envelope for key in ('event_id','resource','data')),'INVALID_CONTRACT','Event, resource and data are required.')
        require(isinstance(envelope['resource'],str) and isinstance(envelope['data'],dict),'INVALID_CONTRACT','Resource must be text and data must be an object.')
        occurred=envelope.get('occurred_at')
        if occurred is not None:
            occurred=parse_datetime(occurred) if isinstance(occurred,str) else None
            require(occurred is not None,'INVALID_TIME','Use an offset-aware ISO timestamp.')
        obj,created=ingest(self.business,self.actor,envelope['resource'],envelope['data'],envelope['event_id'],occurred,self.connection.pk)
        return {'version':self.version,'simulated':True,'created':created,'record':serialize(obj)}
