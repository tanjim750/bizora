"""Retrieval of Ad Account metadata and currency."""

from __future__ import annotations

import re

from metametrics.account.dto import AccountDTO
from metametrics.account.normalizer import AccountNormalizer
from metametrics.client import MetaClientProtocol, Request
from metametrics.config import MetaConfig
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.exceptions import UnexpectedResponseError

__all__ = ["AccountService"]

_CURRENCY_PATTERN: re.Pattern[str] = re.compile(r"\A[A-Z]{3}\Z")

_ACCOUNT_FIELDS = ("id", "name", "account_id", "account_status", "currency", "timezone_name")


class AccountService:
    """Reads the configured Ad Account."""

    def __init__(
        self,
        client: MetaClientProtocol,
        config: MetaConfig,
        normalizer: AccountNormalizer | None = None,
        error_mapper: MetaErrorMapper | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.normalizer = normalizer or AccountNormalizer()
        self.error_mapper = error_mapper or MetaErrorMapper()

    def get_currency(self) -> str:
        """Return the Ad Account currency code, for example ``USD``."""
        account_id = self.config.ad_account_id

        response = self.client.send(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{account_id}",
                query={"fields": "currency"},
            )
        )

        if not response.is_successful():
            raise self.error_mapper.map(response, "Ad Account", account_id)

        body = response.body
        if not isinstance(body, dict) or body.get("id") != account_id:
            raise UnexpectedResponseError(
                "Meta returned an unexpected Ad Account currency response.",
                http_status=response.status_code,
                resource_type="Ad Account",
                resource_id=account_id,
            )

        currency = body.get("currency")
        if not isinstance(currency, str) or not _CURRENCY_PATTERN.match(currency):
            raise UnexpectedResponseError(
                "Meta Ad Account response requires a valid currency code.",
                http_status=response.status_code,
                resource_type="Ad Account",
                resource_id=account_id,
            )

        return currency

    def get(self) -> AccountDTO:
        """Return the full Ad Account metadata."""
        account_id = self.config.ad_account_id

        response = self.client.send(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{account_id}",
                query={"fields": ",".join(_ACCOUNT_FIELDS)},
            )
        )

        if not response.is_successful():
            raise self.error_mapper.map(response, "Ad Account", account_id)

        body = response.body
        if not isinstance(body, dict):
            raise UnexpectedResponseError(
                "Meta returned a malformed Ad Account response.",
                http_status=response.status_code,
            )

        account = self.normalizer.normalize(body)

        if account.id != account_id or account.account_id != account_id[4:]:
            raise UnexpectedResponseError(
                "Meta returned data for an unexpected Ad Account.",
                http_status=response.status_code,
                resource_type="Ad Account",
                resource_id=account_id,
            )

        return account
