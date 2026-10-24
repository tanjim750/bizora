"""Transactional canonical intake. Transport, signatures and provider execution live outside this module."""
import hashlib
import json
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from app import models as m
from .common import DomainError, require, money, normalize_contact, related, create, audit, authorize, validate
from .registry import resource, scoped, NESTED, READ_ONLY
from .states import TRANSITIONS, ALIASES


def _prepare(model, business, raw, allowed_extra=()):
    require(isinstance(raw, dict), 'INVALID_DATA', 'Expected an object.')
    fields = {f.name: f for f in model._meta.fields if not f.primary_key and f.name not in READ_ONLY}
    require(not (set(raw) - set(fields) - set(allowed_extra)), 'UNKNOWN_FIELD',
            'Unknown or server-managed field: ' + ', '.join(sorted(set(raw) - set(fields) - set(allowed_extra))))
    data = {}
    for key, value in raw.items():
        if key not in fields:
            continue
        field = fields[key]
        if isinstance(field, models.ForeignKey):
            data[key] = related(field.related_model, value, business) if value is not None else None
        else:
            if value is not None and isinstance(field, (models.CharField, models.TextField)):
                require(isinstance(value, str) or key.startswith('external_') and isinstance(value, int) and not isinstance(value, bool), 'INVALID_DATA', key + ' must be text.')
            if value is not None and isinstance(field, models.BooleanField):
                require(isinstance(value, bool), 'INVALID_DATA', key + ' must be boolean.')
            try:
                data[key] = field.to_python(value)
            except (ValidationError, ValueError, TypeError):
                raise DomainError('INVALID_DATA', 'Invalid ' + key)
            if isinstance(field, models.IntegerField) and value is not None:
                require(not isinstance(value, bool) and str(value) == str(data[key]), 'INVALID_DATA', 'Integer field must contain an integer.')
            if isinstance(field, models.DecimalField) and value is not None:
                if key in ('confidence', 'ctr', 'cpc', 'cpm', 'roas'):
                    require(data[key].is_finite() and data[key] >= 0 and (key != 'confidence' or data[key] <= 1), 'INVALID_DATA', 'Invalid metric/confidence.')
                else:
                    data[key] = money(value)
            if isinstance(field, models.DateTimeField) and data[key] is not None:
                require(timezone.is_aware(data[key]), 'INVALID_TIME', 'Timestamps must include a UTC offset.')
    if any(f.name == 'business' for f in model._meta.fields):
        data['business'] = business
    return data


def _consistent(data):
    order, payment = data.get('order'), data.get('payment')
    if payment and order:
        require(payment.order_id == order.pk, 'INVALID_RELATION', 'Refund order must match payment.')
    if order and data.get('customer'):
        require(order.customer_id in (None, data['customer'].pk), 'INVALID_RELATION', 'Order customer differs.')
    if data.get('product_variant'):
        require(data.get('product') and data['product_variant'].product_id == data['product'].pk,
                'INVALID_RELATION', 'Variant does not belong to product.')
    if data.get('session'):
        require(not data.get('visitor') or data['session'].visitor_id == data['visitor'].pk,
                'INVALID_RELATION', 'Session visitor differs.')
        require(not data.get('customer') or data['session'].customer_id in (None, data['customer'].pk),
                'INVALID_RELATION', 'Session customer differs.')
    if data.get('conversation'):
        require(not data.get('customer') or data['conversation'].customer_id in (None, data['customer'].pk),
                'INVALID_RELATION', 'Conversation customer differs.')
    if data.get('ad_account') and data.get('integration_connection'):
        require(data['ad_account'].integration_connection_id == data['integration_connection'].pk,
                'INVALID_RELATION', 'Campaign account belongs to another connection.')


def _status(name, value):
    value = str(value).upper()
    value = ALIASES.get(name, {}).get(value, value)
    require(value in TRANSITIONS.get(name, {}), 'INVALID_STATUS', 'Unsupported canonical status.')
    return value


def _timeline(obj, kind):
    customer = getattr(obj, 'customer', None)
    if customer is None and isinstance(obj, m.Refund):
        customer = obj.payment.customer
    if customer:
        event_at = timezone.now()
        if kind.endswith('_CREATED'):
            event_at = next((getattr(obj, field, None) for field in
                    ('occurred_at', 'converted_at', 'ordered_at', 'paid_at', 'started_at', 'created_at')
                    if getattr(obj, field, None) is not None), event_at)
        create(m.CustomerTimelineEvent, customer=customer, event_type=kind,
               entity_type=obj.__class__.__name__, entity_id=obj.pk, event_at=event_at, title=kind)


@transaction.atomic
def ingest(business, actor, name, raw, key, occurred_at=None, connection_id=None):
    """A canonical event has an immutable idempotency key scoped to connection and business."""
    authorize(actor, business, write=True)
    model, _, external_field = resource(name)
    # Serialize all writes for one business on PostgreSQL. Constraints remain the final guard.
    m.Business.objects.select_for_update().get(pk=business.pk)
    require(isinstance(key, str) and 0 < len(key) <= 180, 'INVALID_KEY', 'Idempotency key is required (max 180).')
    connection = related(m.IntegrationConnection, connection_id, business) if connection_id else None
    require(connection is None or connection.status == 'CONNECTED', 'CONNECTION_UNAVAILABLE', 'Connection is not connected.')
    receipt_key = f'{connection.pk if connection else "manual"}:{key}'
    digest = hashlib.sha256(json.dumps({'resource': name, 'data': raw, 'occurred_at': occurred_at},
                                      sort_keys=True, default=str).encode()).hexdigest()
    prior = m.ProcessingReceipt.objects.filter(business=business, key=receipt_key).first()
    if prior:
        require(prior.payload_hash == digest and prior.resource == name, 'IDEMPOTENCY_CONFLICT', 'Key was used for different input.')
        return scoped(name, business).get(pk=prior.entity_id), False
    occurred_at = occurred_at or timezone.now()
    require(timezone.is_aware(occurred_at), 'INVALID_TIME', 'Event time must include timezone.')
    require(isinstance(raw, dict), 'INVALID_DATA', 'Canonical payload must be an object.')
    for nested in NESTED.get(name, set()) & raw.keys():
        expected = dict if nested == 'external_reference' else list
        require(isinstance(raw[nested], expected), 'INVALID_DATA', nested + ' has an invalid structure.')
        if expected is list and nested != 'tags':
            require(all(isinstance(item, dict) for item in raw[nested]), 'INVALID_DATA', nested + ' entries must be objects.')
    data = _prepare(model, business, raw, NESTED.get(name, set()))
    if 'integration_connection' in data:
        require(connection is not None and data['integration_connection'] is not None and data['integration_connection'].pk == connection.pk,
                'INVALID_RELATION', 'Connection must be supplied in the event envelope.')
    if connection and any(f.name == 'integration_connection' for f in model._meta.fields):
        data['integration_connection'] = connection
    if external_field and external_field.startswith('external_'):
        require(isinstance(data.get(external_field), str) and data[external_field].strip(), 'INVALID_IDENTIFIER', 'External identifier is required.')
        data[external_field] = data[external_field].strip()
    if any(f.name == 'customer' for f in model._meta.fields):
        known_customers = {getattr(data[parent], 'customer_id', None) for parent in ('order', 'conversation', 'session', 'visitor') if data.get(parent)} - {None}
        if data.get('customer'):
            known_customers.add(data['customer'].pk)
        require(len(known_customers) <= 1, 'INVALID_RELATION', 'Related records have contradictory customers.')
        if known_customers and not data.get('customer'):
            data['customer'] = related(m.Customer, known_customers.pop(), business)
    for parent in {'messages': ('conversation',), 'campaign-metrics': ('campaign',), 'ad-sets': ('campaign',)}.get(name, ()):
        source = getattr(data.get(parent), 'integration_connection_id', None)
        require(not connection or not source or connection.pk == source, 'INVALID_RELATION', 'Parent and event source connections differ.')
    for enum in ('direction', 'sender_type', 'message_type', 'channel', 'contact_type', 'priority', 'customer_type'):
        if data.get(enum) is not None:
            data[enum] = data[enum].strip().upper().replace(' ', '_')
    _consistent(data)
    if any(f.name == 'currency' for f in model._meta.fields):
        currency_parent = data.get('payment') or (data.get('order') if name == 'payments' else None)
        data.setdefault('currency', currency_parent.currency if currency_parent else business.currency)
        require(isinstance(data['currency'], str) and len(data['currency']) == 3 and data['currency'].isascii() and data['currency'].isalpha(), 'INVALID_CURRENCY', 'Use a three-letter currency code.')
        data['currency'] = data['currency'].upper()
    if name == 'payments':
        if data.get('payment_method'):
            method = data['payment_method'].strip().upper().replace(' ', '_').replace('-', '_')
            method = {'CASH_ON_DELIVERY': 'COD', 'MOBILE_BANK': 'MOBILE_BANKING'}.get(method, method)
            require(method in ('CASH', 'COD', 'CARD', 'MOBILE_BANKING', 'BANK_TRANSFER', 'WALLET', 'OTHER'), 'INVALID_PAYMENT_METHOD', 'Use a supported canonical payment method or OTHER.')
            data['payment_method'] = method
        require(data.get('status', 'PENDING') not in ('PARTIALLY_REFUNDED', 'REFUNDED'), 'REFUND_LEDGER_REQUIRED', 'Refund states must be derived from canonical refunds.')
        require('amount' in data and data['amount'] > 0, 'INVALID_MONEY', 'Payment must be positive.')
        require(not data.get('order') or data['order'].currency == data['currency'], 'CURRENCY_MISMATCH', 'Order and payment currencies differ.')
    if 'event_type' in data:
        data['event_type'] = data['event_type'].upper()
    if name == 'website-events':
        props = data.get('properties')
        require(props is None or isinstance(props, dict), 'INVALID_DATA', 'Event properties must be an object.')
        if data.get('event_type') == 'PERFORMANCE':
            require(isinstance(props, dict) and any(k in props for k in ('latency_ms', 'loading_ms')), 'INVALID_SIGNAL', 'Performance events require latency_ms or loading_ms.')
            for metric in ('latency_ms', 'loading_ms'):
                if metric in props:
                    require(isinstance(props[metric], (int, float)) and not isinstance(props[metric], bool) and Decimal(str(props[metric])).is_finite() and props[metric] >= 0, 'INVALID_SIGNAL', 'Performance durations must be finite and nonnegative.')
        if data.get('event_type') == 'EXPERIENCE':
            require(isinstance(props, dict) and props.get('signal') in ('RAGE_CLICK', 'DEAD_CLICK', 'QUICK_BACK'), 'INVALID_SIGNAL', 'Experience events require a supported signal.')
    if name == 'callbacks':
        require(data.get('scheduled_at') is None or data['scheduled_at'] > timezone.now(), 'INVALID_TIME', 'Schedule callback in the future.')
    existing = None
    if name == 'products' and raw.get('external_reference'):
        ref = raw['external_reference']
        require(connection and ref.get('external_product_id') is not None and str(ref['external_product_id']).strip().strip(), 'INVALID_IDENTIFIER', 'Source and external product ID are required.')
        found = m.ProductExternalReference.objects.filter(integration_connection=connection,
                  external_product_id=str(ref['external_product_id']).strip(), external_variant_id__isnull=True).first()
        existing = found.product if found else None
    elif name == 'customers' and raw.get('external_reference'):
        ref = raw['external_reference']
        require(connection and ref.get('external_customer_id') is not None and str(ref['external_customer_id']).strip().strip(), 'INVALID_IDENTIFIER', 'Source and external customer ID are required.')
        found = m.CustomerExternalReference.objects.filter(integration_connection=connection,
                      external_customer_id=str(ref['external_customer_id']).strip()).first()
        existing = found.customer if found else None
    elif external_field and data.get(external_field):
        lookup = {external_field: data[external_field]}
        # Child identifiers are scoped to their owning parent, never globally.
        for parent in ('payment', 'campaign', 'ad_set', 'integration_connection'):
            if parent in data:
                lookup[parent] = data[parent]
        existing = scoped(name, business).filter(**lookup).first()
    if name == 'product-images':
        existing = scoped(name, business).filter(product=data.get('product'), url=data.get('url')).first()
    if name == 'product-references':
        require(connection is not None, 'INVALID_IDENTIFIER', 'Source connection is required.')
        require(not data.get('product_variant') or data.get('external_variant_id'), 'INVALID_IDENTIFIER', 'Variant mapping requires external variant ID.')
        existing = scoped(name, business).filter(integration_connection=connection, external_product_id=data.get('external_product_id'), external_variant_id=data.get('external_variant_id')).first()
    if name == 'customer-references':
        require(connection is not None, 'INVALID_IDENTIFIER', 'Source connection is required.')
    if name == 'campaign-metrics':
        existing = scoped(name, business).filter(campaign=data.get('campaign'), metric_date=data.get('metric_date')).first()
    if name == 'variants' and data.get('sku'):
        existing = scoped(name, business).filter(product=data.get('product'), sku=data['sku']).first()
    if name == 'contacts':
        data['contact_type'] = str(data.get('contact_type', '')).upper()
        data['normalized_value'] = normalize_contact(data.get('contact_type'), data.get('value'))
        existing = scoped(name, business).filter(customer=data.get('customer'), contact_type=data.get('contact_type'), normalized_value=data['normalized_value']).first()
    if name == 'tags':
        existing = scoped(name, business).filter(customer=data.get('customer'), tag=data.get('tag')).first()
    if 'status' in data and name in TRANSITIONS:
        data['status'] = _status(name, data['status'])
    if name == 'messages':
        if data.get('message_type') == 'LOCATION':
            location = data.get('location')
            require(isinstance(location, dict) and set(location) <= {'latitude', 'longitude', 'label'}, 'INVALID_LOCATION', 'Use latitude, longitude and optional label.')
            require('label' not in location or isinstance(location['label'], str) and len(location['label']) <= 255, 'INVALID_LOCATION', 'Location label must be text up to 255 characters.')
            for key, low, high in [('latitude', -90, 90), ('longitude', -180, 180)]:
                value = location.get(key)
                require(isinstance(value, (int, float)) and not isinstance(value, bool) and Decimal(str(value)).is_finite() and low <= value <= high, 'INVALID_LOCATION', 'Coordinates are invalid.')
        else:
            require(not data.get('location'), 'INVALID_LOCATION', 'Location belongs to LOCATION messages.')
        require(data.get('content') or raw.get('attachments') or data.get('message_type') == 'LOCATION', 'INVALID_MESSAGE', 'Message content or attachment is required.')
        require(data.get('direction') in ('INCOMING', 'OUTGOING'), 'INVALID_DATA', 'Invalid message direction.')
        require(data.get('sender_type') in ('CUSTOMER', 'AGENT', 'AI', 'SYSTEM'), 'INVALID_DATA', 'Invalid sender type.')
        require(data.get('message_type', 'TEXT') in ('TEXT', 'IMAGE', 'VIDEO', 'AUDIO', 'FILE', 'LOCATION', 'OTHER'), 'INVALID_DATA', 'Invalid message type.')
        data.setdefault('delivery_status', 'PENDING')
        require(data['delivery_status'] in TRANSITIONS['messages'], 'INVALID_STATUS', 'Invalid delivery status.')
        require(data.get('read_status') in (None, 'UNREAD', 'READ'), 'INVALID_STATUS', 'Invalid read status.')
    if name == 'conversations':
        require(data.get('channel') in ('MESSENGER', 'WHATSAPP', 'INSTAGRAM', 'TELEGRAM', 'WEBSITE_CHAT', 'OTHER'), 'INVALID_DATA', 'Unsupported channel.')
        require(data.get('priority', 'NORMAL') in ('LOW', 'NORMAL', 'HIGH', 'URGENT'), 'INVALID_DATA', 'Invalid priority.')
        data.setdefault('started_at', occurred_at)
    if name == 'products' and data.get('image_url'):
        try:
            URLValidator(schemes=['https', 'http'])(data['image_url'])
        except ValidationError:
            raise DomainError('INVALID_IMAGE', 'Product images must use HTTP(S).')
    if name in ('attachments', 'product-images'):
        try:
            URLValidator(schemes=['https', 'http'])(data.get('url'))
        except (ValidationError, TypeError):
            raise DomainError('INVALID_ATTACHMENT', 'Attachment URL must be HTTP(S).')
    if name in ('ads', 'ad-sets'):
        require(data.get('status', 'ACTIVE') in ('ACTIVE', 'PAUSED', 'COMPLETED'), 'INVALID_STATUS', 'Invalid advertising status.')
    if name == 'participants':
        require(data.get('participant_type') in ('CUSTOMER', 'AGENT', 'AI', 'SYSTEM'), 'INVALID_DATA', 'Invalid participant type.')
    if name == 'calls':
        require(data.get('direction') in ('INCOMING', 'OUTGOING'), 'INVALID_DATA', 'Invalid call direction.')
        data.setdefault('status', 'INITIATED')
    if name == 'visitors':
        data.setdefault('first_seen_at', occurred_at)
        data['last_seen_at'] = occurred_at
        require('customer' not in raw and raw.get('is_anonymous', True) is True, 'IDENTITY_REQUIRED', 'Known visitors must be linked through identity resolution.')
    if name == 'tags':
        data['source'] = 'MANUAL'
    if name == 'conversions':
        require(data.get('attribution_type') in (None, 'PLATFORM_REPORTED', 'DIRECT_SOURCE_REPORTED'), 'ATTRIBUTION_OWNER_REQUIRED', 'Authoritative attribution belongs to Business Intelligence.')
    if name == 'notes':
        data.update(author_type='AGENT', author_id=actor.pk, is_ai_generated=False)
    for quantity in ('inventory_quantity', 'duration_seconds', 'size_bytes', 'impressions', 'reach', 'clicks', 'conversions'):
        if data.get(quantity) is not None:
            require(data[quantity] >= 0, 'INVALID_DATA', quantity + ' cannot be negative.')
    if name == 'conversions' and data.get('website_session_id'):
        session = related(m.WebsiteSession, data['website_session_id'], business)
        require(not session.customer_id or not data.get('customer') or session.customer_id == data['customer'].pk, 'INVALID_RELATION', 'Conversion session and customer disagree.')
        if session.customer_id and not data.get('customer'):
            data['customer'] = session.customer
    if existing:
        latest = m.ProcessingReceipt.objects.filter(business=business, resource=name, entity_id=existing.pk).order_by('-occurred_at').first()
        require(not latest or occurred_at >= latest.occurred_at, 'STALE_EVENT', 'Older event cannot overwrite newer state.')
        if name in ('orders', 'refunds', 'messages', 'notes', 'website-events'):
            require(m.ProcessingReceipt.objects.filter(business=business, resource=name, entity_id=existing.pk, payload_hash=digest).exists(), 'IMMUTABLE_RECORD', 'Use lifecycle commands; existing snapshots and messages are immutable.')
            m.ProcessingReceipt.objects.create(business=business, connection=connection, key=receipt_key, resource=name, payload_hash=digest, entity_id=existing.pk, occurred_at=occurred_at)
            return existing, False
        if name == 'payments':
            require(existing.amount == data['amount'] and existing.currency == data['currency'], 'IMMUTABLE_PAYMENT', 'Payment amount/currency cannot be overwritten.')
        if 'status' in data and name in TRANSITIONS:
            previous = existing.status
            require(data['status'] == previous or data['status'] in TRANSITIONS[name].get(previous, set()), 'INVALID_TRANSITION', 'Invalid lifecycle transition.')
            # Status history/event production uses the same command path as operational changes.
            if data['status'] != previous:
                transition(business, actor, name, existing.pk, data.pop('status'), 'Source update')
                existing.refresh_from_db()
        if name == 'visitors':
            data.pop('first_seen_at', None)
            data.pop('is_anonymous', None)
            if existing.customer_id:
                data['customer'] = existing.customer
        immutable_relations = {f.name for f in model._meta.fields if isinstance(f, models.ForeignKey)}
        for k in immutable_relations & data.keys():
            require(getattr(existing, k + '_id') == (data[k].pk if data[k] else None), 'IMMUTABLE_RELATION', 'Existing record ownership cannot be changed by intake.')
        for k, v in data.items():
            setattr(existing, k, v)
        if hasattr(existing, 'updated_at'):
            existing.updated_at = timezone.now()
        validate(existing)
        existing.save()
        obj, created = existing, False
    elif name == 'orders':
        obj = _order(business, data, raw.get('items'), occurred_at)
        created = True
    elif name == 'refunds':
        obj = _refund(business, data)
        created = True
    else:
        obj, created = create(model, **data), True
    if name == 'products':
        _product_children(obj, raw, connection, actor)
    if name == 'customers':
        _customer_children(obj, raw, connection)
    if name == 'messages':
        conversation = m.Conversation.objects.select_for_update().get(pk=obj.conversation_id)
        sent = obj.sent_at or occurred_at
        conversation.last_message_at = max(filter(None, [conversation.last_message_at, sent]))
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['last_message_at', 'updated_at'])
        for attachment in raw.get('attachments', []):
            require('message' not in attachment, 'INVALID_RELATION', 'Attachment parent is server managed.')
            try:
                URLValidator(schemes=['https', 'http'])(attachment.get('url'))
            except (ValidationError, TypeError):
                raise DomainError('INVALID_ATTACHMENT', 'Attachment URL must be HTTP(S).')
            create(m.MessageAttachment, message=obj, **_prepare(m.MessageAttachment, business, attachment))
    m.ProcessingReceipt.objects.create(business=business, connection=connection, key=receipt_key,
        resource=name, payload_hash=digest, entity_id=obj.pk, occurred_at=occurred_at)
    audit(business, actor, 'INGESTED' if created else 'UPDATED', obj, {'receipt_key': receipt_key})
    if created:
        _timeline(obj, name.upper() + '_CREATED')
    return obj, created


def _order(business, data, items, occurred_at):
    require(isinstance(items, list) and items, 'INVALID_ORDER', 'At least one order item is required.')
    normalized, subtotal = [], Decimal('0.00')
    for item in items:
        require(isinstance(item, dict), 'INVALID_ORDER', 'Invalid item.')
        fields = _prepare(m.OrderItem, business, item)
        require('order' not in fields, 'INVALID_ORDER', 'Item parent is server managed.')
        _consistent(fields)
        quantity = fields.get('quantity', 1)
        require(isinstance(quantity, int) and quantity > 0, 'INVALID_ORDER', 'Quantity must be positive.')
        product = fields.get('product')
        if product:
            fields['product_name'] = product.name
            fields['sku'] = fields['product_variant'].sku if fields.get('product_variant') else product.sku
            require(product.currency == data.get('currency', business.currency), 'CURRENCY_MISMATCH', 'Product and order currencies differ.')
        require('unit_price' in fields, 'INVALID_ORDER', 'Unit price is required.')
        gross = money(fields['unit_price']) * quantity
        discount = money(fields.get('discount_amount', 0))
        require(discount <= gross, 'INVALID_ORDER', 'Item discount exceeds value.')
        fields.update(quantity=quantity, total_amount=money(gross - discount))
        subtotal += fields['total_amount']
        normalized.append(fields)
    discount = money(data.get('discount_amount', 0))
    require(discount <= subtotal, 'INVALID_ORDER', 'Order discount exceeds subtotal.')
    data.update(subtotal=money(subtotal), total_amount=money(subtotal - discount + money(data.get('shipping_amount', 0)) + money(data.get('tax_amount', 0))), ordered_at=data.get('ordered_at', occurred_at))
    obj = create(m.Order, **data)
    for fields in normalized:
        create(m.OrderItem, order=obj, **fields)
    create(m.OrderStatusHistory, order=obj, from_status=None, to_status=obj.status, source='INGESTION', changed_at=occurred_at)
    return obj


def _refund(business, data):
    require(data.get('payment'), 'INVALID_REFUND', 'Payment is required.')
    payment = m.Payment.objects.select_for_update().get(pk=data['payment'].pk)
    require(payment.status in ('PAID', 'PARTIALLY_REFUNDED'), 'INVALID_REFUND', 'Payment is not refundable.')
    require(data.get('currency', business.currency) == payment.currency, 'CURRENCY_MISMATCH', 'Refund currency differs.')
    amount = money(data.get('amount'))
    require(amount > 0, 'INVALID_REFUND', 'Refund must be positive.')
    used = m.Refund.objects.filter(payment=payment).exclude(status__in=['FAILED', 'CANCELLED']).aggregate(v=Sum('amount'))['v'] or Decimal('0')
    require(used + amount <= payment.amount, 'EXCESSIVE_REFUND', 'Refund exceeds remaining payment amount.')
    require(data.get('status', 'PENDING') in ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED'), 'INVALID_STATUS', 'Invalid refund status.')
    data.setdefault('order', payment.order)
    obj = create(m.Refund, **data)
    if obj.status == 'COMPLETED':
        _refund_payment(payment)
    return obj


def _refund_payment(payment):
    completed = m.Refund.objects.filter(payment=payment, status='COMPLETED').aggregate(v=Sum('amount'))['v'] or Decimal('0')
    payment.status = 'REFUNDED' if completed == payment.amount else 'PARTIALLY_REFUNDED' if completed else 'PAID'
    payment.updated_at = timezone.now()
    payment.save(update_fields=['status', 'updated_at'])


def _product_children(obj, raw, connection, actor):
    if raw.get('external_reference'):
        ref = raw['external_reference']
        m.ProductExternalReference.objects.get_or_create(product=obj, integration_connection=connection,
            external_product_id=str(ref['external_product_id']).strip(), external_variant_id=None,
            defaults={'created_at': timezone.now(), 'updated_at': timezone.now(), 'source_metadata': ref.get('metadata')})
    require(isinstance(raw.get('variants', []), list), 'INVALID_DATA', 'Variants must be a list.')
    for variant in raw.get('variants', []):
        require('product' not in variant, 'INVALID_RELATION', 'Variant parent is server managed.')
        data = _prepare(m.ProductVariant, obj.business, variant)
        if 'status' in data:
            data['status'] = _status('variants', data['status'])
        require(data.get('inventory_quantity') is None or data['inventory_quantity'] >= 0, 'INVALID_DATA', 'Inventory cannot be negative.')
        existing = obj.productvariant_set.filter(sku=data['sku']).first() if data.get('sku') else None
        if existing:
            update_variant(obj.business, actor, existing.pk, variant)
        else:
            create(m.ProductVariant, product=obj, **data)


def _customer_children(obj, raw, connection):
    if raw.get('external_reference'):
        ref = raw['external_reference']
        m.CustomerExternalReference.objects.get_or_create(customer=obj, integration_connection=connection,
            external_customer_id=str(ref['external_customer_id']).strip(), defaults={'created_at': timezone.now(), 'updated_at': timezone.now()})
    require(isinstance(raw.get('contacts', []), list) and isinstance(raw.get('tags', []), list), 'INVALID_DATA', 'Contacts and tags must be lists.')
    for contact in raw.get('contacts', []):
        require(isinstance(contact, dict) and set(contact) <= {'contact_type', 'value', 'is_primary'}, 'INVALID_CONTACT', 'Unsupported contact fields.')
        kind = str(contact.get('contact_type', '')).upper()
        value = normalize_contact(kind, contact.get('value'))
        require('is_primary' not in contact or isinstance(contact['is_primary'], bool), 'INVALID_CONTACT', 'Primary flag must be boolean.')
        if contact.get('is_primary'):
            obj.customercontact_set.filter(contact_type=kind, is_primary=True).update(is_primary=False)
        entry, _ = m.CustomerContact.objects.get_or_create(customer=obj, contact_type=kind, normalized_value=value,
            defaults={'value': contact['value'], 'created_at': timezone.now(), 'updated_at': timezone.now()})
        if contact.get('is_primary'):
            entry.is_primary = True
            entry.save(update_fields=['is_primary'])
    for tag in raw.get('tags', []):
        require(isinstance(tag, str) and 0 < len(tag) <= 100, 'INVALID_DATA', 'Invalid tag.')
        m.CustomerTag.objects.get_or_create(customer=obj, tag=tag.upper(), defaults={'source': 'MANUAL', 'created_at': timezone.now()})


@transaction.atomic
def transition(business, actor, name, pk, status, reason='', expected_status=None):
    authorize(actor, business, write=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = scoped(name, business).select_for_update().filter(pk=pk).first()
    require(obj is not None, 'NOT_FOUND', 'Record not found.')
    from .common import ensure_owned
    ensure_owned(obj, business)
    field = 'delivery_status' if name == 'messages' else 'status'
    previous = getattr(obj, field, None)
    require(expected_status is None or previous == expected_status, 'STALE_STATE', 'Record changed; reload before retrying.')
    status = str(status).upper()
    if name == 'refunds':
        require(previous == status or previous == 'PENDING' and status in ('COMPLETED', 'FAILED', 'CANCELLED'), 'INVALID_TRANSITION', 'Invalid refund transition.')
    else:
        status = _status(name, status)
        require(previous == status or status in TRANSITIONS[name].get(previous, set()), 'INVALID_TRANSITION', 'Invalid status transition.')
    if previous == status:
        return obj
    setattr(obj, field, status)
    if hasattr(obj, 'updated_at'):
        obj.updated_at = timezone.now()
    if name == 'conversations':
        obj.resolved_at = timezone.now() if status == 'RESOLVED' else None
        m.ConversationEvent.objects.create(conversation=obj, actor=actor, event_type='STATUS', from_state=previous, to_state=status, reason=reason)
    if name == 'payments' and status == 'PAID':
        obj.paid_at = timezone.now()
    if name == 'messages' and status == 'DELIVERED':
        obj.delivered_at = timezone.now()
    timestamp_fields = {'shipments': {'SUBMITTED': 'submitted_at', 'PICKED_UP': 'picked_up_at', 'DELIVERED': 'delivered_at', 'RETURNED': 'returned_at'}, 'calls': {'ANSWERED': 'answered_at', 'COMPLETED': 'ended_at', 'MISSED': 'ended_at', 'FAILED': 'ended_at', 'CANCELLED': 'ended_at'}, 'refunds': {'COMPLETED': 'refunded_at'}, 'messages': {'SENT': 'sent_at'}}
    timestamp_field = timestamp_fields.get(name, {}).get(status)
    if timestamp_field and getattr(obj, timestamp_field) is None:
        setattr(obj, timestamp_field, timezone.now())
    obj.save()
    if name == 'orders':
        create(m.OrderStatusHistory, order=obj, from_status=previous, to_status=status, source='OPERATOR', note=reason or None, changed_at=timezone.now())
    if name in ('shipments', 'calls'):
        event_model = m.ShipmentEvent if name == 'shipments' else m.CallEvent
        event_fields = {'shipment': obj, 'status': status, 'occurred_at': timezone.now()} if name == 'shipments' else {'call': obj, 'event_at': timezone.now()}
        create(event_model, event_type=status, **event_fields)
    if name == 'refunds':
        _refund_payment(m.Payment.objects.select_for_update().get(pk=obj.payment_id))
    audit(business, actor, 'STATUS_CHANGED', obj, {'from': previous, 'to': status, 'reason': reason})
    _timeline(obj, name.upper() + '_' + status)
    return obj


@transaction.atomic
def update_variant(business, actor, pk, changes, expected_updated_at=None):
    """Explicit catalog command; never changes an order item's historical snapshot."""
    authorize(actor, business, write=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    obj = related(m.ProductVariant, pk, business)
    require(expected_updated_at is None or obj.updated_at == expected_updated_at, 'STALE_STATE', 'Variant changed; reload before retrying.')
    allowed = {'name', 'sku', 'attributes', 'price', 'inventory_quantity', 'status'}
    require(isinstance(changes, dict) and changes and set(changes) <= allowed, 'INVALID_DATA', 'Only catalog variant fields may change.')
    values = _prepare(m.ProductVariant, business, changes)
    require(values.get('inventory_quantity') is None or values['inventory_quantity'] >= 0, 'INVALID_DATA', 'Inventory cannot be negative.')
    if 'status' in values:
        target = _status('variants', values['status'])
        values['status'] = target
        require(target == obj.status or target in TRANSITIONS['variants'].get(obj.status, set()), 'INVALID_TRANSITION', 'Invalid variant transition.')
    if values.get('sku'):
        require(not m.ProductVariant.objects.filter(product=obj.product, sku=values['sku']).exclude(pk=obj.pk).exists(), 'DUPLICATE_VARIANT', 'Variant SKU already exists.')
    for key, value in values.items():
        setattr(obj, key, value)
    obj.updated_at = timezone.now()
    validate(obj)
    obj.save()
    audit(business, actor, 'VARIANT_UPDATED', obj, {'fields': sorted(values)})
    return obj
