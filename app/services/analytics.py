"""
Authoritative Business Intelligence and Analytics Calculations.
Deterministic calculations establish facts and metrics.
AI advisory never silently alters authoritative metrics.
"""

import datetime
from decimal import Decimal

import pytz
from django.db.models import Q, Sum


def completed_refund_total(business, orders) -> Decimal:
    """Sum canonical COMPLETED refunds for this tenant's order cohort, including partial refunds."""
    from app.models import Refund

    orders = orders.filter(business=business)
    total = Refund.objects.filter(payment__business=business, status="COMPLETED").filter(
        Q(order__in=orders) | Q(order__isnull=True, payment__order__in=orders)
    ).aggregate(total=Sum("amount"))["total"]
    return total or Decimal("0.00")


def calculate_net_revenue(
    gross_total: Decimal, refunds: Decimal = Decimal("0.00")
) -> Decimal:
    """
    COR-004: Calculates authoritative Net Revenue.
    Rule: Net Revenue = Gross Total - Refunds.
    """
    gross = Decimal(str(gross_total))
    ref = Decimal(str(refunds)) if refunds is not None else Decimal("0.00")
    return max(Decimal("0.00"), gross - ref)


def cap_campaign_attributions(attributions: dict, order_total: Decimal) -> dict:
    """
    COR-005: Caps multi-platform campaign attribution so total attributed revenue does not exceed order total.
    Pro-rates attribution proportionally if the sum exceeds order_total.
    """
    order_total = Decimal(str(order_total))
    if not attributions or order_total <= Decimal("0.00"):
        return {k: Decimal("0.00") for k in attributions}

    total_raw = sum(Decimal(str(v)) for v in attributions.values())
    if total_raw <= order_total:
        return {k: Decimal(str(v)) for k, v in attributions.items()}

    scale = order_total / total_raw
    capped = {}
    running_sum = Decimal("0.00")
    keys = list(attributions.keys())
    for i, k in enumerate(keys):
        if i == len(keys) - 1:
            val = max(Decimal("0.00"), order_total - running_sum)
        else:
            val = (Decimal(str(attributions[k])) * scale).quantize(Decimal("0.01"))
            running_sum += val
        capped[k] = val
    return capped


def to_business_date(
    dt: datetime.datetime, business_timezone: str = "Asia/Dhaka"
) -> datetime.date:
    """
    COR-006: Converts UTC or naive datetime to the authoritative business operational date
    according to the tenant's configured timezone (default 'Asia/Dhaka').
    Prevents boundary shifts where Bangladesh night orders are aggregated into the previous UTC date.
    """
    if dt is None:
        return None
    tz = pytz.timezone(business_timezone)
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(tz).date()
