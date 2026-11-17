"""Query parameters for Ad listings."""

from __future__ import annotations

from dataclasses import dataclass

from metametrics.client import QueryValue
from metametrics.exceptions import InvalidInputError
from metametrics.query.fields import Fields
from metametrics.utils.json import php_json_dumps

__all__ = ["AdQuery"]

EFFECTIVE_STATUSES = (
    "ACTIVE",
    "ADSET_PAUSED",
    "ARCHIVED",
    "CAMPAIGN_PAUSED",
    "DELETED",
    "DISAPPROVED",
    "IN_PROCESS",
    "PAUSED",
    "PENDING_BILLING_INFO",
    "PENDING_REVIEW",
    "PREAPPROVED",
    "WITH_ISSUES",
)


@dataclass(frozen=True, slots=True)
class AdQuery:
    """Filters and field selection for an Ad listing."""

    fields: Fields | None = None
    effective_statuses: tuple[str, ...] = ()
    limit: int | None = None

    def __post_init__(self) -> None:
        for status in self.effective_statuses:
            if status not in EFFECTIVE_STATUSES:
                raise InvalidInputError(f'Unsupported Ad effective status "{status}".')

        if self.limit is not None and self.limit < 1:
            raise InvalidInputError("Ad query limit must be greater than zero.")

    def parameters(self) -> dict[str, QueryValue]:
        """Render the query as Meta request parameters."""
        parameters: dict[str, QueryValue] = {}

        if self.effective_statuses:
            unique = list(dict.fromkeys(self.effective_statuses))
            parameters["effective_status"] = php_json_dumps(unique)

        if self.limit is not None:
            parameters["limit"] = self.limit

        return parameters
