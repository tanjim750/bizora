"""Authorized, idempotent orchestration; execution belongs to integration adapters."""
import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from app.integrations.operations import (CheckResult, ProcessingFailure, ProcessingResult,
                                         UnsupportedOperation, operations_for)
from app.models import (FailedRecord, IntegrationConnection, IntegrationError, IntegrationPayload,
                        IntegrationSyncLog, OperationAttempt, SourceFreshness, WebhookObservation)
from .access import require_access
from .policies import safe_details
from .selectors import Policies
from .services import audit, record_observation, scoped_connection, timestamp


TARGETS = {'connections': IntegrationConnection, 'failed-records': FailedRecord,
           'syncs': IntegrationSyncLog, 'webhooks': WebhookObservation}
ACTIONS = {'connections': 'connection_test', 'failed-records': 'record_retry',
           'syncs': 'sync_retry', 'webhooks': 'webhook_replay'}


def _observe(connection, attempt, suffix, kind, data, now):
    return record_observation(connection.business_id, connection.pk, f'operation:{attempt.pk}:{suffix}',
                              kind, data, now, now)


def _process(adapter, connection, attempt, payload, entity_type, now, expected_id=None):
    result = adapter.process(payload, entity_type, now)
    if not isinstance(result, ProcessingResult) or result.entity_type != entity_type or (
            expected_id is not None and result.external_id != expected_id):
        raise ProcessingFailure('INVALID_PROCESSING_RESULT', 'PERSISTENCE', 'Processing did not confirm the expected record.', False)
    if not callable(getattr(adapter, 'confirm_processing', None)):
        raise UnsupportedOperation('The processing owner must provide canonical persistence confirmation.')
    if adapter.confirm_processing(result) is not True:
        raise ProcessingFailure('UNCONFIRMED_CANONICAL_RESULT', 'PERSISTENCE', 'Canonical persistence could not be confirmed.', False)
    _observe(connection, attempt, f'confirmed:{payload.pk}', 'data_confirmed', {
        'entity_type': result.entity_type, 'source_at': result.source_at,
        'original_received_at': result.original_received_at}, now)
    return result


def _resolve_records(connection, payload, entity_type, actor, now):
    rows = list(FailedRecord.objects.filter(connection=connection, payload=payload, entity_type=entity_type)
                .exclude(status='RESOLVED', resolution_method='PROCESSING'))
    error_ids = set()
    for row in rows:
        before = row.status
        row.status, row.resolved_at, row.resolution_method = 'RESOLVED', now, 'PROCESSING'
        row.resolution = 'The integration processor confirmed canonical persistence.'
        row.save()
        audit(connection, 'failed_record', row.pk, 'PROCESSING_RESOLVED', before, 'RESOLVED', actor, at=now)
        error_ids.add(row.error_id)
    for error in IntegrationError.objects.filter(pk__in=error_ids):
        if not FailedRecord.objects.filter(error=error).exclude(status='RESOLVED', resolution_method='PROCESSING').exists() and not (
                WebhookObservation.objects.filter(error=error, status__in=['FAILED', 'REJECTED']).exists()):
            before = error.status
            error.status, error.resolved_at = 'RESOLVED', now
            error.save(update_fields=['status', 'resolved_at'])
            audit(connection, 'error', error.pk, 'PROCESSING_RESOLVED', before, 'RESOLVED', actor, at=now)


def _replay_webhook(adapter, connection, attempt, row, now):
    if row.payload_id is None:
        raise UnsupportedOperation('No protected captured payload is available.')
    result = _process(adapter, connection, attempt, row.payload, row.entity_type, now)
    _observe(connection, attempt, 'webhook-processed', 'webhook', {
        'event_id': row.event_id, 'event_type': row.event_type, 'entity_type': row.entity_type,
        'validation': 'VALID', 'status': 'PROCESSED', 'payload_id': row.payload_id, 'delivery': False}, now)
    _resolve_records(connection, row.payload, row.entity_type, attempt.actor, now)
    return {'canonical_id': result.canonical_id, 'entity_type': result.entity_type}


def _retry_sync(adapter, connection, attempt, original, now):
    payload_ids = (original.metadata or {}).get('payload_ids')
    if not isinstance(payload_ids, list) or not payload_ids:
        raise UnsupportedOperation('Sync retry requires integration-owned captured payload references.')
    if len(payload_ids) > 1000 or any(isinstance(value, bool) or not isinstance(value, int) for value in payload_ids
                                    ) or len(set(payload_ids)) != len(payload_ids):
        raise ValidationError('Sync payload references must be unique integer IDs (at most 1000).')
    payloads = {p.pk: p for p in IntegrationPayload.objects.filter(pk__in=payload_ids, connection=connection)}
    if len(payloads) != len(payload_ids):
        raise ValidationError('Sync payload references do not belong to this connection.')
    start = _observe(connection, attempt, 'sync-start', 'sync', {'status': 'RUNNING',
        'entity_type': original.entity_type, 'sync_type': original.sync_type or 'FULL', 'trigger': 'RETRY',
        'records_received': len(payload_ids), 'discovered': len(payload_ids),
        'metadata': {'payload_ids': payload_ids, 'is_mock': connection.is_mock}}, now)
    run = IntegrationSyncLog.objects.get(pk=start.object_id)
    run.parent, run.initiated_by = original, attempt.actor
    run.save(update_fields=['parent', 'initiated_by'])
    succeeded = failed = skipped = 0
    for payload_id in payload_ids:
        payload = payloads[payload_id]
        try:
            with transaction.atomic():
                result = _process(adapter, connection, attempt, payload, original.entity_type, now)
            _resolve_records(connection, payload, original.entity_type, attempt.actor, now)
            skipped += int(result.skipped)
            succeeded += int(not result.skipped)
        except ProcessingFailure as exc:
            failed += 1
            _observe(connection, attempt, f'sync-failure:{payload.pk}', 'failed_record', {
                'entity_type': original.entity_type, 'external_id': str(payload.body.get('id', f'payload:{payload.pk}')),
                'stage': exc.stage, 'code': exc.code, 'message': exc.message, 'payload_id': payload.pk, 'sync_id': run.pk}, now)
    status = 'PARTIAL' if failed and succeeded else 'FAILED' if failed else 'COMPLETED'
    if succeeded or skipped:
        SourceFreshness.objects.filter(connection=connection, entity_type=original.entity_type).update(complete=not failed)
    _observe(connection, attempt, 'sync-complete', 'sync', {'sync_id': run.pk, 'status': status,
        'records_received': len(payload_ids), 'records_succeeded': succeeded, 'records_skipped': skipped,
        'records_failed': failed}, now)
    return {'sync_id': run.pk, 'sync_status': status, 'records_succeeded': succeeded,
            'records_failed': failed, 'records_skipped': skipped, 'operation_failed': bool(failed)}


def _validate_eligibility(action, row):
    if action == 'sync_retry' and row.status not in {'PARTIAL', 'FAILED'}:
        raise ValidationError('Only partial or failed syncs may be retried.')
    if action == 'record_retry':
        if row.status not in {'OPEN', 'REVIEWING'}:
            raise ValidationError('This failed record is not eligible for retry.')
        if row.code == 'WEBHOOK_SIGNATURE_INVALID' or (row.webhook_id and row.webhook.validation != 'VALID'):
            raise ValidationError('Unverified webhook content cannot enter trusted processing.')
        if row.webhook_id and row.webhook.payload_id and not row.webhook.payload.signature_verified:
            raise ValidationError('Signature verification evidence is missing.')
    if action == 'webhook_replay':
        if row.validation != 'VALID' or row.status != 'FAILED':
            raise ValidationError('Only validated failed webhook events may be replayed.')
        if row.payload_id and not row.payload.signature_verified:
            raise ValidationError('Signature verification evidence is missing.')


@transaction.atomic
def execute_operation(business_id, resource, target_id, action, key, actor, *, now=None):
    require_access(actor, business_id, manage=True)
    if resource not in TARGETS or ACTIONS[resource] != action:
        raise ValidationError('Unsupported operation target.')
    if not isinstance(key, str) or not 0 < len(key) <= 200:
        raise ValidationError('A bounded idempotency key is required.')
    model = TARGETS[resource]
    business_field = 'integration_connection__business_id' if resource == 'syncs' else 'business_id'
    try:
        row = model.objects.get(pk=target_id, **{business_field: business_id})
    except model.DoesNotExist as exc:
        raise ValidationError('Operation target does not belong to this business.') from exc
    connection_id = row.pk if resource == 'connections' else (
        row.integration_connection_id if resource == 'syncs' else row.connection_id)
    connection = scoped_connection(business_id, connection_id, lock=True)
    row.refresh_from_db()
    prior = OperationAttempt.objects.filter(connection=connection, key=key).first()
    if prior:
        if prior.action != action or prior.target_id != target_id:
            raise ValidationError('Idempotency key is bound to another action or target.')
        return prior
    if connection.status in {'DISABLED', 'DISCONNECTED'}:
        raise ValidationError('Disabled/disconnected connections cannot execute operations.')
    _validate_eligibility(action, row)
    if action != 'connection_test':
        from app.configuration.integrations import require_processing_scope
        webhook = row if resource == 'webhooks' else getattr(row, 'webhook', None)
        require_processing_scope(connection, row.entity_type, webhook)
    now = timestamp(now or timezone.now(), 'operation_time')
    policy = Policies(business_id).get(connection_id, getattr(row, 'entity_type', ''))
    previous = OperationAttempt.objects.filter(connection=connection, action=action, target_id=target_id).exclude(status='UNSUPPORTED')
    if action != 'connection_test':
        if previous.count() >= policy.max_retries:
            raise ValidationError('Configured retry limit reached.')
        last = previous.order_by('-pk').first()
        if last and last.next_retry_at and now < last.next_retry_at:
            raise ValidationError('Retry backoff has not elapsed.')
    attempt = OperationAttempt.objects.create(business_id=business_id, connection=connection, key=key,
        action=action, target_id=target_id, status='RUNNING', actor=actor, created_at=now)
    try:
        with transaction.atomic():
            adapter = operations_for(connection)
            if action == 'connection_test':
                result = adapter.test_connection()
                if not isinstance(result, CheckResult):
                    raise ValidationError('Integration adapter returned an invalid connection result.')
                _observe(connection, attempt, 'connection-check', 'connection_check', {
                    'outcome': result.outcome, 'latency_ms': result.latency_ms,
                    'code': result.code, 'message': result.message}, now)
                details = {'health_outcome': result.outcome, 'operation_failed': result.outcome != 'SUCCESS'}
            elif action == 'sync_retry':
                details = _retry_sync(adapter, connection, attempt, row, now)
            elif action == 'webhook_replay':
                details = _replay_webhook(adapter, connection, attempt, row, now)
            elif row.webhook_id:
                details = _replay_webhook(adapter, connection, attempt, row.webhook, now)
            else:
                if not row.payload_id:
                    raise UnsupportedOperation('No protected captured payload is available.')
                result = _process(adapter, connection, attempt, row.payload, row.entity_type, now, row.external_id)
                _resolve_records(connection, row.payload, row.entity_type, actor, now)
                details = {'canonical_id': result.canonical_id, 'entity_type': result.entity_type,
                           'source_at': result.source_at.isoformat(),
                           'original_received_at': result.original_received_at.isoformat()}
        attempt.status = 'FAILED' if details.pop('operation_failed', False) else 'SUCCEEDED'
        attempt.result = safe_details({**details, 'is_mock': connection.is_mock})
    except UnsupportedOperation as exc:
        attempt.status, attempt.result = 'UNSUPPORTED', {'code': 'UNSUPPORTED_CAPABILITY',
            'message': safe_details(str(exc)), 'is_mock': connection.is_mock}
    except (ProcessingFailure, ValidationError) as exc:
        attempt.status = 'FAILED'
        code = exc.code if isinstance(exc, ProcessingFailure) else 'INVALID_OPERATION_RESULT'
        message = exc.message if isinstance(exc, ProcessingFailure) else 'The integration operation returned invalid data.'
        attempt.result = {'code': code, 'message': safe_details(message), 'is_mock': connection.is_mock,
                          'stage': exc.stage if isinstance(exc, ProcessingFailure) else 'INTERNAL',
                          'recoverable': exc.recoverable if isinstance(exc, ProcessingFailure) else False}
        if action == 'record_retry':
            # Keep the original failed record and append another classified occurrence.
            _observe(connection, attempt, 'retry-error', 'integration_error', {'code': row.code,
                'category': 'MAPPING' if row.stage == 'MAPPING' else 'INTERNAL', 'stage': row.stage,
                'entity_type': row.entity_type, 'message': message}, now)
        elif action == 'webhook_replay':
            _observe(connection, attempt, 'replay-error', 'webhook', {'event_id': row.event_id,
                'event_type': row.event_type, 'entity_type': row.entity_type, 'validation': row.validation,
                'status': 'FAILED', 'delivery': False, 'code': code}, now)
    except Exception as exc:
        # An adapter is an external failure boundary. Its savepoint was rolled back.
        # Do not put arbitrary exception text (often containing secrets) in logs/API data.
        logging.getLogger(__name__).error('Integration operation failed (%s).', type(exc).__name__)
        attempt.status, attempt.result = 'FAILED', {'code': 'INTERNAL_PROCESSING_ERROR',
            'message': 'The integration processor failed unexpectedly.', 'exception_type': type(exc).__name__,
            'is_mock': connection.is_mock}
        _observe(connection, attempt, 'internal-error', 'integration_error', {'code': 'INTERNAL_PROCESSING_ERROR',
            'category': 'INTERNAL', 'details': {'exception_type': type(exc).__name__}}, now)
    attempt.completed_at = now
    if attempt.status == 'FAILED' and action != 'connection_test':
        attempt.next_retry_at = now + timedelta(seconds=min(300, 30 * 2 ** previous.count()))
    attempt.save(update_fields=['status', 'result', 'completed_at', 'next_retry_at'])
    audit(connection, {'connections': 'connection', 'syncs': 'sync', 'failed-records': 'failed_record',
                      'webhooks': 'webhook'}[resource], target_id, action, after=attempt.status, actor=actor, at=now)
    return attempt
