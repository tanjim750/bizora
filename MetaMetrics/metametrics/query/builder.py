"""Encoding of Meta query parameters."""

from __future__ import annotations

import json
from collections.abc import Sequence

from metametrics.exceptions import InvalidInputError

from .filters import Filter

__all__ = ["QueryBuilder"]


class QueryBuilder:
    """Encodes typed filters into the Meta ``filtering`` query parameter."""

    def encode_filters(
        self,
        filters: Sequence[Filter],
        allowed_fields: Sequence[str],
    ) -> str | None:
        """Return the JSON-encoded filters, or ``None`` when there are none."""
        if not filters:
            return None

        serialized: list[dict[str, object]] = []

        for filter in filters:
            if not isinstance(filter, Filter):
                raise InvalidInputError("Insights filters must be Filter instances.")

            if filter.field not in allowed_fields:
                raise InvalidInputError(f'Unsupported Insights filter field "{filter.field}".')

            serialized.append(filter.to_dict())

        try:
            return json.dumps(serialized, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            raise InvalidInputError("Insights filters could not be encoded.") from error
