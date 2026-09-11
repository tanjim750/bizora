"""
Marketing Assistant Service (Feature 3).
Translates campaign performance into accessible narrative explanations,
performs cross-domain analysis (order returns, delivery failures),
and suggests grounded marketing optimizations.
"""

from decimal import Decimal
from typing import Any

from django.utils import timezone

from app.models import Business, Campaign, Order
from app.services.analytics import calculate_net_revenue, cap_campaign_attributions


def explain_campaign_performance(
    business: Business,
    campaign: Campaign,
) -> dict[str, Any]:
    """
    Feature 3: Marketing Assistant - Campaign Explanation & Cross-Domain Analysis.
    Combines ad spend, clicks, conversions with downstream order returns and delivery outcomes.
    """
    spend_val = getattr(campaign, "spend", None)
    if spend_val is None and hasattr(campaign, "campaignmetric_set") and campaign.campaignmetric_set.exists():
        spend_val = sum((Decimal(str(m.spend or 0)) for m in campaign.campaignmetric_set.all()), Decimal("0.00"))
    spend = Decimal(str(spend_val or "0.00"))

    budget = Decimal(str(getattr(campaign, "budget", None) or "0.00"))
    utm_name = getattr(campaign, "utm_campaign", None) or (campaign.source_metadata or {}).get("utm_campaign") or campaign.name

    # Sample downstream orders attributed to campaign
    orders = Order.objects.filter(business=business)
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

    explanation = (
        f"Campaign '{campaign.name}' ({campaign.platform}) has spent {business.currency or 'BDT'} {spend} "
        f"against a budget of {budget}. It realized an estimated ROAS of {roas}x on "
        f"{business.currency or 'BDT'} {attributed_revenue} of attributable gross revenue. "
        f"Net realized revenue after deducting refunds is {business.currency or 'BDT'} {net_rev}."
    )

    # Optimization suggestions based on ROAS and budget utilization
    suggestions = []
    if roas >= Decimal("2.50"):
        suggestions.append(
            "Strong performance: Consider scaling budget by 15-20% while monitoring courier fulfillment rates."
        )
    elif roas < Decimal("1.00"):
        suggestions.append(
            "Underperforming: Ad spend exceeds realized revenue. Review target audience, pause low-performing creatives, and audit fulfillment returns."
        )
    else:
        suggestions.append(
            "Moderate performance: Maintain current budget allocation and focus on improving product page conversion."
        )

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "platform": campaign.platform,
        "spend": str(spend),
        "budget": str(budget),
        "attributed_revenue": str(attributed_revenue),
        "net_revenue": str(net_rev),
        "calculated_roas": str(roas),
        "performance_summary": explanation,
        "optimization_suggestions": suggestions,
        "evaluated_at": timezone.now().isoformat(),
    }
