from copy import deepcopy

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from app.models import Business, ConfigurationEvent, ConfigurationRecord, ConfigurationRevision
from app.observability.access import require_access
from app.observability.policies import SECRET_TEXT, safe_details
from app.overview.configuration import ConfigurationConflict, json_values
from app.overview.windows import aware_timestamp
from .models import STATES
from .schemas import PLATFORM_GUARDRAILS, SCHEMAS, defaults


CONTROL = {'key', 'version', 'status', 'priority', 'valid_from', 'valid_to', 'reason'}
SINGLETONS = {'PROFILE', 'GENERAL', 'AI', 'KNOWLEDGE'}


def merge(base, changes):
    result = deepcopy(base)
    for key, value in changes.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else deepcopy(value)
    return result


def event(business_id, section, key, version, dedupe_key, actor, now):
    return ConfigurationEvent.objects.create(business_id=business_id, section=section, key=key,
        version=version, dedupe_key=dedupe_key, actor=actor, created_at=now)


def append_revision(record, actor, reason, now):
    revision = ConfigurationRevision.objects.create(record=record, version=record.version, data=record.data,
        status=record.status, priority=record.priority, valid_from=record.valid_from, valid_to=record.valid_to,
        actor=actor, reason=reason, created_at=now)
    event(record.business_id, record.kind, record.key, record.version, f'record:{record.pk}:v{record.version}', actor, now)
    return revision


def safe_settings(kind, data):
    data = deepcopy(data)
    if kind == 'INTEGRATION':
        references = data.pop('credentials', {})
        data['credentials'] = {'configured': bool(references), 'fields': sorted(references)}
        for name in ('provider_settings', 'mock', 'sync', 'webhooks'):
            if name in data:
                data[name] = safe_details(data[name])
    if kind == 'AI':
        data['guardrails'] = deepcopy(PLATFORM_GUARDRAILS)
    return data


def record_data(record, data=None):
    return {'id': record.pk, 'kind': record.kind, 'key': record.key, 'version': record.version,
        'status': record.status, 'priority': record.priority, 'valid_from': record.valid_from, 'valid_to': record.valid_to,
        'settings': safe_settings(record.kind, data if data is not None else record.data),
        'updated_at': record.updated_at, 'updated_by_id': record.updated_by_id}


def revision_data(row):
    return {'id': row.pk, 'key': row.record.key, 'kind': row.record.kind, 'version': row.version,
        'status': row.status, 'priority': row.priority, 'valid_from': row.valid_from, 'valid_to': row.valid_to,
        'settings': safe_settings(row.record.kind, row.data), 'actor_id': row.actor_id,
        'reason': row.reason, 'created_at': row.created_at}


def section_data(business, kind):
    record = ConfigurationRecord.objects.filter(business=business, kind=kind, key='default').first()
    data = merge(defaults(kind, business), record.data if record else {})
    if kind in {'PROFILE', 'GENERAL'}:
        data.update(currency=business.currency, timezone=business.timezone)
        if kind == 'PROFILE':
            data['name'] = business.name
    return record_data(record, data) if record else {'kind': kind, 'key': 'default', 'version': 0, 'status': 'ACTIVE',
        'settings': safe_settings(kind, data), 'updated_at': None, 'updated_by_id': None}


@transaction.atomic
def record_native_change(business_id, kind, key, data, actor, now):
    """Audit settings validated and persisted by their existing owning domain."""
    require_access(actor, business_id, manage=True)
    Business.objects.select_for_update(no_key=True).get(pk=business_id)
    record = ConfigurationRecord.objects.filter(business_id=business_id, kind=kind, key=key).first()
    record = record or ConfigurationRecord(business_id=business_id, kind=kind, key=key, created_at=now, version=0)
    record.data, record.version = json_values(data), record.version+1
    record.updated_by, record.updated_at = actor, now
    record.save()
    append_revision(record, actor, '', now)
    return record


@transaction.atomic
def save_record(business_id, kind, key, body, actor, *, now=None, create=False, schema=None):
    require_access(actor, business_id, manage=True)
    now = now or timezone.now()
    business = Business.objects.select_for_update(no_key=True).get(pk=business_id)
    if not isinstance(body, dict):
        raise ValidationError('Expected an object.')
    record = ConfigurationRecord.objects.filter(business_id=business_id, kind=kind, key=key).first()
    if create and record:
        raise ConfigurationConflict('Configuration key already exists.')
    if not create and not record and kind not in SINGLETONS:
        raise NotFound('Configuration record not found.')
    expected = body.get('version')
    if expected is not None and (isinstance(expected, bool) or not isinstance(expected, int) or expected < 0):
        raise ValidationError('Version must be a nonnegative integer.')
    if expected is not None and expected != (record.version if record else 0):
        raise ConfigurationConflict()
    if 'key' in body and body['key'] != key:
        raise ValidationError('Stable configuration keys cannot be renamed.')
    if kind in SINGLETONS and (set(body) & {'status', 'priority', 'valid_from', 'valid_to'}):
        raise ValidationError('Singleton configuration is applied immediately.')
    state = body.get('status', record.status if record else ('ACTIVE' if kind in SINGLETONS else 'DRAFT'))
    if state not in STATES:
        raise ValidationError('Invalid configuration state.')
    priority = body.get('priority', record.priority if record else 0)
    if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 10000:
        raise ValidationError('Priority must be an integer from 0 to 10000.')
    dates = {}
    for name in ('valid_from', 'valid_to'):
        dates[name] = aware_timestamp(body[name]) if body.get(name) is not None else (
            getattr(record, name) if record and name not in body else None)
    if dates['valid_to'] and ((dates['valid_from'] and dates['valid_to'] <= dates['valid_from']) or (
            state == 'ACTIVE' and dates['valid_to'] <= now)):
        raise ValidationError('Policy/rule end must follow its effective start.')
    reason = body.get('reason', '')
    if not isinstance(reason, str) or len(reason) > 500 or SECRET_TEXT.search(reason):
        raise ValidationError('Change reason is invalid or contains credential text.')
    base = merge(defaults(kind, business), record.data if record else {})
    if kind in {'PROFILE', 'GENERAL'}:
        base.update(currency=business.currency, timezone=business.timezone)
        if kind == 'PROFILE':
            base['name'] = business.name
    data = merge(base, {k: v for k, v in body.items() if k not in CONTROL})
    parser = (schema or SCHEMAS[kind])(data=data, context={'business_id': business_id, 'status': state})
    parser.is_valid(raise_exception=True)
    data = json_values(parser.validated_data)
    if record is None:
        record = ConfigurationRecord(business=business, kind=kind, key=key, created_at=now, version=0)
    record.data, record.status, record.priority = data, state, priority
    record.valid_from, record.valid_to = dates['valid_from'], dates['valid_to']
    record.version += 1
    record.updated_by, record.updated_at = actor, now
    record.save()
    append_revision(record, actor, reason, now)
    if kind in {'PROFILE', 'GENERAL'}:
        fields = ['currency', 'timezone'] + (['name'] if kind == 'PROFILE' else [])
        for field in fields:
            setattr(business, field, data[field])
        business.updated_at = now
        business.save(update_fields=fields+['updated_at'])
    return record
