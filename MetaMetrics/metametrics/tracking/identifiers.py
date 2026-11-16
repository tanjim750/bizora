"""Value object for tracking identifiers extracted from URLs."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["TrackingIdentifiers"]


@dataclass(frozen=True, slots=True)
class TrackingIdentifiers:
    """Identifiers extracted from an ad tracking URL."""

    campaign_id: str | None = None
    ad_set_id: str | None = None
    ad_id: str | None = None
    source: str | None = None
    medium: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "campaign_id": self.campaign_id,
            "ad_set_id": self.ad_set_id,
            "ad_id": self.ad_id,
            "source": self.source,
            "medium": self.medium,
        }
