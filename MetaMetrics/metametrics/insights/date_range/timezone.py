"""The timezone of the Meta Ad Account."""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from metametrics.exceptions import InvalidInputError

__all__ = ["AccountTimezone"]


@dataclass(frozen=True, slots=True)
class AccountTimezone:
    """The IANA timezone an Ad Account reports its days in."""

    name: str

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.name)
        except (ZoneInfoNotFoundError, ValueError, KeyError) as error:
            raise InvalidInputError("Account timezone must be a valid timezone name.") from error

    @property
    def timezone(self) -> ZoneInfo:
        """Return the timezone object."""
        return ZoneInfo(self.name)
