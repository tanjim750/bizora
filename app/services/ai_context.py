"""
Unified AI Context Engine for Business Brain.
Provides contextual retrieval across:
- Fact-aware retrieval (Feature 5)
- Graph-aware retrieval (Feature 6)
- Memory and policy retrieval (Feature 7)
- Customer-aware context (Feature 8)
- Product-aware context (Feature 9)
- Order-aware context (Feature 10)

Maintains strict multi-tenant isolation and data freshness.
"""

import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from app.models import (
    Business,
    BusinessFact,
    BusinessIssue,
    Customer,
    KnowledgeDocument,
    Order,
    Product,
)
from app.services.graph import create_business_graph, safe_traverse


def assemble_fact_context(
    business: Business,
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Feature 5: Fact-Aware Context Retrieval.
    Retrieves active, verified, non-expired Business Facts for the business tenant.
    Filters out expired and invalidated facts via BusinessFactManager (COR-009).
    """
    qs = BusinessFact.objects.filter(business=business, status="VERIFIED")
    if entity_type and entity_id:
        # Filter metadata or statement if entity reference is provided
        qs = qs.filter(metadata__contains={entity_type: entity_id})

    facts = []
    for fact in qs.order_by("-confidence", "-valid_from")[:limit]:
        facts.append(
            {
                "id": fact.id,
                "fact_type": fact.fact_type,
                "statement": fact.statement,
                "confidence": str(fact.confidence),
                "valid_from": fact.valid_from.isoformat() if fact.valid_from else None,
                "metadata": fact.metadata or {},
            }
        )
    return facts


def assemble_graph_context(
    business: Business,
    start_entity_type: str,
    start_entity_id: int,
    max_depth: int = 3,
) -> dict[str, Any]:
    """
    Feature 6: Graph-Aware Context Retrieval.
    Builds a directed multigraph from business graph edges and traverses relevant connected nodes
    using cycle-safe, depth-bounded traversal (safe_traverse).
    """
    from app.models import GraphEdge, GraphNode

    start_node_key = f"{start_entity_type.lower()}_{start_entity_id}"
    edges = GraphEdge.objects.filter(business=business).select_related(
        "source_node", "target_node"
    )

    graph = create_business_graph()
    edge_descriptions = []

    for edge in edges:
        src = f"{edge.source_node.entity_type.lower()}_{edge.source_node.entity_id}"
        dst = f"{edge.target_node.entity_type.lower()}_{edge.target_node.entity_id}"
        graph.add_edge(src, dst, relationship=edge.relationship_type)
        if src == start_node_key or dst == start_node_key:
            edge_descriptions.append(
                {
                    "source": src,
                    "target": dst,
                    "relationship": edge.relationship_type,
                }
            )

    connected_nodes = []
    if start_node_key in graph:
        connected_nodes = safe_traverse(
            graph, start_node=start_node_key, max_depth=max_depth
        )

    return {
        "start_node": start_node_key,
        "traversed_nodes": connected_nodes,
        "direct_edges": edge_descriptions[:15],
    }


def assemble_memory_context(
    business: Business,
    intent: str | None = None,
    document_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Feature 7: Memory Retrieval.
    Retrieves active policies, FAQs, and business guidelines from KnowledgeDocument.
    """
    if intent:
        docs = KnowledgeDocument.get_active_policies_for_intent(business, intent)
    else:
        docs = KnowledgeDocument.objects.filter(
            business=business, status__in=["READY", "PUBLISHED"]
        )
        if document_type:
            docs = docs.filter(document_type=document_type)

    memory_items = []
    for doc in docs[:5]:
        memory_items.append(
            {
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "content": doc.content,
                "version": doc.version,
            }
        )
    return memory_items


def assemble_customer_context(
    business: Business,
    customer: Customer,
) -> dict[str, Any]:
    """
    Feature 8: Customer-Aware AI.
    Assembles customer profile, order history, lifetime value, and return patterns.
    """
    orders = Order.objects.filter(business=business, customer=customer).order_by(
        "-created_at"
    )
    total_orders = orders.count()
    completed_orders = orders.filter(status__in=["COMPLETED", "DELIVERED"]).count()
    cancelled_orders = orders.filter(
        status__in=["CANCELLED", "REFUNDED", "FAILED_DELIVERY"]
    ).count()

    # DB-side aggregation — avoids loading all orders into Python memory
    spend_agg = orders.aggregate(total=Sum("total_amount"))
    total_spent = Decimal(str(spend_agg["total"] or "0.00"))

    recent_orders = [
        {
            "order_id": o.id,
            "order_number": o.order_number,
            "status": o.status,
            "total_amount": str(o.total_amount),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders[:5]
    ]

    email_contact = customer.customercontact_set.filter(contact_type="EMAIL").first()
    phone_contact = customer.customercontact_set.filter(contact_type="PHONE").first()
    name = (
        customer.display_name
        or f"{customer.first_name or ''} {customer.last_name or ''}".strip()
        or getattr(customer, "name", None)
        or "Customer"
    )

    return {
        "customer_id": customer.id,
        "name": name,
        "email": email_contact.value if email_contact else getattr(customer, "email", None),
        "phone": phone_contact.value if phone_contact else getattr(customer, "phone", None),
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_spend": str(total_spent),
        "recent_orders": recent_orders,
    }


def assemble_product_context(
    business: Business,
    product: Product,
) -> dict[str, Any]:
    """
    Feature 9: Product-Aware AI.
    Assembles canonical product attributes, variants, sales volume, and return/cancellation findings.
    """
    variants = [
        {
            "id": v.id,
            "sku": v.sku,
            "name": v.name,
            "price": str(v.price) if v.price is not None else None,
            "status": v.status,
        }
        for v in product.productvariant_set.all()[:5]
    ]
    from app.models import OrderItem

    # DB-side aggregation — avoids loading all OrderItems into Python memory
    qty_agg = OrderItem.objects.filter(
        product=product, order__business=business
    ).aggregate(total_qty=Sum("quantity"))
    units_sold = qty_agg["total_qty"] or 0

    return {
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "category": product.category,
        "base_price": str(product.price) if product.price is not None else "0.00",
        "variants": variants,
        "units_sold": units_sold,
        "is_active": product.status == "ACTIVE",
    }


def assemble_order_context(
    business: Business,
    order: Order,
) -> dict[str, Any]:
    """
    Feature 10: Order-Aware AI.
    Assembles order items, payments, shipment status, and tracking context.
    """
    items = [
        {
            "product_name": item.product_name,
            "sku": item.sku,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "subtotal": str(item.total_amount),
        }
        for item in order.orderitem_set.all()
    ]

    payments = [
        {
            "id": p.id,
            "payment_method": p.payment_method,
            "amount": str(p.amount),
            "status": p.status,
            "transaction_id": p.transaction_reference,
        }
        for p in order.payment_set.all()
    ]

    shipments = [
        {
            "id": s.id,
            "courier_name": s.provider,
            "tracking_number": s.tracking_code,
            "status": s.status,
            "dispatched_at": s.picked_up_at.isoformat() if s.picked_up_at else None,
            "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
        }
        for s in order.shipment_set.all()
    ]

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "total_amount": str(order.total_amount),
        "currency": order.currency,
        "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
        "customer_id": order.customer_id,
        "items": items,
        "payments": payments,
        "shipments": shipments,
    }


def assemble_full_ai_context(
    business: Business,
    intent: str | None = None,
    customer: Customer | None = None,
    order: Order | None = None,
    product: Product | None = None,
) -> dict[str, Any]:
    """
    Comprehensive context assembly combining facts, issues, policies, and entity context.
    """
    facts = assemble_fact_context(business, limit=8)
    policies = assemble_memory_context(business, intent=intent)
    issues = list(
        BusinessIssue.objects.filter(business=business, status="OPEN").values(
            "id", "issue_type", "title", "severity"
        )[:5]
    )

    context: dict[str, Any] = {
        "business_id": business.id,
        "business_name": business.name,
        "operational_timezone": business.timezone or "Asia/Dhaka",
        "active_facts": facts,
        "open_issues": issues,
        "authoritative_policies": policies,
    }

    if customer:
        context["customer_context"] = assemble_customer_context(business, customer)
    if order:
        context["order_context"] = assemble_order_context(business, order)
    if product:
        context["product_context"] = assemble_product_context(business, product)

    return context
