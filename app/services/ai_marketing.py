"""
Marketing Assistant Service (Feature 3).
Translates campaign performance into accessible narrative explanations,
performs cross-domain analysis (order returns, delivery failures),
and suggests grounded marketing optimizations.
"""

from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from app.models import Business, Campaign, Order
from app.services.ai_context import assemble_memory_context
from app.services.analytics import calculate_net_revenue, cap_campaign_attributions


def explain_campaign_performance(
    business: Business,
    campaign: Campaign,
) -> dict[str, Any]:
    """
    Feature 3: Marketing Assistant - Campaign Explanation & Cross-Domain Analysis.
    Combines ad spend, clicks, conversions with downstream order returns and delivery outcomes.
    """
    from app.services.authorization import ensure_same_business
    ensure_same_business(business, campaign)
    spend_val = getattr(campaign, "spend", None)
    if spend_val is None and hasattr(campaign, "campaignmetric_set") and campaign.campaignmetric_set.exists():
        spend_val = sum((Decimal(str(m.spend or 0)) for m in campaign.campaignmetric_set.all()), Decimal("0.00"))
    spend = Decimal(str(spend_val or "0.00"))

    budget = Decimal(str(getattr(campaign, "budget", None) or "0.00"))
    utm_name = getattr(campaign, "utm_campaign", None) or (campaign.source_metadata or {}).get("utm_campaign") or campaign.name

    # Scoped downstream orders attributed to campaign (AI-006)
    from app.models import CampaignConversion, OrderItem

    conv_orders = list(
        CampaignConversion.objects.filter(campaign=campaign, order__isnull=False).values_list("order_id", flat=True)
    )
    utm_orders = list(
        Order.objects.filter(business=business)
        .only("id", "source_metadata")
        .filter(source_metadata__isnull=False)
    )
    utm_order_ids = [o.id for o in utm_orders if (o.source_metadata or {}).get("utm_campaign") == utm_name]
    matched_order_ids = set(conv_orders) | set(utm_order_ids)
    if matched_order_ids:
        orders = Order.objects.filter(business=business, id__in=matched_order_ids)
    else:
        # No deterministic attribution means no campaign revenue claim.
        orders = Order.objects.none()

    total_revenue = sum(
        (Decimal(str(o.total_amount)) for o in orders), Decimal("0.00")
    )
    refunds = sum(
        (
            Decimal(str(o.total_amount))
            for o in orders
            if o.status in ["REFUNDED", "CANCELLED"]
        ),
        Decimal("0.00"),
    )
    net_rev = calculate_net_revenue(total_revenue, refunds)

    # Attribution capping (COR-005)
    raw_attr = {utm_name: total_revenue}
    capped_attr = cap_campaign_attributions(raw_attr, total_revenue)
    attributed_revenue = capped_attr.get(utm_name, Decimal("0.00"))

    roas = (attributed_revenue / spend).quantize(Decimal("0.01")) if spend > 0 else Decimal("0.00")

    # Customer Quality Context (AI-007): repeat buyers and fulfillment outcomes
    campaign_customer_ids = set(orders.values_list("customer_id", flat=True))
    repeat_customers = 0
    if campaign_customer_ids:
        for cid in campaign_customer_ids:
            if cid and Order.objects.filter(business=business, customer_id=cid).count() > 1:
                repeat_customers += 1
    repeat_rate_pct = round((repeat_customers / len(campaign_customer_ids) * 100), 1) if campaign_customer_ids else 0.0

    # Top Products Context
    top_items = (
        OrderItem.objects.filter(order__in=orders)
        .values("product_name")
        .annotate(units=Sum("quantity"))
        .order_by("-units")[:3]
    )
    top_products = [f"{item['product_name']} ({item['units']} units)" for item in top_items]

    explanation = (
        f"Campaign '{campaign.name}' ({campaign.platform}) has spent {business.currency or 'BDT'} {spend} "
        f"against a budget of {budget}. It realized an estimated ROAS of {roas}x on "
        f"{business.currency or 'BDT'} {attributed_revenue} of attributable gross revenue from {orders.count()} orders. "
        f"Net realized revenue after deducting refunds is {business.currency or 'BDT'} {net_rev}. "
        f"Acquired customer repeat purchase rate is {repeat_rate_pct}%."
    )

    # Optimization suggestions based on ROAS, customer quality, and goal alignment
    suggestions = []
    goals = [item for item in assemble_memory_context(business) if item["document_type"] == "BUSINESS_GOAL"]
    if roas >= Decimal("2.50"):
        suggestions.append(
            "Strong performance: Exceeds target ROAS. Consider scaling budget by 15-20% while monitoring courier fulfillment rates."
        )
    elif roas < Decimal("1.00"):
        suggestions.append(
            "Underperforming: Ad spend exceeds realized revenue. Review target audience, pause low-performing creatives, and audit fulfillment returns."
        )
    else:
        suggestions.append(
            "Moderate performance: Maintain current budget allocation and focus on improving product page conversion."
        )

    if repeat_rate_pct < 10.0 and orders.count() > 5:
        suggestions.append(
            "Low repeat buyer retention: Introduce post-purchase automated re-engagement to improve acquired customer lifetime value."
        )
    if goals:
        suggestions.append(f"Align this review with active goals: {', '.join(goal['title'] for goal in goals[:3])}.")

    # Record AI Audit Event (Feature 17)
    from app.services.ai import record_ai_audit_event
    record_ai_audit_event(
        business=business,
        conversation_type="MARKETING_ASSISTANT",
        action_name="explain_campaign_performance",
        prompt=f"Analyze campaign performance for {campaign.name}",
        output_content=explanation,
        context_reference={"spend": str(spend), "roas": str(roas), "attributed_orders": orders.count()},
    )

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "platform": campaign.platform,
        "spend": str(spend),
        "budget": str(budget),
        "attributed_orders_count": orders.count(),
        "attributed_revenue": str(attributed_revenue),
        "net_revenue": str(net_rev),
        "calculated_roas": str(roas),
        "target_roas": "2.50",
        "customer_repeat_rate_pct": str(repeat_rate_pct),
        "top_products": top_products,
        "performance_summary": explanation,
        "optimization_suggestions": suggestions,
        "active_goals": goals,
        "evaluated_at": timezone.now().isoformat(),
    }
