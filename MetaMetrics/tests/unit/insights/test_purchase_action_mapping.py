"""Tests for the purchase action mapping and the action parsers.

Ported from ``tests/Unit/Insights/PurchaseActionMappingTest.php``.
"""

from __future__ import annotations

import pytest

from metametrics.exceptions import InvalidInputError, UnexpectedResponseError
from metametrics.insights.metrics.purchase_actions import PurchaseActionMapping
from metametrics.insights.parsers.action_parser import ActionParser
from metametrics.insights.parsers.action_value_parser import ActionValueParser


def test_one_mapping_coordinates_count_and_value_priority() -> None:
    mapping = PurchaseActionMapping(["offsite_conversion.fb_pixel_purchase", "omni_purchase"])
    actions = ActionParser(mapping)
    values = ActionValueParser(mapping)

    action_rows = [
        {"action_type": "omni_purchase", "value": "9"},
        {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "7"},
    ]
    value_rows = [
        {"action_type": "omni_purchase", "value": "900"},
        {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "700"},
    ]

    action_type = actions.common_purchase_action_type(action_rows, value_rows)

    assert action_type == "offsite_conversion.fb_pixel_purchase"
    assert actions.purchases_for_type(action_rows, action_type) == 7.0
    assert values.purchase_value_for_type(value_rows, action_type) == 700.0


def test_count_and_value_extraction_do_not_depend_on_array_order() -> None:
    mapping = PurchaseActionMapping(["purchase"])

    assert (
        ActionParser(mapping).purchases(
            [
                {"action_type": "link_click", "value": "20"},
                {"action_type": "purchase", "value": "3"},
            ]
        )
        == 3.0
    )
    assert (
        ActionValueParser(mapping).purchase_value(
            [
                {"action_type": "purchase", "value": "150"},
                {"action_type": "link_click", "value": "20"},
            ]
        )
        == 150.0
    )


def test_explicit_extraction_cannot_bypass_the_configured_mapping() -> None:
    with pytest.raises(InvalidInputError):
        ActionParser(["purchase"]).purchases_for_type([{"action_type": "lead", "value": "5"}], "lead")


def test_the_mapping_rejects_duplicates() -> None:
    with pytest.raises(InvalidInputError, match="must not contain duplicates"):
        PurchaseActionMapping(["purchase", "purchase"])


def test_the_mapping_rejects_an_empty_list() -> None:
    with pytest.raises(InvalidInputError, match="non-empty list"):
        PurchaseActionMapping([])


def test_the_mapping_rejects_blank_action_types() -> None:
    with pytest.raises(InvalidInputError, match="non-empty strings"):
        PurchaseActionMapping([" "])


def test_duplicate_meta_action_rows_are_rejected_instead_of_overwritten() -> None:
    with pytest.raises(UnexpectedResponseError, match="duplicate action type"):
        ActionParser().purchases(
            [
                {"action_type": "purchase", "value": "1"},
                {"action_type": "purchase", "value": "2"},
            ]
        )


def test_duplicate_meta_action_value_rows_are_rejected_instead_of_overwritten() -> None:
    with pytest.raises(UnexpectedResponseError, match="duplicate action type"):
        ActionValueParser().purchase_value(
            [
                {"action_type": "purchase", "value": "10"},
                {"action_type": "purchase", "value": "20"},
            ]
        )


def test_an_empty_action_type_is_rejected() -> None:
    with pytest.raises(UnexpectedResponseError, match="malformed action"):
        ActionParser().purchases([{"action_type": "", "value": "1"}])


def test_a_missing_actions_payload_yields_no_value() -> None:
    assert ActionParser().purchases(None) is None
    assert ActionValueParser().purchase_value(None) is None


def test_an_action_list_without_purchases_normalises_to_zero() -> None:
    assert ActionParser().purchases([{"action_type": "link_click", "value": "25"}]) == 0.0
    assert ActionValueParser().purchase_value([{"action_type": "link_click", "value": "25"}]) == 0.0


def test_a_non_numeric_action_value_is_rejected() -> None:
    with pytest.raises(UnexpectedResponseError, match="must be numeric"):
        ActionParser().purchases([{"action_type": "purchase", "value": "not-a-number"}])


def test_a_non_finite_action_value_is_rejected() -> None:
    with pytest.raises(UnexpectedResponseError, match="must be finite"):
        ActionParser().purchases([{"action_type": "purchase", "value": "1e400"}])
