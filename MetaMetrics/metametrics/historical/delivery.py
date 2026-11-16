"""Delivery discovery and assessment for historical analysis."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from metametrics.exceptions import InvalidInputError
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.metrics.metric import Metric

__all__ = [
    "DeliveryAssessment",
    "DeliveryDiscovery",
    "DeliveryDiscoveryProtocol",
    "DeliveryEvidence",
    "DeliveryStatus",
]


class DeliveryStatus(StrEnum):
    """The outcome of a delivery assessment."""

    DELIVERED = "delivered"
    NOT_DELIVERED = "not_delivered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class DeliveryEvidence:
    """Non-empty, validated set of positive delivery indicators."""

    __slots__ = ("_indicators",)

    def __init__(self, indicators: Mapping[str, float | int]) -> None:
        if not indicators:
            raise InvalidInputError("Delivery evidence requires at least one positive indicator.")

        normalized: dict[str, float] = {}
        for name, value in indicators.items():
            if not isinstance(name, str) or name not in Metric._value2member_map_:
                raise InvalidInputError("Delivery evidence indicators must use supported metric names.")

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InvalidInputError("Delivery evidence indicator values must be positive finite numbers.")

            float_val = float(value)
            if not math.isfinite(float_val) or float_val <= 0:
                raise InvalidInputError("Delivery evidence indicator values must be positive finite numbers.")

            normalized[name] = float_val

        self._indicators = normalized

    def has(self, metric: Metric) -> bool:
        """Whether the evidence contains the given metric."""
        return metric.value in self._indicators

    def value(self, metric: Metric) -> float | None:
        """Return the indicator value for the metric, or None."""
        return self._indicators.get(metric.value)

    def indicators(self) -> dict[str, float]:
        """Return a copy of the indicators map."""
        return dict(self._indicators)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DeliveryEvidence):
            return self._indicators == other._indicators
        return False

    def __repr__(self) -> str:
        return f"DeliveryEvidence({self._indicators!r})"


@dataclass(frozen=True, slots=True)
class DeliveryAssessment:
    """The assessment of an entity's delivery status along with any evidence."""

    status: DeliveryStatus
    evidence: DeliveryEvidence | None = None

    def __post_init__(self) -> None:
        if (self.status == DeliveryStatus.DELIVERED) != (self.evidence is not None):
            raise RuntimeError(
                "Delivered assessments require evidence, and other assessments must not contain it."
            )

    @classmethod
    def delivered(cls, evidence: DeliveryEvidence) -> DeliveryAssessment:
        return cls(DeliveryStatus.DELIVERED, evidence)

    @classmethod
    def not_delivered(cls) -> DeliveryAssessment:
        return cls(DeliveryStatus.NOT_DELIVERED, None)

    @classmethod
    def insufficient_evidence(cls) -> DeliveryAssessment:
        return cls(DeliveryStatus.INSUFFICIENT_EVIDENCE, None)


class DeliveryDiscoveryProtocol(Protocol):
    """Protocol for discovering delivery from Insights."""

    def required_metrics(self) -> list[Metric]: ...

    def assess(self, insights: InsightsDTO) -> DeliveryAssessment: ...

    def has_delivery(self, insights: InsightsDTO) -> bool: ...


class DeliveryDiscovery:
    """Discovers delivery status and evidence from InsightsDTO instances."""

    _EVIDENCE_METRICS: tuple[Metric, ...] = (
        Metric.IMPRESSIONS,
        Metric.SPEND,
        Metric.REACH,
    )

    def required_metrics(self) -> list[Metric]:
        """The metrics required to assess delivery."""
        return list(self._EVIDENCE_METRICS)

    def assess(self, insights: InsightsDTO) -> DeliveryAssessment:
        """Assess delivery for a single insight row."""
        indicators: dict[str, float] = {}
        available = 0

        for metric in self._EVIDENCE_METRICS:
            val = insights.metric(metric)
            if val is None:
                continue

            available += 1
            if val > 0.0:
                indicators[metric.value] = val

        if indicators:
            return DeliveryAssessment.delivered(DeliveryEvidence(indicators))

        return (
            DeliveryAssessment.insufficient_evidence()
            if available == 0
            else DeliveryAssessment.not_delivered()
        )

    def has_delivery(self, insights: InsightsDTO) -> bool:
        """Whether the insight row demonstrates delivery."""
        return self.assess(insights).status == DeliveryStatus.DELIVERED
