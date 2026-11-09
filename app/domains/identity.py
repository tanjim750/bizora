"""Evidence-based identity decisions. Ambiguity produces review records, never a guessed merge."""
from django.db import transaction
from django.utils import timezone
from app import models as m
from .common import require, normalize_contact, related, create, authorize, external_identifier

ENTITY_MODELS = {k.upper(): v for k, v in {
    'customer': m.Customer, 'product': m.Product, 'order': m.Order, 'payment': m.Payment,
    'campaign': m.Campaign, 'session': m.WebsiteSession, 'conversation': m.Conversation,
    'call': m.Call, 'shipment': m.Shipment, 'visitor': m.WebsiteVisitor,
}.items()}


def history(business, actor, action, canonical=None, external=None, rule='', evidence=None):
    return m.IdentityHistory.objects.create(business=business, actor=actor, action=action,
        canonical_identity=canonical, external_identity=external, rule_key=rule, evidence=evidence or {})


def lock(business):
    m.Business.objects.select_for_update().get(pk=business.pk)


def _canonical(business, entity_type, entity_id):
    entity_type = str(entity_type).upper()
    require(entity_type in ENTITY_MODELS, 'INVALID_ENTITY', 'Unsupported canonical entity type.')
    entity = related(ENTITY_MODELS[entity_type], entity_id, business)
    # Entity PK is stable, collision-free and does not depend on provider IDs.
    identity, _ = m.CanonicalIdentity.objects.get_or_create(business=business, entity_type=entity_type, entity_id=entity.pk,
        defaults={'canonical_key': f'{entity_type}-{entity.pk:08d}', 'status': 'ACTIVE',
                  'created_at': timezone.now(), 'updated_at': timezone.now()})
    require(identity.status == 'ACTIVE', 'INACTIVE_IDENTITY', 'Canonical identity is unavailable.')
    return identity


@transaction.atomic
def canonical(business, actor, entity_type, entity_id):
    authorize(actor, business, manager=True)
    lock(business)
    identity = _canonical(business, entity_type, entity_id)
    return identity


def conflict(business, actor, kind, external=None, canonical=None, evidence=None):
    obj = create(m.IdentityConflict, business=business, external_identity=external,
        canonical_identity=canonical, conflict_type=kind, conflicting_data=evidence or {},
        severity={'EXTERNAL_ID_COLLISION': 'CRITICAL', 'INVALID_LINK': 'CRITICAL', 'MULTIPLE_MATCHES': 'MEDIUM'}.get(kind, 'HIGH'), detected_at=timezone.now())
    history(business, actor, 'CONFLICT_DETECTED', canonical, external, evidence={'conflict_id': obj.pk, 'kind': kind})
    return obj


@transaction.atomic
def register(business, actor, connection_id, entity_type, identity_type, value, external_id=None, verified=False):
    authorize(actor, business, manager=True)
    lock(business)
    connection = related(m.IntegrationConnection, connection_id, business)
    entity_type, identity_type = str(entity_type).upper(), str(identity_type).upper()
    require(entity_type in ENTITY_MODELS, 'INVALID_ENTITY', 'Unsupported entity type.')
    require(isinstance(verified, bool), 'INVALID_DATA', 'Verification must be boolean.')
    normalized = normalize_contact(identity_type, value)
    require(external_id is not None and str(external_id).strip() and len(str(external_id)) <= 255,
            'INVALID_IDENTIFIER', 'A source-scoped external identifier is required.')
    external_id = external_identifier(external_id)
    lookup = dict(business=business, integration_connection=connection, entity_type=entity_type,
                  identity_type=identity_type, external_id=str(external_id))
    old = m.ExternalIdentity.objects.filter(**lookup).first()
    if old:
        if old.normalized_value != normalized:
            issue = conflict(business, actor, 'EXTERNAL_ID_COLLISION', external=old)
            return old, issue
        old.last_seen_at = timezone.now()
        old.save(update_fields=['last_seen_at'])
        return old, None
    obj = create(m.ExternalIdentity, **lookup, provider=connection.integration_source.key,
        identity_value=value, normalized_value=normalized, metadata={'verified': bool(verified)},
        first_seen_at=timezone.now(), last_seen_at=timezone.now())
    history(business, actor, 'REGISTERED', external=obj)
    return obj, None


def _link(business, actor, external, target, kind, rule, evidence):
    require(external.business_id == target.business_id == business.pk, 'INVALID_RELATION', 'Identity business differs.')
    require(external.entity_type == target.entity_type or kind == 'ANONYMOUS_TO_KNOWN' and external.entity_type == 'VISITOR' and target.entity_type == 'CUSTOMER', 'INVALID_ENTITY', 'Entity types differ.')
    require(target.status == 'ACTIVE', 'INACTIVE_IDENTITY', 'Target identity is inactive.')
    active = m.IdentityLink.objects.filter(external_identity=external, status='ACTIVE').first()
    if active:
        if active.canonical_identity_id == target.pk:
            return active, None
        issue = conflict(business, actor, 'MULTIPLE_CANONICAL_MATCHES', external, target,
                         {'active_identity_id': active.canonical_identity_id})
        return None, issue
    obj, _ = m.IdentityLink.objects.update_or_create(canonical_identity=target, external_identity=external,
        defaults={'match_type': kind, 'confidence': None if kind == 'MANUAL' else 1, 'status': 'ACTIVE', 'resolved_by': 'MANUAL' if kind == 'MANUAL' else 'SYSTEM',
                  'rule_key': rule, 'linked_at': timezone.now(), 'unlinked_at': None,
                  'metadata': evidence, 'created_at': timezone.now()})
    history(business, actor, 'LINKED', target, external, rule, evidence)
    return obj, None


@transaction.atomic
def link(business, actor, external_id, canonical_id, reason):
    authorize(actor, business, manager=True)
    lock(business)
    require(isinstance(reason, str) and reason.strip(), 'EVIDENCE_REQUIRED', 'Manual link reason is required.')
    return _link(business, actor, related(m.ExternalIdentity, external_id, business),
                 related(m.CanonicalIdentity, canonical_id, business), 'MANUAL', 'AUTHORIZED_MANUAL', {'reason': reason})


@transaction.atomic
def unlink(business, actor, link_id, reason):
    authorize(actor, business, manager=True)
    lock(business)
    require(isinstance(reason, str) and reason.strip(), 'EVIDENCE_REQUIRED', 'Unlink reason is required.')
    obj = m.IdentityLink.objects.select_related('canonical_identity', 'external_identity').get(pk=link_id, canonical_identity__business=business, external_identity__business=business)
    if obj.status == 'ACTIVE':
        obj.status, obj.unlinked_at = 'INVALIDATED', timezone.now()
        obj.save(update_fields=['status', 'unlinked_at'])
        history(business, actor, 'UNLINKED', obj.canonical_identity, obj.external_identity, evidence={'reason': reason})
    return obj


@transaction.atomic
def resolve(business, actor, external_id):
    authorize(actor, business, manager=True)
    lock(business)
    ext = related(m.ExternalIdentity, external_id, business)
    active = m.IdentityLink.objects.filter(external_identity=ext, status='ACTIVE', canonical_identity__status='ACTIVE').first()
    if active:
        from .common import ensure_owned
        ensure_owned(active, business)
        return active, None
    candidates, evidence, rule = [], {}, ''
    if ext.entity_type == 'CUSTOMER':
        refs = m.CustomerExternalReference.objects.filter(integration_connection=ext.integration_connection,
                    external_customer_id=ext.external_id, customer__business=business)
        source_ids = set(refs.values_list('customer_id', flat=True))
        ids = set()
        if ext.identity_type in ('EMAIL', 'PHONE', 'WHATSAPP_PHONE') and (ext.metadata if isinstance(ext.metadata, dict) else {}).get('verified'):
            kinds = ('PHONE', 'WHATSAPP_PHONE') if ext.identity_type in ('PHONE', 'WHATSAPP_PHONE') else ('EMAIL',)
            contacts = m.CustomerContact.objects.filter(customer__business=business, contact_type__in=kinds,
                       normalized_value=ext.normalized_value, is_verified=True)
            ids = set(contacts.values_list('customer_id', flat=True))
            evidence['contact_ids'] = list(contacts.values_list('pk', flat=True))
        if source_ids and ids and source_ids != ids:
            return None, conflict(business, actor, 'CONTRADICTORY_IDENTIFIERS', ext, evidence={'source_customer_ids': sorted(source_ids), 'contact_customer_ids': sorted(ids)})
        candidates = sorted(source_ids or ids)
        rule = 'SOURCE_CUSTOMER_REFERENCE' if source_ids else 'VERIFIED_EXACT_CONTACT'
    elif ext.entity_type == 'PRODUCT':
        refs = m.ProductExternalReference.objects.filter(integration_connection=ext.integration_connection, external_product_id=ext.external_id, product__business=business)
        ids = set(refs.values_list('product_id', flat=True))
        sku_ids = set()
        if ext.identity_type == 'SKU' and isinstance(ext.metadata, dict) and ext.metadata.get('verified') is True and ext.metadata.get('sku_match_rule') == 'EXPLICIT_VERIFIED_SKU_V1':
            sku_ids = set(m.Product.objects.filter(business=business, sku=ext.normalized_value).values_list('pk', flat=True))
        if ids and sku_ids and ids != sku_ids:
            return None, conflict(business, actor, 'CONTRADICTORY_IDENTIFIERS', ext, evidence={'source_product_ids': sorted(ids), 'sku_product_ids': sorted(sku_ids)})
        candidates = sorted(ids or sku_ids)
        rule = 'SOURCE_PRODUCT_REFERENCE' if ids else 'EXPLICIT_VERIFIED_SKU_V1'
    elif ext.entity_type == 'ORDER':
        candidates = list(m.Order.objects.filter(business=business, integration_connection=ext.integration_connection, external_order_id=ext.external_id).values_list('pk', flat=True))
        rule = 'SOURCE_ORDER_REFERENCE'
    else:
        fields = {'PAYMENT': 'external_payment_id', 'CAMPAIGN': 'external_campaign_id', 'SESSION': 'external_session_id',
                  'CONVERSATION': 'external_conversation_id', 'CALL': 'external_call_id', 'SHIPMENT': 'external_shipment_id'}
        if ext.entity_type in fields:
            model = ENTITY_MODELS[ext.entity_type]
            candidates = list(model.objects.filter(business=business, integration_connection=ext.integration_connection,
                              **{fields[ext.entity_type]: ext.external_id}).values_list('pk', flat=True))
            rule = 'SOURCE_ENTITY_REFERENCE'
    if len(candidates) > 1:
        return None, conflict(business, actor, 'MULTIPLE_MATCHES', ext, evidence={'candidate_entity_ids': candidates})
    if not candidates:
        history(business, actor, 'NO_MATCH', external=ext, rule='INSUFFICIENT_EVIDENCE')
        return None, None
    target = _canonical(business, ext.entity_type, candidates[0])
    return _link(business, actor, ext, target, 'EXACT', rule, evidence)


@transaction.atomic
def verify_contact(business, actor, contact_id, reason):
    authorize(actor, business, manager=True)
    lock(business)
    require(isinstance(reason, str) and reason.strip(), 'EVIDENCE_REQUIRED', 'Verification evidence is required.')
    obj = related(m.CustomerContact, contact_id, business)
    obj.is_verified = True
    obj.save(update_fields=['is_verified'])
    history(business, actor, 'CONTACT_VERIFIED', _canonical(business, 'CUSTOMER', obj.customer_id),
            evidence={'contact_id': obj.pk, 'reason': reason})
    return obj


@transaction.atomic
def link_anonymous(business, actor, visitor_id, purchase_event_id, external_identity_id=None):
    authorize(actor, business, manager=True)
    lock(business)
    visitor = related(m.WebsiteVisitor, visitor_id, business)
    event = related(m.WebsiteEvent, purchase_event_id, business)
    require(event.visitor_id == visitor.pk and event.session.visitor_id == visitor.pk,
            'EVIDENCE_REQUIRED', 'Identification event must belong to this visitor and session.')
    rule = 'PURCHASE_ORDER_VISITOR'
    if event.event_type == 'PURCHASE' and event.order_id:
        customer = event.order.customer
    else:
        require(event.event_type in ('LOGIN', 'SIGNUP', 'FORM_SUBMISSION') and external_identity_id,
                'EVIDENCE_REQUIRED', 'Login/form identification requires a verified external identity.')
        external_proof = related(m.ExternalIdentity, external_identity_id, business)
        require(external_proof.identity_type in ('EMAIL', 'PHONE', 'WHATSAPP_PHONE') and
                isinstance(external_proof.metadata, dict) and external_proof.metadata.get('verified') is True,
                'EVIDENCE_REQUIRED', 'Only verified comparable identifiers can recover a journey.')
        require(isinstance(event.properties, dict) and
                normalize_contact(external_proof.identity_type, event.properties.get('identity_value')) == external_proof.normalized_value,
                'EVIDENCE_REQUIRED', 'Event identifier must match the verified external identity.')
        proof_link = m.IdentityLink.objects.filter(external_identity=external_proof, status='ACTIVE',
                     canonical_identity__business=business, canonical_identity__status='ACTIVE',
                     canonical_identity__entity_type='CUSTOMER').first()
        require(proof_link is not None, 'EVIDENCE_REQUIRED', 'Verified identifier must already resolve to a customer.')
        customer = related(m.Customer, proof_link.canonical_identity.entity_id, business)
        rule = 'VERIFIED_IDENTIFIER_VISITOR'
    require(customer is not None, 'EVIDENCE_REQUIRED', 'Purchase order has no known customer.')
    require(visitor.customer_id in (None, customer.pk), 'IDENTITY_CONFLICT', 'Visitor already belongs to another customer.')
    require(not visitor.websitesession_set.exclude(customer_id__in=[customer.pk]).filter(customer__isnull=False).exists(),
            'IDENTITY_CONFLICT', 'Visitor has contradictory session ownership.')
    require(not visitor.websiteevent_set.exclude(customer_id=customer.pk).filter(customer__isnull=False).exists(),
            'IDENTITY_CONFLICT', 'Visitor has contradictory event ownership.')
    from .common import ensure_owned
    from itertools import chain
    for observed in chain(visitor.websitesession_set.all(), visitor.websiteevent_set.all()):
        ensure_owned(observed, business)
    if visitor.customer_id == customer.pk and not visitor.is_anonymous:
        return visitor
    visitor.customer, visitor.is_anonymous, visitor.updated_at = customer, False, timezone.now()
    visitor.save(update_fields=['customer', 'is_anonymous', 'updated_at'])
    visitor.websitesession_set.filter(customer__isnull=True).update(customer=customer)
    visitor.websiteevent_set.filter(customer__isnull=True).update(customer=customer)
    for observed in visitor.websiteevent_set.all():
        m.CustomerTimelineEvent.objects.get_or_create(customer=customer, entity_type='WebsiteEvent', entity_id=observed.pk, event_type='WEBSITE-EVENTS_CREATED', defaults={'event_at': observed.occurred_at, 'created_at': timezone.now(), 'title': 'WEBSITE-EVENTS_CREATED'})
    target = _canonical(business, 'CUSTOMER', customer.pk)
    connection = event.session.integration_connection
    external, _ = m.ExternalIdentity.objects.get_or_create(business=business, integration_connection=connection,
        provider=connection.integration_source.key if connection else 'FIRST_PARTY', entity_type='VISITOR',
        identity_type='CLIENT_ID', external_id=visitor.visitor_key,
        defaults={'identity_value': visitor.visitor_key, 'normalized_value': visitor.visitor_key,
                  'first_seen_at': visitor.first_seen_at, 'last_seen_at': timezone.now(),
                  'created_at': timezone.now(), 'updated_at': timezone.now()})
    evidence = {'visitor_id': visitor.pk, 'purchase_event_id': event.pk, 'order_id': event.order_id}
    active = m.IdentityLink.objects.filter(external_identity=external, status='ACTIVE').first()
    require(active is None or active.canonical_identity_id == target.pk or
            active.canonical_identity.entity_type == 'VISITOR' and active.canonical_identity.entity_id == visitor.pk,
            'IDENTITY_CONFLICT', 'Visitor external identity belongs to another customer.')
    if active and active.canonical_identity_id != target.pk:
        active.status, active.unlinked_at = 'SUPERSEDED', timezone.now()
        active.save(update_fields=['status', 'unlinked_at'])
        history(business, actor, 'SUPERSEDED', active.canonical_identity, external, rule, evidence)
    _link(business, actor, external, target, 'ANONYMOUS_TO_KNOWN', rule, evidence)
    history(business, actor, 'ANONYMOUS_TO_KNOWN', target, rule=rule,
            evidence={'visitor_id': visitor.pk, 'purchase_event_id': event.pk, 'order_id': event.order_id})
    return visitor


@transaction.atomic
def detect_merges(business, actor):
    authorize(actor, business, manager=True)
    lock(business)
    contacts = m.CustomerContact.objects.filter(customer__business=business, is_verified=True).exclude(normalized_value__isnull=True)
    groups = {}
    for c in contacts:
        key = ('PHONE' if c.contact_type == 'WHATSAPP_PHONE' else c.contact_type, c.normalized_value)
        groups.setdefault(key, set()).add(c.customer_id)
    result = []
    for ids in groups.values():
        ids = sorted(ids)
        for i, a in enumerate(ids):
            for b in ids[i+1:]:
                primary, candidate = _canonical(business, 'CUSTOMER', a), _canonical(business, 'CUSTOMER', b)
                obj, made = m.IdentityMergeCandidate.objects.get_or_create(business=business, primary_identity=primary,
                    candidate_identity=candidate, defaults={'match_reason': 'SHARED_VERIFIED_CONTACT', 'confidence': 1,
                    'evidence': {'rule': 'SHARED_VERIFIED_CONTACT'}, 'detected_at': timezone.now(), 'created_at': timezone.now(), 'updated_at': timezone.now()})
                result.append(obj)
                if made:
                    history(business, actor, 'MERGE_CANDIDATE', primary, evidence={'candidate_id': obj.pk})
    product_groups = {}
    for product in m.Product.objects.filter(business=business).exclude(sku__isnull=True).exclude(sku=''):
        product_groups.setdefault(product.sku, []).append(product.pk)
    for product_ids in product_groups.values():
        for index, first in enumerate(sorted(product_ids)):
            for second in sorted(product_ids)[index+1:]:
                primary, candidate = _canonical(business, 'PRODUCT', first), _canonical(business, 'PRODUCT', second)
                obj, made = m.IdentityMergeCandidate.objects.get_or_create(business=business, primary_identity=primary, candidate_identity=candidate, defaults={'match_reason': 'SHARED_SKU_REVIEW', 'evidence': {'rule': 'SHARED_SKU_REVIEW'}, 'detected_at': timezone.now(), 'created_at': timezone.now(), 'updated_at': timezone.now()})
                result.append(obj)
                if made:
                    history(business, actor, 'MERGE_CANDIDATE', primary, evidence={'candidate_id': obj.pk})
    return list({x.pk: x for x in result}.values())


@transaction.atomic
def review_merge(business, actor, candidate_id, decision, reason):
    authorize(actor, business, manager=True)
    lock(business)
    obj = related(m.IdentityMergeCandidate, candidate_id, business)
    require(reason and decision in ('APPROVED', 'REJECTED'), 'INVALID_REVIEW', 'Explicit decision and reason are required.')
    require(obj.status == 'PENDING' or obj.status == decision, 'INVALID_TRANSITION', 'Candidate already reviewed.')
    if obj.status != decision:
        obj.status, obj.resolved_at, obj.updated_at = decision, timezone.now(), timezone.now()
        obj.save(update_fields=['status', 'resolved_at', 'updated_at'])
        history(business, actor, 'MERGE_' + decision, obj.primary_identity, evidence={'candidate_id': obj.pk, 'reason': reason})
    return obj


@transaction.atomic
def execute_merge(business, actor, candidate_id):
    authorize(actor, business, manager=True)
    lock(business)
    obj = related(m.IdentityMergeCandidate, candidate_id, business)
    require(obj.status == 'APPROVED', 'APPROVAL_REQUIRED', 'Merge must first be approved.')
    # Graph, BI polymorphic references, AI context and retained external identities have
    # no agreed redirection/reprojection contract. Never partially reparent canonical data.
    history(business, actor, 'MERGE_EXECUTION_BLOCKED', obj.primary_identity,
            evidence={'candidate_id': obj.pk, 'dependency': 'BI_GRAPH_AI_MERGE_CONTRACT'})
    return {'status': 'BLOCKED', 'code': 'BI_GRAPH_AI_MERGE_CONTRACT', 'candidate_id': obj.pk}


@transaction.atomic
def review_conflict(business, actor, conflict_id, decision, reason):
    authorize(actor, business, manager=True)
    lock(business)
    obj = related(m.IdentityConflict, conflict_id, business)
    require(decision in ('REVIEWING', 'RESOLVED', 'IGNORED') and reason, 'INVALID_REVIEW', 'Decision and reason are required.')
    require(obj.status in ('OPEN', 'REVIEWING') or obj.status == decision, 'INVALID_TRANSITION', 'Conflict is already closed.')
    obj.status, obj.resolution_note, obj.updated_at = decision, reason, timezone.now()
    obj.resolved_at = timezone.now() if decision in ('RESOLVED', 'IGNORED') else None
    obj.save(update_fields=['status', 'resolution_note', 'updated_at', 'resolved_at'])
    history(business, actor, 'CONFLICT_' + decision, obj.canonical_identity, obj.external_identity, evidence={'conflict_id': obj.pk, 'reason': reason})
    return obj


@transaction.atomic
def set_status(business, actor, canonical_id, status, reason):
    """Identity availability is independent of the underlying entity's lifecycle."""
    authorize(actor, business, manager=True)
    lock(business)
    obj = related(m.CanonicalIdentity, canonical_id, business)
    require(status in ('ACTIVE', 'INACTIVE', 'SUPERSEDED') and isinstance(reason, str) and reason.strip(),
            'INVALID_STATUS', 'An availability status and review reason are required. Merge is a separate reviewed operation.')
    require(obj.status != 'MERGED', 'MERGE_CONTRACT_REQUIRED', 'Merged identity redirection cannot be changed here.')
    if obj.status == status:
        return obj
    previous = obj.status
    if status != 'ACTIVE':
        for link_obj in m.IdentityLink.objects.filter(canonical_identity=obj, status='ACTIVE'):
            link_obj.status, link_obj.unlinked_at = 'INVALIDATED', timezone.now()
            link_obj.save(update_fields=['status', 'unlinked_at'])
            history(business, actor, 'UNLINKED', obj, link_obj.external_identity,
                    'IDENTITY_UNAVAILABLE', {'reason': reason})
    obj.status, obj.updated_at = status, timezone.now()
    obj.save(update_fields=['status', 'updated_at'])
    history(business, actor, 'STATUS_CHANGED', obj, evidence={'from': previous, 'to': status, 'reason': reason})
    return obj


@transaction.atomic
def enrich_external(business, actor, external_id, metadata, observed_at, reason, verified=None):
    authorize(actor, business, manager=True)
    lock(business)
    obj = related(m.ExternalIdentity, external_id, business)
    require(isinstance(metadata, dict) and not ({'verified'} & metadata.keys()), 'INVALID_METADATA', 'Provider metadata must be an object; verification uses the explicit argument.')
    require(isinstance(reason, str) and reason.strip() and timezone.is_aware(observed_at), 'EVIDENCE_REQUIRED', 'Observation time with offset and review reason are required.')
    require(verified is None or isinstance(verified, bool), 'INVALID_DATA', 'Verification must be boolean.')
    require(obj.metadata is None or isinstance(obj.metadata, dict), 'INVALID_METADATA', 'Existing metadata requires review.')
    combined = {**(obj.metadata or {}), **metadata}
    if verified is not None:
        combined['verified'] = verified
    obj.metadata = combined
    obj.first_seen_at = min(filter(None, [obj.first_seen_at, observed_at]))
    obj.last_seen_at = max(filter(None, [obj.last_seen_at, observed_at]))
    obj.updated_at = timezone.now()
    from .common import validate
    validate(obj)
    obj.save(update_fields=['metadata', 'first_seen_at', 'last_seen_at', 'updated_at'])
    history(business, actor, 'EXTERNAL_ENRICHED', external=obj, evidence={'reason': reason, 'metadata_keys': sorted(metadata), 'verified': verified})
    return obj


@transaction.atomic
def resolve_many(business, actor, external_ids):
    """All supplied independent evidence must resolve to one customer, or no new link survives."""
    authorize(actor, business, manager=True)
    lock(business)
    require(isinstance(external_ids, list) and 2 <= len(external_ids) <= 20 and
            all(isinstance(pk, int) and not isinstance(pk, bool) for pk in external_ids) and len(set(external_ids)) == len(external_ids), 'INVALID_EVIDENCE', 'Supply 2–20 distinct external identity IDs.')
    identities = [related(m.ExternalIdentity, pk, business) for pk in external_ids]
    require(all(x.entity_type == 'CUSTOMER' for x in identities), 'INVALID_ENTITY', 'Multi-field matching currently supports customer identifiers.')
    require(len({(x.identity_type, x.normalized_value) for x in identities}) > 1,
            'INVALID_EVIDENCE', 'Repeated copies of one identifier are not independent evidence.')
    existing_ids = set(m.IdentityLink.objects.filter(external_identity__in=identities).values_list('pk', flat=True))

    class AbortMatch(Exception):
        pass

    try:
        with transaction.atomic():
            results = [resolve(business, actor, x.pk) for x in identities]
            targets = {link_obj.canonical_identity_id for link_obj, _ in results if link_obj}
            if any(issue for _, issue in results) or len(targets) > 1:
                raise AbortMatch('CONTRADICTORY_IDENTIFIERS', sorted(targets))
            if any(link_obj is None for link_obj, _ in results):
                raise AbortMatch('NO_MATCH', [])
            for link_obj, _ in results:
                if link_obj.pk not in existing_ids:
                    link_obj.match_type, link_obj.rule_key = 'DETERMINISTIC', 'MULTI_FIELD_CORROBORATION'
                    link_obj.metadata = {**(link_obj.metadata or {}), 'external_identity_ids': external_ids}
                    link_obj.save(update_fields=['match_type', 'rule_key', 'metadata'])
            target = results[0][0].canonical_identity
            history(business, actor, 'MULTI_FIELD_MATCH', target, rule='MULTI_FIELD_CORROBORATION', evidence={'external_identity_ids': external_ids})
            return target, None
    except AbortMatch as exc:
        kind, targets = exc.args
        if kind == 'NO_MATCH':
            history(business, actor, 'NO_MATCH', rule='MULTI_FIELD_CORROBORATION', evidence={'external_identity_ids': external_ids})
            return None, None
        return None, conflict(business, actor, kind, identities[0], evidence={'external_identity_ids': external_ids, 'candidate_identity_ids': targets})


@transaction.atomic
def validate_links(business, actor):
    """Review invalid persisted links without silently repairing or discarding identity history."""
    authorize(actor, business, manager=True)
    lock(business)
    from .common import ensure_owned, DomainError
    detected = []
    for obj in m.IdentityLink.objects.filter(canonical_identity__business=business, status='ACTIVE').select_related('canonical_identity', 'external_identity'):
        try:
            ensure_owned(obj, business)
            require(obj.canonical_identity.status == 'ACTIVE', 'INACTIVE_IDENTITY', 'Target is unavailable.')
            require(obj.external_identity.entity_type == obj.canonical_identity.entity_type or
                    obj.match_type == 'ANONYMOUS_TO_KNOWN' and obj.external_identity.entity_type == 'VISITOR' and obj.canonical_identity.entity_type == 'CUSTOMER', 'INVALID_ENTITY', 'Entity type mismatch.')
        except DomainError as exc:
            evidence = {'link_id': obj.pk, 'code': exc.code}
            issue = m.IdentityConflict.objects.filter(business=business, conflict_type='INVALID_LINK',
                    status__in=['OPEN', 'REVIEWING'], conflicting_data=evidence).first()
            if issue is None:
                # Do not retain a foreign external_identity FK in this tenant's audit.
                issue = conflict(business, actor, 'INVALID_LINK',
                    obj.external_identity if obj.external_identity.business_id == business.pk else None,
                    evidence=evidence)
            detected.append(issue)
    return detected
