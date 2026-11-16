"""Tests for historical value objects.

Ported from ``tests/Unit/Historical/HistoricalValueObjectTest.php``.
"""

from __future__ import annotations

from typing import Any

import pytest

from metametrics.exceptions import InvalidInputError, UnsupportedMetricError
from metametrics.historical.delivery import (
    DeliveryAssessment,
    DeliveryEvidence,
    DeliveryStatus,
)
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.query import HistoricalQuery
from metametrics.historical.response import HistoricalResponse
from metametrics.historical.result import HistoricalResult
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.raw_data import InsightsRawData


def _range() -> DateRange:
    return DateRange("2026-09-01", "2026-09-24")


def _insights(level: InsightsLevel, date_range: DateRange) -> InsightsDTO:
    return InsightsDTO(
        entity_id="entity-1",
        entity_name="Entity",
        level=level,
        campaign_id=None if level == InsightsLevel.ACCOUNT else "entity-1",
        ad_set_id=None,
        ad_id=None,
        date_range=date_range,
        metrics={Metric.SPEND.value: 1.0},
        raw_data=InsightsRawData("1", None, None, None, None),
    )


@pytest.mark.parametrize(
    "indicators",
    [
        {},
        {"spend": 0.0},
        {"impressions": -1.0},
        {"unknown": 1.0},
        {"reach": "10"},
    ],
)
def test_delivery_evidence_rejects_invalid_indicators(indicators: dict[str, Any]) -> None:
    with pytest.raises(InvalidInputError):
        DeliveryEvidence(indicators)


def test_historical_result_rejects_account_insights() -> None:
    with pytest.raises(InvalidInputError):
        HistoricalResult(
            requested_period=_range(),
            delivery_evidence=DeliveryEvidence({"spend": 1.0}),
            insights=_insights(InsightsLevel.ACCOUNT, _range()),
        )


def test_historical_result_rejects_insights_outside_requested_period() -> None:
    with pytest.raises(InvalidInputError):
        HistoricalResult(
            requested_period=_range(),
            delivery_evidence=DeliveryEvidence({"spend": 1.0}),
            insights=_insights(InsightsLevel.CAMPAIGN, DateRange("2026-08-31", "2026-09-01")),
        )


def test_historical_result_rejects_evidence_that_does_not_match_insights() -> None:
    with pytest.raises(InvalidInputError):
        HistoricalResult(
            requested_period=_range(),
            delivery_evidence=DeliveryEvidence({"spend": 2.0}),
            insights=_insights(InsightsLevel.CAMPAIGN, _range()),
        )


def test_delivery_assessment_invariants() -> None:
    with pytest.raises(RuntimeError):
        DeliveryAssessment(DeliveryStatus.DELIVERED, None)

    evidence = DeliveryEvidence({"spend": 1.0})
    with pytest.raises(RuntimeError):
        DeliveryAssessment(DeliveryStatus.NOT_DELIVERED, evidence)


def test_historical_query_validation() -> None:
    with pytest.raises(InvalidInputError, match="empty"):
        HistoricalQuery(HistoricalLevel.CAMPAIGN, _range(), parent_id="   ")

    with pytest.raises(InvalidInputError, match="limit"):
        HistoricalQuery(HistoricalLevel.CAMPAIGN, _range(), limit=0)

    with pytest.raises(UnsupportedMetricError):
        HistoricalQuery(HistoricalLevel.CAMPAIGN, _range(), metrics=["invalid"])  # type: ignore[list-item]

    with pytest.raises(InvalidInputError, match="Filter"):
        HistoricalQuery(HistoricalLevel.CAMPAIGN, _range(), filters=["invalid"])  # type: ignore[list-item]


def test_historical_response_validation() -> None:
    with pytest.raises(InvalidInputError, match="currency"):
        HistoricalResponse(HistoricalLevel.CAMPAIGN, "invalid")

    insights = _insights(InsightsLevel.CAMPAIGN, _range())
    result = HistoricalResult(
        requested_period=_range(),
        delivery_evidence=DeliveryEvidence({"spend": 1.0}),
        insights=insights,
    )
    with pytest.raises(InvalidInputError, match="currency"):
        HistoricalResponse(HistoricalLevel.CAMPAIGN, "USD", [result])  # result.currency is None
