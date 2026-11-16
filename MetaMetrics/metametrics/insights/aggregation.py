"""Aggregation of daily Insights rows into one reporting period."""

from __future__ import annotations

import math
from collections.abc import Sequence

from metametrics.exceptions import InvalidInputError, UnsupportedMetricError
from metametrics.insights.aggregation_result import MetricAggregationResult
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.metrics.calculator import MetricCalculator
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.metrics.types import MetricAggregation

__all__ = ["MetricAggregator"]


class MetricAggregator:
    """Aggregates several reporting periods of one entity into a single result."""

    def __init__(
        self,
        registry: MetricRegistry | None = None,
        calculator: MetricCalculator | None = None,
    ) -> None:
        self.registry = registry or MetricRegistry()
        self.calculator = calculator or MetricCalculator(registry=self.registry)

    def aggregate(
        self,
        rows: Sequence[InsightsDTO],
        requested_metrics: Sequence[Metric],
    ) -> MetricAggregationResult | None:
        """Aggregate the rows of one entity into a single result.

        Returns:
            ``None`` when there are no rows to aggregate.
        """
        if not requested_metrics:
            raise InvalidInputError("Metric aggregation requires at least one requested metric.")

        for metric in requested_metrics:
            if not isinstance(metric, Metric):
                raise UnsupportedMetricError("Aggregated metrics must use the Metric enum.")

        if not rows:
            return None

        for row in rows:
            if not isinstance(row, InsightsDTO):
                raise InvalidInputError("Metric aggregation rows must be InsightsDTO instances.")

        ordered = sorted(rows, key=lambda row: (row.date_start, row.date_stop))

        self._validate_rows(ordered)

        foundational: dict[str, float | None] = {}

        for metric in self.registry.foundational_metrics(requested_metrics):
            aggregation = self.registry.aggregation(metric)

            if aggregation == MetricAggregation.SUM:
                foundational[metric.value] = self._sum(ordered, metric)
            elif aggregation == MetricAggregation.META_ONLY:
                foundational[metric.value] = self._aggregate_meta_only(ordered, metric)
            else:
                raise InvalidInputError("Derived metrics cannot be aggregated as foundational values.")

        first = ordered[0]
        last = ordered[-1]

        return MetricAggregationResult(
            entity_id=first.entity_id,
            level=first.level,
            date_range=DateRange(first.date_start, last.date_stop),
            metrics=self.calculator.calculate_all(requested_metrics, foundational),
            currency=first.currency,
        )

    @staticmethod
    def _validate_rows(rows: Sequence[InsightsDTO]) -> None:
        first = rows[0]
        previous: InsightsDTO | None = None

        for row in rows:
            if row.currency != first.currency:
                raise InvalidInputError("Metric aggregation rows must share one currency.")

            if row.entity_id != first.entity_id or row.level != first.level:
                raise InvalidInputError("Metric aggregation rows must represent one entity and level.")

            if previous is not None and row.date_start <= previous.date_stop:
                raise InvalidInputError(
                    "Metric aggregation rows must not have overlapping reporting periods."
                )

            previous = row

    @staticmethod
    def _sum(rows: Sequence[InsightsDTO], metric: Metric) -> float | None:
        total = 0.0

        for row in rows:
            value = row.foundational_metric(metric)

            if value is None:
                return None

            total += value

            if not math.isfinite(total):
                raise InvalidInputError("Metric aggregation produced a non-finite total.")

        return total

    @staticmethod
    def _aggregate_meta_only(rows: Sequence[InsightsDTO], metric: Metric) -> float | None:
        return rows[0].foundational_metric(metric) if len(rows) == 1 else None
