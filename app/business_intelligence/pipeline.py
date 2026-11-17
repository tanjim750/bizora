"""Run the existing Business Intelligence metric calculators for one business and period (BI-03).

Nothing in the codebase called the calculators, so metric snapshots stayed empty. The
Intelligence Processing Flow (docs/implementations/features/business-intelligence.md)
places "Metric Snapshots" and the per-domain analyses between relationships and anomaly
detection; ``run_metric_calculators`` runs exactly those existing recorders:

* metric registry synchronisation (the recorders require a synchronised registry);
* sales, revenue, support, delivery, customer and website metrics;
* campaign metrics only when the caller names an attribution model and a lookback
  window, because the specification defines no default for either.

It adds no calculation and no rule. Anomaly detection, Business Facts and Business Issues
are not touched: their rules are caller-supplied in the existing services. Each recorder
runs in its own savepoint, so one failure is reported in its step and never rolls back the
others. It is driven by the ``run_intelligence`` management command.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any

from django.db import DatabaseError, transaction
from django.utils import timezone

from app.business_intelligence import (
    campaign,
    customer_product,
    delivery,
    metrics,
    revenue,
    support,
    website,
)

logger = logging.getLogger(__name__)

STEP_COMPLETED = "COMPLETED"
STEP_SKIPPED = "SKIPPED"
STEP_FAILED = "FAILED"


@dataclass
class StepResult:
    name: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)
    error: dict[str, str] | None = None


def month_bounds(moment: datetime.datetime) -> tuple[datetime.datetime, datetime.datetime]:
    """The UTC calendar month containing ``moment`` as a half-open [start, end) pair."""
    moment = moment.astimezone(datetime.timezone.utc)
    start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start.replace(year=start.year + 1, month=1) if start.month == 12
           else start.replace(month=start.month + 1))
    return start, end


def default_period(now: datetime.datetime | None = None) -> tuple[str, datetime.datetime, datetime.datetime]:
    """The current UTC calendar month, the period used when the caller names none."""
    start, end = month_bounds(now or timezone.now())
    return "MONTH", start, end


def _calculators(scope: dict[str, Any], attribution_model, lookback_window):
    """(name, callable) pairs; a callable is None when it needs a decision the caller did not make."""
    def delivery_all():
        delivery.calculate_delivery_outcome_rates(**scope)
        delivery.calculate_delivery_time(**scope)
        delivery.calculate_delivery_cost(**scope)

    def campaigns():
        return campaign.record_campaign_metrics(
            **scope, attribution_model=attribution_model, lookback_window=lookback_window,
        )

    return (
        ("sales_metrics", lambda: revenue.record_sales_metrics(**scope)),
        ("revenue_metrics", lambda: revenue.record_revenue_metrics(**scope)),
        ("support_metrics", lambda: support.record_support_metrics(**scope)),
        ("delivery_metrics", delivery_all),
        ("customer_metrics", lambda: customer_product.record_customer_metrics(**scope)),
        ("website_metrics", lambda: website.record_website_metrics(**scope)),
        ("campaign_metrics", campaigns if (attribution_model and lookback_window) else None),
    )


def _run_step(name, fn) -> StepResult:
    if fn is None:
        return StepResult(name, STEP_SKIPPED, {
            "reason": "attribution_model and lookback_window were not supplied; the specification defines no default."})
    try:
        with transaction.atomic():
            fn()
    except (ValueError, DatabaseError) as exc:
        logger.warning("Metric step %s failed: %s", name, exc)
        return StepResult(name, STEP_FAILED, error={"code": type(exc).__name__, "detail": str(exc)[:300]})
    return StepResult(name, STEP_COMPLETED)


def run_metric_calculators(*, business_id: int, period_type: str, period_start: datetime.datetime,
                           period_end: datetime.datetime, attribution_model: str | None = None,
                           lookback_window: Any = None) -> list[StepResult]:
    """Sync the metric registry and run every existing recorder for the period; performs no authorization.

    Never raises for a failing step: each failure is returned in its ``StepResult``.
    """
    steps = [_run_step("metric_registry", lambda: metrics.sync_metric_registry(business_id=business_id))]
    scope = {"business_id": business_id, "period_type": period_type,
             "period_start": period_start, "period_end": period_end}
    for name, fn in _calculators(scope, attribution_model, lookback_window):
        steps.append(_run_step(name, fn))
    return steps


__all__ = [
    "STEP_COMPLETED",
    "STEP_FAILED",
    "STEP_SKIPPED",
    "StepResult",
    "default_period",
    "month_bounds",
    "run_metric_calculators",
]
