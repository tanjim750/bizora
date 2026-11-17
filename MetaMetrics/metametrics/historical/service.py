"""Historical analysis service for Meta advertising entities."""

from __future__ import annotations

from collections.abc import Sequence

from metametrics.exceptions import UnexpectedResponseError
from metametrics.historical.delivery import (
    DeliveryDiscovery,
    DeliveryDiscoveryProtocol,
    DeliveryStatus,
)
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.query import HistoricalQuery
from metametrics.historical.response import HistoricalResponse
from metametrics.historical.result import HistoricalResult
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.query import InsightsQuery
from metametrics.insights.service import InsightsService

__all__ = ["HistoricalService"]


class HistoricalService:
    """Delivers historical performance and delivery analysis."""

    def __init__(
        self,
        insights_service: InsightsService,
        delivery_discovery: DeliveryDiscoveryProtocol | None = None,
    ) -> None:
        self._insights_service = insights_service
        self._delivery_discovery: DeliveryDiscoveryProtocol = (
            delivery_discovery if delivery_discovery is not None else DeliveryDiscovery()
        )

    def get(self, query: HistoricalQuery) -> list[HistoricalResult]:
        """Fetch historical analysis results for the query."""
        insights = self._insights_service.get(self._insights_query(query))
        return self._discover(query, insights)

    def get_response(self, query: HistoricalQuery) -> HistoricalResponse:
        """Fetch historical analysis wrapped in a response envelope."""
        response = self._insights_service.get_response(self._insights_query(query))
        return HistoricalResponse(
            level=query.level,
            currency=response.currency,
            data=self._discover(query, list(response.data)),
        )

    def campaigns(self, date_range: DateRange) -> list[HistoricalResult]:
        """Historical results for campaigns."""
        return self.get(HistoricalQuery(level=HistoricalLevel.CAMPAIGN, date_range=date_range))

    def ad_sets(self, date_range: DateRange, campaign_id: str | None = None) -> list[HistoricalResult]:
        """Historical results for ad sets, optionally scoped to a campaign."""
        return self.get(
            HistoricalQuery(
                level=HistoricalLevel.AD_SET,
                date_range=date_range,
                parent_id=campaign_id,
            )
        )

    def ads(self, date_range: DateRange, parent_id: str | None = None) -> list[HistoricalResult]:
        """Historical results for ads, optionally scoped to a parent campaign or ad set."""
        return self.get(
            HistoricalQuery(
                level=HistoricalLevel.AD,
                date_range=date_range,
                parent_id=parent_id,
            )
        )

    def _insights_query(self, query: HistoricalQuery) -> InsightsQuery:
        return InsightsQuery(
            level=query.level.to_insights_level(),
            date_range=query.date_range,
            metrics=self._effective_metrics(query),
            entity_id=query.parent_id,
            daily=query.daily,
            filters=query.filters,
            limit=query.limit,
            include_ad_set_configuration=False,
        )

    def _discover(self, query: HistoricalQuery, insights: Sequence[InsightsDTO]) -> list[HistoricalResult]:
        results: list[HistoricalResult] = []

        for insight in insights:
            assessment = self._delivery_discovery.assess(insight)

            if assessment.status == DeliveryStatus.INSUFFICIENT_EVIDENCE:
                msg = (
                    f"Meta returned insufficient delivery evidence for "
                    f'{query.level.value} "{insight.entity_id}".'
                )
                raise UnexpectedResponseError(msg)

            evidence = assessment.evidence
            if evidence is None:
                continue

            results.append(
                HistoricalResult(
                    requested_period=query.date_range,
                    delivery_evidence=evidence,
                    insights=insight,
                )
            )

        return results

    def _effective_metrics(self, query: HistoricalQuery) -> list[Metric]:
        unique: dict[str, Metric] = {}
        for m in (*self._delivery_discovery.required_metrics(), *query.metrics):
            unique[m.value] = m
        return list(unique.values())
