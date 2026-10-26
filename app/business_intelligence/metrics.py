"""BI specification §2 and §3: the metric registry and the snapshot contract.

Public API (all keyword-only, all internal — callers authorize business access
before invoking anything here):

* ``sync_metric_registry(*, business_id)`` materializes one ``BusinessMetric``
  row per closed registry definition (§2 Metric Registry) and deactivates
  service-owned rows whose definition was retired.
* ``list_metric_definitions(*, category=None)`` and
  ``get_metric_definition(*, metric_key)``
  expose the registry: the single documented name, category, value type and
  unit for every supported metric concept.
* ``record_metric_snapshot(...)`` writes one reproducible observation for a
  (metric, dimension, period) scope (§3) and is replay-safe.
* ``get_metric_snapshot(...)``, ``get_metric_observation(...)``,
  ``list_metric_snapshots(...)`` and ``compare_metric_periods(...)`` read
  observations back for historical comparison, trend analysis and for facts and
  issues that must cite the exact observation they were derived from.

What this module does not do: it never calculates a metric value. The registry
names the seven documented metric families (Sales, Revenue, Customer,
Marketing, Support, Website, Delivery); the arithmetic, the eligible-source and
eligible-status filters and any threshold belong to the later calculation
tickets, which pass their result in and record their own ``calculation_rule``.
It adds no authentication, authorization, HTTP surface, schema change, policy
threshold, provider access or identity decision.

Registry rules. ``METRIC_DEFINITIONS`` is closed and versioned: every key is
``bi.metric.<name>.v<n>``. A definition's meaning is frozen; changing what a
metric measures requires a new ``.v2`` key so historical snapshots stay
comparable. ``value_type`` and ``unit`` come from closed vocabularies and are
checked against each other, so two modules cannot record the same concept in
different units. Ratios are stored as fractions (0.25), never as percentages;
durations are stored in seconds; ``AMOUNT`` metrics carry the unit ``CURRENCY``.

Currency. A snapshot has no currency column and carries at most one dimension,
so an ``AMOUNT`` observation is always recorded for a single currency scope:
either explicitly through the ``CURRENCY`` dimension, or — when the snapshot
carries another dimension or none — in the business's own recorded currency,
which the calculation rule must state and must never mix. Splitting one AMOUNT
by currency *and* by product at the same time is not expressible in this
schema; that limitation belongs to the calculation tickets, not to this
contract, and it is not worked around here with an extra column or table.

Periods are half-open ``[period_start, period_end)``; ``period_end`` must be
strictly after ``period_start`` and both must be timezone-aware. The service
does not enforce calendar alignment or duration for ``HOUR``/``DAY``/``WEEK``/
``MONTH``: the reporting timezone that would define a business day is a
pending team contract, so ``period_type`` is a label and the half-open bounds
are the authority. ``CUSTOM`` exists for periods that match no calendar unit.

Dimensions (§2 Metric Dimensions, §3 Dimension-Based Snapshots) come from the
closed ``DIMENSION_TYPES`` map. ``dimension_type`` and ``dimension_value`` are
both present or both absent; an absent pair means the business-wide scope.
Entity dimensions take a canonical primary-key string that must resolve inside
the given business, so a caller-supplied id can never reach another business's
data. Label dimensions take a canonical label and are stored verbatim after
whitespace stripping; label spelling is compared exactly, so a caller that
spells one label two ways creates two logical observations. Deriving the label
from canonical data (for example the shipment provider) is the calculation
rule's job; no case folding or aliasing is invented here.

Values are ``Decimal`` only — floats and numeric strings are rejected, so no
binary rounding error can enter an observation. Values are quantized to the
schema's six decimal places with banker's rounding (``ROUND_HALF_EVEN``) before
they are written, so both configured databases receive an identically rounded
decimal; when quantization changed the number the caller's exact input is
preserved in ``metadata["rounded_from"]``. A value whose magnitude exceeds the
schema's 18 integer digits is rejected rather than silently truncated.
Read-back precision is NOT identical across backends: SQLite stores NUMERIC as
a float and keeps roughly 15 significant digits, so a value with 16 or more
significant digits (a large integer part together with six decimals) does not
round-trip exactly there, while PostgreSQL NUMERIC does. Observations in normal
business ranges are unaffected; this limit is not worked around here.

Unavailable data is never written as zero. A caller with no data for a scope
passes the ``UNAVAILABLE`` sentinel: nothing is written, the result status is
``NOT_RECORDED_UNAVAILABLE`` and "no data" is therefore represented by the
absence of a snapshot row. Every row this service does write carries
``metadata["data_available"] = True``, so a recorded zero is always a measured
zero. An earlier observation for the same scope is never deleted or rewritten
by an unavailable run; its id is returned as ``existing_snapshot_id`` and
whether a published period must be withdrawn is an analysis decision owned by
later tickets.

Reproducibility. ``MetricSnapshot`` has no database unique constraint, so one
logical observation per (business, metric, dimension_type, dimension_value,
period_type, period_start, period_end) is enforced here: a repeat run updates
that row in place and never appends a second row. A recalculation that produces
a different value UPDATES the row rather than being rejected, because late
canonical data (refunds, delivery outcomes) legitimately changes a closed
period; the superseded value, rule and calculation time are kept in
``metadata["supersedes"]`` and ``metadata["revision"]`` increments, so the
change stays traceable. Only the immediately previous observation is retained
there — the revision counter, not a full audit trail, records how many times a
period was recalculated. A replay that produces the same value and rule touches
nothing and preserves the row id and all timestamps. ``calculated_at`` is set
by this service, never by the caller. If the identity is occupied by a row this
service does not own, or by more than one row (only possible if a
non-cooperating writer raced the lock), the operation raises
``MetricSnapshotConflictError`` instead of guessing which row is authoritative.

Each public operation runs in one ``transaction.atomic()`` block and any
validation or conflict error rolls the whole operation back. Writes take a
``Business`` row lock to serialize cooperating writers; SQLite does not
implement ``select_for_update`` row locking, so concurrency guarantees there
rest on its database-level locking.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import datetime
import re

from django.db import IntegrityError, transaction
from django.utils import timezone

from app import models


class MetricValidationError(ValueError):
    """A boundary input, metric key, period, dimension or value is invalid."""


class MetricSnapshotConflictError(ValueError):
    """The logical observation identity is occupied by rows this service does not own."""


class MetricDefinitionError(ValueError):
    """The hard-coded registry itself is internally inconsistent."""


# --------------------------------------------------------------------------
# Schema-derived limits: never duplicate a column limit as a literal.
# --------------------------------------------------------------------------

def _field(model, name):
    # Forward concrete fields only: this never walks the reverse relation tree,
    # so the limits can be resolved at import time without the app registry.
    for field in model._meta.concrete_fields:
        if field.name == name:
            return field
    raise MetricDefinitionError(f"{model.__name__} has no field named {name!r}.")


_VALUE_FIELD = _field(models.MetricSnapshot, "value")
_VALUE_DECIMAL_PLACES = _VALUE_FIELD.decimal_places
_VALUE_MAX_DIGITS = _VALUE_FIELD.max_digits
_VALUE_QUANTUM = Decimal(1).scaleb(-_VALUE_DECIMAL_PLACES)
_VALUE_ABS_LIMIT = Decimal(10) ** (_VALUE_MAX_DIGITS - _VALUE_DECIMAL_PLACES)
_DECIMAL_PRECISION = 2 * _VALUE_MAX_DIGITS + _VALUE_DECIMAL_PLACES

_METRIC_KEY_MAX = _field(models.BusinessMetric, "key").max_length
_METRIC_NAME_MAX = _field(models.BusinessMetric, "name").max_length
_METRIC_CATEGORY_MAX = _field(models.BusinessMetric, "category").max_length
_METRIC_VALUE_TYPE_MAX = _field(models.BusinessMetric, "value_type").max_length
_METRIC_UNIT_MAX = _field(models.BusinessMetric, "unit").max_length
_DIMENSION_TYPE_MAX = _field(models.MetricSnapshot, "dimension_type").max_length
_DIMENSION_VALUE_MAX = _field(models.MetricSnapshot, "dimension_value").max_length
_PERIOD_TYPE_MAX = _field(models.MetricSnapshot, "period_type").max_length
_CALCULATION_RULE_MAX = _field(models.MetricSnapshot, "calculation_rule").max_length


# --------------------------------------------------------------------------
# Closed vocabularies
# --------------------------------------------------------------------------

_OWNER = "business_intelligence.metrics"
_KEY_PREFIX = "bi.metric."
_METRIC_KEY_RE = re.compile(r"^bi\.metric\.[a-z0-9_]+\.v[1-9][0-9]*$")
_RULE_VARIANT_RE = re.compile(r"^[a-z0-9_]+$")
_DEFINITION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

CATEGORIES = frozenset({
    "SALES", "REVENUE", "CUSTOMER", "MARKETING", "SUPPORT", "WEBSITE", "DELIVERY",
})

# A value type fixes how a number must be read; its units are closed so the
# same concept cannot be recorded in two scales by two modules.
VALUE_TYPE_UNITS = {
    "COUNT": frozenset({
        "ORDERS", "UNITS", "CUSTOMERS", "SESSIONS", "CONVERSATIONS",
        "SHIPMENTS", "IMPRESSIONS", "CLICKS", "CONVERSIONS", "EVENTS",
    }),
    "AMOUNT": frozenset({"CURRENCY"}),
    "RATIO": frozenset({"RATIO"}),
    "DURATION": frozenset({"SECONDS"}),
    "NUMBER": frozenset({"ORDERS_PER_CUSTOMER"}),
}
VALUE_TYPES = frozenset(VALUE_TYPE_UNITS)
UNITS = frozenset(unit for units in VALUE_TYPE_UNITS.values() for unit in units)

# §3 Time-Based Metric Storage: hourly, daily, weekly, monthly or custom.
PERIOD_TYPES = frozenset({"HOUR", "DAY", "WEEK", "MONTH", "CUSTOM"})

# §2 Metric Dimensions / §3 Dimension-Based Snapshots. ENTITY values are
# canonical primary keys validated inside the business; LABEL values are
# canonical labels carried by the canonical data itself (for example the
# shipment provider for COURIER, or the business currency code for CURRENCY).
DIMENSION_TYPES = {
    "PRODUCT": "ENTITY",
    "PRODUCT_VARIANT": "ENTITY",
    "CAMPAIGN": "ENTITY",
    "REGION": "LABEL",
    "COURIER": "LABEL",
    "CHANNEL": "LABEL",
    "CUSTOMER_SEGMENT": "LABEL",
    "CURRENCY": "LABEL",
}

_ENTITY_DIMENSION_SCOPES = {
    "PRODUCT": (models.Product, "business_id"),
    "PRODUCT_VARIANT": (models.ProductVariant, "product__business_id"),
    "CAMPAIGN": (models.Campaign, "business_id"),
}

WRITE_CREATED = "CREATED"
WRITE_UPDATED = "UPDATED"
WRITE_UNCHANGED = "UNCHANGED"
WRITE_NOT_RECORDED_UNAVAILABLE = "NOT_RECORDED_UNAVAILABLE"
WRITE_STATUSES = frozenset({
    WRITE_CREATED, WRITE_UPDATED, WRITE_UNCHANGED, WRITE_NOT_RECORDED_UNAVAILABLE,
})

DIRECTION_INCREASED = "INCREASED"
DIRECTION_DECREASED = "DECREASED"
DIRECTION_UNCHANGED = "UNCHANGED"
DIRECTION_UNAVAILABLE = "UNAVAILABLE"
COMPARISON_DIRECTIONS = frozenset({
    DIRECTION_INCREASED, DIRECTION_DECREASED, DIRECTION_UNCHANGED, DIRECTION_UNAVAILABLE,
})

_METADATA_HISTORY_KEYS = ("revision", "supersedes")


class _Unavailable:
    """Sentinel: the calculation had no data for this scope, which is not zero."""

    __slots__ = ()

    def __repr__(self):
        return "UNAVAILABLE"


UNAVAILABLE = _Unavailable()


# --------------------------------------------------------------------------
# Registry (§2)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class MetricDefinition:
    key: str
    name: str
    category: str
    value_type: str
    unit: str
    description: str


def _define(name, *, display, category, value_type, unit, description, version=1):
    """Build one registry definition and fail loudly on an inconsistent entry."""
    if not _DEFINITION_NAME_RE.match(name):
        raise MetricDefinitionError(f"Metric name {name!r} is not a lowercase identifier.")
    key = f"{_KEY_PREFIX}{name}.v{version}"
    if len(key) > _METRIC_KEY_MAX or not _METRIC_KEY_RE.match(key):
        raise MetricDefinitionError(f"Metric key {key!r} is invalid or too long.")
    if category not in CATEGORIES or len(category) > _METRIC_CATEGORY_MAX:
        raise MetricDefinitionError(f"Metric {key} has an unsupported category {category!r}.")
    if value_type not in VALUE_TYPES or len(value_type) > _METRIC_VALUE_TYPE_MAX:
        raise MetricDefinitionError(f"Metric {key} has an unsupported value type {value_type!r}.")
    if unit not in VALUE_TYPE_UNITS[value_type] or len(unit) > _METRIC_UNIT_MAX:
        raise MetricDefinitionError(f"Metric {key} may not use unit {unit!r} with {value_type!r}.")
    if not display or len(display) > _METRIC_NAME_MAX:
        raise MetricDefinitionError(f"Metric {key} has an invalid display name.")
    if not description:
        raise MetricDefinitionError(f"Metric {key} must document what it measures.")
    return MetricDefinition(
        key=key,
        name=display,
        category=category,
        value_type=value_type,
        unit=unit,
        description=description,
    )


def _registry(*definitions):
    registry = {}
    for definition in definitions:
        if definition.key in registry:
            raise MetricDefinitionError(f"Duplicate metric key {definition.key}.")
        registry[definition.key] = definition
    return registry


# A closed catalog: a new metric concept requires an explicit, reviewable entry,
# and a changed meaning requires a new version. Each description states the
# measured concept and its unit only; the eligible sources, the eligible record
# statuses and the arithmetic live in the metric's calculation rule, which the
# implementing ticket records in MetricSnapshot.calculation_rule.
METRIC_DEFINITIONS = _registry(
    # Sales metrics (§2 Sales Metrics)
    _define(
        "sales_total_orders",
        display="Total Orders",
        category="SALES",
        value_type="COUNT",
        unit="ORDERS",
        description=(
            "Number of orders counted in the period for the snapshot scope. The "
            "order-status eligibility filter is defined by the calculation rule."
        ),
    ),
    _define(
        "sales_units_sold",
        display="Units Sold",
        category="SALES",
        value_type="COUNT",
        unit="UNITS",
        description=(
            "Number of product units contained in the eligible orders of the period."
        ),
    ),
    _define(
        "sales_average_order_value",
        display="Average Order Value",
        category="SALES",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Eligible order value divided by the number of eligible orders, in a "
            "single currency scope."
        ),
    ),
    _define(
        "sales_cancellation_rate",
        display="Order Cancellation Rate",
        category="SALES",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fraction of the period's counted orders that are cancelled. Stored as a "
            "fraction, not a percentage."
        ),
    ),
    _define(
        "sales_growth_rate",
        display="Sales Growth Rate",
        category="SALES",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fractional change in sales between this period and the compared earlier "
            "period of the same period type and dimension."
        ),
    ),
    # Revenue metrics (§2 Revenue Metrics)
    _define(
        "revenue_gross",
        display="Gross Revenue",
        category="REVENUE",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Revenue recognized from eligible orders or payments in the period, before "
            "refunds, in a single currency scope."
        ),
    ),
    _define(
        "revenue_refunded",
        display="Refunded Revenue",
        category="REVENUE",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Revenue refunded in the period, recorded as a positive amount in a "
            "single currency scope."
        ),
    ),
    _define(
        "revenue_net",
        display="Net Revenue",
        category="REVENUE",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Gross revenue of the period minus the refunded revenue attributed to it by "
            "the calculation rule."
        ),
    ),
    _define(
        "revenue_growth_rate",
        display="Revenue Growth Rate",
        category="REVENUE",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fractional change in revenue between this period and the compared earlier "
            "period of the same period type and dimension."
        ),
    ),
    _define(
        "revenue_per_customer",
        display="Revenue Per Customer",
        category="REVENUE",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Revenue of the period divided by the number of customers counted by the "
            "calculation rule for the same scope."
        ),
    ),
    # Customer metrics (§2 Customer Metrics)
    _define(
        "customer_new_customers",
        display="New Customers Acquired",
        category="CUSTOMER",
        value_type="COUNT",
        unit="CUSTOMERS",
        description=(
            "Number of resolved customers whose first eligible purchase falls inside the "
            "period for this scope."
        ),
    ),
    _define(
        "customer_active_customers",
        display="Active Customers",
        category="CUSTOMER",
        value_type="COUNT",
        unit="CUSTOMERS",
        description=(
            "Number of distinct resolved customers with at least one eligible order in "
            "the period for this scope."
        ),
    ),
    _define(
        "customer_repeat_rate",
        display="Repeat Customer Rate",
        category="CUSTOMER",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fraction of the period's counted customers with more than one eligible "
            "order. Stored as a fraction, not a percentage."
        ),
    ),
    _define(
        "customer_purchase_frequency",
        display="Customer Purchase Frequency",
        category="CUSTOMER",
        value_type="NUMBER",
        unit="ORDERS_PER_CUSTOMER",
        description=(
            "Eligible orders of the period divided by the number of customers who placed "
            "them, expressed as orders per customer."
        ),
    ),
    _define(
        "customer_average_value",
        display="Average Customer Value",
        category="CUSTOMER",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Average value realized per counted customer in the period, in a single "
            "currency scope."
        ),
    ),
    # Marketing metrics (§2 Marketing Metrics)
    _define(
        "marketing_spend",
        display="Advertising Spend",
        category="MARKETING",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Advertising spend reported for the period and scope, in a single "
            "currency scope."
        ),
    ),
    _define(
        "marketing_impressions",
        display="Impressions",
        category="MARKETING",
        value_type="COUNT",
        unit="IMPRESSIONS",
        description="Impressions reported for the period and scope.",
    ),
    _define(
        "marketing_clicks",
        display="Clicks",
        category="MARKETING",
        value_type="COUNT",
        unit="CLICKS",
        description="Clicks reported for the period and scope.",
    ),
    _define(
        "marketing_click_through_rate",
        display="Click-Through Rate (CTR)",
        category="MARKETING",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Clicks divided by impressions for the period and scope. Stored as a "
            "fraction, not a percentage."
        ),
    ),
    _define(
        "marketing_cost_per_click",
        display="Cost Per Click (CPC)",
        category="MARKETING",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Spend divided by clicks for the period and scope, in a single currency "
            "scope."
        ),
    ),
    _define(
        "marketing_cost_per_mille",
        display="Cost Per Mille (CPM)",
        category="MARKETING",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Spend per one thousand impressions for the period and scope, in a "
            "single currency scope."
        ),
    ),
    _define(
        "marketing_conversions",
        display="Marketing Conversions",
        category="MARKETING",
        value_type="COUNT",
        unit="CONVERSIONS",
        description=(
            "Conversions counted for the period and scope. The calculation rule states "
            "whether the conversions are platform-reported or evidence-attributed."
        ),
    ),
    _define(
        "marketing_conversion_rate",
        display="Marketing Conversion Rate",
        category="MARKETING",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Conversions divided by the interaction count named by the calculation rule. "
            "Stored as a fraction, not a percentage."
        ),
    ),
    _define(
        "marketing_attributed_revenue",
        display="Attributed Revenue",
        category="MARKETING",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Revenue attributed to the scope by an explicit attribution rule, in a "
            "single currency scope."
        ),
    ),
    _define(
        "marketing_return_on_ad_spend",
        display="Return On Ad Spend (ROAS)",
        category="MARKETING",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Attributed revenue divided by spend for the period and scope, in one "
            "currency. Stored as a ratio, not a percentage."
        ),
    ),
    # Support metrics (§2 Support Metrics)
    _define(
        "support_response_time",
        display="Support Response Time",
        category="SUPPORT",
        value_type="DURATION",
        unit="SECONDS",
        description=(
            "Average time in seconds between an inbound customer message and the "
            "business reply counted by the calculation rule."
        ),
    ),
    _define(
        "support_resolution_time",
        display="Support Resolution Time",
        category="SUPPORT",
        value_type="DURATION",
        unit="SECONDS",
        description=(
            "Average time in seconds from the start of a conversation to the resolution "
            "state named by the calculation rule."
        ),
    ),
    _define(
        "support_conversation_volume",
        display="Conversation Volume",
        category="SUPPORT",
        value_type="COUNT",
        unit="CONVERSATIONS",
        description="Number of conversations counted in the period for this scope.",
    ),
    _define(
        "support_unresolved_cases",
        display="Unresolved Support Cases",
        category="SUPPORT",
        value_type="COUNT",
        unit="CONVERSATIONS",
        description=(
            "Number of conversations still in an unresolved state at the end of the "
            "period, as defined by the calculation rule."
        ),
    ),
    _define(
        "support_escalation_rate",
        display="Support Escalation Rate",
        category="SUPPORT",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fraction of the period's counted conversations that were escalated. Stored "
            "as a fraction, not a percentage."
        ),
    ),
    # Website metrics (§2 Website Metrics)
    _define(
        "website_sessions",
        display="Website Sessions",
        category="WEBSITE",
        value_type="COUNT",
        unit="SESSIONS",
        description="Number of website sessions counted in the period for this scope.",
    ),
    _define(
        "website_product_views",
        display="Product Views",
        category="WEBSITE",
        value_type="COUNT",
        unit="EVENTS",
        description=(
            "Number of product-view website events counted in the period for this scope."
        ),
    ),
    _define(
        "website_conversion_rate",
        display="Website Conversion Rate",
        category="WEBSITE",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Converting sessions divided by counted sessions for the period and scope. "
            "Stored as a fraction, not a percentage."
        ),
    ),
    _define(
        "website_checkout_completion_rate",
        display="Checkout Completion Rate",
        category="WEBSITE",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Completed checkouts divided by started checkouts for the period and scope. "
            "Stored as a fraction, not a percentage."
        ),
    ),
    _define(
        "website_cart_abandonment_rate",
        display="Cart Abandonment Rate",
        category="WEBSITE",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fraction of the period's counted carts that were not converted into an "
            "order. Stored as a fraction, not a percentage."
        ),
    ),
    _define(
        "website_product_view_conversion_rate",
        display="Product-View Conversion Rate",
        category="WEBSITE",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Purchases divided by product views for the period and scope. Stored as a "
            "fraction, not a percentage."
        ),
    ),
    # Delivery metrics (§2 Delivery Metrics)
    _define(
        "delivery_shipments",
        display="Shipments",
        category="DELIVERY",
        value_type="COUNT",
        unit="SHIPMENTS",
        description="Number of shipments counted in the period for this scope.",
    ),
    _define(
        "delivery_success_rate",
        display="Successful Delivery Rate",
        category="DELIVERY",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fraction of the period's counted shipments that reached a delivered state. "
            "Stored as a fraction, not a percentage."
        ),
    ),
    _define(
        "delivery_failure_rate",
        display="Delivery Failure Rate",
        category="DELIVERY",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fraction of the period's counted shipments that reached a failed state. "
            "Stored as a fraction, not a percentage."
        ),
    ),
    _define(
        "delivery_return_rate",
        display="Delivery Return Rate",
        category="DELIVERY",
        value_type="RATIO",
        unit="RATIO",
        description=(
            "Fraction of the period's counted shipments that were returned. Stored as a "
            "fraction, not a percentage."
        ),
    ),
    _define(
        "delivery_time",
        display="Delivery Time",
        category="DELIVERY",
        value_type="DURATION",
        unit="SECONDS",
        description=(
            "Average time in seconds between the shipment handover and delivery "
            "timestamps counted by the calculation rule."
        ),
    ),
    _define(
        "delivery_cost",
        display="Delivery Cost",
        category="DELIVERY",
        value_type="AMOUNT",
        unit="CURRENCY",
        description=(
            "Delivery charge counted for the period and scope, in a single currency "
            "scope."
        ),
    ),
)


# --------------------------------------------------------------------------
# Result structures
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class MetricRegistrySyncResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0


@dataclass(frozen=True)
class MetricObservation:
    """One reproducible metric observation a fact or issue can cite by id."""

    snapshot_id: int
    business_id: int
    metric_key: str
    value: Decimal
    value_type: str
    unit: str
    period_type: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    dimension_type: str | None
    dimension_value: str | None
    calculation_rule: str
    revision: int
    calculated_at: datetime.datetime


@dataclass(frozen=True)
class SnapshotWriteResult:
    """``observation`` is None only for a NOT_RECORDED_UNAVAILABLE result."""

    status: str
    observation: MetricObservation | None
    previous_value: Decimal | None
    existing_snapshot_id: int | None


@dataclass(frozen=True)
class MetricComparison:
    """§3 Historical Comparison: two observations of one metric and scope."""

    metric_key: str
    period_type: str
    dimension_type: str | None
    dimension_value: str | None
    current: MetricObservation | None
    previous: MetricObservation | None
    absolute_change: Decimal | None
    direction: str


# --------------------------------------------------------------------------
# Boundary validation
# --------------------------------------------------------------------------

def _require_positive_id(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MetricValidationError(f"{label} must be a positive integer.")
    return value


def _require_aware(value, label):
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            return value
        raise MetricValidationError(f"{label} must be timezone-aware.")
    raise MetricValidationError(f"{label} must be a timezone-aware datetime.")


def _require_period(period_type, period_start, period_end):
    """Validate a labelled, half-open [period_start, period_end) period."""
    if not isinstance(period_type, str) or period_type not in PERIOD_TYPES:
        raise MetricValidationError(
            f"period_type must be one of {sorted(PERIOD_TYPES)}."
        )
    if len(period_type) > _PERIOD_TYPE_MAX:
        raise MetricValidationError("period_type exceeds the stored column length.")
    start = _require_aware(period_start, "period_start")
    end = _require_aware(period_end, "period_end")
    if end <= start:
        raise MetricValidationError(
            "period_end must be strictly after period_start; periods are "
            "half-open [period_start, period_end)."
        )
    return period_type, start, end


def _require_dimension(dimension_type, dimension_value):
    """Validate the closed dimension vocabulary and the paired-or-absent rule."""
    if dimension_type is None and dimension_value is None:
        return None, None
    if dimension_type is None or dimension_value is None:
        raise MetricValidationError(
            "dimension_type and dimension_value must both be provided or both omitted."
        )
    if not isinstance(dimension_type, str) or dimension_type not in DIMENSION_TYPES:
        raise MetricValidationError(
            f"dimension_type must be one of {sorted(DIMENSION_TYPES)}."
        )
    if len(dimension_type) > _DIMENSION_TYPE_MAX:
        raise MetricValidationError("dimension_type exceeds the stored column length.")
    if not isinstance(dimension_value, str):
        raise MetricValidationError("dimension_value must be a string.")
    value = dimension_value.strip()
    if not value:
        raise MetricValidationError("dimension_value must not be empty.")
    if len(value) > _DIMENSION_VALUE_MAX:
        raise MetricValidationError(
            f"dimension_value exceeds {_DIMENSION_VALUE_MAX} characters."
        )
    if DIMENSION_TYPES[dimension_type] == "ENTITY":
        if not (value.isascii() and value.isdigit()) or value.startswith("0"):
            raise MetricValidationError(
                f"dimension_value for {dimension_type} must be a canonical positive "
                "entity id written without leading zeros."
            )
    return dimension_type, value


def _require_entity_dimension_scope(business_id, dimension_type, dimension_value):
    """Never trust a caller-supplied id: the row must live in this business."""
    if dimension_type is None or DIMENSION_TYPES[dimension_type] != "ENTITY":
        return
    model, scope_field = _ENTITY_DIMENSION_SCOPES[dimension_type]
    exists = model.objects.filter(
        pk=int(dimension_value), **{scope_field: business_id}
    ).exists()
    if not exists:
        raise MetricValidationError(
            f"{dimension_type} dimension {dimension_value} does not exist in this business."
        )


def _require_metric_key_shape(metric_key):
    if not isinstance(metric_key, str) or not metric_key:
        raise MetricValidationError("metric_key must be a non-empty string.")
    if len(metric_key) > _METRIC_KEY_MAX or not _METRIC_KEY_RE.match(metric_key):
        raise MetricValidationError(
            f"metric_key {metric_key!r} is not a versioned {_KEY_PREFIX}<name>.v<n> key."
        )
    return metric_key


def _require_calculation_rule(definition, calculation_rule):
    """The rule must name this metric, optionally with a documented variant."""
    if calculation_rule is None:
        return definition.key
    if not isinstance(calculation_rule, str) or not calculation_rule:
        raise MetricValidationError("calculation_rule must be a non-empty string.")
    if len(calculation_rule) > _CALCULATION_RULE_MAX:
        raise MetricValidationError(
            f"calculation_rule exceeds {_CALCULATION_RULE_MAX} characters."
        )
    if calculation_rule == definition.key:
        return calculation_rule
    prefix = f"{definition.key}."
    variant = calculation_rule[len(prefix):] if calculation_rule.startswith(prefix) else ""
    if not variant or not _RULE_VARIANT_RE.match(variant):
        raise MetricValidationError(
            f"calculation_rule must be {definition.key} or "
            f"{definition.key}.<lowercase_variant>."
        )
    return calculation_rule


def _normalize_inputs(inputs, seen=None):
    """Keep calculation inputs JSON-safe, float-free and deterministically ordered."""
    if inputs is None:
        return None
    seen = set() if seen is None else seen
    if isinstance(inputs, bool) or inputs is None or isinstance(inputs, (str, int)):
        return inputs
    if isinstance(inputs, Decimal):
        if not inputs.is_finite():
            raise MetricValidationError("inputs must not contain a non-finite Decimal.")
        return str(inputs)
    if isinstance(inputs, float):
        raise MetricValidationError(
            "inputs must not contain floating-point numbers; use Decimal or str."
        )
    if isinstance(inputs, dict):
        if id(inputs) in seen:
            raise MetricValidationError("inputs must not contain a cycle.")
        seen = seen | {id(inputs)}
        normalized = {}
        for key in sorted(inputs):
            if not isinstance(key, str) or not key:
                raise MetricValidationError("inputs keys must be non-empty strings.")
            normalized[key] = _normalize_inputs(inputs[key], seen)
        return normalized
    if isinstance(inputs, (list, tuple)):
        if id(inputs) in seen:
            raise MetricValidationError("inputs must not contain a cycle.")
        seen = seen | {id(inputs)}
        return [_normalize_inputs(item, seen) for item in inputs]
    raise MetricValidationError(
        f"inputs may not contain a value of type {type(inputs).__name__}."
    )


def _require_inputs(inputs):
    if inputs is None:
        return None
    if not isinstance(inputs, dict):
        raise MetricValidationError("inputs must be a mapping when provided.")
    normalized = _normalize_inputs(inputs)
    return normalized or None


def _quantize_value(value):
    """Return (stored_value, exact_caller_value_if_rounded); Decimal only."""
    if value is UNAVAILABLE:
        return None, None
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise MetricValidationError(
            "value must be a Decimal or the UNAVAILABLE sentinel; floats, integers "
            "and strings are rejected so no implicit conversion can change a number."
        )
    if not value.is_finite():
        raise MetricValidationError("value must be a finite Decimal.")
    with localcontext() as context:
        context.prec = _DECIMAL_PRECISION
        try:
            stored = value.quantize(_VALUE_QUANTUM, rounding=ROUND_HALF_EVEN)
        except InvalidOperation as exc:
            raise MetricValidationError(
                "value cannot be stored with "
                f"{_VALUE_DECIMAL_PLACES} decimal places."
            ) from exc
        if stored.copy_abs() >= _VALUE_ABS_LIMIT:
            raise MetricValidationError(
                "value exceeds the "
                f"{_VALUE_MAX_DIGITS - _VALUE_DECIMAL_PLACES} integer digits the "
                "snapshot column can store."
            )
    rounded_from = None if stored == value else str(value)
    return stored, rounded_from


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def _locked_business(business_id):
    try:
        return models.Business.objects.select_for_update().get(pk=business_id)
    except models.Business.DoesNotExist as exc:
        raise MetricValidationError("Business does not exist.") from exc


def _require_business(business_id):
    if not models.Business.objects.filter(pk=business_id).exists():
        raise MetricValidationError("Business does not exist.")


def _lookup_business_metric(business_id, metric_key):
    return models.BusinessMetric.objects.filter(
        business_id=business_id, key=metric_key
    ).first()


def _require_registered_metric(business_id, definition):
    row = _lookup_business_metric(business_id, definition.key)
    if row is None:
        raise MetricValidationError(
            f"Metric {definition.key} is not registered for this business; call "
            "sync_metric_registry first."
        )
    if not row.is_active:
        raise MetricValidationError(
            f"Metric {definition.key} is inactive for this business."
        )
    return row


def _owned(row):
    return isinstance(row.metadata, dict) and row.metadata.get("service") == _OWNER


def _revision(metadata):
    revision = metadata.get("revision") if isinstance(metadata, dict) else None
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        return 0
    return revision


def _observation(row, metric):
    if metric.business_id != row.business_id:
        raise MetricSnapshotConflictError(
            f"Snapshot {row.pk} references a metric owned by another business."
        )
    return MetricObservation(
        snapshot_id=row.pk,
        business_id=row.business_id,
        metric_key=metric.key,
        value=row.value,
        value_type=metric.value_type,
        unit=metric.unit,
        period_type=row.period_type,
        period_start=row.period_start,
        period_end=row.period_end,
        dimension_type=row.dimension_type,
        dimension_value=row.dimension_value,
        calculation_rule=row.calculation_rule,
        revision=_revision(row.metadata),
        calculated_at=row.calculated_at,
    )


def _identity_filter(business_id, metric_id, period_type, period_start, period_end,
                     dimension_type, dimension_value):
    """The logical identity of one observation; no DB constraint enforces it."""
    return dict(
        business_id=business_id,
        metric_id=metric_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
    )


def _single_identity_row(rows, identity):
    if not rows:
        return None
    if len(rows) > 1:
        raise MetricSnapshotConflictError(
            "Multiple snapshot rows share one logical observation identity "
            f"{identity}: ids {[row.pk for row in rows]}. The authoritative row "
            "cannot be chosen automatically."
        )
    row = rows[0]
    if not _owned(row):
        raise MetricSnapshotConflictError(
            f"Snapshot {row.pk} occupies this observation identity but was not "
            "written by this service."
        )
    return row


def _core_metadata(definition, calculation_rule, rounded_from, inputs):
    core = {
        "service": _OWNER,
        "metric_key": definition.key,
        "calculation_rule": calculation_rule,
        "value_type": definition.value_type,
        "unit": definition.unit,
        "data_available": True,
    }
    if rounded_from is not None:
        core["rounded_from"] = rounded_from
    if inputs is not None:
        core["inputs"] = inputs
    return core


def _existing_core(metadata):
    if not isinstance(metadata, dict):
        return {}
    return {
        key: value for key, value in metadata.items()
        if key not in _METADATA_HISTORY_KEYS
    }


# --------------------------------------------------------------------------
# Registry operations (§2)
# --------------------------------------------------------------------------

def get_metric_definition(*, metric_key):
    """Return the single documented definition for a registry key."""
    _require_metric_key_shape(metric_key)
    definition = METRIC_DEFINITIONS.get(metric_key)
    if definition is None:
        raise MetricValidationError(f"Metric {metric_key} is not in the metric registry.")
    return definition


def list_metric_definitions(*, category=None):
    """Return registry definitions, optionally filtered by documented category."""
    if category is not None:
        if not isinstance(category, str) or category not in CATEGORIES:
            raise MetricValidationError(f"category must be one of {sorted(CATEGORIES)}.")
    return tuple(
        definition for _, definition in sorted(METRIC_DEFINITIONS.items())
        if category is None or definition.category == category
    )


def sync_metric_registry(*, business_id):
    """Materialize the closed registry for one business; perform no authorization.

    Creates a BusinessMetric row per definition, repairs drifted name, category,
    value type, unit, description or active flag, reactivates a definition that
    returned, and deactivates service-owned rows whose definition was retired.
    Rows are never deleted because snapshots reference them. Metric rows whose
    key does not use the service prefix belong to someone else and are ignored.
    Repeat runs report ``unchanged`` and touch no timestamp.
    """
    _require_positive_id(business_id, "business_id")
    try:
        with transaction.atomic():
            _locked_business(business_id)
            existing = {
                row.key: row
                for row in models.BusinessMetric.objects.select_for_update()
                .filter(business_id=business_id).order_by("pk")
            }
            now = timezone.now()
            counts = dict(created=0, updated=0, unchanged=0, deactivated=0)
            for key, definition in sorted(METRIC_DEFINITIONS.items()):
                row = existing.get(key)
                if row is None:
                    models.BusinessMetric.objects.create(
                        business_id=business_id,
                        key=definition.key,
                        name=definition.name,
                        category=definition.category,
                        value_type=definition.value_type,
                        unit=definition.unit,
                        description=definition.description,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                    counts["created"] += 1
                    continue
                changed = [
                    field for field, value in (
                        ("name", definition.name),
                        ("category", definition.category),
                        ("value_type", definition.value_type),
                        ("unit", definition.unit),
                        ("description", definition.description),
                        ("is_active", True),
                    ) if getattr(row, field) != value
                ]
                if not changed:
                    counts["unchanged"] += 1
                    continue
                row.name = definition.name
                row.category = definition.category
                row.value_type = definition.value_type
                row.unit = definition.unit
                row.description = definition.description
                row.is_active = True
                row.updated_at = now
                row.save(update_fields=changed + ["updated_at"])
                counts["updated"] += 1
            for key, row in sorted(existing.items()):
                if (key not in METRIC_DEFINITIONS and key.startswith(_KEY_PREFIX)
                        and row.is_active):
                    row.is_active = False
                    row.updated_at = now
                    row.save(update_fields=["is_active", "updated_at"])
                    counts["deactivated"] += 1
            return MetricRegistrySyncResult(**counts)
    except IntegrityError as exc:
        raise MetricSnapshotConflictError(
            "Metric registry synchronization hit a database constraint conflict; "
            "another writer raced the (business, key) unique constraint."
        ) from exc


# --------------------------------------------------------------------------
# Snapshot write contract (§3)
# --------------------------------------------------------------------------

def record_metric_snapshot(*, business_id, metric_key, value, period_type,
                           period_start, period_end, dimension_type=None,
                           dimension_value=None, calculation_rule=None, inputs=None):
    """Record one reproducible observation for a scope and period; no authorization.

    ``value`` is a Decimal or the ``UNAVAILABLE`` sentinel. Absent data writes
    nothing and returns ``NOT_RECORDED_UNAVAILABLE``: zero is never substituted
    for missing data, and any earlier observation for the same identity is left
    untouched and reported as ``existing_snapshot_id``.

    A repeat run for the same logical identity (business, metric, dimension,
    period type, half-open period) never appends a second row. An identical
    recalculation returns ``UNCHANGED`` and preserves the row id and every
    timestamp. A recalculation with a different value, rule or inputs UPDATES
    the row in place rather than being rejected, because late canonical data
    legitimately revises a closed period; the superseded value, rule and
    calculation time move into ``metadata["supersedes"]`` and
    ``metadata["revision"]`` increments so the revision stays traceable.
    """
    _require_positive_id(business_id, "business_id")
    _require_metric_key_shape(metric_key)
    definition = get_metric_definition(metric_key=metric_key)
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    dimension_type, dimension_value = _require_dimension(dimension_type, dimension_value)
    calculation_rule = _require_calculation_rule(definition, calculation_rule)
    normalized_inputs = _require_inputs(inputs)
    stored_value, rounded_from = _quantize_value(value)

    try:
        with transaction.atomic():
            _locked_business(business_id)
            _require_entity_dimension_scope(business_id, dimension_type, dimension_value)
            metric = _require_registered_metric(business_id, definition)
            identity = _identity_filter(
                business_id, metric.pk, period_type, period_start, period_end,
                dimension_type, dimension_value,
            )
            rows = list(
                models.MetricSnapshot.objects.select_for_update()
                .filter(**identity).order_by("pk")
            )
            row = _single_identity_row(rows, identity)

            if stored_value is None:
                return SnapshotWriteResult(
                    status=WRITE_NOT_RECORDED_UNAVAILABLE,
                    observation=None,
                    previous_value=None if row is None else row.value,
                    existing_snapshot_id=None if row is None else row.pk,
                )

            core = _core_metadata(definition, calculation_rule, rounded_from, normalized_inputs)
            now = timezone.now()
            if row is None:
                metadata = dict(core, revision=1)
                row = models.MetricSnapshot.objects.create(
                    metric_id=metric.pk,
                    business_id=business_id,
                    value=stored_value,
                    dimension_type=dimension_type,
                    dimension_value=dimension_value,
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    calculation_rule=calculation_rule,
                    metadata=metadata,
                    calculated_at=now,
                    created_at=now,
                )
                return SnapshotWriteResult(
                    status=WRITE_CREATED,
                    observation=_observation(row, metric),
                    previous_value=None,
                    existing_snapshot_id=None,
                )

            if row.value == stored_value and _existing_core(row.metadata) == core:
                return SnapshotWriteResult(
                    status=WRITE_UNCHANGED,
                    observation=_observation(row, metric),
                    previous_value=None,
                    existing_snapshot_id=row.pk,
                )

            previous_revision = _revision(row.metadata)
            previous_value = row.value
            metadata = dict(
                core,
                revision=previous_revision + 1,
                supersedes={
                    "revision": previous_revision or None,
                    "value": str(previous_value),
                    "calculation_rule": row.calculation_rule,
                    "calculated_at": (
                        row.calculated_at.isoformat() if row.calculated_at else None
                    ),
                },
            )
            row.value = stored_value
            row.calculation_rule = calculation_rule
            row.metadata = metadata
            row.calculated_at = now
            row.save(update_fields=["value", "calculation_rule", "metadata", "calculated_at"])
            return SnapshotWriteResult(
                status=WRITE_UPDATED,
                observation=_observation(row, metric),
                previous_value=previous_value,
                existing_snapshot_id=row.pk,
            )
    except IntegrityError as exc:
        raise MetricSnapshotConflictError(
            "Snapshot reconciliation hit a database constraint conflict."
        ) from exc


# --------------------------------------------------------------------------
# Snapshot read contract (§3)
# --------------------------------------------------------------------------

def get_metric_snapshot(*, business_id, metric_key, period_type, period_start,
                        period_end, dimension_type=None, dimension_value=None):
    """Return the one observation for a scope and period, or None if none exists.

    None means "no observation was recorded" and is never a zero stand-in. If
    the identity is occupied by a row this service does not own, or by more than
    one row, the read raises MetricSnapshotConflictError rather than returning a
    row whose traceability contract is unknown.
    """
    _require_positive_id(business_id, "business_id")
    _require_metric_key_shape(metric_key)
    period_type, period_start, period_end = _require_period(
        period_type, period_start, period_end
    )
    dimension_type, dimension_value = _require_dimension(dimension_type, dimension_value)
    with transaction.atomic():
        _require_business(business_id)
        _require_entity_dimension_scope(business_id, dimension_type, dimension_value)
        metric = _lookup_business_metric(business_id, metric_key)
        if metric is None:
            raise MetricValidationError(
                f"metric {metric_key} is not registered for this business; "
                "run sync_metric_registry before reading its observations."
            )
        identity = _identity_filter(
            business_id, metric.pk, period_type, period_start, period_end,
            dimension_type, dimension_value,
        )
        rows = list(models.MetricSnapshot.objects.filter(**identity).order_by("pk"))
        row = _single_identity_row(rows, identity)
        return None if row is None else _observation(row, metric)


def get_metric_observation(*, business_id, snapshot_id):
    """§3 Reproducible Analysis: resolve the exact observation a finding cites.

    Returns None when the snapshot does not exist in this business, so a
    caller-supplied id can never read another business's observation.
    """
    _require_positive_id(business_id, "business_id")
    _require_positive_id(snapshot_id, "snapshot_id")
    with transaction.atomic():
        _require_business(business_id)
        row = models.MetricSnapshot.objects.select_related("metric").filter(
            pk=snapshot_id, business_id=business_id
        ).first()
        if row is None:
            return None
        if not _owned(row):
            raise MetricSnapshotConflictError(
                f"Snapshot {snapshot_id} was not written by this service, so its "
                "traceability contract is unknown."
            )
        return _observation(row, row.metric)


def list_metric_snapshots(*, business_id, metric_key=None, period_type=None,
                          dimension_type=None, dimension_value=None,
                          window_start=None, window_end=None, calculation_rule=None,
                          include_inactive_metrics=False, limit=None,
                          any_dimension=False):
    """§3 Trend Foundation: the ordered observation history for one scope.

    With no dimension given this returns the BUSINESS-WIDE series only, matching
    the write identity, so a trend is never built over mixed scopes. Pass
    ``any_dimension=True`` to deliberately read every scope at once; it cannot
    be combined with an explicit dimension.

    Only observations written by this service are returned. ``window_start`` and
    ``window_end`` filter on ``period_start`` as a half-open window
    ``[window_start, window_end)``. ``calculation_rule`` filters by the exact
    recorded rule, and inactive metrics are excluded unless requested. An empty
    result means no observation exists; it is never a zero-valued row. Ordering
    is deterministic: period_start, period_end, then snapshot id.
    """
    _require_positive_id(business_id, "business_id")
    if metric_key is not None:
        _require_metric_key_shape(metric_key)
    if period_type is not None and period_type not in PERIOD_TYPES:
        raise MetricValidationError(f"period_type must be one of {sorted(PERIOD_TYPES)}.")
    dimension_type, dimension_value = _require_dimension(dimension_type, dimension_value)
    if window_start is not None:
        window_start = _require_aware(window_start, "window_start")
    if window_end is not None:
        window_end = _require_aware(window_end, "window_end")
    if window_start is not None and window_end is not None and window_end <= window_start:
        raise MetricValidationError(
            "window_end must be strictly after window_start; the window is "
            "half-open [window_start, window_end)."
        )
    if calculation_rule is not None:
        if not isinstance(calculation_rule, str) or not calculation_rule:
            raise MetricValidationError("calculation_rule must be a non-empty string.")
        if len(calculation_rule) > _CALCULATION_RULE_MAX:
            raise MetricValidationError(
                f"calculation_rule exceeds {_CALCULATION_RULE_MAX} characters."
            )
    if not isinstance(include_inactive_metrics, bool):
        raise MetricValidationError("include_inactive_metrics must be a boolean.")
    if not isinstance(any_dimension, bool):
        raise MetricValidationError("any_dimension must be a boolean.")
    if any_dimension and dimension_type is not None:
        raise MetricValidationError(
            "any_dimension cannot be combined with an explicit dimension."
        )
    if limit is not None:
        _require_positive_id(limit, "limit")

    with transaction.atomic():
        _require_business(business_id)
        _require_entity_dimension_scope(business_id, dimension_type, dimension_value)
        query = models.MetricSnapshot.objects.select_related("metric").filter(
            business_id=business_id, metric__business_id=business_id
        )
        if metric_key is not None:
            if _lookup_business_metric(business_id, metric_key) is None:
                raise MetricValidationError(
                    f"metric {metric_key} is not registered for this business; "
                    "run sync_metric_registry before reading its observations."
                )
            query = query.filter(metric__key=metric_key)
        if not include_inactive_metrics:
            query = query.filter(metric__is_active=True)
        if period_type is not None:
            query = query.filter(period_type=period_type)
        if dimension_type is not None:
            query = query.filter(
                dimension_type=dimension_type, dimension_value=dimension_value
            )
        elif not any_dimension:
            query = query.filter(dimension_type__isnull=True, dimension_value__isnull=True)
        if window_start is not None:
            query = query.filter(period_start__gte=window_start)
        if window_end is not None:
            query = query.filter(period_start__lt=window_end)
        if calculation_rule is not None:
            query = query.filter(calculation_rule=calculation_rule)
        query = query.order_by("period_start", "period_end", "id")
        owned = [row for row in query if _owned(row)]
        if limit is not None:
            owned = owned[:limit]
        return tuple(_observation(row, row.metric) for row in owned)


def compare_metric_periods(*, business_id, metric_key, period_type,
                           current_period_start, current_period_end,
                           previous_period_start, previous_period_end,
                           dimension_type=None, dimension_value=None):
    """§3 Historical Comparison: compare two recorded periods of one scope.

    Both periods are half-open and must use the same period type and dimension;
    the previous period must end at or before the current period starts, so the
    compared windows never overlap. If either observation is missing the
    direction is ``UNAVAILABLE`` and ``absolute_change`` is None — a missing
    observation is never treated as zero. No relative or growth figure is
    returned: a growth rate is a registered metric (see the sales and revenue
    growth definitions) whose arithmetic belongs to the calculation tickets, and
    computing one here would give the same business concept two answers.
    Direction reports movement only: whether an increase is an improvement
    depends on the metric's polarity, which the analysis tickets own.
    """
    _require_positive_id(business_id, "business_id")
    _require_metric_key_shape(metric_key)
    period_type, current_start, current_end = _require_period(
        period_type, current_period_start, current_period_end
    )
    _, previous_start, previous_end = _require_period(
        period_type, previous_period_start, previous_period_end
    )
    if previous_end > current_start:
        raise MetricValidationError(
            "previous_period_end must be at or before current_period_start."
        )
    dimension_type, dimension_value = _require_dimension(dimension_type, dimension_value)

    with transaction.atomic():
        current = get_metric_snapshot(
            business_id=business_id, metric_key=metric_key, period_type=period_type,
            period_start=current_start, period_end=current_end,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )
        previous = get_metric_snapshot(
            business_id=business_id, metric_key=metric_key, period_type=period_type,
            period_start=previous_start, period_end=previous_end,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )

    if current is None or previous is None:
        return MetricComparison(
            metric_key=metric_key, period_type=period_type,
            dimension_type=dimension_type, dimension_value=dimension_value,
            current=current, previous=previous,
            absolute_change=None,
            direction=DIRECTION_UNAVAILABLE,
        )

    with localcontext() as context:
        context.prec = _DECIMAL_PRECISION
        absolute_change = current.value - previous.value
    if absolute_change > 0:
        direction = DIRECTION_INCREASED
    elif absolute_change < 0:
        direction = DIRECTION_DECREASED
    else:
        direction = DIRECTION_UNCHANGED
    return MetricComparison(
        metric_key=metric_key, period_type=period_type,
        dimension_type=dimension_type, dimension_value=dimension_value,
        current=current, previous=previous,
        absolute_change=absolute_change,
        direction=direction,
    )
