import json
from django import template
from django.urls import reverse
from django.utils.html import format_html
from uuid import uuid4
register = template.Library()

@register.filter
def display(value):
    if value is None:
        return '—'
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, default=str, ensure_ascii=False)
    return str(value)

@register.simple_tag
def submission_id():
    return uuid4().hex

@register.filter
def is_mapping(value):
    return isinstance(value, dict)

@register.filter
def is_sequence(value):
    return isinstance(value, list)

@register.simple_tag
def record_link(business, resource, row):
    mapping = {'product-images': 'product-images', 'external_references': 'product-references', 'history': None, 'assignments': None, 'identity_history': None, 'merge_candidates': 'merge-candidates', 'callback_requests': 'callbacks', 'events': 'website-events', 'reported_metrics': 'campaign-metrics', 'reported_conversions': 'conversions'}
    resource = mapping.get(resource, resource)
    if resource == 'financial-timeline':
        resource = {'PAYMENT': 'payments', 'REFUND': 'refunds'}.get(row.get('entity_kind'))
    if not resource or not row.get('id'):
        return ''
    from app.domains.registry import RESOURCES
    if resource not in RESOURCES and resource not in ('conflicts', 'merge-candidates', 'actions'):
        return ''
    return format_html('<a href="{}">Open #{}</a>', reverse('ops-detail', kwargs={'business_id': business.pk, 'name': resource, 'pk': row['id']}), row['id'])

@register.simple_tag
def relation_link(business, key, value):
    names = {'customer': 'customers', 'order': 'orders', 'product': 'products', 'product_variant': 'variants', 'payment': 'payments', 'conversation': 'conversations', 'campaign': 'campaigns', 'session': 'sessions', 'visitor': 'visitors', 'shipment': 'shipments', 'call': 'calls'}
    if business and key in names and (type(value) is int) and (value > 0):
        return format_html('<a href="{}">{} #{}</a>', reverse('ops-detail', kwargs={'business_id': business.pk, 'name': names[key], 'pk': value}), key, value)
    return ''


@register.simple_tag
def reference_link(key,value):
    if key!='url' or not isinstance(value,str): return ''
    from django.core.validators import URLValidator
    from django.core.exceptions import ValidationError
    from urllib.parse import urlsplit
    try:
        URLValidator(schemes=['https','http'])(value)
        parsed=urlsplit(value)
        if parsed.username or parsed.password: return ''
    except (ValidationError,ValueError): return ''
    return format_html('<a href="{}" rel="noreferrer noopener">Open stored file reference</a>',value)
