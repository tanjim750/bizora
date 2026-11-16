"""The classification of a metric."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["MetricAggregation", "MetricType", "MetricUnit"]


class MetricType(StrEnum):
    """How a metric is sourced from the Meta Insights API."""

    DIRECT = "direct"
    ACTION = "action"
    ACTION_VALUE = "action_value"
    DERIVED = "derived"


class MetricUnit(StrEnum):
    """The unit a metric is expressed in."""

    MONEY = "money"
    COUNT = "count"
    RATIO = "ratio"
    PERCENT = "percent"


class MetricAggregation(StrEnum):
    """How a metric behaves when several reporting periods are aggregated."""

    SUM = "sum"
    META_ONLY = "meta_only"
    RECALCULATE = "recalculate"
