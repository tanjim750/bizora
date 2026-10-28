"""REST API views and authorization seam for Business Graph.

Serves Business Graph specification and ticket T-019.

Key properties:
1. Deny-by-default authorization seam:
   - Resolves authorized business strictly from authenticated/contextual request.business.
   - Rejects unauthenticated or out-of-scope calls with HTTP 403 PermissionDenied.
   - Refuses to trust caller-supplied business_id in query parameters or payload.
2. Standard DRF endpoints:
   - Traversal and path search
   - Journey projections (Customer, Order, Product, Campaign)
   - Snapshot creation and retrieval
   - Graph rebuild execution
"""

from typing import Any
import datetime

from rest_framework import exceptions, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from app import models
from app.business_graph.journeys import (
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
from app.business_graph.snapshots import (
    create_graph_snapshot,
    get_graph_snapshot,
)
from app.business_graph.sync import (
    rebuild_business_graph,
)
from app.business_graph.traversal import (
    GraphFilter,
    find_paths,
    traverse_graph,
)


def resolve_authorized_business(request: Any) -> models.Business:
    """Resolve the authoritative business scope from the request.

    Deny-by-default: requires request.business or request.auth_business.
    If the caller explicitly passes a business_id parameter or payload field,
    it must strictly match the authorized business; otherwise access is denied.
    """
    biz = getattr(request, "business", None) or getattr(request, "auth_business", None)
    if biz is None:
        raise exceptions.PermissionDenied("Access denied: No authorized business scope.")

    if not isinstance(biz, models.Business):
        if isinstance(biz, int):
            biz_obj = models.Business.objects.filter(pk=biz).first()
            if not biz_obj:
                raise exceptions.PermissionDenied("Access denied: Authorized business not found.")
            biz = biz_obj
        else:
            raise exceptions.PermissionDenied("Access denied: Invalid business context.")

    # Validate against caller-supplied parameters to prevent spoofing
    caller_biz_id = None
    if hasattr(request, "query_params"):
        caller_biz_id = request.query_params.get("business_id")
    if caller_biz_id is None and hasattr(request, "data") and isinstance(request.data, dict):
        caller_biz_id = request.data.get("business_id")

    if caller_biz_id is not None:
        try:
            if int(caller_biz_id) != biz.pk:
                raise exceptions.PermissionDenied(
                    "Access denied: Caller-supplied business_id does not match authorized business."
                )
        except (ValueError, TypeError):
            raise exceptions.PermissionDenied("Access denied: Malformed business_id parameter.")

    return biz


class HasAuthorizedBusiness(permissions.BasePermission):
    """Deny-by-default permission checking for an authorized business."""

    def has_permission(self, request, view):
        try:
            resolve_authorized_business(request)
            return True
        except exceptions.PermissionDenied:
            return False


class BaseGraphAPIView(APIView):
    """Base class providing deny-by-default business scoping and error translation."""

    permission_classes = [HasAuthorizedBusiness]

    def get_authorized_business(self) -> models.Business:
        return resolve_authorized_business(self.request)

    def handle_exception(self, exc):
        if isinstance(exc, GraphScopeError):
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        if isinstance(exc, (GraphValidationError, GraphCrossBusinessError)):
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return super().handle_exception(exc)


class GraphTraversalAPIView(BaseGraphAPIView):
    """Multi-hop bounded graph traversal endpoint."""

    def get(self, request):
        biz = self.get_authorized_business()
        root_type = request.query_params.get("root_entity_type")
        root_id = request.query_params.get("root_entity_id")
        if not root_type or not root_id:
            return Response(
                {"error": "root_entity_type and root_entity_id query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            root_id_int = int(root_id)
        except ValueError:
            return Response({"error": "root_entity_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        direction = request.query_params.get("direction", "OUTBOUND")
        max_depth = int(request.query_params.get("max_depth", 2))
        max_nodes = int(request.query_params.get("max_nodes", 100))

        result = traverse_graph(
            business_id=biz.pk,
            root_entity_type=root_type,
            root_entity_id=root_id_int,
            direction=direction,
            max_depth=max_depth,
            max_nodes=max_nodes,
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
    """Path search endpoint between two entities."""

    def get(self, request):
        biz = self.get_authorized_business()
        start_type = request.query_params.get("start_entity_type")
        start_id = request.query_params.get("start_entity_id")
        end_type = request.query_params.get("end_entity_type")
        end_id = request.query_params.get("end_entity_id")

        if not all([start_type, start_id, end_type, end_id]):
            return Response(
                {"error": "start_entity_type, start_entity_id, end_entity_type, and end_entity_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            s_id = int(start_id)
            e_id = int(end_id)
        except ValueError:
            return Response({"error": "start_entity_id and end_entity_id must be integers."}, status=status.HTTP_400_BAD_REQUEST)

        max_depth = int(request.query_params.get("max_depth", 5))
        direction = request.query_params.get("direction", "OUTBOUND")

        paths = find_paths(
            business_id=biz.pk,
            start_entity_type=start_type,
            start_entity_id=s_id,
            end_entity_type=end_type,
            end_entity_id=e_id,
            direction=direction,
            max_depth=max_depth,
        )

        serialized_paths = []
        for p in paths:
            serialized_paths.append({
                "length": p.length,
                "nodes": [{"id": n.pk, "entity_type": n.entity_type, "entity_id": n.entity_id} for n in p.nodes],
                "edges": [{"id": e.pk, "relationship_type": e.relationship_type} for e in p.edges],
            })

        return Response({
            "business_id": biz.pk,
            "paths_found": len(paths),
            "paths": serialized_paths,
        })


class CustomerJourneyAPIView(BaseGraphAPIView):
    """Customer multi-channel journey endpoint."""

    def get(self, request, customer_id: int):
        biz = self.get_authorized_business()
        journey = build_customer_journey(
            business_id=biz.pk,
            customer_id=customer_id,
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

    def get(self, request, order_id: int):
        biz = self.get_authorized_business()
        oj = build_order_journey(
            business_id=biz.pk,
            order_id=order_id,
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

    def get(self, request, product_id: int):
        biz = self.get_authorized_business()
        pj = build_product_journey(
            business_id=biz.pk,
            product_id=product_id,
        )

        return Response({
            "business_id": biz.pk,
            "product_id": pj.product_id,
            "summary": pj.summary,
            "timeline_length": len(pj.timeline),
        })


class CampaignJourneyAPIView(BaseGraphAPIView):
    """Campaign journey endpoint."""

    def get(self, request, campaign_id: int):
        biz = self.get_authorized_business()
        cj = build_campaign_journey(
            business_id=biz.pk,
            campaign_id=campaign_id,
        )

        return Response({
            "business_id": biz.pk,
            "campaign_id": cj.campaign_id,
            "summary": cj.summary,
            "timeline_length": len(cj.timeline),
        })


class GraphSnapshotListCreateAPIView(BaseGraphAPIView):
    """List or create graph snapshots."""

    def get(self, request):
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

    def post(self, request):
        biz = self.get_authorized_business()
        snapshot_type = request.data.get("snapshot_type", "BUSINESS")
        name = request.data.get("name")
        root_type = request.data.get("root_entity_type")
        root_id = request.data.get("root_entity_id")

        snapshot = create_graph_snapshot(
            business_id=biz.pk,
            snapshot_type=snapshot_type,
            name=name,
            root_entity_type=root_type,
            root_entity_id=int(root_id) if root_id is not None else None,
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

    def get(self, request, snapshot_id: int):
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

    def post(self, request):
        biz = self.get_authorized_business()
        clean = bool(request.data.get("clean", False))
        summary = rebuild_business_graph(
            business_id=biz.pk,
            clean=clean,
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
    "GraphRebuildAPIView",
    "GraphSnapshotDetailAPIView",
    "GraphSnapshotListCreateAPIView",
    "GraphTraversalAPIView",
    "HasAuthorizedBusiness",
    "OrderJourneyAPIView",
    "ProductJourneyAPIView",
    "resolve_authorized_business",
]
