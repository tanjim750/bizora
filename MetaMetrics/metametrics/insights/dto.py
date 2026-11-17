"""The Insights data transfer object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from metametrics.insights.date_range.range import DateRange
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.raw_data import InsightsRawData

__all__ = ["InsightsDTO"]


@dataclass(frozen=True, slots=True)
class InsightsDTO:
    """One normalised row of Meta performance data."""

    entity_id: str
    entity_name: str | None
    level: InsightsLevel
    campaign_id: str | None
    ad_set_id: str | None
    ad_id: str | None
    date_range: DateRange
    metrics: dict[str, float | None] = field(default_factory=dict)
    raw_data: InsightsRawData = field(default_factory=InsightsRawData)
    foundational_metrics: dict[str, float | None] = field(default_factory=dict)
    currency: str | None = None

    @property
    def date_start(self) -> str:
        """The first day of the reporting period."""
        return self.date_range.since

    @property
    def date_stop(self) -> str:
        """The last day of the reporting period."""
        return self.date_range.until

    def has_metric(self, metric: Metric) -> bool:
        """Whether the row carries a value for the metric."""
        return metric.value in self.metrics

    def metric(self, metric: Metric) -> float | None:
        """Return the value of a metric, or ``None`` when it is unavailable."""
        return self.metrics.get(metric.value)

    def foundational_metric(self, metric: Metric) -> float | None:
        """Return the value of a foundational metric."""
        return self.foundational_metrics.get(metric.value)

    def to_dict(self, include_currency: bool = True) -> dict[str, Any]:
        """Render the row as a plain dictionary."""
        payload: dict[str, Any] = {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "level": self.level.value,
        }

        if include_currency:
            payload["currency"] = self.currency

        payload.update(
            {
                "campaign_id": self.campaign_id,
                "adset_id": self.ad_set_id,
                "ad_id": self.ad_id,
                "date_start": self.date_start,
                "date_stop": self.date_stop,
            }
        )
        payload.update(self.metrics)

        return payload

    @property
    def spend(self) -> float | None:
        """The spend of the row."""
        return self.metric(Metric.SPEND)

    @property
    def purchases(self) -> float | None:
        """The purchase count of the row."""
        return self.metric(Metric.PURCHASES)

    @property
    def cost_per_purchase(self) -> float | None:
        """The cost per purchase of the row."""
        return self.metric(Metric.COST_PER_PURCHASE)

    @property
    def purchase_value(self) -> float | None:
        """The purchase value of the row."""
        return self.metric(Metric.PURCHASE_VALUE)

    @property
    def roas(self) -> float | None:
        """The return on ad spend of the row."""
        return self.metric(Metric.ROAS)

    @property
    def impressions(self) -> float | None:
        """The impressions of the row."""
        return self.metric(Metric.IMPRESSIONS)

    @property
    def reach(self) -> float | None:
        """The reach of the row."""
        return self.metric(Metric.REACH)

    @property
    def clicks(self) -> float | None:
        """The clicks of the row."""
        return self.metric(Metric.CLICKS)

    @property
    def link_clicks(self) -> float | None:
        """The link clicks of the row."""
        return self.metric(Metric.LINK_CLICKS)

    @property
    def cpc(self) -> float | None:
        """The cost per click of the row."""
        return self.metric(Metric.CPC)

    @property
    def ctr(self) -> float | None:
        """The click-through rate of the row."""
        return self.metric(Metric.CTR)

    @property
    def cpm(self) -> float | None:
        """The cost per mille of the row."""
        return self.metric(Metric.CPM)
