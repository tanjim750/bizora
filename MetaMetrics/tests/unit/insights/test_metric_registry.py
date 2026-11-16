"""Tests for the metric catalogue.

Ported from ``tests/Unit/Insights/MetricRegistryTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.exceptions import UnsupportedMetricError
from metametrics.insights.metrics.definition import MetricDefinition
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.metrics.types import MetricAggregation, MetricType, MetricUnit

EXPECTED: dict[Metric, tuple[MetricType, MetricUnit, MetricAggregation, list[str], list[Metric]]] = {
    Metric.SPEND: (MetricType.DIRECT, MetricUnit.MONEY, MetricAggregation.SUM, ["spend"], []),
    Metric.PURCHASES: (MetricType.ACTION, MetricUnit.COUNT, MetricAggregation.SUM, ["actions"], []),
    Metric.COST_PER_PURCHASE: (
        MetricType.DERIVED,
        MetricUnit.MONEY,
        MetricAggregation.RECALCULATE,
        [],
        [Metric.SPEND, Metric.PURCHASES],
    ),
    Metric.PURCHASE_VALUE: (
        MetricType.ACTION_VALUE,
        MetricUnit.MONEY,
        MetricAggregation.SUM,
        ["action_values"],
        [],
    ),
    Metric.ROAS: (
        MetricType.DERIVED,
        MetricUnit.RATIO,
        MetricAggregation.RECALCULATE,
        [],
        [Metric.SPEND, Metric.PURCHASE_VALUE],
    ),
    Metric.IMPRESSIONS: (
        MetricType.DIRECT,
        MetricUnit.COUNT,
        MetricAggregation.SUM,
        ["impressions"],
        [],
    ),
    Metric.REACH: (MetricType.DIRECT, MetricUnit.COUNT, MetricAggregation.META_ONLY, ["reach"], []),
    Metric.CLICKS: (MetricType.DIRECT, MetricUnit.COUNT, MetricAggregation.SUM, ["clicks"], []),
    Metric.LINK_CLICKS: (
        MetricType.DIRECT,
        MetricUnit.COUNT,
        MetricAggregation.SUM,
        ["inline_link_clicks"],
        [],
    ),
    Metric.CPC: (
        MetricType.DERIVED,
        MetricUnit.MONEY,
        MetricAggregation.RECALCULATE,
        [],
        [Metric.SPEND, Metric.CLICKS],
    ),
    Metric.CTR: (
        MetricType.DERIVED,
        MetricUnit.PERCENT,
        MetricAggregation.RECALCULATE,
        [],
        [Metric.CLICKS, Metric.IMPRESSIONS],
    ),
    Metric.CPM: (
        MetricType.DERIVED,
        MetricUnit.MONEY,
        MetricAggregation.RECALCULATE,
        [],
        [Metric.SPEND, Metric.IMPRESSIONS],
    ),
}


def test_every_metric_has_typed_validated_metadata() -> None:
    registry = MetricRegistry()

    assert len(registry.definitions()) == len(Metric)

    for metric in Metric:
        definition = registry.definition(metric)
        metric_type, unit, aggregation, fields, dependencies = EXPECTED[metric]

        assert definition.metric == metric
        assert definition.type == metric_type
        assert definition.unit == unit
        assert definition.aggregation == aggregation
        assert list(definition.meta_fields) == fields
        assert list(definition.dependencies) == dependencies

    assert registry.requires_actions(Metric.PURCHASES) is True
    assert registry.requires_actions(Metric.COST_PER_PURCHASE) is True
    assert registry.requires_action_values(Metric.PURCHASE_VALUE) is True
    assert registry.requires_action_values(Metric.ROAS) is True
    assert registry.requires_actions(Metric.ROAS) is False
    assert registry.requires_action_values(Metric.COST_PER_PURCHASE) is False


def test_the_string_boundary_rejects_unsupported_metrics() -> None:
    registry = MetricRegistry()

    assert registry.from_name("roas") == Metric.ROAS

    with pytest.raises(UnsupportedMetricError, match="not_a_metric"):
        registry.from_name("not_a_metric")


def test_duplicate_definitions_are_rejected() -> None:
    definitions = MetricRegistry().definitions()
    definitions.append(definitions[0])

    with pytest.raises(UnsupportedMetricError, match="Duplicate metric definition"):
        MetricRegistry(definitions)


def test_missing_definitions_are_rejected() -> None:
    definitions = MetricRegistry().definitions()
    definitions.pop()

    with pytest.raises(UnsupportedMetricError, match="missing definition"):
        MetricRegistry(definitions)


def test_circular_dependencies_are_rejected() -> None:
    definitions = [
        MetricDefinition(
            Metric.SPEND,
            MetricType.DERIVED,
            MetricUnit.MONEY,
            MetricAggregation.RECALCULATE,
            dependencies=(Metric.CPC,),
        )
        if definition.metric == Metric.SPEND
        else definition
        for definition in MetricRegistry().definitions()
    ]

    with pytest.raises(UnsupportedMetricError, match="Circular metric dependency"):
        MetricRegistry(definitions)


def test_malformed_definitions_are_rejected() -> None:
    with pytest.raises(UnsupportedMetricError):
        MetricDefinition(
            Metric.CTR,
            MetricType.DERIVED,
            MetricUnit.PERCENT,
            MetricAggregation.RECALCULATE,
            meta_fields=("ctr",),
            dependencies=(Metric.CLICKS, Metric.IMPRESSIONS),
        )


def test_a_derived_metric_without_dependencies_is_rejected() -> None:
    with pytest.raises(UnsupportedMetricError, match="requires dependencies"):
        MetricDefinition(Metric.CTR, MetricType.DERIVED, MetricUnit.PERCENT, MetricAggregation.RECALCULATE)


def test_a_foundational_metric_with_dependencies_is_rejected() -> None:
    with pytest.raises(UnsupportedMetricError, match="requires Meta fields"):
        MetricDefinition(
            Metric.CLICKS,
            MetricType.DIRECT,
            MetricUnit.COUNT,
            MetricAggregation.SUM,
            dependencies=(Metric.IMPRESSIONS,),
        )


def test_duplicate_meta_fields_are_rejected() -> None:
    with pytest.raises(UnsupportedMetricError, match="duplicate Meta fields"):
        MetricDefinition(
            Metric.CLICKS,
            MetricType.DIRECT,
            MetricUnit.COUNT,
            MetricAggregation.SUM,
            meta_fields=("clicks", "clicks"),
        )


def test_duplicate_dependencies_are_rejected() -> None:
    with pytest.raises(UnsupportedMetricError, match="duplicate dependencies"):
        MetricDefinition(
            Metric.CTR,
            MetricType.DERIVED,
            MetricUnit.PERCENT,
            MetricAggregation.RECALCULATE,
            dependencies=(Metric.CLICKS, Metric.CLICKS),
        )


def test_incompatible_type_and_aggregation_are_rejected() -> None:
    with pytest.raises(UnsupportedMetricError, match="incompatible type and aggregation"):
        MetricDefinition(
            Metric.CLICKS,
            MetricType.DIRECT,
            MetricUnit.COUNT,
            MetricAggregation.RECALCULATE,
            meta_fields=("clicks",),
        )
