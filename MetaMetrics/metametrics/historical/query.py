"""Specification for historical analysis queries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from metametrics.exceptions import InvalidInputError, UnsupportedMetricError
from metametrics.historical.level import HistoricalLevel
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.metrics.metric import Metric
from metametrics.query.filters import Filter

__all__ = ["HistoricalQuery"]


@dataclass(frozen=True, slots=True)
class HistoricalQuery:
    """Historical analysis query parameters."""

    level: HistoricalLevel
    date_range: DateRange
    parent_id: str | None = None
    metrics: Sequence[Metric] = field(default_factory=tuple)
    daily: bool = False
    filters: Sequence[Filter] = field(default_factory=tuple)
    limit: int | None = None

    def __post_init__(self) -> None:
        if self.parent_id is not None and not self.parent_id.strip():
            raise InvalidInputError("Historical parent scope ID must not be empty.")

        if self.limit is not None and self.limit < 1:
            raise InvalidInputError("Historical query limit must be greater than zero.")

        unique_metrics: dict[str, Metric] = {}
        for m in self.metrics:
            if not isinstance(m, Metric):
                raise UnsupportedMetricError("Historical metrics must use the Metric enum.")
            unique_metrics[m.value] = m

        for f in self.filters:
            if not isinstance(f, Filter):
                raise InvalidInputError("Historical filters must be Filter instances.")

        object.__setattr__(self, "metrics", tuple(unique_metrics.values()))
        object.__setattr__(self, "filters", tuple(self.filters))
