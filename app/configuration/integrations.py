"""Integration setup owns settings; adapters own network access and processing."""
import os
import re

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from app.models import Business, ConfigurationRecord, IntegrationConnection, IntegrationSource
from app.observability.access import require_access
from app.overview.configuration import StrictSerializer
from .schemas import JsonObject
from .services import CONTROL, merge, record_data, safe_settings, save_record


CAPABILITIES = {
    'COMMERCE': {'entities': ['PRODUCT', 'CUSTOMER', 'ORDER', 'PAYMENT', 'REFUND'],
        'scopes': ['READ_PRODUCTS', 'READ_CUSTOMERS', 'READ_ORDERS', 'READ_PAYMENTS']},
    'MARKETING': {'entities': ['CAMPAIGN', 'CAMPAIGN_METRIC', 'CONVERSION'], 'scopes': ['READ_CAMPAIGNS', 'READ_METRICS']},
    'ANALYTICS': {'entities': ['WEBSITE_VISITOR', 'WEBSITE_SESSION', 'WEBSITE_EVENT'], 'scopes': ['READ_ANALYTICS']},
    'COMMUNICATION': {'entities': ['CONVERSATION', 'MESSAGE', 'CUSTOMER'], 'scopes': ['READ_CONVERSATIONS', 'SEND_MESSAGES']},
    'COURIER': {'entities': ['SHIPMENT', 'SHIPMENT_EVENT'], 'scopes': ['READ_SHIPMENTS', 'CREATE_SHIPMENTS']},
    'CALLING': {'entities': ['CALL', 'CALL_EVENT', 'TRANSCRIPT'], 'scopes': ['READ_CALLS', 'INITIATE_CALLS']},
}
ENTITY_SCOPES = {'PRODUCT': 'READ_PRODUCTS', 'CUSTOMER': 'READ_CUSTOMERS', 'ORDER': 'READ_ORDERS',
    'PAYMENT': 'READ_PAYMENTS', 'REFUND': 'READ_PAYMENTS', 'CAMPAIGN': 'READ_CAMPAIGNS',
    'CAMPAIGN_METRIC': 'READ_METRICS', 'CONVERSION': 'READ_METRICS', 'WEBSITE_VISITOR': 'READ_ANALYTICS',
    'WEBSITE_SESSION': 'READ_ANALYTICS', 'WEBSITE_EVENT': 'READ_ANALYTICS', 'CONVERSATION': 'READ_CONVERSATIONS',
    'MESSAGE': 'READ_CONVERSATIONS', 'SHIPMENT': 'READ_SHIPMENTS', 'SHIPMENT_EVENT': 'READ_SHIPMENTS',
    'CALL': 'READ_CALLS', 'CALL_EVENT': 'READ_CALLS', 'TRANSCRIPT': 'READ_CALLS'}


def capabilities(source):
    category = {'ECOMMERCE': 'COMMERCE', 'COURIER_DELIVERY': 'COURIER', 'MESSAGING': 'COMMUNICATION', 'SUPPORT': 'COMMUNICATION'}.get(source.category.upper(), source.category.upper())
    return CAPABILITIES.get(category, {'entities': [], 'scopes': []})


class Sync(StrictSerializer):
    mode = serializers.ChoiceField(choices=['FULL', 'INCREMENTAL', 'SCHEDULED', 'MANUAL'])
    interval_seconds = serializers.IntegerField(min_value=60, max_value=2592000)


class Webhooks(StrictSerializer):
    enabled = serializers.BooleanField()
    events = serializers.ListField(child=serializers.RegexField(r'^[a-zA-Z0-9_.:-]{1,100}$'), max_length=50)
    endpoint = serializers.URLField(required=False, allow_blank=True, max_length=1000)

    def validate(self, data):
        if data['enabled'] and (not data['events'] or not data.get('endpoint', '').startswith('https://')):
            raise serializers.ValidationError('Enabled webhooks require subscriptions and an HTTPS endpoint.')
        return data


class Mock(StrictSerializer):
    connection_outcome = serializers.ChoiceField(choices=['SUCCESS', 'DEGRADED', 'ERROR', 'AUTH_ERROR', 'EXPIRED'])
    processing_outcome = serializers.ChoiceField(choices=['SUCCESS', 'TIMEOUT'], required=False)
    product_name_field = serializers.RegexField(r'^[a-zA-Z_][a-zA-Z0-9_]{0,99}$')


class IntegrationSchema(StrictSerializer):
    connection_id = serializers.IntegerField(min_value=1)
    provider_id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=150)
    enabled = serializers.BooleanField()
    is_mock = serializers.BooleanField()
    entities = serializers.ListField(child=serializers.CharField(max_length=100), max_length=20)
    scopes = serializers.ListField(child=serializers.CharField(max_length=100), max_length=20)
    sync = Sync()
    webhooks = Webhooks()
    provider_settings = JsonObject()
    credentials = serializers.DictField(child=serializers.CharField(max_length=200))
    mock = Mock()

    def validate(self, data):
        source = IntegrationSource.objects.filter(pk=data['provider_id'], is_active=True).first()
        if not source:
            raise serializers.ValidationError('Provider is unavailable.')
        supported = capabilities(source)
        if not supported['entities'] or set(data['entities'])-set(supported['entities']) or set(data['scopes'])-set(supported['scopes']):
            raise serializers.ValidationError('Provider does not support the selected entities or scopes.')
        for entity in data['entities']:
            required = 'READ_CONVERSATIONS' if entity == 'CUSTOMER' and source.category.upper() in {'COMMUNICATION', 'SUPPORT', 'MESSAGING'} else ENTITY_SCOPES[entity]
            if required not in data['scopes']:
                raise serializers.ValidationError('Selected entities require their corresponding read scope.')
        allowed = {'api_key', 'secret_key', 'access_token', 'refresh_token', 'client_id', 'client_secret', 'webhook_secret'}
        pattern = rf'env:BIZORA_BUSINESS_{self.context["business_id"]}_[A-Z][A-Z0-9_]{{0,100}}'
        if set(data['credentials'])-allowed or any(not re.fullmatch(pattern, value) for value in data['credentials'].values()):
            raise serializers.ValidationError('Credentials must be business-scoped secret references, never secret values.')
        if not data['is_mock'] and data['enabled'] and not data['credentials']:
            raise serializers.ValidationError('Live connections require configured credential references.')
        if not data['is_mock'] and data['webhooks']['enabled'] and 'webhook_secret' not in data['credentials']:
            raise serializers.ValidationError('Live webhook configuration requires a signing-secret reference.')
        return data


def connection_settings(row):
    config = row.config if isinstance(row.config, dict) else {}
    supported = capabilities(row.integration_source)
    return {'connection_id': row.pk, 'provider_id': row.integration_source_id, 'name': row.name or row.integration_source.name,
        'enabled': row.status != 'DISABLED', 'is_mock': row.is_mock,
        'entities': config.get('entities', supported['entities']), 'scopes': config.get('scopes', supported['scopes']),
        'sync': config.get('sync', {'mode': 'MANUAL', 'interval_seconds': 900}),
        'webhooks': config.get('webhooks', {'enabled': False, 'events': [], 'endpoint': ''}),
        'provider_settings': config.get('provider_settings', {}),
        'credentials': config.get('credentials', {}) if isinstance(config.get('credentials', {}), dict) else {},
        'mock': merge({'connection_outcome': 'SUCCESS', 'product_name_field': 'name'}, config.get('mock', {}))}


NOT_LOADED = object()


def connection_data(row, record=NOT_LOADED):
    if record is NOT_LOADED:
        record = ConfigurationRecord.objects.filter(business_id=row.business_id, kind='INTEGRATION', key=str(row.pk)).first()
    data = record_data(record) if record else {'version': 0, 'kind': 'INTEGRATION', 'key': str(row.pk),
        'settings': safe_settings('INTEGRATION', connection_settings(row)), 'status': 'ACTIVE' if row.status != 'DISABLED' else 'DISABLED'}
    return {**data, 'id': row.pk, 'observability': f'/api/businesses/{row.business_id}/observability/connections/{row.pk}/'}


@transaction.atomic
def save_connection(business_id, actor, body, now, pk=None):
    require_access(actor, business_id, manage=True)
    Business.objects.select_for_update(no_key=True).get(pk=business_id)
    if not isinstance(body, dict) or set(body) & (CONTROL-{'version', 'reason'}):
        raise ValidationError('Connection setup accepts settings, version, and reason.')
    if pk is None:
        provider_id = body.get('provider_id')
        if isinstance(provider_id, bool) or not isinstance(provider_id, int):
            raise ValidationError('Provider ID is required.')
        source = IntegrationSource.objects.filter(pk=provider_id, is_active=True).first()
        if not source:
            raise ValidationError('Provider is unavailable.')
        row = IntegrationConnection.objects.create(business_id=business_id, integration_source=source,
            name=source.name, is_mock=True, created_at=now, updated_at=now)
    else:
        row = IntegrationConnection.objects.select_related('integration_source').filter(business_id=business_id, pk=pk).first()
        if row is None:
            raise NotFound('Connection not found.')
        if 'provider_id' in body and body['provider_id'] != row.integration_source_id:
            raise ValidationError('Create another connection to change providers.')
    if 'connection_id' in body and body['connection_id'] != row.pk:
        raise ValidationError('Connection identifier cannot be changed.')
    changes = merge(connection_settings(row), body)
    existing = ConfigurationRecord.objects.filter(business_id=business_id, kind='INTEGRATION', key=str(row.pk)).exists()
    changes['status'] = 'ACTIVE' if changes['enabled'] else 'DISABLED'
    record = save_record(business_id, 'INTEGRATION', str(row.pk), changes, actor,
        now=now, create=not existing, schema=IntegrationSchema)
    data = record.data
    row.name, row.is_mock = data['name'], data['is_mock']
    row.config = {**(row.config if isinstance(row.config, dict) else {}),
                  **{k: v for k, v in data.items() if k not in {'connection_id', 'provider_id', 'name', 'is_mock', 'enabled'}}}
    if not data['enabled']:
        row.status = 'DISABLED'
    elif row.status == 'DISABLED':
        row.status = 'CONNECTED'
    row.updated_at = now
    row.save(update_fields=['name', 'is_mock', 'status', 'config', 'updated_at'])
    return row


class CredentialUnavailable(Exception):
    pass


def require_processing_scope(connection, entity_type, webhook=None):
    """Enforce explicit selections; legacy connections without them keep prior behavior."""
    from django.core.exceptions import ValidationError as DomainValidationError
    config = connection.config if isinstance(connection.config, dict) else {}
    if 'entities' in config and (not isinstance(config['entities'], list) or entity_type not in config['entities']):
        raise DomainValidationError('Entity processing is disabled by integration configuration.')
    if 'scopes' in config:
        required = ENTITY_SCOPES.get(entity_type)
        if entity_type == 'CUSTOMER' and connection.integration_source.category.upper() in {'COMMUNICATION', 'SUPPORT', 'MESSAGING'}:
            required = 'READ_CONVERSATIONS'
        if required is None or required not in config['scopes']:
            raise DomainValidationError('Entity processing is not authorized by the integration scopes.')
    if webhook is not None and 'webhooks' in config:
        settings = config['webhooks']
        if not isinstance(settings, dict) or not settings.get('enabled') or webhook.event_type not in settings.get('events', []):
            raise DomainValidationError('Webhook subscription is disabled by integration configuration.')


def resolve_credentials(connection):
    """Trusted adapter boundary only. There is deliberately no HTTP read endpoint."""
    record = ConfigurationRecord.objects.filter(business_id=connection.business_id, kind='INTEGRATION', key=str(connection.pk)).first()
    if not record or not record.data['enabled']:
        raise CredentialUnavailable('Configured credentials are unavailable.')
    prefix = f'env:BIZORA_BUSINESS_{connection.business_id}_'
    resolved = {}
    for field, reference in record.data['credentials'].items():
        if not isinstance(reference, str) or not reference.startswith(prefix):
            raise CredentialUnavailable('Configured credentials are unavailable.')
        value = os.environ.get(reference[4:])
        if not value:
            raise CredentialUnavailable('Configured credentials are unavailable.')
        resolved[field] = value
    return resolved
