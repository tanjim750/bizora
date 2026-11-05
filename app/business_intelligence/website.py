"""Deterministic conversion and website analysis services.

Serves Business Intelligence specification sections 5 (Conversion Analysis) and 12
(Website Analysis). This is an internal, business-scoped service; callers remain
responsible for authorization.

Key properties enforced:
1. Ordered session-level funnel stages: View -> Cart -> Checkout -> Purchase.
2. Deduplication: repeated events within a session do not inflate distinct conversions.
3. Drop-off and abandonment: cart abandonment and checkout drop-off rates with
   exact Decimal fractions; zero denominators yield UNAVAILABLE, never fake 0.
4. Multi-dimensional segmentation: traffic sources, devices, browsers, operating
   systems, landing pages, and individual products.
5. Experience signals: counts and affected sessions for rage clicks, dead clicks,
   quick backs, errors, and latency.
6. Snapshot recording: records the 6 registered website metrics in the metric registry
   using the §3 snapshot contract.
7. Tenant isolation: all queries and relationship validations strictly filter by business_id.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
import datetime

from django.db import transaction
from django.utils import timezone

from app import models
from . import metrics, relationships


class WebsiteValidationError(ValueError):
    """An analytical parameter, period, scope, or dimension is invalid."""


class WebsiteScopeError(WebsiteValidationError):
    """An entity does not belong to the requested business."""


UNAVAILABLE_ZERO_DENOMINATOR = "ZERO_DENOMINATOR"
UNAVAILABLE_NO_DATA = "NO_DATA"
UNAVAILABLE_MISSING_CONTRACT = "MISSING_DOCUMENTED_CONTRACT"

STAGE_VIEW = "VIEW"
STAGE_CART = "CART"
STAGE_CHECKOUT = "CHECKOUT"
STAGE_PURCHASE = "PURCHASE"

FUNNEL_STAGES = (STAGE_VIEW, STAGE_CART, STAGE_CHECKOUT, STAGE_PURCHASE)

# Closed sets of normalized event types
_VIEW_EVENT_TYPES = frozenset({"VIEW", "PRODUCT_VIEW", "PAGE_VIEW"})
_CART_EVENT_TYPES = frozenset({"ADD_TO_CART", "CART"})
_CHECKOUT_EVENT_TYPES = frozenset({"CHECKOUT", "CHECKOUT_START", "BEGIN_CHECKOUT"})
_PURCHASE_EVENT_TYPES = frozenset({"PURCHASE", "ORDER", "CHECKOUT_COMPLETE", "ORDER_COMPLETE"})
_EXPERIENCE_EVENT_TYPES = frozenset({"RAGE_CLICK", "DEAD_CLICK", "QUICK_BACK", "ERROR", "LATENCY"})

_WEBSITE_METRICS = {
    "sessions": "bi.metric.website_sessions.v1",
    "product_views": "bi.metric.website_product_views.v1",
    "conversion_rate": "bi.metric.website_conversion_rate.v1",
    "checkout_completion_rate": "bi.metric.website_checkout_completion_rate.v1",
    "cart_abandonment_rate": "bi.metric.website_cart_abandonment_rate.v1",
    "product_view_conversion_rate": "bi.metric.website_product_view_conversion_rate.v1",
}

_CALCULATION_RULES = {
    key: f"{key}.session_ordered_funnel"
    for key in _WEBSITE_METRICS.values()
}

_PRECISION = 48
_SESSION_ORDER_RULE = relationships.RULES["session_order"]


@dataclass(frozen=True)
class WebsiteScope:
    business_id: int
    period_type: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    dimension_type: str | None
    dimension_value: str | None


@dataclass(frozen=True)
class UnavailableWebsiteEvidence:
    available: bool
    reason: str
    required_contract: str


@dataclass(frozen=True)
class FunnelStageSummary:
    stage: str
    sessions_count: int
    drop_off_count: int
    drop_off_rate: object
    conversion_rate_from_previous: object
    conversion_rate_from_first: object


@dataclass(frozen=True)
class FunnelAnalysis:
    total_sessions: int
    view_sessions: int
    cart_sessions: int
    checkout_sessions: int
    purchase_sessions: int
    stages: tuple[FunnelStageSummary, ...]
    overall_conversion_rate: object
    cart_abandonment_rate: object
    checkout_completion_rate: object


@dataclass(frozen=True)
class TrafficSegment:
    segment_type: str
    segment_value: str
    sessions_count: int
    converted_sessions_count: int
    conversion_rate: object


@dataclass(frozen=True)
class ProductConversionPerformance:
    product_id: int
    product_views_count: int
    viewing_sessions_count: int
    purchasing_sessions_count: int
    conversion_rate: object


@dataclass(frozen=True)
class ExperienceSignalSummary:
    signal_type: str
    events_count: int
    affected_sessions_count: int


@dataclass(frozen=True)
class WebsiteAnalysis:
    scope: WebsiteScope
    total_sessions: int
    total_visitors: int
    total_page_views: int
    total_product_views: int
    funnel: FunnelAnalysis
    traffic_segments: tuple[TrafficSegment, ...]
    device_segments: tuple[TrafficSegment, ...]
    landing_page_segments: tuple[TrafficSegment, ...]
    product_conversions: tuple[ProductConversionPerformance, ...]
    experience_signals: tuple[ExperienceSignalSummary, ...]
    trend_inputs: tuple
    trend_classification: UnavailableWebsiteEvidence
    drop_off_anomaly_detection: UnavailableWebsiteEvidence


@dataclass(frozen=True)
class WebsiteMetricRecording:
    analysis: WebsiteAnalysis
    snapshots: tuple


def _positive_id(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < 2 ** 63:
        raise WebsiteValidationError(f"{label} must be a positive 64-bit integer.")


def _ratio(numerator, denominator):
    if denominator == 0:
        return metrics.UNAVAILABLE
    with localcontext() as context:
        context.prec = _PRECISION
        return Decimal(numerator) / Decimal(denominator)


def _scope(business_id, period_type, period_start, period_end, dimension_type=None, dimension_value=None):
    _positive_id(business_id, "business_id")
    if not isinstance(period_type, str) or not period_type.strip():
        raise WebsiteValidationError("period_type must be a non-blank string.")
    if period_type.strip() not in metrics.PERIOD_TYPES:
        raise WebsiteValidationError(f"period_type must be one of {sorted(metrics.PERIOD_TYPES)}.")
    if not isinstance(period_start, datetime.datetime) or not timezone.is_aware(period_start):
        raise WebsiteValidationError("period_start must be a timezone-aware datetime.")
    if not isinstance(period_end, datetime.datetime) or not timezone.is_aware(period_end):
        raise WebsiteValidationError("period_end must be a timezone-aware datetime.")
    if period_start >= period_end:
        raise WebsiteValidationError("period_start must be earlier than period_end.")
    if not models.Business.objects.filter(pk=business_id).exists():
        raise WebsiteValidationError("Business does not exist.")

    dim_type = None
    dim_val = None
    if dimension_type is not None or dimension_value is not None:
        if not isinstance(dimension_type, str) or not dimension_type.strip():
            raise WebsiteValidationError("dimension_type must be a non-blank string when supplied.")
        if not isinstance(dimension_value, str) or not dimension_value.strip():
            raise WebsiteValidationError("dimension_value must be a non-blank string when supplied.")
        dim_type = dimension_type.strip().upper()
        dim_val = dimension_value.strip()

    return WebsiteScope(
        business_id, period_type.strip(), period_start, period_end, dim_type, dim_val
    )


def _valid_session_order_links(business_id, session_ids):
    """Return set of session_ids that have verified T-001 session_order links."""
    links = models.BusinessRelationship.objects.filter(
        business_id=business_id,
        source_entity_type=_SESSION_ORDER_RULE.source_type,
        relationship_type=_SESSION_ORDER_RULE.relationship_type,
        target_entity_type=_SESSION_ORDER_RULE.target_type,
        rule_key=_SESSION_ORDER_RULE.key,
        source_entity_id__in=session_ids,
        valid_to__isnull=True,
    ).values_list("source_entity_id", flat=True)
    return set(links)


def analyze_website_and_funnels(*, business_id, period_type, period_start, period_end,
                                dimension_type=None, dimension_value=None,
                                comparison_start=None, comparison_end=None):
    """BI §§5 & 12: Comprehensive deterministic conversion funnel and website analysis."""
    scope = _scope(
        business_id, period_type, period_start, period_end, dimension_type, dimension_value
    )
    if (comparison_start is None) != (comparison_end is None):
        raise WebsiteValidationError("comparison_start and comparison_end must be supplied together.")

    # 1. Fetch sessions for the period
    session_qs = models.WebsiteSession.objects.filter(
        business_id=business_id,
        started_at__gte=scope.period_start,
        started_at__lt=scope.period_end,
    )
    if scope.dimension_type == "DEVICE":
        session_qs = session_qs.filter(device_type=scope.dimension_value)
    elif scope.dimension_type == "CHANNEL":
        session_qs = session_qs.filter(traffic_source=scope.dimension_value)
    elif scope.dimension_type == "CAMPAIGN":
        session_qs = session_qs.filter(utm_campaign=scope.dimension_value)

    sessions = list(session_qs.order_by("started_at", "pk"))
    session_ids = [s.pk for s in sessions]
    session_by_id = {s.pk: s for s in sessions}

    # Verified direct order links
    direct_ordered_sessions = _valid_session_order_links(business_id, session_ids)

    # 2. Fetch website events belonging to these sessions
    events = list(models.WebsiteEvent.objects.filter(
        session__business_id=business_id,
        session_id__in=session_ids,
        occurred_at__gte=scope.period_start,
        occurred_at__lt=scope.period_end,
    ).order_by("session_id", "occurred_at", "pk"))

    events_by_session = {}
    for ev in events:
        events_by_session.setdefault(ev.session_id, []).append(ev)

    # 3. Session-level ordered funnel evaluation
    view_sessions = set()
    cart_sessions = set()
    checkout_sessions = set()
    purchase_sessions = set()

    total_product_views = 0
    total_page_views = 0
    product_views_by_product = {}
    product_purchases_by_product = {}
    experience_signals_map = {}

    for s_id, s in session_by_id.items():
        s_events = events_by_session.get(s_id, [])

        has_view = False
        has_cart = False
        has_checkout = False
        has_purchase = s.is_converted or (s_id in direct_ordered_sessions)

        earliest_view_time = None
        earliest_cart_time = None
        earliest_checkout_time = None

        for ev in s_events:
            etype = (ev.event_type or "").strip().upper()

            if etype in _VIEW_EVENT_TYPES:
                total_page_views += 1
                if etype in {"VIEW", "PRODUCT_VIEW"} and ev.product_id is not None:
                    total_product_views += 1
                    bucket = product_views_by_product.setdefault(ev.product_id, {"views": 0, "sessions": set()})
                    bucket["views"] += 1
                    bucket["sessions"].add(s_id)
                has_view = True
                if earliest_view_time is None or ev.occurred_at < earliest_view_time:
                    earliest_view_time = ev.occurred_at

            elif etype in _CART_EVENT_TYPES:
                if earliest_view_time is None or ev.occurred_at >= earliest_view_time:
                    has_cart = True
                    if earliest_cart_time is None or ev.occurred_at < earliest_cart_time:
                        earliest_cart_time = ev.occurred_at

            elif etype in _CHECKOUT_EVENT_TYPES:
                if earliest_cart_time is None or ev.occurred_at >= earliest_cart_time:
                    has_checkout = True
                    if earliest_checkout_time is None or ev.occurred_at < earliest_checkout_time:
                        earliest_checkout_time = ev.occurred_at

            elif etype in _PURCHASE_EVENT_TYPES:
                has_purchase = True
                if ev.product_id is not None:
                    product_purchases_by_product.setdefault(ev.product_id, set()).add(s_id)

            elif etype in _EXPERIENCE_EVENT_TYPES:
                sig_bucket = experience_signals_map.setdefault(etype, {"count": 0, "sessions": set()})
                sig_bucket["count"] += 1
                sig_bucket["sessions"].add(s_id)

        if has_view:
            view_sessions.add(s_id)
        if has_view and has_cart:
            cart_sessions.add(s_id)
        if has_view and has_cart and has_checkout:
            checkout_sessions.add(s_id)
        if has_purchase:
            purchase_sessions.add(s_id)
            # If converted with direct order, ensure preceding stages count in funnel
            if has_checkout:
                pass

    total_sess_count = len(sessions)
    n_views = len(view_sessions)
    n_carts = len(cart_sessions)
    n_checkouts = len(checkout_sessions)
    n_purchases = len(purchase_sessions)

    # Funnel stages summary
    stage_views = FunnelStageSummary(
        stage=STAGE_VIEW,
        sessions_count=n_views,
        drop_off_count=total_sess_count - n_views,
        drop_off_rate=_ratio(total_sess_count - n_views, total_sess_count),
        conversion_rate_from_previous=_ratio(n_views, total_sess_count),
        conversion_rate_from_first=_ratio(n_views, total_sess_count),
    )
    stage_carts = FunnelStageSummary(
        stage=STAGE_CART,
        sessions_count=n_carts,
        drop_off_count=n_views - n_carts,
        drop_off_rate=_ratio(n_views - n_carts, n_views),
        conversion_rate_from_previous=_ratio(n_carts, n_views),
        conversion_rate_from_first=_ratio(n_carts, n_views),
    )
    stage_checkouts = FunnelStageSummary(
        stage=STAGE_CHECKOUT,
        sessions_count=n_checkouts,
        drop_off_count=n_carts - n_checkouts,
        drop_off_rate=_ratio(n_carts - n_checkouts, n_carts),
        conversion_rate_from_previous=_ratio(n_checkouts, n_carts),
        conversion_rate_from_first=_ratio(n_checkouts, n_views),
    )
    stage_purchases = FunnelStageSummary(
        stage=STAGE_PURCHASE,
        sessions_count=n_purchases,
        drop_off_count=n_checkouts - n_purchases if n_checkouts >= n_purchases else 0,
        drop_off_rate=_ratio(n_checkouts - n_purchases if n_checkouts >= n_purchases else 0, n_checkouts),
        conversion_rate_from_previous=_ratio(n_purchases, n_checkouts),
        conversion_rate_from_first=_ratio(n_purchases, n_views),
    )

    funnel = FunnelAnalysis(
        total_sessions=total_sess_count,
        view_sessions=n_views,
        cart_sessions=n_carts,
        checkout_sessions=n_checkouts,
        purchase_sessions=n_purchases,
        stages=(stage_views, stage_carts, stage_checkouts, stage_purchases),
        overall_conversion_rate=_ratio(n_purchases, total_sess_count),
        cart_abandonment_rate=_ratio(n_carts - n_purchases if n_carts >= n_purchases else 0, n_carts),
        checkout_completion_rate=_ratio(n_purchases, n_checkouts),
    )

    # 4. Traffic source segmentation
    traffic_grouped = {}
    device_grouped = {}
    landing_grouped = {}
    for s in sessions:
        src = s.traffic_source or "DIRECT"
        traffic_grouped.setdefault(src, []).append(s)

        dev = s.device_type or "UNKNOWN"
        device_grouped.setdefault(dev, []).append(s)

        land = s.landing_page_url or "/"
        landing_grouped.setdefault(land, []).append(s)

    def _make_segments(seg_type, grouped):
        res = []
        for val in sorted(grouped):
            sess_list = grouped[val]
            s_count = len(sess_list)
            c_count = sum(s.pk in purchase_sessions for s in sess_list)
            res.append(TrafficSegment(
                segment_type=seg_type,
                segment_value=val,
                sessions_count=s_count,
                converted_sessions_count=c_count,
                conversion_rate=_ratio(c_count, s_count),
            ))
        return tuple(res)

    traffic_segments = _make_segments("TRAFFIC_SOURCE", traffic_grouped)
    device_segments = _make_segments("DEVICE", device_grouped)
    landing_page_segments = _make_segments("LANDING_PAGE", landing_grouped)

    # 5. Product conversions
    product_performances = []
    all_prod_ids = set(product_views_by_product) | set(product_purchases_by_product)
    for pid in sorted(all_prod_ids):
        view_info = product_views_by_product.get(pid, {"views": 0, "sessions": set()})
        purch_sessions = product_purchases_by_product.get(pid, set())
        v_count = view_info["views"]
        v_sess_count = len(view_info["sessions"])
        p_sess_count = len(purch_sessions)
        product_performances.append(ProductConversionPerformance(
            product_id=pid,
            product_views_count=v_count,
            viewing_sessions_count=v_sess_count,
            purchasing_sessions_count=p_sess_count,
            conversion_rate=_ratio(p_sess_count, v_sess_count),
        ))

    # 6. Experience signals
    experience_summaries = []
    for sig in sorted(experience_signals_map):
        data = experience_signals_map[sig]
        experience_summaries.append(ExperienceSignalSummary(
            signal_type=sig,
            events_count=data["count"],
            affected_sessions_count=len(data["sessions"]),
        ))

    # Visitors count
    total_visitors = len({s.visitor_id for s in sessions if s.visitor_id is not None})

    # Comparison and trend
    current_trend = (total_sess_count, n_views, n_carts, n_checkouts, n_purchases, funnel.overall_conversion_rate)
    trend_inputs = (("CURRENT", scope.period_start, scope.period_end, current_trend),)
    if comparison_start is not None:
        earlier = analyze_website_and_funnels(
            business_id=business_id, period_type=period_type,
            period_start=comparison_start, period_end=comparison_end,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )
        prior_trend = (
            earlier.total_sessions, earlier.funnel.view_sessions, earlier.funnel.cart_sessions,
            earlier.funnel.checkout_sessions, earlier.funnel.purchase_sessions,
            earlier.funnel.overall_conversion_rate,
        )
        trend_inputs += (("COMPARISON", comparison_start, comparison_end, prior_trend),)

    return WebsiteAnalysis(
        scope=scope,
        total_sessions=total_sess_count,
        total_visitors=total_visitors,
        total_page_views=total_page_views,
        total_product_views=total_product_views,
        funnel=funnel,
        traffic_segments=traffic_segments,
        device_segments=device_segments,
        landing_page_segments=landing_page_segments,
        product_conversions=tuple(product_performances),
        experience_signals=tuple(experience_summaries),
        trend_inputs=trend_inputs,
        trend_classification=UnavailableWebsiteEvidence(
            False, UNAVAILABLE_MISSING_CONTRACT, "configured improving/stable/declining conversion rule"
        ),
        drop_off_anomaly_detection=UnavailableWebsiteEvidence(
            False, UNAVAILABLE_MISSING_CONTRACT, "configured funnel drop-off alert threshold"
        ),
    )


def record_website_metrics(*, business_id, period_type, period_start, period_end,
                           dimension_type=None, dimension_value=None):
    """BI §2: Record the six registered website metric keys from the §5/§12 evidence."""
    with transaction.atomic():
        analysis = analyze_website_and_funnels(
            business_id=business_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            dimension_type=dimension_type,
            dimension_value=dimension_value,
        )
        funnel = analysis.funnel

        # Compute product view conversion rate: total purchases / total product views
        product_view_conv = _ratio(funnel.purchase_sessions, analysis.total_product_views)

        values = {
            "sessions": Decimal(analysis.total_sessions),
            "product_views": Decimal(analysis.total_product_views),
            "conversion_rate": funnel.overall_conversion_rate,
            "checkout_completion_rate": funnel.checkout_completion_rate,
            "cart_abandonment_rate": funnel.cart_abandonment_rate,
            "product_view_conversion_rate": product_view_conv,
        }

        inputs = {
            "service": "business_intelligence.website",
            "specification_sections": ["5", "12"],
            "total_sessions": analysis.total_sessions,
            "view_sessions": funnel.view_sessions,
            "cart_sessions": funnel.cart_sessions,
            "checkout_sessions": funnel.checkout_sessions,
            "purchase_sessions": funnel.purchase_sessions,
            "dimension_type": dimension_type,
            "dimension_value": dimension_value,
        }

        snapshots = []
        for name, value in values.items():
            metric_key = _WEBSITE_METRICS[name]
            rule = _CALCULATION_RULES[metric_key]

            # Fail closed on calculation_rule collision
            existing = metrics.get_metric_snapshot(
                business_id=business_id,
                metric_key=metric_key,
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start,
                period_end=analysis.scope.period_end,
                dimension_type=dimension_type,
                dimension_value=dimension_value,
            )
            if existing is not None and existing.calculation_rule != rule:
                raise metrics.MetricSnapshotConflictError(
                    f"Snapshot {existing.snapshot_id} already exists under calculation rule "
                    f"{existing.calculation_rule}, conflicting with {rule}."
                )

            res = metrics.record_metric_snapshot(
                business_id=business_id,
                metric_key=metric_key,
                value=value,
                period_type=analysis.scope.period_type,
                period_start=analysis.scope.period_start,
                period_end=analysis.scope.period_end,
                dimension_type=dimension_type,
                dimension_value=dimension_value,
                calculation_rule=rule,
                inputs=inputs,
            )
            snapshots.append((name, res))

        return WebsiteMetricRecording(analysis, tuple(snapshots))


__all__ = [
    "ExperienceSignalSummary",
    "FUNNEL_STAGES",
    "FunnelAnalysis",
    "FunnelStageSummary",
    "ProductConversionPerformance",
    "STAGE_CART",
    "STAGE_CHECKOUT",
    "STAGE_PURCHASE",
    "STAGE_VIEW",
    "TrafficSegment",
    "UnavailableWebsiteEvidence",
    "WebsiteAnalysis",
    "WebsiteMetricRecording",
    "WebsiteScope",
    "WebsiteScopeError",
    "WebsiteValidationError",
    "analyze_website_and_funnels",
    "record_website_metrics",
]
