"""The result of historical analysis for a single entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from metametrics.exceptions import InvalidInputError
from metametrics.historical.delivery import DeliveryEvidence
from metametrics.historical.level import HistoricalLevel
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.metrics.metric import Metric

__all__ = ["HistoricalResult"]


@dataclass(frozen=True, slots=True)
class HistoricalResult:
    """Historical delivery result for a single entity."""

    requested_period: DateRange
    delivery_evidence: DeliveryEvidence
    insights: InsightsDTO

    def __post_init__(self) -> None:
        try:
            HistoricalLevel(self.insights.level.value)
        except ValueError:
            raise InvalidInputError("Historical results require Campaign, Ad Set, or Ad Insights.") from None

        if (
            self.insights.date_start < self.requested_period.since
            or self.insights.date_stop > self.requested_period.until
        ):
            raise InvalidInputError(
                "Historical Insights must fall within the requested reporting period."
            )

        for name, value in self.delivery_evidence.indicators().items():
            if self.insights.metric(Metric(name)) != value:
                raise InvalidInputError(
                    "Historical delivery evidence must match its Insights metrics."
                )

    @property
    def entity_id(self) -> str:
        return self.insights.entity_id

    @property
    def entity_name(self) -> str | None:
        return self.insights.entity_name

    @property
    def currency(self) -> str | None:
        return self.insights.currency

    @property
    def level(self) -> HistoricalLevel:
        return HistoricalLevel(self.insights.level.value)

    @property
    def campaign_id(self) -> str | None:
        return self.insights.campaign_id

    @property
    def ad_set_id(self) -> str | None:
        return self.insights.ad_set_id

    @property
    def ad_id(self) -> str | None:
        return self.insights.ad_id

    @property
    def requested_since(self) -> str:
        return self.requested_period.since

    @property
    def requested_until(self) -> str:
        return self.requested_period.until

    def to_dict(self, include_currency: bool = True) -> dict[str, Any]:
        """Render the row as a plain dictionary."""
        return self.insights.to_dict(include_currency)
