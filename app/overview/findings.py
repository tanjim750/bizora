from django.db.models import Case, IntegerField, Prefetch, Q, Value, When

from app.models import AiAction, AiRecommendation, AiRecommendationEvidence, BusinessIssue, BusinessIssueEvidence
from app.observability.policies import safe_details
from .catalog import ACTIVE_ISSUES, ACTIVE_RECOMMENDATIONS, DOMAINS, ENTITY_DOMAINS, SEVERITIES
from .evidence import REC_RELATED, RELATED


def ranked(query, field):
    return query.annotate(monitoring_rank=Case(*[When(**{field: severity}, then=Value(index))
        for index, severity in enumerate(SEVERITIES)], default=Value(99), output_field=IntegerField()))


def issues_query(business_id, params, now, config):
    query = BusinessIssue.objects.filter(business_id=business_id, detected_at__lte=now, created_at__lte=now)
    query = query.filter(status=params['status']) if 'status' in params else query.filter(status__in=ACTIVE_ISSUES, resolved_at__isnull=True)
    query = query.filter(severity=params['severity']) if 'severity' in params else query.filter(severity__in=config['issue_severities'])
    if 'entity_type' in params:
        query = query.filter(subject_entity_type__iexact=params['entity_type'])
    if 'entity_id' in params:
        query = query.filter(subject_entity_id=params['entity_id'])
    for key, lookup in [('from', 'gte'), ('to', 'lt')]:
        if key in params:
            query = query.filter(**{f'detected_at__{lookup}': params[key]})
    return ranked(query, 'severity').order_by('monitoring_rank', '-detected_at', '-pk')


def recommendations_query(business_id, params, now, config):
    query = AiRecommendation.objects.filter(business_id=business_id, generated_at__lte=now, created_at__lte=now)
    if params.get('status') == 'EXPIRED':
        query = query.filter(Q(status='EXPIRED') | Q(status__in=ACTIVE_RECOMMENDATIONS, expires_at__lte=now))
    elif 'status' in params:
        query = query.filter(status=params['status'])
    else:
        query = query.filter(status__in=ACTIVE_RECOMMENDATIONS).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    query = query.filter(priority=params['priority']) if 'priority' in params else query.filter(priority__in=config['recommendation_priorities'])
    if 'issue' in params:
        query = query.filter(business_issue_id=params['issue'], business_issue__business_id=business_id)
    for key, lookup in [('from', 'gte'), ('to', 'lt')]:
        if key in params:
            query = query.filter(**{f'generated_at__{lookup}': params[key]})
    return ranked(query.select_related('business_issue'), 'priority').order_by('monitoring_rank', '-generated_at', '-pk')


def with_issue_evidence(query):
    return query.prefetch_related(Prefetch('businessissueevidence_set',
        queryset=BusinessIssueEvidence.objects.select_related(*RELATED).order_by('pk')[:101], to_attr='monitoring_evidence'))


def with_recommendation_context(query, business_id):
    return query.prefetch_related(Prefetch('airecommendationevidence_set',
        queryset=AiRecommendationEvidence.objects.select_related(*REC_RELATED).order_by('pk')[:101], to_attr='monitoring_evidence'),
        Prefetch('aiaction_set', queryset=AiAction.objects.filter(business_id=business_id).order_by('-created_at', '-pk')[:20],
                 to_attr='monitoring_actions'))


def issue_domains(row):
    metadata = row.metadata if isinstance(row.metadata, dict) else {}
    domains = metadata.get('domains', [])
    domains = [domain for domain in domains if domain in DOMAINS] if isinstance(domains, list) else []
    fallback = ENTITY_DOMAINS.get((row.subject_entity_type or '').lower())
    return list(dict.fromkeys(domains + ([fallback] if fallback else [])))


def issue_data(row, evidence, now, detail=False):
    metadata = row.metadata if isinstance(row.metadata, dict) else {}
    trend = metadata.get('trend', 'UNKNOWN')
    if not isinstance(trend, str) or trend not in {'IMPROVING', 'WORSENING', 'STABLE'}:
        trend = 'UNKNOWN'
    data = {'id': row.pk, 'title': row.title, 'type': row.issue_type, 'severity': row.severity, 'status': row.status,
            'confidence': str(row.confidence), 'detected_at': row.detected_at, 'updated_at': row.updated_at,
            'resolved_at': row.resolved_at, 'domains': issue_domains(row), 'trend': trend,
            'trend_source': 'BI_ISSUE_METADATA' if trend != 'UNKNOWN' else None,
            'entity': evidence.entity(row.subject_entity_type, row.subject_entity_id),
            'drilldown': evidence.href('issues', row.pk), 'rule_key': row.rule_key}
    data['context'] = {key: str(metadata[key])[:255] for key in ('region', 'courier', 'customer_segment', 'campaign', 'product')
                       if isinstance(metadata.get(key), (str, int, float))}
    if hasattr(row, 'monitoring_evidence'):
        data['evidence_summary'] = evidence.issue_evidence(row)[:3]
    if detail:
        data.update(description=row.description, evidence=evidence.issue_evidence(row), evidence_limit=50,
            graph=evidence.graph_context(row.subject_entity_type, row.subject_entity_id))
        recs = recommendations_query(row.business_id, {'issue': row.pk}, now,
                                     {'recommendation_priorities': list(SEVERITIES)})[:20]
        data['recommendations'] = [{'id': r.pk, 'title': r.title, 'status': r.status,
                                   'drilldown': evidence.href('recommendations', r.pk)} for r in recs]
    return data


def recommendation_data(row, evidence, now, detail=False):
    metadata = row.metadata if isinstance(row.metadata, dict) else {}
    goals = metadata.get('goals', [])
    issue = row.business_issue if row.business_issue_id and evidence.owned(row.business_issue) else None
    data = {'id': row.pk, 'title': row.title, 'type': row.recommendation_type, 'priority': row.priority,
            'status': row.status, 'confidence': str(row.confidence) if row.confidence is not None else None,
            'effective_status': 'EXPIRED' if row.status in ACTIVE_RECOMMENDATIONS and row.expires_at is not None and row.expires_at <= now else row.status,
            'generated_at': row.generated_at, 'expires_at': row.expires_at,
            'expired': row.expires_at is not None and row.expires_at <= now,
            'issue': evidence.reference('issues', issue) if issue else None,
            'goals': [g[:255] for g in goals if isinstance(g, str)][:20] if isinstance(goals, list) else [],
            'suggested_action_type': row.suggested_action_type, 'drilldown': evidence.href('recommendations', row.pk)}
    if hasattr(row, 'monitoring_evidence'):
        data['evidence_summary'] = evidence.recommendation_evidence(row)[:3]
    if hasattr(row, 'monitoring_actions'):
        data['action_summary'] = [{'id': a.pk, 'type': a.action_type, 'status': a.status}
                                  for a in row.monitoring_actions if a.created_at <= now][:3]
    if detail:
        actions = getattr(row, 'monitoring_actions', None)
        if actions is None:
            actions = row.aiaction_set.filter(business_id=row.business_id, created_at__lte=now).order_by('-created_at', '-pk')[:20]
        data.update(description=row.description, rationale=row.rationale,
            evidence=evidence.recommendation_evidence(row), evidence_limit=50,
            graph=evidence.graph_context(issue.subject_entity_type, issue.subject_entity_id) if issue else {'nodes': [], 'edges': []},
            actions=[{'id': a.pk, 'type': a.action_type, 'status': a.status,
                      'target': evidence.entity(a.target_entity_type, a.target_entity_id), 'preview': safe_details(a.action_payload),
                      'approved_at': a.approved_at, 'executed_at': a.executed_at, 'is_simulated': a.is_simulated}
                     for a in actions if a.created_at <= now][:20])
    return data
