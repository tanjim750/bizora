"""Reusable canonical lookups and chronological operational queries, never BI calculations."""
from django.db.models import Q
from app import models as m
from .common import require, related, normalize_contact
from .registry import scoped


def lookup(name, business, queryset, params):
    require('contact_type' not in params or name != 'customers' or 'contact' in params, 'INVALID_FILTER', 'Customer contact type requires a contact value.')
    if 'contact' in params:
        require(name == 'customers', 'INVALID_FILTER', 'Contact lookup applies to customers.')
        kind = params.get('contact_type', 'EMAIL').upper()
        normalized = normalize_contact(kind, params['contact'])
        contacts = m.CustomerContact.objects.filter(customer__business=business, contact_type=kind, normalized_value=normalized)
        queryset = queryset.filter(pk__in=contacts.values('customer_id'))
    if name == 'customers' and 'tag' in params:
        queryset = queryset.filter(customertag__tag=params['tag'].upper()).distinct()
    if 'external_id' in params or 'connection_id' in params:
        require('external_id' in params and 'connection_id' in params, 'INVALID_FILTER', 'External lookup requires both source connection and external ID.')
        connection = related(m.IntegrationConnection, int(params['connection_id']), business)
        if name == 'customers':
            queryset = queryset.filter(customerexternalreference__integration_connection=connection,
                                      customerexternalreference__external_customer_id=params['external_id'])
        elif name == 'products':
            queryset = queryset.filter(productexternalreference__integration_connection=connection,
                                      productexternalreference__external_product_id=params['external_id']).distinct()
        else:
            from .registry import resource
            field = resource(name)[2]
            require(field and 'integration_connection' in {f.name for f in queryset.model._meta.fields}, 'INVALID_FILTER', 'Source lookup is unsupported for this resource.')
            queryset = queryset.filter(integration_connection=connection, **{field: params['external_id']})
    return queryset


def conversation_search(queryset, business, term):
    messages = scoped('messages', business).filter(content__icontains=term)
    return queryset.filter(Q(subject__icontains=term) | Q(customer__display_name__icontains=term) |
                           Q(pk__in=messages.values('conversation_id'))).distinct()
