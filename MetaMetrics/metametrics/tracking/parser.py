"""Tracking URL parser extracting Meta entity identifiers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import SplitResult, parse_qsl, urlsplit

from metametrics.exceptions import InvalidInputError
from metametrics.tracking.identifiers import TrackingIdentifiers

__all__ = ["TrackingUrlParser"]

_DEFAULT_PARAMETER_MAPPING: dict[str, str] = {
    "campaignId": "utm_id",
    "adSetId": "utm_term",
    "adId": "utm_content",
    "source": "utm_source",
    "medium": "utm_medium",
}

_PARAM_NAME_RE: re.Pattern[str] = re.compile(r"\A[a-zA-Z][a-zA-Z0-9_-]*\Z")
_NUMERIC_RE: re.Pattern[str] = re.compile(r"\A[0-9]+\Z")
_HOST_RE: re.Pattern[str] = re.compile(r"\A[a-zA-Z0-9.-]+(:[0-9]+)?\Z")


class TrackingUrlParser:
    """Parses ad tracking URLs according to Meta conventions."""

    def parse(
        self,
        url: str,
        parameter_mapping: Mapping[str, str] | None = None,
    ) -> TrackingIdentifiers:
        """Parse identifiers from a tracking URL with optional mapping overrides."""
        parts = self._validate_url(url)
        mapping = self._validate_mapping(parameter_mapping)

        parameters: dict[str, str] = {}
        if parts.query:
            for key, val in parse_qsl(parts.query, keep_blank_values=True):
                parameters[key] = val

        def get_param(name: str) -> str | None:
            v = parameters.get(name)
            return v if v is not None and v.strip() != "" else None

        campaign_id = get_param(mapping["campaignId"])
        if campaign_id is None:
            fallback = get_param("utm_campaign")
            if fallback is not None and _NUMERIC_RE.match(fallback):
                campaign_id = fallback

        return TrackingIdentifiers(
            campaign_id=campaign_id,
            ad_set_id=get_param(mapping["adSetId"]),
            ad_id=get_param(mapping["adId"]),
            source=get_param(mapping["source"]),
            medium=get_param(mapping["medium"]),
        )

    def _validate_url(self, url: str) -> SplitResult:
        if not url or not url.strip():
            raise InvalidInputError("Tracking URL must not be empty.")

        if any(c in url for c in (" ", "\t", "\n", "\r")):
            raise InvalidInputError("Tracking URL must be a valid HTTP or HTTPS URL.")

        try:
            parts = urlsplit(url)
        except Exception as exc:
            raise InvalidInputError("Tracking URL must be a valid HTTP or HTTPS URL.") from exc

        if not parts.scheme or not parts.netloc:
            raise InvalidInputError("Tracking URL must be a valid HTTP or HTTPS URL.")

        if parts.scheme.lower() not in ("http", "https"):
            raise InvalidInputError("Tracking URL must be a valid HTTP or HTTPS URL.")

        if not _HOST_RE.match(parts.netloc):
            raise InvalidInputError("Tracking URL must be a valid HTTP or HTTPS URL.")

        return parts

    def _validate_mapping(self, overrides: Mapping[str, str] | None) -> dict[str, str]:
        if overrides:
            for identifier, parameter in overrides.items():
                if not isinstance(identifier, str) or identifier not in _DEFAULT_PARAMETER_MAPPING:
                    raise InvalidInputError("Tracking parameter mapping contains an unsupported identifier.")

                if not isinstance(parameter, str) or not _PARAM_NAME_RE.match(parameter):
                    raise InvalidInputError("Tracking parameter names must be non-empty URL parameter names.")

        mapping = {**_DEFAULT_PARAMETER_MAPPING, **(overrides or {})}

        if len(set(mapping.values())) != len(mapping):
            raise InvalidInputError("Tracking parameter mapping must use unique parameter names.")

        return mapping
