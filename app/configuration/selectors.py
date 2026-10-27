"""Read contracts for owning domains; rules evaluate caller-supplied inputs only."""
from decimal import Decimal, InvalidOperation
import operator

from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from app.models import Business, ConfigurationRevision, KnowledgeSource
from .schemas import PLATFORM_GUARDRAILS, TASKS, ai_providers
from .services import section_data


def effective_revisions(business_id, kind, at=None):
    at = at or timezone.now()
    eligible = ConfigurationRevision.objects.filter(record__business_id=business_id, record__kind=kind,
        created_at__lte=at).exclude(status='DRAFT').filter(Q(valid_from__isnull=True) | Q(valid_from__lte=at))
    # Choose the latest publication before checking its state or expiry. Old ACTIVE
    # rows must not reappear after a later disable/archive/expiry.
    latest = eligible.filter(record_id=OuterRef('record_id')).order_by('-version').values('pk')[:1]
    return eligible.filter(pk=Subquery(latest), status='ACTIVE').filter(
        Q(valid_to__isnull=True) | Q(valid_to__gt=at)).select_related('record').order_by('-priority', 'record__key')


def scope_matches(required, scope):
    return all(key in scope and scope[key] == value for key, value in required.items())


def contract(row):
    return {'id': row.pk, 'key': row.record.key, 'version': row.version, 'settings': row.data,
            'priority': row.priority, 'valid_from': row.valid_from, 'valid_to': row.valid_to,
            'rule_reference': f'config:{row.record.kind.lower()}:{row.record.key}:v{row.version}'}


def effective_rules(business_id, category=None, scope=None, at=None):
    scope = scope or {}
    return [contract(row) for row in effective_revisions(business_id, 'RULE', at)
            if (not category or row.data['category'] == category) and scope_matches(row.data.get('scope', {}), scope)]


def evaluate_rule(rule, inputs):
    data = rule['settings']
    missing = set()
    if data.get('min_samples'):
        value = inputs.get(data['sample_metric'])
        try:
            sample = Decimal(str(value)) if not isinstance(value, bool) else Decimal('NaN')
            if not sample.is_finite() or sample < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return {'status': 'UNKNOWN', 'missing_fields': [data['sample_metric']], 'rule_reference': rule['rule_reference']}
        if sample < data['min_samples']:
            return {'status': 'INSUFFICIENT_SAMPLE', 'rule_reference': rule['rule_reference']}
    mode, conditions = next(iter(data['conditions'].items()))
    outcomes = []
    for condition in conditions:
        field, op, expected = condition['field'], condition['operator'], condition['value']
        value = inputs.get(field)
        if value is None:
            missing.add(field)
            continue
        if op in {'gt', 'gte', 'lt', 'lte'}:
            try:
                actual, expected = Decimal(str(value)), Decimal(str(expected))
                if isinstance(value, bool) or not actual.is_finite():
                    raise InvalidOperation
                result = {'gt': operator.gt, 'gte': operator.ge, 'lt': operator.lt, 'lte': operator.le}[op](actual, expected)
            except (InvalidOperation, ValueError):
                missing.add(field)
                continue
        else:
            result = (value == expected) if op == 'eq' else (value != expected) if op == 'ne' else (
                value in expected if op == 'in' else value not in expected)
        outcomes.append(result)
    if mode == 'all' and False in outcomes:
        status = 'NO_MATCH'
    elif mode == 'any' and True in outcomes:
        status = 'MATCH'
    elif missing:
        status = 'UNKNOWN'
    else:
        status = 'MATCH' if (all(outcomes) if mode == 'all' else any(outcomes)) else 'NO_MATCH'
    return {'status': status, 'missing_fields': sorted(missing), 'rule_reference': rule['rule_reference'],
            'outcome': data['outcome'] if status == 'MATCH' else None}


def effective_policies(business_id, scope=None, at=None, for_ai=False):
    rows = [row for row in effective_revisions(business_id, 'POLICY', at)
            if scope_matches(row.data.get('scope', {}), scope or {}) and (not for_ai or row.data.get('ai_available', False))]
    rows.sort(key=lambda r: (-r.priority, -len(r.data.get('scope', {})), r.record.key))
    return [contract(row) for row in rows]


def ai_configuration(business_id, workflow=None):
    from django.conf import settings
    if workflow is not None and workflow not in TASKS:
        raise ValueError('Unknown AI workflow.')
    result = section_data(Business.objects.get(pk=business_id), 'AI')['settings']
    result['guardrails'] = dict(PLATFORM_GUARDRAILS)
    result['confidence_threshold'] = str(max(Decimal(result['confidence_threshold']),
        Decimal(str(getattr(settings, 'BIZORA_AI_MIN_CONFIDENCE', '0.6')))))
    provider = ai_providers().get(result['provider'])
    if provider is None or any(model not in provider['models'] for model in result['models'].values()):
        result.update(enabled=False, unavailable_reason='PROVIDER_OR_MODEL_NOT_REGISTERED')
    preferences = result.get('workflows', {}).get(workflow, {}) if workflow else {}
    result['effective_context_categories'] = [v for v in preferences.get('context_categories', result['context_categories'])
                                               if v in result['context_categories']]
    result['confidence_threshold'] = str(max(Decimal(result['confidence_threshold']),
        Decimal(preferences.get('confidence_threshold', result['confidence_threshold']))))
    result['allowed_actions'] = [v for v in preferences.get('allowed_actions', result['allowed_actions'])
        if v in result['allowed_actions'] and v not in result['execution']['disabled_actions']]
    result['response'] = {**result['response'], **preferences.get('response', {})}
    if workflow:
        result['workflow_enabled'] = bool(result['enabled'] and result['features'].get(workflow, False)
            and preferences.get('enabled', True) and workflow in result['models'])
    return result


def action_policy(business_id, action):
    data = ai_configuration(business_id)
    return {'may_propose': data['enabled'] and action in data['allowed_actions'] and action not in data['execution']['disabled_actions'],
            'approval_required': True, 'automatic_external_execution': False}


def knowledge_configuration(business_id, workflow=None, historical=False):
    if workflow is not None and workflow not in TASKS:
        raise ValueError('Unknown knowledge workflow.')
    data = section_data(Business.objects.get(pk=business_id), 'KNOWLEDGE')['settings']
    categories = data['workflow_scopes'].get(workflow, data['knowledge_types'])
    return {**data, 'effective_categories': categories,
            'include_archived': historical and data['include_archived_for_history']}


def approved_sources(business_id, workflow=None, at=None, historical=False):
    settings = knowledge_configuration(business_id, workflow, historical)
    allowed = set(settings['effective_categories'])
    if settings['include_archived']:
        candidates = ConfigurationRevision.objects.filter(record__business_id=business_id, record__kind='SOURCE',
            status='ACTIVE', created_at__lte=at or timezone.now())
        latest = candidates.filter(record_id=OuterRef('record_id')).order_by('-version').values('pk')[:1]
        rows = list(candidates.filter(pk=Subquery(latest)).select_related('record'))
    else:
        rows = list(effective_revisions(business_id, 'SOURCE', at))
    ids = [r.data['source_id'] for r in rows if r.data['knowledge_type'] in allowed]
    states = ['ACTIVE', 'ARCHIVED'] if settings['include_archived'] else ['ACTIVE']
    existing = set(KnowledgeSource.objects.filter(business_id=business_id, pk__in=ids, status__in=states).values_list('pk', flat=True))
    return [contract(row) for row in rows if row.data['source_id'] in existing]
