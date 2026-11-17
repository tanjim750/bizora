"""The entity levels supported by the Meta Historical analysis."""

from __future__ import annotations

from enum import StrEnum

from metametrics.insights.level import InsightsLevel

__all__ = ["HistoricalLevel"]


class HistoricalLevel(StrEnum):
    """The entity level a historical analysis query is performed at."""

    CAMPAIGN = "campaign"
    AD_SET = "adset"
    AD = "ad"

    def to_insights_level(self) -> InsightsLevel:
        """Convert this historical level into its matching InsightsLevel."""
        return InsightsLevel(self.value)
