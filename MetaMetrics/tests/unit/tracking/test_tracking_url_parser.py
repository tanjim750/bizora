"""Tests for TrackingUrlParser.

Ported from ``tests/Unit/Tracking/TrackingUrlParserTest.php``.
"""

from __future__ import annotations

from typing import Any

import pytest

from metametrics.exceptions import InvalidInputError
from metametrics.tracking.identifiers import TrackingIdentifiers
from metametrics.tracking.parser import TrackingUrlParser


@pytest.fixture
def parser() -> TrackingUrlParser:
    return TrackingUrlParser()


def test_it_parses_a_complete_tracking_url(parser: TrackingUrlParser) -> None:
    result = parser.parse(
        "https://example.com/product/item?utm_campaign=23859320180340794"
        "&utm_content=23859320180330794&utm_id=23859320180340794"
        "&utm_medium=paid&utm_source=fb&utm_term=23859320180350794"
    )

    assert result.campaign_id == "23859320180340794"
    assert result.ad_set_id == "23859320180350794"
    assert result.ad_id == "23859320180330794"
    assert result.source == "fb"
    assert result.medium == "paid"


def test_it_returns_nullable_fields_for_a_partial_url(parser: TrackingUrlParser) -> None:
    result = parser.parse("https://example.com/product?utm_content=23859320180330794")

    assert result.campaign_id is None
    assert result.ad_set_id is None
    assert result.ad_id == "23859320180330794"
    assert result.source is None
    assert result.medium is None


def test_numeric_utm_campaign_is_used_as_campaign_fallback(parser: TrackingUrlParser) -> None:
    result = parser.parse("https://example.com/product?utm_campaign=23859320180340794")
    assert result.campaign_id == "23859320180340794"


def test_campaign_name_is_not_used_as_campaign_id(parser: TrackingUrlParser) -> None:
    result = parser.parse("https://example.com/product?utm_campaign=summer_sale")
    assert result.campaign_id is None


def test_primary_campaign_id_wins_over_fallback(parser: TrackingUrlParser) -> None:
    result = parser.parse("https://example.com/product?utm_id=111&utm_campaign=222")
    assert result.campaign_id == "111"


def test_it_supports_partial_custom_parameter_mapping(parser: TrackingUrlParser) -> None:
    result = parser.parse(
        "https://example.com/product?campaign_id=111&adset_id=222&ad_id=333"
        "&utm_source=instagram&utm_medium=paid-social",
        {
            "campaignId": "campaign_id",
            "adSetId": "adset_id",
            "adId": "ad_id",
        },
    )

    assert result.campaign_id == "111"
    assert result.ad_set_id == "222"
    assert result.ad_id == "333"
    assert result.source == "instagram"
    assert result.medium == "paid-social"


def test_fbclid_does_not_produce_entity_identifiers(parser: TrackingUrlParser) -> None:
    result = parser.parse("https://example.com/product?fbclid=opaque-click-id")
    assert result.campaign_id is None
    assert result.ad_set_id is None
    assert result.ad_id is None


def test_url_without_tracking_returns_an_empty_value_object(parser: TrackingUrlParser) -> None:
    result = parser.parse("https://example.com/product?color=blue")
    assert isinstance(result, TrackingIdentifiers)
    assert result.campaign_id is None
    assert result.ad_set_id is None
    assert result.ad_id is None
    assert result.source is None
    assert result.medium is None


def test_url_without_query_returns_an_empty_value_object(parser: TrackingUrlParser) -> None:
    result = parser.parse("https://example.com/product")
    assert isinstance(result, TrackingIdentifiers)
    assert result.campaign_id is None
    assert result.ad_set_id is None
    assert result.ad_id is None
    assert result.source is None
    assert result.medium is None


def test_it_preserves_large_ids_as_strings(parser: TrackingUrlParser) -> None:
    large_id = "999999999999999999999999999999999999"
    result = parser.parse(f"https://example.com/?utm_id={large_id}")
    assert result.campaign_id == large_id
    assert isinstance(result.campaign_id, str)


def test_it_decodes_values_and_uses_the_last_duplicate(parser: TrackingUrlParser) -> None:
    result = parser.parse(
        "https://example.com/?utm_source=first&utm_source=facebook%20ads&utm_medium="
    )
    assert result.source == "facebook ads"
    assert result.medium is None


def test_array_and_empty_tracking_values_are_ignored(parser: TrackingUrlParser) -> None:
    result = parser.parse(
        "https://example.com/?utm_id[]=111&utm_term=%20%20&utm_content="
    )
    assert result.campaign_id is None
    assert result.ad_set_id is None
    assert result.ad_id is None


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "/product?utm_id=111",
        "https:///product?utm_id=111",
        "https://exa mple.com/product?utm_id=111",
        "ftp://example.com/product?utm_id=111",
    ],
)
def test_it_rejects_malformed_urls(parser: TrackingUrlParser, url: str) -> None:
    with pytest.raises(InvalidInputError):
        parser.parse(url)


@pytest.mark.parametrize(
    "mapping",
    [
        {"pixelId": "pixel_id"},
        {"campaignId": ""},
        {"campaignId": "campaign.id"},
        {"campaignId": 123},
        {"campaignId": "utm_term"},
    ],
)
def test_it_rejects_invalid_parameter_mappings(
    parser: TrackingUrlParser,
    mapping: dict[str, Any],
) -> None:
    with pytest.raises(InvalidInputError):
        parser.parse("https://example.com/", mapping)
