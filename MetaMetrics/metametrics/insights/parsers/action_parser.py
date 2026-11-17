"""Parsing of the Meta ``actions`` payload."""

from __future__ import annotations

import math
from collections.abc import Iterable

from metametrics.exceptions import InvalidInputError, UnexpectedResponseError
from metametrics.insights.metrics.purchase_actions import DEFAULT_ACTION_TYPES, PurchaseActionMapping
from metametrics.utils.numbers import is_numeric

__all__ = ["ActionParser"]


class ActionParser:
    """Extracts purchase counts from the Meta ``actions`` payload."""

    PURCHASE_ACTION_TYPES = DEFAULT_ACTION_TYPES

    def __init__(
        self,
        purchase_action_types: Iterable[str] | PurchaseActionMapping = PURCHASE_ACTION_TYPES,
    ) -> None:
        self.purchase_action_mapping = (
            purchase_action_types
            if isinstance(purchase_action_types, PurchaseActionMapping)
            else PurchaseActionMapping(purchase_action_types)
        )

    def purchases(self, actions: object) -> float | None:
        """Return the purchase count of an ``actions`` payload."""
        return self._extract(actions, "actions")

    def purchases_for_type(self, actions: object, action_type: str | None) -> float | None:
        """Return the purchase count of one specific action type."""
        if actions is None:
            return None

        if action_type is None:
            return None if self.contains_purchase(actions) else 0.0

        if not self.purchase_action_mapping.supports(action_type):
            raise InvalidInputError("Purchase action type is not included in the configured mapping.")

        return self._values(actions, "actions").get(action_type, 0.0)

    def common_purchase_action_type(self, actions: object, action_values: object) -> str | None:
        """Return the action type that both payloads share, if any."""
        action_types = self._values(actions, "actions").keys()
        value_types = self._values(action_values, "action_values").keys()

        return self.purchase_action_mapping.preferred_common_type(action_types, value_types)

    def contains_purchase(self, actions: object) -> bool:
        """Whether an ``actions`` payload contains any purchase action."""
        values = self._values(actions, "actions")

        return any(action_type in values for action_type in self.purchase_action_mapping.action_types)

    def _extract(self, actions: object, field: str) -> float | None:
        if actions is None:
            return None

        values = self._values(actions, field)

        for action_type in self.purchase_action_mapping.action_types:
            if action_type in values:
                return values[action_type]

        return 0.0

    @staticmethod
    def _values(actions: object, field: str) -> dict[str, float]:
        if not isinstance(actions, list):
            raise UnexpectedResponseError(f'Meta Insights "{field}" must be a list.')

        values: dict[str, float] = {}

        for action in actions:
            if (
                not isinstance(action, dict)
                or not isinstance(action.get("action_type"), str)
                or action["action_type"] == ""
                or "value" not in action
            ):
                raise UnexpectedResponseError(f'Meta Insights "{field}" contains a malformed action.')

            action_type = action["action_type"]
            if action_type in values:
                raise UnexpectedResponseError(f'Meta Insights "{field}" contains a duplicate action type.')

            values[action_type] = _number(action["value"], field)

        return values


def _number(value: object, field: str) -> float:
    if not is_numeric(value):
        raise UnexpectedResponseError(f'Meta Insights "{field}" action value must be numeric.')

    number = float(value.strip()) if isinstance(value, str) else float(value)

    if not math.isfinite(number):
        raise UnexpectedResponseError(f'Meta Insights "{field}" action value must be finite.')

    return number
