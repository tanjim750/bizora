"""Query parameters for Ad Set listings."""

from __future__ import annotations

from dataclasses import dataclass

from metametrics.client import QueryValue
from metametrics.exceptions import InvalidInputError
from metametrics.query.fields import Fields
from metametrics.utils.json import php_json_dumps

__all__ = ["AdSetQuery"]

EFFECTIVE_STATUSES = (
    "ACTIVE",
    "ARCHIVED",
    "CAMPAIGN_PAUSED",
    "DELETED",
    "IN_PROCESS",
    "PAUSED",
    "WITH_ISSUES",
)


@dataclass(frozen=True, slots=True)
class AdSetQuery:
    """Filters and field selection for an Ad Set listing."""

    fields: Fields | None = None
    effective_statuses: tuple[str, ...] = ()
    completed: bool | None = None
    limit: int | None = None

    def __post_init__(self) -> None:
        for status in self.effective_statuses:
            if status not in EFFECTIVE_STATUSES:
                raise InvalidInputError(f'Unsupported Ad Set effective status "{status}".')

        if self.limit is not None and self.limit < 1:
            raise InvalidInputError("Ad Set query limit must be greater than zero.")

    def parameters(self) -> dict[str, QueryValue]:
        """Render the query as Meta request parameters."""
        parameters: dict[str, QueryValue] = {}

        if self.effective_statuses:
            unique = list(dict.fromkeys(self.effective_statuses))
            parameters["effective_status"] = php_json_dumps(unique)

        if self.completed is not None:
            parameters["is_completed"] = self.completed

        if self.limit is not None:
            parameters["limit"] = self.limit

        return parameters
