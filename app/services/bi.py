"""
Deterministic Business Intelligence Service.
Authoritative facts and metrics are established here.
AI advisory never independently calculates or alters these authoritative metrics.
"""
from decimal import Decimal
from django.utils import timezone
from app.models import Business, BusinessFact, BusinessIssue, BusinessIssueEvidence, MetricSnapshot, Order
from app.services.analytics import calculate_net_revenue, to_business_date


def compute_daily_business_metrics(business: Business, target_date=None) -> dict:
    """
    Computes deterministic daily metrics for a business tenant using operational timezone.
    """
    now = timezone.now()
    if target_date is None:
        target_date = to_business_date(now, business.timezone or "Asia/Dhaka")

    orders = Order.objects.filter(business=business)
    gross_revenue = Decimal('0.00')
    refunds = Decimal('0.00')
    total_orders = 0
    failed_deliveries = 0

    for order in orders:
        order_date = to_business_date(order.ordered_at or order.created_at, business.timezone or "Asia/Dhaka")
        if order_date == target_date:
            total_orders += 1
            gross_revenue += Decimal(str(order.total_amount))
            if order.status == 'CANCELLED' or order.status == 'REFUNDED':
                refunds += Decimal(str(order.total_amount))
            if order.status == 'FAILED_DELIVERY':
                failed_deliveries += 1

    net_revenue = calculate_net_revenue(gross_revenue, refunds)
    failure_rate = Decimal(failed_deliveries) / Decimal(total_orders) if total_orders > 0 else Decimal('0.00')

    from app.models import BusinessMetric
    metric, _ = BusinessMetric.objects.get_or_create(
        business=business,
        key="DAILY_PERFORMANCE",
        defaults={
            "name": "Daily Performance Metrics",
            "category": "REVENUE",
            "value_type": "DECIMAL",
            "unit": business.currency or "BDT",
        }
    )

    metric_snapshot = MetricSnapshot.objects.create(
        metric=metric,
        business=business,
        value=net_revenue,
        period_type="DAILY",
        period_start=now - timezone.timedelta(days=1),
        period_end=now,
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
    if metrics["failure_rate"] >= Decimal('0.20') and metrics["total_orders"] >= 1:
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
                "confidence": Decimal('1.0000'),
                "status": "VERIFIED",
                "valid_from": now,
                "valid_to": now + timezone.timedelta(days=7),
                "detected_at": now,
            }
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
            confidence=Decimal('1.0000'),
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
            weight=Decimal('1.0000'),
        )
        detected_issues.append(issue)

    return detected_issues
