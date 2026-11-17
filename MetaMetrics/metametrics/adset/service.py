"""Retrieval of Ad Set data."""

from __future__ import annotations

from urllib.parse import quote

from metametrics.adset.dto import AdSetDTO
from metametrics.adset.normalizer import AdSetNormalizer
from metametrics.adset.query import AdSetQuery
from metametrics.client import MetaClientProtocol, Request
from metametrics.config import MetaConfig
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.exceptions import InvalidInputError, UnexpectedResponseError
from metametrics.pagination.paginator import Paginator
from metametrics.query.fields import Fields

__all__ = ["AdSetService"]

DEFAULT_FIELDS = (
    "id",
    "name",
    "campaign_id",
    "status",
    "configured_status",
    "effective_status",
    "optimization_goal",
    "billing_event",
    "daily_budget",
    "lifetime_budget",
    "created_time",
    "updated_time",
    "start_time",
    "end_time",
)

REQUIRED_FIELDS = ("id", "name", "campaign_id")


class AdSetService:
    """Lists and looks up Ad Sets."""

    def __init__(
        self,
        client: MetaClientProtocol,
        config: MetaConfig,
        normalizer: AdSetNormalizer | None = None,
        paginator: Paginator | None = None,
        error_mapper: MetaErrorMapper | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.normalizer = normalizer or AdSetNormalizer()
        self.error_mapper = error_mapper or MetaErrorMapper()
        self.paginator = paginator or Paginator(client, self.error_mapper)

    def all(self, query: AdSetQuery | None = None) -> list[AdSetDTO]:
        """Return every Ad Set of the configured Ad Account."""
        return self.collection(self.config.ad_account_id, query)

    def for_campaign(self, campaign_id: str, query: AdSetQuery | None = None) -> list[AdSetDTO]:
        """Return every Ad Set of one Campaign."""
        if not campaign_id or campaign_id.strip() == "":
            raise InvalidInputError("Campaign ID must not be empty.")

        return self.collection(campaign_id, query)

    def find(self, ad_set_id: str, fields: Fields | None = None) -> AdSetDTO:
        """Return a single Ad Set by its object id."""
        if not ad_set_id or ad_set_id.strip() == "":
            raise InvalidInputError("Ad Set ID must not be empty.")

        response = self.client.send(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{quote(ad_set_id, safe='')}",
                query={"fields": self.ad_set_fields(fields).to_query_value()},
            )
        )

        if not response.is_successful():
            raise self.error_mapper.map(response, "Ad Set", ad_set_id)

        body = response.body
        if not isinstance(body, dict):
            raise UnexpectedResponseError("Meta returned a malformed Ad Set response.")

        return self.normalizer.normalize(body)

    def collection(self, parent_id: str, query: AdSetQuery | None = None) -> list[AdSetDTO]:
        """Return the Ad Sets of an Ad Account or Campaign."""
        query = query or AdSetQuery()
        fields = self.ad_set_fields(query.fields)

        parameters = {"fields": fields.to_query_value(), **query.parameters()}

        items = self.paginator.fetch_all(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{quote(parent_id, safe='')}/adsets",
                query=parameters,
            )
        )

        return [self.normalizer.normalize(item) for item in items]

    @staticmethod
    def ad_set_fields(fields: Fields | None) -> Fields:
        """Validate and complete the requested Ad Set fields."""
        fields = fields or Fields(list(DEFAULT_FIELDS))

        for field in fields.values:
            if field not in DEFAULT_FIELDS:
                raise InvalidInputError(f'Unsupported normalized Ad Set field "{field}".')

        return fields.with_required(list(REQUIRED_FIELDS))
