"""Deterministic, evidence-supported marketing attribution services.

Serves Business Intelligence specification section 4 (Attribution).  This is an
internal, business-scoped service; callers remain responsible for authorization.
It consumes canonical models and valid T-001 relationships to associate conversions
(e.g., Orders) with marketing touchpoints (sessions and campaigns).

Key properties enforced:
1. Deterministic models: DIRECT, FIRST_TOUCH, and LAST_TOUCH.
2. Platform-reported attribution (from advertising platforms via CampaignConversion
   or SOURCE_REPORTED relationships) is preserved but kept strictly distinct from
   deterministic attribution.
3. Strict temporal ordering: touchpoints must occur at or before the conversion;
   future touchpoints are never eligible.
4. Configurable lookback window: touchpoints older than the window are excluded.
5. Resolved identity: customer journeys connect touchpoints of known canonical
   customers; unresolved guest identities remain unattributed across visitors (no
   speculative identity merging).
6. Cross-tenant isolation: all operations strictly filter by business_id.
7. Exact Decimal arithmetic: currency values are never mixed or aggregated across
   currencies without grouping.
"""

from dataclasses import dataclass
from decimal import Decimal
import datetime

from django.utils import timezone

from app import models
from . import metrics, relationships, revenue


class AttributionValidationError(ValueError):
    """An attribution boundary, parameter, or period input is invalid."""


class AttributionScopeError(AttributionValidationError):
    """An entity does not belong to the requested business."""


# Attribution models (§4)
MODEL_DIRECT = "DIRECT"
MODEL_FIRST_TOUCH = "FIRST_TOUCH"
MODEL_LAST_TOUCH = "LAST_TOUCH"
MODEL_PLATFORM_REPORTED = "PLATFORM_REPORTED"

SUPPORTED_MODELS = frozenset({
    MODEL_DIRECT,
    MODEL_FIRST_TOUCH,
    MODEL_LAST_TOUCH,
    MODEL_PLATFORM_REPORTED,
})

# Provenance labels (§4)
PROVENANCE_DETERMINISTIC = "DETERMINISTIC"
PROVENANCE_PLATFORM_REPORTED = "PLATFORM_REPORTED"
PROVENANCE_UNATTRIBUTED = "UNATTRIBUTED"

# Touchpoint types
TOUCHPOINT_SESSION = "WEBSITE_SESSION"
TOUCHPOINT_CAMPAIGN = "CAMPAIGN"

_SESSION_ORDER_RULE = relationships.RULES["session_order"]
_CAMPAIGN_ORDER_RULE = relationships.RULES["campaign_order"]
_CAMPAIGN_SESSION_RULE = relationships.RULES["campaign_session"]
_CUSTOMER_SESSION_RULE = relationships.RULES["customer_session"]

_RELATIONSHIP_SOURCES = {
    _SESSION_ORDER_RULE.key: "DETERMINISTIC",
    _CUSTOMER_SESSION_RULE.key: "DETERMINISTIC",
    _CAMPAIGN_ORDER_RULE.key: "DETERMINISTIC",
    _CAMPAIGN_SESSION_RULE.key: "DETERMINISTIC",
}


@dataclass(frozen=True)
class AttributionTouchpoint:
    """An identifiable marketing or website touchpoint in a customer journey."""
    touchpoint_type: str
    touchpoint_id: int
    timestamp: datetime.datetime
    campaign_id: int | None
    campaign_name: str | None
    platform: str | None
    traffic_source: str | None
    traffic_medium: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    customer_id: int | None
    visitor_id: int | None
    relationship_id: int | None
    provenance: str


@dataclass(frozen=True)
class AttributionResult:
    """The result of attributing a single conversion under a specific model."""
    conversion_type: str
    conversion_id: int
    conversion_timestamp: datetime.datetime
    customer_id: int | None
    currency: str
    amount: Decimal
    model: str
    is_attributed: bool
    touchpoint: AttributionTouchpoint | None
    candidate_touchpoint_count: int
    lookback_window_seconds: Decimal
    provenance: str
    evidence_relationships: tuple[int, ...]
    evidence_event_ids: tuple[int, ...]


@dataclass(frozen=True)
class OrderAttribution:
    """Comprehensive multi-model attribution for an individual order."""
    order_id: int
    customer_id: int | None
    ordered_at: datetime.datetime
    currency: str
    total_amount: Decimal
    direct: AttributionResult
    first_touch: AttributionResult
    last_touch: AttributionResult
    platform_reported: tuple[AttributionResult, ...]


@dataclass(frozen=True)
class CampaignAttributionSummary:
    """Aggregated conversions and revenue attributed to a campaign under a model."""
    campaign_id: int
    campaign_name: str
    platform: str
    model: str
    attributed_orders_count: int
    attributed_revenue_by_currency: tuple[tuple[str, Decimal], ...]
    unique_customers_count: int
    provenance: str
    evidence_relationship_ids: tuple[int, ...]


@dataclass(frozen=True)
class CustomerJourneyAttribution:
    """Attribution analysis across a known customer's journey."""
    customer_id: int
    touchpoints: tuple[AttributionTouchpoint, ...]
    orders: tuple[OrderAttribution, ...]
    first_touchpoint: AttributionTouchpoint | None
    last_touchpoint: AttributionTouchpoint | None
    direct_attributions_count: int


@dataclass(frozen=True)
class AttributionScope:
    business_id: int
    period_type: str
    period_start: datetime.datetime
    period_end: datetime.datetime


@dataclass(frozen=True)
class AttributionPeriodSummary:
    """Summary of attribution across all eligible orders in an analytical period."""
    scope: AttributionScope
    lookback_window_seconds: Decimal
    total_orders_count: int
    eligible_orders_count: int
    orders_without_customer_count: int
    attributed_counts_by_model: dict[str, int]
    unattributed_counts_by_model: dict[str, int]
    order_attributions: tuple[OrderAttribution, ...]
    campaign_summaries: tuple[CampaignAttributionSummary, ...]


def _positive_id(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < 2 ** 63:
        raise AttributionValidationError(f"{label} must be a positive 64-bit integer.")


def _parse_lookback(lookback_window):
    if lookback_window is None:
        raise AttributionValidationError(
            "lookback_window is required because the specification defines no "
            "default attribution window."
        )
    if isinstance(lookback_window, datetime.timedelta):
        if lookback_window <= datetime.timedelta(0):
            raise AttributionValidationError("lookback_window must be a positive timedelta.")
        return lookback_window
    if isinstance(lookback_window, bool):
        raise AttributionValidationError(
            "lookback_window must be a timedelta or positive finite seconds."
        )
    if isinstance(lookback_window, (int, float, Decimal)):
        seconds = Decimal(str(lookback_window))
        if not seconds.is_finite():
            raise AttributionValidationError("lookback_window must be finite.")
        if lookback_window <= 0:
            raise AttributionValidationError("lookback_window must be positive.")
        try:
            return datetime.timedelta(seconds=float(seconds))
        except OverflowError as exc:
            raise AttributionValidationError("lookback_window is too large.") from exc
    raise AttributionValidationError("lookback_window must be a timedelta or positive seconds.")


def _period(business_id, period_type, period_start, period_end):
    _positive_id(business_id, "business_id")
    if not isinstance(period_type, str) or not period_type.strip():
        raise AttributionValidationError("period_type must be a non-blank string.")
    if period_type.strip() not in metrics.PERIOD_TYPES:
        raise AttributionValidationError(
            f"period_type must be one of {sorted(metrics.PERIOD_TYPES)}."
        )
    if not isinstance(period_start, datetime.datetime) or not timezone.is_aware(period_start):
        raise AttributionValidationError("period_start must be a timezone-aware datetime.")
    if not isinstance(period_end, datetime.datetime) or not timezone.is_aware(period_end):
        raise AttributionValidationError("period_end must be a timezone-aware datetime.")
    if period_start >= period_end:
        raise AttributionValidationError("period_start must be earlier than period_end.")
    if not models.Business.objects.filter(pk=business_id).exists():
        raise AttributionValidationError("Business does not exist.")
    return AttributionScope(business_id, period_type.strip(), period_start, period_end)


def _valid_relationships(business_id, rule, *, source_ids=None, target_ids=None):
    """Retrieve verified, unexpired T-001 relationships for the given business."""
    query = models.BusinessRelationship.objects.filter(
        business_id=business_id,
        source_entity_type=rule.source_type,
        relationship_type=rule.relationship_type,
        target_entity_type=rule.target_type,
        rule_key=rule.key,
        relationship_source=_RELATIONSHIP_SOURCES[rule.key],
        valid_to__isnull=True,
    ).order_by("source_entity_id", "target_entity_id", "pk")
    if source_ids:
        query = query.filter(source_entity_id__in=sorted(source_ids))
    if target_ids:
        query = query.filter(target_entity_id__in=sorted(target_ids))
    rows = list(query)
    endpoint_models = {
        "ORDER": (models.Order, "business_id"),
        "CAMPAIGN": (models.Campaign, "business_id"),
        "WEBSITE_SESSION": (models.WebsiteSession, "business_id"),
        "CUSTOMER": (models.Customer, "business_id"),
    }
    if rule.source_type not in endpoint_models or rule.target_type not in endpoint_models:
        return rows
    source_model, source_business = endpoint_models[rule.source_type]
    target_model, target_business = endpoint_models[rule.target_type]
    valid_source_ids = set(source_model.objects.filter(
        **{source_business: business_id}, pk__in=[row.source_entity_id for row in rows]
    ).values_list("pk", flat=True))
    valid_target_ids = set(target_model.objects.filter(
        **{target_business: business_id}, pk__in=[row.target_entity_id for row in rows]
    ).values_list("pk", flat=True))
    return [
        row for row in rows
        if row.source_entity_id in valid_source_ids and row.target_entity_id in valid_target_ids
    ]


def _build_touchpoints_for_sessions(sessions, campaign_by_session):
    """Convert website sessions to AttributionTouchpoint objects with campaign context."""
    touchpoints = []
    for s in sessions:
        if s.started_at is None:
            continue
        campaign_info = campaign_by_session.get(s.pk)
        campaign_id = campaign_info[0] if campaign_info else None
        campaign_name = campaign_info[1] if campaign_info else None
        campaign_platform = campaign_info[2] if campaign_info else None
        relationship_id = campaign_info[3] if campaign_info else None

        touchpoints.append(AttributionTouchpoint(
            touchpoint_type=TOUCHPOINT_SESSION,
            touchpoint_id=s.pk,
            timestamp=s.started_at,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            platform=campaign_platform,
            traffic_source=s.traffic_source,
            traffic_medium=s.traffic_medium,
            utm_source=s.utm_source,
            utm_medium=s.utm_medium,
            utm_campaign=s.utm_campaign,
            customer_id=s.customer_id,
            visitor_id=s.visitor_id,
            relationship_id=relationship_id,
            provenance=PROVENANCE_DETERMINISTIC,
        ))
    return touchpoints


def _attribute_order_deterministic(
        order, candidate_touchpoints, direct_session_id, direct_relationship_id,
        direct_event_id, lookback_delta):
    """Compute DIRECT, FIRST_TOUCH, and LAST_TOUCH for an order from eligible touchpoints."""
    window_seconds = Decimal(str(lookback_delta.total_seconds()))
    amount = order.total_amount if isinstance(order.total_amount, Decimal) else Decimal(str(order.total_amount or "0"))
    currency = order.currency or ""

    # Qualifying touchpoints must be at or before order timestamp, within lookback window
    qualifying = [
        tp for tp in candidate_touchpoints
        if tp.timestamp <= order.ordered_at and (order.ordered_at - tp.timestamp) <= lookback_delta
    ]
    qualifying.sort(key=lambda item: (item.timestamp, item.touchpoint_type, item.touchpoint_id))

    # 1. DIRECT attribution
    direct_tp = None
    direct_relationships = []
    if direct_session_id is not None:
        for tp in qualifying:
            if tp.touchpoint_type == TOUCHPOINT_SESSION and tp.touchpoint_id == direct_session_id:
                if tp.timestamp <= order.ordered_at:
                    direct_tp = tp
                    if direct_relationship_id is not None:
                        direct_relationships.append(direct_relationship_id)
                    if tp.relationship_id and tp.relationship_id not in direct_relationships:
                        direct_relationships.append(tp.relationship_id)
                break

    direct_result = AttributionResult(
        conversion_type="ORDER",
        conversion_id=order.pk,
        conversion_timestamp=order.ordered_at,
        customer_id=order.customer_id,
        currency=currency,
        amount=amount,
        model=MODEL_DIRECT,
        is_attributed=direct_tp is not None,
        touchpoint=direct_tp,
        candidate_touchpoint_count=len(qualifying),
        lookback_window_seconds=window_seconds,
        provenance=PROVENANCE_DETERMINISTIC if direct_tp is not None else PROVENANCE_UNATTRIBUTED,
        evidence_relationships=tuple(direct_relationships),
        evidence_event_ids=(direct_event_id,) if direct_tp is not None and direct_event_id else (),
    )

    # 2. FIRST_TOUCH attribution
    first_tp = qualifying[0] if qualifying else None
    first_relationships = [first_tp.relationship_id] if (first_tp and first_tp.relationship_id) else []
    first_result = AttributionResult(
        conversion_type="ORDER",
        conversion_id=order.pk,
        conversion_timestamp=order.ordered_at,
        customer_id=order.customer_id,
        currency=currency,
        amount=amount,
        model=MODEL_FIRST_TOUCH,
        is_attributed=first_tp is not None,
        touchpoint=first_tp,
        candidate_touchpoint_count=len(qualifying),
        lookback_window_seconds=window_seconds,
        provenance=PROVENANCE_DETERMINISTIC if first_tp is not None else PROVENANCE_UNATTRIBUTED,
        evidence_relationships=tuple(first_relationships),
        evidence_event_ids=(),
    )

    # 3. LAST_TOUCH attribution
    last_tp = qualifying[-1] if qualifying else None
    last_relationships = [last_tp.relationship_id] if (last_tp and last_tp.relationship_id) else []
    last_result = AttributionResult(
        conversion_type="ORDER",
        conversion_id=order.pk,
        conversion_timestamp=order.ordered_at,
        customer_id=order.customer_id,
        currency=currency,
        amount=amount,
        model=MODEL_LAST_TOUCH,
        is_attributed=last_tp is not None,
        touchpoint=last_tp,
        candidate_touchpoint_count=len(qualifying),
        lookback_window_seconds=window_seconds,
        provenance=PROVENANCE_DETERMINISTIC if last_tp is not None else PROVENANCE_UNATTRIBUTED,
        evidence_relationships=tuple(last_relationships),
        evidence_event_ids=(),
    )

    return direct_result, first_result, last_result


def attribute_order(*, business_id, order_id, lookback_window=None):
    """BI §4: Perform multi-model evidence-supported attribution for a single order."""
    _positive_id(business_id, "business_id")
    _positive_id(order_id, "order_id")
    lookback_delta = _parse_lookback(lookback_window)
    window_seconds = Decimal(str(lookback_delta.total_seconds()))

    try:
        order = models.Order.objects.get(pk=order_id, business_id=business_id)
    except models.Order.DoesNotExist:
        raise AttributionScopeError(f"Order {order_id} does not exist for business {business_id}.")

    if order.ordered_at is None:
        raise AttributionValidationError(f"Order {order_id} has no ordered_at timestamp; cannot attribute.")
    if order.customer_id is not None and not models.Customer.objects.filter(
            pk=order.customer_id, business_id=business_id).exists():
        raise AttributionScopeError(
            f"Order {order_id} references a customer outside business {business_id}."
        )

    # 1. Discover platform-reported attribution links (CampaignConversion / campaign_order)
    campaign_order_links = _valid_relationships(
        business_id, _CAMPAIGN_ORDER_RULE, target_ids=[order.pk]
    )
    campaign_ids = [link.source_entity_id for link in campaign_order_links]
    campaigns = {c.pk: c for c in models.Campaign.objects.filter(business_id=business_id, pk__in=campaign_ids)}

    platform_reported = []
    amount = order.total_amount if isinstance(order.total_amount, Decimal) else Decimal(str(order.total_amount or "0"))
    currency = order.currency or ""
    for link in campaign_order_links:
        campaign = campaigns.get(link.source_entity_id)
        if campaign:
            tp = AttributionTouchpoint(
                touchpoint_type=TOUCHPOINT_CAMPAIGN,
                touchpoint_id=campaign.pk,
                timestamp=order.ordered_at,
                campaign_id=campaign.pk,
                campaign_name=campaign.name,
                platform=campaign.platform,
                traffic_source=None,
                traffic_medium=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                customer_id=order.customer_id,
                visitor_id=None,
                relationship_id=link.pk,
                provenance=PROVENANCE_PLATFORM_REPORTED,
            )
            platform_reported.append(AttributionResult(
                conversion_type="ORDER",
                conversion_id=order.pk,
                conversion_timestamp=order.ordered_at,
                customer_id=order.customer_id,
                currency=currency,
                amount=amount,
                model=MODEL_PLATFORM_REPORTED,
                is_attributed=True,
                touchpoint=tp,
                candidate_touchpoint_count=len(campaign_order_links),
                lookback_window_seconds=window_seconds,
                provenance=PROVENANCE_PLATFORM_REPORTED,
                evidence_relationships=(link.pk,),
                evidence_event_ids=(),
            ))

    # 2. Discover direct session linkage (session_order or WebsiteEvent with order_id)
    session_order_links = _valid_relationships(
        business_id, _SESSION_ORDER_RULE, target_ids=[order.pk]
    )
    direct_session_id = None
    direct_relationship_id = None
    direct_event_id = None
    if session_order_links:
        direct_session_id = session_order_links[0].source_entity_id
        direct_relationship_id = session_order_links[0].pk
    else:
        direct_event = models.WebsiteEvent.objects.filter(
            session__business_id=business_id, order_id=order.pk
        ).order_by("occurred_at", "pk").first()
        if direct_event:
            direct_session_id = direct_event.session_id
            direct_event_id = direct_event.pk

    # 3. Discover customer touchpoints
    # If the order is anonymous / guest (customer_id is None):
    # Only the direct session (if any) or sessions of the same anonymous visitor can be evaluated.
    candidate_sessions = []
    if order.customer_id is not None:
        candidate_sessions = list(models.WebsiteSession.objects.filter(
            business_id=business_id,
            customer_id=order.customer_id,
            started_at__isnull=False,
            started_at__lte=order.ordered_at,
            started_at__gte=order.ordered_at - lookback_delta,
        ).order_by("started_at", "pk"))
    elif direct_session_id is not None:
        direct_session = models.WebsiteSession.objects.filter(
            pk=direct_session_id, business_id=business_id
        ).first()
        if direct_session:
            candidate_sessions = [direct_session]

    # Map sessions to campaigns
    session_ids = [s.pk for s in candidate_sessions]
    camp_session_links = _valid_relationships(
        business_id, _CAMPAIGN_SESSION_RULE, target_ids=session_ids
    )
    camp_ids = [link.source_entity_id for link in camp_session_links]
    linked_campaigns = {c.pk: c for c in models.Campaign.objects.filter(business_id=business_id, pk__in=camp_ids)}
    campaign_by_session = {}
    for link in camp_session_links:
        c = linked_campaigns.get(link.source_entity_id)
        if c:
            campaign_by_session[link.target_entity_id] = (c.pk, c.name, c.platform, link.pk)

    touchpoints = _build_touchpoints_for_sessions(
        candidate_sessions, campaign_by_session
    )

    direct_res, first_res, last_res = _attribute_order_deterministic(
        order, touchpoints, direct_session_id, direct_relationship_id,
        direct_event_id, lookback_delta
    )

    return OrderAttribution(
        order_id=order.pk,
        customer_id=order.customer_id,
        ordered_at=order.ordered_at,
        currency=currency,
        total_amount=amount,
        direct=direct_res,
        first_touch=first_res,
        last_touch=last_res,
        platform_reported=tuple(platform_reported),
    )


def attribute_orders(*, business_id, period_type, period_start, period_end, lookback_window=None):
    """BI §4: Perform attribution across all revenue-eligible orders in an analytical period."""
    scope = _period(business_id, period_type, period_start, period_end)
    lookback_delta = _parse_lookback(lookback_window)
    window_seconds = Decimal(str(lookback_delta.total_seconds()))

    eligible_statuses = revenue.REVENUE_ELIGIBLE_ORDER_STATUSES
    orders = list(models.Order.objects.filter(
        business_id=business_id,
        status__in=sorted(eligible_statuses),
        ordered_at__isnull=False,
        ordered_at__gte=scope.period_start,
        ordered_at__lt=scope.period_end,
    ).order_by("ordered_at", "pk"))

    total_orders = models.Order.objects.filter(
        business_id=business_id,
        ordered_at__gte=scope.period_start,
        ordered_at__lt=scope.period_end,
    ).count()

    order_attributions = []
    attributed_counts = {model: 0 for model in SUPPORTED_MODELS}
    unattributed_counts = {model: 0 for model in SUPPORTED_MODELS}
    orders_without_customer = 0

    for order in orders:
        if order.customer_id is None:
            orders_without_customer += 1
        oa = attribute_order(business_id=business_id, order_id=order.pk, lookback_window=lookback_delta)
        order_attributions.append(oa)

        if oa.direct.is_attributed:
            attributed_counts[MODEL_DIRECT] += 1
        else:
            unattributed_counts[MODEL_DIRECT] += 1

        if oa.first_touch.is_attributed:
            attributed_counts[MODEL_FIRST_TOUCH] += 1
        else:
            unattributed_counts[MODEL_FIRST_TOUCH] += 1

        if oa.last_touch.is_attributed:
            attributed_counts[MODEL_LAST_TOUCH] += 1
        else:
            unattributed_counts[MODEL_LAST_TOUCH] += 1

        if oa.platform_reported:
            attributed_counts[MODEL_PLATFORM_REPORTED] += 1
        else:
            unattributed_counts[MODEL_PLATFORM_REPORTED] += 1

    # Campaign attribution summary under LAST_TOUCH by default
    campaign_summaries = attribute_campaigns(
        business_id=business_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        lookback_window=lookback_delta,
        model=MODEL_LAST_TOUCH,
        precomputed_attributions=order_attributions,
    )

    return AttributionPeriodSummary(
        scope=scope,
        lookback_window_seconds=window_seconds,
        total_orders_count=total_orders,
        eligible_orders_count=len(orders),
        orders_without_customer_count=orders_without_customer,
        attributed_counts_by_model=attributed_counts,
        unattributed_counts_by_model=unattributed_counts,
        order_attributions=tuple(order_attributions),
        campaign_summaries=campaign_summaries,
    )


def attribute_campaigns(*, business_id, period_type, period_start, period_end,
                        lookback_window=None, model=MODEL_LAST_TOUCH, precomputed_attributions=None):
    """BI §4: Summarize attributed conversions and revenue by marketing campaign."""
    scope = _period(business_id, period_type, period_start, period_end)
    if model not in SUPPORTED_MODELS:
        raise AttributionValidationError(f"model must be one of {sorted(SUPPORTED_MODELS)}.")
    lookback_delta = _parse_lookback(lookback_window)

    if precomputed_attributions is None:
        summary = attribute_orders(
            business_id=business_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            lookback_window=lookback_delta,
        )
        attributions = summary.order_attributions
    else:
        attributions = precomputed_attributions

    campaigns = {c.pk: c for c in models.Campaign.objects.filter(business_id=business_id)}
    grouped = {}

    for oa in attributions:
        if model == MODEL_PLATFORM_REPORTED:
            for res in oa.platform_reported:
                if res.touchpoint and res.touchpoint.campaign_id:
                    cid = res.touchpoint.campaign_id
                    grouped.setdefault(cid, []).append((res, oa))
        else:
            res = getattr(oa, model.lower(), None)
            if res and res.is_attributed and res.touchpoint and res.touchpoint.campaign_id:
                cid = res.touchpoint.campaign_id
                grouped.setdefault(cid, []).append((res, oa))

    summaries = []
    for cid in sorted(campaigns):
        campaign = campaigns[cid]
        entries = grouped.get(cid, [])
        orders_count = len(entries)
        unique_customers = len({oa.customer_id for _, oa in entries if oa.customer_id is not None})

        # Sum revenue per currency
        currency_totals = {}
        evidence_rels = set()
        for res, oa in entries:
            currency_totals[oa.currency] = currency_totals.get(oa.currency, Decimal("0")) + oa.total_amount
            evidence_rels.update(res.evidence_relationships)

        revenue_pairs = tuple(sorted(currency_totals.items()))
        provenance = PROVENANCE_PLATFORM_REPORTED if model == MODEL_PLATFORM_REPORTED else PROVENANCE_DETERMINISTIC

        summaries.append(CampaignAttributionSummary(
            campaign_id=cid,
            campaign_name=campaign.name,
            platform=campaign.platform,
            model=model,
            attributed_orders_count=orders_count,
            attributed_revenue_by_currency=revenue_pairs,
            unique_customers_count=unique_customers,
            provenance=provenance,
            evidence_relationship_ids=tuple(sorted(evidence_rels)),
        ))

    return tuple(summaries)


def attribute_customer_journey(*, business_id, customer_id, lookback_window=None):
    """BI §4: Trace and attribute touchpoints across a known canonical customer journey."""
    _positive_id(business_id, "business_id")
    _positive_id(customer_id, "customer_id")
    lookback_delta = _parse_lookback(lookback_window)

    try:
        customer = models.Customer.objects.get(pk=customer_id, business_id=business_id)
    except models.Customer.DoesNotExist:
        raise AttributionScopeError(f"Customer {customer_id} does not exist for business {business_id}.")

    sessions = list(models.WebsiteSession.objects.filter(
        business_id=business_id, customer_id=customer_id, started_at__isnull=False
    ).order_by("started_at", "pk"))

    session_ids = [s.pk for s in sessions]
    camp_session_links = _valid_relationships(
        business_id, _CAMPAIGN_SESSION_RULE, target_ids=session_ids
    )
    camp_ids = [link.source_entity_id for link in camp_session_links]
    linked_campaigns = {c.pk: c for c in models.Campaign.objects.filter(business_id=business_id, pk__in=camp_ids)}
    campaign_by_session = {}
    for link in camp_session_links:
        c = linked_campaigns.get(link.source_entity_id)
        if c:
            campaign_by_session[link.target_entity_id] = (c.pk, c.name, c.platform, link.pk)

    touchpoints = tuple(_build_touchpoints_for_sessions(
        sessions, campaign_by_session
    ))

    # Trace customer orders
    orders = list(models.Order.objects.filter(
        business_id=business_id, customer_id=customer_id, ordered_at__isnull=False
    ).order_by("ordered_at", "pk"))

    order_attributions = []
    direct_count = 0
    for order in orders:
        oa = attribute_order(business_id=business_id, order_id=order.pk, lookback_window=lookback_delta)
        order_attributions.append(oa)
        if oa.direct.is_attributed:
            direct_count += 1

    first_tp = touchpoints[0] if touchpoints else None
    last_tp = touchpoints[-1] if touchpoints else None

    return CustomerJourneyAttribution(
        customer_id=customer_id,
        touchpoints=touchpoints,
        orders=tuple(order_attributions),
        first_touchpoint=first_tp,
        last_touchpoint=last_tp,
        direct_attributions_count=direct_count,
    )


__all__ = [
    "AttributionPeriodSummary",
    "AttributionResult",
    "AttributionScope",
    "AttributionScopeError",
    "AttributionTouchpoint",
    "AttributionValidationError",
    "CampaignAttributionSummary",
    "CustomerJourneyAttribution",
    "MODEL_DIRECT",
    "MODEL_FIRST_TOUCH",
    "MODEL_LAST_TOUCH",
    "MODEL_PLATFORM_REPORTED",
    "OrderAttribution",
    "PROVENANCE_DETERMINISTIC",
    "PROVENANCE_PLATFORM_REPORTED",
    "PROVENANCE_UNATTRIBUTED",
    "SUPPORTED_MODELS",
    "TOUCHPOINT_CAMPAIGN",
    "TOUCHPOINT_SESSION",
    "attribute_campaigns",
    "attribute_customer_journey",
    "attribute_order",
    "attribute_orders",
]
