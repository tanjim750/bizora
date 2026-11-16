"""Customer and order journey projection services for Business Graph.

Serves Business Graph specification sections 5 (Customer Journey Graph) and 7 (Order Journey Graph)
for ticket T-016.

Key principles enforced:
1. Grounded in verified relationships:
   - Projects journeys strictly from existing GraphNode and GraphEdge records.
   - Never infers, guesses, or fabricates connections if relationships are missing.
2. Multi-tenant isolation:
   - Enforces business_id matching for root entity and all traversed entities.
3. Chronological timeline exploration:
   - Orders all journey touchpoints by activity timestamp.
4. Cross-channel context:
   - Captures marketing, website, commerce, payment, fulfillment, support, and calling events.
"""

from dataclasses import dataclass, field
from typing import Any
import datetime

from app import models
from app.business_graph.projection import (
    GraphScopeError,
    GraphNotFoundError,
    GraphValidationError,
)
from app.business_graph.traversal import (
    GraphFilter,
    traverse_graph,
)


STAGE_MAPPING: dict[str, str] = {
    "CAMPAIGN": "MARKETING",
    "CAMPAIGN_CONVERSION": "MARKETING",
    "WEBSITE_VISITOR": "WEBSITE",
    "WEBSITE_SESSION": "WEBSITE",
    "WEBSITE_EVENT": "WEBSITE",
    "CUSTOMER": "CUSTOMER",
    "ORDER": "COMMERCE",
    "PRODUCT": "COMMERCE",
    "PRODUCT_VARIANT": "COMMERCE",
    "PAYMENT": "PAYMENT",
    "SHIPMENT": "FULFILLMENT",
    "CONVERSATION": "SUPPORT",
    "MESSAGE": "SUPPORT",
    "CALL": "CALLING",
}


@dataclass(frozen=True)
class JourneyTimelineEvent:
    entity_type: str
    entity_id: int
    label: str
    stage: str
    timestamp: datetime.datetime | None
    properties: dict[str, Any]
    connecting_relationships: list[str] = field(default_factory=list)


@dataclass
class CustomerJourney:
    business_id: int
    customer_id: int
    canonical_identity_id: int | None
    customer_node: models.GraphNode
    nodes: list[models.GraphNode]
    edges: list[models.GraphEdge]
    timeline: list[JourneyTimelineEvent]
    summary: dict[str, Any]


@dataclass
class OrderJourney:
    business_id: int
    order_id: int
    order_node: models.GraphNode
    customer_node: models.GraphNode | None
    product_nodes: list[models.GraphNode]
    payment_nodes: list[models.GraphNode]
    shipment_nodes: list[models.GraphNode]
    marketing_nodes: list[models.GraphNode]
    communication_nodes: list[models.GraphNode]
    nodes: list[models.GraphNode]
    edges: list[models.GraphEdge]
    timeline: list[JourneyTimelineEvent]
    status: str
    total_amount: str | None


@dataclass
class ProductJourney:
    business_id: int
    product_id: int
    product_node: models.GraphNode
    order_nodes: list[models.GraphNode]
    customer_nodes: list[models.GraphNode]
    campaign_nodes: list[models.GraphNode]
    website_nodes: list[models.GraphNode]
    shipment_nodes: list[models.GraphNode]
    payment_nodes: list[models.GraphNode]
    communication_nodes: list[models.GraphNode]
    nodes: list[models.GraphNode]
    edges: list[models.GraphEdge]
    timeline: list[JourneyTimelineEvent]
    summary: dict[str, Any]


@dataclass
class CampaignJourney:
    business_id: int
    campaign_id: int
    campaign_node: models.GraphNode
    session_nodes: list[models.GraphNode]
    conversion_nodes: list[models.GraphNode]
    customer_nodes: list[models.GraphNode]
    order_nodes: list[models.GraphNode]
    product_nodes: list[models.GraphNode]
    payment_nodes: list[models.GraphNode]
    shipment_nodes: list[models.GraphNode]
    communication_nodes: list[models.GraphNode]
    nodes: list[models.GraphNode]
    edges: list[models.GraphEdge]
    timeline: list[JourneyTimelineEvent]
    summary: dict[str, Any]


def _extract_node_timestamp(node: models.GraphNode) -> datetime.datetime | None:
    """Determine the authoritative activity timestamp for chronological timeline ordering."""
    return node.first_seen_at or node.created_at


def _build_timeline_events(
    nodes: list[models.GraphNode],
    edges: list[models.GraphEdge],
) -> list[JourneyTimelineEvent]:
    """Construct a chronological sequence of timeline events from graph nodes and edges."""
    # Map node_id -> list of incoming/outgoing relationship types
    rel_map: dict[int, list[str]] = {node.pk: [] for node in nodes}
    for edge in edges:
        if edge.source_node_id in rel_map:
            rel_map[edge.source_node_id].append(f"-> {edge.relationship_type}")
        if edge.target_node_id in rel_map:
            rel_map[edge.target_node_id].append(f"<- {edge.relationship_type}")

    events: list[JourneyTimelineEvent] = []
    for node in nodes:
        ts = _extract_node_timestamp(node)
        stage = STAGE_MAPPING.get(node.entity_type, "OTHER")
        events.append(
            JourneyTimelineEvent(
                entity_type=node.entity_type,
                entity_id=node.entity_id,
                label=node.label or f"{node.entity_type} #{node.entity_id}",
                stage=stage,
                timestamp=ts,
                properties=node.properties or {},
                connecting_relationships=sorted(set(rel_map.get(node.pk, []))),
            )
        )

    # Deterministic chronological sort: None timestamps placed at end
    def sort_key(ev: JourneyTimelineEvent):
        # (has_no_timestamp, timestamp or min, entity_type, entity_id)
        has_no_ts = 1 if ev.timestamp is None else 0
        ts_val = ev.timestamp or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        return (has_no_ts, ts_val, ev.stage, ev.entity_type, ev.entity_id)

    events.sort(key=sort_key)
    return events


def build_customer_journey(
    *,
    business_id: int,
    customer_id: int,
    filters: GraphFilter | None = None,
) -> CustomerJourney:
    """Build the connected multi-channel customer journey from verified graph data.

    Follows:
    Customer -> Orders -> Products / Payments / Shipments
    Customer -> Sessions -> Events / Campaigns
    Customer -> Conversations -> Messages / Calls
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")
    if not isinstance(customer_id, int) or customer_id <= 0 or customer_id > 2**63 - 1:
        raise GraphValidationError("customer_id must be a positive integer at most 9223372036854775807")

    cust = models.Customer.objects.filter(pk=customer_id).first()
    if cust is None:
        raise GraphNotFoundError(f"Customer #{customer_id} does not exist.")
    if cust.business_id != business_id:
        raise GraphScopeError(f"Customer #{customer_id} belongs to business {cust.business_id}, not {business_id}.")

    cust_node = models.GraphNode.objects.filter(
        business_id=business_id,
        entity_type="CUSTOMER",
        entity_id=customer_id,
    ).first()

    if cust_node is None:
        raise GraphValidationError(
            f"Customer #{customer_id} has not been projected into business {business_id} graph."
        )

    # 1. Multi-hop traversal starting from customer node
    # Depth 3 covers: Customer -> Order -> Shipment/Payment/Product
    # and Customer -> Session -> Campaign
    traversal = traverse_graph(
        business_id=business_id,
        root_entity_type="CUSTOMER",
        root_entity_id=customer_id,
        direction="BIDIRECTIONAL",
        max_depth=3,
        max_nodes=500,
        filters=filters,
    )

    nodes = traversal.nodes
    edges = traversal.edges

    # 2. Build chronological timeline
    timeline = _build_timeline_events(nodes, edges)

    # 3. Compile summary statistics
    node_types = [n.entity_type for n in nodes]
    summary = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "order_count": node_types.count("ORDER"),
        "session_count": node_types.count("WEBSITE_SESSION"),
        "conversation_count": node_types.count("CONVERSATION"),
        "call_count": node_types.count("CALL"),
        "shipment_count": node_types.count("SHIPMENT"),
        "payment_count": node_types.count("PAYMENT"),
    }

    return CustomerJourney(
        business_id=business_id,
        customer_id=customer_id,
        canonical_identity_id=cust_node.canonical_identity_id,
        customer_node=cust_node,
        nodes=nodes,
        edges=edges,
        timeline=timeline,
        summary=summary,
    )


def build_order_journey(
    *,
    business_id: int,
    order_id: int,
    filters: GraphFilter | None = None,
) -> OrderJourney:
    """Build the connected lifecycle order journey from verified graph data.

    Connects:
    Order -> Customer
    Order -> Products & Variants
    Order -> Payments
    Order -> Shipments
    Order -> Attributed Campaigns / Sessions
    Order -> Support / Calls
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")
    if not isinstance(order_id, int) or order_id <= 0 or order_id > 2**63 - 1:
        raise GraphValidationError("order_id must be a positive integer at most 9223372036854775807")

    order = models.Order.objects.filter(pk=order_id).first()
    if order is None:
        raise GraphNotFoundError(f"Order #{order_id} does not exist.")
    if order.business_id != business_id:
        raise GraphScopeError(f"Order #{order_id} belongs to business {order.business_id}, not {business_id}.")

    order_node = models.GraphNode.objects.filter(
        business_id=business_id,
        entity_type="ORDER",
        entity_id=order_id,
    ).first()

    if order_node is None:
        raise GraphValidationError(
            f"Order #{order_id} has not been projected into business {business_id} graph."
        )

    # Bounded bidirectional traversal around order node
    traversal = traverse_graph(
        business_id=business_id,
        root_entity_type="ORDER",
        root_entity_id=order_id,
        direction="BIDIRECTIONAL",
        max_depth=2,
        max_nodes=200,
        filters=filters,
    )

    nodes = traversal.nodes
    edges = traversal.edges

    # Categorize nodes
    customer_node: models.GraphNode | None = None
    product_nodes: list[models.GraphNode] = []
    payment_nodes: list[models.GraphNode] = []
    shipment_nodes: list[models.GraphNode] = []
    marketing_nodes: list[models.GraphNode] = []
    comm_nodes: list[models.GraphNode] = []

    for n in nodes:
        if n.entity_type == "CUSTOMER":
            customer_node = n
        elif n.entity_type in ("PRODUCT", "PRODUCT_VARIANT"):
            product_nodes.append(n)
        elif n.entity_type == "PAYMENT":
            payment_nodes.append(n)
        elif n.entity_type == "SHIPMENT":
            shipment_nodes.append(n)
        elif n.entity_type in ("CAMPAIGN", "CAMPAIGN_CONVERSION", "WEBSITE_SESSION"):
            marketing_nodes.append(n)
        elif n.entity_type in ("CONVERSATION", "MESSAGE", "CALL"):
            comm_nodes.append(n)

    timeline = _build_timeline_events(nodes, edges)

    status = (order_node.properties or {}).get("status", order.status or "UNKNOWN")
    total_amount = (order_node.properties or {}).get("total_amount", str(order.total_amount) if order.total_amount is not None else None)

    return OrderJourney(
        business_id=business_id,
        order_id=order_id,
        order_node=order_node,
        customer_node=customer_node,
        product_nodes=product_nodes,
        payment_nodes=payment_nodes,
        shipment_nodes=shipment_nodes,
        marketing_nodes=marketing_nodes,
        communication_nodes=comm_nodes,
        nodes=nodes,
        edges=edges,
        timeline=timeline,
        status=status,
        total_amount=total_amount,
    )


def build_product_journey(
    *,
    business_id: int,
    product_id: int,
    filters: GraphFilter | None = None,
) -> ProductJourney:
    """Build the connected multi-domain product journey from verified graph data.

    Connects:
    Product -> Orders
    Product -> Customers (via orders)
    Product -> Campaigns (via attributed orders and sessions)
    Product -> Website events & sessions
    Product -> Shipments (via orders)
    Product -> Payments (via orders)
    Product -> Support / Calls (via orders)
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")
    if not isinstance(product_id, int) or product_id <= 0 or product_id > 2**63 - 1:
        raise GraphValidationError("product_id must be a positive integer at most 9223372036854775807")

    product = models.Product.objects.filter(pk=product_id).first()
    if product is None:
        raise GraphNotFoundError(f"Product #{product_id} does not exist.")
    if product.business_id != business_id:
        raise GraphScopeError(f"Product #{product_id} belongs to business {product.business_id}, not {business_id}.")

    product_node = models.GraphNode.objects.filter(
        business_id=business_id,
        entity_type="PRODUCT",
        entity_id=product_id,
    ).first()

    if product_node is None:
        raise GraphValidationError(
            f"Product #{product_id} has not been projected into business {business_id} graph."
        )

    traversal = traverse_graph(
        business_id=business_id,
        root_entity_type="PRODUCT",
        root_entity_id=product_id,
        direction="BIDIRECTIONAL",
        max_depth=3,
        max_nodes=500,
        filters=filters,
    )

    nodes = traversal.nodes
    edges = traversal.edges

    order_nodes: list[models.GraphNode] = []
    customer_nodes: list[models.GraphNode] = []
    campaign_nodes: list[models.GraphNode] = []
    website_nodes: list[models.GraphNode] = []
    shipment_nodes: list[models.GraphNode] = []
    payment_nodes: list[models.GraphNode] = []
    comm_nodes: list[models.GraphNode] = []

    for n in nodes:
        if n.entity_type == "ORDER":
            order_nodes.append(n)
        elif n.entity_type == "CUSTOMER":
            customer_nodes.append(n)
        elif n.entity_type == "CAMPAIGN":
            campaign_nodes.append(n)
        elif n.entity_type in ("WEBSITE_VISITOR", "WEBSITE_SESSION", "WEBSITE_EVENT"):
            website_nodes.append(n)
        elif n.entity_type == "SHIPMENT":
            shipment_nodes.append(n)
        elif n.entity_type == "PAYMENT":
            payment_nodes.append(n)
        elif n.entity_type in ("CONVERSATION", "MESSAGE", "CALL"):
            comm_nodes.append(n)

    timeline = _build_timeline_events(nodes, edges)

    summary = {
        "order_count": len(order_nodes),
        "customer_count": len(customer_nodes),
        "campaign_count": len(campaign_nodes),
        "website_count": len(website_nodes),
        "shipment_count": len(shipment_nodes),
        "payment_count": len(payment_nodes),
        "communication_count": len(comm_nodes),
    }

    return ProductJourney(
        business_id=business_id,
        product_id=product_id,
        product_node=product_node,
        order_nodes=order_nodes,
        customer_nodes=customer_nodes,
        campaign_nodes=campaign_nodes,
        website_nodes=website_nodes,
        shipment_nodes=shipment_nodes,
        payment_nodes=payment_nodes,
        communication_nodes=comm_nodes,
        nodes=nodes,
        edges=edges,
        timeline=timeline,
        summary=summary,
    )


def build_campaign_journey(
    *,
    business_id: int,
    campaign_id: int,
    filters: GraphFilter | None = None,
) -> CampaignJourney:
    """Build the connected marketing-to-outcome campaign journey from verified graph data.

    Connects:
    Campaign -> Sessions & Conversions
    Campaign -> Customers
    Campaign -> Orders & Attributed Revenue
    Campaign -> Products
    Campaign -> Payments & Shipments (downstream outcomes)
    Campaign -> Support / Calls
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise GraphValidationError("business_id must be a positive integer")
    if not isinstance(campaign_id, int) or campaign_id <= 0 or campaign_id > 2**63 - 1:
        raise GraphValidationError("campaign_id must be a positive integer at most 9223372036854775807")

    camp = models.Campaign.objects.filter(pk=campaign_id).first()
    if camp is None:
        raise GraphNotFoundError(f"Campaign #{campaign_id} does not exist.")
    if camp.business_id != business_id:
        raise GraphScopeError(f"Campaign #{campaign_id} belongs to business {camp.business_id}, not {business_id}.")

    camp_node = models.GraphNode.objects.filter(
        business_id=business_id,
        entity_type="CAMPAIGN",
        entity_id=campaign_id,
    ).first()

    if camp_node is None:
        raise GraphValidationError(
            f"Campaign #{campaign_id} has not been projected into business {business_id} graph."
        )

    traversal = traverse_graph(
        business_id=business_id,
        root_entity_type="CAMPAIGN",
        root_entity_id=campaign_id,
        direction="BIDIRECTIONAL",
        max_depth=4,
        max_nodes=500,
        filters=filters,
    )

    nodes = traversal.nodes
    edges = traversal.edges

    session_nodes: list[models.GraphNode] = []
    conversion_nodes: list[models.GraphNode] = []
    customer_nodes: list[models.GraphNode] = []
    order_nodes: list[models.GraphNode] = []
    product_nodes: list[models.GraphNode] = []
    payment_nodes: list[models.GraphNode] = []
    shipment_nodes: list[models.GraphNode] = []
    comm_nodes: list[models.GraphNode] = []

    for n in nodes:
        if n.entity_type == "WEBSITE_SESSION":
            session_nodes.append(n)
        elif n.entity_type == "CAMPAIGN_CONVERSION":
            conversion_nodes.append(n)
        elif n.entity_type == "CUSTOMER":
            customer_nodes.append(n)
        elif n.entity_type == "ORDER":
            order_nodes.append(n)
        elif n.entity_type in ("PRODUCT", "PRODUCT_VARIANT"):
            product_nodes.append(n)
        elif n.entity_type == "PAYMENT":
            payment_nodes.append(n)
        elif n.entity_type == "SHIPMENT":
            shipment_nodes.append(n)
        elif n.entity_type in ("CONVERSATION", "MESSAGE", "CALL"):
            comm_nodes.append(n)

    timeline = _build_timeline_events(nodes, edges)

    summary = {
        "session_count": len(session_nodes),
        "conversion_count": len(conversion_nodes),
        "customer_count": len(customer_nodes),
        "order_count": len(order_nodes),
        "product_count": len(product_nodes),
        "payment_count": len(payment_nodes),
        "shipment_count": len(shipment_nodes),
        "communication_count": len(comm_nodes),
    }

    return CampaignJourney(
        business_id=business_id,
        campaign_id=campaign_id,
        campaign_node=camp_node,
        session_nodes=session_nodes,
        conversion_nodes=conversion_nodes,
        customer_nodes=customer_nodes,
        order_nodes=order_nodes,
        product_nodes=product_nodes,
        payment_nodes=payment_nodes,
        shipment_nodes=shipment_nodes,
        communication_nodes=comm_nodes,
        nodes=nodes,
        edges=edges,
        timeline=timeline,
        summary=summary,
    )


__all__ = [
    "CampaignJourney",
    "CustomerJourney",
    "JourneyTimelineEvent",
    "OrderJourney",
    "ProductJourney",
    "STAGE_MAPPING",
    "build_campaign_journey",
    "build_customer_journey",
    "build_order_journey",
    "build_product_journey",
]
