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

from django.db.models import Q, Sum
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
    as_of: datetime.datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Feature 5: Fact-Aware Context Retrieval.
    Retrieves active, verified, non-expired Business Facts for the business tenant.
    Filters out expired and invalidated facts via BusinessFactManager (COR-009).
    Eagerly loads supporting evidence and allows time-aware as_of filtering.
    """
    now = as_of or timezone.now()
    qs = BusinessFact.objects.active_for_context(business).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_to__isnull=True) | Q(valid_to__gte=now),
    )
    if as_of:
        qs = qs.filter(Q(valid_from__isnull=True) | Q(valid_from__lte=as_of)).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=as_of))

    if entity_type and entity_id:
        qs = qs.filter(subject_entity_type=entity_type, subject_entity_id=entity_id)

    facts = []
    for fact in qs.prefetch_related("businessfactevidence_set").order_by("-confidence", "-valid_from")[:limit]:
        evidence_list = [
            {
                "evidence_type": ev.evidence_type,
                "description": ev.description,
                "entity_type": ev.entity_type,
                "entity_id": ev.entity_id,
            }
            for ev in fact.businessfactevidence_set.all()[:5]
        ]
        facts.append(
            {
                "id": fact.id,
                "fact_type": fact.fact_type,
                "statement": fact.statement,
                "confidence": str(fact.confidence),
                "valid_from": fact.valid_from.isoformat() if fact.valid_from else None,
                "metadata": fact.metadata or {},
                "supporting_evidence": evidence_list,
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
    Bounds edge retrieval to the local BFS neighborhood instead of loading the entire table.
    """
    now = timezone.now()
    from app.models import GraphEdge, GraphNode

    start_node_key = f"{start_entity_type.lower()}_{start_entity_id}"
    
    # Identify starting node if it exists
    start_node = GraphNode.objects.filter(
        business=business,
        entity_type__iexact=start_entity_type,
        entity_id=start_entity_id,
    ).first()

    # Bounded neighborhood retrieval using BFS expansion
    current_node_ids = {start_node.id} if start_node else set()
    visited_node_ids = set(current_node_ids)
    collected_edges = []

    if current_node_ids:
        for _ in range(max_depth):
            if not current_node_ids:
                break
            layer_edges = list(
            GraphEdge.objects.filter(business=business)
            .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=now))
            .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=now))
                .filter(Q(source_node_id__in=current_node_ids) | Q(target_node_id__in=current_node_ids))
                .select_related("source_node", "target_node")[:100]
            )
            next_node_ids = set()
            for edge in layer_edges:
                collected_edges.append(edge)
                if edge.source_node_id not in visited_node_ids:
                    next_node_ids.add(edge.source_node_id)
                    visited_node_ids.add(edge.source_node_id)
                if edge.target_node_id not in visited_node_ids:
                    next_node_ids.add(edge.target_node_id)
                    visited_node_ids.add(edge.target_node_id)
            current_node_ids = next_node_ids
    else:
        # Fallback if start_node not registered in GraphNode: fetch direct edges by label/string
        collected_edges = []

    graph = create_business_graph()
    edge_descriptions = []

    for edge in collected_edges:
        if edge.source_node.business_id != business.id or edge.target_node.business_id != business.id:
            continue
        src = f"{edge.source_node.entity_type.lower()}_{edge.source_node.entity_id}"
        dst = f"{edge.target_node.entity_type.lower()}_{edge.target_node.entity_id}"
        graph.add_edge(src, dst, relationship=edge.relationship_type)
        graph.add_edge(dst, src, relationship=f"INCOMING_{edge.relationship_type}")
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
    Retrieves active policies, FAQs, business guidelines from KnowledgeDocument,
    as well as historical decisions and approved recommendations.
    """
    from app.models import AiAction, AiRecommendation

    if intent:
        docs = KnowledgeDocument.get_active_policies_for_intent(business, intent)
    else:
        docs = KnowledgeDocument.objects.filter(
            business=business, status__in=["READY", "PUBLISHED"]
        ).exclude(knowledge_source__status="ARCHIVED")
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
                "source_reference": doc.knowledge_source.source_reference,
            }
        )
        # Prefer bounded, searchable chunks when they are available. This is
        # deterministic fallback retrieval until a vector index is configured.
        terms = [term for term in (intent or "").replace("_", " ").lower().split() if len(term) > 2]
        chunks = doc.knowledgechunk_set.all()
        if terms:
            chunks = [chunk for chunk in chunks if any(term in chunk.content.lower() for term in terms)]
        for chunk in list(chunks)[:3]:
            memory_items.append({
                "id": chunk.id, "title": doc.title, "document_type": doc.document_type,
                "content": chunk.content, "version": doc.version,
                "source_reference": doc.knowledge_source.source_reference,
            })

    # Historical approved recommendations & decisions
    approved_recs = AiRecommendation.objects.filter(
        business=business, status__in=["APPROVED", "ACCEPTED", "EXECUTED"]
    ).order_by("-generated_at")[:3]
    for rec in approved_recs:
        memory_items.append(
            {
                "id": rec.id,
                "title": f"Approved Recommendation: {rec.title}",
                "document_type": "APPROVED_RECOMMENDATION",
                "content": f"{rec.description} (Action: {rec.suggested_action_type})",
                "version": 1,
            }
        )

    past_actions = AiAction.objects.filter(
        business=business, status="EXECUTED"
    ).order_by("-executed_at")[:3]
    for act in past_actions:
        memory_items.append(
            {
                "id": act.id,
                "title": f"Executed Decision: {act.action_type}",
                "document_type": "EXECUTED_ACTION",
                "content": f"Action on {act.target_entity_type} {act.target_entity_id}: {act.action_payload}",
                "version": 1,
            }
        )

    from app.models import BusinessGoal
    for goal in BusinessGoal.objects.filter(business=business, status="ACTIVE")[:5]:
        memory_items.append({
            "id": goal.id, "title": f"Business Goal: {goal.name}",
            "document_type": "BUSINESS_GOAL", "content": f"{goal.metric_key} target {goal.target_value}",
            "version": 1,
        })

    return memory_items


def assemble_customer_context(
    business: Business,
    customer: Customer,
) -> dict[str, Any]:
    """
    Feature 8: Customer-Aware AI.
    Assembles customer profile, order history, lifetime value, and return patterns.
    """
    from app.services.authorization import ensure_same_business
    ensure_same_business(business, customer)
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

    # Support history and delivery reliability (AI-015)
    from app.models import Call, Conversation, Payment, Shipment
    support_history = [
        {"id": c.id, "subject": c.subject, "status": c.status, "channel": c.channel}
        for c in Conversation.objects.filter(business=business, customer=customer).order_by("-started_at")[:3]
    ]
    cancellation_rate_pct = round((cancelled_orders / total_orders * 100), 1) if total_orders > 0 else 0.0

    return {
        "customer_id": customer.id,
        "name": name,
        "email": email_contact.value if email_contact else getattr(customer, "email", None),
        "phone": phone_contact.value if phone_contact else getattr(customer, "phone", None),
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "cancellation_rate_pct": cancellation_rate_pct,
        "total_spend": str(total_spent.quantize(Decimal("0.01"))),
        "recent_orders": recent_orders,
        "recent_support_history": support_history,
        "recent_calls": list(Call.objects.filter(business=business, customer=customer).order_by("-started_at").values("id", "direction", "status")[:3]),
        "payments": list(Payment.objects.filter(business=business, customer=customer).order_by("-created_at").values("id", "amount", "status")[:5]),
        "shipments": list(Shipment.objects.filter(business=business, customer=customer).order_by("-created_at").values("id", "provider", "status")[:5]),
    }


def assemble_product_context(
    business: Business,
    product: Product,
) -> dict[str, Any]:
    """
    Feature 9: Product-Aware AI.
    Assembles canonical product attributes, variants, sales volume, and return/cancellation findings.
    """
    from app.services.authorization import ensure_same_business
    ensure_same_business(business, product)
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
    from app.models import BusinessIssue, CampaignConversion, OrderItem

    # DB-side aggregation — avoids loading all OrderItems into Python memory
    qty_agg = OrderItem.objects.filter(
        product=product, order__business=business
    ).aggregate(total_qty=Sum("quantity"))
    units_sold = qty_agg["total_qty"] or 0

    # Downstream returns & cancellation findings (AI-016)
    ret_agg = OrderItem.objects.filter(
        product=product,
        order__business=business,
        order__status__in=["CANCELLED", "REFUNDED", "FAILED_DELIVERY"],
    ).aggregate(ret_qty=Sum("quantity"))
    units_returned = ret_agg["ret_qty"] or 0
    return_rate_pct = round((units_returned / units_sold * 100), 1) if units_sold > 0 else 0.0

    # Product knowledge docs
    docs = KnowledgeDocument.objects.filter(
        business=business,
        title__icontains=product.name,
        status__in=["READY", "PUBLISHED"],
    ).exclude(knowledge_source__status="ARCHIVED")[:2]
    product_guides = [{"id": d.id, "title": d.title} for d in docs]
    product_issues = list(BusinessIssue.objects.filter(
        business=business, subject_entity_type="product", subject_entity_id=product.id
    ).values("id", "issue_type", "title", "severity")[:5])

    return {
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "category": product.category,
        "base_price": str(product.price) if product.price is not None else "0.00",
        "variants": variants,
        "units_sold": units_sold,
        "units_returned": units_returned,
        "return_rate_pct": return_rate_pct,
        "product_guides": product_guides,
        "product_issues": product_issues,
        "campaign_conversions": list(CampaignConversion.objects.filter(
            order__orderitem__product=product, campaign__business=business
        ).values("campaign_id", "conversion_type", "conversion_value")[:5]),
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
    from app.services.authorization import ensure_same_business
    ensure_same_business(business, order)
    if order.customer_id and order.customer.business_id != business.id:
        raise ValueError("Order customer belongs to another business.")
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

    # Associated conversations and calls (AI-016)
    from app.models import Call, Conversation, OrderStatusHistory, Refund
    order_convs = list(
        Conversation.objects.filter(
            business=business,
            customer_id=order.customer_id,
            subject__icontains=order.order_number or "",
        ).values("id", "subject", "status")[:3]
    ) if order.order_number else []

    attribution = {
        "utm_campaign": (order.source_metadata or {}).get("utm_campaign"),
        "channel": (order.source_metadata or {}).get("channel"),
    }

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
        "associated_conversations": order_convs,
        "calls": list(Call.objects.filter(business=business, order=order).values("id", "direction", "status")[:3]),
        "refunds": list(Refund.objects.filter(order=order).values("id", "amount", "status", "reason")[:5]),
        "status_history": list(OrderStatusHistory.objects.filter(order=order).order_by("changed_at").values("from_status", "to_status", "changed_at")[:10]),
        "attribution": attribution,
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
        if customer and order.customer_id != customer.id:
            raise ValueError("Order and customer context do not refer to the same customer.")
        context["order_context"] = assemble_order_context(business, order)
    if product:
        context["product_context"] = assemble_product_context(business, product)

    return context
