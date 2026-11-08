from django.db.models import Q
from django.utils import timezone
from app import models as m
from .common import related, require
from .registry import scoped
from .operations import unavailable
from .contracts import current_facts, safe_records, recommendation_supported


def serialize(obj):
    """Canonical API representation. Provider metadata and transport URLs stay private."""
    excluded = {'source_metadata', 'config', 'recording_url'}
    return {f.name: getattr(obj, f.attname) for f in obj._meta.fields if f.name not in excluded}


def section(queryset, limit=50, ordering="pk"):
    count = queryset.count()
    return {'count': count, 'results': [serialize(x) for x in queryset.order_by(ordering)[:limit]],
            'truncated': count > limit}


def authority_context(business, entity_type=None, entity_id=None):
    facts = safe_records(current_facts(business), business)
    issues = m.BusinessIssue.objects.filter(business=business, status__in=['OPEN', 'ACKNOWLEDGED'])
    relations = m.BusinessRelationship.objects.filter(business=business).filter(Q(valid_from__isnull=True) | Q(valid_from__lte=timezone.now())).filter(Q(valid_to__isnull=True) | Q(valid_to__gt=timezone.now()))
    nodes = m.GraphNode.objects.filter(business=business)
    recommendations = m.AiRecommendation.objects.filter(business=business, status='SUGGESTED').filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    if entity_type:
        facts = facts.filter(subject_entity_type=entity_type, subject_entity_id=entity_id)
        issues = issues.filter(subject_entity_type=entity_type, subject_entity_id=entity_id)
        relations = relations.filter(Q(source_entity_type=entity_type, source_entity_id=entity_id) | Q(target_entity_type=entity_type, target_entity_id=entity_id))
        nodes = nodes.filter(entity_type=entity_type, entity_id=entity_id)
        recommendations = recommendations.filter(business_issue__in=issues)
    recommendations = recommendations.filter(airecommendationevidence__business_fact__in=facts).distinct()
    recommendations = recommendations.filter(pk__in=[r.pk for r in recommendations if recommendation_supported(r, business)])
    issues, relations, nodes = (safe_records(qs, business) for qs in (issues, relations, nodes))
    fact_evidence = m.BusinessFactEvidence.objects.filter(business_fact__in=facts)
    issue_evidence = m.BusinessIssueEvidence.objects.filter(business_issue__in=issues)
    return {'fact_evidence': section(safe_records(fact_evidence, business)), 'issue_evidence': section(safe_records(issue_evidence, business)),
            'recommendation_evidence': section(m.AiRecommendationEvidence.objects.filter(ai_recommendation__in=recommendations)),
            'facts': section(facts), 'issues': section(issues), 'relationships': section(relations),
            'graph_nodes': section(nodes), 'recommendations': section(recommendations),
            'metric_definitions': section(m.BusinessMetric.objects.filter(business=business)),
            'metrics': section(m.MetricSnapshot.objects.filter(business=business, metric__business=business)) if entity_type is None else unavailable('Business Intelligence: entity metric dimensions'),
            'ai_answers': unavailable('AI Intelligence'), 'attribution_analysis': unavailable('Business Intelligence'),
            'freshness': unavailable('Integration & Data Observability')}


def overview(business):
    return {'business': {'id': business.pk, 'name': business.name, 'currency': business.currency, 'timezone': business.timezone},
            'canonical_counts': {name: scoped(name, business).count() for name in
                                 ('customers', 'products', 'orders', 'payments', 'conversations', 'shipments', 'calls', 'campaigns', 'sessions')},
            'recent_activity': section(m.DomainAudit.objects.filter(business=business), ordering='-created_at'),
            'intelligence': authority_context(business), 'business_health': unavailable('Overview & Monitoring')}


def customer360(business, pk):
    customer = related(m.Customer, pk, business)
    ids = m.CanonicalIdentity.objects.filter(business=business, entity_type='CUSTOMER', entity_id=pk)
    return {'customer': serialize(customer), 'contacts': section(customer.customercontact_set.all()),
            'tags': section(customer.customertag_set.all()), 'identities': section(ids),
            'external_identities': section(m.ExternalIdentity.objects.filter(identitylink__canonical_identity__in=ids, identitylink__status='ACTIVE', business=business).distinct()),
            'identity_links': section(m.IdentityLink.objects.filter(canonical_identity__in=ids, status='ACTIVE', external_identity__business=business)),
            'orders': section(scoped('orders', business).filter(customer=customer)),
            'payments': section(scoped('payments', business).filter(customer=customer)),
            'refunds': section(scoped('refunds', business).filter(payment__customer=customer)),
            'conversations': section(scoped('conversations', business).filter(customer=customer)),
            'messages': section(scoped('messages', business).filter(conversation__customer=customer), ordering='created_at'),
            'calls': section(scoped('calls', business).filter(customer=customer)),
            'shipments': section(scoped('shipments', business).filter(customer=customer)),
            'sessions': section(scoped('sessions', business).filter(customer=customer)),
            'website_events': section(scoped('website-events', business).filter(customer=customer)),
            'marketing_conversions': section(scoped('conversions', business).filter(customer=customer)),
            'timeline': section(customer.customertimelineevent_set.all(), ordering='event_at'),
            'intelligence': authority_context(business, 'CUSTOMER', pk)}


def detail(business, name, pk):
    obj = scoped(name, business).get(pk=pk)
    from .common import ensure_owned
    ensure_owned(obj, business)
    result = {'record': serialize(obj)}
    mapping = {
        'products': [('variants', 'product'), ('product-images', 'product'), ('orders', None)],
        'orders': [('payments', 'order'), ('refunds', 'order'), ('shipments', 'order'), ('calls', 'order')],
        'payments': [('refunds', 'payment')],
        'conversations': [('messages', 'conversation'), ('participants', 'conversation'), ('notes', 'conversation'), ('calls', 'conversation')],
        'messages': [('attachments', 'message')],
        'campaigns': [('campaign-metrics', 'campaign'), ('conversions', 'campaign'), ('ad-sets', 'campaign')],
        'visitors': [('sessions', 'visitor'), ('website-events', 'visitor')],
        'sessions': [('website-events', 'session')],
        'shipments': [('shipment-events', 'shipment')],
        'calls': [('call-events', 'call'), ('transcripts', 'call')],
    }
    for child, field in mapping.get(name, []):
        qs = scoped(child, business)
        qs = qs.filter(**{field: obj}) if field else qs.filter(orderitem__product=obj).distinct()
        result[child] = section(qs, ordering={'messages': 'created_at', 'website-events': 'occurred_at', 'shipment-events': 'occurred_at', 'call-events': 'event_at', 'campaign-metrics': 'metric_date'}.get(child, 'pk'))
    extras = {
        'products': {'external_references': m.ProductExternalReference.objects.filter(product=obj)} if name == 'products' else {},
        'orders': {'items': m.OrderItem.objects.filter(order=obj), 'history': m.OrderStatusHistory.objects.filter(order=obj)} if name == 'orders' else {},
        'conversations': {'assignments': m.ConversationAssignment.objects.filter(conversation=obj), 'history': m.ConversationEvent.objects.filter(conversation=obj)} if name == 'conversations' else {},
    }
    for key, qs in extras.get(name, {}).items():
        result[key] = section(qs, ordering={'history': 'changed_at' if name == 'orders' else 'created_at', 'assignments': 'assigned_at'}.get(key, 'pk'))
    for field in ('customer', 'order', 'conversation', 'product'):
        if hasattr(obj, field + '_id') and getattr(obj, field + '_id'):
            result[field] = serialize(related(obj._meta.get_field(field).related_model, getattr(obj, field + '_id'), business))
    if name == 'products':
        orders = scoped('orders', business).filter(orderitem__product=obj).distinct()
        now = timezone.now()
        verified_customers = safe_records(m.BusinessRelationship.objects.filter(business=business,
            relationship_source__in=['DETERMINISTIC', 'MANUAL']).filter(
            Q(source_entity_type='PRODUCT', source_entity_id=obj.pk, target_entity_type='CUSTOMER') |
            Q(target_entity_type='PRODUCT', target_entity_id=obj.pk, source_entity_type='CUSTOMER')).filter(
            Q(valid_from__isnull=True) | Q(valid_from__lte=now)).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gt=now)), business)
        linked_customer_ids = {row.target_entity_id if row.source_entity_type == 'PRODUCT' else row.source_entity_id
                               for row in verified_customers}
        result['customers'] = section(scoped('customers', business).filter(
            Q(order__in=orders) | Q(pk__in=linked_customer_ids)).distinct())
        result['shipments'] = section(scoped('shipments', business).filter(order__in=orders))
        result['calls'] = section(scoped('calls', business).filter(order__in=orders))
    if name in ('orders', 'products'):
        order_ids = [obj.pk] if name == 'orders' else list(scoped('orders', business).filter(orderitem__product=obj).values_list('pk', flat=True))
        verified = m.BusinessRelationship.objects.filter(business=business,
            source_entity_type='ORDER', source_entity_id__in=order_ids,
            relationship_type='HAS_CONVERSATION', target_entity_type='CONVERSATION').filter(Q(valid_from__isnull=True) | Q(valid_from__lte=timezone.now())).filter(Q(valid_to__isnull=True) | Q(valid_to__gt=timezone.now()))
        result['related_conversations'] = section(scoped('conversations', business).filter(pk__in=verified.values('target_entity_id')))
    result['intelligence'] = authority_context(business, {'sessions': 'SESSION', 'conversations': 'CONVERSATION', 'calls': 'CALL', 'customers': 'CUSTOMER', 'products': 'PRODUCT', 'payments': 'PAYMENT', 'orders': 'ORDER', 'campaigns': 'CAMPAIGN', 'shipments': 'SHIPMENT'}.get(name, name.upper()), pk)
    if name == 'calls':
        result['recording_access'] = unavailable('Calling Integration: authorized recording transport')
    return result


def financial_timeline(business, customer_id=None, order_id=None):
    """A chronology of stored financial activity, not revenue recognition or BI."""
    from django.db.models import Value, CharField
    from django.db.models.functions import Coalesce
    payments, refunds = scoped('payments', business), scoped('refunds', business)
    if customer_id is not None:
        customer = related(m.Customer, customer_id, business)
        payments, refunds = payments.filter(customer=customer), refunds.filter(payment__customer=customer)
    if order_id is not None:
        order = related(m.Order, order_id, business)
        payments, refunds = payments.filter(order=order), refunds.filter(order=order)
    fields = ('id', 'event_at', 'entity_kind', 'amount', 'currency', 'status', 'order_id')
    payments = payments.annotate(event_at=Coalesce('paid_at', 'created_at'), entity_kind=Value('PAYMENT', output_field=CharField())).values(*fields)
    refunds = refunds.annotate(event_at=Coalesce('refunded_at', 'created_at'), entity_kind=Value('REFUND', output_field=CharField())).values(*fields)
    return payments.union(refunds, all=True).order_by('-event_at', 'entity_kind', 'id')


def support_context(business, conversation_id, order_id=None):
    """Canonical suggested-reply/handover inputs. Does not produce a reply or policy."""
    conversation = related(m.Conversation, conversation_id, business)
    context = {'conversation': serialize(conversation),
               'messages': section(scoped('messages', business).filter(conversation=conversation), ordering='created_at'),
               'internal_notes': section(scoped('notes', business).filter(conversation=conversation), ordering='created_at'),
               'history': section(m.ConversationEvent.objects.filter(conversation=conversation), ordering='created_at'),
               'customer': customer360(business, conversation.customer_id) if conversation.customer_id else None,
               'policy_context': unavailable('Business Memory & Knowledge'),
               'suggested_reply': unavailable('AI Intelligence')}
    if order_id is not None:
        order = related(m.Order, order_id, business)
        explicit = m.BusinessRelationship.objects.filter(business=business, source_entity_type='ORDER', source_entity_id=order.pk,
                   target_entity_type='CONVERSATION', target_entity_id=conversation.pk, relationship_type='HAS_CONVERSATION').filter(
                   Q(valid_from__isnull=True) | Q(valid_from__lte=timezone.now())).filter(Q(valid_to__isnull=True) | Q(valid_to__gt=timezone.now()))
        require(order.customer_id is not None and order.customer_id == conversation.customer_id or explicit.exists(),
                'INVALID_RELATION', 'Order has no verified relationship to this conversation.')
        context['order'] = detail(business, 'orders', order.pk)
    return context


def retargeting_context(business, customer_id):
    customer = related(m.Customer, customer_id, business)
    return {'customer_id': customer.pk, 'kind': 'OBSERVED_SIGNALS',
            'sessions': section(scoped('sessions', business).filter(customer=customer), ordering='started_at'),
            'events': section(scoped('website-events', business).filter(customer=customer), ordering='occurred_at'),
            'conversions': section(scoped('conversions', business).filter(customer=customer), ordering='converted_at'),
            'audience_recommendation': unavailable('Business Intelligence / AI Intelligence')}


def graph_context(business, entity_type, entity_id):
    """Consume a persisted one-hop graph; graph building and traversal stay externally owned."""
    from .identity import ENTITY_MODELS
    require(entity_type in ENTITY_MODELS, 'INVALID_ENTITY', 'Unsupported canonical entity type.')
    related(ENTITY_MODELS[entity_type], entity_id, business)
    roots = safe_records(m.GraphNode.objects.filter(business=business, entity_type=entity_type, entity_id=entity_id), business)
    now = timezone.now()
    edges = safe_records(m.GraphEdge.objects.filter(business=business).filter(
        Q(source_node__in=roots) | Q(target_node__in=roots)).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now)).filter(Q(valid_to__isnull=True) | Q(valid_to__gt=now)), business)
    neighbors = m.GraphNode.objects.filter(business=business).filter(
        Q(pk__in=roots.values('pk')) | Q(pk__in=edges.values('source_node_id')) | Q(pk__in=edges.values('target_node_id')))
    return {'status': 'AVAILABLE' if roots.exists() else 'UNAVAILABLE', 'owner': 'Business Graph',
            'nodes': section(safe_records(neighbors, business)), 'edges': section(edges),
            'generation': unavailable('Business Graph'), 'scope': 'PERSISTED_ONE_HOP'}
