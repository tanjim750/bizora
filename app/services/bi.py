"""
Deterministic Business Intelligence Service.
Authoritative facts and metrics are established here.
AI advisory never independently calculates or alters these authoritative metrics.
"""

import datetime
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from app.models import (
    Business,
    BusinessFact,
    BusinessIssue,
    BusinessIssueEvidence,
    MetricSnapshot,
    Order,
)
from app.services.analytics import calculate_net_revenue, to_business_date


def compute_daily_business_metrics(business: Business, target_date=None) -> dict:
    """
    Computes deterministic daily metrics for a business tenant using operational timezone.
    """
    now = timezone.now()
    if target_date is None:
        target_date = to_business_date(now, business.timezone or "Asia/Dhaka")

    # DB-side date window for the target business date (UTC boundaries that contain the local date)
    biz_tz_name = business.timezone or "Asia/Dhaka"
    import pytz
    biz_tz = pytz.timezone(biz_tz_name)
    # Derive UTC start/end for the target business date
    naive_start = datetime.datetime.combine(target_date, datetime.time.min)
    naive_end = datetime.datetime.combine(target_date, datetime.time.max)
    period_start_utc = biz_tz.localize(naive_start).astimezone(pytz.UTC)
    period_end_utc = biz_tz.localize(naive_end).astimezone(pytz.UTC)

    day_orders = Order.objects.filter(
        business=business,
    ).filter(
        Q(ordered_at__gte=period_start_utc, ordered_at__lte=period_end_utc)
        | Q(ordered_at__isnull=True, created_at__gte=period_start_utc, created_at__lte=period_end_utc)
    )

    total_orders = day_orders.count()
    agg = day_orders.aggregate(gross=Sum("total_amount"))
    gross_revenue = Decimal(str(agg["gross"] or "0.00"))

    refund_agg = day_orders.filter(
        status__in=["CANCELLED", "REFUNDED"]
    ).aggregate(ref=Sum("total_amount"))
    refunds = Decimal(str(refund_agg["ref"] or "0.00"))

    failed_deliveries = day_orders.filter(status="FAILED_DELIVERY").count()

    net_revenue = calculate_net_revenue(gross_revenue, refunds)
    failure_rate = (
        Decimal(failed_deliveries) / Decimal(total_orders)
        if total_orders > 0
        else Decimal("0.00")
    )

    from app.models import BusinessMetric

    metric, _ = BusinessMetric.objects.get_or_create(
        business=business,
        key="DAILY_PERFORMANCE",
        defaults={
            "name": "Daily Performance Metrics",
            "category": "REVENUE",
            "value_type": "DECIMAL",
            "unit": business.currency or "BDT",
        },
    )

    metric_snapshot = MetricSnapshot.objects.create(
        metric=metric,
        business=business,
        value=net_revenue,
        period_type="DAILY",
        period_start=period_start_utc,
        period_end=period_end_utc,
        calculation_rule="NET_REVENUE_CALCULATION",
        metadata={
            "gross_revenue": str(gross_revenue),
            "refunds": str(refunds),
            "total_orders": total_orders,
            "failed_deliveries": failed_deliveries,
            "failure_rate": str(round(failure_rate, 4)),
            "metric_date": str(target_date),
        },
        calculated_at=now,
    )

    return {
        "metric_date": target_date,
        "gross_revenue": gross_revenue,
        "refunds": refunds,
        "net_revenue": net_revenue,
        "total_orders": total_orders,
        "failed_deliveries": failed_deliveries,
        "failure_rate": failure_rate,
        "snapshot": metric_snapshot,
    }


def detect_business_issues_from_metrics(business: Business, target_date=None) -> list:
    """
    Evaluates verified facts from metric thresholds and establishes authoritative BusinessIssues.
    """
    metrics = compute_daily_business_metrics(business, target_date)
    now = timezone.now()
    detected_issues = []

    # Deterministic threshold rule: Failure rate > 20%
    if metrics["failure_rate"] >= Decimal("0.20") and metrics["total_orders"] >= 1:
        # Establish deterministic BusinessFact
        fact, _ = BusinessFact.objects.get_or_create(
            business=business,
            fact_type="HIGH_DELIVERY_FAILURE_RATE",
            subject_entity_type="business",
            subject_entity_id=business.id,
            defaults={
                "statement": f"Delivery failure rate reached {metrics['failure_rate']:.1%} on {metrics['metric_date']}",
                "value": metrics["failure_rate"],
                "value_unit": "PERCENT",
                "confidence": Decimal("1.0000"),
                "status": "VERIFIED",
                "valid_from": now,
                "valid_to": now + datetime.timedelta(days=7),
                "detected_at": now,
            },
        )

        # Establish or update authoritative BusinessIssue (deduplicated per COR-007)
        issue = BusinessIssue.objects.create(
            business=business,
            issue_type="EXCESSIVE_DELIVERY_FAILURES",
            subject_entity_type="business",
            subject_entity_id=business.id,
            title="High Delivery Failure Rate Detected",
            description=fact.statement,
            severity="HIGH",
            confidence=Decimal("1.0000"),
            status="OPEN",
            detected_at=now,
        )

        # Ground issue with evidence
        BusinessIssueEvidence.objects.create(
            business_issue=issue,
            business_fact=fact,
            metric_snapshot=metrics["snapshot"],
            evidence_type="METRIC_THRESHOLD_BREACH",
            description=fact.statement,
            weight=Decimal("1.0000"),
        )
        detected_issues.append(issue)

    return detected_issues
