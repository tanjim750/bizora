"""A node in the entity hierarchy tree."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from metametrics.exceptions import InvalidInputError
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.result import HistoricalResult

__all__ = ["HierarchyNode"]


@dataclass(frozen=True, slots=True)
class HierarchyNode:
    """A campaign, ad set, or ad node within an entity hierarchy."""

    historical_result: HistoricalResult
    children: tuple[HierarchyNode, ...] = field(default_factory=tuple)

    def __init__(
        self,
        historical_result: HistoricalResult,
        children: Sequence[HierarchyNode] = (),
    ) -> None:
        object.__setattr__(self, "historical_result", historical_result)
        validated_children: list[HierarchyNode] = []

        for child in children:
            if not isinstance(child, HierarchyNode):
                raise InvalidInputError("Hierarchy children must be HierarchyNode instances.")
            self._validate_child(child)
            validated_children.append(child)

        object.__setattr__(self, "children", tuple(validated_children))

    @property
    def entity_id(self) -> str:
        return self.historical_result.entity_id

    @property
    def level(self) -> HistoricalLevel:
        return self.historical_result.level

    def _validate_child(self, child: HierarchyNode) -> None:
        valid_relationship: bool
        if self.level == HistoricalLevel.CAMPAIGN:
            valid_relationship = (
                child.level == HistoricalLevel.AD_SET
                and child.historical_result.campaign_id == self.entity_id
            )
        elif self.level == HistoricalLevel.AD_SET:
            valid_relationship = (
                child.level == HistoricalLevel.AD
                and child.historical_result.ad_set_id == self.entity_id
            )
        else:
            valid_relationship = False

        same_period = (
            child.historical_result.insights.date_start == self.historical_result.insights.date_start
            and child.historical_result.insights.date_stop == self.historical_result.insights.date_stop
        )

        if not valid_relationship or not same_period:
            raise InvalidInputError(
                "Hierarchy child does not match its parent level, ID, and reporting period."
            )
