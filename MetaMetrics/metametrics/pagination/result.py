"""A single page of a paginated Meta API collection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["PaginationResult"]


@dataclass(frozen=True, slots=True)
class PaginationResult:
    """The items of one page plus the cursor for the next one."""

    items: tuple[dict[str, Any], ...]
    next_cursor: str | None = None

    @property
    def has_next_page(self) -> bool:
        """Whether another page is available."""
        return self.next_cursor is not None
