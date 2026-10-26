"""A paginated SQL union over authoritative events and explicitly labelled state observations."""
from datetime import timedelta

from django.db.models import Case, CharField, F, Q, Value, When
from django.db.models.functions import Cast, Concat

from app import models


# model, tenant path, domain, timestamp, event field (or literal), entity type, entity id, unique event key, condition
SOURCES = [
    ('Order', 'business_id', 'sales', 'created_at', '=ORDER_CREATED', 'order', 'pk', 'created', Q()),
    ('OrderStatusHistory', 'order__business_id', 'sales', 'changed_at', 'to_status', 'order', 'order_id', 'status', Q()),
    ('Payment', 'business_id', 'payments', 'created_at', '=PAYMENT_CREATED', 'payment', 'pk', 'created', Q()),
    ('Payment', 'business_id', 'payments', 'paid_at', '=PAYMENT_PAID', 'payment', 'pk', 'paid', Q()),
    ('Payment', 'business_id', 'payments', 'updated_at', 'status', 'payment', 'pk', 'state', Q(status__in=['FAILED', 'REJECTED']) & Q(updated_at__gt=F('created_at'))),
    ('Refund', 'payment__business_id', 'payments', 'refunded_at', '=REFUND', 'refund', 'pk', 'refunded', Q()),
    ('Customer', 'business_id', 'customers', 'created_at', '=CUSTOMER_CREATED', 'customer', 'pk', 'created', Q()),
    ('CustomerTimelineEvent', 'customer__business_id', 'customers', 'event_at', 'event_type', 'customer', 'customer_id', 'timeline', Q()),
    ('Conversation', 'business_id', 'support', 'started_at', '=CONVERSATION_OPENED', 'conversation', 'pk', 'opened', Q()),
    ('Conversation', 'business_id', 'support', 'resolved_at', '=CONVERSATION_RESOLVED', 'conversation', 'pk', 'resolved', Q()),
    ('Conversation', 'business_id', 'support', 'updated_at', 'status', 'conversation', 'pk', 'state', Q(updated_at__gt=F('created_at')) & Q(status__in=['ESCALATED', 'HANDED_OVER'])),
    ('ConversationAssignment', 'conversation__business_id', 'support', 'assigned_at', '=CONVERSATION_ASSIGNED', 'conversation', 'conversation_id', 'assigned', Q()),
    ('Shipment', 'business_id', 'delivery', 'created_at', '=SHIPMENT_CREATED', 'shipment', 'pk', 'created', Q()),
    ('ShipmentEvent', 'shipment__business_id', 'delivery', 'occurred_at', 'event_type', 'shipment', 'shipment_id', 'event', Q()),
    ('Campaign', 'business_id', 'marketing', 'created_at', '=CAMPAIGN_CREATED', 'campaign', 'pk', 'created', Q()),
    ('Campaign', 'business_id', 'marketing', 'updated_at', 'status', 'campaign', 'pk', 'state', Q(updated_at__gt=F('created_at'))),
    ('CampaignConversion', 'campaign__business_id', 'marketing', 'converted_at', 'conversion_type', 'campaign', 'campaign_id', 'conversion', Q()),
    ('WebsiteEvent', 'session__business_id', 'website', 'occurred_at', 'event_type', 'website_session', 'session_id', 'event', Q()),
    ('Call', 'business_id', 'calling', 'created_at', '=CALL_CREATED', 'call', 'pk', 'created', Q()),
    ('CallEvent', 'call__business_id', 'calling', 'event_at', 'event_type', 'call', 'call_id', 'event', Q()),
    ('BusinessIssue', 'business_id', 'issues', 'detected_at', '=ISSUE_DETECTED', 'issue', 'pk', 'detected', Q()),
    ('BusinessIssue', 'business_id', 'issues', 'updated_at', 'status', 'issue', 'pk', 'state', Q(updated_at__gt=F('detected_at'))),
    ('AiRecommendation', 'business_id', 'ai', 'generated_at', '=RECOMMENDATION_GENERATED', 'recommendation', 'pk', 'generated', Q()),
    ('AiRecommendation', 'business_id', 'ai', 'updated_at', 'status', 'recommendation', 'pk', 'state', ~Q(status='SUGGESTED') & Q(updated_at__gt=F('generated_at'))),
    ('AiAction', 'business_id', 'ai', 'created_at', '=ACTION_CREATED', 'recommendation', 'ai_recommendation_id', 'created', Q()),
    ('AiAction', 'business_id', 'ai', 'approved_at', '=ACTION_APPROVED', 'recommendation', 'ai_recommendation_id', 'approved', Q()),
    ('AiAction', 'business_id', 'ai', 'executed_at', '=ACTION_EXECUTED', 'recommendation', 'ai_recommendation_id', 'executed', Q()),
    ('AiAction', 'business_id', 'ai', 'updated_at', 'status', 'recommendation', 'ai_recommendation_id', 'state', Q(status__in=['REJECTED', 'UNDER_REVIEW', 'FAILED']) & Q(updated_at__gt=F('created_at'))),
]
HIGH_EVENTS = ['FAILED', 'DELIVERY_FAILED', 'RETURNED', 'ESCALATED', 'REJECTED', 'PAYMENT_FAILED']


def activity_query(business_id, params, now):
    queries = []
    for name, tenant, domain, clock, event, entity, entity_id, key, condition in SOURCES:
        if params.get('domain') and params['domain'] != domain:
            continue
        if params.get('entity_type') and params['entity_type'] != entity:
            continue
        query = getattr(models, name).objects.filter(condition, **{tenant: business_id,
            clock+'__gte': params.get('from', now-timedelta(days=30)),
            clock+'__lt': params.get('to', now+timedelta(microseconds=1)), 'created_at__lte': now})
        if name == 'AiAction':
            query = query.filter(ai_recommendation__business_id=business_id)
        if name == 'WebsiteEvent':
            query = query.filter(visitor__business_id=business_id)
        if 'entity_id' in params:
            query = query.filter(**{entity_id: params['entity_id']})
        event_expr = Value(event[1:]) if event.startswith('=') else F(event)
        severity_expr = F('severity') if name == 'BusinessIssue' else F('priority') if name == 'AiRecommendation' else (
            Case(When(**{f'{event}__in': HIGH_EVENTS}, then=Value('HIGH')), default=Value('INFO'))
            if not event.startswith('=') else Value('INFO'))
        query = query.order_by().annotate(
            activity_id=Concat(Value(f'{name}:{key}:'), Cast('pk', CharField())),
            activity_at=F(clock), activity_domain=Value(domain, output_field=CharField()),
            activity_event=Cast(event_expr, CharField()), activity_severity=Cast(severity_expr, CharField()),
            activity_entity_type=Value(entity, output_field=CharField()), activity_entity_id=F(entity_id),
            activity_source=Value(name, output_field=CharField()),
            activity_basis=Value('LATEST_STATE_OBSERVATION' if key == 'state' else 'RECORDED_EVENT', output_field=CharField()))
        if 'severity' in params:
            query = query.filter(activity_severity=params['severity'])
        queries.append(query.values('activity_id', 'activity_at', 'activity_domain', 'activity_event',
            'activity_severity', 'activity_entity_type', 'activity_entity_id', 'activity_source', 'activity_basis'))
    if not queries:
        return []
    return queries[0].union(*queries[1:], all=True).order_by('-activity_at', 'activity_id')


def activity_data(row, business_id):
    entity_type, pk = row['activity_entity_type'], row['activity_entity_id']
    if entity_type in {'issue', 'recommendation'}:
        path = f'{entity_type}s/{pk}/'
    else:
        path = f'entities/{entity_type}/{pk}/'
    return {'id': row['activity_id'], 'occurred_at': row['activity_at'], 'domain': row['activity_domain'],
            'event': row['activity_event'], 'severity': row['activity_severity'], 'source': row['activity_source'],
            'basis': row['activity_basis'], 'entity': {'type': entity_type, 'id': pk},
            'drilldown': f'/api/businesses/{business_id}/overview/{path}'}
