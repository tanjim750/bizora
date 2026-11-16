"""Canonical graph nodes and relationship-edge projection service.

Serves Business Graph specification sections 1 (Graph Nodes), 2 (Graph Edges),
3 (Graph Building), and 4 (Graph Projection) for ticket T-013.

Key properties enforced:
1. Projection from source-of-truth:
   - Projects canonical entities (Customer, Order, Product, Shipment, etc.)
     into GraphNode instances.
   - Preserves entity_type, entity_id, label, properties, first_seen_at, last_seen_at.
   - Associates canonical_identity when present.
2. Verified relationship edge projection:
   - Converts authoritative BusinessRelationship records into GraphEdge instances.
   - Retains edge direction (source_node -> target_node), relationship_type,
     confidence, validity periods, and business_relationship foreign key.
3. Multi-tenant isolation & Cross-business rejection:
   - Strictly validates that source and target entities belong to the same business.
   - Rejects cross-business corruption with GraphCrossBusinessError.
4. Security Gate SEC-MED-2:
   - Relationship authority is derived from rule_key + relationship_source,
     NEVER from writable metadata.service.
5. Lifecycle and expiry:
   - Expired relationships (valid_to in the past) are not projected as active edges.
6. Atomic & Idempotent:
   - All projection runs execute in transaction.atomic().
   - Repeated projections update in-place without generating duplicates.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
import datetime

from django.db import transaction
from django.db.models import Model
from django.utils import timezone

from app import models


class GraphValidationError(ValueError):
    """A graph parameter, scope, entity, or relationship is invalid."""


class GraphNotFoundError(GraphValidationError):
    """A requested entity, node or snapshot does not exist in the requested business."""


class GraphScopeError(GraphValidationError):
    """An entity does not belong to the requested business."""


class GraphCrossBusinessError(GraphValidationError):
    """Source and target entities belong to different businesses."""


# Supported canonical entity models and their business resolution paths
SUPPORTED_ENTITY_MODELS: dict[str, type[Model]] = {
    "CUSTOMER": models.Customer,
    "PRODUCT": models.Product,
    "PRODUCT_VARIANT": models.ProductVariant,
    "ORDER": models.Order,
    "PAYMENT": models.Payment,
    "SHIPMENT": models.Shipment,
    "CAMPAIGN": models.Campaign,
    "CAMPAIGN_CONVERSION": models.CampaignConversion,
    "WEBSITE_VISITOR": models.WebsiteVisitor,
    "WEBSITE_SESSION": models.WebsiteSession,
    "WEBSITE_EVENT": models.WebsiteEvent,
    "CONVERSATION": models.Conversation,
    "MESSAGE": models.Message,
    "CALL": models.Call,
}

# Closed set of supported deterministic relationship rules (BI §1 / BG §2)
# Maps rule_key -> (source_entity_type, relationship_type, target_entity_type)
SUPPORTED_RELATIONSHIP_RULES: dict[str, tuple[str, str, str]] = {
    "customer_order": ("CUSTOMER", "PLACED_ORDER", "ORDER"),
    "order_product": ("ORDER", "CONTAINS_PRODUCT", "PRODUCT"),
    "order_variant": ("ORDER", "CONTAINS_VARIANT", "PRODUCT_VARIANT"),
    "order_payment": ("ORDER", "HAS_PAYMENT", "PAYMENT"),
    "order_shipment": ("ORDER", "HAS_SHIPMENT", "SHIPMENT"),
    "customer_conversation": ("CUSTOMER", "HAS_CONVERSATION", "CONVERSATION"),
    "customer_message": ("CUSTOMER", "HAS_MESSAGE", "MESSAGE"),
    "conversation_message": ("CONVERSATION", "HAS_MESSAGE", "MESSAGE"),
    "customer_call": ("CUSTOMER", "HAS_CALL", "CALL"),
    "conversation_call": ("CONVERSATION", "HAS_CALL", "CALL"),
    "order_call": ("ORDER", "HAS_CALL", "CALL"),
    "customer_visitor": ("CUSTOMER", "HAS_VISITOR", "WEBSITE_VISITOR"),
    "visitor_session": ("WEBSITE_VISITOR", "HAS_SESSION", "WEBSITE_SESSION"),
    "customer_session": ("CUSTOMER", "HAS_SESSION", "WEBSITE_SESSION"),
    "session_event": ("WEBSITE_SESSION", "HAS_EVENT", "WEBSITE_EVENT"),
    "customer_event": ("CUSTOMER", "HAS_WEBSITE_EVENT", "WEBSITE_EVENT"),
    "event_product": ("WEBSITE_EVENT", "REFERENCES_PRODUCT", "PRODUCT"),
    "event_order": ("WEBSITE_EVENT", "REFERENCES_ORDER", "ORDER"),
    "session_order": ("WEBSITE_SESSION", "REFERENCES_ORDER", "ORDER"),
    "campaign_conversion": ("CAMPAIGN", "HAS_REPORTED_CONVERSION", "CAMPAIGN_CONVERSION"),
    "campaign_customer": ("CAMPAIGN", "REPORTED_CUSTOMER", "CUSTOMER"),
    "campaign_order": ("CAMPAIGN", "REPORTED_ORDER", "ORDER"),
    "campaign_session": ("CAMPAIGN", "REPORTED_SESSION", "WEBSITE_SESSION"),
}

# Business Intelligence persists every rule as "bi.relationship.<name>.v1" (BG-03); the bare
# "<name>" form is what the Graph rule table and its fixtures use. Both resolve to the same
# rule through canonical_rule_name(), which is the single place the two spellings are aligned.
BI_RELATIONSHIP_KEY_PREFIX = "bi.relationship."
BI_RELATIONSHIP_KEY_SUFFIX = ".v1"


def canonical_rule_name(rule_key: str | None) -> str:
    """Return the bare rule name for a bare or Business Intelligence-versioned rule key."""
    key = rule_key or ""
    if key.startswith(BI_RELATIONSHIP_KEY_PREFIX) and key.endswith(BI_RELATIONSHIP_KEY_SUFFIX):
        return key[len(BI_RELATIONSHIP_KEY_PREFIX) : -len(BI_RELATIONSHIP_KEY_SUFFIX)]
    return key


# Every persisted rule_key the Graph is allowed to project (use in rule_key__in filters).
PROJECTABLE_RULE_KEYS = frozenset(SUPPORTED_RELATIONSHIP_RULES) | frozenset(
    f"{BI_RELATIONSHIP_KEY_PREFIX}{name}{BI_RELATIONSHIP_KEY_SUFFIX}" for name in SUPPORTED_RELATIONSHIP_RULES
)

VALID_RELATIONSHIP_SOURCES = frozenset({"DETERMINISTIC", "REPORTED", "DIRECT", "PLATFORM_REPORTED"})


@dataclass(frozen=True)
class ProjectionSummary:
    business_id: int
    nodes_created: int
    nodes_updated: int
    edges_created: int
    edges_updated: int
    edges_pruned: int
    total_nodes: int
    total_edges: int


ENTITY_BUSINESS_LOOKUPS: dict[str, str] = {
    "WEBSITE_EVENT": "session__business_id",
    "MESSAGE": "conversation__business_id",
    "CAMPAIGN_CONVERSION": "campaign__business_id",
    "PRODUCT_VARIANT": "product__business_id",
}


def get_entity_business_filter(entity_type: str, business_id: int) -> dict[str, Any]:
    """Return ORM filter kwargs scoping entity_type to business_id."""
    lookup = ENTITY_BUSINESS_LOOKUPS.get(entity_type, "business_id")
    return {lookup: business_id}


def _resolve_entity_business_id(entity_type: str, entity: Model) -> int:
    """Resolve the authoritative business ID for a canonical entity."""
    lookup = ENTITY_BUSINESS_LOOKUPS.get(entity_type)
    if lookup == "session__business_id":
        if hasattr(entity, "session") and entity.session is not None and hasattr(entity.session, "business_id"):
            return entity.session.business_id
    elif lookup == "conversation__business_id":
        if hasattr(entity, "conversation") and entity.conversation is not None and hasattr(entity.conversation, "business_id"):
            return entity.conversation.business_id
    elif lookup == "campaign__business_id":
        if hasattr(entity, "campaign") and entity.campaign is not None and hasattr(entity.campaign, "business_id"):
            return entity.campaign.business_id
    elif lookup == "product__business_id":
        if hasattr(entity, "product") and entity.product is not None and hasattr(entity.product, "business_id"):
            return entity.product.business_id
    elif hasattr(entity, "business_id"):
        return entity.business_id
    raise GraphValidationError(f"Cannot resolve business_id for entity type {entity_type}")


def _build_node_label(entity_type: str, entity: Model) -> str:
    """Construct human-readable node label (BG §1 Node Labels)."""
    if entity_type == "CUSTOMER":
        return entity.display_name or f"Customer #{entity.pk}"
    elif entity_type == "PRODUCT":
        return entity.name
    elif entity_type == "PRODUCT_VARIANT":
        return getattr(entity, "title", None) or getattr(entity, "sku", None) or f"Variant #{entity.pk}"
    elif entity_type == "ORDER":
        return getattr(entity, "order_number", None) or f"Order #{entity.pk}"
    elif entity_type == "PAYMENT":
        return f"Payment {getattr(entity, 'amount', '')} {getattr(entity, 'currency', '')}".strip()
    elif entity_type == "SHIPMENT":
        return f"Shipment ({getattr(entity, 'provider', '')}) #{entity.pk}"
    elif entity_type == "CAMPAIGN":
        return entity.name
    elif entity_type == "CAMPAIGN_CONVERSION":
        return f"{getattr(entity, 'conversion_type', 'Conversion')} #{entity.pk}"
    elif entity_type == "WEBSITE_VISITOR":
        return getattr(entity, "visitor_key", None) or f"Visitor #{entity.pk}"
    elif entity_type == "WEBSITE_SESSION":
        return f"Session #{entity.pk}"
    elif entity_type == "WEBSITE_EVENT":
        return f"{getattr(entity, 'event_type', 'Event')} #{entity.pk}"
    elif entity_type == "CONVERSATION":
        return f"{getattr(entity, 'channel', '')} Conversation #{entity.pk}"
    elif entity_type == "MESSAGE":
        return f"{getattr(entity, 'direction', '')} Message #{entity.pk}"
    elif entity_type == "CALL":
        return f"{getattr(entity, 'direction', '')} Call #{entity.pk}"
    return f"{entity_type} #{entity.pk}"


def _build_node_properties(entity_type: str, entity: Model) -> dict[str, Any]:
    """Selective graph properties (BG §1 Node Properties / BG §4 Selective Properties)."""
    props: dict[str, Any] = {}
    for attr in ("status", "channel", "priority", "currency", "provider", "event_type", "direction", "total_amount"):
        if hasattr(entity, attr):
            val = getattr(entity, attr)
            if isinstance(val, Decimal):
                val = str(val)
            props[attr] = val
    return props


def _get_entity_timestamps(entity: Model) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    """Extract first_seen_at and last_seen_at for graph nodes (BG §1 Node Activity Tracking)."""
    created = getattr(entity, "created_at", None)
    started = getattr(entity, "started_at", None)
    ordered = getattr(entity, "ordered_at", None)
    first_seen = started or ordered or created

    updated = getattr(entity, "updated_at", None)
    last_msg = getattr(entity, "last_message_at", None)
    resolved = getattr(entity, "resolved_at", None)
    last_seen = last_msg or resolved or updated or first_seen

    return first_seen, last_seen


def project_entity_node(
    *,
    business_id: int,
    entity_type: str,
    entity_id: int,
) -> tuple[models.GraphNode, bool]:
    """Project a canonical entity into a GraphNode. Idempotent. Returns (node, created)."""
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    entity_type = (entity_type or "").upper()
    if entity_type not in SUPPORTED_ENTITY_MODELS:
        raise GraphValidationError(
            f"Unsupported entity_type {entity_type!r}; expected one of {sorted(SUPPORTED_ENTITY_MODELS)}"
        )

    model_cls = SUPPORTED_ENTITY_MODELS[entity_type]
    entity = model_cls.objects.filter(pk=entity_id).first()
    if entity is None:
        raise GraphValidationError(f"Entity {entity_type} #{entity_id} does not exist.")

    actual_business_id = _resolve_entity_business_id(entity_type, entity)
    if actual_business_id != business_id:
        raise GraphScopeError(
            f"Entity {entity_type} #{entity_id} belongs to business {actual_business_id}, not {business_id}."
        )

    label = _build_node_label(entity_type, entity)
    properties = _build_node_properties(entity_type, entity)
    first_seen, last_seen = _get_entity_timestamps(entity)
    now = timezone.now()

    canonical_identity_id = getattr(entity, "canonical_identity_id", None)

    with transaction.atomic():
        node, created = models.GraphNode.objects.update_or_create(
            business_id=business_id,
            entity_type=entity_type,
            entity_id=entity_id,
            defaults={
                "canonical_identity_id": canonical_identity_id,
                "label": label,
                "node_type": entity_type,
                "properties": properties,
                "first_seen_at": first_seen,
                "last_seen_at": last_seen,
                "created_at": getattr(entity, "created_at", now),
                "updated_at": now,
            },
        )
    return node, created


def project_relationship_edge(
    *,
    business_id: int,
    relationship: models.BusinessRelationship,
) -> tuple[models.GraphEdge | None, bool]:
    """Project an authoritative BusinessRelationship into a GraphEdge.

    Security Gate SEC-MED-2: Authority is derived strictly from rule_key and
    relationship_source, never trusting metadata.service.
    Returns (edge, created) or (None, False) if relationship is expired/pruned.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    if relationship.business_id != business_id:
        raise GraphScopeError(
            f"Relationship #{relationship.pk} belongs to business {relationship.business_id}, not {business_id}."
        )

    # 1. Authority validation via rule_key & relationship_source (SEC-MED-2)
    rule_key = relationship.rule_key or ""
    rule_name = canonical_rule_name(rule_key)
    if rule_name not in SUPPORTED_RELATIONSHIP_RULES:
        raise GraphValidationError(
            f"Relationship #{relationship.pk} has unsupported rule_key {rule_key!r}."
        )

    expected_triplet = SUPPORTED_RELATIONSHIP_RULES[rule_name]
    actual_triplet = (
        relationship.source_entity_type,
        relationship.relationship_type,
        relationship.target_entity_type,
    )
    if actual_triplet != expected_triplet:
        raise GraphValidationError(
            f"Relationship #{relationship.pk} triplet {actual_triplet} does not match expected {expected_triplet}."
        )

    source = (relationship.relationship_source or "").upper()
    if source not in VALID_RELATIONSHIP_SOURCES:
        raise GraphValidationError(
            f"Relationship #{relationship.pk} has invalid source {relationship.relationship_source!r}."
        )

    # 2. Expiry check: expired relationships do not remain active graph edges
    now = timezone.now()
    if relationship.valid_to is not None and relationship.valid_to <= now:
        # Prune existing edge if present
        models.GraphEdge.objects.filter(business_relationship=relationship).delete()
        return None, False

    # 3. Source & Target validation and cross-business integrity check
    source_model = SUPPORTED_ENTITY_MODELS.get(relationship.source_entity_type)
    target_model = SUPPORTED_ENTITY_MODELS.get(relationship.target_entity_type)

    if not source_model or not target_model:
        raise GraphValidationError(f"Unsupported source or target entity type in relationship #{relationship.pk}")

    source_entity = source_model.objects.filter(pk=relationship.source_entity_id).first()
    target_entity = target_model.objects.filter(pk=relationship.target_entity_id).first()

    if source_entity is None or target_entity is None:
        raise GraphValidationError(f"Source or target entity missing for relationship #{relationship.pk}")

    s_biz = _resolve_entity_business_id(relationship.source_entity_type, source_entity)
    t_biz = _resolve_entity_business_id(relationship.target_entity_type, target_entity)

    if s_biz != business_id or t_biz != business_id:
        raise GraphCrossBusinessError(
            f"Relationship #{relationship.pk} connects entities across businesses: source has {s_biz}, target has {t_biz}."
        )

    with transaction.atomic():
        source_node, _ = project_entity_node(
            business_id=business_id,
            entity_type=relationship.source_entity_type,
            entity_id=relationship.source_entity_id,
        )
        target_node, _ = project_entity_node(
            business_id=business_id,
            entity_type=relationship.target_entity_type,
            entity_id=relationship.target_entity_id,
        )

        edge_properties = {
            "rule_key": relationship.rule_key,
            "relationship_source": relationship.relationship_source,
            "metadata": relationship.metadata or {},
        }

        edge, created = models.GraphEdge.objects.update_or_create(
            source_node=source_node,
            target_node=target_node,
            relationship_type=relationship.relationship_type,
            defaults={
                "business_id": business_id,
                "business_relationship": relationship,
                "confidence": relationship.confidence,
                "properties": edge_properties,
                "valid_from": relationship.valid_from,
                "valid_to": relationship.valid_to,
                "created_at": relationship.created_at,
                "updated_at": now,
            },
        )
    return edge, created


def project_business_graph(*, business_id: int) -> ProjectionSummary:
    """Full projection of all canonical entities and active relationships for a business."""
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    if not models.Business.objects.filter(pk=business_id).exists():
        raise GraphScopeError(f"Business {business_id} does not exist.")

    nodes_created = 0
    nodes_updated = 0
    edges_created = 0
    edges_updated = 0
    edges_pruned = 0

    with transaction.atomic():
        # 1. Project nodes for all supported canonical entities
        for entity_type, model_cls in SUPPORTED_ENTITY_MODELS.items():
            filter_kwargs = get_entity_business_filter(entity_type, business_id)
            entity_ids = model_cls.objects.filter(**filter_kwargs).values_list("pk", flat=True)
            for e_id in entity_ids:
                _, created = project_entity_node(
                    business_id=business_id,
                    entity_type=entity_type,
                    entity_id=e_id,
                )
                if created:
                    nodes_created += 1
                else:
                    nodes_updated += 1

        # 2. Project edges for all active relationships
        nodes_before_edges = models.GraphNode.objects.filter(business_id=business_id).count()

        rels = models.BusinessRelationship.objects.filter(
            business_id=business_id,
            rule_key__in=PROJECTABLE_RULE_KEYS,
        ).order_by("pk")

        for rel in rels:
            edge, created = project_relationship_edge(
                business_id=business_id,
                relationship=rel,
            )
            if edge is not None:
                if created:
                    edges_created += 1
                else:
                    edges_updated += 1
            else:
                edges_pruned += 1

        nodes_after_edges = models.GraphNode.objects.filter(business_id=business_id).count()
        nodes_created += max(0, nodes_after_edges - nodes_before_edges)

        total_nodes = models.GraphNode.objects.filter(business_id=business_id).count()
        total_edges = models.GraphEdge.objects.filter(business_id=business_id).count()

    return ProjectionSummary(
        business_id=business_id,
        nodes_created=nodes_created,
        nodes_updated=nodes_updated,
        edges_created=edges_created,
        edges_updated=edges_updated,
        edges_pruned=edges_pruned,
        total_nodes=total_nodes,
        total_edges=total_edges,
    )


__all__ = [
    "BI_RELATIONSHIP_KEY_PREFIX",
    "BI_RELATIONSHIP_KEY_SUFFIX",
    "ENTITY_BUSINESS_LOOKUPS",
    "GraphCrossBusinessError",
    "GraphNotFoundError",
    "GraphScopeError",
    "GraphValidationError",
    "ProjectionSummary",
    "SUPPORTED_ENTITY_MODELS",
    "PROJECTABLE_RULE_KEYS",
    "SUPPORTED_RELATIONSHIP_RULES",
    "VALID_RELATIONSHIP_SOURCES",
    "canonical_rule_name",
    "get_entity_business_filter",
    "project_business_graph",
    "project_entity_node",
    "project_relationship_edge",
]
