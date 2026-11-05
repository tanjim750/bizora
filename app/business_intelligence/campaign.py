"""Deterministic campaign analysis for BI specification section 8.

Provider ratio columns are evidence only. Standardized CTR, CPC, CPM,
conversion rate and ROAS are recalculated from normalized daily inputs. The
caller supplies the attribution model and lookback window; no threshold or
window is invented here.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
import datetime

from django.db import transaction
from django.utils import timezone

from app import models
from . import attribution, metrics


class CampaignValidationError(ValueError):
    pass


class CampaignScopeError(CampaignValidationError):
    pass


UNAVAILABLE_NO_DENOMINATOR = "NO_DENOMINATOR"
UNAVAILABLE_NO_ATTRIBUTED_REVENUE = "NO_ATTRIBUTED_REVENUE"
UNAVAILABLE_MISSING_THRESHOLD = "MISSING_CONFIGURED_THRESHOLD"

_METRICS = {
    "spend": "bi.metric.marketing_spend.v1",
    "impressions": "bi.metric.marketing_impressions.v1",
    "clicks": "bi.metric.marketing_clicks.v1",
    "ctr": "bi.metric.marketing_click_through_rate.v1",
    "cpc": "bi.metric.marketing_cost_per_click.v1",
    "cpm": "bi.metric.marketing_cost_per_mille.v1",
    "conversions": "bi.metric.marketing_conversions.v1",
    "conversion_rate": "bi.metric.marketing_conversion_rate.v1",
    "attributed_revenue": "bi.metric.marketing_attributed_revenue.v1",
    "roas": "bi.metric.marketing_return_on_ad_spend.v1",
}
_PRECISION = 48


@dataclass(frozen=True)
class UnavailableCampaignEvidence:
    available: bool
    reason: str
    required_contract: str


@dataclass(frozen=True)
class CampaignPerformance:
    campaign_id: int
    name: str
    platform: str
    currency: str
    source_row_ids: tuple
    impressions: int
    reach: int
    clicks: int
    spend: Decimal
    reported_conversions: int
    reported_conversion_value: Decimal
    ctr: object
    cpc: object
    cpm: object
    conversion_rate: object
    attributed_orders: int
    attributed_revenue: object
    attributed_revenue_excluded_currencies: tuple
    roas: object
    attribution_model: str
    attribution_relationship_ids: tuple


@dataclass(frozen=True)
class CampaignAnalysis:
    business_id: int
    period_type: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    metric_date_start: datetime.date
    metric_date_end: datetime.date
    performances: tuple
    comparison_inputs: tuple
    low_performance_detection: UnavailableCampaignEvidence


@dataclass(frozen=True)
class CampaignMetricRecording:
    analysis: CampaignAnalysis
    snapshots: tuple


def _ratio(numerator, denominator):
    if denominator == 0:
        return metrics.UNAVAILABLE
    with localcontext() as context:
        context.prec = _PRECISION
        return Decimal(numerator) / Decimal(denominator)


def _scope(business_id, period_type, period_start, period_end):
    if isinstance(business_id, bool) or not isinstance(business_id, int) or not 0 < business_id < 2 ** 63:
        raise CampaignValidationError("business_id must be a positive 64-bit integer.")
    if period_type not in metrics.PERIOD_TYPES:
        raise CampaignValidationError(f"period_type must be one of {sorted(metrics.PERIOD_TYPES)}.")
    for value, name in ((period_start, "period_start"), (period_end, "period_end")):
        if not isinstance(value, datetime.datetime) or not timezone.is_aware(value):
            raise CampaignValidationError(f"{name} must be a timezone-aware datetime.")
    if period_start >= period_end:
        raise CampaignValidationError("period_start must be earlier than period_end.")
    if not models.Business.objects.filter(pk=business_id).exists():
        raise CampaignValidationError("Business does not exist.")
    return period_start.date(), period_end.date()


def _validate_row(row):
    values = (row.impressions, row.reach, row.clicks, row.conversions)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise CampaignValidationError(f"CampaignMetric {row.pk} contains a negative or invalid count.")
    for value, label in ((row.spend, "spend"), (row.conversion_value, "conversion_value")):
        if not isinstance(value, Decimal) or value < 0:
            raise CampaignValidationError(f"CampaignMetric {row.pk} has invalid {label}.")


def analyze_campaigns(*, business_id, period_type, period_start, period_end,
                      attribution_model, lookback_window,
                      comparison_start=None, comparison_end=None):
    """Return standardized §8 campaign performance for one explicit period."""
    date_start, date_end = _scope(business_id, period_type, period_start, period_end)
    if attribution_model not in attribution.SUPPORTED_MODELS:
        raise CampaignValidationError(
            f"attribution_model must be one of {sorted(attribution.SUPPORTED_MODELS)}."
        )
    # Validate the required caller-supplied window through T-006.
    attribution._parse_lookback(lookback_window)
    if (comparison_start is None) != (comparison_end is None):
        raise CampaignValidationError("comparison_start and comparison_end must be supplied together.")

    campaigns = list(models.Campaign.objects.filter(business_id=business_id).order_by("pk"))
    campaign_ids = [row.pk for row in campaigns]
    daily = list(models.CampaignMetric.objects.filter(
        campaign_id__in=campaign_ids,
        metric_date__gte=date_start,
        metric_date__lt=date_end,
    ).order_by("campaign_id", "metric_date", "pk"))
    by_campaign = {}
    for row in daily:
        _validate_row(row)
        by_campaign.setdefault(row.campaign_id, []).append(row)

    attributed = attribution.attribute_campaigns(
        business_id=business_id, period_type=period_type,
        period_start=period_start, period_end=period_end,
        lookback_window=lookback_window, model=attribution_model,
    )
    attributed_by_campaign = {row.campaign_id: row for row in attributed}
    performances = []
    for campaign in campaigns:
        rows = by_campaign.get(campaign.pk, ())
        if not isinstance(campaign.currency, str) or not campaign.currency.strip():
            raise CampaignValidationError(f"Campaign {campaign.pk} has no currency.")
        if rows:
            impressions = sum(row.impressions for row in rows)
            reach = sum(row.reach for row in rows)
            clicks = sum(row.clicks for row in rows)
            spend = sum((row.spend for row in rows), Decimal("0"))
            reported_conversions = sum(row.conversions for row in rows)
            reported_value = sum((row.conversion_value for row in rows), Decimal("0"))
            ctr = _ratio(clicks, impressions)
            cpc = _ratio(spend, clicks)
            cpm = _ratio(spend * Decimal("1000"), impressions)
            conversion_rate = _ratio(reported_conversions, clicks)
        else:
            impressions = reach = clicks = spend = metrics.UNAVAILABLE
            reported_conversions = reported_value = metrics.UNAVAILABLE
            ctr = cpc = cpm = conversion_rate = metrics.UNAVAILABLE
        summary = attributed_by_campaign.get(campaign.pk)
        revenue_pairs = () if summary is None else summary.attributed_revenue_by_currency
        matching = [value for code, value in revenue_pairs if code == campaign.currency]
        attributed_revenue = matching[0] if matching else metrics.UNAVAILABLE
        excluded = tuple((code, value) for code, value in revenue_pairs if code != campaign.currency)
        performances.append(CampaignPerformance(
            campaign_id=campaign.pk, name=campaign.name, platform=campaign.platform,
            currency=campaign.currency, source_row_ids=tuple(row.pk for row in rows),
            impressions=impressions, reach=reach, clicks=clicks, spend=spend,
            reported_conversions=reported_conversions,
            reported_conversion_value=reported_value,
            ctr=ctr, cpc=cpc, cpm=cpm, conversion_rate=conversion_rate,
            attributed_orders=0 if summary is None else summary.attributed_orders_count,
            attributed_revenue=attributed_revenue,
            attributed_revenue_excluded_currencies=excluded,
            roas=(metrics.UNAVAILABLE if attributed_revenue is metrics.UNAVAILABLE
                  or spend is metrics.UNAVAILABLE
                  else _ratio(attributed_revenue, spend)),
            attribution_model=attribution_model,
            attribution_relationship_ids=(() if summary is None else summary.evidence_relationship_ids),
        ))

    current = tuple((row.campaign_id, row.impressions, row.clicks, row.spend,
                     row.reported_conversions, row.attributed_revenue) for row in performances)
    comparison_inputs = (("CURRENT", period_start, period_end, current),)
    if comparison_start is not None:
        earlier = analyze_campaigns(
            business_id=business_id, period_type=period_type,
            period_start=comparison_start, period_end=comparison_end,
            attribution_model=attribution_model, lookback_window=lookback_window,
        )
        prior = tuple((row.campaign_id, row.impressions, row.clicks, row.spend,
                       row.reported_conversions, row.attributed_revenue)
                      for row in earlier.performances)
        comparison_inputs += (("COMPARISON", comparison_start, comparison_end, prior),)
    return CampaignAnalysis(
        business_id, period_type, period_start, period_end, date_start, date_end,
        tuple(performances), comparison_inputs,
        UnavailableCampaignEvidence(
            False, UNAVAILABLE_MISSING_THRESHOLD,
            "configured or historical low-performance expectation",
        ),
    )


def record_campaign_metrics(*, business_id, period_type, period_start, period_end,
                            attribution_model, lookback_window):
    """Record the ten existing marketing metric keys by CAMPAIGN dimension."""
    with transaction.atomic():
        analysis = analyze_campaigns(
            business_id=business_id, period_type=period_type,
            period_start=period_start, period_end=period_end,
            attribution_model=attribution_model, lookback_window=lookback_window,
        )
        writes = []
        for row in analysis.performances:
            inputs = {
                "service": "business_intelligence.campaign",
                "campaign_id": row.campaign_id,
                "source_campaign_metric_ids": list(row.source_row_ids),
                "currency": row.currency,
                "attribution_model": row.attribution_model,
                "attribution_relationship_ids": list(row.attribution_relationship_ids),
                "conversion_rate_denominator": "PLATFORM_REPORTED_CLICKS",
                "attributed_revenue_excluded_currencies": [
                    [code, str(value)] for code, value in row.attributed_revenue_excluded_currencies
                ],
            }
            values = {
                "spend": row.spend,
                "impressions": (metrics.UNAVAILABLE if row.impressions is metrics.UNAVAILABLE
                                else Decimal(row.impressions)),
                "clicks": (metrics.UNAVAILABLE if row.clicks is metrics.UNAVAILABLE
                           else Decimal(row.clicks)),
                "ctr": row.ctr, "cpc": row.cpc,
                "cpm": row.cpm,
                "conversions": (metrics.UNAVAILABLE
                                if row.reported_conversions is metrics.UNAVAILABLE
                                else Decimal(row.reported_conversions)),
                "conversion_rate": row.conversion_rate,
                "attributed_revenue": row.attributed_revenue, "roas": row.roas,
            }
            for name, value in values.items():
                metric_key = _METRICS[name]
                variant = "platform_daily"
                if name in {"attributed_revenue", "roas"}:
                    variant = f"{attribution_model.lower()}_attribution"
                write = metrics.record_metric_snapshot(
                    business_id=business_id, metric_key=metric_key, value=value,
                    period_type=period_type, period_start=period_start,
                    period_end=period_end, dimension_type="CAMPAIGN",
                    dimension_value=str(row.campaign_id),
                    calculation_rule=f"{metric_key}.{variant}", inputs=inputs,
                )
                writes.append((row.campaign_id, name, write))
        return CampaignMetricRecording(analysis, tuple(writes))


__all__ = [
    "CampaignAnalysis", "CampaignMetricRecording", "CampaignPerformance",
    "CampaignScopeError", "CampaignValidationError", "UnavailableCampaignEvidence",
    "analyze_campaigns", "record_campaign_metrics",
]
