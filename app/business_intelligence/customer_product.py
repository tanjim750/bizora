"""Deterministic BI product, customer and retention analysis.

Serves Business Intelligence specification sections 7, 9 and 10.  This is an
internal, business-scoped service; callers remain responsible for authorization.
It consumes canonical foreign keys and valid T-001 relationships, never resolves
identity, attributes a campaign, invents a threshold, or mutates canonical data.

Periods are half-open ``[period_start, period_end)`` on ``Order.ordered_at``.
Eligible purchases reuse T-003's documented accepted/reversed order states.
Amounts are exact ``Decimal`` values and are never combined across currencies.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
import datetime

from django.db import transaction
from django.utils import timezone

from app import models

from . import metrics, relationships, revenue


class AnalysisValidationError(ValueError):
    """An analysis boundary, period, scope or currency is invalid."""


class AnalysisCurrencyMixError(AnalysisValidationError):
    """An amount scope contains multiple currencies and cannot be combined."""


UNAVAILABLE_MISSING_CONTRACT = "MISSING_DOCUMENTED_CONTRACT"
UNAVAILABLE_NO_OBSERVATIONS = "NO_OBSERVATIONS"
UNAVAILABLE_ZERO_DENOMINATOR = "ZERO_DENOMINATOR"
UNAVAILABLE_MIXED_CURRENCY = "MIXED_CURRENCY"

SEGMENT_NEW = "NEW"
SEGMENT_REPEAT = "REPEAT"

DIMENSION_CHANNEL = "CHANNEL"
DIMENSION_PRODUCT = "PRODUCT"
DIMENSION_CAMPAIGN = "CAMPAIGN"
DIMENSION_CUSTOMER_GROUP = "CUSTOMER_GROUP"
DIMENSION_REGION = "REGION"
RETENTION_DIMENSIONS = frozenset({
    DIMENSION_CHANNEL, DIMENSION_PRODUCT, DIMENSION_CAMPAIGN,
    DIMENSION_CUSTOMER_GROUP, DIMENSION_REGION,
})

_ELIGIBLE_STATUSES = revenue.REVENUE_ELIGIBLE_ORDER_STATUSES
_COUNTED_STATUSES = revenue.COUNTED_ORDER_STATUSES
_CANCELLED_STATUSES = revenue.ORDER_STATUSES_CANCELLED
_FAILED_SHIPMENT_STATUSES = frozenset({"FAILED"})
_RETURN_SHIPMENT_STATUSES = frozenset({"RETURNING", "RETURNED"})
_UNRESOLVED_CONVERSATION_STATUSES = frozenset({"OPEN", "PENDING"})
_DOCUMENTED_CONVERSATION_STATUSES = frozenset({"OPEN", "PENDING", "RESOLVED", "CLOSED"})

_CUSTOMER_METRICS = {
    "new_customers": "bi.metric.customer_new_customers.v1",
    "active_customers": "bi.metric.customer_active_customers.v1",
    "repeat_rate": "bi.metric.customer_repeat_rate.v1",
    "purchase_frequency": "bi.metric.customer_purchase_frequency.v1",
    "average_value": "bi.metric.customer_average_value.v1",
}
_CALCULATION_RULES = {
    key: f"{key}.eligible_orders"
    for key in _CUSTOMER_METRICS.values()
}
_PRECISION = 48

_ORDER_PRODUCT_RULE = relationships.RULES["order_product"]
_ORDER_SHIPMENT_RULE = relationships.RULES["order_shipment"]
_CAMPAIGN_ORDER_RULE = relationships.RULES["campaign_order"]


@dataclass(frozen=True)
class Scope:
    business_id: int
    period_type: str
    period_start: object
    period_end: object


@dataclass(frozen=True)
class UnavailableEvidence:
    available: bool
    reason: str
    required_contract: str
    observed_count: int = 0


@dataclass(frozen=True)
class ProductPerformance:
    product_id: int
    units_sold: int
    order_count: int
    order_frequency: Decimal
    revenue_by_currency: tuple
    first_ordered_at: object
    last_ordered_at: object
    order_ids: tuple


@dataclass(frozen=True)
class ProductContext:
    product_id: int
    campaign_outcomes: tuple
    delivery_outcomes: tuple


@dataclass(frozen=True)
class ProductAnalysis:
    scope: Scope
    products: tuple
    contexts: tuple
    eligible_orders: int
    orders_without_timestamp: int
    orders_without_resolved_product: int
    unclassified_order_statuses: tuple
    trend_inputs: tuple
    conversion_performance: UnavailableEvidence
    trend_classification: UnavailableEvidence
    high_performing_detection: UnavailableEvidence
    underperforming_detection: UnavailableEvidence
    refund_allocation: UnavailableEvidence
    relationship_provenance: tuple


@dataclass(frozen=True)
class CustomerPurchase:
    customer_id: int
    segment: str
    order_count: int
    total_by_currency: tuple
    product_units: tuple
    ordered_purchases: tuple
    consecutive_gap_seconds: tuple
    channels: tuple
    customer_groups: tuple


@dataclass(frozen=True)
class CustomerActivity:
    customer_id: int
    orders: tuple
    payments: tuple
    website_sessions: tuple
    website_events: tuple
    conversations: tuple
    calls: tuple
    shipments: tuple
    journey: tuple
    channel_evidence: tuple


@dataclass(frozen=True)
class CustomerRiskSignals:
    customer_id: int
    cancelled_orders: int
    failed_shipments: int
    returned_shipments: int
    unresolved_conversations: int
    unclassified_shipment_statuses: tuple
    unclassified_conversation_statuses: tuple


@dataclass(frozen=True)
class CustomerAnalysis:
    scope: Scope
    customers: tuple
    activities: tuple
    risk_signals: tuple
    orders_without_customer: int
    missing_activity_timestamps: tuple
    acquisition_channel: UnavailableEvidence


@dataclass(frozen=True)
class RetentionSegment:
    dimension_type: str
    dimension_value: str
    customers: int
    repeat_customers: int
    repeat_rate: object
    order_count: int
    purchase_frequency: object


@dataclass(frozen=True)
class CampaignRetention:
    campaign_id: int
    reported_customers: int
    repeat_customers: int
    repeat_rate: object
    evidence_relationship_ids: tuple
    provenance: str


@dataclass(frozen=True)
class RetentionAnalysis:
    scope: Scope
    customers: int
    new_customers: int
    repeat_customers: int
    repeat_rate: object
    order_count: int
    purchase_frequency: object
    customer_gaps: tuple
    product_repeat: tuple
    campaign_retention: tuple
    segments: tuple
    unavailable_segments: tuple
    trend_inputs: tuple
    trend_classification: UnavailableEvidence
    period_orders_without_customer: int
    orders_without_timestamp: int


@dataclass(frozen=True)
class CustomerMetricRecording:
    analysis: RetentionAnalysis
    average_value_by_currency: tuple
    snapshots: tuple


def _positive_id(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < 2 ** 63:
        raise AnalysisValidationError(f"{label} must be a positive 64-bit integer.")


def _period(business_id, period_type, period_start, period_end):
    _positive_id(business_id, "business_id")
    if not isinstance(period_type, str) or not period_type.strip():
        raise AnalysisValidationError("period_type must be a non-blank string.")
    if period_type.strip() not in metrics.PERIOD_TYPES:
        raise AnalysisValidationError(
            f"period_type must be one of {sorted(metrics.PERIOD_TYPES)}."
        )
    if not isinstance(period_start, datetime.datetime) or not timezone.is_aware(period_start):
        raise AnalysisValidationError("period_start must be a timezone-aware datetime.")
    if not isinstance(period_end, datetime.datetime) or not timezone.is_aware(period_end):
        raise AnalysisValidationError("period_end must be a timezone-aware datetime.")
    if period_start >= period_end:
        raise AnalysisValidationError("period_start must be earlier than period_end.")
    if not models.Business.objects.filter(pk=business_id).exists():
        raise AnalysisValidationError("Business does not exist.")
    return Scope(business_id, period_type.strip(), period_start, period_end)


def _orders(scope, *, all_history=False):
    query = models.Order.objects.filter(
        business_id=scope.business_id,
        status__in=sorted(_ELIGIBLE_STATUSES),
        ordered_at__isnull=False,
    )
    if not all_history:
        query = query.filter(ordered_at__gte=scope.period_start, ordered_at__lt=scope.period_end)
    return list(query.select_related("integration_connection__integration_source").order_by("ordered_at", "pk"))


def _all_period_orders(scope):
    return list(models.Order.objects.filter(
        business_id=scope.business_id,
        ordered_at__gte=scope.period_start,
        ordered_at__lt=scope.period_end,
    ).select_related("integration_connection__integration_source").order_by("ordered_at", "pk"))


def _valid_relationships(business_id, rule, *, source_ids=(), target_ids=()):
    query = models.BusinessRelationship.objects.filter(
        business_id=business_id,
        source_entity_type=rule.source_type,
        relationship_type=rule.relationship_type,
        target_entity_type=rule.target_type,
        rule_key=rule.key,
        relationship_source="DETERMINISTIC",
        valid_to__isnull=True,
    ).order_by("source_entity_id", "target_entity_id", "pk")
    if source_ids:
        query = query.filter(source_entity_id__in=sorted(source_ids))
    if target_ids:
        query = query.filter(target_entity_id__in=sorted(target_ids))
    rows = list(query)
    endpoint_models = {
        "ORDER": (models.Order, "business_id"),
        "PRODUCT": (models.Product, "business_id"),
        "CAMPAIGN": (models.Campaign, "business_id"),
        "SHIPMENT": (models.Shipment, "business_id"),
    }
    source_model, source_business = endpoint_models[rule.source_type]
    target_model, target_business = endpoint_models[rule.target_type]
    valid_source_ids = set(source_model.objects.filter(
        **{source_business: business_id}, pk__in=[row.source_entity_id for row in rows]
    ).values_list("pk", flat=True))
    valid_target_ids = set(target_model.objects.filter(
        **{target_business: business_id}, pk__in=[row.target_entity_id for row in rows]
    ).values_list("pk", flat=True))
    return [row for row in rows if row.source_entity_id in valid_source_ids
            and row.target_entity_id in valid_target_ids]


def _owned_customer_ids(business_id):
    return set(models.Customer.objects.filter(business_id=business_id)
               .values_list("pk", flat=True))


def _channel_key(row, business_id):
    connection = row.integration_connection
    if connection is None or connection.business_id != business_id:
        return None
    return connection.integration_source.key


def _product_rows(scope, orders):
    order_ids = [row.pk for row in orders]
    links = _valid_relationships(scope.business_id, _ORDER_PRODUCT_RULE, source_ids=order_ids)
    linked = {(row.source_entity_id, row.target_entity_id) for row in links}
    items = models.OrderItem.objects.filter(order_id__in=order_ids).order_by("order_id", "pk")
    rows = []
    for item in items:
        if item.product_id is not None and (item.order_id, item.product_id) in linked:
            rows.append(item)
    return rows, links


def _ratio(numerator, denominator):
    if denominator == 0:
        return metrics.UNAVAILABLE
    with localcontext() as context:
        context.prec = _PRECISION
        return Decimal(numerator) / Decimal(denominator)


def _money_pairs(amounts):
    totals = {}
    for currency, amount in amounts:
        if isinstance(currency, str) and currency.strip():
            key = currency.strip()
            totals[key] = totals.get(key, Decimal("0")) + amount
    return tuple(sorted(totals.items()))


def analyze_products(*, business_id, period_type, period_start, period_end,
                     comparison_start=None, comparison_end=None):
    """BI §7: product sales/revenue plus raw comparison and verified context."""
    scope = _period(business_id, period_type, period_start, period_end)
    if (comparison_start is None) != (comparison_end is None):
        raise AnalysisValidationError("comparison_start and comparison_end must be supplied together.")
    if comparison_start is not None:
        comparison = _period(business_id, period_type, comparison_start, comparison_end)
    else:
        comparison = None
    orders = _orders(scope)
    items, links = _product_rows(scope, orders)
    order_by_id = {row.pk: row for row in orders}
    grouped = {}
    for item in items:
        grouped.setdefault(item.product_id, []).append(item)
    performances = []
    for product_id in sorted(grouped):
        product_items = grouped[product_id]
        product_orders = sorted({item.order_id for item in product_items})
        times = [order_by_id[order_id].ordered_at for order_id in product_orders]
        performances.append(ProductPerformance(
            product_id=product_id,
            units_sold=sum(item.quantity for item in product_items),
            order_count=len(product_orders),
            order_frequency=_ratio(len(product_orders), len(orders)),
            revenue_by_currency=_money_pairs(
                (order_by_id[item.order_id].currency, item.total_amount) for item in product_items
            ),
            first_ordered_at=min(times), last_ordered_at=max(times),
            order_ids=tuple(product_orders),
        ))

    order_products = {}
    for link in links:
        order_products.setdefault(link.source_entity_id, set()).add(link.target_entity_id)
    campaign_links = _valid_relationships(
        scope.business_id, _CAMPAIGN_ORDER_RULE, target_ids=[row.pk for row in orders]
    )
    campaigns = {}
    for link in campaign_links:
        for product_id in order_products.get(link.target_entity_id, ()):
            campaigns.setdefault(product_id, []).append((
                link.source_entity_id, link.target_entity_id, link.pk,
                "PLATFORM_REPORTED", link.rule_key,
            ))
    shipment_links = _valid_relationships(
        scope.business_id, _ORDER_SHIPMENT_RULE, source_ids=[row.pk for row in orders]
    )
    verified_shipments = {
        (link.source_entity_id, link.target_entity_id): link.pk for link in shipment_links
    }
    shipment_rows = models.Shipment.objects.filter(
        business_id=scope.business_id,
        id__in=sorted(link.target_entity_id for link in shipment_links),
    ).order_by("pk")
    delivery = {}
    for shipment in shipment_rows:
        relationship_id = verified_shipments.get((shipment.order_id, shipment.pk))
        if relationship_id is None:
            continue
        for product_id in order_products.get(shipment.order_id, ()):
            delivery.setdefault(product_id, []).append((
                shipment.pk, shipment.order_id, shipment.status,
                shipment.status in _FAILED_SHIPMENT_STATUSES,
                shipment.status in _RETURN_SHIPMENT_STATUSES,
                relationship_id, _ORDER_SHIPMENT_RULE.key,
            ))
    contexts = tuple(ProductContext(
        product_id=product_id,
        campaign_outcomes=tuple(sorted(campaigns.get(product_id, ()))),
        delivery_outcomes=tuple(sorted(delivery.get(product_id, ()))),
    ) for product_id in sorted(grouped))

    current_raw = tuple((row.product_id, row.units_sold, row.order_count, row.revenue_by_currency)
                        for row in performances)
    trend_inputs = (("CURRENT", scope.period_start, scope.period_end, current_raw),)
    if comparison is not None:
        prior = analyze_products(
            business_id=business_id, period_type=period_type,
            period_start=comparison.period_start, period_end=comparison.period_end,
        )
        prior_raw = tuple((row.product_id, row.units_sold, row.order_count, row.revenue_by_currency)
                          for row in prior.products)
        trend_inputs += (("COMPARISON", comparison.period_start, comparison.period_end, prior_raw),)
    all_rows = _all_period_orders(scope)
    unclassified = tuple(sorted({row.status for row in all_rows if row.status not in _COUNTED_STATUSES}))
    missing_time = models.Order.objects.filter(business_id=business_id, ordered_at__isnull=True).count()
    unresolved_orders = sum(1 for row in orders if row.pk not in order_products)
    raw_events = models.WebsiteEvent.objects.filter(
        session__business_id=business_id, product_id__isnull=False,
        occurred_at__gte=period_start, occurred_at__lt=period_end,
    ).count()
    return ProductAnalysis(
        scope=scope, products=tuple(performances), contexts=contexts,
        eligible_orders=len(orders), orders_without_timestamp=missing_time,
        orders_without_resolved_product=unresolved_orders,
        unclassified_order_statuses=unclassified, trend_inputs=trend_inputs,
        conversion_performance=UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "documented product-view/engagement event types and conversion mapping", raw_events),
        trend_classification=UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "configured improving/stable/declining rule", len(current_raw)),
        high_performing_detection=UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "configured disproportionate-performance rule", len(current_raw)),
        underperforming_detection=UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "configured weak/declining-performance rule", len(current_raw)),
        refund_allocation=UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "canonical refund-to-order-item/product allocation relationship"),
        relationship_provenance=(
            ("PRODUCT", _ORDER_PRODUCT_RULE.key, "DETERMINISTIC"),
            ("CAMPAIGN", _CAMPAIGN_ORDER_RULE.key, "PLATFORM_REPORTED"),
            ("DELIVERY", _ORDER_SHIPMENT_RULE.key, "DETERMINISTIC"),
        ),
    )


def _journey_rows(customer_id, orders, payments, sessions, events, conversations, calls, shipments):
    rows = []
    missing = []
    sources = (
        ("ORDER", orders, "ordered_at"), ("PAYMENT", payments, "paid_at"),
        ("WEBSITE_SESSION", sessions, "started_at"), ("WEBSITE_EVENT", events, "occurred_at"),
        ("CONVERSATION", conversations, "started_at"), ("CALL", calls, "started_at"),
        ("SHIPMENT", shipments, "submitted_at"),
    )
    for entity_type, values, field in sources:
        for value in values:
            timestamp = getattr(value, field)
            if timestamp is None:
                missing.append((entity_type, value.pk, field))
            else:
                rows.append((timestamp, entity_type, value.pk))
    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return tuple(rows), tuple(missing)


def analyze_customers(*, business_id, period_type, period_start, period_end):
    """BI §9: purchase/value/activity/channel/journey evidence and raw risk counts."""
    scope = _period(business_id, period_type, period_start, period_end)
    orders = _orders(scope)
    history = _orders(scope, all_history=True)
    owned_customers = _owned_customer_ids(business_id)
    first_by_customer = {}
    for row in history:
        if row.customer_id in owned_customers and row.customer_id not in first_by_customer:
            first_by_customer[row.customer_id] = (row.ordered_at, row.pk)
    grouped = {}
    for row in orders:
        if row.customer_id in owned_customers:
            grouped.setdefault(row.customer_id, []).append(row)
    item_rows, _ = _product_rows(scope, orders)
    items_by_customer = {}
    owner = {row.pk: row.customer_id for row in orders}
    for item in item_rows:
        if item.product_id is not None and owner.get(item.order_id) is not None:
            bucket = items_by_customer.setdefault(owner[item.order_id], {})
            bucket[item.product_id] = bucket.get(item.product_id, 0) + item.quantity
    tags = {}
    for customer_id, tag in models.CustomerTag.objects.filter(
        customer__business_id=business_id, customer_id__in=sorted(grouped)
    ).values_list("customer_id", "tag").order_by("customer_id", "tag"):
        tags.setdefault(customer_id, []).append(tag)

    purchases = []
    for customer_id in sorted(grouped):
        customer_orders = grouped[customer_id]
        purchase_rows = tuple((row.ordered_at, row.pk, row.currency, row.total_amount)
                              for row in customer_orders)
        gaps = tuple(Decimal((right[0] - left[0]).total_seconds())
                     for left, right in zip(purchase_rows, purchase_rows[1:]))
        channels = tuple(sorted({key for row in customer_orders
                                 if (key := _channel_key(row, business_id)) is not None}))
        first = first_by_customer[customer_id]
        segment = SEGMENT_NEW if scope.period_start <= first[0] < scope.period_end else SEGMENT_REPEAT
        purchases.append(CustomerPurchase(
            customer_id=customer_id, segment=segment,
            order_count=len(customer_orders),
            total_by_currency=_money_pairs((row.currency, row.total_amount) for row in customer_orders),
            product_units=tuple(sorted(items_by_customer.get(customer_id, {}).items())),
            ordered_purchases=purchase_rows, consecutive_gap_seconds=gaps,
            channels=channels, customer_groups=tuple(tags.get(customer_id, ())),
        ))

    activities = []
    risks = []
    missing_all = []
    period_all_orders = _all_period_orders(scope)
    activity_customer_ids = set(grouped)
    activity_customer_ids.update(models.Payment.objects.filter(
        business_id=business_id, customer_id__isnull=False,
        paid_at__gte=period_start, paid_at__lt=period_end,
        customer_id__in=sorted(owned_customers),
    ).values_list("customer_id", flat=True))
    activity_customer_ids.update(models.WebsiteSession.objects.filter(
        business_id=business_id, customer_id__isnull=False,
        started_at__gte=period_start, started_at__lt=period_end,
        customer_id__in=sorted(owned_customers),
    ).values_list("customer_id", flat=True))
    activity_customer_ids.update(models.WebsiteEvent.objects.filter(
        session__business_id=business_id, customer_id__isnull=False,
        occurred_at__gte=period_start, occurred_at__lt=period_end,
        customer_id__in=sorted(owned_customers),
    ).values_list("customer_id", flat=True))
    activity_customer_ids.update(models.Conversation.objects.filter(
        business_id=business_id, customer_id__isnull=False,
        started_at__gte=period_start, started_at__lt=period_end,
        customer_id__in=sorted(owned_customers),
    ).values_list("customer_id", flat=True))
    activity_customer_ids.update(models.Call.objects.filter(
        business_id=business_id, customer_id__isnull=False,
        started_at__gte=period_start, started_at__lt=period_end,
        customer_id__in=sorted(owned_customers),
    ).values_list("customer_id", flat=True))
    activity_customer_ids.update(models.Shipment.objects.filter(
        business_id=business_id, customer_id__isnull=False,
        order_id__in=[row.pk for row in period_all_orders],
        customer_id__in=sorted(owned_customers),
    ).values_list("customer_id", flat=True))
    for customer_id in sorted(activity_customer_ids):
        customer_orders = grouped.get(customer_id, [])
        activity_orders = [row for row in period_all_orders if row.customer_id == customer_id]
        payments = list(models.Payment.objects.filter(
            business_id=business_id, customer_id=customer_id,
            paid_at__gte=period_start, paid_at__lt=period_end,
        ).order_by("paid_at", "pk"))
        missing_payments = list(models.Payment.objects.filter(
            business_id=business_id, customer_id=customer_id, paid_at__isnull=True,
        ).order_by("pk"))
        payments.extend(missing_payments)
        sessions = list(models.WebsiteSession.objects.filter(
            business_id=business_id, customer_id=customer_id,
            started_at__gte=period_start, started_at__lt=period_end,
        ).order_by("started_at", "pk"))
        events = list(models.WebsiteEvent.objects.filter(
            session__business_id=business_id, customer_id=customer_id,
            occurred_at__gte=period_start, occurred_at__lt=period_end,
        ).order_by("occurred_at", "pk"))
        conversations = list(models.Conversation.objects.filter(
            business_id=business_id, customer_id=customer_id,
            started_at__gte=period_start, started_at__lt=period_end,
        ).order_by("started_at", "pk"))
        calls = list(models.Call.objects.filter(
            business_id=business_id, customer_id=customer_id,
            started_at__gte=period_start, started_at__lt=period_end,
        ).order_by("started_at", "pk"))
        calls.extend(models.Call.objects.filter(
            business_id=business_id, customer_id=customer_id, started_at__isnull=True,
        ).order_by("pk"))
        shipments = list(models.Shipment.objects.filter(
            business_id=business_id, customer_id=customer_id,
            order_id__in=[row.pk for row in activity_orders],
        ).order_by("pk"))
        journey, missing = _journey_rows(
            customer_id, activity_orders, payments, sessions, events,
            conversations, calls, shipments,
        )
        missing_all.extend((customer_id,) + row for row in missing)
        activities.append(CustomerActivity(
            customer_id, tuple(row.pk for row in activity_orders),
            tuple(row.pk for row in payments), tuple(row.pk for row in sessions),
            tuple(row.pk for row in events), tuple(row.pk for row in conversations),
            tuple(row.pk for row in calls), tuple(row.pk for row in shipments), journey,
            tuple(sorted(
                [("PURCHASE", "ORDER", row.pk, key)
                 for row in activity_orders
                 if (key := _channel_key(row, business_id)) is not None]
                + [("PAYMENT", "PAYMENT", row.pk, key)
                   for row in payments
                   if (key := _channel_key(row, business_id)) is not None]
                + [("WEBSITE", "WEBSITE_SESSION", row.pk, key)
                   for row in sessions
                   if (key := _channel_key(row, business_id)) is not None]
                + [("COMMUNICATION", "CONVERSATION", row.pk, row.channel)
                   for row in conversations]
                + [("COMMUNICATION", "CALL", row.pk, row.direction)
                   for row in calls]
            )),
        ))
        shipment_statuses = {row.status for row in shipments}
        conversation_statuses = {row.status for row in conversations}
        risks.append(CustomerRiskSignals(
            customer_id=customer_id,
            cancelled_orders=sum(1 for row in period_all_orders
                                 if row.customer_id == customer_id and row.status in _CANCELLED_STATUSES),
            failed_shipments=sum(row.status in _FAILED_SHIPMENT_STATUSES for row in shipments),
            returned_shipments=sum(row.status in _RETURN_SHIPMENT_STATUSES for row in shipments),
            unresolved_conversations=sum(row.status in _UNRESOLVED_CONVERSATION_STATUSES
                                         for row in conversations),
            unclassified_shipment_statuses=tuple(sorted(shipment_statuses - {
                "PENDING", "SUBMITTED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY",
                "DELIVERED", "FAILED", "RETURNING", "RETURNED", "CANCELLED",
            })),
            unclassified_conversation_statuses=tuple(sorted(
                conversation_statuses - _DOCUMENTED_CONVERSATION_STATUSES
            )),
        ))
    return CustomerAnalysis(
        scope=scope, customers=tuple(purchases), activities=tuple(activities),
        risk_signals=tuple(risks),
        orders_without_customer=sum(row.customer_id not in owned_customers for row in orders),
        missing_activity_timestamps=tuple(sorted(missing_all)),
        acquisition_channel=UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "canonical acquisition-channel field or deterministic acquisition rule"),
    )


def _retention_summary(customer_orders):
    customers = len(customer_orders)
    repeat = sum(len(rows) > 1 for rows in customer_orders.values())
    orders = sum(len(rows) for rows in customer_orders.values())
    return customers, repeat, _ratio(repeat, customers), orders, _ratio(orders, customers)


def analyze_retention(*, business_id, period_type, period_start, period_end,
                      comparison_start=None, comparison_end=None):
    """BI §10: repeat behavior, chronological gaps and evidence-backed segments."""
    scope = _period(business_id, period_type, period_start, period_end)
    if (comparison_start is None) != (comparison_end is None):
        raise AnalysisValidationError("comparison_start and comparison_end must be supplied together.")
    orders = _orders(scope)
    history = _orders(scope, all_history=True)
    owned_customers = _owned_customer_ids(business_id)
    grouped = {}
    for row in orders:
        if row.customer_id in owned_customers:
            grouped.setdefault(row.customer_id, []).append(row)
    customers, repeat, repeat_rate, order_count, frequency = _retention_summary(grouped)
    prior_customers = {row.customer_id for row in history
                       if row.customer_id in owned_customers and row.ordered_at < period_start}
    new = sum(customer_id not in prior_customers for customer_id in grouped)
    gaps = tuple((customer_id, tuple(
        Decimal((right.ordered_at - left.ordered_at).total_seconds())
        for left, right in zip(rows, rows[1:])
    )) for customer_id, rows in sorted(grouped.items()))

    item_rows, _ = _product_rows(scope, orders)
    owner = {row.pk: row.customer_id for row in orders}
    product_customers = {}
    for item in item_rows:
        customer_id = owner.get(item.order_id)
        if customer_id is not None:
            product_customers.setdefault(item.product_id, {}).setdefault(customer_id, set()).add(item.order_id)
    product_repeat = tuple((product_id, len(rows), sum(len(order_ids) > 1 for order_ids in rows.values()),
                            _ratio(sum(len(order_ids) > 1 for order_ids in rows.values()), len(rows)))
                           for product_id, rows in sorted(product_customers.items()))

    campaign_links = _valid_relationships(
        business_id, _CAMPAIGN_ORDER_RULE, target_ids=[row.pk for row in orders]
    )
    order_customer = {row.pk: row.customer_id for row in orders}
    campaign_groups = {}
    campaign_evidence = {}
    for link in campaign_links:
        customer_id = order_customer.get(link.target_entity_id)
        if customer_id is not None:
            campaign_groups.setdefault(link.source_entity_id, set()).add(customer_id)
            campaign_evidence.setdefault(link.source_entity_id, []).append(link.pk)
    campaign_retention = []
    for campaign_id in sorted(campaign_groups):
        campaign_customers = campaign_groups[campaign_id]
        repeated = sum(len(grouped[customer_id]) > 1 for customer_id in campaign_customers)
        campaign_retention.append(CampaignRetention(
            campaign_id, len(campaign_customers), repeated,
            _ratio(repeated, len(campaign_customers)),
            tuple(sorted(campaign_evidence[campaign_id])), "PLATFORM_REPORTED",
        ))

    segment_members = {}
    for customer_id, rows in grouped.items():
        for row in rows:
            if row.integration_connection_id is not None:
                key = _channel_key(row, business_id)
                if key is not None:
                    segment_members.setdefault((DIMENSION_CHANNEL, key), {}).setdefault(customer_id, []).append(row)
    for product_id, customer_rows in product_customers.items():
        for customer_id, order_ids in customer_rows.items():
            segment_members.setdefault((DIMENSION_PRODUCT, str(product_id)), {})[customer_id] = [
                row for row in grouped[customer_id] if row.pk in order_ids
            ]
    for campaign_id, member_ids in campaign_groups.items():
        for customer_id in member_ids:
            segment_members.setdefault((DIMENSION_CAMPAIGN, str(campaign_id)), {})[customer_id] = grouped[customer_id]
    for customer_id, tag in models.CustomerTag.objects.filter(
        customer__business_id=business_id, customer_id__in=sorted(grouped)
    ).values_list("customer_id", "tag").order_by("customer_id", "tag"):
        segment_members.setdefault((DIMENSION_CUSTOMER_GROUP, tag), {})[customer_id] = grouped[customer_id]
    segments = []
    for (dimension_type, dimension_value), members in sorted(segment_members.items()):
        count, repeated, rate, orders_count, freq = _retention_summary(members)
        segments.append(RetentionSegment(
            dimension_type, dimension_value, count, repeated, rate, orders_count, freq
        ))
    unavailable = (
        (DIMENSION_REGION, UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "canonical customer/order region field or configured normalized region metadata key")),
    )
    current_trend = (scope.period_start, scope.period_end, customers, repeat,
                     repeat_rate, order_count, frequency)
    trend_inputs = (("CURRENT", current_trend),)
    if comparison_start is not None:
        comparison = analyze_retention(
            business_id=business_id, period_type=period_type,
            period_start=comparison_start, period_end=comparison_end,
        )
        trend_inputs += (("COMPARISON", (
            comparison.scope.period_start, comparison.scope.period_end,
            comparison.customers, comparison.repeat_customers,
            comparison.repeat_rate, comparison.order_count,
            comparison.purchase_frequency,
        )),)
    return RetentionAnalysis(
        scope, customers, new, repeat, repeat_rate, order_count, frequency,
        gaps, product_repeat, tuple(campaign_retention), tuple(segments), unavailable,
        trend_inputs, UnavailableEvidence(False, UNAVAILABLE_MISSING_CONTRACT,
            "configured improving/stable/declining retention rule", len(trend_inputs)),
        sum(row.customer_id not in owned_customers for row in orders),
        models.Order.objects.filter(business_id=business_id, ordered_at__isnull=True).count(),
    )


def record_customer_metrics(*, business_id, period_type, period_start, period_end,
                            currency=None):
    """Record the five existing §2 customer keys from the §9/§10 evidence."""
    if currency is not None and (not isinstance(currency, str) or not currency.strip()):
        raise AnalysisValidationError("currency must be a non-blank string when supplied.")
    with transaction.atomic():
        analysis = analyze_retention(
            business_id=business_id, period_type=period_type,
            period_start=period_start, period_end=period_end,
        )
        orders = _orders(analysis.scope)
        owned_customers = _owned_customer_ids(business_id)
        customer_orders = [row for row in orders if row.customer_id in owned_customers]
        observed = sorted({row.currency for row in customer_orders
                           if isinstance(row.currency, str) and row.currency.strip()})
        if currency is None and len(observed) > 1:
            average_pairs = tuple((code, _ratio(
                sum((row.total_amount for row in customer_orders if row.currency == code), Decimal("0")),
                len({row.customer_id for row in customer_orders if row.currency == code}),
            )) for code in observed)
            average_reason = None
        else:
            selected = currency.strip() if currency is not None else (
                observed[0] if observed else models.Business.objects.get(pk=business_id).currency
            )
            scoped = [row for row in customer_orders if row.currency == selected]
            average_value = _ratio(
                sum((row.total_amount for row in scoped), Decimal("0")),
                len({row.customer_id for row in scoped}),
            )
            average_pairs = ((selected, average_value),)
            average_reason = None if average_value is not metrics.UNAVAILABLE else UNAVAILABLE_ZERO_DENOMINATOR
        values = {
            "new_customers": Decimal(analysis.new_customers),
            "active_customers": Decimal(analysis.customers),
            "repeat_rate": analysis.repeat_rate,
            "purchase_frequency": analysis.purchase_frequency,
        }
        inputs = {
            "service": "business_intelligence.customer_product",
            "specification_sections": ["7", "9", "10"],
            "eligible_order_statuses": sorted(_ELIGIBLE_STATUSES),
            "order_period_timestamp_field": "ordered_at",
            "eligible_order_ids": [row.pk for row in orders],
            "orders_without_resolved_customer": analysis.period_orders_without_customer,
            "orders_without_period_timestamp": analysis.orders_without_timestamp,
            "customer_ids": sorted({row.customer_id for row in customer_orders}),
        }
        snapshots = []
        for name in ("new_customers", "active_customers", "repeat_rate", "purchase_frequency"):
            metric_key = _CUSTOMER_METRICS[name]
            rule = _CALCULATION_RULES[metric_key]
            existing = metrics.get_metric_snapshot(
                business_id=business_id, metric_key=metric_key,
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start,
                period_end=analysis.scope.period_end,
            )
            if existing is not None and existing.calculation_rule != rule:
                raise metrics.MetricSnapshotConflictError(
                    f"Snapshot {existing.snapshot_id} already exists under calculation rule "
                    f"{existing.calculation_rule}, conflicting with {rule}."
                )
            snapshots.append((name, metrics.record_metric_snapshot(
                business_id=business_id, metric_key=metric_key, value=values[name],
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start, period_end=analysis.scope.period_end,
                calculation_rule=rule, inputs=inputs,
            )))
        average_key = _CUSTOMER_METRICS["average_value"]
        average_rule = _CALCULATION_RULES[average_key]
        for code, average in average_pairs:
            existing = metrics.get_metric_snapshot(
                business_id=business_id, metric_key=average_key,
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start,
                period_end=analysis.scope.period_end,
                dimension_type="CURRENCY", dimension_value=code,
            )
            if existing is not None and existing.calculation_rule != average_rule:
                raise metrics.MetricSnapshotConflictError(
                    f"Snapshot {existing.snapshot_id} already exists under calculation rule "
                    f"{existing.calculation_rule}, conflicting with {average_rule}."
                )
            average_inputs = {
                **inputs,
                "currency": code,
                "average_value_unavailable_reason": (
                    average_reason if average is metrics.UNAVAILABLE else None
                ),
                "currency_order_ids": [row.pk for row in customer_orders if row.currency == code],
            }
            snapshots.append((f"average_value:{code}", metrics.record_metric_snapshot(
                business_id=business_id, metric_key=average_key, value=average,
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start, period_end=analysis.scope.period_end,
                dimension_type="CURRENCY", dimension_value=code,
                calculation_rule=average_rule, inputs=average_inputs,
            )))
        return CustomerMetricRecording(analysis, average_pairs, tuple(snapshots))


__all__ = [
    "AnalysisCurrencyMixError", "AnalysisValidationError", "CampaignRetention",
    "CustomerActivity", "CustomerAnalysis", "CustomerMetricRecording", "CustomerPurchase",
    "CustomerRiskSignals", "ProductAnalysis", "ProductContext", "ProductPerformance",
    "RetentionAnalysis", "RetentionSegment", "Scope", "UnavailableEvidence",
    "analyze_customers", "analyze_products", "analyze_retention", "record_customer_metrics",
]
