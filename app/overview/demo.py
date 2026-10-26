"""Reproducible upstream fixtures checked through real monitoring views.

The BI fixture values are declared inputs, not computations performed by Overview.
"""
import hashlib
from datetime import timedelta, timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from app.models import (AiAction, AiRecommendation, AiRecommendationEvidence, Business, BusinessAccess, BusinessIssue,
                        BusinessIssueEvidence, BusinessMetric, BusinessRelationship, Campaign, IntegrationConnection,
                        IntegrationSource, MetricSnapshot, MockExpectedResult, MockScenario, MockScenarioEvent, Order, Shipment)
from app.observability.services import record_observation
from .configuration import save_configuration
from .views import CollectionView, DetailView


@transaction.atomic
def run_demo(seed, at, business_slug=None):
    if not 0 <= seed <= 2**63-1 or at.tzinfo is None:
        raise ValidationError('Use a nonnegative signed 64-bit seed and a timezone-aware time.')
    at = at.astimezone(timezone.utc)
    suffix = hashlib.sha256(at.isoformat().encode()).hexdigest()[:8]
    slug = business_slug or f'overview-demo-{seed}-{suffix}'
    if not slug.startswith('overview-demo-') or len(slug) > 140:
        raise ValidationError('Demo slugs must start with overview-demo- and fit 140 characters.')
    slug_key = hashlib.sha256(slug.encode()).hexdigest()[:8]
    key = f'OVERVIEW:{seed}:{suffix}:{slug_key}'
    scenario = MockScenario.objects.select_for_update().filter(key=key).first()
    if scenario is None:
        if Business.objects.filter(slug=slug).exists():
            raise ValidationError('Refusing to change an existing business without this demo ownership marker.')
        business = Business.objects.create(name=f'Overview demo {seed}', slug=slug, timezone='UTC', created_at=at, updated_at=at)
        scenario = MockScenario.objects.create(business=business, key=key, name='Overview acceptance',
            scenario_type='OVERVIEW_MONITORING', seed=seed, start_at=at-timedelta(days=2), end_at=at,
            configuration={'owner': 'overview-demo-v1'}, created_at=at, updated_at=at)
        refs = _build_inputs(scenario, at)
        scenario.configuration = {'owner': 'overview-demo-v1', 'refs': refs}
        scenario.save(update_fields=['configuration'])
    else:
        if scenario.business.slug != slug or scenario.configuration.get('owner') != 'overview-demo-v1':
            raise ValidationError('Demo ownership mismatch.')
        refs = scenario.configuration['refs']
    return _validate(scenario, refs, at)


def _build_inputs(scenario, at):
    business = scenario.business
    times = {'created_at': at, 'updated_at': at}
    user = get_user_model().objects.create_user(username=f'overview-demo-manager-{business.pk}')
    BusinessAccess.objects.create(business=business, user=user, role='MANAGER')
    refs = {'actor': user.pk}
    for name in ('other', 'empty', 'stale'):
        row = Business.objects.create(name=f'Overview demo {name}', slug=f'{business.slug}-{name}', timezone='UTC', **times)
        refs[name] = row.pk
        if name != 'other':
            BusinessAccess.objects.create(business=row, user=user, role='MANAGER')
    source, _ = IntegrationSource.objects.get_or_create(key='overview_mock_commerce', defaults={
        'name': 'Overview mock commerce', 'category': 'COMMERCE', **times})
    conn = IntegrationConnection.objects.create(business=business, integration_source=source, name='Demo commerce', is_mock=True, **times)
    for key, kind, data in [('check', 'connection_check', {'outcome': 'SUCCESS'}),
                             ('coverage', 'data_confirmed', {'entity_type': 'ORDER', 'source_at': at, 'complete': True})]:
        record_observation(business.pk, conn.pk, f'overview-demo-{key}', kind, data, at, at)
    start = at.replace(hour=0, minute=0, second=0, microsecond=0)-timedelta(days=1)
    end = start+timedelta(days=1)
    declared = [('total_revenue', 'sales', 100, 105, 'BDT'), ('realized_revenue', 'sales', 100, 105, 'BDT'),
        ('order_count', 'sales', 100, 121, 'COUNT'), ('marketing_spend', 'marketing', 100, 118, 'BDT'),
        ('new_customers', 'customers', 100, 120, 'COUNT'), ('website_conversion_rate', 'website', 2, 2.1, '%'),
        ('unresolved_conversations', 'support', 30, 35, 'COUNT'), ('delivery_failure_rate', 'delivery', 9, 20, '%'),
        ('return_rate', 'delivery', 9, 11.52, '%'), ('refunded_revenue', 'payments', 100, 124, 'BDT')]
    points = {}
    for key, domain, previous, current, unit in declared:
        definition = BusinessMetric.objects.create(business=business, key=key, name=key.replace('_', ' ').title(),
            category=domain.upper(), unit=unit, **times)
        for value, left, right in [(previous, start-timedelta(days=1), start), (current, start, end)]:
            point = MetricSnapshot.objects.create(business=business, metric=definition, value=str(value), period_type='DAY',
                period_start=left, period_end=right, calculated_at=at, calculation_rule='demo.declared_bi_input.v1', created_at=at)
            points[key] = point
        MockScenarioEvent.objects.create(mock_scenario=scenario, sequence_no=len(points), source_type='BI_FIXTURE',
            event_type='DECLARED_METRIC_INPUT', event_at=at, payload={'metric': key, 'previous': previous, 'current': current,
                                                                     'snapshot_id': points[key].pk}, created_at=at)
    order = Order.objects.create(business=business, order_number='DEMO-1', status='COMPLETED', **times)
    shipment = Shipment.objects.create(business=business, order=order, provider='Courier X', status='FAILED', **times)
    campaign = Campaign.objects.create(business=business, name='Campaign A', platform='MOCK', **times)
    relationship = BusinessRelationship.objects.create(business=business, source_entity_type='campaign',
        source_entity_id=campaign.pk, target_entity_type='shipment', target_entity_id=shipment.pk,
        relationship_type='ATTRIBUTED_DELIVERY', rule_key='demo.attribution.v1', **times)
    row = BusinessIssue.objects.create(business=business, issue_type='HIGH_DELIVERY_FAILURE', title='Gazipur delivery failures',
        description='Additional demand is losing value through failed deliveries and refunds.', severity='HIGH',
        subject_entity_type='shipment', subject_entity_id=shipment.pk, detected_at=at-timedelta(minutes=20),
        metadata={'domains': ['marketing', 'delivery', 'sales', 'payments'], 'trend': 'WORSENING', 'region': 'Gazipur',
                  'courier': 'Courier X', 'monitoring_scenarios': ['marketing_delivery', 'courier_revenue']}, **times)
    BusinessIssueEvidence.objects.create(business_issue=row, relationship=relationship, evidence_type='RELATIONSHIP', created_at=at)
    for key in ('delivery_failure_rate', 'realized_revenue', 'refunded_revenue'):
        BusinessIssueEvidence.objects.create(business_issue=row, metric_snapshot=points[key], evidence_type='METRIC', created_at=at)
    rec = AiRecommendation.objects.create(business=business, business_issue=row, recommendation_type='COURIER_ALLOCATION',
        title='Test alternative courier allocation', description='Try a smaller alternate allocation for Gazipur orders.',
        rationale='Stored AI recommendation grounded in the existing delivery issue.', confidence='.9', priority='HIGH',
        suggested_action_type='ALLOCATE_COURIER', generated_at=at-timedelta(minutes=10),
        metadata={'goals': ['Reduce delivery failure']}, **times)
    AiRecommendationEvidence.objects.create(ai_recommendation=rec, business_issue=row,
        metric_snapshot=points['delivery_failure_rate'], business_relationship=relationship, evidence_type='BUSINESS_CONTEXT', created_at=at)
    AiAction.objects.create(business=business, ai_recommendation=rec, action_type='ALLOCATE_COURIER',
        action_payload={'region': 'Gazipur', 'allocation_percent': 10}, **times)
    rules = [{'key': key, 'direction': 'NEUTRAL'} for key, *_ in declared]
    next(r for r in rules if r['key'] == 'delivery_failure_rate').update(direction='LOWER', warning='10', critical='25',
        target_max='9', goal='Reduce delivery failure', sources=[{'connection_id': conn.pk, 'entity_type': 'ORDER'}])
    save_configuration(business.pk, user, {'kpis': rules}, at)
    stale = Business.objects.get(pk=refs['stale'])
    definition = BusinessMetric.objects.create(business=stale, key='total_revenue', name='Revenue', category='SALES', **times)
    MetricSnapshot.objects.create(business=stale, metric=definition, value=100, period_start=start, period_end=end,
        period_type='DAY', calculated_at=end, created_at=end)
    stale_conn = IntegrationConnection.objects.create(business=stale, integration_source=source,
        name='Stale demo source', is_mock=True, **times)
    record_observation(stale.pk, stale_conn.pk, 'old-coverage', 'data_confirmed',
        {'entity_type': 'ORDER', 'source_at': at-timedelta(hours=2), 'complete': True}, at, at)
    save_configuration(stale.pk, user, {'domains': ['sales'], 'snapshot_ttl_seconds': 60,
        'kpis': [{'key': 'total_revenue', 'target_min': '10',
                  'sources': [{'connection_id': stale_conn.pk, 'entity_type': 'ORDER'}]}]}, at)
    refs.update(issue=row.pk, recommendation=rec.pk, snapshot=points['delivery_failure_rate'].pk)
    return refs


def _validate(scenario, refs, at):
    actor = get_user_model().objects.get(pk=refs['actor'])
    class FixedCollection(CollectionView):
        def evaluation_time(self):
            return at
    class FixedDetail(DetailView):
        def evaluation_time(self):
            return at
    factory = APIRequestFactory()
    def get(resource, business_id=scenario.business_id, pk=None):
        request = factory.get(f'/api/businesses/{business_id}/overview/{resource}/')
        force_authenticate(request, user=actor)
        view = FixedDetail if pk is not None else FixedCollection
        kwargs = {'business_id': business_id, 'resource': resource, **({'pk': pk} if pk is not None else {})}
        return view.as_view()(request, **kwargs)
    summary = get('summary').data
    kpis = {row['key']: row for row in summary['kpis']}
    cross = {row['key']: row for row in get('cross-domain').data['results']}
    rec = get('recommendations', pk=refs['recommendation']).data
    expectations = [
        ('business_health', 'WARNING', summary['health']['status']),
        ('order_growth', '21.000000', kpis['order_count']['comparison']['percent_change']),
        ('realized_revenue_growth', '5.000000', kpis['realized_revenue']['comparison']['percent_change']),
        ('marketing_growth', '18.000000', kpis['marketing_spend']['comparison']['percent_change']),
        ('delivery_failure_context', ['9.000000', '20.000000'], [kpis['delivery_failure_rate']['comparison']['previous_value'], kpis['delivery_failure_rate']['value']]),
        ('refunded_revenue_growth', '24.000000', kpis['refunded_revenue']['comparison']['percent_change']),
        ('cross_domain_issue', [refs['issue']], [row['id'] for row in cross['marketing_delivery']['issues']]),
        ('courier_revenue_context', 'REQUIRES_ATTENTION', cross['courier_revenue']['status']),
        ('stored_recommendation', refs['issue'], rec['issue']['id'] if rec['issue'] else None),
        ('goal_alignment', ['Reduce delivery failure'], rec['goals']),
        ('source_freshness', 'FRESH', kpis['delivery_failure_rate']['sources'][0]['status']),
        ('recent_activity', True, bool(get('activity').data['results'])),
        ('empty_business_health', 'UNKNOWN', get('health', refs['empty']).data['status']),
        ('stale_business_health', 'UNKNOWN', get('health', refs['stale']).data['status']),
        ('tenant_access', 403, get('summary', refs['other']).status_code),
        ('evidence_drilldown', 200, get('snapshots', pk=refs['snapshot']).status_code),
    ]
    checks = []
    for key, expected, actual in expectations:
        row, _ = MockExpectedResult.objects.get_or_create(mock_scenario=scenario, result_key=key,
            defaults={'result_type': 'OVERVIEW_MONITORING', 'expected_value': expected, 'created_at': at})
        checks.append({'key': key, 'expected': row.expected_value, 'actual': actual, 'passed': actual == row.expected_value})
    return {'seed': scenario.seed, 'business_slug': scenario.business.slug, 'as_of': at.isoformat(),
            'passed': all(row['passed'] for row in checks), 'checks': checks}
