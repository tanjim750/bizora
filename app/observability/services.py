"""Atomic observation recording. Only integration/processing owners publish these inputs."""
import hashlib
import json
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from app.models import (ConnectionCheck, FailedRecord, IntegrationConnection, IntegrationError,
                        IntegrationPayload, IntegrationSyncLog, ObservationReceipt,
                        ObservabilityAudit, ProviderRequest, SourceFreshness,
                        WebhookDelivery, WebhookObservation)
from .policies import safe_details


KINDS = {'connection_check', 'provider_request', 'sync', 'failed_record', 'webhook',
         'data_confirmed', 'integration_error'}
TERMINAL = {'COMPLETED', 'PARTIAL', 'FAILED'}


def digest(value):
    try:
        encoded = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise ValidationError('Observation must contain JSON-compatible values.') from exc
    if len(encoded) > 65536:
        raise ValidationError('Observation exceeds 64 KiB; use a payload reference.')
    return hashlib.sha256(encoded).hexdigest()


def timestamp(value, field='timestamp'):
    if isinstance(value, str):
        value = parse_datetime(value)
    if not isinstance(value, datetime) or timezone.is_naive(value):
        raise ValidationError({field: 'A timezone-aware timestamp is required.'})
    return value


def text(data, field, default=None, limit=100):
    value = data.get(field, default)
    if not isinstance(value, str) or (not value and default is None) or len(value) > limit:
        raise ValidationError({field: f'A string of at most {limit} characters is required.'})
    return value


def integer(data, field, default=None, maximum=None):
    value = data.get(field, default)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (maximum is not None and value > maximum):
        raise ValidationError({field: 'A nonnegative integer in the supported range is required.'})
    return value


def enum(data, field, values, default=None):
    value = data.get(field, default)
    if value not in values.split():
        raise ValidationError({field: f'Expected one of: {values}.'})
    return value


def scoped_connection(business_id, connection_id, lock=False):
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
           for value in (business_id, connection_id)):
        raise ValidationError('Business and connection identifiers must be positive integers.')
    query = IntegrationConnection.objects.select_related('integration_source', 'business')
    if lock:
        # Lock only this row, not joined business/provider rows on PostgreSQL.
        query = query.select_for_update(of=('self',))
    try:
        return query.get(pk=connection_id, business_id=business_id)
    except IntegrationConnection.DoesNotExist as exc:
        raise ValidationError('Connection does not belong to the selected business.') from exc


def related(model, value, connection):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError('Related object identifiers must be integers.')
    field = 'integration_connection_id' if model is IntegrationSyncLog else 'connection_id'
    try:
        return model.objects.get(pk=value, **{field: connection.pk})
    except model.DoesNotExist as exc:
        raise ValidationError('Related object does not belong to this connection.') from exc


def create_validated(model, **kwargs):
    row = model(**kwargs)
    row.full_clean(validate_unique=False, validate_constraints=False)
    row.save()
    return row


def scoped_values(connection):
    return {'business_id': connection.business_id, 'connection': connection}


def audit(connection, target_type, target_id, action, before='', after='', actor=None, note='', at=None):
    return ObservabilityAudit.objects.create(**scoped_values(connection), target_type=target_type,
        target_id=target_id, action=action, from_status=before, to_status=after, actor=actor,
        note=safe_details(note), created_at=at or timezone.now())


def _error(connection, data, at, *, sync=None, webhook=None):
    code = text(data, 'code')
    category = enum(data, 'category',
        'AUTHENTICATION CONNECTIVITY PROVIDER_API RATE_LIMIT WEBHOOK SYNC MAPPING NORMALIZATION VALIDATION INTERNAL',
        'INTERNAL')
    severity = enum(data, 'severity', 'LOW MEDIUM HIGH CRITICAL', 'MEDIUM')
    entity_type = text(data, 'entity_type', '')
    stage = text(data, 'stage', '', 30)
    fingerprint = digest([category, code, stage, entity_type])
    values = dict(code=code, category=category, severity=severity, stage=stage, entity_type=entity_type,
                  external_id=text(data, 'external_id', '', 255),
                  message=safe_details(text(data, 'message', code.replace('_', ' ').capitalize(), 2000)),
                  details=safe_details(data.get('details', {})), sync=sync, webhook=webhook)
    row, created = IntegrationError.objects.get_or_create(connection=connection, fingerprint=fingerprint,
        defaults=dict(business_id=connection.business_id, first_seen_at=at, last_seen_at=at, **values))
    if not created:
        before = row.status
        changes = {'occurrences': models.F('occurrences') + 1,
                   'first_seen_at': min(row.first_seen_at, at), 'last_seen_at': max(row.last_seen_at, at)}
        if at >= row.last_seen_at:
            changes.update(values)
            if row.status == 'RESOLVED' and (row.resolved_at is None or at >= row.resolved_at):
                changes.update(status='ACTIVE', resolved_at=None)
                audit(connection, 'error', row.pk, 'REOPEN', before, 'ACTIVE', at=at)
        IntegrationError.objects.filter(pk=row.pk).update(**changes)
        row.refresh_from_db()
    return row


def _failure(connection, data, at, error=None):
    entity_type = text(data, 'entity_type')
    external_id = text(data, 'external_id', limit=255)
    stage = enum(data, 'stage', 'RETRIEVAL MAPPING NORMALIZATION VALIDATION IDENTITY_INPUT PERSISTENCE ROUTING')
    code = text(data, 'code')
    sync = related(IntegrationSyncLog, data.get('sync_id'), connection)
    webhook = related(WebhookObservation, data.get('webhook_id'), connection)
    payload = related(IntegrationPayload, data.get('payload_id'), connection)
    error = error or _error(connection, {**data, 'category': data.get('category',
        stage if stage in {'MAPPING', 'NORMALIZATION', 'VALIDATION'} else 'INTERNAL')}, at, sync=sync, webhook=webhook)
    fingerprint = digest([entity_type, external_id, stage, code, payload.pk if payload else None])
    row, created = FailedRecord.objects.get_or_create(connection=connection, fingerprint=fingerprint,
        defaults=dict(business_id=connection.business_id, entity_type=entity_type, external_id=external_id,
                      stage=stage, code=code, message=error.message, error=error, sync=sync, webhook=webhook,
                      payload=payload, first_seen_at=at, last_seen_at=at))
    if not created:
        before = row.status
        row.first_seen_at = min(row.first_seen_at, at)
        if at >= row.last_seen_at:
            row.last_seen_at = at
            row.error = error
            if row.status == 'RESOLVED':
                row.status, row.resolved_at, row.resolution_method = 'OPEN', None, ''
                audit(connection, 'failed_record', row.pk, 'REOPEN', before, 'OPEN', at=at)
        row.save()
    return row


def _sync(connection, data, at):
    status = enum(data, 'status', 'PENDING RUNNING COMPLETED PARTIAL FAILED')
    row = related(IntegrationSyncLog, data.get('sync_id'), connection)
    if row is not None and at < row.last_observed_at:
        return row
    if row is not None:
        if row.counter_schema == 'LEGACY' and not all(name in data for name in (
                'records_received', 'records_succeeded', 'records_skipped', 'records_failed')):
            raise ValidationError('Legacy runs require a complete explicit counter snapshot before V1 updates.')
        allowed = {'PENDING': {'PENDING', 'RUNNING', 'FAILED'}, 'RUNNING': {'RUNNING', *TERMINAL}}
        if row.status in TERMINAL or status not in allowed.get(row.status, set()):
            raise ValidationError('Invalid sync state transition.')
    counts = {}
    for name in ('records_received', 'records_succeeded', 'records_skipped', 'records_failed'):
        counts[name] = integer(data, name, getattr(row, name, 0))
        if row is not None and counts[name] < getattr(row, name):
            raise ValidationError('Sync counters cannot decrease.')
    processed = sum(counts[name] for name in ('records_succeeded', 'records_skipped', 'records_failed'))
    if data.get('records_processed', processed) != processed or processed > counts['records_received']:
        raise ValidationError('Processed must equal succeeded + skipped + failed and cannot exceed received.')
    discovered = integer(data, 'discovered', row.discovered if row else None)
    if discovered is not None and counts['records_received'] > discovered:
        raise ValidationError('Received cannot exceed a known discovered total.')
    if status in {'COMPLETED', 'PARTIAL'} and processed != counts['records_received']:
        raise ValidationError('Completed/partial runs must account for every received record.')
    if status == 'COMPLETED' and counts['records_failed']:
        raise ValidationError('A clean completion cannot contain failed records.')
    if status == 'PARTIAL' and not (counts['records_failed'] and counts['records_succeeded']):
        raise ValidationError('Partial completion requires both success and failure.')
    if row is None:
        row = IntegrationSyncLog(integration_connection=connection, created_at=at,
            started_at=at if status == 'RUNNING' else None,
            entity_type=text(data, 'entity_type'), sync_type=enum(data, 'sync_type', 'FULL INCREMENTAL', 'FULL'),
            trigger=enum(data, 'trigger', 'MANUAL SCHEDULED REPLAY RETRY', 'MANUAL'))
    if status == 'RUNNING' and row.started_at is None:
        row.started_at = at
    if data.get('started_at') is not None:
        started_at = timestamp(data['started_at'], 'started_at')
        if status == 'PENDING' or started_at > at or (row.started_at is not None and row.started_at != started_at):
            raise ValidationError('Sync start time is inconsistent with its execution state.')
        row.started_at = started_at
    row.status = status
    row.counter_schema = 'V1'
    row.discovered = discovered
    row.records_processed = processed
    for name, value in counts.items():
        setattr(row, name, value)
    if 'cursor' in data:
        row.cursor = safe_details(data['cursor'])
    if 'metadata' in data:
        if not isinstance(data['metadata'], dict):
            raise ValidationError('Sync metadata must be an object.')
        row.metadata = safe_details(data['metadata'])
    row.error_message = safe_details(text(data, 'error_message', row.error_message or '', 2000))
    row.last_observed_at = at
    if status in TERMINAL:
        row.completed_at = at
        connection.last_synced_at = max(filter(None, [connection.last_synced_at, at]))
        if status == 'COMPLETED':
            connection.last_successful_sync_at = max(filter(None, [connection.last_successful_sync_at, at]))
        connection.save(update_fields=['last_synced_at', 'last_successful_sync_at'])
    row.save()
    if status in {'PARTIAL', 'FAILED'}:
        _error(connection, {'code': 'SYNC_PARTIAL' if status == 'PARTIAL' else 'SYNC_FAILED',
                           'category': 'SYNC', 'entity_type': row.entity_type,
                           'message': row.error_message or 'Synchronization has processing failures.'}, at, sync=row)
    return row


def _webhook(connection, receipt, data, at, received):
    validation = enum(data, 'validation', 'UNKNOWN VALID INVALID', 'UNKNOWN')
    status = enum(data, 'status', 'RECEIVED ROUTING PROCESSED FAILED REJECTED', 'RECEIVED')
    event_id = text(data, 'event_id', f'observation:{receipt.key}', 255)
    event_type = text(data, 'event_type')
    payload = related(IntegrationPayload, data.get('payload_id'), connection)
    if validation == 'VALID' and payload is not None and not payload.signature_verified:
        raise ValidationError('The captured webhook payload has no valid signature evidence.')
    if validation == 'INVALID':
        status = 'REJECTED'
    if status in {'PROCESSED', 'ROUTING'} and validation != 'VALID':
        raise ValidationError('Only validated webhook events may enter trusted processing.')
    provider_at = timestamp(data['provider_event_at'], 'provider_event_at') if data.get('provider_event_at') else None
    row, created = WebhookObservation.objects.get_or_create(connection=connection, event_id=event_id,
        defaults=dict(business_id=connection.business_id, event_type=event_type,
                      entity_type=text(data, 'entity_type', ''), validation=validation, status=status,
                      payload=payload, provider_event_at=provider_at, received_at=received,
                      processed_at=at if status == 'PROCESSED' else None, last_observed_at=at))
    is_delivery = data.get('delivery', True)
    if not isinstance(is_delivery, bool):
        raise ValidationError('delivery must be boolean.')
    if not created:
        if row.event_type != event_type or (payload and row.payload_id and row.payload_id != payload.pk):
            raise ValidationError('Webhook identity cannot be rebound to another event or payload.')
        if row.validation == 'INVALID' and validation == 'VALID':
            raise ValidationError('Rejected signatures cannot be promoted by a processing observation.')
        if is_delivery:
            row.delivery_count = models.F('delivery_count') + 1
        if row.status != 'PROCESSED' and at >= row.last_observed_at:
            row.status, row.validation, row.last_observed_at = status, validation, at
            if status == 'PROCESSED':
                row.processed_at = at
        row.save()
        row.refresh_from_db()
    if is_delivery or created:
        WebhookDelivery.objects.create(webhook=row, observation=receipt, received_at=received,
                                       validation=validation, duplicate=not created)
    if status in {'FAILED', 'REJECTED'} and (created or row.status != 'PROCESSED'):
        code = 'WEBHOOK_SIGNATURE_INVALID' if validation == 'INVALID' else text(data, 'code', 'WEBHOOK_PROCESSING_FAILED')
        error = _error(connection, {**data, 'code': code, 'category': 'WEBHOOK',
                                   'stage': 'VALIDATION' if validation == 'INVALID' else 'ROUTING'}, at, webhook=row)
        row.error = error
        row.save(update_fields=['error'])
        _failure(connection, {**data, 'entity_type': row.entity_type or 'WEBHOOK', 'external_id': event_id,
                              'stage': 'VALIDATION' if validation == 'INVALID' else 'ROUTING',
                              'code': code, 'webhook_id': row.pk}, at, error=error)
    return row


def _confirmed(connection, data, at, received):
    entity_type = text(data, 'entity_type')
    original_received = timestamp(data.get('original_received_at', received), 'original_received_at')
    coverage_at = timestamp(data.get('source_at', original_received), 'source_at')
    if coverage_at > original_received or original_received > at:
        raise ValidationError('Source coverage must not follow original reception or processing confirmation.')
    complete = data.get('complete', True)
    if not isinstance(complete, bool):
        raise ValidationError('complete must be boolean.')
    row, created = SourceFreshness.objects.get_or_create(connection=connection, entity_type=entity_type,
        defaults=dict(business_id=connection.business_id))
    if row.coverage_at is None or coverage_at > row.coverage_at:
        row.coverage_at, row.received_at, row.confirmed_at, row.complete = coverage_at, original_received, at, complete
        row.save()
    return row


@transaction.atomic
def record_observation(business_id, connection_id, key, kind, data, observed_at=None, received_at=None):
    """Record an integration-owner observation once; all related writes commit together."""
    connection = scoped_connection(business_id, connection_id, lock=True)
    if kind not in KINDS or not isinstance(data, dict):
        raise ValidationError('Unsupported observation kind or non-object data.')
    key = text({'key': key}, 'key', limit=200)
    at = timestamp(observed_at or timezone.now(), 'observed_at')
    received = timestamp(received_at or timezone.now(), 'received_at')
    if at > received:
        raise ValidationError('Observation time cannot follow reception time.')
    fingerprint = digest([kind, data])
    prior = ObservationReceipt.objects.filter(connection=connection, key=key).first()
    if prior:
        if prior.digest != fingerprint or prior.kind != kind:
            raise ValidationError('An observation key cannot be reused for different content.')
        return prior
    receipt = ObservationReceipt.objects.create(**scoped_values(connection), key=key, kind=kind,
        digest=fingerprint, observed_at=at, received_at=received)
    scope = scoped_values(connection)
    if kind == 'connection_check':
        outcome = enum(data, 'outcome', 'SUCCESS DEGRADED ERROR AUTH_ERROR EXPIRED')
        credential = {'SUCCESS': 'USABLE', 'AUTH_ERROR': 'INVALID', 'EXPIRED': 'EXPIRED'}.get(outcome, 'UNKNOWN')
        row = create_validated(ConnectionCheck, **scope, observation=receipt, outcome=outcome,
            authentication=enum(data, 'authentication', 'USABLE INVALID EXPIRED UNKNOWN', credential),
            credential_status=enum(data, 'credential_status', 'USABLE INVALID EXPIRED UNKNOWN', credential),
            latency_ms=integer(data, 'latency_ms'), code=text(data, 'code', ''),
            message=safe_details(text(data, 'message', '', 2000)), observed_at=at)
        if outcome != 'SUCCESS':
            _error(connection, {'code': row.code or ('AUTHENTICATION_FAILED' if outcome in {'AUTH_ERROR', 'EXPIRED'}
                else 'CONNECTION_DEGRADED' if outcome == 'DEGRADED' else 'CONNECTION_FAILED'),
                'category': 'AUTHENTICATION' if outcome in {'AUTH_ERROR', 'EXPIRED'} else 'CONNECTIVITY',
                'message': row.message or 'The provider connection needs attention.'}, at)
    elif kind == 'provider_request':
        status_code = integer(data, 'http_status', maximum=599)
        if status_code is not None and status_code < 100:
            raise ValidationError('Invalid HTTP status.')
        outcome = enum(data, 'outcome', 'SUCCESS AUTH_ERROR RATE_LIMIT TIMEOUT PROVIDER_ERROR CONNECTIVITY_ERROR')
        row = create_validated(ProviderRequest, **scope, observation=receipt,
            outcome=outcome, capability=text(data, 'capability', 'default'),
            target=text(data, 'target', f'CONNECTION:{connection.pk}' if connection.integration_source.key in
                        {'woocommerce', 'custom_website'} else 'GLOBAL', 200),
            http_status=status_code, latency_ms=integer(data, 'latency_ms'),
            rate_limit_remaining=integer(data, 'rate_limit_remaining'),
            retry_after_seconds=integer(data, 'retry_after_seconds'),
            quota_scope=enum(data, 'quota_scope', 'CONNECTION PROVIDER', 'CONNECTION'), observed_at=at)
        if outcome != 'SUCCESS':
            category = {'AUTH_ERROR': 'AUTHENTICATION', 'RATE_LIMIT': 'RATE_LIMIT',
                        'CONNECTIVITY_ERROR': 'CONNECTIVITY'}.get(outcome, 'PROVIDER_API')
            _error(connection, {'code': outcome, 'category': category,
                               'details': {'http_status': status_code, 'capability': row.capability}}, at)
    elif kind == 'sync':
        row = _sync(connection, data, at)
    elif kind == 'failed_record':
        row = _failure(connection, data, at)
    elif kind == 'webhook':
        row = _webhook(connection, receipt, data, at, received)
    elif kind == 'data_confirmed':
        row = _confirmed(connection, data, at, received)
    else:
        row = _error(connection, data, at,
                     sync=related(IntegrationSyncLog, data.get('sync_id'), connection),
                     webhook=related(WebhookObservation, data.get('webhook_id'), connection))
    receipt.object_id = row.pk
    receipt.save(update_fields=['object_id'])
    return receipt


def publish_after_commit(**observation):
    """Use inside canonical processing transactions; rollback suppresses publication.

    This is synchronous post-commit dispatch, not durable delivery. Exceptions propagate
    to the caller; integrations requiring delivery guarantees must supply an outbox.
    """
    from app.events import DomainEvent, dispatch
    transaction.on_commit(lambda: dispatch(DomainEvent('integration.observation', observation)))
