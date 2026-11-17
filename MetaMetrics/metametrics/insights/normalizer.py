"""Normalisation of parsed Insights rows."""

from __future__ import annotations

from collections.abc import Sequence

from metametrics.insights.dto import InsightsDTO
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.calculator import MetricCalculator
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.parsers.parsed import ParsedInsights

__all__ = ["InsightsNormalizer"]


class InsightsNormalizer:
    """Turns parsed Insights rows into :class:`InsightsDTO` values."""

    def __init__(self, calculator: MetricCalculator | None = None) -> None:
        self.calculator = calculator or MetricCalculator()

    def normalize(
        self,
        parsed: ParsedInsights,
        level: InsightsLevel,
        requested_metrics: Sequence[Metric],
    ) -> InsightsDTO:
        """Normalise one parsed row."""
        return InsightsDTO(
            entity_id=parsed.entity_id,
            entity_name=parsed.entity_name,
            level=level,
            campaign_id=parsed.campaign_id,
            ad_set_id=parsed.ad_set_id,
            ad_id=parsed.ad_id,
            date_range=parsed.date_range,
            metrics=self.calculator.calculate_all(requested_metrics, parsed.foundational),
            raw_data=parsed.raw_data,
            foundational_metrics=dict(parsed.foundational),
            currency=parsed.currency,
        )
