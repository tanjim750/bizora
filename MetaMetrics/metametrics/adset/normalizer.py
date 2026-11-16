"""Normalisation of raw Ad Set payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from metametrics.adset.dto import AdSetDTO
from metametrics.utils.payload import PayloadReader

__all__ = ["AdSetNormalizer"]


class AdSetNormalizer:
    """Turns a raw Ad Set payload into an :class:`AdSetDTO`."""

    def __init__(self) -> None:
        self.reader = PayloadReader("Ad Set")

    def normalize(self, ad_set: Mapping[str, Any]) -> AdSetDTO:
        """Normalise a decoded Ad Set payload."""
        return AdSetDTO(
            id=self.reader.required_string(ad_set, "id"),
            name=self.reader.required_string(ad_set, "name"),
            campaign_id=self.reader.required_string(ad_set, "campaign_id"),
            status=self.reader.optional_string(ad_set, "status"),
            configured_status=self.reader.optional_string(ad_set, "configured_status"),
            effective_status=self.reader.optional_string(ad_set, "effective_status"),
            optimization_goal=self.reader.optional_string(ad_set, "optimization_goal"),
            billing_event=self.reader.optional_string(ad_set, "billing_event"),
            daily_budget=self.reader.optional_string(ad_set, "daily_budget"),
            lifetime_budget=self.reader.optional_string(ad_set, "lifetime_budget"),
            created_time=self.reader.optional_datetime(ad_set, "created_time"),
            updated_time=self.reader.optional_datetime(ad_set, "updated_time"),
            start_time=self.reader.optional_datetime(ad_set, "start_time"),
            end_time=self.reader.optional_datetime(ad_set, "end_time"),
        )
