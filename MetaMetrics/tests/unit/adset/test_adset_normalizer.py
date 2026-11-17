"""Tests for the Ad Set normalizer.

Ported from ``tests/Unit/AdSet/AdSetNormalizerTest.php``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from metametrics.adset.normalizer import AdSetNormalizer
from metametrics.exceptions import UnexpectedResponseError


def test_it_normalizes_a_full_payload() -> None:
    ad_set = AdSetNormalizer().normalize(
        {
            "id": "1200000000000002",
            "name": "Lookalike 1%",
            "campaign_id": "1200000000000001",
            "status": "ACTIVE",
            "configured_status": "ACTIVE",
            "effective_status": "ACTIVE",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "billing_event": "IMPRESSIONS",
            "daily_budget": "5000",
            "lifetime_budget": "100000",
            "created_time": "2026-08-10T00:00:00+0000",
            "updated_time": "2026-09-01T10:30:00+0000",
            "start_time": "2026-08-11T00:00:00+0000",
            "end_time": "2026-10-01T00:00:00+0000",
        }
    )

    assert ad_set.id == "1200000000000002"
    assert ad_set.campaign_id == "1200000000000001"
    assert ad_set.optimization_goal == "OFFSITE_CONVERSIONS"
    assert ad_set.daily_budget == "5000"
    assert ad_set.created_time == datetime(2026, 8, 10, tzinfo=UTC)
    assert ad_set.end_time == datetime(2026, 10, 1, tzinfo=UTC)


def test_it_leaves_optional_fields_empty() -> None:
    ad_set = AdSetNormalizer().normalize({"id": "1", "name": "Ad Set", "campaign_id": "2"})

    assert ad_set.status is None
    assert ad_set.daily_budget is None
    assert ad_set.start_time is None
    assert ad_set.end_time is None


@pytest.mark.parametrize("field", ["id", "name", "campaign_id"])
def test_it_requires_the_identity_fields(field: str) -> None:
    payload = {"id": "1", "name": "Ad Set", "campaign_id": "2"}
    del payload[field]

    with pytest.raises(UnexpectedResponseError, match=f'requires a valid "{field}" field'):
        AdSetNormalizer().normalize(payload)


def test_it_rejects_a_malformed_timestamp() -> None:
    with pytest.raises(UnexpectedResponseError, match='field "start_time" must be a valid timestamp'):
        AdSetNormalizer().normalize({"id": "1", "name": "Ad Set", "campaign_id": "2", "start_time": "nope"})
