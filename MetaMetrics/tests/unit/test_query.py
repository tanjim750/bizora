"""Tests for the query primitives: fields, filters, and filter encoding."""

from __future__ import annotations

import pytest

from metametrics.exceptions import InvalidInputError
from metametrics.query.builder import QueryBuilder
from metametrics.query.fields import Fields
from metametrics.query.filters import Filter, FilterOperator


def test_fields_require_at_least_one_selection() -> None:
    with pytest.raises(InvalidInputError, match="At least one field"):
        Fields([])


@pytest.mark.parametrize("field", ["Name", "1name", "name-with-dash", "name.with.dot", ""])
def test_fields_reject_invalid_meta_field_names(field: str) -> None:
    with pytest.raises(InvalidInputError, match="valid Meta field names"):
        Fields([field])


def test_fields_are_deduplicated_and_ordered() -> None:
    fields = Fields(["name", "id", "name"])

    assert fields.values == ("name", "id")
    assert fields.to_query_value() == "name,id"


def test_required_fields_are_merged_ahead_of_the_selection() -> None:
    fields = Fields(["name"]).with_required(["id", "name"])

    assert fields.values == ("id", "name")
    assert fields.to_query_value() == "id,name"


def test_filters_require_a_valid_field_name() -> None:
    with pytest.raises(InvalidInputError, match="valid Meta field name"):
        Filter(field="Campaign.ID", operator=FilterOperator.EQUAL, value="1")


def test_filters_accept_a_dotted_field_name() -> None:
    assert Filter(field="campaign.id", operator=FilterOperator.EQUAL, value="1").field == "campaign.id"


def test_list_operators_require_a_non_empty_list() -> None:
    with pytest.raises(InvalidInputError, match="require a non-empty value list"):
        Filter(field="campaign.id", operator=FilterOperator.IN, value=())


def test_scalar_operators_reject_a_list() -> None:
    with pytest.raises(InvalidInputError, match="require a scalar value"):
        Filter(field="campaign.id", operator=FilterOperator.EQUAL, value=("1", "2"))


def test_a_filter_renders_the_meta_shape() -> None:
    assert Filter(field="campaign.id", operator=FilterOperator.EQUAL, value="1").to_dict() == {
        "field": "campaign.id",
        "operator": "EQUAL",
        "value": "1",
    }

    assert Filter(field="campaign.id", operator=FilterOperator.IN, value=["1", "2"]).to_dict() == {
        "field": "campaign.id",
        "operator": "IN",
        "value": ["1", "2"],
    }


def test_the_query_builder_returns_none_without_filters() -> None:
    assert QueryBuilder().encode_filters([], ["campaign.id"]) is None


def test_the_query_builder_encodes_filters_without_spaces() -> None:
    encoded = QueryBuilder().encode_filters(
        [Filter(field="campaign.id", operator=FilterOperator.IN, value=["1", "2"])],
        ["campaign.id"],
    )

    assert encoded == '[{"field":"campaign.id","operator":"IN","value":["1","2"]}]'


def test_the_query_builder_rejects_unknown_filter_fields() -> None:
    with pytest.raises(InvalidInputError, match="Unsupported Insights filter field"):
        QueryBuilder().encode_filters(
            [Filter(field="campaign.id", operator=FilterOperator.EQUAL, value="1")],
            ["adset.id"],
        )
