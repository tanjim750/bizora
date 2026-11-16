"""Normalisation of raw Ad payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from metametrics.ad.dto import AdDTO
from metametrics.utils.payload import PayloadReader

__all__ = ["AdNormalizer"]


class AdNormalizer:
    """Turns a raw Ad payload into an :class:`AdDTO`."""

    def __init__(self) -> None:
        self.reader = PayloadReader("Ad")

    def normalize(self, ad: Mapping[str, Any]) -> AdDTO:
        """Normalise a decoded Ad payload."""
        return AdDTO(
            id=self.reader.required_string(ad, "id"),
            name=self.reader.required_string(ad, "name"),
            ad_set_id=self.reader.required_string(ad, "adset_id"),
            campaign_id=self.reader.required_string(ad, "campaign_id"),
            status=self.reader.optional_string(ad, "status"),
            configured_status=self.reader.optional_string(ad, "configured_status"),
            effective_status=self.reader.optional_string(ad, "effective_status"),
            created_time=self.reader.optional_datetime(ad, "created_time"),
            updated_time=self.reader.optional_datetime(ad, "updated_time"),
        )
