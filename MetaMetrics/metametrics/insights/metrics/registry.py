"""The catalogue of supported metrics."""

from __future__ import annotations

from collections.abc import Sequence

from metametrics.exceptions import UnsupportedMetricError
from metametrics.insights.metrics.definition import MetricDefinition
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.types import MetricAggregation, MetricType, MetricUnit

__all__ = ["MetricRegistry"]


class MetricRegistry:
    """Resolves metric dependencies and validates the metric catalogue.

    The registry is the single source of truth for which Meta fields a metric
    needs and which other metrics it is computed from.
    """

    def __init__(self, definitions: Sequence[MetricDefinition] | None = None) -> None:
        catalogue: dict[str, MetricDefinition] = {}

        for definition in definitions if definitions is not None else self.default_definitions():
            if not isinstance(definition, MetricDefinition):
                raise UnsupportedMetricError("Metric definitions must use MetricDefinition instances.")

            name = definition.metric.value
            if name in catalogue:
                raise UnsupportedMetricError(f'Duplicate metric definition "{name}".')

            catalogue[name] = definition

        self._definitions = catalogue
        self._validate_catalogue()

    @staticmethod
    def default_definitions() -> list[MetricDefinition]:
        """The metric catalogue shipped with the library."""
        return [
            MetricDefinition(
                Metric.SPEND, MetricType.DIRECT, MetricUnit.MONEY, MetricAggregation.SUM, ("spend",)
            ),
            MetricDefinition(
                Metric.PURCHASES, MetricType.ACTION, MetricUnit.COUNT, MetricAggregation.SUM, ("actions",)
            ),
            MetricDefinition(
                Metric.COST_PER_PURCHASE,
                MetricType.DERIVED,
                MetricUnit.MONEY,
                MetricAggregation.RECALCULATE,
                dependencies=(Metric.SPEND, Metric.PURCHASES),
            ),
            MetricDefinition(
                Metric.PURCHASE_VALUE,
                MetricType.ACTION_VALUE,
                MetricUnit.MONEY,
                MetricAggregation.SUM,
                ("action_values",),
            ),
            MetricDefinition(
                Metric.ROAS,
                MetricType.DERIVED,
                MetricUnit.RATIO,
                MetricAggregation.RECALCULATE,
                dependencies=(Metric.SPEND, Metric.PURCHASE_VALUE),
            ),
            MetricDefinition(
                Metric.IMPRESSIONS,
                MetricType.DIRECT,
                MetricUnit.COUNT,
                MetricAggregation.SUM,
                ("impressions",),
            ),
            MetricDefinition(
                Metric.REACH, MetricType.DIRECT, MetricUnit.COUNT, MetricAggregation.META_ONLY, ("reach",)
            ),
            MetricDefinition(
                Metric.CLICKS, MetricType.DIRECT, MetricUnit.COUNT, MetricAggregation.SUM, ("clicks",)
            ),
            MetricDefinition(
                Metric.LINK_CLICKS,
                MetricType.DIRECT,
                MetricUnit.COUNT,
                MetricAggregation.SUM,
                ("inline_link_clicks",),
            ),
            MetricDefinition(
                Metric.CPC,
                MetricType.DERIVED,
                MetricUnit.MONEY,
                MetricAggregation.RECALCULATE,
                dependencies=(Metric.SPEND, Metric.CLICKS),
            ),
            MetricDefinition(
                Metric.CTR,
                MetricType.DERIVED,
                MetricUnit.PERCENT,
                MetricAggregation.RECALCULATE,
                dependencies=(Metric.CLICKS, Metric.IMPRESSIONS),
            ),
            MetricDefinition(
                Metric.CPM,
                MetricType.DERIVED,
                MetricUnit.MONEY,
                MetricAggregation.RECALCULATE,
                dependencies=(Metric.SPEND, Metric.IMPRESSIONS),
            ),
        ]

    def supports(self, metric: Metric | str) -> bool:
        """Whether the metric is part of the catalogue."""
        name = metric.value if isinstance(metric, Metric) else metric

        return name in self._definitions

    def from_name(self, name: str) -> Metric:
        """Return the metric with the given name.

        Raises:
            UnsupportedMetricError: when the name is unknown or unsupported.
        """
        try:
            metric = Metric(name)
        except ValueError as error:
            raise UnsupportedMetricError(f'Unsupported metric "{name}".') from error

        if not self.supports(metric):
            raise UnsupportedMetricError(f'Unsupported metric "{name}".')

        return metric

    def definition(self, metric: Metric) -> MetricDefinition:
        """Return the definition of a metric.

        Raises:
            UnsupportedMetricError: when the metric is not part of the catalogue.
        """
        definition = self._definitions.get(metric.value)

        if definition is None:
            raise UnsupportedMetricError(f'Unsupported metric "{metric.value}".')

        return definition

    def definitions(self) -> list[MetricDefinition]:
        """Return every definition of the catalogue."""
        return list(self._definitions.values())

    def foundational_metrics(self, metrics: Sequence[Metric]) -> list[Metric]:
        """Return the metrics that must be fetched to compute the requested ones."""
        resolved: dict[str, Metric] = {}

        for metric in metrics:
            self._resolve(self._metric(metric), resolved, {})

        return list(resolved.values())

    def meta_fields(self, metrics: Sequence[Metric]) -> list[str]:
        """Return the Meta fields that must be requested for the given metrics."""
        fields: dict[str, str] = {}

        for metric in self.foundational_metrics(metrics):
            for meta_field in self.definition(metric).meta_fields:
                fields.setdefault(meta_field, meta_field)

        return list(fields.values())

    def dependencies(self, metric: Metric) -> list[Metric]:
        """Return the metrics a metric is computed from."""
        return list(self.definition(metric).dependencies)

    def type(self, metric: Metric) -> MetricType:
        """Return the type of a metric."""
        return self.definition(metric).type

    def is_derived(self, metric: Metric) -> bool:
        """Whether a metric is computed from other metrics."""
        return self.definition(metric).is_derived

    def unit(self, metric: Metric) -> MetricUnit:
        """Return the unit of a metric."""
        return self.definition(metric).unit

    def aggregation(self, metric: Metric) -> MetricAggregation:
        """Return the aggregation behaviour of a metric."""
        return self.definition(metric).aggregation

    def requires_actions(self, metric: Metric) -> bool:
        """Whether a metric (or one of its dependencies) needs the ``actions`` payload."""
        return any(
            self.definition(foundational).requires_actions
            for foundational in self.foundational_metrics((metric,))
        )

    def requires_action_values(self, metric: Metric) -> bool:
        """Whether a metric (or one of its dependencies) needs the ``action_values`` payload."""
        return any(
            self.definition(foundational).requires_action_values
            for foundational in self.foundational_metrics((metric,))
        )

    def source_field(self, metric: Metric) -> str | None:
        """Return the Meta field a metric is read from."""
        meta_fields = self.definition(metric).meta_fields

        return meta_fields[0] if meta_fields else None

    def _resolve(self, metric: Metric, resolved: dict[str, Metric], resolving: dict[str, bool]) -> None:
        if metric.value in resolved:
            return

        if resolving.get(metric.value):
            raise UnsupportedMetricError(f'Circular metric dependency detected for "{metric.value}".')

        resolving[metric.value] = True

        for dependency in self.dependencies(metric):
            # PHP passes ``$resolving`` by value, so a sibling branch never sees
            # the keys another branch added. Copying keeps that behaviour.
            self._resolve(dependency, resolved, dict(resolving))

        if not self.is_derived(metric):
            resolved[metric.value] = metric

    @staticmethod
    def _metric(metric: object) -> Metric:
        if not isinstance(metric, Metric):
            raise UnsupportedMetricError("Insights metrics must use a supported Metric enum.")

        return metric

    def _validate_catalogue(self) -> None:
        for metric in Metric:
            if not self.supports(metric):
                raise UnsupportedMetricError(f'Metric catalog is missing definition "{metric.value}".')

        if len(self._definitions) != len(Metric):
            raise UnsupportedMetricError("Metric catalog contains unsupported definitions.")

        for metric in Metric:
            for dependency in self.dependencies(metric):
                if not self.supports(dependency):
                    raise UnsupportedMetricError(f'Metric "{metric.value}" depends on an unsupported metric.')

            self._resolve(metric, {}, {})
