"""Tests for the metric pipeline.

Ported from ``tests/Unit/Insights/MetricPipelineTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.exceptions import InvalidInputError, UnexpectedResponseError
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.calculator import MetricCalculator
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.normalizer import InsightsNormalizer
from metametrics.insights.parsers.insights_parser import InsightsParser


def test_the_registry_resolves_only_required_foundational_fields() -> None:
    registry = MetricRegistry()

    assert registry.foundational_metrics([Metric.ROAS, Metric.CTR]) == [
        Metric.SPEND,
        Metric.PURCHASE_VALUE,
        Metric.CLICKS,
        Metric.IMPRESSIONS,
    ]
    assert registry.meta_fields([Metric.ROAS, Metric.CTR]) == [
        "spend",
        "action_values",
        "clicks",
        "impressions",
    ]


def test_it_calculates_derived_metrics_from_foundational_values() -> None:
    values = {
        Metric.SPEND.value: 100.0,
        Metric.PURCHASES.value: 4.0,
        Metric.PURCHASE_VALUE.value: 300.0,
        Metric.CLICKS.value: 20.0,
        Metric.IMPRESSIONS.value: 1000.0,
    }
    calculator = MetricCalculator()

    assert calculator.calculate(Metric.COST_PER_PURCHASE, values) == 25.0
    assert calculator.calculate(Metric.ROAS, values) == 3.0
    assert calculator.calculate(Metric.CPC, values) == 5.0
    assert calculator.calculate(Metric.CTR, values) == 2.0
    assert calculator.calculate(Metric.CPM, values) == 100.0


def test_it_preserves_missing_values_and_avoids_zero_division() -> None:
    calculator = MetricCalculator()

    def value(metric: Metric, amount: float | None) -> dict[str, float | None]:
        return {metric.value: amount}

    assert calculator.calculate(Metric.ROAS, value(Metric.PURCHASE_VALUE, 0.0)) is None
    assert calculator.calculate(Metric.CPC, value(Metric.CLICKS, 0.0)) is None
    assert calculator.calculate(Metric.COST_PER_PURCHASE, value(Metric.PURCHASES, None)) is None
    assert calculator.calculate(Metric.COST_PER_PURCHASE, value(Metric.PURCHASES, 0.0)) is None
    assert calculator.calculate(Metric.CPC, value(Metric.SPEND, None)) is None
    assert calculator.calculate(Metric.CTR, value(Metric.IMPRESSIONS, 0.0)) is None
    assert calculator.calculate(Metric.CPM, value(Metric.IMPRESSIONS, 0.0)) is None
    assert (
        calculator.calculate(
            Metric.CTR,
            {Metric.CLICKS.value: 0.0, Metric.IMPRESSIONS.value: 1000.0},
        )
        == 0.0
    )
    assert (
        calculator.calculate(
            Metric.ROAS,
            {Metric.PURCHASE_VALUE.value: 0.0, Metric.SPEND.value: 100.0},
        )
        == 0.0
    )


def test_the_calculator_rejects_malformed_normalized_input() -> None:
    with pytest.raises(InvalidInputError):
        MetricCalculator().calculate(Metric.CPC, {Metric.SPEND.value: "100", Metric.CLICKS.value: 10.0})


def test_count_and_value_use_one_shared_purchase_action_type() -> None:
    metrics = [Metric.PURCHASES, Metric.PURCHASE_VALUE, Metric.COST_PER_PURCHASE, Metric.ROAS]
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "campaign_name": "Sales",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "spend": "100",
            "actions": [
                {"action_type": "omni_purchase", "value": "10"},
                {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "8"},
            ],
            "action_values": [
                {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "800"},
            ],
        },
        InsightsLevel.CAMPAIGN,
        MetricRegistry().foundational_metrics(metrics),
    )
    insights = InsightsNormalizer().normalize(parsed, InsightsLevel.CAMPAIGN, metrics)

    assert insights.purchases == 8.0
    assert insights.purchase_value == 800.0
    assert insights.cost_per_purchase == 12.5
    assert insights.roas == 8.0


def test_incompatible_purchase_action_types_remain_unavailable() -> None:
    metrics = [Metric.PURCHASES, Metric.PURCHASE_VALUE]
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "actions": [{"action_type": "omni_purchase", "value": "10"}],
            "action_values": [{"action_type": "offsite_conversion.fb_pixel_purchase", "value": "800"}],
        },
        InsightsLevel.CAMPAIGN,
        metrics,
    )

    assert parsed.foundational[Metric.PURCHASES.value] is None
    assert parsed.foundational[Metric.PURCHASE_VALUE.value] is None


def test_a_missing_purchase_count_does_not_erase_the_available_purchase_value() -> None:
    metrics = [Metric.PURCHASES, Metric.PURCHASE_VALUE]
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "actions": None,
            "action_values": [{"action_type": "purchase", "value": "800"}],
        },
        InsightsLevel.CAMPAIGN,
        metrics,
    )

    assert parsed.foundational[Metric.PURCHASES.value] is None
    assert parsed.foundational[Metric.PURCHASE_VALUE.value] == 800.0


def test_a_missing_purchase_value_does_not_erase_the_available_purchase_count() -> None:
    metrics = [Metric.PURCHASES, Metric.PURCHASE_VALUE]
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "actions": [{"action_type": "purchase", "value": "2"}],
            "action_values": None,
        },
        InsightsLevel.CAMPAIGN,
        metrics,
    )

    assert parsed.foundational[Metric.PURCHASES.value] == 2.0
    assert parsed.foundational[Metric.PURCHASE_VALUE.value] is None


def test_it_preserves_the_ad_hierarchy_and_normalizes_numeric_strings() -> None:
    metrics = [Metric.SPEND, Metric.IMPRESSIONS]
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "adset_id": "adset-1",
            "ad_id": "ad-1",
            "ad_name": "Creative One",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-01",
            "spend": "12.345678",
            "impressions": "1000",
        },
        InsightsLevel.AD,
        metrics,
    )
    insights = InsightsNormalizer().normalize(parsed, InsightsLevel.AD, metrics)

    assert insights.entity_id == "ad-1"
    assert insights.campaign_id == "campaign-1"
    assert insights.ad_set_id == "adset-1"
    assert insights.ad_id == "ad-1"
    assert insights.spend == 12.345678
    assert insights.impressions == 1000.0


def test_it_preserves_the_ad_set_hierarchy() -> None:
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "adset_id": "adset-1",
            "adset_name": "Prospecting",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "spend": "50",
        },
        InsightsLevel.AD_SET,
        [Metric.SPEND],
    )
    insights = InsightsNormalizer().normalize(parsed, InsightsLevel.AD_SET, [Metric.SPEND])

    assert insights.entity_id == "adset-1"
    assert insights.campaign_id == "campaign-1"
    assert insights.ad_set_id == "adset-1"
    assert insights.ad_id is None


def test_the_current_status_and_creation_date_do_not_affect_requested_period_insights() -> None:
    metrics = [Metric.SPEND, Metric.IMPRESSIONS]
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "campaign_name": "Historical Campaign",
            "status": "PAUSED",
            "created_time": "2026-08-10T00:00:00+0000",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "spend": "100",
            "impressions": "1000",
        },
        InsightsLevel.CAMPAIGN,
        metrics,
    )
    insights = InsightsNormalizer().normalize(parsed, InsightsLevel.CAMPAIGN, metrics)

    assert insights.date_start == "2026-09-01"
    assert insights.date_stop == "2026-09-24"
    assert insights.spend == 100.0
    assert insights.impressions == 1000.0


def test_an_explicit_action_list_without_purchases_normalizes_to_zero() -> None:
    parsed = InsightsParser().parse(
        {
            "account_id": "123",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "actions": [{"action_type": "link_click", "value": "25"}],
        },
        InsightsLevel.ACCOUNT,
        [Metric.PURCHASES],
    )

    assert parsed.foundational[Metric.PURCHASES.value] == 0.0


def test_it_preserves_the_complete_raw_cpr_inputs() -> None:
    actions = [
        {
            "action_type": "offsite_conversion.fb_pixel_purchase",
            "value": "4",
            "1d_view": "1",
            "7d_click": "3",
        }
    ]
    cost_per_action_type = [{"action_type": "offsite_conversion.fb_pixel_purchase", "value": "25.125"}]
    promoted_object = {
        "custom_conversion_id": "custom-1",
        "product_set_id": "product-set-1",
        "extra_meta_field": {"nested": True},
    }
    parsed = InsightsParser().parse(
        {
            "campaign_id": "campaign-1",
            "adset_id": "adset-1",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "spend": "100.5000",
            "actions": actions,
            "cost_per_action_type": cost_per_action_type,
        },
        InsightsLevel.AD_SET,
        [Metric.SPEND],
        {
            "id": "adset-1",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "promoted_object": promoted_object,
        },
    )
    insights = InsightsNormalizer().normalize(parsed, InsightsLevel.AD_SET, [Metric.SPEND])

    assert insights.raw_data.spend == "100.5000"
    assert insights.raw_data.actions == actions
    assert insights.raw_data.cost_per_action_type == cost_per_action_type
    assert insights.raw_data.optimization_goal == "OFFSITE_CONVERSIONS"
    assert insights.raw_data.promoted_object == promoted_object


@pytest.mark.parametrize("value", ["not-a-number", "", ["100"], {"a": 1}, True])
def test_it_rejects_malformed_numeric_data(value: object) -> None:
    with pytest.raises(UnexpectedResponseError):
        InsightsParser().parse(
            {
                "account_id": "123",
                "date_start": "2026-09-01",
                "date_stop": "2026-09-24",
                "spend": value,
            },
            InsightsLevel.ACCOUNT,
            [Metric.SPEND],
        )


def test_a_null_spend_yields_no_value_instead_of_an_error() -> None:
    parsed = InsightsParser().parse(
        {
            "account_id": "123",
            "date_start": "2026-09-01",
            "date_stop": "2026-09-24",
            "spend": None,
        },
        InsightsLevel.ACCOUNT,
        [Metric.SPEND],
    )

    assert parsed.foundational[Metric.SPEND.value] is None
    assert parsed.raw_data.spend is None


def test_it_rejects_an_invalid_account_currency() -> None:
    with pytest.raises(UnexpectedResponseError, match="valid account_currency"):
        InsightsParser().parse(
            {
                "account_id": "123",
                "account_currency": "usd",
                "date_start": "2026-09-01",
                "date_stop": "2026-09-24",
            },
            InsightsLevel.ACCOUNT,
            [Metric.SPEND],
        )


def test_it_requires_the_identity_fields_of_the_level() -> None:
    with pytest.raises(UnexpectedResponseError, match='"ad_id"'):
        InsightsParser().parse(
            {
                "campaign_id": "campaign-1",
                "adset_id": "adset-1",
                "date_start": "2026-09-01",
                "date_stop": "2026-09-24",
            },
            InsightsLevel.AD,
            [Metric.SPEND],
        )
