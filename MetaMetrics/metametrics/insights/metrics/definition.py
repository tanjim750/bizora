"""The definition of a single metric."""

from __future__ import annotations

import re
from dataclasses import dataclass

from metametrics.exceptions import UnsupportedMetricError
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.types import MetricAggregation, MetricType, MetricUnit

__all__ = ["MetricDefinition"]

_META_FIELD_PATTERN: re.Pattern[str] = re.compile(r"\A[a-z][a-z0-9_]*\Z")


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """How one metric is sourced, computed, and aggregated."""

    metric: Metric
    type: MetricType
    unit: MetricUnit
    aggregation: MetricAggregation
    meta_fields: tuple[str, ...] = ()
    dependencies: tuple[Metric, ...] = ()

    def __init__(
        self,
        metric: Metric,
        type: MetricType,
        unit: MetricUnit,
        aggregation: MetricAggregation,
        meta_fields: tuple[str, ...] | list[str] = (),
        dependencies: tuple[Metric, ...] | list[Metric] = (),
    ) -> None:
        fields = tuple(meta_fields)
        resolved_dependencies = tuple(dependencies)

        if len(fields) != len(set(fields)):
            raise UnsupportedMetricError(f'Metric "{metric.value}" contains duplicate Meta fields.')

        for meta_field in fields:
            if not isinstance(meta_field, str) or not _META_FIELD_PATTERN.match(meta_field):
                raise UnsupportedMetricError(f'Metric "{metric.value}" contains an invalid Meta field.')

        for dependency in resolved_dependencies:
            if not isinstance(dependency, Metric):
                raise UnsupportedMetricError(f'Metric "{metric.value}" contains an invalid dependency.')

        if len(resolved_dependencies) != len({dependency.value for dependency in resolved_dependencies}):
            raise UnsupportedMetricError(f'Metric "{metric.value}" contains duplicate dependencies.')

        is_derived = type == MetricType.DERIVED

        if is_derived and (fields or not resolved_dependencies):
            raise UnsupportedMetricError(
                f'Derived metric "{metric.value}" requires dependencies and no direct Meta fields.'
            )

        if not is_derived and (not fields or resolved_dependencies):
            raise UnsupportedMetricError(
                f'Foundational metric "{metric.value}" requires Meta fields and no dependencies.'
            )

        if is_derived != (aggregation == MetricAggregation.RECALCULATE):
            raise UnsupportedMetricError(
                f'Metric "{metric.value}" contains incompatible type and aggregation semantics.'
            )

        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "type", type)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "aggregation", aggregation)
        object.__setattr__(self, "meta_fields", fields)
        object.__setattr__(self, "dependencies", resolved_dependencies)

    @property
    def is_derived(self) -> bool:
        """Whether the metric is computed from other metrics."""
        return self.type == MetricType.DERIVED

    @property
    def requires_actions(self) -> bool:
        """Whether the metric is sourced from the ``actions`` payload."""
        return self.type == MetricType.ACTION

    @property
    def requires_action_values(self) -> bool:
        """Whether the metric is sourced from the ``action_values`` payload."""
        return self.type == MetricType.ACTION_VALUE
