"""The raw Meta payload fields an Insights row preserves verbatim."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["InsightsRawData"]


@dataclass(frozen=True, slots=True)
class InsightsRawData:
    """The unmodified Meta values behind an Insights row."""

    spend: str | int | float | None = None
    actions: list[dict[str, Any]] | None = None
    cost_per_action_type: list[dict[str, Any]] | None = None
    optimization_goal: str | None = None
    promoted_object: Any = None
