"""REST API views and authorization seam for Business Graph.

Serves Business Graph specification and ticket T-019.

Key properties:
1. Deny-by-default authorization seam (see app/business_scope.py):
   - The business comes only from the URL (businesses/<business_id>/graph/...).
   - The caller must be an active member of that business; reads need any member role,
     snapshot creation and rebuilds need OWNER or MANAGER.
   - Rejects unauthenticated or non-member calls with HTTP 403 and never echoes ids.
   - Ignores any business_id sent in the query string or payload.
2. Standard DRF endpoints:
   - Traversal and path search
   - Journey projections (Customer, Order, Product, Campaign)
   - Snapshot creation and retrieval
   - Graph rebuild execution
"""

from decimal import Decimal, InvalidOperation
from typing import Any
import datetime
import logging

from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response

from app import models
from app.business_scope import NOT_FOUND_DETAIL, BusinessScopedAPIView, error_response
from app.business_graph.journeys import (
    build_campaign_journey,
    build_customer_journey,
    build_order_journey,
    build_product_journey,
)
from app.business_graph.projection import (
    GraphCrossBusinessError,
    GraphNotFoundError,
    GraphScopeError,
    GraphValidationError,
)
from app.business_graph.snapshots import (
    create_graph_snapshot,
    explain_path,
    get_graph_snapshot,
)
from app.business_graph.sync import (
    rebuild_business_graph,
)
from app.business_graph.traversal import (
    GraphFilter,
    find_paths,
    query_subgraph,
    traverse_graph,
)


logger = logging.getLogger(__name__)

# BG-05: the documents ask for caps but give no numbers. These are named, reviewable values
# (to be confirmed by the owner); a request above a cap is rejected with 400, never silently clamped.
MAX_TRAVERSAL_DEPTH = 5
MAX_TRAVERSAL_NODES = 1000
MAX_QUERY_LIMIT = 1000


def _int_param(source: Any, name: str, default: int | None, *, minimum: int, maximum: int | None = None) -> int | None:
    """Read an optional integer parameter; a malformed or out-of-range value is a 400 (BG-06, BG-05)."""
    raw = source.get(name) if source is not None else None
    if raw is None or raw == "":
        return default
    if isinstance(raw, bool) or (isinstance(raw, float) and not raw.is_integer()):
        raise GraphValidationError(f"{name} must be an integer.")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise GraphValidationError(f"{name} must be an integer.")
    if value < minimum:
        raise GraphValidationError(f"{name} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise GraphValidationError(f"{name} must be at most {maximum}.")
    return value


def _json_object(request) -> Any:
    """The request body as a mapping; anything else (array, string) is a 400 instead of a crash."""
    if not hasattr(request.data, "get"):
        raise GraphValidationError("The request body must be a JSON object.")
    return request.data


def _text_field(body: Any, name: str) -> str | None:
    value = body.get(name)
    if value is not None and not isinstance(value, str):
        raise GraphValidationError(f"{name} must be a string.")
    return value


def _datetime_param(get_fn, name: str) -> datetime.datetime | None:
    """Read an optional timezone-aware ISO 8601 datetime; malformed or naive values are a 400 (BG-06)."""
    raw = get_fn(name)
    if not raw:
        return None
    if isinstance(raw, datetime.datetime):
        value = raw
    elif isinstance(raw, str):
        try:
            value = parse_datetime(raw)
        except ValueError:
            value = None
        if value is None:
            raise GraphValidationError(f"{name} must be an ISO 8601 datetime.")
    else:
        raise GraphValidationError(f"{name} must be an ISO 8601 datetime.")
    if value.tzinfo is None:
        raise GraphValidationError(f"{name} must include a UTC offset.")
    return value


def _parse_graph_filter(params: Any) -> GraphFilter | None:
    """Parse GraphFilter criteria from query_params or dict payload."""
    if not params:
        return None

    get_fn = getattr(params, "get", None)
    if not callable(get_fn):
        return None

    min_confidence = None
    min_conf_raw = get_fn("min_confidence")
    if min_conf_raw is not None and min_conf_raw != "":
        try:
            min_confidence = Decimal(str(min_conf_raw))
        except (InvalidOperation, TypeError, ValueError):
            pass

    status_val = get_fn("status") or None
    channel_val = get_fn("channel") or None
    provider_val = get_fn("provider") or None

    entity_types = None
    et_raw = get_fn("entity_types")
    if et_raw:
        if isinstance(et_raw, (list, set, tuple)):
            entity_types = frozenset(str(x).strip().upper() for x in et_raw if str(x).strip())
        elif isinstance(et_raw, str):
            entity_types = frozenset(x.strip().upper() for x in et_raw.split(",") if x.strip())

    relationship_types = None
    rt_raw = get_fn("relationship_types")
    if rt_raw:
        if isinstance(rt_raw, (list, set, tuple)):
            relationship_types = frozenset(str(x).strip().upper() for x in rt_raw if str(x).strip())
        elif isinstance(rt_raw, str):
            relationship_types = frozenset(x.strip().upper() for x in rt_raw.split(",") if x.strip())

    time_from = _datetime_param(get_fn, "time_from")
    time_to = _datetime_param(get_fn, "time_to")
    valid_at = _datetime_param(get_fn, "valid_at")

    dimensions = None
    dim_raw = get_fn("dimensions")
    if isinstance(dim_raw, dict):
        dimensions = dim_raw

    if all(
        v is None
        for v in (
            min_confidence,
            status_val,
            channel_val,
            provider_val,
            entity_types,
            relationship_types,
            time_from,
            time_to,
            valid_at,
            dimensions,
        )
    ):
        return None

    return GraphFilter(
        entity_types=entity_types,
        relationship_types=relationship_types,
        min_confidence=min_confidence,
        valid_at=valid_at,
        time_from=time_from,
        time_to=time_to,
        status=status_val,
        channel=channel_val,
        provider=provider_val,
        dimensions=dimensions,
    )


class BaseGraphAPIView(BusinessScopedAPIView):
    """Base class providing URL-scoped membership checks and error translation."""

    def handle_exception(self, exc):
        if isinstance(exc, (GraphNotFoundError, GraphScopeError, GraphCrossBusinessError)):
            # BG-07: missing and foreign entities answer identically, and the service message
            # (which names the owning business) is logged, never returned to the caller.
            log = logger.info if isinstance(exc, GraphNotFoundError) else logger.warning
            log("Graph request not served: %s", exc)
            return error_response("NOT_FOUND", NOT_FOUND_DETAIL, status.HTTP_404_NOT_FOUND)
        if isinstance(exc, GraphValidationError):
            return error_response("INVALID_DATA", str(exc), status.HTTP_400_BAD_REQUEST)
        return super().handle_exception(exc)


class GraphTraversalAPIView(BaseGraphAPIView):
    """Multi-hop bounded graph traversal endpoint."""

    def get(self, request, business_id: int):
        biz = self.get_authorized_business()
        root_type = request.query_params.get("root_entity_type")
        root_id = request.query_params.get("root_entity_id")
        if not root_type or not root_id:
            return error_response(
                "INVALID_DATA",
                "root_entity_type and root_entity_id query parameters are required.",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            root_id_int = int(root_id)
        except ValueError:
            return error_response("INVALID_DATA", "root_entity_id must be an integer.", status.HTTP_400_BAD_REQUEST)

        direction = request.query_params.get("direction", "OUTBOUND")
        max_depth = _int_param(request.query_params, "max_depth", 2, minimum=0, maximum=MAX_TRAVERSAL_DEPTH)
        max_nodes = _int_param(request.query_params, "max_nodes", 100, minimum=1, maximum=MAX_TRAVERSAL_NODES)
        filters = _parse_graph_filter(request.query_params)

        result = traverse_graph(
            business_id=biz.pk,
            root_entity_type=root_type,
            root_entity_id=root_id_int,
            direction=direction,
            max_depth=max_depth,
            max_nodes=max_nodes,
            filters=filters,
        )

        return Response({
            "business_id": biz.pk,
            "root_node_id": result.root_node_id,
            "depth_reached": result.depth_reached,
            "truncated": result.truncated,
            "node_count": result.node_count,
            "edge_count": result.edge_count,
            "nodes": [
                {
                    "id": n.pk,
                    "entity_type": n.entity_type,
                    "entity_id": n.entity_id,
                    "label": n.label,
                    "properties": n.properties,
                }
                for n in result.nodes
            ],
            "edges": [
                {
                    "id": e.pk,
                    "source_node_id": e.source_node_id,
                    "target_node_id": e.target_node_id,
                    "relationship_type": e.relationship_type,
                    "confidence": str(e.confidence),
                }
                for e in result.edges
            ],
        })


class GraphPathSearchAPIView(BaseGraphAPIView):
    """Path search endpoint between two entities with optional explainability."""

    def get(self, request, business_id: int):
        biz = self.get_authorized_business()
        start_type = request.query_params.get("start_entity_type")
        start_id = request.query_params.get("start_entity_id")
        end_type = request.query_params.get("end_entity_type")
        end_id = request.query_params.get("end_entity_id")

        if not all([start_type, start_id, end_type, end_id]):
            return error_response(
                "INVALID_DATA",
                "start_entity_type, start_entity_id, end_entity_type, and end_entity_id are required.",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            s_id = int(start_id)
            e_id = int(end_id)
        except ValueError:
            return error_response(
                "INVALID_DATA", "start_entity_id and end_entity_id must be integers.", status.HTTP_400_BAD_REQUEST
            )

        max_depth = _int_param(request.query_params, "max_depth", 5, minimum=1, maximum=MAX_TRAVERSAL_DEPTH)
        direction = request.query_params.get("direction", "OUTBOUND")
        explain = str(request.query_params.get("explain", "false")).lower() in ("true", "1")
        filters = _parse_graph_filter(request.query_params)

        paths = find_paths(
            business_id=biz.pk,
            start_entity_type=start_type,
            start_entity_id=s_id,
            end_entity_type=end_type,
            end_entity_id=e_id,
            direction=direction,
            max_depth=max_depth,
            filters=filters,
        )

        serialized_paths = []
        for p in paths:
            item = {
                "length": p.length,
                "nodes": [{"id": n.pk, "entity_type": n.entity_type, "entity_id": n.entity_id} for n in p.nodes],
                "edges": [{"id": e.pk, "relationship_type": e.relationship_type} for e in p.edges],
            }
            if explain:
                item["explanation"] = explain_path(business_id=biz.pk, path=p)
            serialized_paths.append(item)

        return Response({
            "business_id": biz.pk,
            "paths_found": len(paths),
            "paths": serialized_paths,
        })


class GraphQueryAPIView(BaseGraphAPIView):
    """General structured graph query endpoint for entities and relationships."""

    def get(self, request, business_id: int):
        biz = self.get_authorized_business()
        entity_type = request.query_params.get("entity_type")
        entity_id = _int_param(request.query_params, "entity_id", None, minimum=1)
        relationship_type = request.query_params.get("relationship_type")
        limit = _int_param(request.query_params, "limit", 100, minimum=1, maximum=MAX_QUERY_LIMIT)
        filters = _parse_graph_filter(request.query_params)

        result = query_subgraph(
            business_id=biz.pk,
            entity_type=entity_type,
            entity_id=entity_id,
            relationship_type=relationship_type,
            filters=filters,
            limit=limit,
        )

        return Response({
            "business_id": biz.pk,
            "root_node_id": result.root_node_id,
            "depth_reached": result.depth_reached,
            "truncated": result.truncated,
            "node_count": result.node_count,
            "edge_count": result.edge_count,
            "nodes": [
                {
                    "id": n.pk,
                    "entity_type": n.entity_type,
                    "entity_id": n.entity_id,
                    "label": n.label,
                    "properties": n.properties,
                }
                for n in result.nodes
            ],
            "edges": [
                {
                    "id": e.pk,
                    "source_node_id": e.source_node_id,
                    "target_node_id": e.target_node_id,
                    "relationship_type": e.relationship_type,
                    "confidence": str(e.confidence),
                }
                for e in result.edges
            ],
        })


class CustomerJourneyAPIView(BaseGraphAPIView):
    """Customer multi-channel journey endpoint."""

    def get(self, request, business_id: int, customer_id: int):
        biz = self.get_authorized_business()
        filters = _parse_graph_filter(request.query_params)
        journey = build_customer_journey(
            business_id=biz.pk,
            customer_id=customer_id,
            filters=filters,
        )

        return Response({
            "business_id": biz.pk,
            "customer_id": journey.customer_id,
            "canonical_identity_id": journey.canonical_identity_id,
            "node_count": len(journey.nodes),
            "edge_count": len(journey.edges),
            "summary": journey.summary,
            "timeline": [
                {
                    "entity_type": ev.entity_type,
                    "entity_id": ev.entity_id,
                    "label": ev.label,
                    "stage": ev.stage,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                    "properties": ev.properties,
                }
                for ev in journey.timeline
            ],
        })


class OrderJourneyAPIView(BaseGraphAPIView):
    """Order lifecycle journey endpoint."""

    def get(self, request, business_id: int, order_id: int):
        biz = self.get_authorized_business()
        filters = _parse_graph_filter(request.query_params)
        oj = build_order_journey(
            business_id=biz.pk,
            order_id=order_id,
            filters=filters,
        )

        return Response({
            "business_id": biz.pk,
            "order_id": oj.order_id,
            "status": oj.status,
            "total_amount": oj.total_amount,
            "customer_node_id": oj.customer_node.pk if oj.customer_node else None,
            "product_count": len(oj.product_nodes),
            "payment_count": len(oj.payment_nodes),
            "shipment_count": len(oj.shipment_nodes),
            "timeline": [
                {
                    "entity_type": ev.entity_type,
                    "entity_id": ev.entity_id,
                    "label": ev.label,
                    "stage": ev.stage,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                }
                for ev in oj.timeline
            ],
        })


class ProductJourneyAPIView(BaseGraphAPIView):
    """Product journey endpoint."""

    def get(self, request, business_id: int, product_id: int):
        biz = self.get_authorized_business()
        filters = _parse_graph_filter(request.query_params)
        pj = build_product_journey(
            business_id=biz.pk,
            product_id=product_id,
            filters=filters,
        )

        return Response({
            "business_id": biz.pk,
            "product_id": pj.product_id,
            "summary": pj.summary,
            "timeline_length": len(pj.timeline),
        })


class CampaignJourneyAPIView(BaseGraphAPIView):
    """Campaign journey endpoint."""

    def get(self, request, business_id: int, campaign_id: int):
        biz = self.get_authorized_business()
        filters = _parse_graph_filter(request.query_params)
        cj = build_campaign_journey(
            business_id=biz.pk,
            campaign_id=campaign_id,
            filters=filters,
        )

        return Response({
            "business_id": biz.pk,
            "campaign_id": cj.campaign_id,
            "summary": cj.summary,
            "timeline_length": len(cj.timeline),
        })


class GraphSnapshotListCreateAPIView(BaseGraphAPIView):
    """List or create graph snapshots."""

    def get(self, request, business_id: int):
        biz = self.get_authorized_business()
        snapshots = models.GraphSnapshot.objects.filter(business_id=biz.pk).order_by("-generated_at")
        return Response([
            {
                "id": s.pk,
                "name": s.name,
                "snapshot_type": s.snapshot_type,
                "node_count": s.node_count,
                "edge_count": s.edge_count,
                "generated_at": s.generated_at.isoformat(),
            }
            for s in snapshots
        ])

    def post(self, request, business_id: int):
        biz = self.get_authorized_business()
        body = _json_object(request)
        snapshot_type = _text_field(body, "snapshot_type") or "BUSINESS"
        name = _text_field(body, "name")
        root_type = _text_field(body, "root_entity_type")
        filters = _parse_graph_filter(body.get("filters") or body)

        snapshot = create_graph_snapshot(
            business_id=biz.pk,
            snapshot_type=snapshot_type,
            name=name,
            root_entity_type=root_type,
            root_entity_id=_int_param(body, "root_entity_id", None, minimum=1),
            filters=filters,
        )

        return Response(
            {
                "id": snapshot.pk,
                "name": snapshot.name,
                "snapshot_type": snapshot.snapshot_type,
                "node_count": snapshot.node_count,
                "edge_count": snapshot.edge_count,
                "generated_at": snapshot.generated_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class GraphSnapshotDetailAPIView(BaseGraphAPIView):
    """Retrieve an individual graph snapshot with serialized data."""

    def get(self, request, business_id: int, snapshot_id: int):
        biz = self.get_authorized_business()
        snapshot = get_graph_snapshot(
            business_id=biz.pk,
            snapshot_id=snapshot_id,
        )

        return Response({
            "id": snapshot.pk,
            "business_id": snapshot.business_id,
            "name": snapshot.name,
            "snapshot_type": snapshot.snapshot_type,
            "node_count": snapshot.node_count,
            "edge_count": snapshot.edge_count,
            "filters": snapshot.filters,
            "snapshot_data": snapshot.snapshot_data,
            "generated_at": snapshot.generated_at.isoformat(),
        })


class GraphRebuildAPIView(BaseGraphAPIView):
    """Execute a full graph rebuild for the authorized business."""

    def post(self, request, business_id: int):
        biz = self.get_authorized_business()
        clean_raw = _json_object(request).get("clean", False)
        if not isinstance(clean_raw, bool):
            raise GraphValidationError("clean must be a boolean.")
        summary = rebuild_business_graph(
            business_id=biz.pk,
            clean=clean_raw,
        )

        return Response({
            "business_id": summary.business_id,
            "nodes_created": summary.nodes_created,
            "nodes_updated": summary.nodes_updated,
            "nodes_pruned": summary.nodes_pruned,
            "edges_created": summary.edges_created,
            "edges_updated": summary.edges_updated,
            "edges_pruned": summary.edges_pruned,
            "total_nodes": summary.total_nodes,
            "total_edges": summary.total_edges,
        })


__all__ = [
    "BaseGraphAPIView",
    "CampaignJourneyAPIView",
    "CustomerJourneyAPIView",
    "GraphPathSearchAPIView",
    "GraphQueryAPIView",
    "GraphRebuildAPIView",
    "GraphSnapshotDetailAPIView",
    "GraphSnapshotListCreateAPIView",
    "GraphTraversalAPIView",
    "OrderJourneyAPIView",
    "ProductJourneyAPIView",
]
