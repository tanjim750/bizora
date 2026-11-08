"""Projection synchronization, pruning, and full rebuild services for Business Graph.

Serves Business Graph specification sections 3 (Graph Building) and 4 (Graph Projection)
for ticket T-014.

Features implemented:
1. Incremental graph node sync:
   - Synchronizes individual canonical entities (upsert / delete).
   - Keeps node properties, timestamps, and canonical identity links fresh.
   - Cleans up associated edges when an entity node is deleted.
2. Incremental graph edge sync:
   - Synchronizes authoritative BusinessRelationship records into GraphEdge.
   - Prunes or rejects expired, invalid, or cross-business relationships.
   - Deletes graph edges when relationships are deleted or invalidated.
3. Stale projection cleanup (Pruning):
   - Removes orphan nodes whose underlying canonical records no longer exist.
   - Removes orphan edges whose source/target nodes or underlying relationships were deleted.
   - Prunes expired edges (valid_to in the past).
4. Full graph rebuild:
   - Scoped strictly to the requested business.
   - Fully atomic and idempotent.
   - Supports clean rebuild (wipe & reproject) or reconciliation rebuild (prune stale & update).
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from app import models
from app.business_graph.projection import (
    GraphScopeError,
    GraphValidationError,
    SUPPORTED_ENTITY_MODELS,
    SUPPORTED_RELATIONSHIP_RULES,
    project_business_graph,
    project_entity_node,
    project_relationship_edge,
)


@dataclass(frozen=True)
class PruneSummary:
    business_id: int
    stale_nodes_pruned: int
    stale_edges_pruned: int


@dataclass(frozen=True)
class RebuildSummary:
    business_id: int
    nodes_created: int
    nodes_updated: int
    nodes_pruned: int
    edges_created: int
    edges_updated: int
    edges_pruned: int
    total_nodes: int
    total_edges: int


def _get_existing_entity_pks(business_id: int, entity_type: str, candidate_pks: list[int]) -> set[int]:
    """Retrieve existing primary keys belonging to business_id for a given entity_type."""
    if not candidate_pks:
        return set()
    model_cls = SUPPORTED_ENTITY_MODELS.get(entity_type)
    if not model_cls:
        return set()

    filter_kwargs: dict[str, Any] = {"pk__in": candidate_pks}
    if hasattr(model_cls, "business_id"):
        filter_kwargs["business_id"] = business_id
    elif hasattr(model_cls, "product"):
        filter_kwargs["product__business_id"] = business_id
    elif hasattr(model_cls, "campaign"):
        filter_kwargs["campaign__business_id"] = business_id
    elif hasattr(model_cls, "session"):
        filter_kwargs["session__business_id"] = business_id
    elif hasattr(model_cls, "conversation"):
        filter_kwargs["conversation__business_id"] = business_id
    else:
        return set()

    return set(model_cls.objects.filter(**filter_kwargs).values_list("pk", flat=True))


def prune_stale_projections(*, business_id: int) -> PruneSummary:
    """Identify and delete stale graph nodes and edges for a business.

    Stale projections include:
    1. GraphNodes whose canonical entity record no longer exists or changed business.
    2. GraphEdges whose business_relationship is deleted, expired, or invalid.
    3. GraphEdges whose source or target nodes no longer exist or belong to another business.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    stale_nodes_count = 0
    stale_edges_count = 0
    now = timezone.now()

    with transaction.atomic():
        # 1. Prune edges expired by valid_to
        expired_edges = models.GraphEdge.objects.filter(
            business_id=business_id,
            valid_to__lte=now,
        )
        count_expired = expired_edges.count()
        if count_expired > 0:
            expired_edges.delete()
            stale_edges_count += count_expired

        # 2. Prune edges pointing to non-existent or deleted BusinessRelationships
        all_edge_rel_ids = set(
            models.GraphEdge.objects.filter(
                business_id=business_id,
                business_relationship__isnull=False,
            ).values_list("business_relationship_id", flat=True)
        )
        if all_edge_rel_ids:
            active_rel_ids = set(
                models.BusinessRelationship.objects.filter(
                    business_id=business_id,
                    pk__in=all_edge_rel_ids,
                    rule_key__in=SUPPORTED_RELATIONSHIP_RULES.keys(),
                ).values_list("pk", flat=True)
            )
            orphan_rel_ids = all_edge_rel_ids - active_rel_ids
            if orphan_rel_ids:
                deleted_count, _ = models.GraphEdge.objects.filter(
                    business_id=business_id,
                    business_relationship_id__in=orphan_rel_ids,
                ).delete()
                stale_edges_count += deleted_count

        # 3. Check for stale nodes per entity_type
        nodes_qs = models.GraphNode.objects.filter(business_id=business_id)
        entity_types = nodes_qs.values_list("entity_type", flat=True).distinct()

        stale_node_ids: list[int] = []
        for et in entity_types:
            node_pks_map = dict(
                nodes_qs.filter(entity_type=et).values_list("id", "entity_id")
            )
            candidate_entity_ids = list(node_pks_map.values())
            valid_entity_ids = _get_existing_entity_pks(business_id, et, candidate_entity_ids)
            for node_id, entity_id in node_pks_map.items():
                if entity_id not in valid_entity_ids:
                    stale_node_ids.append(node_id)

        if stale_node_ids:
            # Delete attached edges first
            deleted_edges, _ = models.GraphEdge.objects.filter(
                business_id=business_id,
                source_node_id__in=stale_node_ids,
            ).delete()
            stale_edges_count += deleted_edges

            deleted_target_edges, _ = models.GraphEdge.objects.filter(
                business_id=business_id,
                target_node_id__in=stale_node_ids,
            ).delete()
            stale_edges_count += deleted_target_edges

            # Delete the stale nodes
            deleted_nodes, _ = models.GraphNode.objects.filter(id__in=stale_node_ids).delete()
            stale_nodes_count += deleted_nodes

        # 4. Final check for any dangling edges whose source or target nodes were deleted
        existing_node_ids = set(models.GraphNode.objects.filter(business_id=business_id).values_list("id", flat=True))
        dangling_edges = models.GraphEdge.objects.filter(business_id=business_id).exclude(
            source_node_id__in=existing_node_ids,
            target_node_id__in=existing_node_ids,
        )
        dangling_count = dangling_edges.count()
        if dangling_count > 0:
            dangling_edges.delete()
            stale_edges_count += dangling_count

    return PruneSummary(
        business_id=business_id,
        stale_nodes_pruned=stale_nodes_count,
        stale_edges_pruned=stale_edges_count,
    )


def sync_entity_node(
    *,
    business_id: int,
    entity_type: str,
    entity_id: int,
    action: str = "upsert",
) -> tuple[models.GraphNode | None, bool]:
    """Incrementally synchronize a canonical entity change to the graph.

    action="upsert": creates or updates the GraphNode, and refreshes any
                     existing active relationships connected to this entity.
    action="delete": removes the GraphNode and deletes all connected GraphEdges.
    Returns (node, created_or_modified).
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    action = (action or "").lower()
    if action not in ("upsert", "delete"):
        raise GraphValidationError(f"Invalid action {action!r}; expected 'upsert' or 'delete'.")

    entity_type = (entity_type or "").upper()
    if entity_type not in SUPPORTED_ENTITY_MODELS:
        raise GraphValidationError(
            f"Unsupported entity_type {entity_type!r}; expected one of {sorted(SUPPORTED_ENTITY_MODELS)}"
        )

    with transaction.atomic():
        if action == "delete":
            node = models.GraphNode.objects.filter(
                business_id=business_id,
                entity_type=entity_type,
                entity_id=entity_id,
            ).first()
            if node is not None:
                # Remove connected edges first
                models.GraphEdge.objects.filter(source_node=node).delete()
                models.GraphEdge.objects.filter(target_node=node).delete()
                node.delete()
                return None, True
            return None, False

        # action == "upsert"
        node, created = project_entity_node(
            business_id=business_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        # Refresh connected relationships for this entity if any exist
        connected_rels = models.BusinessRelationship.objects.filter(
            business_id=business_id,
            rule_key__in=SUPPORTED_RELATIONSHIP_RULES.keys(),
        ).filter(
            Q(source_entity_type=entity_type, source_entity_id=entity_id)
            | Q(target_entity_type=entity_type, target_entity_id=entity_id)
        )
        for rel in connected_rels:
            project_relationship_edge(business_id=business_id, relationship=rel)

        return node, created


def sync_relationship_edge(
    *,
    business_id: int,
    relationship_id: int,
    action: str = "upsert",
) -> tuple[models.GraphEdge | None, bool]:
    """Incrementally synchronize an authoritative relationship change to the graph.

    action="upsert": projects or updates the GraphEdge. Prunes if expired or invalid.
    action="delete": deletes the GraphEdge for this BusinessRelationship.
    Returns (edge, created_or_modified).
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    action = (action or "").lower()
    if action not in ("upsert", "delete"):
        raise GraphValidationError(f"Invalid action {action!r}; expected 'upsert' or 'delete'.")

    with transaction.atomic():
        if action == "delete":
            deleted_count, _ = models.GraphEdge.objects.filter(
                business_id=business_id,
                business_relationship_id=relationship_id,
            ).delete()
            return None, deleted_count > 0

        # action == "upsert"
        rel = models.BusinessRelationship.objects.filter(pk=relationship_id).first()
        if rel is None:
            raise GraphValidationError(f"Relationship #{relationship_id} does not exist.")

        if rel.business_id != business_id:
            raise GraphScopeError(
                f"Relationship #{relationship_id} belongs to business {rel.business_id}, not {business_id}."
            )

        edge, created = project_relationship_edge(
            business_id=business_id,
            relationship=rel,
        )
        return edge, created


def rebuild_business_graph(
    *,
    business_id: int,
    clean: bool = False,
) -> RebuildSummary:
    """Perform a full synchronization or clean rebuild of the business graph.

    If clean=True: deletes all GraphEdge and GraphNode records for business_id,
                   then projects all canonical entities and active relationships.
    If clean=False: prunes stale projections first, then reconciles/projects
                    all canonical entities and active relationships.
    Fully atomic and idempotent.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    if not models.Business.objects.filter(pk=business_id).exists():
        raise GraphScopeError(f"Business {business_id} does not exist.")

    with transaction.atomic():
        nodes_pruned = 0
        edges_pruned = 0

        if clean:
            edges_pruned, _ = models.GraphEdge.objects.filter(business_id=business_id).delete()
            nodes_pruned, _ = models.GraphNode.objects.filter(business_id=business_id).delete()
        else:
            prune_summary = prune_stale_projections(business_id=business_id)
            nodes_pruned = prune_summary.stale_nodes_pruned
            edges_pruned = prune_summary.stale_edges_pruned

        projection_summary = project_business_graph(business_id=business_id)
        edges_pruned += projection_summary.edges_pruned

    return RebuildSummary(
        business_id=business_id,
        nodes_created=projection_summary.nodes_created,
        nodes_updated=projection_summary.nodes_updated,
        nodes_pruned=nodes_pruned,
        edges_created=projection_summary.edges_created,
        edges_updated=projection_summary.edges_updated,
        edges_pruned=edges_pruned,
        total_nodes=projection_summary.total_nodes,
        total_edges=projection_summary.total_edges,
    )


__all__ = [
    "PruneSummary",
    "RebuildSummary",
    "prune_stale_projections",
    "rebuild_business_graph",
    "sync_entity_node",
    "sync_relationship_edge",
]
