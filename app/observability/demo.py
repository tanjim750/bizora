"""Reproducible inputs and independently checked expectations, using real module paths."""
import hashlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from app.integrations.payloads import capture_payload
from app.models import (Business, BusinessAccess, FailedRecord, IntegrationConnection, IntegrationError,
                        IntegrationSource, IntegrationSyncLog, MockExpectedResult, MockScenario,
                        MockScenarioEvent, Order, SourceFreshness)
from .operations import execute_operation
from .selectors import connection_snapshots, provider_snapshots
from .services import record_observation


@transaction.atomic
def run_demo(seed, at, business_slug=None):
    if not 0 <= seed <= 2**63 - 1:
        raise ValidationError('Seed must be a nonnegative signed 64-bit integer.')
    suffix = hashlib.sha256(at.isoformat().encode()).hexdigest()[:8]
    slug = business_slug or f'obs-demo-{seed}-{suffix}'
    if not slug.startswith('obs-demo-') or len(slug) > 150:
        raise ValidationError('Demo business slugs must start with obs-demo- and fit 150 characters.')
    slug_key = hashlib.sha256(slug.encode()).hexdigest()[:8]
    scenario_key = f'OBSERVABILITY:{seed}:{suffix}:{slug_key}'
    scenario = MockScenario.objects.select_for_update().filter(key=scenario_key).first()
    if scenario is None:
        if Business.objects.filter(slug=slug).exists():
            raise ValidationError('Refusing to modify an existing business without this demo ownership marker.')
        business = Business.objects.create(name=f'Observability demo {seed}', slug=slug, created_at=at, updated_at=at)
        scenario = MockScenario.objects.create(business=business, key=scenario_key, name='Observability acceptance',
            scenario_type='INTEGRATION_OBSERVABILITY', seed=seed, start_at=at - timedelta(hours=3), end_at=at,
            configuration={'owner': 'obs-demo-v1'}, created_at=at, updated_at=at)
        refs = _build_inputs(scenario, at)
        scenario.configuration = {'owner': 'obs-demo-v1', 'refs': refs}
        scenario.save(update_fields=['configuration'])
    else:
        if scenario.configuration.get('owner') != 'obs-demo-v1' or scenario.business.slug != slug:
            raise ValidationError('Demo ownership mismatch.')
        refs = scenario.configuration['refs']
    return _validate(scenario, refs, at)


def _build_inputs(scenario, at):
    business = scenario.business
    user = get_user_model().objects.create_user(username=f'obs-demo-manager-{business.pk}')
    BusinessAccess.objects.create(business=business, user=user, role='MANAGER')
    other = Business.objects.create(name='Private second demo tenant', slug=f'{business.slug}-other', created_at=at, updated_at=at)
    refs = {'actor': user.pk, 'other_business': other.pk}
    def source(key, name, category):
        return IntegrationSource.objects.get_or_create(key=key, defaults=dict(name=name, category=category,
                                                        created_at=at, updated_at=at))[0]
    woo = source('woocommerce', 'WooCommerce', 'COMMERCE')
    meta = source('meta_ads', 'Meta Ads', 'MARKETING')
    ga4 = source('ga4', 'GA4', 'ANALYTICS')
    def connection(name, provider, owner=business):
        return IntegrationConnection.objects.create(business=owner, integration_source=provider, name=name,
                                                     is_mock=True, created_at=at, updated_at=at)
    def observe(conn, key, kind, data, when=at):
        receipt = record_observation(conn.business_id, conn.pk, key, kind, data, when, at)
        MockScenarioEvent.objects.create(mock_scenario=scenario, sequence_no=MockScenarioEvent.objects.filter(
            mock_scenario=scenario).count() + 1, source_type=conn.integration_source.key, event_type=kind,
            event_at=when, payload={'observation_key': key, 'kind': kind, 'connection_id': conn.pk}, created_at=at)
        return receipt
    def operate(conn, resource, target, action, key):
        return execute_operation(business.pk, resource, target, action, key, user, now=at)
    def failed(conn, key, payload):
        return observe(conn, key, 'failed_record', dict(entity_type='PRODUCT', external_id=str(payload.body['id']),
            stage='MAPPING', code='MAPPING_ERROR', payload_id=payload.pk)).object_id

    healthy = connection('Healthy', woo)
    refs['healthy'] = healthy.pk
    payload = capture_payload(healthy.pk, 'healthy-product', {'id': f'{scenario.seed}-healthy', 'name': 'Demo coffee'},
                              received_at=at - timedelta(seconds=60), source_at=at - timedelta(seconds=120))
    operate(healthy, 'failed-records', failed(healthy, 'historical-mapping-failure', payload), 'record_retry', 'healthy-retry')
    operate(healthy, 'connections', healthy.pk, 'connection_test', 'healthy-check')

    partial = connection('Partial sync', woo)
    refs['partial'] = partial.pk
    payloads = [capture_payload(partial.pk, f'product-{i}', {'id': f'{scenario.seed}-{i}', 'name': f'Demo product {i}'},
                received_at=at, source_at=at - timedelta(seconds=60)) for i in range(8)]
    payloads += [capture_payload(partial.pk, 'late-duplicate', {'id': f'{scenario.seed}-0', 'name': 'Old value'},
                received_at=at, source_at=at - timedelta(seconds=120)),
                 capture_payload(partial.pk, 'bad-product', {'id': f'{scenario.seed}-bad'}, received_at=at)]
    original = observe(partial, 'failed-sync', 'sync', dict(status='FAILED', entity_type='PRODUCT',
        records_received=10, records_failed=10, metadata={'payload_ids': [p.pk for p in payloads]}))
    attempt = operate(partial, 'syncs', original.object_id, 'sync_retry', 'retry-partial-sync')
    refs['partial_run'] = attempt.result['sync_id']

    hooks = connection('Webhook failures', woo)
    refs['hooks'] = hooks.pk
    observe(hooks, 'successful-check', 'connection_check', {'outcome': 'SUCCESS'})
    # A historical canonical order is fixture context; newly received products above
    # exercise normalization/persistence. Observability itself does not own orders.
    Order.objects.create(business=business, integration_connection=hooks, external_order_id=f'{scenario.seed}-old-order',
                         ordered_at=at - timedelta(minutes=52), created_at=at - timedelta(minutes=52), updated_at=at - timedelta(minutes=52))
    observe(hooks, 'previous-order-confirmed', 'data_confirmed', {'entity_type': 'ORDER', 'source_at': at - timedelta(minutes=52)})
    for i in range(37):
        observe(hooks, f'invalid-hook-{i}', 'webhook', {'event_id': f'{scenario.seed}-hook-{i}',
            'event_type': 'order.created', 'entity_type': 'ORDER', 'validation': 'INVALID'})

    auth = connection('Expired Meta token', meta)
    refs['auth'] = auth.pk
    observe(auth, 'invalid-token', 'connection_check', {'outcome': 'AUTH_ERROR'})
    outage = connection('GA4 outage', ga4)
    other_outage = connection('Private GA4 account', ga4, other)
    refs['outage'] = outage.pk
    for i, conn in enumerate([outage, other_outage, other_outage]):
        observe(conn, f'provider-error-{i}', 'provider_request', {'outcome': 'PROVIDER_ERROR',
                'http_status': 503, 'capability': 'analytics', 'target': 'GLOBAL', 'latency_ms': 4000})

    replay = connection('Freshness replay', woo)
    refs['replay'] = replay.pk
    old = capture_payload(replay.pk, 'old-product', {'id': f'{scenario.seed}-replay', 'name': 'Old product'},
                          received_at=at - timedelta(hours=1), source_at=at - timedelta(hours=2))
    old_attempt = operate(replay, 'failed-records', failed(replay, 'old-product-failure', old), 'record_retry', 'replay-old')
    refs['old_attempt'] = old_attempt.pk
    refs['old_was_stale'] = connection_snapshots([IntegrationConnection.objects.select_related('business', 'integration_source').get(pk=replay.pk)], at)[0]['freshness'][0]['status'] == 'STALE'
    new = capture_payload(replay.pk, 'new-product', {'id': f'{scenario.seed}-replay', 'name': 'Current product'},
                          received_at=at, source_at=at)
    operate(replay, 'failed-records', failed(replay, 'new-product-failure', new), 'record_retry', 'replay-new')
    return refs


def _validate(scenario, refs, at):
    from app.models import OperationAttempt
    business = scenario.business
    connections = IntegrationConnection.objects.filter(business=business).select_related('business', 'integration_source')
    snapshots = {r['id']: r for r in connection_snapshots(connections, at)}
    run = IntegrationSyncLog.objects.get(pk=refs['partial_run'])
    hook = snapshots[refs['hooks']]
    hook_error = IntegrationError.objects.filter(connection_id=refs['hooks'], code='WEBHOOK_SIGNATURE_INVALID').first()
    actor = get_user_model().objects.get(pk=refs['actor'])
    from .views import SummaryView
    request = APIRequestFactory().get(f"/api/businesses/{refs['other_business']}/observability/summary/")
    force_authenticate(request, user=actor)
    denied = SummaryView.as_view()(request, business_id=refs['other_business'])
    sources = IntegrationSource.objects.filter(integrationconnection__business=business).distinct()
    providers = {r['key']: r for r in provider_snapshots(sources, business.pk, at)}
    old = OperationAttempt.objects.get(pk=refs['old_attempt'])
    expectations = [
        ('healthy_connection', 'HEALTHY', snapshots[refs['healthy']]['health']['status']),
        ('healthy_freshness', 'FRESH', snapshots[refs['healthy']]['freshness'][0]['status']),
        ('partial_sync_accounting', [10, 8, 1, 1, 'PARTIAL'],
            [run.records_processed, run.records_succeeded, run.records_skipped, run.records_failed, run.status]),
        ('partial_data_warning', False, SourceFreshness.objects.get(connection_id=refs['partial']).complete),
        ('webhook_connection', 'DEGRADED', hook['health']['status']),
        ('failed_webhooks', 37, hook['failed_events']),
        ('webhook_error_occurrences', 37, hook_error.occurrences if hook_error else 0),
        ('order_freshness', 'STALE', hook['freshness'][0]['status']),
        ('isolated_authentication', ['ERROR', 'UNKNOWN'], [snapshots[refs['auth']]['health']['status'], providers['meta_ads']['status']]),
        ('provider_outage', 'UNAVAILABLE', providers['ga4']['status']),
        ('old_replay_remained_old', [True, (at - timedelta(hours=2)).isoformat()],
            [refs['old_was_stale'], old.result.get('source_at')]),
        ('new_source_restores_freshness', 'FRESH', snapshots[refs['replay']]['freshness'][0]['status']),
        ('business_access_boundary', 403, denied.status_code),
    ]
    checks = []
    for key, expected, actual in expectations:
        definition, _ = MockExpectedResult.objects.get_or_create(mock_scenario=scenario, result_key=key,
            defaults=dict(result_type='OBSERVABILITY', expected_value=expected, created_at=at))
        checks.append({'key': key, 'expected': definition.expected_value, 'actual': actual,
                       'passed': definition.expected_value == actual})
    return {'seed': scenario.seed, 'business_slug': business.slug, 'as_of': at.isoformat(),
            'passed': all(row['passed'] for row in checks), 'checks': checks}
