"""Graph snapshots and evidence-aware context services.

Serves Business Graph specification sections 12 (Graph Snapshots) and 13 (Evidence-Aware Graph)
for ticket T-018.

Key principles enforced:
1. Stable serialized snapshots:
   - Persists graph nodes, edges, timeline, and summary in snapshot_data.
   - Snapshots remain completely stable even after later underlying graph changes or pruning.
2. Evidence awareness & Traceability:
   - Connects graph edges to authoritative BusinessRelationship records with rule_key,
     relationship_source, confidence, and metadata.
   - Links nodes with verified BusinessFact and BusinessIssue records.
3. Explainable paths:
   - Provides step-by-step explanation for why each edge exists and what evidence grounds it.
4. Multi-tenant isolation:
   - Strictly enforces business scope on snapshot creation, retrieval, and evidence lookup.
"""

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any
import datetime

from django.db import transaction
from django.utils import timezone

from app import models
from app.business_graph.journeys import (
    CustomerJourney,
    OrderJourney,
    build_campaign_journey,
    build_customer_journey,
    build_order_journey,
    build_product_journey,
)
from app.business_graph.projection import (
    GraphCrossBusinessError,
    GraphScopeError,
    GraphValidationError,
)
from app.business_graph.traversal import (
    GraphFilter,
    GraphPath,
    traverse_graph,
)


SUPPORTED_SNAPSHOT_TYPES = frozenset({
    "BUSINESS",
    "CUSTOMER",
    "ORDER",
    "PRODUCT",
    "CAMPAIGN",
})


@dataclass
class EvidenceContext:
    business_id: int
    edge_evidence: dict[int, dict[str, Any]] = field(default_factory=dict)
    node_facts: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    node_issues: dict[int, list[dict[str, Any]]] = field(default_factory=dict)


def _serialize_node(node: models.GraphNode) -> dict[str, Any]:
    """Serialize a GraphNode into a stable dictionary."""
    return {
        "id": node.pk,
        "entity_type": node.entity_type,
        "entity_id": node.entity_id,
        "canonical_identity_id": node.canonical_identity_id,
        "label": node.label,
        "node_type": node.node_type,
        "properties": node.properties or {},
        "first_seen_at": node.first_seen_at.isoformat() if node.first_seen_at else None,
        "last_seen_at": node.last_seen_at.isoformat() if node.last_seen_at else None,
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }


def _serialize_edge(edge: models.GraphEdge) -> dict[str, Any]:
    """Serialize a GraphEdge into a stable dictionary."""
    return {
        "id": edge.pk,
        "source_node_id": edge.source_node_id,
        "target_node_id": edge.target_node_id,
        "relationship_type": edge.relationship_type,
        "confidence": str(edge.confidence),
        "properties": edge.properties or {},
        "valid_from": edge.valid_from.isoformat() if edge.valid_from else None,
        "valid_to": edge.valid_to.isoformat() if edge.valid_to else None,
        "business_relationship_id": edge.business_relationship_id,
    }


def _serialize_timeline(timeline: list[Any]) -> list[dict[str, Any]]:
    """Serialize timeline events into JSON-safe dictionaries."""
    serialized = []
    for ev in timeline:
        serialized.append({
            "entity_type": ev.entity_type,
            "entity_id": ev.entity_id,
            "label": ev.label,
            "stage": ev.stage,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "properties": ev.properties,
            "connecting_relationships": ev.connecting_relationships,
        })
    return serialized


def create_graph_snapshot(
    *,
    business_id: int,
    snapshot_type: str = "BUSINESS",
    name: str | None = None,
    root_entity_type: str | None = None,
    root_entity_id: int | None = None,
    filters: GraphFilter | None = None,
) -> models.GraphSnapshot:
    """Create and persist a stable graph snapshot.

    Captures current nodes, edges, timeline, and structural summaries.
    The resulting snapshot_data is independent of later modifications to the graph.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    if not models.Business.objects.filter(pk=business_id).exists():
        raise GraphScopeError(f"Business {business_id} does not exist.")

    snapshot_type = (snapshot_type or "BUSINESS").upper()
    if snapshot_type not in SUPPORTED_SNAPSHOT_TYPES:
        raise GraphValidationError(
            f"Unsupported snapshot_type {snapshot_type!r}; expected one of {sorted(SUPPORTED_SNAPSHOT_TYPES)}"
        )

    now = timezone.now()
    nodes: list[models.GraphNode] = []
    edges: list[models.GraphEdge] = []
    timeline: list[Any] = []
    summary: dict[str, Any] = {}

    if snapshot_type == "BUSINESS":
        nodes = list(models.GraphNode.objects.filter(business_id=business_id).order_by("id"))
        edges = list(models.GraphEdge.objects.filter(business_id=business_id).order_by("id"))
        summary = {"type": "FULL_BUSINESS_GRAPH", "node_count": len(nodes), "edge_count": len(edges)}
        name = name or f"Business Graph Snapshot ({now.strftime('%Y-%m-%d %H:%M')})"

    elif snapshot_type == "CUSTOMER":
        if not root_entity_id:
            raise GraphValidationError("root_entity_id is required for CUSTOMER snapshot")
        root_entity_type = "CUSTOMER"
        journey = build_customer_journey(
            business_id=business_id,
            customer_id=root_entity_id,
            filters=filters,
        )
        nodes = journey.nodes
        edges = journey.edges
        timeline = journey.timeline
        summary = journey.summary
        name = name or f"Customer Journey Snapshot #{root_entity_id}"

    elif snapshot_type == "ORDER":
        if not root_entity_id:
            raise GraphValidationError("root_entity_id is required for ORDER snapshot")
        root_entity_type = "ORDER"
        oj = build_order_journey(
            business_id=business_id,
            order_id=root_entity_id,
            filters=filters,
        )
        nodes = oj.nodes
        edges = oj.edges
        timeline = oj.timeline
        summary = {"status": oj.status, "total_amount": oj.total_amount, "node_count": len(nodes), "edge_count": len(edges)}
        name = name or f"Order Journey Snapshot #{root_entity_id}"

    elif snapshot_type == "PRODUCT":
        if not root_entity_id:
            raise GraphValidationError("root_entity_id is required for PRODUCT snapshot")
        root_entity_type = "PRODUCT"
        pj = build_product_journey(
            business_id=business_id,
            product_id=root_entity_id,
            filters=filters,
        )
        nodes = pj.nodes
        edges = pj.edges
        timeline = pj.timeline
        summary = pj.summary
        name = name or f"Product Journey Snapshot #{root_entity_id}"

    elif snapshot_type == "CAMPAIGN":
        if not root_entity_id:
            raise GraphValidationError("root_entity_id is required for CAMPAIGN snapshot")
        root_entity_type = "CAMPAIGN"
        cj = build_campaign_journey(
            business_id=business_id,
            campaign_id=root_entity_id,
            filters=filters,
        )
        nodes = cj.nodes
        edges = cj.edges
        timeline = cj.timeline
        summary = cj.summary
        name = name or f"Campaign Journey Snapshot #{root_entity_id}"

    serialized_data = {
        "nodes": [_serialize_node(n) for n in nodes],
        "edges": [_serialize_edge(e) for e in edges],
        "timeline": _serialize_timeline(timeline),
        "summary": summary,
    }

    serialized_filters: dict[str, Any] = {}
    if filters:
        if filters.entity_types:
            serialized_filters["entity_types"] = sorted(filters.entity_types)
        if filters.relationship_types:
            serialized_filters["relationship_types"] = sorted(filters.relationship_types)
        if filters.min_confidence is not None:
            serialized_filters["min_confidence"] = str(filters.min_confidence)
        if filters.status:
            serialized_filters["status"] = filters.status
        if filters.channel:
            serialized_filters["channel"] = filters.channel
        if filters.provider:
            serialized_filters["provider"] = filters.provider
        if filters.dimensions:
            serialized_filters["dimensions"] = filters.dimensions

    with transaction.atomic():
        snapshot = models.GraphSnapshot.objects.create(
            business_id=business_id,
            name=name,
            snapshot_type=snapshot_type,
            root_entity_type=root_entity_type,
            root_entity_id=root_entity_id,
            node_count=len(nodes),
            edge_count=len(edges),
            filters=serialized_filters or None,
            snapshot_data=serialized_data,
            generated_at=now,
            created_at=now,
        )

    return snapshot


def get_graph_snapshot(
    *,
    business_id: int,
    snapshot_id: int,
) -> models.GraphSnapshot:
    """Retrieve a graph snapshot by ID with multi-tenant scope enforcement."""
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    snapshot = models.GraphSnapshot.objects.filter(pk=snapshot_id).first()
    if snapshot is None:
        raise GraphValidationError(f"GraphSnapshot #{snapshot_id} does not exist.")

    if snapshot.business_id != business_id:
        raise GraphScopeError(
            f"GraphSnapshot #{snapshot_id} belongs to business {snapshot.business_id}, not {business_id}."
        )

    return snapshot


def build_evidence_context(
    *,
    business_id: int,
    nodes: list[models.GraphNode],
    edges: list[models.GraphEdge],
) -> EvidenceContext:
    """Retrieve authoritative evidence, verified facts, and issues for graph elements.

    Implements BG §13 (Evidence-Aware Graph).
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    # 1. Edge evidence via BusinessRelationship
    edge_evidence: dict[int, dict[str, Any]] = {}
    rel_ids = [e.business_relationship_id for e in edges if e.business_relationship_id is not None]
    if rel_ids:
        rels = models.BusinessRelationship.objects.filter(
            business_id=business_id,
            pk__in=rel_ids,
        )
        rel_map = {r.pk: r for r in rels}

        for edge in edges:
            if edge.business_relationship_id in rel_map:
                rel = rel_map[edge.business_relationship_id]
                edge_evidence[edge.pk] = {
                    "relationship_id": rel.pk,
                    "rule_key": rel.rule_key,
                    "relationship_source": rel.relationship_source,
                    "confidence": str(rel.confidence),
                    "valid_from": rel.valid_from.isoformat() if rel.valid_from else None,
                    "valid_to": rel.valid_to.isoformat() if rel.valid_to else None,
                    "metadata": rel.metadata or {},
                }

    # 2. Node facts via BusinessFact
    node_facts: dict[int, list[dict[str, Any]]] = {n.pk: [] for n in nodes}
    for n in nodes:
        facts = models.BusinessFact.objects.filter(
            business_id=business_id,
            subject_entity_type=n.entity_type,
            subject_entity_id=n.entity_id,
        ).order_by("pk")
        for f in facts:
            node_facts[n.pk].append({
                "fact_id": f.pk,
                "fact_type": f.fact_type,
                "statement": f.statement,
                "value": str(f.value) if f.value is not None else None,
                "value_unit": f.value_unit,
                "confidence": str(f.confidence),
                "status": f.status,
                "rule_key": f.rule_key,
            })

    # 3. Node issues via BusinessIssue
    node_issues: dict[int, list[dict[str, Any]]] = {n.pk: [] for n in nodes}
    for n in nodes:
        issues = models.BusinessIssue.objects.filter(
            business_id=business_id,
            subject_entity_type=n.entity_type,
            subject_entity_id=n.entity_id,
        ).order_by("pk")
        for iss in issues:
            node_issues[n.pk].append({
                "issue_id": iss.pk,
                "issue_type": iss.issue_type,
                "title": iss.title,
                "severity": iss.severity,
                "status": iss.status,
                "confidence": str(iss.confidence),
                "description": iss.description,
            })

    return EvidenceContext(
        business_id=business_id,
        edge_evidence=edge_evidence,
        node_facts=node_facts,
        node_issues=node_issues,
    )


def explain_path(
    *,
    business_id: int,
    path: GraphPath,
) -> list[dict[str, Any]]:
    """Generate step-by-step explainable evidence for a graph path.

    Explains why each edge exists and what facts/issues touch each participating node.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    evidence_context = build_evidence_context(
        business_id=business_id,
        nodes=path.nodes,
        edges=path.edges,
    )

    explanation: list[dict[str, Any]] = []
    for step in path.steps:
        node = step.node
        edge = step.edge_to_next

        step_dict = {
            "node": {
                "id": node.pk,
                "entity_type": node.entity_type,
                "entity_id": node.entity_id,
                "label": node.label,
                "facts": evidence_context.node_facts.get(node.pk, []),
                "issues": evidence_context.node_issues.get(node.pk, []),
            },
            "edge": None,
        }

        if edge is not None:
            step_dict["edge"] = {
                "id": edge.pk,
                "relationship_type": edge.relationship_type,
                "confidence": str(edge.confidence),
                "evidence": evidence_context.edge_evidence.get(edge.pk, {}),
            }

        explanation.append(step_dict)

    return explanation


__all__ = [
    "EvidenceContext",
    "SUPPORTED_SNAPSHOT_TYPES",
    "build_evidence_context",
    "create_graph_snapshot",
    "explain_path",
    "get_graph_snapshot",
]
