"""Local read contracts for externally owned authoritative records.

These functions validate ownership, validity and evidence; they never generate analytics,
relationships, AI answers or provider execution outcomes.
"""
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from app import models as m
from .common import DomainError, ensure_owned


def current_facts(business):
    now = timezone.now()
    return m.BusinessFact.objects.filter(business=business, status='VERIFIED').filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now)).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gt=now))


def safe_records(queryset, business):
    """Never return foreign-tenant references embedded in an otherwise owned record."""
    ids = []
    for record in queryset.iterator():
        try:
            ensure_owned(record, business)
        except (DomainError, ObjectDoesNotExist):
            continue
        ids.append(record.pk)
    return queryset.filter(pk__in=ids)


def recommendation_supported(recommendation, business):
    if recommendation.business_id != business.pk or recommendation.status not in ('SUGGESTED', 'APPROVED'):
        return False
    if recommendation.expires_at and recommendation.expires_at <= timezone.now():
        return False
    try:
        ensure_owned(recommendation, business)
    except (DomainError, ObjectDoesNotExist):
        return False
    evidence = m.AiRecommendationEvidence.objects.filter(ai_recommendation=recommendation)
    if not evidence.exists() or safe_records(evidence, business).count() != evidence.count():
        return False
    current = current_facts(business)
    fact_ids = set(evidence.exclude(business_fact__isnull=True).values_list('business_fact_id', flat=True))
    return bool(fact_ids) and fact_ids <= set(safe_records(current, business).values_list('pk', flat=True))


def capability(owner, name, results=None):
    return {'owner': owner, 'capability': name, 'status': 'AVAILABLE' if results is not None else 'UNAVAILABLE',
            'results': results, 'authoritative': results is not None}


def prepare_operation(business, actor, operation, entity_id):
    """Canonical outbound request for Integrations; preparing never executes or changes state."""
    from .common import authorize, related, require
    authorize(actor, business, write=True)
    specs = {'SHIPMENT_SUBMIT': m.Shipment, 'SHIPMENT_CANCEL': m.Shipment,
             'CALL_INITIATE': m.Call, 'MESSAGE_SEND': m.Message}
    require(operation in specs, 'INVALID_OPERATION', 'Unsupported outbound operation.')
    obj = related(specs[operation], entity_id, business)
    connection = getattr(obj, 'integration_connection', None)
    require(connection is not None and connection.status == 'CONNECTED', 'CONNECTION_UNAVAILABLE', 'A connected integration source is required.')
    if operation == 'SHIPMENT_SUBMIT':
        require(obj.status == 'PENDING', 'INVALID_TRANSITION', 'Only pending shipments may be submitted.')
        require(obj.recipient_phone and obj.delivery_address, 'INVALID_SHIPMENT', 'Recipient phone and address are required.')
        payload = {'order_id': obj.order_id, 'tracking_code': obj.tracking_code,
                   'recipient_name': obj.recipient_name, 'recipient_phone': obj.recipient_phone,
                   'delivery_address': obj.delivery_address, 'cod_amount': str(obj.cod_amount), 'currency': obj.currency}
    elif operation == 'SHIPMENT_CANCEL':
        require(obj.status in ('PENDING', 'SUBMITTED'), 'INVALID_TRANSITION', 'Shipment is no longer cancellable.')
        payload = {'external_shipment_id': obj.external_shipment_id, 'tracking_code': obj.tracking_code}
    elif operation == 'CALL_INITIATE':
        require(obj.direction == 'OUTGOING' and obj.status == 'INITIATED' and obj.receiver_number,
                'INVALID_CALL', 'An initiated outgoing call with receiver number is required.')
        payload = {'caller': obj.caller_number, 'receiver': obj.receiver_number, 'customer_id': obj.customer_id,
                   'order_id': obj.order_id, 'conversation_id': obj.conversation_id}
    else:
        require(obj.direction == 'OUTGOING' and obj.delivery_status == 'PENDING', 'INVALID_MESSAGE', 'Only pending outgoing messages can be sent.')
        payload = {'conversation_id': obj.conversation_id, 'channel': obj.conversation.channel,
                   'external_conversation_id': obj.conversation.external_conversation_id,
                   'message_type': obj.message_type, 'content': obj.content, 'location': obj.location,
                   'attachments': list(obj.messageattachment_set.values('attachment_type', 'url', 'mime_type'))}
    return {'version': 'bizora.outbound.v1', **capability('Integrations', operation), 'request': {'operation': operation,
            'business_id': business.pk, 'connection_id': connection.pk, 'entity_type': type(obj).__name__.upper(),
            'entity_id': obj.pk, 'payload': payload}, 'execution': 'NOT_EXECUTED', 'simulated_source': connection.is_mock}
