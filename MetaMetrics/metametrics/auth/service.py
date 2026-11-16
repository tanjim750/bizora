"""Authentication against the configured Meta Ad Account."""

from __future__ import annotations

from dataclasses import dataclass

from metametrics.client import MetaClientProtocol, Request
from metametrics.config import MetaConfig
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.exceptions import UnexpectedResponseError

__all__ = ["AuthenticationResult", "AuthenticationService"]


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """The outcome of a successful Ad Account validation."""

    account_id: str

    @property
    def authenticated(self) -> bool:
        return True

    @property
    def account_accessible(self) -> bool:
        return True


class AuthenticationService:
    """Validates that the configured token can reach the configured Ad Account."""

    def __init__(
        self,
        client: MetaClientProtocol,
        config: MetaConfig,
        error_mapper: MetaErrorMapper | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.error_mapper = error_mapper or MetaErrorMapper()

    def validate(self) -> AuthenticationResult:
        """Validate the credentials against the configured Ad Account."""
        response = self.client.send(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{self.config.ad_account_id}",
                query={"fields": "id"},
            )
        )

        if not response.is_successful():
            raise self.error_mapper.map(response, "Ad Account", self.config.ad_account_id)

        body = response.body
        if not isinstance(body, dict) or body.get("id") != self.config.ad_account_id:
            raise UnexpectedResponseError(
                "Meta returned an unexpected response while validating the Ad Account.",
                http_status=response.status_code,
            )

        return AuthenticationResult(account_id=self.config.ad_account_id)
