"""BI specification §1: reconcile explicit canonical references for one business.

Public API: ``rebuild_relationships(*, business_id: int)`` returns immutable
created/updated/unchanged/invalidated counts. This is an internal service; callers
must authorize business access before invoking it. Invalid IDs, missing entities,
foreign-business references and contradictory parent references raise
RelationshipValidationError; occupied tuples owned elsewhere raise
RelationshipConflictError. Either error rolls back the entire reconciliation.

The fixed RULES registry defines uppercase, directed entity/relation vocabulary
and versioned rule keys. Confidence 1 means the canonical reference exists, not
that a payment succeeded or a platform attribution claim is analytically proven.
CampaignConversion references retain source/platform provenance as REPORTED_*
links; UTM strings, names, phones, raw metadata and unresolved identities are
never matched. Customer/message associations use explicit message customer IDs;
conversation participation alone does not identify a message's customer.
Child rows are collected through their parent's business scope (order,
conversation, session or campaign), so a child whose parent belongs to another
business is excluded from this rebuild rather than rejected; it is the owning
business that rejects it. Every direct reference the service reads is still
validated against this business, so no cross-business edge can be created.

Metadata contains sorted, deduplicated canonical evidence references. Unchanged
replays preserve IDs and all timestamps. Removed service-owned links expire via
valid_to, never deletion; reactivation reuses the row with a new valid_from.
The schema permits one row per tuple, so disjoint validity intervals cannot be
retained in that row. Unrelated/manual links are never overwritten or expired.

A Business row lock serializes cooperating rebuilds on row-locking databases.
Canonical writers must coordinate with that lock for a stable concurrent input
snapshot; SQLite does not implement select_for_update row locking. No source
entities, identity decisions, schema, authentication or provider data are changed.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import json

from django.db import IntegrityError, transaction
from django.utils import timezone

from app import models


class RelationshipValidationError(ValueError):
    """The requested business or its canonical reference chain is invalid."""


class RelationshipConflictError(ValueError):
    """The schema's unique tuple is already owned by another relationship rule."""


@dataclass(frozen=True)
class RelationshipRebuildResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    invalidated: int = 0


@dataclass(frozen=True)
class RelationshipRule:
    key: str
    source_type: str
    relationship_type: str
    target_type: str


def _rule(name, source, relationship, target):
    return RelationshipRule(f"bi.relationship.{name}.v1", source, relationship, target)


# A closed registry: new relationships require an explicit, reviewable rule.
RULES = {
    "customer_order": _rule("customer_order", "CUSTOMER", "PLACED_ORDER", "ORDER"),
    "order_product": _rule("order_product", "ORDER", "CONTAINS_PRODUCT", "PRODUCT"),
    "order_variant": _rule("order_variant", "ORDER", "CONTAINS_VARIANT", "PRODUCT_VARIANT"),
    "order_payment": _rule("order_payment", "ORDER", "HAS_PAYMENT", "PAYMENT"),
    "order_shipment": _rule("order_shipment", "ORDER", "HAS_SHIPMENT", "SHIPMENT"),
    "customer_conversation": _rule("customer_conversation", "CUSTOMER", "HAS_CONVERSATION", "CONVERSATION"),
    "customer_message": _rule("customer_message", "CUSTOMER", "HAS_MESSAGE", "MESSAGE"),
    "conversation_message": _rule("conversation_message", "CONVERSATION", "HAS_MESSAGE", "MESSAGE"),
    "customer_call": _rule("customer_call", "CUSTOMER", "HAS_CALL", "CALL"),
    "conversation_call": _rule("conversation_call", "CONVERSATION", "HAS_CALL", "CALL"),
    "order_call": _rule("order_call", "ORDER", "HAS_CALL", "CALL"),
    "customer_visitor": _rule("customer_visitor", "CUSTOMER", "HAS_VISITOR", "WEBSITE_VISITOR"),
    "visitor_session": _rule("visitor_session", "WEBSITE_VISITOR", "HAS_SESSION", "WEBSITE_SESSION"),
    "customer_session": _rule("customer_session", "CUSTOMER", "HAS_SESSION", "WEBSITE_SESSION"),
    "session_event": _rule("session_event", "WEBSITE_SESSION", "HAS_EVENT", "WEBSITE_EVENT"),
    "customer_event": _rule("customer_event", "CUSTOMER", "HAS_WEBSITE_EVENT", "WEBSITE_EVENT"),
    "event_product": _rule("event_product", "WEBSITE_EVENT", "REFERENCES_PRODUCT", "PRODUCT"),
    "event_order": _rule("event_order", "WEBSITE_EVENT", "REFERENCES_ORDER", "ORDER"),
    "session_order": _rule("session_order", "WEBSITE_SESSION", "REFERENCES_ORDER", "ORDER"),
    "campaign_conversion": _rule("campaign_conversion", "CAMPAIGN", "HAS_REPORTED_CONVERSION", "CAMPAIGN_CONVERSION"),
    "campaign_customer": _rule("campaign_customer", "CAMPAIGN", "REPORTED_CUSTOMER", "CUSTOMER"),
    "campaign_order": _rule("campaign_order", "CAMPAIGN", "REPORTED_ORDER", "ORDER"),
    "campaign_session": _rule("campaign_session", "CAMPAIGN", "REPORTED_SESSION", "WEBSITE_SESSION"),
}

_OWNER = "business_intelligence.relationships"
_RULE_KEYS = frozenset(rule.key for rule in RULES.values())
_ENTITY_TYPES = {
    models.Order: "ORDER",
    models.OrderItem: "ORDER_ITEM",
    models.ProductVariant: "PRODUCT_VARIANT",
    models.Payment: "PAYMENT",
    models.Shipment: "SHIPMENT",
    models.Conversation: "CONVERSATION",
    models.ConversationParticipant: "CONVERSATION_PARTICIPANT",
    models.Message: "MESSAGE",
    models.Call: "CALL",
    models.WebsiteVisitor: "WEBSITE_VISITOR",
    models.WebsiteSession: "WEBSITE_SESSION",
    models.WebsiteEvent: "WEBSITE_EVENT",
    models.CampaignConversion: "CAMPAIGN_CONVERSION",
}


@dataclass
class _Candidate:
    rule: RelationshipRule
    evidence: dict = field(default_factory=dict)

    def add_evidence(self, evidence):
        for item in evidence:
            self.evidence[json.dumps(item, sort_keys=True)] = item

    def metadata(self):
        return {
            "service": _OWNER,
            "evidence": [self.evidence[key] for key in sorted(self.evidence)],
        }


def _ref(row, *fields, **details):
    """Reference canonical records without copying customer/provider payloads."""
    return {
        "entity_type": _ENTITY_TYPES[type(row)],
        "entity_id": row.pk,
        "fields": sorted(fields),
        **details,
    }


class _Collector:
    def __init__(self, business_id):
        self.business_id = business_id
        self.candidates = {}
        self.cache = {}

    def roots(self, model):
        rows = list(model.objects.filter(business_id=self.business_id).order_by("pk"))
        for row in rows:
            self.cache[(model, row.pk)] = row
        return rows

    def require(self, model, pk):
        if pk is None:
            return None
        cache_key = (model, pk)
        if cache_key not in self.cache:
            self.cache[cache_key] = model.objects.filter(pk=pk).first()
        row = self.cache[cache_key]
        if row is None:
            raise RelationshipValidationError(f"Missing {model.__name__} reference {pk}.")
        if hasattr(row, "business_id") and row.business_id != self.business_id:
            raise RelationshipValidationError(f"{model.__name__} {pk} belongs to another business.")
        return row

    def customer(self, row):
        return self.require(models.Customer, row.customer_id)

    def integration(self, row):
        self.require(models.IntegrationConnection, row.integration_connection_id)

    def add(self, name, source, target, *evidence):
        if source is None or target is None:
            return
        rule = RULES[name]
        key = (rule.source_type, source.pk, rule.relationship_type, rule.target_type, target.pk)
        candidate = self.candidates.setdefault(key, _Candidate(rule))
        if candidate.rule != rule:
            raise RelationshipConflictError("Multiple service rules produced the same tuple.")
        candidate.add_evidence(evidence)

    def collect(self):
        # Validate root ownership and integrations even when no edge can be made.
        root_models = (
            models.Customer, models.Product, models.Order, models.Payment,
            models.Shipment, models.Conversation, models.Call, models.Campaign,
            models.WebsiteVisitor, models.WebsiteSession,
        )
        roots = {model: self.roots(model) for model in root_models}
        for rows in roots.values():
            for row in rows:
                if hasattr(row, "customer_id"):
                    self.customer(row)
                if hasattr(row, "integration_connection_id"):
                    self.integration(row)

        for order in roots[models.Order]:
            self.add("customer_order", self.customer(order), order, _ref(order, "customer_id"))
        for item in models.OrderItem.objects.filter(order__business_id=self.business_id).order_by("pk"):
            order = self.require(models.Order, item.order_id)
            product = self.require(models.Product, item.product_id)
            variant = self.require(models.ProductVariant, item.product_variant_id)
            evidence = [_ref(item, "order_id", "product_id", "product_variant_id")]
            if variant:
                variant_product = self.require(models.Product, variant.product_id)
                if product is not None and product.pk != variant_product.pk:
                    raise RelationshipValidationError(f"OrderItem {item.pk} variant disagrees with its product.")
                product = variant_product
                evidence.append(_ref(variant, "product_id"))
            self.add("order_product", order, product, *evidence)
            self.add("order_variant", order, variant, *evidence)
        for payment in roots[models.Payment]:
            order = self.require(models.Order, payment.order_id)
            self.add("order_payment", order, payment, _ref(payment, "order_id"))
        for shipment in roots[models.Shipment]:
            order = self.require(models.Order, shipment.order_id)
            self.add("order_shipment", order, shipment, _ref(shipment, "order_id"))

        for conversation in roots[models.Conversation]:
            self.add("customer_conversation", self.customer(conversation), conversation,
                     _ref(conversation, "customer_id"))
        for participant in models.ConversationParticipant.objects.filter(
            conversation__business_id=self.business_id
        ).order_by("pk"):
            conversation = self.require(models.Conversation, participant.conversation_id)
            self.add("customer_conversation", self.customer(participant), conversation,
                     _ref(participant, "conversation_id", "customer_id"))
        for message in models.Message.objects.filter(conversation__business_id=self.business_id).order_by("pk"):
            conversation = self.require(models.Conversation, message.conversation_id)
            customer = self.customer(message)
            self.integration(message)
            evidence = _ref(message, "conversation_id", "customer_id")
            self.add("conversation_message", conversation, message, evidence)
            self.add("customer_message", customer, message, evidence)
        for call in roots[models.Call]:
            conversation = self.require(models.Conversation, call.conversation_id)
            order = self.require(models.Order, call.order_id)
            evidence = _ref(call, "customer_id", "conversation_id", "order_id")
            self.add("customer_call", self.customer(call), call, evidence)
            self.add("conversation_call", conversation, call, evidence)
            self.add("order_call", order, call, evidence)

        for visitor in roots[models.WebsiteVisitor]:
            self.add("customer_visitor", self.customer(visitor), visitor, _ref(visitor, "customer_id"))
        for session in roots[models.WebsiteSession]:
            visitor = self.require(models.WebsiteVisitor, session.visitor_id)
            # The visitor can contain another resolved customer without identifying
            # the customer of this particular session; never merge identities here.
            self.customer(visitor)
            evidence = _ref(session, "visitor_id", "customer_id")
            self.add("visitor_session", visitor, session, evidence)
            self.add("customer_session", self.customer(session), session, evidence)
        for event in models.WebsiteEvent.objects.filter(session__business_id=self.business_id).order_by("pk"):
            session = self.require(models.WebsiteSession, event.session_id)
            visitor = self.require(models.WebsiteVisitor, event.visitor_id)
            if session.visitor_id != visitor.pk:
                raise RelationshipValidationError(f"WebsiteEvent {event.pk} visitor disagrees with its session.")
            self.customer(visitor)
            customer = self.customer(event)
            product = self.require(models.Product, event.product_id)
            order = self.require(models.Order, event.order_id)
            evidence = _ref(event, "session_id", "visitor_id", "customer_id", "product_id", "order_id")
            self.add("session_event", session, event, evidence)
            self.add("customer_event", customer, event, evidence)
            self.add("event_product", event, product, evidence)
            self.add("event_order", event, order, evidence)
            self.add("session_order", session, order, evidence, _ref(session, "visitor_id"))

        for conversion in models.CampaignConversion.objects.filter(
            campaign__business_id=self.business_id
        ).order_by("pk"):
            campaign = self.require(models.Campaign, conversion.campaign_id)
            customer = self.customer(conversion)
            order = self.require(models.Order, conversion.order_id)
            session = self.require(models.WebsiteSession, conversion.website_session_id)
            # website_session_id is an integer, not a schema-enforced foreign key.
            if session:
                visitor = self.require(models.WebsiteVisitor, session.visitor_id)
                self.customer(visitor)
                self.customer(session)
                self.integration(session)
            evidence = _ref(
                conversion, "campaign_id", "customer_id", "order_id", "website_session_id",
                provenance="SOURCE_REPORTED", platform=campaign.platform,
                attribution_type=conversion.attribution_type,
                integration_connection_id=campaign.integration_connection_id,
            )
            self.add("campaign_conversion", campaign, conversion, evidence)
            self.add("campaign_customer", campaign, customer, evidence)
            self.add("campaign_order", campaign, order, evidence)
            self.add("campaign_session", campaign, session, evidence)
        return self.candidates


def _key(row):
    return (row.source_entity_type, row.source_entity_id, row.relationship_type,
            row.target_entity_type, row.target_entity_id)


def _owned(row):
    return (row.rule_key in _RULE_KEYS and row.relationship_source == "DETERMINISTIC"
            and isinstance(row.metadata, dict) and row.metadata.get("service") == _OWNER)


def rebuild_relationships(*, business_id):
    """Atomically reconcile supported explicit links; perform no authorization."""
    if (isinstance(business_id, bool) or not isinstance(business_id, int)
            or not 1 <= business_id < 2 ** 63):
        raise RelationshipValidationError("business_id must be a positive 64-bit integer.")
    try:
        with transaction.atomic():
            try:
                models.Business.objects.select_for_update().get(pk=business_id)
            except models.Business.DoesNotExist as exc:
                raise RelationshipValidationError("Business does not exist.") from exc
            candidates = _Collector(business_id).collect()
            existing = {
                _key(row): row for row in models.BusinessRelationship.objects.select_for_update()
                .filter(business_id=business_id).order_by("pk")
            }
            # Detect conflicts before applying any updates or expirations.
            for key, candidate in candidates.items():
                row = existing.get(key)
                if row is not None and (not _owned(row) or row.rule_key != candidate.rule.key):
                    raise RelationshipConflictError(f"Relationship tuple is owned elsewhere: {key}.")
            now = timezone.now()
            counts = dict(created=0, updated=0, unchanged=0, invalidated=0)
            for key, candidate in sorted(candidates.items()):
                row = existing.get(key)
                metadata = candidate.metadata()
                if row is None:
                    models.BusinessRelationship.objects.create(
                        business_id=business_id, source_entity_type=key[0], source_entity_id=key[1],
                        relationship_type=key[2], target_entity_type=key[3], target_entity_id=key[4],
                        rule_key=candidate.rule.key, relationship_source="DETERMINISTIC",
                        confidence=Decimal("1.0000"), metadata=metadata,
                        valid_from=now, valid_to=None, created_at=now, updated_at=now,
                    )
                    counts["created"] += 1
                elif row.metadata != metadata or row.confidence != Decimal("1") or row.valid_to is not None:
                    row.metadata = metadata
                    row.confidence = Decimal("1.0000")
                    if row.valid_to is not None:
                        row.valid_from = now
                    row.valid_to = None
                    row.updated_at = now
                    row.save(update_fields=["metadata", "confidence", "valid_from", "valid_to", "updated_at"])
                    counts["updated"] += 1
                else:
                    counts["unchanged"] += 1
            for key, row in existing.items():
                if key not in candidates and _owned(row) and row.valid_to is None:
                    row.valid_to = now
                    row.updated_at = now
                    row.save(update_fields=["valid_to", "updated_at"])
                    counts["invalidated"] += 1
            return RelationshipRebuildResult(**counts)
    except IntegrityError as exc:
        # A non-cooperating writer may race the unique tuple despite the lock.
        raise RelationshipConflictError("Relationship reconciliation encountered a database constraint conflict.") from exc
