"""Read-only merge inventory/reconciliation handshake. Execution deliberately remains blocked."""
import hashlib
import json
from django.db import models, transaction
from django.db.models import Q
from app import models as m
from .common import authorize, related, require, ensure_owned, DomainError
from .identity import ENTITY_MODELS
from .boundaries import exchange, MERGE_OWNERS
VERSION = 'bizora.merge.v1'
DOWNSTREAM = {'BusinessRelationship': 'Business Intelligence', 'BusinessMetric': 'Business Intelligence', 'MetricSnapshot': 'Business Intelligence', 'BusinessFact': 'Business Intelligence', 'BusinessFactEvidence': 'Business Intelligence', 'BusinessIssue': 'Business Intelligence', 'BusinessIssueEvidence': 'Business Intelligence', 'GraphNode': 'Business Graph', 'GraphEdge': 'Business Graph', 'GraphSnapshot': 'Business Graph', 'AiConversation': 'AI Intelligence', 'AiMessage': 'AI Intelligence', 'AiRecommendation': 'AI Intelligence', 'AiRecommendationEvidence': 'AI Intelligence', 'AiAction': 'AI Intelligence', 'KnowledgeSource': 'Business Memory', 'KnowledgeDocument': 'Business Memory', 'KnowledgeChunk': 'Business Memory', 'KnowledgeEmbedding': 'Business Memory'}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode()).hexdigest()

@transaction.atomic
def plan(business, actor, candidate_id):
    authorize(actor, business, manager=True)
    m.Business.objects.select_for_update().get(pk=business.pk)
    candidate = related(m.IdentityMergeCandidate, candidate_id, business)
    target, source = (candidate.primary_identity, candidate.candidate_identity)
    require(target.pk != source.pk and target.entity_type == source.entity_type and (target.entity_type in ENTITY_MODELS), 'INVALID_MERGE', 'Merge identities must be distinct entities of the same supported type.')
    require(target.entity_id != source.entity_id, 'INVALID_MERGE', 'Both identities already refer to the same canonical entity.')
    entity_model = ENTITY_MODELS[source.entity_type]
    for identity in (target, source):
        related(entity_model, identity.entity_id, business)
    relationships = []
    safety = []
    for model in m.Business._meta.apps.get_app_config('app').get_models():
        fields = {field.name: field for field in model._meta.fields}
        query = Q()
        paths = []
        for name, field in fields.items():
            if isinstance(field, models.ForeignKey) and field.related_model in (entity_model, m.CanonicalIdentity):
                ids = [source.entity_id, target.entity_id] if field.related_model == entity_model else [source.pk, target.pk]
                query |= Q(**{name + '__in': ids})
                paths.append(name)
        for prefix in ('', 'source_', 'target_', 'subject_'):
            kind, entity_id = (prefix + 'entity_type', prefix + 'entity_id')
            if kind in fields and entity_id in fields:
                query |= Q(**{kind + '__iexact': source.entity_type, entity_id + '__in': [source.entity_id, target.entity_id]})
                paths.append(kind + '/' + entity_id)
        if model == m.ProcessingReceipt:
            from .registry import RESOURCES
            resources = [key for key, value in RESOURCES.items() if value[0] == entity_model]
            query |= Q(resource__in=resources, entity_id__in=[source.entity_id, target.entity_id])
            paths.append('resource/entity_id')
        if not paths:
            continue
        rows = list(model.objects.filter(query).order_by('pk'))
        for row in rows:
            try:
                ensure_owned(row, business)
            except DomainError:
                safety.append({'model': model.__name__, 'code': 'CROSS_TENANT_RELATIONSHIP'})
        relationships.append({'model': model.__name__, 'table': model._meta.db_table, 'owner': DOWNSTREAM.get(model.__name__, 'LOCAL'), 'paths': paths, 'count': len(rows), 'digest': digest([{f.attname: getattr(row, f.attname) for f in model._meta.fields} for row in rows])})
    if candidate.status != 'APPROVED':
        safety.append({'code': 'APPROVAL_REQUIRED'})
    if target.status != 'ACTIVE' or source.status != 'ACTIVE':
        safety.append({'code': 'INACTIVE_IDENTITY'})
    body = {'version': VERSION, 'business_id': business.pk, 'candidate_id': candidate.pk, 'source_identity_id': source.pk, 'target_identity_id': target.pk, 'entity_type': source.entity_type, 'source_entity_id': source.entity_id, 'target_entity_id': target.entity_id, 'candidate_status': candidate.status, 'relationships': relationships, 'safety_errors': safety, 'dependencies': list(MERGE_OWNERS)}
    fingerprint = digest(body)
    return {**body, 'fingerprint': fingerprint, 'plan_id': 'merge-' + fingerprint[:24], 'execution': 'BLOCKED', 'execution_reason': 'BI_GRAPH_AI_MERGE_CONTRACT', 'limitations': ['Inventory covers ORM foreign keys and known typed polymorphic references; arbitrary JSON/provider metadata references require owner acknowledgements.', 'No redirects, consolidation, reparenting, snapshots, adapter acknowledgements or audit records are written.']}

def dry_run(business, actor, candidate_id, adapters=None, expected_fingerprint=None):
    original = plan(business, actor, candidate_id)
    require(expected_fingerprint is None or original['fingerprint'] == expected_fingerprint, 'STALE_PLAN', 'Merge plan changed; review a fresh inventory.')
    acknowledgements = []
    for owner in MERGE_OWNERS:
        response = exchange(business, actor, owner, 'prepare_merge', original, original['plan_id'], (adapters or {}).get(owner))
        if response['status'] == 'AVAILABLE':
            result = response['result']
            require(result.get('fingerprint') == original['fingerprint'] and result.get('decision') in ('PREPARED', 'REJECTED') and isinstance(result.get('preserves_relationships'), bool) and isinstance(result.get('notes'), str), 'INVALID_ACK', 'Merge acknowledgement requires matching fingerprint, decision, preservation flag and notes.')
        acknowledgements.append(response)
    current = plan(business, actor, candidate_id)
    require(current['fingerprint'] == original['fingerprint'], 'STALE_PLAN', 'Relationships changed during reconciliation; retry with a new plan.')
    prepared = all((x['status'] == 'AVAILABLE' and x['result']['decision'] == 'PREPARED' and x['result']['preserves_relationships'] for x in acknowledgements))
    rejected = any((x['status'] == 'REJECTED' or (x['status'] == 'AVAILABLE' and (x['result']['decision'] == 'REJECTED' or not x['result']['preserves_relationships'])) for x in acknowledgements))
    readiness = 'UNSAFE' if original['safety_errors'] else 'REJECTED' if rejected else 'SIMULATED_PREPARED' if prepared and any((x['simulated'] for x in acknowledgements)) else 'PREPARED_REQUIRES_EXECUTOR_REVIEW' if prepared else 'WAITING_FOR_OWNERS'
    return {**original, 'readiness': readiness, 'acknowledgements': acknowledgements, 'executed': False}
