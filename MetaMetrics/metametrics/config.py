"""Configuration for the Meta Marketing API client."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .exceptions import InvalidConfigurationError

__all__ = ["ConfigurationValidator", "MetaConfig"]

_AD_ACCOUNT_ID_PATTERN: re.Pattern[str] = re.compile(r"\Aact_[0-9]+\Z")
_NUMERIC_ACCOUNT_ID_PATTERN: re.Pattern[str] = re.compile(r"\A[0-9]+\Z")
_API_VERSION_PATTERN: re.Pattern[str] = re.compile(r"\Av[0-9]+\.[0-9]+\Z")


class ConfigurationValidator:
    """Validation helpers for :class:`MetaConfig`."""

    @staticmethod
    def validate_access_token(access_token: str) -> None:
        if not isinstance(access_token, str) or access_token.strip() == "":
            raise InvalidConfigurationError("Meta Access Token must not be empty.")

    @staticmethod
    def normalize_ad_account_id(ad_account_id: str) -> str:
        if not isinstance(ad_account_id, str):
            raise InvalidConfigurationError('Meta Ad Account ID must follow the format "act_<numeric-id>".')

        candidate = ad_account_id
        if _NUMERIC_ACCOUNT_ID_PATTERN.match(candidate):
            candidate = f"act_{candidate}"

        if not _AD_ACCOUNT_ID_PATTERN.match(candidate):
            raise InvalidConfigurationError('Meta Ad Account ID must follow the format "act_<numeric-id>".')

        return candidate

    @staticmethod
    def validate_api_version(api_version: str) -> None:
        if not isinstance(api_version, str) or not _API_VERSION_PATTERN.match(api_version):
            raise InvalidConfigurationError('Meta Marketing API Version must follow the format "vXX.X".')


@dataclass(frozen=True, slots=True)
class MetaConfig:
    """Immutable client configuration.

    The access token is redacted from ``repr()`` and cannot be restored from a
    serialised payload, mirroring the PHP ``__debugInfo`` / ``__serialize`` /
    ``__unserialize`` behaviour.
    """

    access_token: str
    ad_account_id: str
    api_version: str

    def __post_init__(self) -> None:
        ConfigurationValidator.validate_access_token(self.access_token)
        ConfigurationValidator.validate_api_version(self.api_version)
        normalized = ConfigurationValidator.normalize_ad_account_id(self.ad_account_id)
        object.__setattr__(self, "ad_account_id", normalized)

    def __repr__(self) -> str:
        return (
            f"MetaConfig(access_token='[REDACTED]', ad_account_id={self.ad_account_id!r}, "
            f"api_version={self.api_version!r})"
        )

    def __getstate__(self) -> dict[str, object]:
        """Return a redacted snapshot; the access token is never serialised."""
        return {
            "access_token": "[REDACTED]",
            "ad_account_id": self.ad_account_id,
            "api_version": self.api_version,
        }

    def __setstate__(self, state: object) -> None:
        """Refuse to restore a configuration; a redacted snapshot holds no credentials."""
        raise RuntimeError("MetaConfig cannot be deserialized.")
