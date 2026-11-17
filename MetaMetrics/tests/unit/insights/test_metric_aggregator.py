"""Tests for the metric aggregator.

Ported from ``tests/Unit/Insights/MetricAggregatorTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.exceptions import InvalidInputError
from metametrics.insights.aggregation import MetricAggregator
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.normalizer import InsightsNormalizer
from metametrics.insights.parsers.insights_parser import InsightsParser

METRICS = [Metric.CTR, Metric.CPC, Metric.CPM, Metric.ROAS, Metric.REACH]


def make_row(
    date: str,
    spend: str,
    clicks: str,
    impressions: str,
    reach: str,
    purchase_value: str,
    campaign_id: str = "campaign-1",
    currency: str | None = "USD",
) -> InsightsDTO:
    row: dict[str, object] = {
        "campaign_id": campaign_id,
        "campaign_name": "Campaign",
        "date_start": date,
        "date_stop": date,
        "spend": spend,
        "clicks": clicks,
        "impressions": impressions,
        "reach": reach,
        "action_values": [{"action_type": "purchase", "value": purchase_value}],
    }

    if currency is not None:
        row["account_currency"] = currency

    foundational = MetricRegistry().foundational_metrics(METRICS)
    parsed = InsightsParser().parse(row, InsightsLevel.CAMPAIGN, foundational)

    return InsightsNormalizer().normalize(parsed, InsightsLevel.CAMPAIGN, METRICS)


def test_it_recalculates_ratios_from_foundational_totals() -> None:
    result = MetricAggregator().aggregate(
        [
            make_row("2026-09-01", "20", "10", "100", "60", "40"),
            make_row("2026-09-02", "80", "10", "900", "500", "260"),
        ],
        METRICS,
    )

    assert result is not None
    assert result.currency == "USD"
    assert result.to_dict()["currency"] == "USD"
    assert result.metric(Metric.CTR) == 2.0
    assert result.metric(Metric.CPC) == 5.0
    assert result.metric(Metric.CPM) == 100.0
    assert result.metric(Metric.ROAS) == 3.0
    assert result.metric(Metric.REACH) is None
    assert result.date_range.since == "2026-09-01"
    assert result.date_range.until == "2026-09-02"


def test_a_single_row_reach_uses_the_meta_reported_value() -> None:
    result = MetricAggregator().aggregate(
        [make_row("2026-09-01", "20", "10", "100", "60", "40")],
        [Metric.REACH],
    )

    assert result is not None
    assert result.metric(Metric.REACH) == 60.0


def test_empty_rows_do_not_manufacture_an_aggregate() -> None:
    assert MetricAggregator().aggregate([], [Metric.SPEND]) is None


def test_overlapping_rows_are_rejected() -> None:
    with pytest.raises(InvalidInputError, match="overlapping"):
        MetricAggregator().aggregate(
            [
                make_row("2026-09-01", "20", "10", "100", "60", "40"),
                make_row("2026-09-01", "80", "10", "900", "500", "260"),
            ],
            [Metric.SPEND],
        )


def test_mixed_entities_are_rejected() -> None:
    with pytest.raises(InvalidInputError, match="one entity"):
        MetricAggregator().aggregate(
            [
                make_row("2026-09-01", "20", "10", "100", "60", "40"),
                make_row("2026-09-02", "80", "10", "900", "500", "260", "campaign-2"),
            ],
            [Metric.SPEND],
        )


def test_mixed_currencies_cannot_be_aggregated() -> None:
    with pytest.raises(InvalidInputError, match="currency"):
        MetricAggregator().aggregate(
            [
                make_row("2026-09-01", "20", "10", "100", "60", "40"),
                make_row("2026-09-02", "80", "10", "900", "500", "260", currency="BDT"),
            ],
            [Metric.CPC],
        )


def test_known_and_unknown_currencies_cannot_be_aggregated() -> None:
    with pytest.raises(InvalidInputError, match="currency"):
        MetricAggregator().aggregate(
            [
                make_row("2026-09-01", "20", "10", "100", "60", "40"),
                make_row("2026-09-02", "80", "10", "900", "500", "260", currency=None),
            ],
            [Metric.CPC],
        )


def test_legacy_rows_without_a_currency_remain_supported() -> None:
    result = MetricAggregator().aggregate(
        [make_row("2026-09-01", "20", "10", "100", "60", "40", currency=None)],
        [Metric.CPC],
    )

    assert result is not None
    assert result.currency is None
    assert result.metric(Metric.CPC) == 2.0


def test_aggregation_requires_at_least_one_metric() -> None:
    with pytest.raises(InvalidInputError, match="at least one requested metric"):
        MetricAggregator().aggregate([], [])
