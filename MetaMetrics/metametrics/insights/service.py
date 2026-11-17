"""Retrieval and analysis of Meta performance data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any
from urllib.parse import quote

from metametrics.account.service import AccountService
from metametrics.client import MetaClientProtocol, QueryValue, Request
from metametrics.config import MetaConfig
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.exceptions import UnexpectedResponseError
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.filter_fields import InsightsFilterField
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.normalizer import InsightsNormalizer
from metametrics.insights.parsers.insights_parser import InsightsParser
from metametrics.insights.parsers.parsed import ParsedInsights
from metametrics.insights.query import InsightsQuery
from metametrics.insights.response import InsightsResponse
from metametrics.pagination.paginator import Paginator
from metametrics.query.builder import QueryBuilder
from metametrics.utils.json import php_json_dumps

__all__ = ["InsightsService"]

RAW_CPR_FIELDS = ("spend", "actions", "cost_per_action_type")

AD_SET_CONFIGURATION_FIELDS = ("id", "optimization_goal", "promoted_object")

_IDENTITY_FIELDS: dict[InsightsLevel, tuple[str, ...]] = {
    InsightsLevel.ACCOUNT: ("account_id", "account_name"),
    InsightsLevel.CAMPAIGN: ("campaign_id", "campaign_name"),
    InsightsLevel.AD_SET: ("campaign_id", "adset_id", "adset_name"),
    InsightsLevel.AD: ("campaign_id", "adset_id", "ad_id", "ad_name"),
}


class InsightsService:
    """Queries Meta performance data and normalises the result."""

    def __init__(
        self,
        client: MetaClientProtocol,
        config: MetaConfig,
        registry: MetricRegistry | None = None,
        parser: InsightsParser | None = None,
        normalizer: InsightsNormalizer | None = None,
        paginator: Paginator | None = None,
        query_builder: QueryBuilder | None = None,
        error_mapper: MetaErrorMapper | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.registry = registry or MetricRegistry()
        self.parser = parser or InsightsParser(registry=self.registry)
        self.normalizer = normalizer or InsightsNormalizer()
        self.query_builder = query_builder or QueryBuilder()
        self.error_mapper = error_mapper or MetaErrorMapper()
        self.paginator = paginator or Paginator(client, self.error_mapper)

    def get(self, query: InsightsQuery) -> list[InsightsDTO]:
        """Run an Insights query and return the normalised rows."""
        foundational_metrics = self.registry.foundational_metrics(query.metrics)

        items = self.paginator.fetch_all(
            Request(
                method="GET",
                path=(
                    f"/{self.config.api_version}/"
                    f"{quote(query.entity_id or self.config.ad_account_id, safe='')}/insights"
                ),
                query=self._parameters(query),
            )
        )

        ad_set_configurations: dict[str, Mapping[str, Any]] = {}
        if query.level == InsightsLevel.AD_SET and query.include_ad_set_configuration:
            ad_set_configurations = self._ad_set_configurations(items)

        parsed_rows: list[ParsedInsights] = []
        currency: str | None = None

        for item in items:
            ad_set_id = item.get("adset_id")
            configuration = ad_set_configurations.get(ad_set_id) if isinstance(ad_set_id, str) else None

            parsed = self.parser.parse(item, query.level, foundational_metrics, configuration)

            if parsed.currency is not None:
                if currency is not None and currency != parsed.currency:
                    raise UnexpectedResponseError("Meta Insights returned conflicting account currencies.")

                currency = parsed.currency

            parsed_rows.append(parsed)

        if not parsed_rows:
            return []

        resolved_currency = currency if currency is not None else self._account_currency()

        return [
            self.normalizer.normalize(
                replace(parsed, currency=resolved_currency),
                query.level,
                query.metrics,
            )
            for parsed in parsed_rows
        ]

    def get_response(self, query: InsightsQuery) -> InsightsResponse:
        """Run an Insights query and return the rows inside their envelope."""
        data = self.get(query)

        currency = data[0].currency if data else self._account_currency()

        if currency is None:
            raise UnexpectedResponseError("Meta Insights returned no account currency.")

        return InsightsResponse(level=query.level, currency=currency, data=tuple(data))

    def _account_currency(self) -> str:
        return AccountService(self.client, self.config, error_mapper=self.error_mapper).get_currency()

    def _parameters(self, query: InsightsQuery) -> dict[str, QueryValue]:
        fields: dict[str, str] = {}

        for field in (
            *_IDENTITY_FIELDS[query.level],
            "date_start",
            "date_stop",
            "account_currency",
            *RAW_CPR_FIELDS,
            *self.registry.meta_fields(query.metrics),
        ):
            fields.setdefault(field, field)

        parameters: dict[str, QueryValue] = {
            "fields": ",".join(fields.values()),
            "level": query.level.value,
            "time_range": php_json_dumps(query.date_range.to_dict()),
        }

        if query.daily:
            parameters["time_increment"] = 1

        filtering = self.query_builder.encode_filters(query.filters, InsightsFilterField.values())
        if filtering is not None:
            parameters["filtering"] = filtering

        if query.limit is not None:
            parameters["limit"] = query.limit

        return parameters

    def _ad_set_configurations(self, items: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
        ids: dict[str, str] = {}

        for item in items:
            ad_set_id = item.get("adset_id")

            if not isinstance(ad_set_id, str) or ad_set_id == "":
                raise UnexpectedResponseError('Ad Set-level Insights require a valid "adset_id" field.')

            ids[ad_set_id] = ad_set_id

        configurations: dict[str, Mapping[str, Any]] = {}

        for ad_set_id in ids:
            response = self.client.send(
                Request(
                    method="GET",
                    path=f"/{self.config.api_version}/{quote(ad_set_id, safe='')}",
                    query={"fields": ",".join(AD_SET_CONFIGURATION_FIELDS)},
                )
            )

            if not response.is_successful():
                raise self.error_mapper.map(response, "Ad Set", ad_set_id)

            body = response.body
            if not isinstance(body, dict):
                raise UnexpectedResponseError("Meta returned malformed Ad Set configuration data.")

            if body.get("id") != ad_set_id:
                raise UnexpectedResponseError(
                    f'Meta did not return valid configuration for Ad Set "{ad_set_id}".'
                )

            configurations[ad_set_id] = body

        return configurations
