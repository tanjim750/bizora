"""Parsing of raw Meta Insights rows."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from metametrics.exceptions import UnexpectedResponseError
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.parsers.action_parser import ActionParser
from metametrics.insights.parsers.action_value_parser import ActionValueParser
from metametrics.insights.parsers.parsed import ParsedInsights
from metametrics.insights.raw_data import InsightsRawData
from metametrics.utils.numbers import is_numeric

__all__ = ["InsightsParser"]

_CURRENCY_PATTERN: re.Pattern[str] = re.compile(r"\A[A-Z]{3}\Z")

_IDENTITY_FIELDS: dict[InsightsLevel, tuple[str, str]] = {
    InsightsLevel.ACCOUNT: ("account_id", "account_name"),
    InsightsLevel.CAMPAIGN: ("campaign_id", "campaign_name"),
    InsightsLevel.AD_SET: ("adset_id", "adset_name"),
    InsightsLevel.AD: ("ad_id", "ad_name"),
}


class InsightsParser:
    """Turns raw Meta Insights rows into :class:`ParsedInsights` values."""

    def __init__(
        self,
        action_parser: ActionParser | None = None,
        action_value_parser: ActionValueParser | None = None,
        registry: MetricRegistry | None = None,
    ) -> None:
        self.action_parser = action_parser or ActionParser()
        self.action_value_parser = action_value_parser or ActionValueParser()
        self.registry = registry or MetricRegistry()

    def parse(
        self,
        row: Mapping[str, Any],
        level: InsightsLevel,
        foundational_metrics: Sequence[Metric],
        ad_set_configuration: Mapping[str, Any] | None = None,
    ) -> ParsedInsights:
        """Parse one raw Insights row."""
        id_field, name_field = _IDENTITY_FIELDS[level]

        return ParsedInsights(
            currency=self._currency(row),
            entity_id=self._required_string(row, id_field),
            entity_name=self._optional_string(row, name_field),
            campaign_id=None if level == InsightsLevel.ACCOUNT else self._required_string(row, "campaign_id"),
            ad_set_id=(
                self._required_string(row, "adset_id")
                if level in (InsightsLevel.AD_SET, InsightsLevel.AD)
                else None
            ),
            ad_id=self._required_string(row, "ad_id") if level == InsightsLevel.AD else None,
            date_range=DateRange(
                self._required_string(row, "date_start"),
                self._required_string(row, "date_stop"),
            ),
            foundational=self._foundational(row, foundational_metrics),
            raw_data=InsightsRawData(
                spend=self._raw_number(row, "spend"),
                actions=self._raw_list(row, "actions"),
                cost_per_action_type=self._raw_list(row, "cost_per_action_type"),
                optimization_goal=self._configuration_string(ad_set_configuration, "optimization_goal"),
                promoted_object=self._promoted_object(ad_set_configuration),
            ),
        )

    def _currency(self, row: Mapping[str, Any]) -> str | None:
        if "account_currency" not in row:
            return None

        currency = row["account_currency"]

        if not isinstance(currency, str) or not _CURRENCY_PATTERN.match(currency):
            raise UnexpectedResponseError("Meta Insights requires a valid account_currency code.")

        return currency

    def _foundational(
        self,
        row: Mapping[str, Any],
        metrics: Sequence[Metric],
    ) -> dict[str, float | None]:
        values: dict[str, float | None] = {}

        needs_purchases = Metric.PURCHASES in metrics
        needs_purchase_value = Metric.PURCHASE_VALUE in metrics
        can_align_purchases = (
            needs_purchases
            and needs_purchase_value
            and row.get("actions") is not None
            and row.get("action_values") is not None
        )

        shared_action_type: str | None = None
        if can_align_purchases:
            shared_action_type = self.action_parser.common_purchase_action_type(
                row.get("actions"),
                row.get("action_values"),
            )

        for metric in metrics:
            if metric == Metric.PURCHASES:
                if can_align_purchases:
                    values[metric.value] = self.action_parser.purchases_for_type(
                        row.get("actions"), shared_action_type
                    )
                else:
                    values[metric.value] = self.action_parser.purchases(row.get("actions"))
            elif metric == Metric.PURCHASE_VALUE:
                if can_align_purchases:
                    values[metric.value] = self.action_value_parser.purchase_value_for_type(
                        row.get("action_values"), shared_action_type
                    )
                else:
                    values[metric.value] = self.action_value_parser.purchase_value(row.get("action_values"))
            else:
                values[metric.value] = self._optional_number(row, self.registry.source_field(metric))

        return values

    @staticmethod
    def _required_string(data: Mapping[str, Any], field: str) -> str:
        value = data.get(field)

        if not isinstance(value, str) or value == "":
            raise UnexpectedResponseError(f'Meta Insights row requires a valid "{field}" field.')

        return value

    @staticmethod
    def _optional_string(data: Mapping[str, Any], field: str) -> str | None:
        if field not in data or data[field] is None:
            return None

        value = data[field]
        if not isinstance(value, str) or value == "":
            raise UnexpectedResponseError(f'Meta Insights "{field}" field must be a string.')

        return value

    @staticmethod
    def _optional_number(data: Mapping[str, Any], field: str | None) -> float | None:
        if field is None or field not in data or data[field] is None:
            return None

        value = data[field]
        if not is_numeric(value):
            raise UnexpectedResponseError(f'Meta Insights "{field}" field must be numeric.')

        number = float(value.strip()) if isinstance(value, str) else float(value)

        if not math.isfinite(number):
            raise UnexpectedResponseError(f'Meta Insights "{field}" field must be finite.')

        return number

    @staticmethod
    def _raw_number(data: Mapping[str, Any], field: str) -> str | int | float | None:
        if field not in data or data[field] is None:
            return None

        value = data[field]
        if not is_numeric(value):
            raise UnexpectedResponseError(f'Meta Insights "{field}" field must be numeric.')

        return value

    @staticmethod
    def _raw_list(data: Mapping[str, Any], field: str) -> list[dict[str, Any]] | None:
        if field not in data or data[field] is None:
            return None

        value = data[field]
        if not isinstance(value, list):
            raise UnexpectedResponseError(f'Meta Insights "{field}" field must be a list.')

        for item in value:
            if not isinstance(item, dict):
                raise UnexpectedResponseError(f'Meta Insights "{field}" contains a malformed item.')

        return list(value)

    @staticmethod
    def _configuration_string(configuration: Mapping[str, Any] | None, field: str) -> str | None:
        if configuration is None or field not in configuration or configuration[field] is None:
            return None

        value = configuration[field]
        if not isinstance(value, str) or value == "":
            raise UnexpectedResponseError(f'Meta Ad Set configuration "{field}" must be a string.')

        return value

    @staticmethod
    def _promoted_object(configuration: Mapping[str, Any] | None) -> Any:
        if configuration is None:
            return None

        if "promoted_object" not in configuration or configuration["promoted_object"] is None:
            return None

        value = configuration["promoted_object"]
        if not isinstance(value, (dict, list)):
            raise UnexpectedResponseError('Meta Ad Set configuration "promoted_object" must be an object.')

        return value
