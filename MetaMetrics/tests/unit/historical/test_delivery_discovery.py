"""Tests for historical delivery discovery.

Ported from ``tests/Unit/Historical/DeliveryDiscoveryTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.historical.delivery import DeliveryDiscovery, DeliveryStatus
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.raw_data import InsightsRawData


def _insights(metrics: dict[str, float | None]) -> InsightsDTO:
    return InsightsDTO(
        entity_id="campaign-1",
        entity_name="Campaign",
        level=InsightsLevel.CAMPAIGN,
        campaign_id="campaign-1",
        ad_set_id=None,
        ad_id=None,
        date_range=DateRange("2026-09-01", "2026-09-24"),
        metrics=metrics,
        raw_data=InsightsRawData(None, None, None, None, None),
    )


@pytest.mark.parametrize(
    ("metrics", "expected"),
    [
        ({"impressions": 1.0, "spend": 0.0, "reach": 0.0}, DeliveryStatus.DELIVERED),
        ({"impressions": 0.0, "spend": 0.01, "reach": 0.0}, DeliveryStatus.DELIVERED),
        ({"impressions": 0.0, "spend": 0.0, "reach": 1.0}, DeliveryStatus.DELIVERED),
        ({"impressions": 0.0, "spend": 0.0, "reach": 0.0}, DeliveryStatus.NOT_DELIVERED),
        ({"impressions": None, "spend": None, "reach": None}, DeliveryStatus.INSUFFICIENT_EVIDENCE),
        ({"purchases": 12.0}, DeliveryStatus.INSUFFICIENT_EVIDENCE),
    ],
)
def test_it_classifies_delivery_evidence(
    metrics: dict[str, float | None],
    expected: DeliveryStatus,
) -> None:
    discovery = DeliveryDiscovery()
    assessment = discovery.assess(_insights(metrics))
    assert assessment.status == expected


def test_it_reports_the_qualifying_evidence() -> None:
    discovery = DeliveryDiscovery()
    assessment = discovery.assess(
        _insights({"impressions": 1000.0, "spend": 20.0, "reach": 0.0})
    )
    evidence = assessment.evidence
    assert evidence is not None
    assert evidence.indicators() == {"impressions": 1000.0, "spend": 20.0}
    assert evidence.has(Metric.SPEND)
    assert evidence.value(Metric.REACH) is None
    assert discovery.has_delivery(_insights({"impressions": 1000.0, "spend": 20.0, "reach": 0.0}))
