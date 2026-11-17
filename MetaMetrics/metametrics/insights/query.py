"""An Insights query."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from metametrics.exceptions import InvalidInputError, UnsupportedMetricError
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.query.filters import Filter

__all__ = ["InsightsQuery"]


@dataclass(frozen=True, slots=True)
class InsightsQuery:
    """The metrics, period, and filters of an Insights request."""

    level: InsightsLevel
    date_range: DateRange
    metrics: tuple[Metric, ...]
    entity_id: str | None = None
    daily: bool = False
    filters: tuple[Filter, ...] = field(default_factory=tuple)
    limit: int | None = None
    include_ad_set_configuration: bool = True

    def __init__(
        self,
        level: InsightsLevel,
        date_range: DateRange,
        metrics: Sequence[Metric],
        entity_id: str | None = None,
        daily: bool = False,
        filters: Sequence[Filter] = (),
        limit: int | None = None,
        include_ad_set_configuration: bool = True,
    ) -> None:
        if not metrics:
            raise InvalidInputError("At least one Insights metric must be selected.")

        unique_metrics: dict[str, Metric] = {}

        for metric in metrics:
            if not isinstance(metric, Metric):
                raise UnsupportedMetricError("Insights metrics must use the Metric enum.")

            unique_metrics[metric.value] = metric

        for filter_ in filters:
            if not isinstance(filter_, Filter):
                raise InvalidInputError("Insights filters must be Filter instances.")

        if entity_id is not None and entity_id.strip() == "":
            raise InvalidInputError("Insights entity ID must not be empty.")

        if limit is not None and limit < 1:
            raise InvalidInputError("Insights query limit must be greater than zero.")

        object.__setattr__(self, "level", level)
        object.__setattr__(self, "date_range", date_range)
        object.__setattr__(self, "metrics", tuple(unique_metrics.values()))
        object.__setattr__(self, "entity_id", entity_id)
        object.__setattr__(self, "daily", daily)
        object.__setattr__(self, "filters", tuple(filters))
        object.__setattr__(self, "limit", limit)
        object.__setattr__(self, "include_ad_set_configuration", include_ad_set_configuration)
