"""Bounded projections over observed evidence, independent of provider execution."""
from datetime import timedelta

from django.db.models import Avg, Count, Max, OuterRef, Q, Subquery, Case, When, Value, DateTimeField

from app.models import (ConnectionCheck, FailedRecord, IntegrationError, IntegrationSyncLog,
                        MonitoringPolicy, ProviderRequest, SourceFreshness, WebhookObservation)
from .policies import freshness, classify_provider


class Policies:
    def __init__(self, business_id):
        self.rows = list(MonitoringPolicy.objects.filter(business_id=business_id))
        self.default = MonitoringPolicy()

    def get(self, connection_id=None, entity_type=''):
        matching = [p for p in self.rows if p.connection_id in {None, connection_id}
                    and p.entity_type in {'', entity_type}]
        return max(matching, key=lambda p: (p.connection_id is not None, bool(p.entity_type)), default=self.default)


def _latest(query):
    return query.filter(pk=Subquery(query.filter(connection_id=OuterRef('connection_id'))
                                   .order_by('-observed_at', '-pk').values('pk')[:1]))


def connection_snapshots(connections, now):
    connections = list(connections)
    if not connections:
        return []
    ids = [c.pk for c in connections]
    policies = Policies(connections[0].business_id)
    checks = ConnectionCheck.objects.filter(connection_id__in=ids, observed_at__lte=now)
    requests = ProviderRequest.objects.filter(connection_id__in=ids, observed_at__lte=now)
    latest_checks = {r.connection_id: r for r in _latest(checks)}
    latest_requests = {r.connection_id: r for r in _latest(requests)}
    communication = {}
    for query in [checks, requests]:
        for r in query.values('connection_id').annotate(
                successful=Max('observed_at', filter=Q(outcome='SUCCESS')),
                failed=Max('observed_at', filter=~Q(outcome='SUCCESS'))):
            dates = communication.setdefault(r['connection_id'], {'successful': None, 'failed': None})
            for key in dates:
                dates[key] = max(filter(None, [dates[key], r[key]]), default=None)
    thresholds = Case(*[When(connection_id=c.pk, then=Value(now - timedelta(
        seconds=policies.get(c.pk).window_seconds))) for c in connections], output_field=DateTimeField())
    patterns = {r['connection_id']: r for r in requests.filter(observed_at__gte=thresholds).values('connection_id').annotate(
        samples=Count('id'), failures=Count('id', filter=~Q(outcome='SUCCESS')), average=Avg('latency_ms'))}
    hooks = {r['connection_id']: r for r in WebhookObservation.objects.filter(
        connection_id__in=ids, received_at__gte=thresholds, received_at__lte=now).values('connection_id').annotate(
            failed=Count('id', filter=Q(status__in=['FAILED', 'REJECTED'])),
            last_failure=Max('received_at', filter=Q(status__in=['FAILED', 'REJECTED'])),
            last_success=Max('processed_at', filter=Q(status='PROCESSED')))}
    failures = {r['connection_id']: r['count'] for r in FailedRecord.objects.filter(
        connection_id__in=ids, last_seen_at__gte=thresholds, last_seen_at__lte=now).exclude(
            status='RESOLVED', resolution_method='PROCESSING').values('connection_id').annotate(count=Count('id'))}
    errors = {r['connection_id']: r for r in IntegrationError.objects.filter(connection_id__in=ids,
        last_seen_at__lte=now).values('connection_id').annotate(
            active=Count('id', filter=Q(status__in=['ACTIVE', 'ACKNOWLEDGED'])),
            recent=Count('id', filter=Q(last_seen_at__gte=thresholds)),
            last_failure=Max('last_seen_at'))}
    runs = IntegrationSyncLog.objects.filter(integration_connection_id__in=ids, last_observed_at__lte=now)
    latest_runs = {r.integration_connection_id: r for r in runs.filter(pk=Subquery(
        runs.filter(integration_connection_id=OuterRef('integration_connection_id')).order_by('-last_observed_at', '-pk')
        .values('pk')[:1]))}
    coverage = {(r.connection_id, r.entity_type): r for r in SourceFreshness.objects.filter(connection_id__in=ids)}
    entity_types = {c.pk: set() for c in connections}
    for connection_id, entity_type in coverage:
        entity_types[connection_id].add(entity_type)
    for r in runs.exclude(entity_type='').values('integration_connection_id', 'entity_type').distinct():
        entity_types[r['integration_connection_id']].add(r['entity_type'])
    for c in connections:
        entity_types[c.pk].update(p.entity_type for p in policies.rows
                                  if p.entity_type and p.connection_id in {None, c.pk})
    output = []
    for c in connections:
        policy = policies.get(c.pk)
        latest = max(filter(None, [latest_checks.get(c.pk), latest_requests.get(c.pk)]),
                     key=lambda r: (r.observed_at, r.pk), default=None)
        health = {'status': 'UNKNOWN', 'reason': 'NO_RECENT_OBSERVATION', 'authentication': 'UNKNOWN',
                  'credential_status': 'UNKNOWN', 'observed_at': latest.observed_at if latest else None,
                  'latency_ms': latest.latency_ms if latest else None}
        check = latest_checks.get(c.pk)
        if check and (now - check.observed_at).total_seconds() <= policy.observation_ttl_seconds:
            health.update(authentication=check.authentication, credential_status=check.credential_status)
        if latest and (now - latest.observed_at).total_seconds() <= policy.observation_ttl_seconds:
            status = 'HEALTHY' if latest.outcome == 'SUCCESS' else (
                'ERROR' if latest.outcome in {'AUTH_ERROR', 'EXPIRED', 'ERROR'} else 'DEGRADED')
            health.update(status=status, reason=latest.outcome)
            if latest.outcome == 'AUTH_ERROR':
                health.update(authentication='INVALID', credential_status='INVALID')
            if latest.latency_ms is not None and latest.latency_ms > policy.latency_ms and status == 'HEALTHY':
                health.update(status='DEGRADED', reason='HIGH_LATENCY')
        pattern = patterns.get(c.pk)
        if pattern and pattern['samples'] >= policy.min_samples and health['status'] == 'HEALTHY' and (
                pattern['failures'] / pattern['samples'] >= policy.error_ratio):
            health.update(status='DEGRADED', reason='ELEVATED_REQUEST_ERROR_RATE')
        rate_limit = {'status': 'UNKNOWN', 'remaining': None, 'retry_after_seconds': None, 'quota_scope': None}
        request = latest_requests.get(c.pk)
        if request and (now - request.observed_at).total_seconds() <= policy.observation_ttl_seconds:
            remaining = request.rate_limit_remaining
            rate_status = ('EXHAUSTED' if remaining == 0 or request.outcome == 'RATE_LIMIT' else
                           'APPROACHING' if remaining is not None and remaining <= 10 else
                           'AVAILABLE' if remaining is not None else 'UNKNOWN')
            rate_limit.update(status=rate_status, remaining=remaining, retry_after_seconds=request.retry_after_seconds,
                              quota_scope=request.quota_scope)
            if rate_status in {'APPROACHING', 'EXHAUSTED'} and health['status'] != 'ERROR':
                health.update(status='DEGRADED', reason='RATE_LIMIT_' + rate_status)
        hook = hooks.get(c.pk, {})
        run = latest_runs.get(c.pk)
        if health['status'] not in {'ERROR'}:
            if hook.get('failed'):
                health.update(status='DEGRADED', reason='WEBHOOK_PROCESSING_FAILURES')
            elif failures.get(c.pk):
                health.update(status='DEGRADED', reason='FAILED_RECORDS')
            elif run and run.status in {'FAILED', 'PARTIAL'} and (
                    now - run.last_observed_at).total_seconds() <= policy.observation_ttl_seconds:
                health.update(status='ERROR' if run.status == 'FAILED' else 'DEGRADED', reason='SYNC_FAILURES')
            elif run and run.status in {'PENDING', 'RUNNING'} and (
                    now - run.last_observed_at).total_seconds() > policy.sync_timeout_seconds:
                health.update(status='DEGRADED', reason='SYNC_STALLED')
        if c.status == 'EXPIRED':
            health.update(status='ERROR', reason='CREDENTIAL_EXPIRED', authentication='EXPIRED', credential_status='EXPIRED')
        freshness_rows = []
        for entity in sorted(entity_types[c.pk]):
            item = coverage.get((c.pk, entity))
            p = policies.get(c.pk, entity)
            result = freshness(item.coverage_at if item else None, now, p.delayed_seconds, p.stale_seconds)
            result.update(connection_id=c.pk, provider_id=c.integration_source_id, entity_type=entity,
                          last_received_at=item.received_at if item else None,
                          confirmed_at=item.confirmed_at if item else None, complete=item.complete if item else False,
                          monitoring_enabled=p.enabled and c.status != 'DISABLED',
                          evidence={'freshness_id': item.pk if item else None})
            result['warning'] = result['status'] != 'FRESH' or not result['complete']
            freshness_rows.append(result)
        summary = health['status']
        summary_reason = health['reason']
        monitored_data = [r for r in freshness_rows if r['monitoring_enabled']]
        if summary not in {'ERROR', 'DEGRADED'}:
            if any(r['status'] == 'STALE' for r in monitored_data):
                summary, summary_reason = 'STALE', 'EXPECTED_UPDATE_OVERDUE'
            elif any(r['status'] == 'DELAYED' or (r['status'] == 'FRESH' and not r['complete']) for r in monitored_data):
                summary, summary_reason = 'DEGRADED', 'INCOMPLETE_OR_DELAYED_DATA'
            elif any(r['status'] == 'UNAVAILABLE' for r in monitored_data):
                summary, summary_reason = 'UNKNOWN', 'NO_CONFIRMED_DATA'
        if c.status in {'DISABLED', 'DISCONNECTED'}:
            summary, summary_reason = 'DISCONNECTED', c.status
            health.update(status='UNKNOWN', reason=c.status)
        output.append({'id': c.pk, 'business_id': c.business_id, 'provider_id': c.integration_source_id,
            'provider': c.integration_source.name, 'name': c.name, 'lifecycle_status': c.status,
            'is_mock': c.is_mock, 'health': health, 'summary_status': summary, 'summary_reason': summary_reason, 'freshness': freshness_rows,
            'rate_limit': rate_limit,
            'last_successful_connection': communication.get(c.pk, {}).get('successful'),
            'last_failure': max(filter(None, [communication.get(c.pk, {}).get('failed'),
                errors.get(c.pk, {}).get('last_failure')]), default=None),
            'errors': errors.get(c.pk, {'active': 0, 'recent': 0}), 'failed_events': hook.get('failed', 0),
            'monitoring_enabled': policy.enabled and c.status != 'DISABLED',
            'as_of': now, 'business_timezone': c.business.timezone})
    return output


def reliability_summary(connections, now):
    rows = connection_snapshots(connections, now)
    active = [r for r in rows if r['monitoring_enabled']]
    priority = {'ERROR': 0, 'DEGRADED': 1, 'STALE': 2, 'DISCONNECTED': 3, 'UNKNOWN': 4, 'HEALTHY': 5}
    overall = min(active, key=lambda r: priority[r['summary_status']])['summary_status'] if active else 'UNKNOWN'
    problems = [{'connection_id': r['id'], 'provider': r['provider'], 'status': r['summary_status'],
                 'reason': r['summary_reason'], 'failed_events': r['failed_events'],
                 'freshness': r['freshness'], 'impact': 'New source data may be incomplete or outdated.'}
                for r in active if r['summary_status'] != 'HEALTHY']
    return {'status': overall, 'as_of': now, 'connection_count': len(rows),
            'failed_webhooks': sum(r['failed_events'] for r in active),
            'active_error_groups': sum(r['errors']['active'] for r in active), 'problems': problems}


def provider_snapshots(sources, business_id, now, privileged=False):
    sources = list(sources)
    if not sources:
        return []
    policy = Policies(business_id).get()
    query = ProviderRequest.objects.filter(connection__integration_source_id__in=[s.pk for s in sources],
        observed_at__gte=now - timedelta(seconds=policy.window_seconds), observed_at__lte=now)
    # Shared service evidence is safe to classify; tenant-owned endpoints remain local.
    query = query.filter(Q(target='GLOBAL') | Q(business_id=business_id)) if not privileged else query
    usable = ~Q(outcome='AUTH_ERROR') & ~(Q(outcome='RATE_LIMIT') & Q(quota_scope='CONNECTION'))
    aggregates = query.values('connection__integration_source_id', 'capability', 'target').annotate(
        samples=Count('id', filter=usable), connections=Count('connection_id', distinct=True, filter=usable),
        failures=Count('id', filter=usable & Q(outcome__in=['PROVIDER_ERROR', 'TIMEOUT', 'CONNECTIVITY_ERROR'])),
        limited=Count('id', filter=usable & Q(outcome='RATE_LIMIT')), average=Avg('latency_ms', filter=usable),
        local_samples=Count('id', filter=usable & Q(business_id=business_id)))
    groups = {}
    for row in aggregates:
        result = classify_provider(row['samples'], row['connections'], row['failures'], row['limited'], row['average'],
            policy.min_samples, policy.min_connections, policy.error_ratio, policy.latency_ms)
        if not privileged:
            result = {k: result[k] for k in ('status', 'reason')}
            result['local_sample_count'] = row['local_samples']
        result.update(capability=row['capability'], target=row['target'], evidence_scope='AGGREGATED_PROVIDER',
                      as_of=now, window_seconds=policy.window_seconds)
        groups.setdefault(row['connection__integration_source_id'], []).append(result)
    output = []
    priorities = {'UNAVAILABLE': 0, 'DEGRADED': 1, 'UNKNOWN': 2, 'HEALTHY': 3}
    for source in sources:
        capabilities = groups.get(source.pk, [])
        status = min(capabilities, key=lambda r: priorities[r['status']])['status'] if capabilities else 'UNKNOWN'
        output.append({'id': source.pk, 'key': source.key, 'name': source.name, 'status': status,
                       'capabilities': capabilities, 'as_of': now})
    return output
