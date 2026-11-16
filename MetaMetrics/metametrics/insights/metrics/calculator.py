"""Computation of derived metrics."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from metametrics.exceptions import InvalidInputError
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.registry import MetricRegistry

__all__ = ["MetricCalculator"]


class MetricCalculator:
    """Computes derived metrics from foundational metric values."""

    def __init__(self, registry: MetricRegistry | None = None) -> None:
        self.registry = registry or MetricRegistry()

    def calculate_all(
        self,
        requested: Sequence[Metric],
        foundational: Mapping[str, float | None],
    ) -> dict[str, float | None]:
        """Compute every requested metric from the foundational values."""
        return {metric.value: self.calculate(metric, foundational) for metric in requested}

    def calculate(self, metric: Metric, values: Mapping[str, float | None]) -> float | None:
        """Compute one metric from the foundational values."""
        self.registry.definition(metric)

        if not self.registry.is_derived(metric):
            return self._value(values, metric)

        if metric == Metric.COST_PER_PURCHASE:
            return self._divide(self._value(values, Metric.SPEND), self._value(values, Metric.PURCHASES))

        if metric == Metric.ROAS:
            return self._divide(self._value(values, Metric.PURCHASE_VALUE), self._value(values, Metric.SPEND))

        if metric == Metric.CPC:
            return self._divide(self._value(values, Metric.SPEND), self._value(values, Metric.CLICKS))

        if metric == Metric.CTR:
            ratio = self._divide(self._value(values, Metric.CLICKS), self._value(values, Metric.IMPRESSIONS))
            return self._multiply(ratio, 100.0)

        if metric == Metric.CPM:
            ratio = self._divide(self._value(values, Metric.SPEND), self._value(values, Metric.IMPRESSIONS))
            return self._multiply(ratio, 1000.0)

        return None

    @staticmethod
    def _value(values: Mapping[str, float | None], metric: Metric) -> float | None:
        if metric.value not in values or values[metric.value] is None:
            return None

        value = values[metric.value]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidInputError(f'Normalized metric "{metric.value}" must be a finite number or null.')

        number = float(value)
        if not math.isfinite(number):
            raise InvalidInputError(f'Normalized metric "{metric.value}" must be a finite number or null.')

        return number

    @staticmethod
    def _divide(numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator is None or denominator == 0.0:
            return None

        result = numerator / denominator
        if not math.isfinite(result):
            raise InvalidInputError("Derived metric calculation produced a non-finite value.")

        return result

    @staticmethod
    def _multiply(value: float | None, multiplier: float) -> float | None:
        if value is None:
            return None

        result = value * multiplier
        if not math.isfinite(result):
            raise InvalidInputError("Derived metric calculation produced a non-finite value.")

        return result
