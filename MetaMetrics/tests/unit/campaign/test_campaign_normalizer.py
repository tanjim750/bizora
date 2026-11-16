"""Tests for the Campaign normalizer.

Ported from ``tests/Unit/Campaign/CampaignNormalizerTest.php``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from metametrics.campaign.normalizer import CampaignNormalizer
from metametrics.exceptions import UnexpectedResponseError


def test_it_normalizes_a_full_payload() -> None:
    campaign = CampaignNormalizer().normalize(
        {
            "id": "1200000000000001",
            "name": "Prospecting",
            "status": "ACTIVE",
            "configured_status": "ACTIVE",
            "effective_status": "PAUSED",
            "objective": "OUTCOME_SALES",
            "created_time": "2026-08-10T00:00:00+0000",
            "updated_time": "2026-09-01T10:30:00+0000",
        }
    )

    assert campaign.id == "1200000000000001"
    assert campaign.name == "Prospecting"
    assert campaign.status == "ACTIVE"
    assert campaign.configured_status == "ACTIVE"
    assert campaign.effective_status == "PAUSED"
    assert campaign.objective == "OUTCOME_SALES"
    assert campaign.created_time == datetime(2026, 8, 10, tzinfo=UTC)


def test_it_leaves_optional_fields_empty() -> None:
    campaign = CampaignNormalizer().normalize({"id": "1", "name": "Campaign"})

    assert campaign.status is None
    assert campaign.configured_status is None
    assert campaign.effective_status is None
    assert campaign.objective is None
    assert campaign.created_time is None
    assert campaign.updated_time is None


@pytest.mark.parametrize("field", ["id", "name"])
def test_it_requires_an_id_and_a_name(field: str) -> None:
    payload = {"id": "1", "name": "Campaign"}
    del payload[field]

    with pytest.raises(UnexpectedResponseError, match=f'requires a valid "{field}" field'):
        CampaignNormalizer().normalize(payload)


def test_it_rejects_an_empty_optional_string() -> None:
    with pytest.raises(UnexpectedResponseError, match='field "status" must be a string'):
        CampaignNormalizer().normalize({"id": "1", "name": "Campaign", "status": ""})


def test_it_rejects_a_malformed_timestamp() -> None:
    with pytest.raises(UnexpectedResponseError, match='field "created_time" must be a valid timestamp'):
        CampaignNormalizer().normalize({"id": "1", "name": "Campaign", "created_time": "not-a-date"})
