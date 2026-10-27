"""Deterministic configuration acceptance through real authorized API views."""
import hashlib
from datetime import timedelta, timezone

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from app.models import (Business, BusinessAccess, ConfigurationEvent, IntegrationSource, KnowledgeReprocessingRequest,
                        MockExpectedResult, MockScenario, MockScenarioEvent, MonitoringPolicy, OperationAttempt)
from app.observability.views import OperationView, PolicyView
from app.overview.configuration import configuration
from app.overview.views import ConfigurationView
from .integrations import connection_data
from .selectors import (action_policy, ai_configuration, approved_sources, effective_policies, effective_rules,
                        evaluate_rule, knowledge_configuration)
from .views import ConnectionsView, ReprocessingView, ResourceView, SectionView, SourcesView


def request_at(view, method, business_id, actor, at, data=None, **kwargs):
    class FixedView(view):
        def evaluation_time(self):
            return at
    request = getattr(APIRequestFactory(), method)(f'/api/businesses/{business_id}/configuration/', data or {}, format='json')
    force_authenticate(request, user=actor)
    return FixedView.as_view()(request, business_id=business_id, **kwargs)


@transaction.atomic
def run_demo(seed, at, business_slug=None):
    if not 0 <= seed <= 2**63-1:
        raise ValidationError('Seed must be a nonnegative signed 64-bit integer.')
    at = at.astimezone(timezone.utc)
    suffix = hashlib.sha256(at.isoformat().encode()).hexdigest()[:8]
    slug = business_slug or f'config-demo-{seed}-{suffix}'
    if not slug.startswith('config-demo-') or len(slug) > 140:
        raise ValidationError('Demo slugs must use config-demo- and fit 140 characters.')
    key = f'CONFIG:{seed}:{suffix}:{hashlib.sha256(slug.encode()).hexdigest()[:8]}'
    scenario = MockScenario.objects.select_for_update().filter(key=key).first()
    if scenario is None:
        if Business.objects.filter(slug=slug).exists():
            raise ValidationError('Refusing to modify an existing business without this demo ownership marker.')
        business = Business.objects.create(name='Configuration acceptance', slug=slug, created_at=at, updated_at=at)
        scenario = MockScenario.objects.create(business=business, key=key, name='Business Configuration acceptance',
            scenario_type='BUSINESS_CONFIGURATION', seed=seed, start_at=at-timedelta(days=1), end_at=at,
            configuration={'owner': 'configuration-demo-v1'}, created_at=at, updated_at=at)
        refs = build(scenario, at)
        scenario.configuration = {'owner': 'configuration-demo-v1', 'refs': refs}
        scenario.save(update_fields=['configuration'])
    else:
        if scenario.business.slug != slug or scenario.configuration.get('owner') != 'configuration-demo-v1':
            raise ValidationError('Demo ownership mismatch.')
        refs = scenario.configuration['refs']
    return validate(scenario, refs, at)


def build(scenario, at):
    business = scenario.business
    actor = get_user_model().objects.create_user(username=f'config-demo-manager-{business.pk}')
    reader = get_user_model().objects.create_user(username=f'config-demo-reader-{business.pk}')
    BusinessAccess.objects.create(business=business, user=actor, role='MANAGER')
    BusinessAccess.objects.create(business=business, user=reader, role='READER')
    other = Business.objects.create(name='Private demo business', slug=f'{business.slug}-other', created_at=at, updated_at=at)
    refs = {'actor': actor.pk, 'reader': reader.pk, 'other': other.pk}
    def write(view, method, body, **kwargs):
        response = request_at(view, method, business.pk, actor, at, body, **kwargs)
        if response.status_code not in {200, 201}:
            raise ValidationError(f'Demo setup failed for {view.__name__}: {response.data}')
        MockScenarioEvent.objects.create(mock_scenario=scenario, sequence_no=MockScenarioEvent.objects.filter(mock_scenario=scenario).count()+1,
            source_type='CONFIGURATION_API', event_type=method.upper(), event_at=at,
            payload={'view': view.__name__, 'version': response.data.get('version'), 'target_id': response.data.get('id')}, created_at=at)
        return response.data
    write(SectionView, 'put', {'name': 'Example Store', 'industry': 'RETAIL', 'description': 'Coffee and household retail',
        'currency': 'BDT', 'timezone': 'Asia/Dhaka', 'operating_regions': ['Dhaka', 'Gazipur'],
        'channels': ['WEBSITE', 'SOCIAL_COMMERCE']}, section='profile')
    write(SectionView, 'put', {'language': 'bn', 'locale': 'bn-BD', 'reporting_period': 'WEEK', 'week_start': 6}, section='general')
    write(SectionView, 'put', {'enabled': True, 'provider': 'mock', 'models': {'business_assistant': 'mock-business'},
        'features': {'business_assistant': True}, 'confidence_threshold': '0.85',
        'allowed_actions': ['PROPOSE_COURIER_CHANGE']}, section='ai')
    write(SectionView, 'put', {'chunk_size': 700, 'chunk_overlap': 70,
        'workflow_scopes': {'customer_support': ['POLICY', 'SUPPORT']}}, section='knowledge')
    write(ResourceView, 'post', {'key': 'high_delivery_failure', 'status': 'ACTIVE', 'category': 'DELIVERY', 'priority': 10,
        'conditions': {'all': [{'field': 'delivery_failure_rate', 'operator': 'gt', 'value': '15'}]},
        'scope': {'region': 'Gazipur', 'courier': 'Courier X'}, 'sample_metric': 'shipment_count', 'min_samples': 20,
        'window_days': 30, 'outcome': {'type': 'ALERT', 'code': 'HIGH_DELIVERY_FAILURE', 'severity': 'HIGH'}}, section='rules')
    write(ResourceView, 'post', {'key': 'returns', 'status': 'ACTIVE', 'category': 'RETURN', 'title': 'Return policy',
        'terms': 'Unused products may be returned within seven days.', 'ai_available': True,
        'parameters': {'window_days': 7, 'eligibility': ['UNUSED'], 'procedure': 'Contact support'}}, section='policies')
    source, _ = IntegrationSource.objects.get_or_create(key='configuration_demo_commerce', defaults={
        'name': 'Mock commerce', 'category': 'COMMERCE', 'created_at': at, 'updated_at': at})
    conn = write(ConnectionsView, 'post', {'provider_id': source.pk, 'name': 'Demo store', 'enabled': True, 'is_mock': True,
        'entities': ['PRODUCT', 'ORDER'], 'scopes': ['READ_PRODUCTS', 'READ_ORDERS'],
        'credentials': {'api_key': f'env:BIZORA_BUSINESS_{business.pk}_DEMO_COMMERCE'},
        'sync': {'mode': 'INCREMENTAL', 'interval_seconds': 900}})
    refs['connection'] = conn['id']
    attempt = write(OperationView, 'post', {'idempotency_key': 'configuration-demo-check'}, resource='connections', pk=conn['id'], action='connection_test')
    refs['attempt'] = attempt['id']
    source = write(SourcesView, 'post', {'name': 'Approved support manual', 'source_type': 'MANUAL',
        'knowledge_type': 'SUPPORT', 'source_reference': 'manual:support-guide-v1', 'status': 'ACTIVE'})
    refs['source'] = source['id']
    reprocess = write(ReprocessingView, 'post', {'idempotency_key': 'configuration-demo-reembed', 'source_id': source['id'], 'action': 'REEMBED'})
    refs['reprocessing'] = reprocess['id']
    write(ConfigurationView, 'put', {'inherit_reporting_period': True, 'kpis': [{'key': 'realized_revenue', 'direction': 'HIGHER'},
        {'key': 'delivery_failure_rate', 'direction': 'LOWER', 'warning': '10', 'critical': '20', 'warning_severity': 'HIGH'}]}, resource='configuration')
    write(PolicyView, 'put', {'connection_id': conn['id'], 'entity_type': 'ORDER', 'delayed_seconds': 300,
        'stale_seconds': 600, 'max_retries': 2, 'enabled': True})
    return refs


def validate(scenario, refs, at):
    business = Business.objects.get(pk=scenario.business_id)
    actor = get_user_model().objects.get(pk=refs['actor'])
    reader = get_user_model().objects.get(pk=refs['reader'])
    general = request_at(SectionView, 'get', business.pk, actor, at, section='general').data
    ai = ai_configuration(business.pk)
    rules = effective_rules(business.pk, category='DELIVERY', scope={'region': 'Gazipur', 'courier': 'Courier X'}, at=at)
    policies = effective_policies(business.pk, at=at, for_ai=True)
    monitoring = configuration(business.pk)
    reprocess = KnowledgeReprocessingRequest.objects.select_related('configuration_revision').get(pk=refs['reprocessing'])
    from app.models import IntegrationConnection
    connection = IntegrationConnection.objects.select_related('integration_source').get(pk=refs['connection'])
    conn = connection_data(connection)
    invalid = request_at(SectionView, 'put', business.pk, actor, at, {'execution': {'approval_required': False}}, section='ai')
    expectations = [
        ('canonical_profile', ['Example Store', 'BDT', 'Asia/Dhaka'], [business.name, business.currency, business.timezone]),
        ('general_reporting_period', 'WEEK', general['settings']['reporting_period']),
        ('reporting_inheritance', ['WEEK', 6], [monitoring['period'], monitoring['week_start']]),
        ('ai_model', 'mock-business', ai['models'].get('business_assistant')),
        ('ai_confidence', '0.8500', ai['confidence_threshold']),
        ('mandatory_guardrails', [True, False], [ai['guardrails']['external_execution_requires_approval'], ai['guardrails']['ai_may_create_verified_facts']]),
        ('guardrail_override_rejected', 400, invalid.status_code),
        ('action_proposal_requires_approval', [True, True, False], list(action_policy(business.pk, 'PROPOSE_COURIER_CHANGE').values())),
        ('knowledge_chunking', [700, 70], [knowledge_configuration(business.pk)['chunk_size'], knowledge_configuration(business.pk)['chunk_overlap']]),
        ('rule_matches_declared_inputs', 'MATCH', evaluate_rule(rules[0], {'delivery_failure_rate': '17', 'shipment_count': 25})['status'] if rules else 'MISSING'),
        ('rule_minimum_sample', 'INSUFFICIENT_SAMPLE', evaluate_rule(rules[0], {'delivery_failure_rate': '17', 'shipment_count': 10})['status'] if rules else 'MISSING'),
        ('approved_policy_for_ai', 7, policies[0]['settings']['parameters']['window_days'] if policies else None),
        ('approved_knowledge_source', [refs['source']], [r['settings']['source_id'] for r in approved_sources(business.pk, workflow='customer_support', at=at)]),
        ('reprocessing_pins_configuration', ['REQUESTED', 700], [reprocess.status, reprocess.configuration_revision.data['chunk_size']]),
        ('connection_configuration', [True, 900], [connection.is_mock, conn['settings']['sync']['interval_seconds']]),
        ('real_mock_connection_test', 'SUCCEEDED', OperationAttempt.objects.get(pk=refs['attempt']).status),
        ('credential_references_hidden', False, f'BIZORA_BUSINESS_{business.pk}_DEMO_COMMERCE' in str(conn)),
        ('freshness_thresholds', [300, 600, 2], list(MonitoringPolicy.objects.filter(business=business).values_list('delayed_seconds', 'stale_seconds', 'max_retries').get())),
        ('tenant_access', 403, request_at(SectionView, 'get', refs['other'], actor, at, section='profile').status_code),
        ('reader_cannot_configure', 403, request_at(SectionView, 'put', business.pk, reader, at, {'name': 'No'}, section='profile').status_code),
        ('durable_change_events', True, ConfigurationEvent.objects.filter(business=business).count() >= 8),
    ]
    checks = []
    for key, expected, actual in expectations:
        record, _ = MockExpectedResult.objects.get_or_create(mock_scenario=scenario, result_key=key,
            defaults={'result_type': 'BUSINESS_CONFIGURATION', 'expected_value': expected, 'created_at': at})
        checks.append({'key': key, 'expected': record.expected_value, 'actual': actual, 'passed': actual == record.expected_value})
    return {'seed': scenario.seed, 'business_slug': business.slug, 'as_of': at.isoformat(),
            'passed': all(r['passed'] for r in checks), 'checks': checks}
