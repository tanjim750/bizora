"""The result of aggregating several Insights reporting periods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from metametrics.insights.date_range.range import DateRange
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric

__all__ = ["MetricAggregationResult"]


@dataclass(frozen=True, slots=True)
class MetricAggregationResult:
    """One entity's metrics across a whole reporting period."""

    entity_id: str
    level: InsightsLevel
    date_range: DateRange
    metrics: dict[str, float | None] = field(default_factory=dict)
    currency: str | None = None

    @property
    def date_start(self) -> str:
        """The first day of the aggregated period."""
        return self.date_range.since

    @property
    def date_stop(self) -> str:
        """The last day of the aggregated period."""
        return self.date_range.until

    def metric(self, metric: Metric) -> float | None:
        """Return the value of a metric, or ``None`` when it is unavailable."""
        return self.metrics.get(metric.value)

    def to_dict(self) -> dict[str, Any]:
        """Render the result as a plain dictionary."""
        payload: dict[str, Any] = {
            "entity_id": self.entity_id,
            "level": self.level.value,
            "currency": self.currency,
            "date_start": self.date_start,
            "date_stop": self.date_stop,
        }
        payload.update(self.metrics)

        return payload
