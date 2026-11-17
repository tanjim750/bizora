"""Parsing of the Meta ``action_values`` payload."""

from __future__ import annotations

import math
from collections.abc import Iterable

from metametrics.exceptions import InvalidInputError, UnexpectedResponseError
from metametrics.insights.metrics.purchase_actions import PurchaseActionMapping
from metametrics.insights.parsers.action_parser import ActionParser
from metametrics.utils.numbers import is_numeric

__all__ = ["ActionValueParser"]


class ActionValueParser:
    """Extracts purchase value from the Meta ``action_values`` payload."""

    def __init__(
        self,
        purchase_action_types: Iterable[str] | PurchaseActionMapping | None = None,
    ) -> None:
        if purchase_action_types is None:
            purchase_action_types = ActionParser.PURCHASE_ACTION_TYPES

        self.purchase_action_mapping = (
            purchase_action_types
            if isinstance(purchase_action_types, PurchaseActionMapping)
            else PurchaseActionMapping(purchase_action_types)
        )

    def purchase_value(self, action_values: object) -> float | None:
        """Return the purchase value of an ``action_values`` payload."""
        return self.purchase_value_for_type(
            action_values, self._preferred_purchase_action_type(action_values)
        )

    def purchase_value_for_type(self, action_values: object, action_type: str | None) -> float | None:
        """Return the purchase value of one specific action type."""
        if action_values is None:
            return None

        if action_type is None:
            return None if self.contains_purchase(action_values) else 0.0

        if not self.purchase_action_mapping.supports(action_type):
            raise InvalidInputError("Purchase action type is not included in the configured mapping.")

        return self._values(action_values).get(action_type, 0.0)

    def contains_purchase(self, action_values: object) -> bool:
        """Whether an ``action_values`` payload contains any purchase action."""
        return self._preferred_purchase_action_type(action_values) is not None

    def _preferred_purchase_action_type(self, action_values: object) -> str | None:
        values = self._values(action_values)

        for action_type in self.purchase_action_mapping.action_types:
            if action_type in values:
                return action_type

        return None

    @staticmethod
    def _values(action_values: object) -> dict[str, float]:
        if action_values is None:
            return {}

        if not isinstance(action_values, list):
            raise UnexpectedResponseError('Meta Insights "action_values" must be a list.')

        values: dict[str, float] = {}

        for action in action_values:
            if (
                not isinstance(action, dict)
                or not isinstance(action.get("action_type"), str)
                or action["action_type"] == ""
                or "value" not in action
            ):
                raise UnexpectedResponseError('Meta Insights "action_values" contains a malformed action.')

            action_type = action["action_type"]
            if action_type in values:
                raise UnexpectedResponseError(
                    'Meta Insights "action_values" contains a duplicate action type.'
                )

            values[action_type] = _number(action["value"])

        return values


def _number(value: object) -> float:
    if not is_numeric(value):
        raise UnexpectedResponseError('Meta Insights "action_values" action value must be numeric.')

    number = float(value.strip()) if isinstance(value, str) else float(value)

    if not math.isfinite(number):
        raise UnexpectedResponseError('Meta Insights "action_values" action value must be finite.')

    return number
