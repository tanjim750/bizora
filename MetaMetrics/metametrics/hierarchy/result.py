"""The structured hierarchy tree result."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from metametrics.exceptions import InvalidInputError
from metametrics.hierarchy.node import HierarchyNode
from metametrics.historical.level import HistoricalLevel
from metametrics.insights.date_range.range import DateRange

__all__ = ["HierarchyResult"]


@dataclass(frozen=True, slots=True)
class HierarchyResult:
    """The complete hierarchy tree with attached and unattached entities."""

    requested_period: DateRange
    campaigns: tuple[HierarchyNode, ...] = field(default_factory=tuple)
    unattached_ad_sets: tuple[HierarchyNode, ...] = field(default_factory=tuple)
    unattached_ads: tuple[HierarchyNode, ...] = field(default_factory=tuple)
    currency: str | None = None

    def __init__(
        self,
        requested_period: DateRange,
        campaigns: Sequence[HierarchyNode] = (),
        unattached_ad_sets: Sequence[HierarchyNode] = (),
        unattached_ads: Sequence[HierarchyNode] = (),
        currency: str | None = None,
    ) -> None:
        object.__setattr__(self, "requested_period", requested_period)

        self._assert_level(campaigns, HistoricalLevel.CAMPAIGN)
        self._assert_level(unattached_ad_sets, HistoricalLevel.AD_SET)
        self._assert_level(unattached_ads, HistoricalLevel.AD)

        campaigns_tuple = tuple(campaigns)
        unattached_ad_sets_tuple = tuple(unattached_ad_sets)
        unattached_ads_tuple = tuple(unattached_ads)

        object.__setattr__(self, "campaigns", campaigns_tuple)
        object.__setattr__(self, "unattached_ad_sets", unattached_ad_sets_tuple)
        object.__setattr__(self, "unattached_ads", unattached_ads_tuple)

        all_nodes = (*campaigns_tuple, *unattached_ad_sets_tuple, *unattached_ads_tuple)
        resolved_currency = currency if currency is not None else (
            all_nodes[0].historical_result.currency if all_nodes else None
        )
        object.__setattr__(self, "currency", resolved_currency)

        for node in all_nodes:
            self._assert_currency(node)

    # Aliases
    @property
    def unattached_adsets(self) -> tuple[HierarchyNode, ...]:
        return self.unattached_ad_sets

    def to_dict(self) -> dict[str, Any]:
        """Render the hierarchy tree as a plain dictionary."""
        return {
            "currency": self.currency,
            "requested_period": self.requested_period.to_dict(),
            "campaigns": [self._node_dict(n) for n in self.campaigns],
            "unattached_adsets": [self._node_dict(n) for n in self.unattached_ad_sets],
            "unattached_ads": [self._node_dict(n) for n in self.unattached_ads],
        }

    # jsonSerialize parity
    def json_serialize(self) -> dict[str, Any]:
        return self.to_dict()

    def _node_dict(self, node: HierarchyNode) -> dict[str, Any]:
        res = dict(node.historical_result.to_dict(include_currency=False))
        res["children"] = [self._node_dict(child) for child in node.children]
        return res

    def _assert_currency(self, node: HierarchyNode) -> None:
        if node.historical_result.currency != self.currency:
            raise InvalidInputError("Hierarchy nodes must share the response currency.")

        for child in node.children:
            self._assert_currency(child)

    def _assert_level(self, nodes: Sequence[HierarchyNode], level: HistoricalLevel) -> None:
        for node in nodes:
            if not isinstance(node, HierarchyNode) or node.level != level:
                raise InvalidInputError(f"Hierarchy collection requires {level.value} nodes.")

            if node.historical_result.requested_period.to_dict() != self.requested_period.to_dict():
                raise InvalidInputError("Hierarchy nodes must use the hierarchy requested period.")
