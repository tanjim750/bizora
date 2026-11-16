"""Tests for the Ad normalizer.

Ported from ``tests/Unit/Ad/AdNormalizerTest.php``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from metametrics.ad.normalizer import AdNormalizer
from metametrics.exceptions import UnexpectedResponseError


def test_it_normalizes_a_full_payload() -> None:
    ad = AdNormalizer().normalize(
        {
            "id": "1200000000000003",
            "name": "Creative One",
            "adset_id": "1200000000000002",
            "campaign_id": "1200000000000001",
            "status": "ACTIVE",
            "configured_status": "ACTIVE",
            "effective_status": "ACTIVE",
            "created_time": "2026-08-10T00:00:00+0000",
            "updated_time": "2026-09-01T10:30:00+0000",
        }
    )

    assert ad.id == "1200000000000003"
    assert ad.ad_set_id == "1200000000000002"
    assert ad.campaign_id == "1200000000000001"
    assert ad.created_time == datetime(2026, 8, 10, tzinfo=UTC)


def test_it_leaves_optional_fields_empty() -> None:
    ad = AdNormalizer().normalize({"id": "1", "name": "Ad", "adset_id": "2", "campaign_id": "3"})

    assert ad.status is None
    assert ad.configured_status is None
    assert ad.effective_status is None
    assert ad.created_time is None
    assert ad.updated_time is None


@pytest.mark.parametrize("field", ["id", "name", "adset_id", "campaign_id"])
def test_it_requires_the_identity_fields(field: str) -> None:
    payload = {"id": "1", "name": "Ad", "adset_id": "2", "campaign_id": "3"}
    del payload[field]

    with pytest.raises(UnexpectedResponseError, match=f'requires a valid "{field}" field'):
        AdNormalizer().normalize(payload)


def test_it_rejects_a_malformed_timestamp() -> None:
    with pytest.raises(UnexpectedResponseError, match='field "updated_time" must be a valid timestamp'):
        AdNormalizer().normalize(
            {"id": "1", "name": "Ad", "adset_id": "2", "campaign_id": "3", "updated_time": "nope"}
        )
