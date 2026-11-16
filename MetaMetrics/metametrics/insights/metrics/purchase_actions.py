"""The mapping of Meta action types onto purchase metrics."""

from __future__ import annotations

from collections.abc import Iterable

from metametrics.exceptions import InvalidInputError

__all__ = ["PurchaseActionMapping"]

DEFAULT_ACTION_TYPES: tuple[str, ...] = (
    "omni_purchase",
    "purchase",
    "offsite_conversion.fb_pixel_purchase",
    "app_custom_event.fb_mobile_purchase",
    "onsite_conversion.purchase",
    "offline_conversion.purchase",
)


class PurchaseActionMapping:
    """The Meta action types that count as a purchase, in priority order."""

    def __init__(self, action_types: Iterable[str] = DEFAULT_ACTION_TYPES) -> None:
        types = tuple(action_types)

        if not types:
            raise InvalidInputError("Purchase action mapping must be a non-empty list.")

        for action_type in types:
            if not isinstance(action_type, str) or action_type.strip() == "":
                raise InvalidInputError("Purchase action types must be non-empty strings.")

        if len(types) != len(set(types)):
            raise InvalidInputError("Purchase action mapping must not contain duplicates.")

        self._action_types = types

    @property
    def action_types(self) -> tuple[str, ...]:
        """The configured action types, in priority order."""
        return self._action_types

    def supports(self, action_type: str) -> bool:
        """Whether the action type counts as a purchase."""
        return action_type in self._action_types

    def preferred_common_type(self, *sets: Iterable[str]) -> str | None:
        """Return the first action type present in every set."""
        for action_type in self._action_types:
            for candidates in sets:
                if action_type not in candidates:
                    break
            else:
                return action_type

        return None
