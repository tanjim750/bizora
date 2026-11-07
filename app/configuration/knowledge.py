from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from app.models import (Business, ConfigurationRecord, KnowledgeDocument, KnowledgeReprocessingRequest, KnowledgeSource)
from app.observability.access import require_access
from app.overview.configuration import ConfigurationConflict, StrictSerializer
from .schemas import KNOWLEDGE_TYPES, SOURCE_TYPES, bounded_json
from .selectors import effective_revisions, knowledge_configuration
from .services import CONTROL, merge, record_data, save_record


class SourceSchema(StrictSerializer):
    source_id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=255)
    source_type = serializers.ChoiceField(choices=SOURCE_TYPES)
    knowledge_type = serializers.ChoiceField(choices=KNOWLEDGE_TYPES)
    source_reference = serializers.CharField(max_length=1000)

    def validate(self, data):
        bounded_json(data['source_reference'])
        if data['source_type'] == 'WEBSITE' and not data['source_reference'].startswith('https://'):
            raise serializers.ValidationError('Website knowledge sources require an HTTPS reference.')
        return data


NOT_LOADED = object()


def source_data(source, row=NOT_LOADED):
    if row is NOT_LOADED:
        row = ConfigurationRecord.objects.filter(business_id=source.business_id, kind='SOURCE', key=str(source.pk)).first()
    return {**(record_data(row) if row else {'version': 0, 'kind': 'SOURCE', 'key': str(source.pk),
        'status': 'UNAPPROVED', 'settings': {'name': source.name, 'source_type': source.source_type,
        'knowledge_type': source.knowledge_type, 'source_reference': source.source_reference}}), 'id': source.pk}


@transaction.atomic
def save_source(business_id, actor, body, now, pk=None):
    require_access(actor, business_id, manage=True)
    Business.objects.select_for_update(no_key=True).get(pk=business_id)
    if not isinstance(body, dict) or set(body) & {'priority', 'valid_from', 'valid_to', 'key'}:
        raise ValidationError('Source configuration accepts settings, status, version, and reason.')
    if pk is None:
        source = KnowledgeSource.objects.create(business_id=business_id, name='Draft source', source_type='MANUAL',
            status='DRAFT', created_at=now, updated_at=now)
    else:
        source = KnowledgeSource.objects.filter(business_id=business_id, pk=pk).first()
        if source is None:
            raise NotFound('Knowledge source not found.')
    base = {'source_id': source.pk, 'name': source.name, 'source_type': source.source_type,
        'knowledge_type': source.knowledge_type or 'INTERNAL', 'source_reference': source.source_reference or 'manual:unconfigured'}
    existing = ConfigurationRecord.objects.filter(business_id=business_id, kind='SOURCE', key=str(source.pk)).first()
    if existing:
        base = existing.data
    if 'source_id' in body and body['source_id'] != source.pk:
        raise ValidationError('Source identifier cannot be changed.')
    changes = merge(base, body)
    record = save_record(business_id, 'SOURCE', str(source.pk), changes, actor, now=now,
                         create=existing is None, schema=SourceSchema)
    settings = knowledge_configuration(business_id)
    if record.status == 'ACTIVE' and (record.data['source_type'] not in settings['ingestion']['allowed_types'] or
                                      record.data['knowledge_type'] not in settings['knowledge_types']):
        raise ValidationError('Source type and knowledge category must be enabled before approval.')
    active = effective_revisions(business_id, 'SOURCE', now).filter(record=record).first()
    applied = active.data if active else record.data
    for field in ('name', 'source_type', 'knowledge_type', 'source_reference'):
        setattr(source, field, applied[field])
    source.status = 'ACTIVE' if active else record.status
    source.updated_at = now
    source.save()
    return source


class ReprocessingSchema(StrictSerializer):
    idempotency_key = serializers.RegexField(r'^[a-zA-Z0-9_.:-]{1,100}$')
    source_id = serializers.IntegerField(min_value=1, required=False)
    document_id = serializers.IntegerField(min_value=1, required=False)
    action = serializers.ChoiceField(choices=['REPROCESS', 'REEMBED'])

    def validate(self, data):
        if ('source_id' in data) == ('document_id' in data):
            raise serializers.ValidationError('Choose exactly one source or document.')
        return data


@transaction.atomic
def request_reprocessing(business_id, actor, body, now):
    require_access(actor, business_id, manage=True)
    Business.objects.select_for_update(no_key=True).get(pk=business_id)
    parsed = ReprocessingSchema(data=body)
    parsed.is_valid(raise_exception=True)
    data = parsed.validated_data
    source = document = None
    if 'document_id' in data:
        document = KnowledgeDocument.objects.filter(pk=data['document_id'], business_id=business_id,
            knowledge_source__business_id=business_id).first()
        if not document:
            raise ValidationError('Document does not belong to this business and source.')
        source = document.knowledge_source
    else:
        source = KnowledgeSource.objects.filter(pk=data['source_id'], business_id=business_id).first()
        if not source:
            raise ValidationError('Source does not belong to this business.')
    previous = KnowledgeReprocessingRequest.objects.filter(business_id=business_id, key=data['idempotency_key']).first()
    if previous:
        if (previous.source_id, previous.document_id, previous.action) != (source.pk, document.pk if document else None, data['action']):
            raise ConfigurationConflict('Idempotency key is bound to another request.')
        return previous, False
    source_revision = effective_revisions(business_id, 'SOURCE', now).filter(data__source_id=source.pk).first()
    if not source_revision:
        raise ValidationError('Source must be approved before requesting processing.')
    revision = effective_revisions(business_id, 'KNOWLEDGE', now).first()
    if revision is None:
        # Pin a validated default configuration so later edits cannot change the request.
        record = save_record(business_id, 'KNOWLEDGE', 'default', {}, actor, now=now)
        revision = record.revisions.get(version=record.version)
    row = KnowledgeReprocessingRequest.objects.create(business_id=business_id, key=data['idempotency_key'],
        source=source, document=document, action=data['action'], configuration_revision=revision,
        source_revision=source_revision, document_version=document.version if document else None,
        requested_by=actor, created_at=now)
    return row, True


def reprocessing_data(row):
    return {'id': row.pk, 'source_id': row.source_id, 'document_id': row.document_id, 'action': row.action,
        'status': row.status, 'configuration_revision_id': row.configuration_revision_id,
        'source_revision_id': row.source_revision_id, 'document_version': row.document_version,
        'created_at': row.created_at, 'requested_by_id': row.requested_by_id,
        'execution_owner': 'BUSINESS_MEMORY_KNOWLEDGE', 'worker_available': False}
