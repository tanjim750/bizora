"""Retrieval of Campaign data."""

from __future__ import annotations

from urllib.parse import quote

from metametrics.campaign.dto import CampaignDTO
from metametrics.campaign.normalizer import CampaignNormalizer
from metametrics.campaign.query import CampaignQuery
from metametrics.client import MetaClientProtocol, Request
from metametrics.config import MetaConfig
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.exceptions import InvalidInputError, UnexpectedResponseError
from metametrics.pagination.paginator import Paginator
from metametrics.query.fields import Fields

__all__ = ["CampaignService"]

DEFAULT_FIELDS = (
    "id",
    "name",
    "status",
    "configured_status",
    "effective_status",
    "objective",
    "created_time",
    "updated_time",
)

REQUIRED_FIELDS = ("id", "name")


class CampaignService:
    """Lists and looks up Campaigns."""

    def __init__(
        self,
        client: MetaClientProtocol,
        config: MetaConfig,
        normalizer: CampaignNormalizer | None = None,
        paginator: Paginator | None = None,
        error_mapper: MetaErrorMapper | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.normalizer = normalizer or CampaignNormalizer()
        self.error_mapper = error_mapper or MetaErrorMapper()
        self.paginator = paginator or Paginator(client, self.error_mapper)

    def all(self, query: CampaignQuery | None = None) -> list[CampaignDTO]:
        """Return every Campaign of the configured Ad Account."""
        query = query or CampaignQuery()
        fields = self.campaign_fields(query.fields)

        parameters = {"fields": fields.to_query_value(), **query.parameters()}

        items = self.paginator.fetch_all(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{self.config.ad_account_id}/campaigns",
                query=parameters,
            )
        )

        return [self.normalizer.normalize(item) for item in items]

    def find(self, campaign_id: str, fields: Fields | None = None) -> CampaignDTO:
        """Return a single Campaign by its object id."""
        if not campaign_id or campaign_id.strip() == "":
            raise InvalidInputError("Campaign ID must not be empty.")

        response = self.client.send(
            Request(
                method="GET",
                path=f"/{self.config.api_version}/{quote(campaign_id, safe='')}",
                query={"fields": self.campaign_fields(fields).to_query_value()},
            )
        )

        if not response.is_successful():
            raise self.error_mapper.map(response, "Campaign", campaign_id)

        body = response.body
        if not isinstance(body, dict):
            raise UnexpectedResponseError("Meta returned a malformed Campaign response.")

        return self.normalizer.normalize(body)

    @staticmethod
    def campaign_fields(fields: Fields | None) -> Fields:
        """Validate and complete the requested Campaign fields."""
        fields = fields or Fields(list(DEFAULT_FIELDS))

        for field in fields.values:
            if field not in DEFAULT_FIELDS:
                raise InvalidInputError(f'Unsupported normalized Campaign field "{field}".')

        return fields.with_required(list(REQUIRED_FIELDS))
