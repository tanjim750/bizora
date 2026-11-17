"""Normalisation of raw Campaign payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from metametrics.campaign.dto import CampaignDTO
from metametrics.utils.payload import PayloadReader

__all__ = ["CampaignNormalizer"]


class CampaignNormalizer:
    """Turns a raw Campaign payload into a :class:`CampaignDTO`."""

    def __init__(self) -> None:
        self.reader = PayloadReader("Campaign")

    def normalize(self, campaign: Mapping[str, Any]) -> CampaignDTO:
        """Normalise a decoded Campaign payload."""
        return CampaignDTO(
            id=self.reader.required_string(campaign, "id"),
            name=self.reader.required_string(campaign, "name"),
            status=self.reader.optional_string(campaign, "status"),
            configured_status=self.reader.optional_string(campaign, "configured_status"),
            effective_status=self.reader.optional_string(campaign, "effective_status"),
            objective=self.reader.optional_string(campaign, "objective"),
            created_time=self.reader.optional_datetime(campaign, "created_time"),
            updated_time=self.reader.optional_datetime(campaign, "updated_time"),
        )
