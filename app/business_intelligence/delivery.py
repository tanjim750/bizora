"""BI specification §13 (Delivery Analysis) and the §2 Delivery Metrics family.

This module calculates the nine documented delivery analyses from canonical
shipments, shipment timestamps, orders, customers and delivery charges, and
records each measurement as a reproducible ``MetricSnapshot`` through the §3
snapshot contract in ``metrics.py``.

Public API (all keyword-only; every function is internal — callers authorize
business access before invoking anything here). Each entry serves one
documented §13 bullet; everything else in this module — the status
classification tables, the cohort/segment timestamp maps, the rule registry
itself and every intermediate helper — is private, because a caller measures
delivery by calling an operation, not by re-implementing its parts:

* ``calculate_delivery_outcome_rates`` — §13 Delivery Success Rate, Delivery
  Failure Rate and Return Rate Analysis; records ``delivery_shipments``,
  ``delivery_success_rate``, ``delivery_failure_rate`` and
  ``delivery_return_rate``.
* ``calculate_delivery_time`` — §13 Delivery Time Analysis; records
  ``delivery_time``.
* ``calculate_delivery_cost`` — §13 Delivery Cost Analysis; records
  ``delivery_cost`` and reports the charge's share of matched order value.
* ``compare_couriers`` — §13 Courier Performance Comparison (success, failure,
  return, timing and cost per ``Shipment.provider``).
* ``analyze_regional_delivery`` — §13 Regional Delivery Analysis.
* ``analyze_product_delivery`` — §13 Product Delivery Analysis, grouped through
  the order→product relationships already produced by ``relationships.py``.
* ``analyze_customer_delivery`` — §13 Customer Delivery Analysis.
* ``get_delivery_rule`` resolves the one closed calculation rule a measurement
  was recorded under, so §3 Calculation Traceability stays usable: a later fact
  or issue can find the exact observations by their ``calculation_rule``.

The ``COHORT_*``, ``SEGMENT_*``, ``DIMENSION_*`` and ``METRIC_*`` constants are
public only because a caller passes them in as arguments; the maps and sets
behind them are private.

What this module does not do. It adds no metric key and no dimension type: it
only uses the six already-registered DELIVERY definitions and the dimensions
the registry already declares. It never creates a BusinessFact, BusinessIssue
or anomaly, never labels a courier, region, product or customer as bad, risky
or fraudulent, and never ranks groups by outcome: a measurement is not an
interpretation. Threshold-based judgement ("unusually high" in the §13 Regional
bullet), period-over-period and baseline comparison belong to anomaly detection
(T-010) and fact/issue detection (T-011); reading observations back and
comparing periods is done with ``metrics.get_metric_snapshot`` /
``metrics.list_metric_snapshots`` / ``metrics.compare_metric_periods`` and is
not re-implemented here. No HTTP surface, view, serializer, URL,
authentication, authorization, schema change, migration, provider access or
identity decision is added. ``metrics.sync_metric_registry`` must have been run
for the business first; otherwise the snapshot contract rejects the write.

Status vocabulary. The canonical shipment lifecycle is documented in
``docs/implementations/features/business-data.md`` line 364: PENDING,
SUBMITTED, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED,
RETURNING, RETURNED, CANCELLED. That line says "states such as", and
``Shipment.status`` is a free-text ``CharField`` with no ``choices``, so the
list is documented but NOT guaranteed exhaustive. The classification sets below
are therefore named module constants, each tied to the §13 bullet that
justifies it, and a status outside all of them is classified ``UNCLASSIFIED``:
never ignored, never counted as a failure. Matching is exact — no case folding
or aliasing is invented — so a writer that stores a different spelling shows up
as an unclassified status instead of silently changing a rate. Every snapshot
carries the classification sets, the unclassified statuses and their counts in
``inputs``, so a reader can always tell whether a rate covered all shipments.

Cohort and denominator (this ticket's declared eligibility filter, per the
T-002 AC amendment: the ticket implementing a calculation declares the filter).
A shipment belongs to a period through exactly one timestamp, chosen by the
caller from the closed ``_COHORT_TIMESTAMP_FIELDS`` map and recorded in the
``calculation_rule``: ``COHORT_SUBMITTED`` uses ``submitted_at`` (the §13 Return
Rate bullet speaks of returns "after submission") and ``COHORT_CREATED`` uses
``created_at`` (always present, for providers that do not report a submission
time). A shipment is never moved between cohorts and ``created_at`` is never
silently substituted for a missing ``submitted_at``; with ``COHORT_SUBMITTED``,
shipments created inside the period that have no ``submitted_at`` are reported
as ``cohort_excluded_unsubmitted_business_wide``, a business-wide figure that is
never group-scoped. The rate denominator is every shipment in
the cohort and scope — including in-flight, cancelled and unclassified ones —
because the registered definitions read "fraction of the period's counted
shipments". In-flight shipments are therefore IN the denominator and in NO
numerator: an incomplete period shows a lower success rate that rises as
shipments resolve, which is why ``inputs`` always exposes the in-flight count.
Excluding cancellations (or in-flight shipments) from the denominator would be
an eligibility policy the two specifications do not state, so it is not
applied; the counts needed to apply such a policy later are preserved.

Zero denominators. With no shipment in scope the three rates are the
``UNAVAILABLE`` sentinel — never 0, never a division error — so nothing is
written for them. ``delivery_shipments`` is still recorded as a measured 0,
because "we counted and found none" is a measurement of the count itself; an
undefined ratio is not. The same UNAVAILABLE rule applies to an average over
zero timed shipments, to a cost share over zero matched order value and to
``delivery_cost`` when the currency scope holds no shipment at all — with no
shipment, nothing was observed about charges, which is not the same as a
measured zero spend.

Timing. ``delivery_time`` is measured between the documented lifecycle columns
``Shipment.submitted_at``, ``Shipment.picked_up_at`` and
``Shipment.delivered_at``; the segment is part of the ``calculation_rule``.
There is no "handover" column in the schema, so no duration is approximated
from ``created_at`` or ``updated_at``. Missing timestamps are first-class: a
shipment missing either endpoint, or whose endpoints are out of order,
contributes no duration at all, and every excluded count is recorded in
``inputs`` — including ``excluded_success_without_end_timestamp``, which per
segment means a shipment in the success class whose END timestamp for THAT
segment is absent (for the two delivery-ending segments, the documented
"delivered shipment with no delivery timestamp"). Because §13 names "successful
delivery", the two segments that end at ``delivered_at`` measure only the
success class and report any non-success shipment that still carried both
ordered timestamps; the submission-to-pickup leg admits every status, because
the handover precedes any delivery outcome. Durations are exact ``Decimal``
seconds.

One measure never replaces another. The snapshot identity does not include the
calculation rule, so a second timing segment, the other cohort or a second
currency for the same metric, period and dimension would land on one row and
silently update it. Recording such a run raises ``DeliveryCalculationError``
naming both rules; only a recalculation under the SAME variant updates in
place. Widening that identity belongs to ``metrics.py`` and is not done here.

Currency. ``delivery_cost`` is an AMOUNT, so one observation covers exactly one
currency and charges are never summed across currencies. The scope currency is
the ``CURRENCY`` dimension value when that dimension is used, otherwise the
caller's ``currency`` argument, otherwise the business's own recorded
``Business.currency``. Shipments in another currency are excluded and counted
per currency in ``inputs``. Order economics are measured only against orders
whose ``Order.currency`` equals the scope currency; the others are counted as
mismatched, and an order paying for several shipments contributes its total
once. The currency code itself is recorded in ``inputs["currency"]`` (and in
the dimension when the CURRENCY dimension is used) rather than inside the
``calculation_rule``: a rule variant is a closed lowercase token, while
currency codes are open canonical data.

Periods are half-open ``[period_start, period_end)`` and must be
timezone-aware. Calendar alignment is NOT enforced: the business reporting
timezone that would define an aligned day is an open team contract (Q4), so
``period_type`` stays a label and the bounds are the authority.

Determinism. The calculation-rule registry ``_DELIVERY_RULES`` is closed and
versioned, every result dataclass is frozen, all arithmetic is ``Decimal``
(never float), group discovery and every returned sequence are sorted by label
or id (not by outcome), and each public operation runs in one
``transaction.atomic()`` block so a failed analysis records nothing. Shipment
rows are read with an explicit ``business_id`` filter and the relationship rows
used for product grouping are matched on this service's own rule key, so no
caller-supplied value can widen the scope beyond the one business. Rows are
loaded and grouped in Python rather than aggregated in SQL to keep one code
path for filtering and grouping; pushing aggregation into the database for very
large shipment volumes is a later optimization, not a contract change.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from types import MappingProxyType
from typing import Any
import datetime
import re

from django.db import transaction
from django.utils import timezone

from app import models

from .metrics import (
    DIMENSION_TYPES,
    PERIOD_TYPES,
    UNAVAILABLE,
    SnapshotWriteResult,
    get_metric_definition,
    get_metric_snapshot,
    record_metric_snapshot,
)
from .relationships import RULES as _RELATIONSHIP_RULES


class DeliveryValidationError(ValueError):
    """A boundary input (business, period, cohort, dimension, scope) is invalid."""


class DeliveryCalculationError(ValueError):
    """An internal calculation invariant broke; no partial result is returned."""


class DeliveryRuleError(ValueError):
    """The hard-coded delivery rule or status registry is internally inconsistent."""


# --------------------------------------------------------------------------
# Schema-derived limits: never duplicate a column limit as a literal.
# --------------------------------------------------------------------------

def _field(model, name):
    for field in model._meta.concrete_fields:
        if field.name == name:
            return field
    raise DeliveryRuleError(f"{model.__name__} has no field named {name!r}.")


_VALUE_FIELD = _field(models.MetricSnapshot, "value")
# Working precision for exact division; derived from the stored column, so no
# precision literal is duplicated here.
_CALC_PRECISION = 2 * _VALUE_FIELD.max_digits + _VALUE_FIELD.decimal_places
_CALCULATION_RULE_MAX = _field(models.MetricSnapshot, "calculation_rule").max_length
_DIMENSION_VALUE_MAX = _field(models.MetricSnapshot, "dimension_value").max_length

_SECONDS_PER_DAY = Decimal(24 * 60 * 60)
_MICROSECONDS_PER_SECOND = Decimal(10) ** 6
_ZERO = Decimal(0)
_ONE = Decimal(1)

_VARIANT_RE = re.compile(r"^[a-z0-9_]+$")


# --------------------------------------------------------------------------
# Documented status vocabulary and the §13 classification sets
# --------------------------------------------------------------------------

# docs/implementations/features/business-data.md line 364 (§9 Courier,
# "Shipment Status Management"): tracks states *such as* these ten. The list is
# documented but not guaranteed exhaustive and the column has no choices.
_DOCUMENTED_SHIPMENT_STATUSES = frozenset({
    "PENDING", "SUBMITTED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY",
    "DELIVERED", "FAILED", "RETURNING", "RETURNED", "CANCELLED",
})

# §13 "Delivery Success Rate — Measures the percentage of shipments
# successfully delivered": DELIVERED is the only documented success state.
_SUCCESS_STATUSES = frozenset({"DELIVERED"})

# §13 "Delivery Failure Rate — Measures failed delivery attempts and
# unsuccessful shipments": FAILED is the documented failure state. RETURNING,
# RETURNED and CANCELLED are deliberately NOT here — they have their own
# documented meaning and the return bullet owns the first two.
_FAILURE_STATUSES = frozenset({"FAILED"})

# §13 "Return Rate Analysis — Evaluates how frequently shipments are returned
# after submission or delivery attempts": a return in progress and a completed
# return both count as returned; their separate counts stay in ``inputs``.
_RETURN_STATUSES = frozenset({"RETURNING", "RETURNED"})

# Still moving through the lifecycle: neither a success nor a failure yet. A
# shipment in flight at period end is never counted as a failed delivery.
_IN_FLIGHT_STATUSES = frozenset({
    "PENDING", "SUBMITTED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY",
})

# Terminal without a delivery attempt outcome; kept separate so a cancellation
# is never reported as a delivery failure.
_CANCELLED_STATUSES = frozenset({"CANCELLED"})

_CLASS_SUCCESS = "SUCCESS"
_CLASS_FAILURE = "FAILURE"
_CLASS_RETURN = "RETURN"
_CLASS_IN_FLIGHT = "IN_FLIGHT"
_CLASS_CANCELLED = "CANCELLED"
_CLASS_UNCLASSIFIED = "UNCLASSIFIED"

_STATUS_CLASSES = (
    (_CLASS_SUCCESS, _SUCCESS_STATUSES),
    (_CLASS_FAILURE, _FAILURE_STATUSES),
    (_CLASS_RETURN, _RETURN_STATUSES),
    (_CLASS_IN_FLIGHT, _IN_FLIGHT_STATUSES),
    (_CLASS_CANCELLED, _CANCELLED_STATUSES),
)

# Bumped whenever a classification set changes, so an older observation's
# calculation_rule still identifies the sets that produced it.
_STATUS_SET_VERSION = "s1"


def _validate_status_sets():
    """A status may belong to exactly one class, and the sets must stay documented."""
    seen = set()
    for name, statuses in _STATUS_CLASSES:
        if not statuses:
            raise DeliveryRuleError(f"Classification set {name} is empty.")
        overlap = seen & set(statuses)
        if overlap:
            raise DeliveryRuleError(
                f"Classification set {name} overlaps an earlier set on {sorted(overlap)}; "
                "the classes must partition the denominator."
            )
        seen |= set(statuses)
    undocumented = seen - _DOCUMENTED_SHIPMENT_STATUSES
    if undocumented:
        raise DeliveryRuleError(
            f"Classification sets contain undocumented statuses {sorted(undocumented)}."
        )
    unclassified = _DOCUMENTED_SHIPMENT_STATUSES - seen
    if unclassified:
        raise DeliveryRuleError(
            f"Documented statuses {sorted(unclassified)} are not classified; every "
            "documented lifecycle state must be explicitly assigned."
        )


_validate_status_sets()


def _classify_status(*, status):
    """Return the documented outcome class for one canonical shipment status.

    Matching is exact. A status outside every classification set returns
    ``UNCLASSIFIED`` — it is never ignored and never counted as a failure.
    """
    if not isinstance(status, str):
        raise DeliveryValidationError("status must be a string.")
    for name, statuses in _STATUS_CLASSES:
        if status in statuses:
            return name
    return _CLASS_UNCLASSIFIED


def _statuses_text(statuses):
    """Spell a classification set out inside a rule description, never a symbol."""
    return ", ".join(sorted(statuses))


def _status_set_inputs():
    return {
        name.lower(): sorted(statuses) for name, statuses in _STATUS_CLASSES
    }


# --------------------------------------------------------------------------
# Cohorts, timing segments and supported dimensions
# --------------------------------------------------------------------------

COHORT_SUBMITTED = "COHORT_SUBMITTED"
COHORT_CREATED = "COHORT_CREATED"

# The one timestamp that places a shipment in a period, per cohort.
_COHORT_TIMESTAMP_FIELDS = {
    COHORT_SUBMITTED: "submitted_at",
    COHORT_CREATED: "created_at",
}

SEGMENT_SUBMISSION_TO_DELIVERY = "SUBMISSION_TO_DELIVERY"
SEGMENT_SUBMISSION_TO_PICKUP = "SUBMISSION_TO_PICKUP"
SEGMENT_PICKUP_TO_DELIVERY = "PICKUP_TO_DELIVERY"

# §13 Delivery Time Analysis: "the time between shipment submission, pickup,
# and successful delivery" — the three segments the documented columns support.
_SEGMENT_TIMESTAMP_FIELDS = {
    SEGMENT_SUBMISSION_TO_DELIVERY: ("submitted_at", "delivered_at"),
    SEGMENT_SUBMISSION_TO_PICKUP: ("submitted_at", "picked_up_at"),
    SEGMENT_PICKUP_TO_DELIVERY: ("picked_up_at", "delivered_at"),
}

DIMENSION_COURIER = "COURIER"
DIMENSION_REGION = "REGION"
DIMENSION_PRODUCT = "PRODUCT"
DIMENSION_CURRENCY = "CURRENCY"

# The §2 dimensions a shipment scope can actually be resolved from canonical
# data: provider (COURIER), normalized region label (REGION), the order's
# products through the relationship service (PRODUCT) and the shipment currency
# (CURRENCY). CUSTOMER_SEGMENT is not here: no canonical segment field exists on
# Customer, and deterministic segmentation is owned by another ticket.
_DELIVERY_DIMENSIONS = frozenset({
    DIMENSION_COURIER, DIMENSION_REGION, DIMENSION_PRODUCT, DIMENSION_CURRENCY,
})

# Mirrors relationships.py; relationship ownership is matched on the service's
# own rule key plus this source rather than on the writable metadata marker.
_DETERMINISTIC_RELATIONSHIP_SOURCE = "DETERMINISTIC"
_ORDER_PRODUCT_RULE = _RELATIONSHIP_RULES["order_product"]

_REGION_UNRESOLVED_MISSING_METADATA = "MISSING_METADATA"
_REGION_UNRESOLVED_MISSING_KEY = "MISSING_KEY"
_REGION_UNRESOLVED_NOT_A_STRING = "NOT_A_STRING"
_REGION_UNRESOLVED_BLANK = "BLANK"
_REGION_UNRESOLVED_TOO_LONG = "TOO_LONG"
_REGION_UNRESOLVED_REASONS = (
    _REGION_UNRESOLVED_MISSING_METADATA,
    _REGION_UNRESOLVED_MISSING_KEY,
    _REGION_UNRESOLVED_NOT_A_STRING,
    _REGION_UNRESOLVED_BLANK,
    _REGION_UNRESOLVED_TOO_LONG,
)


# --------------------------------------------------------------------------
# Closed, versioned calculation-rule registry
# --------------------------------------------------------------------------

METRIC_SHIPMENTS = "bi.metric.delivery_shipments.v1"
METRIC_SUCCESS_RATE = "bi.metric.delivery_success_rate.v1"
METRIC_FAILURE_RATE = "bi.metric.delivery_failure_rate.v1"
METRIC_RETURN_RATE = "bi.metric.delivery_return_rate.v1"
METRIC_TIME = "bi.metric.delivery_time.v1"
METRIC_COST = "bi.metric.delivery_cost.v1"

_METRIC_KEYS = (
    METRIC_SHIPMENTS, METRIC_SUCCESS_RATE, METRIC_FAILURE_RATE,
    METRIC_RETURN_RATE, METRIC_TIME, METRIC_COST,
)

_DENOMINATOR_NOTE = (
    "Denominator: every shipment of the cohort inside the scope, including "
    "in-flight, cancelled and unclassified ones, so the outcome classes "
    "partition it."
)

_RULE_DESCRIPTIONS = {
    METRIC_SHIPMENTS: (
        "§13: count of shipments of the cohort inside the scope. No status is "
        "excluded; a count of zero is a measured zero."
    ),
    METRIC_SUCCESS_RATE: (
        "§13 Delivery Success Rate: shipments whose current canonical status is "
        f"one of {_statuses_text(_SUCCESS_STATUSES)}, divided by the cohort. "
        f"{_DENOMINATOR_NOTE}"
    ),
    METRIC_FAILURE_RATE: (
        "§13 Delivery Failure Rate: shipments whose current canonical status is "
        f"one of {_statuses_text(_FAILURE_STATUSES)}, divided by the cohort. "
        f"{_DENOMINATOR_NOTE} In-flight, cancelled and unclassified shipments "
        "are not failures."
    ),
    METRIC_RETURN_RATE: (
        "§13 Return Rate Analysis: shipments whose current canonical status is "
        f"one of {_statuses_text(_RETURN_STATUSES)}, divided by the cohort. "
        f"{_DENOMINATOR_NOTE}"
    ),
    METRIC_TIME: (
        "§13 Delivery Time Analysis: mean exact Decimal seconds between the two "
        "documented lifecycle timestamps of the segment, over the shipments of "
        "the cohort that carry both timestamps in order. Shipments missing an "
        "endpoint contribute nothing and are counted in inputs."
    ),
    METRIC_COST: (
        "§13 Delivery Cost Analysis: sum of Shipment.delivery_charge over the "
        "shipments of the cohort in one currency scope. Shipments in another "
        "currency are excluded and counted in inputs."
    ),
}

_EXPECTED_VALUE_TYPES = {
    METRIC_SHIPMENTS: "COUNT",
    METRIC_SUCCESS_RATE: "RATIO",
    METRIC_FAILURE_RATE: "RATIO",
    METRIC_RETURN_RATE: "RATIO",
    METRIC_TIME: "DURATION",
    METRIC_COST: "AMOUNT",
}

_RATE_METRIC_KEYS = (METRIC_SUCCESS_RATE, METRIC_FAILURE_RATE, METRIC_RETURN_RATE)


@dataclass(frozen=True)
class DeliveryRule:
    """One closed calculation rule: what is measured, over which cohort."""

    metric_key: str
    calculation_rule: str
    cohort: str
    segment: str | None
    status_set_version: str | None
    value_type: str
    unit: str
    description: str


def _make_rule(metric_key, cohort, segment, variant_parts, status_set_version):
    definition = get_metric_definition(metric_key=metric_key)
    if definition.category != "DELIVERY":
        raise DeliveryRuleError(
            f"{metric_key} is not a DELIVERY metric; this module only calculates "
            "the documented Delivery Metrics family."
        )
    expected = _EXPECTED_VALUE_TYPES[metric_key]
    if definition.value_type != expected:
        raise DeliveryRuleError(
            f"{metric_key} is registered as {definition.value_type}, but this "
            f"calculation produces {expected}."
        )
    variant = "_".join(variant_parts)
    if not _VARIANT_RE.match(variant):
        raise DeliveryRuleError(f"Calculation-rule variant {variant!r} is not lowercase.")
    calculation_rule = f"{metric_key}.{variant}"
    if len(calculation_rule) > _CALCULATION_RULE_MAX:
        raise DeliveryRuleError(
            f"calculation_rule {calculation_rule!r} exceeds the stored column length."
        )
    return DeliveryRule(
        metric_key=metric_key,
        calculation_rule=calculation_rule,
        cohort=cohort,
        segment=segment,
        status_set_version=status_set_version,
        value_type=definition.value_type,
        unit=definition.unit,
        description=_RULE_DESCRIPTIONS[metric_key],
    )


def _build_delivery_rules():
    """A closed registry: a new delivery calculation needs a reviewable entry."""
    rules = {}
    for cohort in sorted(_COHORT_TIMESTAMP_FIELDS):
        cohort_part = cohort.lower()
        # A plain count does not depend on the classification sets.
        for metric_key in (METRIC_SHIPMENTS, METRIC_COST):
            rules[(metric_key, cohort, None)] = _make_rule(
                metric_key, cohort, None, (cohort_part,), None
            )
        # The rates do, so the status-set version is part of their variant.
        for metric_key in _RATE_METRIC_KEYS:
            rules[(metric_key, cohort, None)] = _make_rule(
                metric_key, cohort, None, (cohort_part, _STATUS_SET_VERSION),
                _STATUS_SET_VERSION,
            )
        for segment in sorted(_SEGMENT_TIMESTAMP_FIELDS):
            rules[(METRIC_TIME, cohort, segment)] = _make_rule(
                METRIC_TIME, cohort, segment, (segment.lower(), cohort_part), None
            )
    return rules


_DELIVERY_RULES = _build_delivery_rules()


def get_delivery_rule(*, metric_key, cohort, segment=None):
    """Return the one closed calculation rule for a metric, cohort and segment."""
    _require_cohort(cohort)
    if metric_key not in _METRIC_KEYS:
        raise DeliveryValidationError(
            f"metric_key must be one of {sorted(_METRIC_KEYS)}."
        )
    if segment is not None:
        _require_segment(segment)
    rule = _DELIVERY_RULES.get((metric_key, cohort, segment))
    if rule is None:
        raise DeliveryValidationError(
            f"No delivery rule exists for {metric_key} with cohort {cohort} and "
            f"segment {segment}."
        )
    return rule


# --------------------------------------------------------------------------
# Result structures
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DeliveryStatusCounts:
    """How the scope's shipments partition across the documented outcome classes."""

    shipments: int
    delivered: int
    failed: int
    returning: int
    returned: int
    in_flight: int
    cancelled: int
    unclassified: int
    unclassified_statuses: tuple

    @property
    def returns(self):
        """Return-rate numerator: returns in progress plus completed returns."""
        return self.returning + self.returned


@dataclass(frozen=True)
class DeliveryScope:
    """The business, period and dimension one measurement was taken over."""

    business_id: int
    period_type: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    cohort: str
    dimension_type: str | None
    dimension_value: str | None


@dataclass(frozen=True)
class DeliveryOutcomeResult:
    """§13 success, failure and return rates for one scope.

    Each rate is a ``Decimal`` fraction or the ``UNAVAILABLE`` sentinel when the
    scope holds no shipment. ``counts.shipments`` is a measured count even when
    zero. ``cohort_excluded_unsubmitted_business_wide`` is exactly what its name
    says: the BUSINESS-WIDE number of shipments created inside the period with
    no ``submitted_at``. It is 0 for the ``COHORT_CREATED`` cohort, where it does
    not apply, and it is deliberately not group-scoped — a shipment with no
    submission time joins no courier, region or product cohort group at all — so
    the same business-wide figure appears on every grouped result and the field
    name prevents reading it as a per-group count.
    """

    scope: DeliveryScope
    counts: DeliveryStatusCounts
    success_rate: Any
    failure_rate: Any
    return_rate: Any
    cohort_excluded_unsubmitted_business_wide: int
    inputs: Any
    shipments_snapshot: SnapshotWriteResult | None
    success_rate_snapshot: SnapshotWriteResult | None
    failure_rate_snapshot: SnapshotWriteResult | None
    return_rate_snapshot: SnapshotWriteResult | None


@dataclass(frozen=True)
class DeliveryTimingResult:
    """§13 Delivery Time Analysis for one segment and scope, in exact seconds.

    ``requires_success_status`` is True for the two segments that end at
    ``delivered_at``: §13 names "successful delivery", so only the success class
    is measured there and ``excluded_not_success_with_both_timestamps`` holds the
    shipments that carried both ordered timestamps but were not a successful
    delivery. It is always 0 for ``SEGMENT_SUBMISSION_TO_PICKUP``, where every
    status is eligible because the handover precedes any delivery outcome.

    The exclusive partition is ``measured`` + ``excluded_missing_start`` +
    ``excluded_missing_end`` + ``excluded_out_of_order`` +
    ``excluded_not_success_with_both_timestamps`` = ``shipments``.
    ``excluded_success_without_end_timestamp`` is a named OVERLAPPING subset of
    the missing-timestamp exclusions, not a sixth bucket: it counts shipments in
    the success class whose end timestamp for THIS segment is absent. For the
    two delivery-ending segments that is the documented "delivered shipment with
    no delivery timestamp" case; for ``SEGMENT_SUBMISSION_TO_PICKUP`` it is a
    delivered shipment with no pickup timestamp. ``start_field`` and
    ``end_field`` always name the two timestamps the number was taken from.
    """

    scope: DeliveryScope
    segment: str
    start_field: str
    end_field: str
    requires_success_status: bool
    shipments: int
    measured: int
    excluded_missing_start: int
    excluded_missing_end: int
    excluded_success_without_end_timestamp: int
    excluded_out_of_order: int
    excluded_not_success_with_both_timestamps: int
    total_seconds: Decimal
    average_seconds: Any
    inputs: Any
    snapshot: SnapshotWriteResult | None


@dataclass(frozen=True)
class DeliveryCostResult:
    """§13 Delivery Cost Analysis for one currency scope.

    ``charge_share_of_order_value`` expresses the documented "impact on order
    economics" as a fraction of the matched order value; it is returned and kept
    in the snapshot's ``inputs`` as supporting evidence, because the registry has
    no ratio metric for it.

    Numerator and denominator are the SAME shipment set: the share divides
    ``matched_charge_total`` — the charges of the ``shipments_in_share``
    shipments whose order is in the matched set — by ``order_value_total``, the
    value of exactly those ``orders_matched`` orders. Charges whose order was
    excluded for a currency mismatch, or is not available inside this business,
    are reported in ``charge_excluded_from_share`` /
    ``shipments_excluded_from_share`` / ``orders_unavailable_in_business``
    instead of inflating the ratio. ``total_charge`` remains the full
    in-currency charge total and is what the ``delivery_cost`` metric records,
    so spend is never under-reported.
    """

    scope: DeliveryScope
    currency: str
    shipments: int
    shipments_in_currency: int
    shipments_excluded_other_currency: int
    excluded_currencies: tuple
    total_charge: Decimal
    orders_matched: int
    orders_excluded_currency_mismatch: int
    orders_unavailable_in_business: int
    order_value_total: Decimal
    shipments_in_share: int
    shipments_excluded_from_share: int
    matched_charge_total: Decimal
    charge_excluded_from_share: Decimal
    charge_share_of_order_value: Any
    inputs: Any
    snapshot: SnapshotWriteResult | None


@dataclass(frozen=True)
class CourierDeliveryPerformance:
    """One courier provider's success, failure, return, timing and cost."""

    courier: str
    outcomes: DeliveryOutcomeResult
    timing: DeliveryTimingResult
    cost: DeliveryCostResult


@dataclass(frozen=True)
class CourierComparison:
    """§13 Courier Performance Comparison, ordered by provider label."""

    couriers: tuple
    unresolved_courier_shipments: int
    couriers_below_minimum: int
    minimum_shipments: int | None


@dataclass(frozen=True)
class RegionDeliveryPerformance:
    """One region's outcome rates and delivery timing."""

    region: str
    outcomes: DeliveryOutcomeResult
    timing: DeliveryTimingResult


@dataclass(frozen=True)
class RegionalDeliveryAnalysis:
    """§13 Regional Delivery Analysis, ordered by region label.

    No region is flagged: "unusually high" is a threshold, owned by configurable
    anomaly rules (T-010) and issue detection (T-011), not by this measurement.
    """

    region_metadata_key: str
    regions: tuple
    unresolved_shipments: int
    unresolved_reasons: tuple
    regions_below_minimum: int
    minimum_shipments: int | None


@dataclass(frozen=True)
class ProductDeliveryPerformance:
    """One canonical product's delivery outcomes, through its orders' shipments."""

    product_id: int
    outcomes: DeliveryOutcomeResult


@dataclass(frozen=True)
class ProductDeliveryAnalysis:
    """§13 Product Delivery Analysis, ordered by canonical product id.

    A shipment counts once for every product its order contains, so per-product
    scopes overlap and do not sum to the business-wide figure.
    """

    products: tuple
    shipments_without_product_relationship: int
    relationship_rule_key: str
    products_below_minimum: int
    minimum_shipments: int | None


@dataclass(frozen=True)
class CustomerDeliveryOutcome:
    """One resolved customer's observed shipment outcomes. No label, no verdict."""

    customer_id: int
    counts: DeliveryStatusCounts
    failed_or_returned: int


@dataclass(frozen=True)
class CustomerDeliveryAnalysis:
    """§13 Customer Delivery Analysis, ordered by canonical customer id.

    This counts observable shipment outcomes only. Calling a customer risky or
    fraudulent is an interpretation owned by issue detection (T-011); nothing
    here is recorded as a metric snapshot because the registry declares no
    CUSTOMER dimension.
    """

    scope: DeliveryScope
    customers: tuple
    shipments: int
    shipments_without_customer: int
    customers_below_minimum: int
    minimum_failed_or_returned: int | None


# --------------------------------------------------------------------------
# Boundary validation
# --------------------------------------------------------------------------

def _require_positive_id(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DeliveryValidationError(f"{label} must be a positive integer.")
    return value


def _require_optional_minimum(value, label):
    if value is None:
        return None
    return _require_positive_id(value, label)


def _require_aware(value, label):
    if isinstance(value, datetime.datetime) and timezone.is_aware(value):
        return value
    raise DeliveryValidationError(f"{label} must be a timezone-aware datetime.")


def _require_period(period_type, period_start, period_end):
    """Half-open [period_start, period_end); no calendar alignment is enforced."""
    if not isinstance(period_type, str) or period_type not in PERIOD_TYPES:
        raise DeliveryValidationError(f"period_type must be one of {sorted(PERIOD_TYPES)}.")
    start = _require_aware(period_start, "period_start")
    end = _require_aware(period_end, "period_end")
    if end <= start:
        raise DeliveryValidationError(
            "period_end must be strictly after period_start; periods are half-open "
            "[period_start, period_end)."
        )
    return period_type, start, end


def _require_cohort(cohort):
    if not isinstance(cohort, str) or cohort not in _COHORT_TIMESTAMP_FIELDS:
        raise DeliveryValidationError(
            f"cohort must be one of {sorted(_COHORT_TIMESTAMP_FIELDS)}."
        )
    return cohort


def _require_segment(segment):
    if not isinstance(segment, str) or segment not in _SEGMENT_TIMESTAMP_FIELDS:
        raise DeliveryValidationError(
            f"segment must be one of {sorted(_SEGMENT_TIMESTAMP_FIELDS)}."
        )
    return segment


def _require_label(value, label):
    if not isinstance(value, str):
        raise DeliveryValidationError(f"{label} must be a string.")
    stripped = value.strip()
    if not stripped:
        raise DeliveryValidationError(f"{label} must not be empty.")
    if len(stripped) > _DIMENSION_VALUE_MAX:
        raise DeliveryValidationError(
            f"{label} exceeds {_DIMENSION_VALUE_MAX} characters."
        )
    return stripped


def _require_dimension(dimension_type, dimension_value, region_metadata_key):
    """Validate a §13 scope: both parts present or both absent."""
    if dimension_type is None and dimension_value is None:
        if region_metadata_key is not None:
            raise DeliveryValidationError(
                "region_metadata_key is only meaningful with the REGION dimension."
            )
        return None, None, None
    if dimension_type is None or dimension_value is None:
        raise DeliveryValidationError(
            "dimension_type and dimension_value must both be provided or both omitted."
        )
    if not isinstance(dimension_type, str) or dimension_type not in DIMENSION_TYPES:
        raise DeliveryValidationError(
            f"dimension_type must be one of {sorted(DIMENSION_TYPES)}."
        )
    if dimension_type not in _DELIVERY_DIMENSIONS:
        raise DeliveryValidationError(
            f"Delivery analysis supports the {sorted(_DELIVERY_DIMENSIONS)} dimensions; "
            f"{dimension_type} is not resolvable from canonical shipment data here."
        )
    value = _require_label(dimension_value, "dimension_value")
    if dimension_type == DIMENSION_PRODUCT:
        if not (value.isascii() and value.isdigit()) or value.startswith("0"):
            raise DeliveryValidationError(
                "dimension_value for PRODUCT must be a canonical positive product id "
                "written without leading zeros."
            )
    if dimension_type == DIMENSION_REGION:
        if region_metadata_key is None:
            raise DeliveryValidationError(
                "region_metadata_key is required with the REGION dimension: the "
                "schema has no canonical region column, so the region label is read "
                "from the shipment's normalized source_metadata."
            )
        region_metadata_key = _require_region_metadata_key(region_metadata_key)
    elif region_metadata_key is not None:
        raise DeliveryValidationError(
            "region_metadata_key is only meaningful with the REGION dimension."
        )
    return dimension_type, value, region_metadata_key


def _require_region_metadata_key(region_metadata_key):
    if not isinstance(region_metadata_key, str) or not region_metadata_key.strip():
        raise DeliveryValidationError("region_metadata_key must be a non-empty string.")
    if region_metadata_key != region_metadata_key.strip():
        raise DeliveryValidationError(
            "region_metadata_key must not carry surrounding whitespace."
        )
    return region_metadata_key


def _require_flag(value, label):
    if not isinstance(value, bool):
        raise DeliveryValidationError(f"{label} must be a boolean.")
    return value


def _require_business(business_id):
    """Business-scoped reads start here; the caller has already authorized access."""
    business = models.Business.objects.filter(pk=business_id).only("id", "currency").first()
    if business is None:
        raise DeliveryValidationError("Business does not exist.")
    return business


# --------------------------------------------------------------------------
# Exact Decimal arithmetic
# --------------------------------------------------------------------------

def _divide(numerator, denominator):
    """Exact Decimal division; a zero denominator is UNAVAILABLE, never 0."""
    if not isinstance(numerator, Decimal) or not isinstance(denominator, Decimal):
        raise DeliveryCalculationError("Delivery arithmetic uses Decimal only.")
    if denominator <= _ZERO:
        return UNAVAILABLE
    with localcontext() as context:
        context.prec = _CALC_PRECISION
        return numerator / denominator


def _seconds(delta):
    """Exact Decimal seconds for a timedelta; no float is ever constructed."""
    with localcontext() as context:
        context.prec = _CALC_PRECISION
        return (
            Decimal(delta.days) * _SECONDS_PER_DAY
            + Decimal(delta.seconds)
            + Decimal(delta.microseconds) / _MICROSECONDS_PER_SECOND
        )


def _sum(values):
    """Total Decimals at the working precision, so no addition silently rounds."""
    with localcontext() as context:
        context.prec = _CALC_PRECISION
        total = _ZERO
        for value in values:
            if not isinstance(value, Decimal):
                raise DeliveryCalculationError("Delivery arithmetic uses Decimal only.")
            total += value
        return total


def _require_fraction(value, label):
    if value is UNAVAILABLE:
        return value
    if not isinstance(value, Decimal) or not (_ZERO <= value <= _ONE):
        raise DeliveryCalculationError(
            f"{label} must be a fraction between 0 and 1; the classification sets "
            "no longer partition the denominator."
        )
    return value


# --------------------------------------------------------------------------
# Canonical shipment loading, scoping and grouping
# --------------------------------------------------------------------------

# Model field names (not FK attnames): ``only()`` resolves these through the
# model meta, and the FK columns still load as ``order_id``/``customer_id``.
_SHIPMENT_FIELDS = (
    "id", "order", "customer", "provider", "status", "delivery_charge",
    "currency", "submitted_at", "picked_up_at", "delivered_at", "returned_at",
    "source_metadata", "created_at",
)


def _load_cohort(business_id, cohort, period_start, period_end):
    """Return the business's shipments whose cohort timestamp is in the period."""
    cohort_field = _COHORT_TIMESTAMP_FIELDS[cohort]
    rows = list(
        models.Shipment.objects.filter(
            business_id=business_id,
            **{f"{cohort_field}__gte": period_start, f"{cohort_field}__lt": period_end},
        ).only(*_SHIPMENT_FIELDS).order_by("pk")
    )
    excluded_unsubmitted = 0
    if cohort == COHORT_SUBMITTED:
        # Reported, never reassigned: a shipment with no submission time is not
        # given one from created_at.
        excluded_unsubmitted = models.Shipment.objects.filter(
            business_id=business_id,
            submitted_at__isnull=True,
            created_at__gte=period_start,
            created_at__lt=period_end,
        ).count()
    return rows, excluded_unsubmitted


def _order_product_map(business_id, order_ids):
    """Reuse the §1 order→product relationships instead of re-deriving links."""
    mapping = {}
    if not order_ids:
        return mapping
    rows = models.BusinessRelationship.objects.filter(
        business_id=business_id,
        source_entity_type=_ORDER_PRODUCT_RULE.source_type,
        relationship_type=_ORDER_PRODUCT_RULE.relationship_type,
        target_entity_type=_ORDER_PRODUCT_RULE.target_type,
        rule_key=_ORDER_PRODUCT_RULE.key,
        relationship_source=_DETERMINISTIC_RELATIONSHIP_SOURCE,
        valid_to__isnull=True,
        source_entity_id__in=sorted(order_ids),
    ).values_list("source_entity_id", "target_entity_id")
    for order_id, product_id in rows:
        mapping.setdefault(order_id, set()).add(product_id)
    return {order_id: tuple(sorted(products)) for order_id, products in mapping.items()}


def _region_label(row, region_metadata_key):
    """Resolve a region label from normalized metadata, or say why it is unresolved."""
    metadata = row.source_metadata
    if not isinstance(metadata, dict):
        return None, _REGION_UNRESOLVED_MISSING_METADATA
    if region_metadata_key not in metadata:
        return None, _REGION_UNRESOLVED_MISSING_KEY
    value = metadata[region_metadata_key]
    if not isinstance(value, str):
        return None, _REGION_UNRESOLVED_NOT_A_STRING
    label = value.strip()
    if not label:
        return None, _REGION_UNRESOLVED_BLANK
    if len(label) > _DIMENSION_VALUE_MAX:
        return None, _REGION_UNRESOLVED_TOO_LONG
    return label, None


def _label_of(value):
    """A canonical label as stored, whitespace-stripped; never case-folded."""
    return value.strip() if isinstance(value, str) else ""


def _scoped_rows(rows, business_id, dimension_type, dimension_value, region_metadata_key):
    """Restrict loaded shipments to one dimension scope using canonical fields."""
    if dimension_type is None:
        return rows
    if dimension_type == DIMENSION_COURIER:
        return [row for row in rows if _label_of(row.provider) == dimension_value]
    if dimension_type == DIMENSION_CURRENCY:
        return [row for row in rows if _label_of(row.currency) == dimension_value]
    if dimension_type == DIMENSION_REGION:
        scoped = []
        for row in rows:
            label, _ = _region_label(row, region_metadata_key)
            if label == dimension_value:
                scoped.append(row)
        return scoped
    if dimension_type == DIMENSION_PRODUCT:
        product_id = int(dimension_value)
        mapping = _order_product_map(business_id, {row.order_id for row in rows})
        return [row for row in rows if product_id in mapping.get(row.order_id, ())]
    raise DeliveryValidationError(f"Unsupported delivery dimension {dimension_type}.")


def _count_statuses(rows):
    """Partition the scope's shipments across the documented classification sets."""
    totals = {name: 0 for name, _ in _STATUS_CLASSES}
    totals[_CLASS_UNCLASSIFIED] = 0
    returning = 0
    returned = 0
    unclassified = {}
    for row in rows:
        status = row.status if isinstance(row.status, str) else ""
        name = _classify_status(status=status)
        totals[name] += 1
        if name == _CLASS_RETURN:
            if status == "RETURNING":
                returning += 1
            else:
                returned += 1
        elif name == _CLASS_UNCLASSIFIED:
            unclassified[status] = unclassified.get(status, 0) + 1
    counts = DeliveryStatusCounts(
        shipments=len(rows),
        delivered=totals[_CLASS_SUCCESS],
        failed=totals[_CLASS_FAILURE],
        returning=returning,
        returned=returned,
        in_flight=totals[_CLASS_IN_FLIGHT],
        cancelled=totals[_CLASS_CANCELLED],
        unclassified=totals[_CLASS_UNCLASSIFIED],
        unclassified_statuses=tuple(
            (status, unclassified[status]) for status in sorted(unclassified)
        ),
    )
    partition = (
        counts.delivered + counts.failed + counts.returns + counts.in_flight
        + counts.cancelled + counts.unclassified
    )
    if partition != counts.shipments:
        raise DeliveryCalculationError(
            "Shipment classification did not partition the scope: "
            f"{partition} classified of {counts.shipments} shipments."
        )
    return counts


def _counts_inputs(counts):
    return {
        "shipments": counts.shipments,
        "delivered": counts.delivered,
        "failed": counts.failed,
        "returning": counts.returning,
        "returned": counts.returned,
        "in_flight": counts.in_flight,
        "cancelled": counts.cancelled,
        "unclassified": counts.unclassified,
        # Named so a reader can tell whether a rate covered all shipments.
        "unclassified_statuses": [
            {"status": status, "count": count}
            for status, count in counts.unclassified_statuses
        ],
    }


def _scope_inputs(cohort, dimension_type, dimension_value, region_metadata_key):
    return {
        "cohort": cohort,
        "cohort_field": _COHORT_TIMESTAMP_FIELDS[cohort],
        "scope": {
            "dimension_type": dimension_type,
            "dimension_value": dimension_value,
            "region_metadata_key": region_metadata_key,
        },
    }


def _recorded_currency(business_id, snapshot_id):
    """Read back the currency an existing observation was recorded for."""
    metadata = models.MetricSnapshot.objects.filter(
        pk=snapshot_id, business_id=business_id
    ).values_list("metadata", flat=True).first()
    if not isinstance(metadata, dict):
        return None
    inputs = metadata.get("inputs")
    if not isinstance(inputs, dict):
        return None
    currency = inputs.get("currency")
    return currency if isinstance(currency, str) else None


def _require_no_variant_conflict(rule, scope, inputs):
    """Never let one delivery measure silently replace a different one.

    The ``MetricSnapshot`` logical identity is (business, metric, dimension,
    period_type, period_start, period_end) and does NOT include the calculation
    rule. Two different measures of the same metric and scope therefore land on
    one row: a second timing segment, the other cohort, or a second currency for
    the same cost scope. The snapshot contract would UPDATE the earlier row in
    place with a revision bump, so a reader could not tell that the number
    changed meaning — a wrong number with no error. Such a run raises here
    instead, naming both rules, which also keeps §13 Delivery Time Analysis
    honest: submission, pickup and successful delivery are three measures, and
    only one of them can occupy one snapshot identity.

    A genuine recalculation under the SAME variant still updates in place: that
    is late canonical data revising one measure, not one measure replacing
    another. Widening the snapshot identity is a shared ``metrics.py`` contract
    and is deliberately not attempted here.
    """
    existing = get_metric_snapshot(
        business_id=scope.business_id,
        metric_key=rule.metric_key,
        period_type=scope.period_type,
        period_start=scope.period_start,
        period_end=scope.period_end,
        dimension_type=scope.dimension_type,
        dimension_value=scope.dimension_value,
    )
    if existing is None:
        return
    if existing.calculation_rule != rule.calculation_rule:
        raise DeliveryCalculationError(
            f"Snapshot {existing.snapshot_id} already holds this period and "
            f"scope for {rule.metric_key} under calculation rule "
            f"{existing.calculation_rule}, which measures something different "
            f"from {rule.calculation_rule}. The snapshot identity does not "
            "include the calculation rule, so recording this would silently "
            "replace that measure; record the other variant under a distinct "
            "dimension or period, or call with record=False."
        )
    currency = inputs.get("currency")
    if currency is None:
        return
    recorded = _recorded_currency(scope.business_id, existing.snapshot_id)
    if recorded is not None and recorded != currency:
        raise DeliveryCalculationError(
            f"Snapshot {existing.snapshot_id} already holds this period and "
            f"scope for {rule.metric_key} in {recorded}; recording {currency} "
            "would silently replace an amount in another currency. Record the "
            "second currency under the CURRENCY dimension."
        )


def _record(rule, scope, value, inputs, record):
    """Write one observation through the §3 snapshot contract, or skip it."""
    if not record:
        return None
    if value is not UNAVAILABLE:
        # An unavailable run writes nothing and leaves any existing row
        # untouched, so it can never replace another measure.
        _require_no_variant_conflict(rule, scope, inputs)
    return record_metric_snapshot(
        business_id=scope.business_id,
        metric_key=rule.metric_key,
        value=value,
        period_type=scope.period_type,
        period_start=scope.period_start,
        period_end=scope.period_end,
        dimension_type=scope.dimension_type,
        dimension_value=scope.dimension_value,
        calculation_rule=rule.calculation_rule,
        inputs=inputs,
    )


# --------------------------------------------------------------------------
# §13 Delivery Success Rate, Delivery Failure Rate, Return Rate Analysis
# --------------------------------------------------------------------------

def _outcome_result(scope, rows, excluded_unsubmitted, region_metadata_key, record):
    counts = _count_statuses(rows)
    denominator = Decimal(counts.shipments)
    rates = {
        METRIC_SUCCESS_RATE: _require_fraction(
            _divide(Decimal(counts.delivered), denominator), "success_rate"
        ),
        METRIC_FAILURE_RATE: _require_fraction(
            _divide(Decimal(counts.failed), denominator), "failure_rate"
        ),
        METRIC_RETURN_RATE: _require_fraction(
            _divide(Decimal(counts.returns), denominator), "return_rate"
        ),
    }
    inputs = dict(
        _scope_inputs(scope.cohort, scope.dimension_type, scope.dimension_value,
                      region_metadata_key),
        **_counts_inputs(counts),
        status_set_version=_STATUS_SET_VERSION,
        status_sets=_status_set_inputs(),
        denominator="ALL_COHORT_SHIPMENTS_IN_SCOPE",
        denominator_includes_in_flight=True,
        # Business-wide for the period, NOT group-scoped: a shipment with no
        # submission time joins no cohort group at all, so the name says so.
        cohort_excluded_unsubmitted_business_wide=excluded_unsubmitted,
    )
    snapshots = {
        METRIC_SHIPMENTS: _record(
            get_delivery_rule(metric_key=METRIC_SHIPMENTS, cohort=scope.cohort),
            scope, Decimal(counts.shipments), inputs, record,
        )
    }
    for metric_key in _RATE_METRIC_KEYS:
        snapshots[metric_key] = _record(
            get_delivery_rule(metric_key=metric_key, cohort=scope.cohort),
            scope, rates[metric_key], inputs, record,
        )
    return DeliveryOutcomeResult(
        scope=scope,
        counts=counts,
        success_rate=rates[METRIC_SUCCESS_RATE],
        failure_rate=rates[METRIC_FAILURE_RATE],
        return_rate=rates[METRIC_RETURN_RATE],
        cohort_excluded_unsubmitted_business_wide=excluded_unsubmitted,
        inputs=MappingProxyType(dict(inputs)),
        shipments_snapshot=snapshots[METRIC_SHIPMENTS],
        success_rate_snapshot=snapshots[METRIC_SUCCESS_RATE],
        failure_rate_snapshot=snapshots[METRIC_FAILURE_RATE],
        return_rate_snapshot=snapshots[METRIC_RETURN_RATE],
    )


def calculate_delivery_outcome_rates(*, business_id, period_type, period_start,
                                     period_end, cohort=COHORT_SUBMITTED,
                                     dimension_type=None, dimension_value=None,
                                     region_metadata_key=None, record=True):
    """§13 success, failure and return rates plus the shipment count for one scope.

    The denominator is every shipment of the cohort inside the scope: in-flight
    shipments are counted there and in no numerator, so an incomplete period is
    visible through ``counts.in_flight`` rather than inflating the failure rate.
    With no shipment in scope the three rates are ``UNAVAILABLE`` and only the
    measured zero count is recorded. Performs no authorization.
    """
    _require_positive_id(business_id, "business_id")
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    _require_cohort(cohort)
    dimension_type, dimension_value, region_metadata_key = _require_dimension(
        dimension_type, dimension_value, region_metadata_key
    )
    _require_flag(record, "record")
    with transaction.atomic():
        _require_business(business_id)
        rows, excluded_unsubmitted = _load_cohort(
            business_id, cohort, period_start, period_end
        )
        rows = _scoped_rows(
            rows, business_id, dimension_type, dimension_value, region_metadata_key
        )
        scope = DeliveryScope(
            business_id=business_id, period_type=period_type,
            period_start=period_start, period_end=period_end, cohort=cohort,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )
        return _outcome_result(
            scope, rows, excluded_unsubmitted, region_metadata_key, record
        )


# --------------------------------------------------------------------------
# §13 Delivery Time Analysis
# --------------------------------------------------------------------------

def _timing_result(scope, segment, rows, region_metadata_key, record):
    start_field, end_field = _SEGMENT_TIMESTAMP_FIELDS[segment]
    # §13 Delivery Time Analysis measures "the time between shipment
    # submission, pickup, and SUCCESSFUL delivery", so a segment that ends at
    # the delivery timestamp only admits the success class: a stray
    # delivered_at on a FAILED or RETURNED shipment is not a successful
    # delivery. The submission-to-pickup leg is the courier handover, which
    # happens before any delivery outcome exists, so every status is eligible
    # there — filtering it by the final outcome would hide handover delays on
    # the shipments that later failed or were returned.
    requires_success = end_field == "delivered_at"
    durations = []
    missing_start = 0
    missing_end = 0
    success_without_end = 0
    out_of_order = 0
    not_success_with_both = 0
    for row in rows:
        start = getattr(row, start_field)
        end = getattr(row, end_field)
        is_success = _classify_status(status=row.status or "") == _CLASS_SUCCESS
        if end is None and is_success:
            # A shipment in the success class whose segment end timestamp is
            # missing contributes no fabricated duration; it is reported, not
            # approximated.
            success_without_end += 1
        if start is None:
            missing_start += 1
            continue
        if end is None:
            missing_end += 1
            continue
        if end < start:
            out_of_order += 1
            continue
        if requires_success and not is_success:
            # Checked last, so this counter holds exactly the shipments that
            # carry both ordered timestamps yet are not a successful delivery.
            not_success_with_both += 1
            continue
        durations.append(_seconds(end - start))
    measured = len(durations)
    total = _sum(durations)
    average = _divide(total, Decimal(measured))
    inputs = dict(
        _scope_inputs(scope.cohort, scope.dimension_type, scope.dimension_value,
                      region_metadata_key),
        segment=segment,
        start_field=start_field,
        end_field=end_field,
        requires_success_status=requires_success,
        eligible_statuses=sorted(_SUCCESS_STATUSES) if requires_success else None,
        shipments=len(rows),
        measured=measured,
        excluded_missing_start=missing_start,
        excluded_missing_end=missing_end,
        excluded_success_without_end_timestamp=success_without_end,
        excluded_out_of_order=out_of_order,
        excluded_not_success_with_both_timestamps=not_success_with_both,
        total_seconds=total,
    )
    rule = get_delivery_rule(
        metric_key=METRIC_TIME, cohort=scope.cohort, segment=segment
    )
    snapshot = _record(rule, scope, average, inputs, record)
    return DeliveryTimingResult(
        scope=scope,
        segment=segment,
        start_field=start_field,
        end_field=end_field,
        requires_success_status=requires_success,
        shipments=len(rows),
        measured=measured,
        excluded_missing_start=missing_start,
        excluded_missing_end=missing_end,
        excluded_success_without_end_timestamp=success_without_end,
        excluded_out_of_order=out_of_order,
        excluded_not_success_with_both_timestamps=not_success_with_both,
        total_seconds=total,
        average_seconds=average,
        inputs=MappingProxyType(dict(inputs)),
        snapshot=snapshot,
    )


def calculate_delivery_time(*, business_id, period_type, period_start, period_end,
                            segment=SEGMENT_SUBMISSION_TO_DELIVERY,
                            cohort=COHORT_SUBMITTED, dimension_type=None,
                            dimension_value=None, region_metadata_key=None,
                            record=True):
    """§13 Delivery Time Analysis: mean exact seconds for one documented segment.

    Only shipments carrying both of the segment's documented timestamps in order
    contribute. Missing endpoints, out-of-order endpoints and shipments without
    the segment's end timestamp are excluded and counted.

    Status eligibility, per §13 Delivery Time Analysis ("Measures the time
    between shipment submission, pickup, and successful delivery"): for
    ``SEGMENT_SUBMISSION_TO_DELIVERY`` and ``SEGMENT_PICKUP_TO_DELIVERY``, which
    end at ``delivered_at``, only shipments in the success class (DELIVERED) are
    measured, so a stray ``delivered_at`` on a FAILED or RETURNED shipment never
    enters a delivery time; those are counted in
    ``excluded_not_success_with_both_timestamps``. For
    ``SEGMENT_SUBMISSION_TO_PICKUP`` every status is eligible, because that leg
    measures the courier handover, which happens before any delivery outcome
    exists; restricting it to the success class would hide handover delays on
    exactly the shipments that later failed or were returned.

    With no timed shipment the average is ``UNAVAILABLE`` and nothing is
    recorded. Performs no authorization.
    """
    _require_positive_id(business_id, "business_id")
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    _require_cohort(cohort)
    _require_segment(segment)
    dimension_type, dimension_value, region_metadata_key = _require_dimension(
        dimension_type, dimension_value, region_metadata_key
    )
    _require_flag(record, "record")
    with transaction.atomic():
        _require_business(business_id)
        rows, _ = _load_cohort(business_id, cohort, period_start, period_end)
        rows = _scoped_rows(
            rows, business_id, dimension_type, dimension_value, region_metadata_key
        )
        scope = DeliveryScope(
            business_id=business_id, period_type=period_type,
            period_start=period_start, period_end=period_end, cohort=cohort,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )
        return _timing_result(scope, segment, rows, region_metadata_key, record)


# --------------------------------------------------------------------------
# §13 Delivery Cost Analysis
# --------------------------------------------------------------------------

def _cost_result(scope, rows, currency, region_metadata_key, record):
    in_currency = []
    excluded = {}
    for row in rows:
        row_currency = _label_of(row.currency)
        if row_currency == currency:
            in_currency.append(row)
        else:
            excluded[row_currency] = excluded.get(row_currency, 0) + 1
    for row in in_currency:
        if not isinstance(row.delivery_charge, Decimal):
            raise DeliveryCalculationError(
                f"Shipment {row.pk} delivery_charge is not a Decimal; delivery cost "
                "never converts a non-decimal number."
            )
    total_charge = _sum([row.delivery_charge for row in in_currency])

    order_ids = {row.order_id for row in in_currency}
    orders_matched = 0
    orders_mismatched = 0
    orders_unavailable = 0
    order_values = []
    matched_order_ids = set()
    if order_ids:
        found = set()
        orders = models.Order.objects.filter(
            business_id=scope.business_id, pk__in=sorted(order_ids)
        ).only("id", "currency", "total_amount").order_by("pk")
        for order in orders:
            found.add(order.pk)
            if _label_of(order.currency) != currency:
                orders_mismatched += 1
                continue
            if not isinstance(order.total_amount, Decimal):
                raise DeliveryCalculationError(
                    f"Order {order.pk} total_amount is not a Decimal; order "
                    "economics never convert a non-decimal number."
                )
            orders_matched += 1
            matched_order_ids.add(order.pk)
            order_values.append(order.total_amount)
        # An order the business-scoped query did not return belongs to another
        # business or no longer exists; its value is never borrowed.
        orders_unavailable = len(order_ids - found)
    order_value_total = _sum(order_values)
    # The share must divide like with like: only the charges of the shipments
    # whose order is in the matched set, over exactly those orders' value. The
    # recorded delivery_cost metric stays the full in-currency charge total, so
    # spend is not under-reported; the difference is reported separately.
    share_shipments = [row for row in in_currency if row.order_id in matched_order_ids]
    matched_charge_total = _sum([row.delivery_charge for row in share_shipments])
    charge_excluded_from_share = _sum([total_charge, -matched_charge_total])
    share = _divide(matched_charge_total, order_value_total)

    inputs = dict(
        _scope_inputs(scope.cohort, scope.dimension_type, scope.dimension_value,
                      region_metadata_key),
        currency=currency,
        shipments=len(rows),
        shipments_in_currency=len(in_currency),
        shipments_excluded_other_currency=sum(excluded.values()),
        excluded_currencies=[
            {"currency": code, "shipments": excluded[code]} for code in sorted(excluded)
        ],
        total_charge=total_charge,
        orders_matched=orders_matched,
        orders_excluded_currency_mismatch=orders_mismatched,
        orders_unavailable_in_business=orders_unavailable,
        order_value_total=order_value_total,
        shipments_in_share=len(share_shipments),
        shipments_excluded_from_share=len(in_currency) - len(share_shipments),
        matched_charge_total=matched_charge_total,
        charge_excluded_from_share=charge_excluded_from_share,
        charge_share_of_order_value=(
            None if share is UNAVAILABLE else share
        ),
    )
    rule = get_delivery_rule(metric_key=METRIC_COST, cohort=scope.cohort)
    # With no shipment in the currency scope nothing was observed about charges,
    # so the AMOUNT is unavailable rather than a measured zero spend. The
    # shipment count metric already records that the scope held zero shipments.
    snapshot = _record(
        rule, scope, total_charge if in_currency else UNAVAILABLE, inputs, record
    )
    return DeliveryCostResult(
        scope=scope,
        currency=currency,
        shipments=len(rows),
        shipments_in_currency=len(in_currency),
        shipments_excluded_other_currency=sum(excluded.values()),
        excluded_currencies=tuple((code, excluded[code]) for code in sorted(excluded)),
        total_charge=total_charge,
        orders_matched=orders_matched,
        orders_excluded_currency_mismatch=orders_mismatched,
        orders_unavailable_in_business=orders_unavailable,
        order_value_total=order_value_total,
        shipments_in_share=len(share_shipments),
        shipments_excluded_from_share=len(in_currency) - len(share_shipments),
        matched_charge_total=matched_charge_total,
        charge_excluded_from_share=charge_excluded_from_share,
        charge_share_of_order_value=share,
        inputs=MappingProxyType(dict(inputs)),
        snapshot=snapshot,
    )


def _resolve_currency(business, currency, dimension_type, dimension_value):
    """One currency per AMOUNT observation; charges are never summed across them."""
    if dimension_type == DIMENSION_CURRENCY:
        if currency is not None and _require_label(currency, "currency") != dimension_value:
            raise DeliveryValidationError(
                "currency contradicts the CURRENCY dimension value."
            )
        return dimension_value
    if currency is not None:
        return _require_label(currency, "currency")
    business_currency = business.currency
    if not isinstance(business_currency, str) or not business_currency.strip():
        raise DeliveryValidationError(
            "The business has no recorded currency, so the cost scope currency must "
            "be supplied explicitly."
        )
    return business_currency.strip()


def calculate_delivery_cost(*, business_id, period_type, period_start, period_end,
                            currency=None, cohort=COHORT_SUBMITTED,
                            dimension_type=None, dimension_value=None,
                            region_metadata_key=None, record=True):
    """§13 Delivery Cost Analysis: courier charges in one currency, and their share.

    The scope currency is the CURRENCY dimension value, else ``currency``, else
    ``Business.currency``; shipments in any other currency are excluded and
    counted. ``charge_share_of_order_value`` divides like with like: the charges
    of the shipments whose order is in the matched set, over exactly those
    orders' value, counting each order once. It is ``UNAVAILABLE`` when no
    positive order value matched, and charges whose order was excluded for a
    currency mismatch or is unavailable in this business are reported separately
    rather than inflating the ratio. Only the full in-currency charge total is
    recorded as a metric; the registry has no ratio key for the share.
    With no shipment in the currency scope the recorded value is ``UNAVAILABLE``
    rather than a measured zero spend. Performs no authorization.
    """
    _require_positive_id(business_id, "business_id")
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    _require_cohort(cohort)
    dimension_type, dimension_value, region_metadata_key = _require_dimension(
        dimension_type, dimension_value, region_metadata_key
    )
    _require_flag(record, "record")
    with transaction.atomic():
        business = _require_business(business_id)
        scope_currency = _resolve_currency(
            business, currency, dimension_type, dimension_value
        )
        rows, _ = _load_cohort(business_id, cohort, period_start, period_end)
        rows = _scoped_rows(
            rows, business_id, dimension_type, dimension_value, region_metadata_key
        )
        scope = DeliveryScope(
            business_id=business_id, period_type=period_type,
            period_start=period_start, period_end=period_end, cohort=cohort,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )
        return _cost_result(scope, rows, scope_currency, region_metadata_key, record)


# --------------------------------------------------------------------------
# §13 Courier Performance Comparison
# --------------------------------------------------------------------------

def compare_couriers(*, business_id, period_type, period_start, period_end,
                     cohort=COHORT_SUBMITTED,
                     segment=SEGMENT_SUBMISSION_TO_DELIVERY, currency=None,
                     minimum_shipments=None, record=True):
    """§13 Courier Performance Comparison across ``Shipment.provider``.

    Providers are discovered from the cohort and returned ordered by label, not
    ranked by outcome. Each provider gets its own success, failure, return,
    timing and cost measurement under the COURIER dimension. Shipments whose
    provider is blank cannot carry a dimension label and are reported as
    ``unresolved_courier_shipments`` instead of being merged into a fabricated
    provider. ``minimum_shipments`` is an optional caller-supplied reporting
    floor — there is no built-in threshold — and groups below it are neither
    returned nor recorded. Performs no authorization.
    """
    _require_positive_id(business_id, "business_id")
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    _require_cohort(cohort)
    _require_segment(segment)
    _require_optional_minimum(minimum_shipments, "minimum_shipments")
    _require_flag(record, "record")
    if currency is not None:
        currency = _require_label(currency, "currency")
    with transaction.atomic():
        business = _require_business(business_id)
        scope_currency = _resolve_currency(business, currency, None, None)
        rows, excluded_unsubmitted = _load_cohort(
            business_id, cohort, period_start, period_end
        )
        groups = {}
        unresolved = 0
        for row in rows:
            provider = _label_of(row.provider)
            if not provider or len(provider) > _DIMENSION_VALUE_MAX:
                unresolved += 1
                continue
            groups.setdefault(provider, []).append(row)
        performances = []
        below_minimum = 0
        for provider in sorted(groups):
            group = groups[provider]
            if minimum_shipments is not None and len(group) < minimum_shipments:
                below_minimum += 1
                continue
            scope = DeliveryScope(
                business_id=business_id, period_type=period_type,
                period_start=period_start, period_end=period_end, cohort=cohort,
                dimension_type=DIMENSION_COURIER, dimension_value=provider,
            )
            performances.append(CourierDeliveryPerformance(
                courier=provider,
                outcomes=_outcome_result(
                    scope, group, excluded_unsubmitted, None, record
                ),
                timing=_timing_result(scope, segment, group, None, record),
                cost=_cost_result(scope, group, scope_currency, None, record),
            ))
        return CourierComparison(
            couriers=tuple(performances),
            unresolved_courier_shipments=unresolved,
            couriers_below_minimum=below_minimum,
            minimum_shipments=minimum_shipments,
        )


# --------------------------------------------------------------------------
# §13 Regional Delivery Analysis
# --------------------------------------------------------------------------

def analyze_regional_delivery(*, business_id, period_type, period_start, period_end,
                              region_metadata_key, cohort=COHORT_SUBMITTED,
                              segment=SEGMENT_SUBMISSION_TO_DELIVERY,
                              minimum_shipments=None, record=True):
    """§13 Regional Delivery Analysis: failures, returns and delays per region.

    The schema carries no canonical region column — ``Shipment.delivery_address``
    is free text and is deliberately NOT parsed — so the region label is read
    from the normalized ``Shipment.source_metadata`` under the caller-configured
    ``region_metadata_key``. Shipments whose label cannot be resolved are
    reported with their reason instead of being bucketed into an invented
    region. Regions are returned ordered by label, never ranked: "unusually
    high" is a threshold owned by configurable anomaly rules (T-010) and issue
    detection (T-011), so no literal threshold exists here.
    ``minimum_shipments`` is an optional caller-supplied reporting floor.
    Performs no authorization.
    """
    _require_positive_id(business_id, "business_id")
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    _require_cohort(cohort)
    _require_segment(segment)
    region_metadata_key = _require_region_metadata_key(region_metadata_key)
    _require_optional_minimum(minimum_shipments, "minimum_shipments")
    _require_flag(record, "record")
    with transaction.atomic():
        _require_business(business_id)
        rows, excluded_unsubmitted = _load_cohort(
            business_id, cohort, period_start, period_end
        )
        groups = {}
        reasons = {reason: 0 for reason in _REGION_UNRESOLVED_REASONS}
        unresolved = 0
        for row in rows:
            label, reason = _region_label(row, region_metadata_key)
            if label is None:
                reasons[reason] += 1
                unresolved += 1
                continue
            groups.setdefault(label, []).append(row)
        performances = []
        below_minimum = 0
        for label in sorted(groups):
            group = groups[label]
            if minimum_shipments is not None and len(group) < minimum_shipments:
                below_minimum += 1
                continue
            scope = DeliveryScope(
                business_id=business_id, period_type=period_type,
                period_start=period_start, period_end=period_end, cohort=cohort,
                dimension_type=DIMENSION_REGION, dimension_value=label,
            )
            performances.append(RegionDeliveryPerformance(
                region=label,
                outcomes=_outcome_result(
                    scope, group, excluded_unsubmitted, region_metadata_key, record
                ),
                timing=_timing_result(
                    scope, segment, group, region_metadata_key, record
                ),
            ))
        return RegionalDeliveryAnalysis(
            region_metadata_key=region_metadata_key,
            regions=tuple(performances),
            unresolved_shipments=unresolved,
            unresolved_reasons=tuple(
                (reason, reasons[reason]) for reason in _REGION_UNRESOLVED_REASONS
                if reasons[reason]
            ),
            regions_below_minimum=below_minimum,
            minimum_shipments=minimum_shipments,
        )


# --------------------------------------------------------------------------
# §13 Product Delivery Analysis
# --------------------------------------------------------------------------

def analyze_product_delivery(*, business_id, period_type, period_start, period_end,
                             cohort=COHORT_SUBMITTED, minimum_shipments=None,
                             record=True):
    """§13 Product Delivery Analysis through the §1 order→product relationships.

    Products are reached from the shipment's order using the relationships the
    relationship service already produced (``CONTAINS_PRODUCT``, still valid),
    never by re-deriving order items here. A shipment counts once for every
    product its order contains, so per-product scopes overlap by design and do
    not sum to the business-wide figure. Shipments whose order has no valid
    product relationship are reported as
    ``shipments_without_product_relationship``, which is how an un-rebuilt
    relationship set shows up instead of silently emptying the analysis.
    Products are ordered by canonical id, never ranked:
    "disproportionately associated" is a threshold owned by T-010/T-011.
    Performs no authorization.
    """
    _require_positive_id(business_id, "business_id")
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    _require_cohort(cohort)
    _require_optional_minimum(minimum_shipments, "minimum_shipments")
    _require_flag(record, "record")
    with transaction.atomic():
        _require_business(business_id)
        rows, excluded_unsubmitted = _load_cohort(
            business_id, cohort, period_start, period_end
        )
        mapping = _order_product_map(business_id, {row.order_id for row in rows})
        groups = {}
        without_relationship = 0
        for row in rows:
            products = mapping.get(row.order_id, ())
            if not products:
                without_relationship += 1
                continue
            for product_id in products:
                groups.setdefault(product_id, []).append(row)
        performances = []
        below_minimum = 0
        for product_id in sorted(groups):
            group = groups[product_id]
            if minimum_shipments is not None and len(group) < minimum_shipments:
                below_minimum += 1
                continue
            scope = DeliveryScope(
                business_id=business_id, period_type=period_type,
                period_start=period_start, period_end=period_end, cohort=cohort,
                dimension_type=DIMENSION_PRODUCT, dimension_value=str(product_id),
            )
            performances.append(ProductDeliveryPerformance(
                product_id=product_id,
                outcomes=_outcome_result(
                    scope, group, excluded_unsubmitted, None, record
                ),
            ))
        return ProductDeliveryAnalysis(
            products=tuple(performances),
            shipments_without_product_relationship=without_relationship,
            relationship_rule_key=_ORDER_PRODUCT_RULE.key,
            products_below_minimum=below_minimum,
            minimum_shipments=minimum_shipments,
        )


# --------------------------------------------------------------------------
# §13 Customer Delivery Analysis
# --------------------------------------------------------------------------

def analyze_customer_delivery(*, business_id, period_type, period_start, period_end,
                              cohort=COHORT_SUBMITTED,
                              minimum_failed_or_returned=None):
    """§13 Customer Delivery Analysis: observed failed and returned shipments.

    This counts outcomes per resolved customer and nothing else. No customer is
    labelled risky, abusive or fraudulent and no customer is ranked by outcome:
    that interpretation belongs to issue detection (T-011). "Repeated" is a
    threshold, so ``minimum_failed_or_returned`` is a caller-supplied reporting
    floor with no default. Nothing is recorded as a metric snapshot: the metric
    registry declares no CUSTOMER dimension, and inventing one is out of scope
    for this ticket. Shipments with no resolved customer are counted separately
    through identity already resolved upstream; no identity decision is made
    here. Performs no authorization.
    """
    _require_positive_id(business_id, "business_id")
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    _require_cohort(cohort)
    _require_optional_minimum(minimum_failed_or_returned, "minimum_failed_or_returned")
    with transaction.atomic():
        _require_business(business_id)
        rows, _ = _load_cohort(business_id, cohort, period_start, period_end)
        groups = {}
        without_customer = 0
        for row in rows:
            if row.customer_id is None:
                without_customer += 1
                continue
            groups.setdefault(row.customer_id, []).append(row)
        outcomes = []
        below_minimum = 0
        for customer_id in sorted(groups):
            counts = _count_statuses(groups[customer_id])
            failed_or_returned = counts.failed + counts.returns
            if (minimum_failed_or_returned is not None
                    and failed_or_returned < minimum_failed_or_returned):
                below_minimum += 1
                continue
            outcomes.append(CustomerDeliveryOutcome(
                customer_id=customer_id,
                counts=counts,
                failed_or_returned=failed_or_returned,
            ))
        scope = DeliveryScope(
            business_id=business_id, period_type=period_type,
            period_start=period_start, period_end=period_end, cohort=cohort,
            dimension_type=None, dimension_value=None,
        )
        return CustomerDeliveryAnalysis(
            scope=scope,
            customers=tuple(outcomes),
            shipments=len(rows),
            shipments_without_customer=without_customer,
            customers_below_minimum=below_minimum,
            minimum_failed_or_returned=minimum_failed_or_returned,
        )
