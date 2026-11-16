"""Graph traversal, path search, query, and filtering services.

Serves Business Graph specification sections 9 (Graph Traversal), 10 (Graph Query),
and 11 (Graph Filtering) for ticket T-015.

Key principles enforced:
1. Multi-tenant isolation:
   - Root nodes, candidate nodes, and traversed edges must strictly match business_id.
   - Any attempt to query outside business raises GraphScopeError.
2. Bounded & Cycle-safe traversal:
   - Traversal depth is strictly capped (max_depth).
   - Max node count is strictly capped (max_nodes) to prevent unbounded memory growth.
   - Visited sets and per-path tracking eliminate cycle loops.
3. Direction awareness:
   - Supports 'OUTBOUND', 'INBOUND', and 'BIDIRECTIONAL' traversal.
4. Flexible filtering:
   - Filters on entity types, relationship types, confidence cutoffs, validity timestamps,
     time horizons, and node/edge properties.
5. Deterministic ordering:
   - Traversal results and path searches return deterministic sequences.
6. Missing relationships remain missing:
   - Never fabricates edges or paths when no verified connection exists.
"""

from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
import datetime

from django.db.models import Q

from app import models
from app.business_graph.projection import (
    GraphScopeError,
    GraphNotFoundError,
    GraphValidationError,
)


VALID_DIRECTIONS = frozenset({"OUTBOUND", "INBOUND", "BIDIRECTIONAL"})


@dataclass(frozen=True)
class GraphFilter:
    entity_types: frozenset[str] | None = None
    relationship_types: frozenset[str] | None = None
    min_confidence: Decimal | None = None
    valid_at: datetime.datetime | None = None
    time_from: datetime.datetime | None = None
    time_to: datetime.datetime | None = None
    node_properties: dict[str, Any] | None = None
    edge_properties: dict[str, Any] | None = None
    status: str | None = None
    channel: str | None = None
    provider: str | None = None
    dimensions: dict[str, Any] | None = None


@dataclass
class TraversalResult:
    business_id: int
    root_node_id: int
    depth_reached: int
    truncated: bool
    nodes: list[models.GraphNode] = field(default_factory=list)
    edges: list[models.GraphEdge] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


@dataclass(frozen=True)
class PathStep:
    node: models.GraphNode
    edge_to_next: models.GraphEdge | None = None


@dataclass(frozen=True)
class GraphPath:
    steps: tuple[PathStep, ...]

    @property
    def length(self) -> int:
        return max(0, len(self.steps) - 1)

    @property
    def nodes(self) -> list[models.GraphNode]:
        return [step.node for step in self.steps]

    @property
    def edges(self) -> list[models.GraphEdge]:
        return [step.edge_to_next for step in self.steps if step.edge_to_next is not None]


def _matches_node_filter(node: models.GraphNode, filters: GraphFilter | None) -> bool:
    """Check if a GraphNode matches the provided filter criteria."""
    if filters is None:
        return True

    if filters.entity_types and node.entity_type not in filters.entity_types:
        return False

    if filters.time_from and node.created_at and node.created_at < filters.time_from:
        return False

    if filters.time_to and node.created_at and node.created_at > filters.time_to:
        return False

    if filters.status:
        props = node.properties or {}
        if props.get("status") != filters.status:
            return False

    if filters.channel:
        props = node.properties or {}
        if props.get("channel") != filters.channel:
            return False

    if filters.provider:
        props = node.properties or {}
        if props.get("provider") != filters.provider:
            return False

    if filters.dimensions:
        props = node.properties or {}
        for k, v in filters.dimensions.items():
            if props.get(k) != v:
                return False

    if filters.node_properties:
        props = node.properties or {}
        for k, v in filters.node_properties.items():
            if props.get(k) != v:
                return False

    return True


def _matches_edge_filter(edge: models.GraphEdge, filters: GraphFilter | None) -> bool:
    """Check if a GraphEdge matches the provided filter criteria."""
    if filters is None:
        return True

    if filters.relationship_types and edge.relationship_type not in filters.relationship_types:
        return False

    if filters.min_confidence is not None and edge.confidence < filters.min_confidence:
        return False

    if filters.valid_at is not None:
        if edge.valid_from and edge.valid_from > filters.valid_at:
            return False
        if edge.valid_to and edge.valid_to < filters.valid_at:
            return False

    if filters.time_from and edge.created_at and edge.created_at < filters.time_from:
        return False

    if filters.time_to and edge.created_at and edge.created_at > filters.time_to:
        return False

    if filters.edge_properties:
        props = edge.properties or {}
        for k, v in filters.edge_properties.items():
            if props.get(k) != v:
                return False

    return True


def get_neighbors(
    *,
    business_id: int,
    node_id: int,
    direction: str = "BIDIRECTIONAL",
    filters: GraphFilter | None = None,
    limit: int | None = None,
) -> list[tuple[models.GraphEdge, models.GraphNode]]:
    """Retrieve direct neighbors and connecting edges for a node.

    direction: 'OUTBOUND', 'INBOUND', or 'BIDIRECTIONAL'.
    Returns list of (edge, neighbor_node) deterministically sorted.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    direction = (direction or "BIDIRECTIONAL").upper()
    if direction not in VALID_DIRECTIONS:
        raise GraphValidationError(
            f"Invalid direction {direction!r}; expected one of {sorted(VALID_DIRECTIONS)}"
        )

    node = models.GraphNode.objects.filter(pk=node_id).first()
    if node is None:
        raise GraphNotFoundError(f"GraphNode #{node_id} does not exist.")
    if node.business_id != business_id:
        raise GraphScopeError(f"GraphNode #{node_id} belongs to business {node.business_id}, not {business_id}.")

    edges_qs = models.GraphEdge.objects.filter(business_id=business_id).select_related("source_node", "target_node")

    if direction == "OUTBOUND":
        edges_qs = edges_qs.filter(source_node_id=node_id)
    elif direction == "INBOUND":
        edges_qs = edges_qs.filter(target_node_id=node_id)
    else:  # BIDIRECTIONAL
        edges_qs = edges_qs.filter(Q(source_node_id=node_id) | Q(target_node_id=node_id))

    # Apply database-level relationship type filter if possible
    if filters and filters.relationship_types:
        edges_qs = edges_qs.filter(relationship_type__in=filters.relationship_types)
    if filters and filters.min_confidence is not None:
        edges_qs = edges_qs.filter(confidence__gte=filters.min_confidence)

    edges_list = list(edges_qs.order_by("relationship_type", "id"))
    results: list[tuple[models.GraphEdge, models.GraphNode]] = []

    for edge in edges_list:
        if not _matches_edge_filter(edge, filters):
            continue

        neighbor = edge.target_node if edge.source_node_id == node_id else edge.source_node
        if neighbor.business_id != business_id:
            continue
        if not _matches_node_filter(neighbor, filters):
            continue

        results.append((edge, neighbor))
        if limit is not None and len(results) >= limit:
            break

    return results


def traverse_graph(
    *,
    business_id: int,
    root_entity_type: str,
    root_entity_id: int,
    direction: str = "OUTBOUND",
    max_depth: int = 2,
    max_nodes: int = 100,
    filters: GraphFilter | None = None,
) -> TraversalResult:
    """Bounded multi-hop graph traversal starting from a canonical entity.

    Guarantees:
    - Cycle safety via visited node tracking.
    - Explicit depth and node count bounds.
    - Multi-tenant business scope verification.
    - Deterministic ordering of visited nodes and edges.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    if max_depth < 0:
        raise GraphValidationError("max_depth must be non-negative")
    if max_nodes <= 0:
        raise GraphValidationError("max_nodes must be positive")

    direction = (direction or "OUTBOUND").upper()
    if direction not in VALID_DIRECTIONS:
        raise GraphValidationError(
            f"Invalid direction {direction!r}; expected one of {sorted(VALID_DIRECTIONS)}"
        )

    root_entity_type = (root_entity_type or "").upper()
    root_node = models.GraphNode.objects.filter(
        business_id=business_id,
        entity_type=root_entity_type,
        entity_id=root_entity_id,
    ).first()

    if root_node is None:
        # Check if node exists under another business to raise proper scope error
        other_node = models.GraphNode.objects.filter(
            entity_type=root_entity_type,
            entity_id=root_entity_id,
        ).first()
        if other_node is not None and other_node.business_id != business_id:
            raise GraphScopeError(
                f"Root entity {root_entity_type} #{root_entity_id} belongs to business {other_node.business_id}, not {business_id}."
            )
        raise GraphNotFoundError(
            f"Root entity {root_entity_type} #{root_entity_id} not found in business {business_id} graph."
        )

    nodes: list[models.GraphNode] = [root_node]
    edges: list[models.GraphEdge] = []
    visited_node_ids: set[int] = {root_node.pk}
    seen_edge_ids: set[int] = set()

    queue: deque[tuple[models.GraphNode, int]] = deque([(root_node, 0)])
    max_depth_reached = 0
    truncated = False

    while queue:
        curr_node, curr_depth = queue.popleft()
        if curr_depth > max_depth_reached:
            max_depth_reached = curr_depth

        if curr_depth >= max_depth:
            continue

        neighbors = get_neighbors(
            business_id=business_id,
            node_id=curr_node.pk,
            direction=direction,
            filters=filters,
        )

        for edge, neighbor in neighbors:
            if neighbor.pk not in visited_node_ids:
                if len(nodes) >= max_nodes:
                    truncated = True
                    break
                visited_node_ids.add(neighbor.pk)
                nodes.append(neighbor)
                queue.append((neighbor, curr_depth + 1))

            if edge.pk not in seen_edge_ids:
                seen_edge_ids.add(edge.pk)
                edges.append(edge)

        if truncated:
            break

    # Drop any edge whose endpoints were not both visited (e.g. truncated traversal)
    edges = [
        edge for edge in edges
        if edge.source_node_id in visited_node_ids and edge.target_node_id in visited_node_ids
    ]

    return TraversalResult(
        business_id=business_id,
        root_node_id=root_node.pk,
        depth_reached=max_depth_reached,
        truncated=truncated,
        nodes=nodes,
        edges=edges,
    )


def find_paths(
    *,
    business_id: int,
    start_entity_type: str,
    start_entity_id: int,
    end_entity_type: str,
    end_entity_id: int,
    direction: str = "OUTBOUND",
    max_depth: int = 5,
    filters: GraphFilter | None = None,
    limit: int = 10,
) -> list[GraphPath]:
    """Search for valid paths between two canonical entities.

    Guarantees:
    - Bounded search depth.
    - Cycle safety within paths.
    - Missing relationships remain missing (returns empty list if unconnected).
    - Multi-tenant business validation.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    if max_depth <= 0:
        raise GraphValidationError("max_depth must be positive")
    if limit <= 0:
        raise GraphValidationError("limit must be positive")

    start_entity_type = (start_entity_type or "").upper()
    end_entity_type = (end_entity_type or "").upper()

    start_node = models.GraphNode.objects.filter(
        business_id=business_id,
        entity_type=start_entity_type,
        entity_id=start_entity_id,
    ).first()
    if start_node is None:
        raise GraphNotFoundError(f"Start node {start_entity_type} #{start_entity_id} does not exist.")

    end_node = models.GraphNode.objects.filter(
        business_id=business_id,
        entity_type=end_entity_type,
        entity_id=end_entity_id,
    ).first()
    if end_node is None:
        raise GraphNotFoundError(f"End node {end_entity_type} #{end_entity_id} does not exist.")

    if start_node.pk == end_node.pk:
        # Same node path of length 0
        return [GraphPath(steps=(PathStep(node=start_node, edge_to_next=None),))]

    found_paths: list[GraphPath] = []
    # Queue stores: list of (node, edge_to_next) tuples
    queue: deque[list[tuple[models.GraphNode, models.GraphEdge | None]]] = deque([
        [(start_node, None)]
    ])

    while queue and len(found_paths) < limit:
        current_path = queue.popleft()
        last_node, _ = current_path[-1]
        current_depth = len(current_path) - 1

        if current_depth >= max_depth:
            continue

        path_node_ids = {node.pk for node, _ in current_path}

        neighbors = get_neighbors(
            business_id=business_id,
            node_id=last_node.pk,
            direction=direction,
            filters=filters,
        )

        for edge, neighbor in neighbors:
            if neighbor.pk in path_node_ids:
                # Cycle prevention: do not loop back into current path
                continue

            # Update previous step's edge_to_next
            extended_path = list(current_path)
            prev_node, _ = extended_path[-1]
            extended_path[-1] = (prev_node, edge)
            extended_path.append((neighbor, None))

            if neighbor.pk == end_node.pk:
                steps = tuple(
                    PathStep(node=n, edge_to_next=e) for n, e in extended_path
                )
                found_paths.append(GraphPath(steps=steps))
                if len(found_paths) >= limit:
                    break
            else:
                queue.append(extended_path)

    return found_paths


def query_subgraph(
    *,
    business_id: int,
    entity_type: str | None = None,
    entity_id: int | None = None,
    relationship_type: str | None = None,
    filters: GraphFilter | None = None,
    limit: int = 100,
) -> TraversalResult:
    """General structured graph query endpoint for entities and relationships."""
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")

    if entity_type and entity_id:
        return traverse_graph(
            business_id=business_id,
            root_entity_type=entity_type,
            root_entity_id=entity_id,
            direction="BIDIRECTIONAL",
            max_depth=2,
            max_nodes=limit,
            filters=filters,
        )

    # Relationship-centric query
    edges_qs = models.GraphEdge.objects.filter(business_id=business_id).select_related("source_node", "target_node")
    if relationship_type:
        edges_qs = edges_qs.filter(relationship_type=relationship_type)

    if filters and filters.min_confidence is not None:
        edges_qs = edges_qs.filter(confidence__gte=filters.min_confidence)

    edges_list = list(edges_qs.order_by("relationship_type", "id")[:limit])

    nodes_dict: dict[int, models.GraphNode] = {}
    matched_edges: list[models.GraphEdge] = []

    for edge in edges_list:
        if not _matches_edge_filter(edge, filters):
            continue
        if not _matches_node_filter(edge.source_node, filters):
            continue
        if not _matches_node_filter(edge.target_node, filters):
            continue

        nodes_dict[edge.source_node_id] = edge.source_node
        nodes_dict[edge.target_node_id] = edge.target_node
        matched_edges.append(edge)

    return TraversalResult(
        business_id=business_id,
        root_node_id=0,
        depth_reached=1 if matched_edges else 0,
        truncated=len(matched_edges) >= limit,
        nodes=list(nodes_dict.values()),
        edges=matched_edges,
    )


__all__ = [
    "GraphFilter",
    "GraphPath",
    "PathStep",
    "TraversalResult",
    "VALID_DIRECTIONS",
    "find_paths",
    "get_neighbors",
    "query_subgraph",
    "traverse_graph",
]
