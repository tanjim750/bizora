"""The metric catalogue and computation engine.

This package holds the metric primitives only. They must not depend on the
Insights data transfer objects, otherwise importing a DTO would pull the whole
package back into itself.
"""

from metametrics.insights.metrics.calculator import MetricCalculator
from metametrics.insights.metrics.definition import MetricDefinition
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.purchase_actions import PurchaseActionMapping
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.metrics.types import MetricAggregation, MetricType, MetricUnit

__all__ = [
    "Metric",
    "MetricAggregation",
    "MetricCalculator",
    "MetricDefinition",
    "MetricRegistry",
    "MetricType",
    "MetricUnit",
    "PurchaseActionMapping",
]
