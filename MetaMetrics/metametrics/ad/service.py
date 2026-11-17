"""Retrieval of Ad data."""

from __future__ import annotations

from urllib.parse import quote

from metametrics.ad.dto import AdDTO
from metametrics.ad.normalizer import AdNormalizer
from metametrics.ad.query import AdQuery
from metametrics.client import MetaClientProtocol, Request
from metametrics.config import MetaConfig
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.exceptions import InvalidInputError, UnexpectedResponseError
from metametrics.pagination.paginator import Paginator
from metametrics.query.fields import Fields

__all__ = ["AdService"]

DEFAULT_FIELDS = (
    "id",
    "name",
    "adset_id",
    "campaign_id",
    "status",
    "configured_status",
    "effective_status",
    "created_time",
    "updated_time",
)

REQUIRED_FIELDS = ("id", "name", "adset_id", "campaign_id")


class AdService:
    """Lists and looks up Ads."""

    def __init__(
        self,
        client: MetaClientProtocol,
        config: MetaConfig,
        normalizer: AdNormalizer | None = None,
        paginator: Paginator | None = None,
        error_mapper: MetaErrorMapper | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.normalizer = normalizer or AdNormalizer()
        self.error_mapper = error_mapper or MetaErrorMapper()
        self.paginator = paginator or Paginator(client, self.error_mapper)

    def all(self, query: AdQuery | None = None) -> list[AdDTO]:
        """Return every Ad of the configured Ad Account."""
        return self.collection(self.config.ad_account_id, query)

    def for_campaign(self, campaign_id: str, query: AdQuery | None = None) -> list[AdDTO]:
        """Return every Ad of one Campaign."""
        return self.collection(self._required_id(campaign_id, "Campaign"), query)

    def for_ad_set(self, ad_set_id: str, query: AdQuery | None = None) -> list[AdDTO]:
        """Return every Ad of one Ad Set."""
        return self.collection(self._required_id(ad_set_id, "Ad Set"), query)

    def find(self, ad_id: str, fields: Fields | None = None) -> AdDTO:
        """Return a single Ad by its object id."""
        ad_id = self._required_id(ad_id, "Ad")

        response = self.client.send(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{quote(ad_id, safe='')}",
                query={"fields": self.ad_fields(fields).to_query_value()},
            )
        )

        if not response.is_successful():
            raise self.error_mapper.map(response, "Ad", ad_id)

        body = response.body
        if not isinstance(body, dict):
            raise UnexpectedResponseError("Meta returned a malformed Ad response.")

        return self.normalizer.normalize(body)

    def collection(self, parent_id: str, query: AdQuery | None = None) -> list[AdDTO]:
        """Return the Ads of an Ad Account, Campaign, or Ad Set."""
        query = query or AdQuery()
        fields = self.ad_fields(query.fields)

        parameters = {"fields": fields.to_query_value(), **query.parameters()}

        items = self.paginator.fetch_all(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{quote(parent_id, safe='')}/ads",
                query=parameters,
            )
        )

        return [self.normalizer.normalize(item) for item in items]

    @staticmethod
    def ad_fields(fields: Fields | None) -> Fields:
        """Validate and complete the requested Ad fields."""
        fields = fields or Fields(list(DEFAULT_FIELDS))

        for field in fields.values:
            if field not in DEFAULT_FIELDS:
                raise InvalidInputError(f'Unsupported normalized Ad field "{field}".')

        return fields.with_required(list(REQUIRED_FIELDS))

    @staticmethod
    def _required_id(value: str, label: str) -> str:
        if not value or value.strip() == "":
            raise InvalidInputError(f"{label} ID must not be empty.")

        return value
