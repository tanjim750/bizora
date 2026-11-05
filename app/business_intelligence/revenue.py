"""BI specification §6 (Revenue Analysis) and the §2 Sales/Revenue metric families.

This module calculates the sales and revenue observations for one business and
records them through the §3 snapshot contract in ``metrics.py``. It is an
INTERNAL service: it adds no endpoint, view, serializer, URL, authentication or
authorization, and the caller must authorize business access before invoking
anything here. Every query is scoped to the business being processed.

Public API (all keyword-only). Read-only calculations:

* ``compute_order_revenue(...)`` — §6 Total Revenue Analysis on the order basis:
  counted/eligible/cancelled/reversed orders, gross amount, units and distinct
  resolved customers for one currency scope and one period.
* ``compute_payment_receipts(...)`` — the payment basis: money whose payment
  status says it was actually received in the period.
* ``compute_refund_impact(...)`` — §6 Refund Impact Analysis: completed refunds
  of the period, including refunds whose order link is null.
* ``reconcile_revenue(...)`` — the AC's payment/refund reconciliation: order
  basis against payment basis against refunds, with the unreconciled difference
  and the full coverage report.
* ``summarize_revenue_breakdown(...)`` — §6 Product / Campaign / Customer /
  Channel Revenue Analysis as an ordered per-dimension-value breakdown.
* ``detect_revenue_change(...)`` — §6 Revenue Change Detection against the
  previous comparison period or a baseline mean of recorded observations.

Recording operations (one ``transaction.atomic()`` block each, replay-safe
because ``metrics.record_metric_snapshot`` is):

* ``record_sales_metrics(...)`` — §2 Sales Metrics: total orders, units sold,
  average order value, cancellation rate.
* ``record_revenue_metrics(...)`` — §2 Revenue Metrics: gross revenue, refunded
  revenue, net revenue, revenue per customer.
* ``record_revenue_breakdown(...)`` — records the breakdown above for every
  dimension value it found (§6 product/campaign/channel/segment bullets).
* ``record_sales_growth_rate(...)`` / ``record_revenue_growth_rate(...)`` —
  §6 Revenue Trend Analysis and the §2 growth-rate metrics, computed only from
  observations this service already recorded for both periods.

What this module does NOT do. It defines no new metric key and never edits the
registry: every key it writes is one of the ten Sales/Revenue keys already in
``metrics.METRIC_DEFINITIONS``. It does not resolve identity (``Order.customer``
is consumed as the already-resolved canonical customer), does not perform
deterministic attribution, does not create relationships, does not detect
anomalies, facts or issues, and does not generate recommendations. It changes no
canonical row, no schema and no shared configuration.

--------------------------------------------------------------------------
Status eligibility (the §2/T-002 amendment: the ticket that implements a
calculation declares that metric's eligibility filter)
--------------------------------------------------------------------------

The order lifecycle is documented in
``docs/implementations/features/business-data.md`` line 110 and the payment
states in the same file line 145. Both lists are introduced with "such as", and
both model columns are free-text ``CharField``s with no ``choices``, so the
vocabulary is documented but NOT guaranteed exhaustive. Therefore:

* Comparison is EXACT against the documented spelling. No case folding, no
  whitespace trimming and no aliasing is invented here — normalizing provider
  spellings is the Business Data domain's job (business-data.md "Order
  Normalization" / "Payment Normalization").
* A status this module does not recognise is NEVER silently ignored. It is
  counted in ``coverage`` under ``unclassified_order_statuses`` /
  ``unclassified_payment_statuses`` (plus its row count and amount) and that
  coverage is written into every snapshot's ``inputs`` metadata, so a reader can
  always tell whether a number covered all the data in scope.
* A snapshot's ``calculation_rule`` carries a distinct variant whenever the
  eligible set or the scope derivation differs, so two tickets can never record
  one metric key with two meanings. ``CALCULATION_RULES`` is the closed,
  versioned table of those variants.

Gross revenue on the order basis counts ``CONFIRMED``, ``PROCESSING``,
``SHIPPED``, ``DELIVERED`` (the sale was accepted) and also ``RETURNED`` and
``REFUNDED`` (the sale was accepted and later reversed). The reversal is
subtracted exactly once, from ``Refund`` rows, because §6 "Refund Impact
Analysis — accounts for refunds when evaluating realized business revenue" makes
the refund the evidence of the realized reduction. Excluding reversed orders
from gross *and* subtracting their refunds would subtract the same reversal
twice; the amount sitting in reversal states is reported separately as
``reversed_order_amount`` so an un-refunded return is visible rather than
hidden. ``PENDING`` is not yet an accepted sale and ``CANCELLED`` is not a sale
at all; §2 Sales Metrics names an order cancellation rate, which is what makes
``CANCELLED`` its own classification with its own counter.

Payments: money has arrived only for ``PAID``, ``PARTIALLY_REFUNDED`` and
``REFUNDED`` — the last two were captured first and their reduction again comes
from ``Refund`` rows. ``PENDING``, ``AUTHORIZED``, ``FAILED`` and ``CANCELLED``
are payment rows where no money arrived: a payment row existing is not receipt,
only its status is.

Refunds: business-data.md documents refund amount, reason, status and
"completion information" (line 153-154) but documents NO refund status
vocabulary anywhere. Declaring one would be inventing policy, so this module
filters refunds on their canonical completion timestamp (``refunded_at`` inside
the period) and does not filter on ``Refund.status`` at all. Every distinct
refund status in scope is counted in ``coverage["refund_statuses"]`` so nothing
is invisible, and the open contract is listed in the handoff for the team.

--------------------------------------------------------------------------
Periods, currency, money and zero denominators
--------------------------------------------------------------------------

Periods are half-open ``[period_start, period_end)`` and both bounds must be
timezone-aware. ``period_type`` stays a label: the reporting timezone that would
define an aligned business day is an open team question, so no calendar
alignment is enforced here (the same decision as ``metrics.py``).

An order belongs to the period containing ``Order.ordered_at``. The model has no
``placed_at``; it has ``ordered_at`` (the business event time, nullable) and
``created_at`` (the ingestion time, non-null). ``created_at`` is deliberately
NOT used, not even as a fallback: a re-import would move historical orders into
a different period and silently rewrite a closed period's revenue. Orders with
``ordered_at IS NULL`` therefore belong to no period; they are excluded and
reported as ``orders_without_period_timestamp``. The payment basis uses
``Payment.paid_at`` (receipt time) and refunds use ``Refund.refunded_at``, with
the same explicit missing-timestamp counters.

Currency isolation. ``Order``, ``Payment`` and ``Refund`` each carry their own
``currency`` column, and amounts are NEVER summed across currencies. One amount
observation covers exactly one currency, resolved in this order: the caller's
``currency`` argument; else the ``CURRENCY`` dimension value; else the single
currency observed in scope; else, when the scope contains no money row at all,
the business's own recorded currency. If a scope contains more than one currency
and the caller named none, the operation raises ``RevenueCurrencyMixError``
rather than guessing or summing. Rows in another currency are excluded and
counted (``*_in_other_currency``), and rows with a blank currency are counted as
``*_without_currency``. ``summarize_revenue_breakdown(breakdown="CURRENCY")`` is
the sanctioned way to look at a multi-currency business: each row is one
currency and rows are never added together.

All money arithmetic is ``Decimal``; floats never appear. Sums are computed in
Python rather than with database ``SUM`` aggregation so the result is exact and
identical on both configured backends (SQLite computes NUMERIC aggregates in
floating point). The order money columns hold 2 decimal places while
``MetricSnapshot.value`` holds 6, so every sum of stored amounts is exact at 6
places and only the divisions (average order value, revenue per customer,
cancellation rate, growth rates) need rounding: they are computed at high
Decimal precision and quantized to 6 places with banker's rounding
(``ROUND_HALF_EVEN``) by ``metrics.record_metric_snapshot``, which preserves the
unrounded value in ``metadata["rounded_from"]``. No value is truncated.

Zero denominators never produce 0 and never raise: average order value with no
eligible order, revenue per customer with no resolved customer, cancellation
rate with no counted order and a growth rate whose earlier period is missing or
zero all record the ``metrics.UNAVAILABLE`` sentinel, so "no data" stays the
absence of a snapshot row. Amount sums are different: over a complete, correctly
scoped population an empty eligible set is a measured zero (a period with no
revenue is a real business fact that §6 Revenue Change Detection must be able to
see), so gross, refunded and net revenue record 0 when the currency scope is
determined. A negative net revenue is likewise a measured fact: refunds
completed in a period may exceed that period's gross revenue.

--------------------------------------------------------------------------
Scopes, and what is deliberately left to a later ticket
--------------------------------------------------------------------------

Order-total based figures support the business-wide scope and the ``CURRENCY``,
``CHANNEL``, ``CUSTOMER_SEGMENT`` and ``CAMPAIGN`` dimensions. ``CHANNEL`` is
the canonical integration source key of the order's connection (§6 "commerce,
acquisition, or marketing channels"); an order without an integration connection
has no canonical channel and is counted as ``orders_without_channel`` rather
than being assigned a guessed one. ``CUSTOMER_SEGMENT`` is a canonical
``CustomerTag`` label (business-data.md line 70: ``VIP``, ``REPEAT_BUYER``,
``HIGH_VALUE``, ``DELIVERY_RISK``, ``NEW_CUSTOMER``, "such as"); a customer may
carry several tags, so segment observations are NOT additive.

``CAMPAIGN`` scope uses only the links T-001 already produced: valid
``CAMPAIGN -REPORTED_ORDER-> ORDER`` relationships created by
``relationships.RULES["campaign_order"]``. Those links are PLATFORM-REPORTED,
not proven attribution, which is why the campaign variants carry
``reported_campaign`` in their name and why campaign revenue is recorded under
``revenue_gross``/``revenue_net`` and never under
``bi.metric.marketing_attributed_revenue.v1``. One order may be reported by
several campaigns, so per-campaign observations are not additive either and
``orders_reported_by_multiple_campaigns`` is reported. Deterministic,
evidence-weighted campaign attribution — and therefore any single-owner split of
one order's revenue across campaigns — is T-006 and is not pre-empted here.

``PRODUCT``/``PRODUCT_VARIANT`` revenue is item-based: it sums
``OrderItem.total_amount`` of eligible orders, because the order total also
contains shipping, tax and order-level discount, and splitting those across
items would be an allocation policy the documentation does not define. For the
same reason ``revenue_net`` and ``revenue_refunded`` are NOT recorded per
product: ``Refund`` is linked to a payment and an order, never to an order item,
so an item-level refund figure does not exist in this schema.

The ``significance`` of a revenue change is never a literal in this module: it
is the caller's ``significant_change_ratio`` / ``significant_absolute_change``.
When neither is supplied the result reports ``is_significant=None`` with
criteria ``NOT_SUPPLIED`` — choosing a default threshold belongs to the
configurable anomaly rules of T-010, and turning a change into a statement
belongs to the facts and issues of T-011.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from types import MappingProxyType
import datetime
import re

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from app import models

from . import metrics
from . import relationships


class RevenueValidationError(ValueError):
    """A boundary input, period, dimension, currency or threshold is invalid."""


class RevenueCurrencyMixError(RevenueValidationError):
    """The scope mixes currencies and the caller named none; refuse to guess."""


class RevenueScopeError(RevenueValidationError):
    """The requested figure cannot be expressed for the requested scope."""


class RevenueDefinitionError(ValueError):
    """This module's own closed rule table is internally inconsistent."""


# --------------------------------------------------------------------------
# Schema-derived limits: never duplicate a column limit as a literal.
# --------------------------------------------------------------------------

def _max_length(model, name):
    return model._meta.get_field(name).max_length


def _decimal_places(model, name):
    return model._meta.get_field(name).decimal_places


_CURRENCY_MAX = _max_length(models.Order, "currency")
_CALCULATION_RULE_MAX = _max_length(models.MetricSnapshot, "calculation_rule")
_SNAPSHOT_MAX_DIGITS = models.MetricSnapshot._meta.get_field("value").max_digits
_SNAPSHOT_DECIMAL_PLACES = _decimal_places(models.MetricSnapshot, "value")
_ORDER_DECIMAL_PLACES = _decimal_places(models.Order, "total_amount")
# Wide enough that no intermediate division loses a digit the snapshot keeps.
_PRECISION = 2 * _SNAPSHOT_MAX_DIGITS + _SNAPSHOT_DECIMAL_PLACES
if _ORDER_DECIMAL_PLACES > _SNAPSHOT_DECIMAL_PLACES:
    # Sums of stored order amounts must be exact at the snapshot's scale.
    raise RevenueDefinitionError(
        "The order money columns carry more decimal places than a metric "
        "snapshot can store exactly."
    )


# --------------------------------------------------------------------------
# Documented status vocabulary and the eligibility sets this ticket declares
# --------------------------------------------------------------------------

# Order lifecycle — docs/implementations/features/business-data.md line 110.
# Internal sub-classifications; the four PUBLIC sets below are the eligibility
# filters that define what a recorded metric actually measured.
# The sale was accepted and has not been reversed: these are the orders whose
# totals constitute revenue (§6 Total Revenue Analysis).
_ORDER_STATUSES_ACCEPTED = frozenset({
    "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED",
})
# The sale was accepted and later reversed. Still part of gross revenue; the
# realized reduction comes from Refund rows exactly once (§6 Refund Impact).
_ORDER_STATUSES_REVERSED = frozenset({"RETURNED", "REFUNDED"})
# Not yet an accepted sale, so not revenue.
_ORDER_STATUSES_PENDING = frozenset({"PENDING"})

# Never a sale; its own classification because §2 Sales Metrics names a
# cancellation rate, whose numerator this set is.
ORDER_STATUSES_CANCELLED = frozenset({"CANCELLED"})
# Eligible for an amount in gross revenue, average order value, units sold,
# net revenue and revenue per customer (§2 Revenue Metrics, §6 Total Revenue).
REVENUE_ELIGIBLE_ORDER_STATUSES = _ORDER_STATUSES_ACCEPTED | _ORDER_STATUSES_REVERSED
# The denominator of total orders and of the cancellation rate: every order of
# the period whose status is part of the documented lifecycle (§2 Sales Metrics).
COUNTED_ORDER_STATUSES = (
    REVENUE_ELIGIBLE_ORDER_STATUSES | _ORDER_STATUSES_PENDING | ORDER_STATUSES_CANCELLED
)

# Payment states — docs/implementations/features/business-data.md line 145.
# Money actually arrived. PARTIALLY_REFUNDED/REFUNDED were captured first and
# their reduction is taken from Refund rows, not by dropping the receipt.
PAYMENT_STATUSES_RECEIVED = frozenset({"PAID", "PARTIALLY_REFUNDED", "REFUNDED"})
# A payment row exists but no money arrived.
_PAYMENT_STATUSES_NOT_RECEIVED = frozenset({
    "PENDING", "AUTHORIZED", "FAILED", "CANCELLED",
})

# business-data.md documents refund amount/reason/status/completion information
# (lines 153-154) but no refund status vocabulary. A refund is therefore counted
# by its canonical completion timestamp and its status is reported, not filtered;
# every snapshot's inputs record the field used and the statuses encountered.
_REFUND_COMPLETION_TIMESTAMP_FIELD = "refunded_at"

# The business event time that places an order in a period; see the docstring.
_ORDER_PERIOD_TIMESTAMP_FIELD = "ordered_at"
_PAYMENT_PERIOD_TIMESTAMP_FIELD = "paid_at"

# A blank enum-like string must still be visible in the coverage report, and a
# JSON metadata key may not be empty.
_BLANK_LABEL = "(blank)"


# --------------------------------------------------------------------------
# Metric keys: reused from the §2 registry, never invented here
# --------------------------------------------------------------------------

_METRIC_TOTAL_ORDERS = "bi.metric.sales_total_orders.v1"
_METRIC_UNITS_SOLD = "bi.metric.sales_units_sold.v1"
_METRIC_AVERAGE_ORDER_VALUE = "bi.metric.sales_average_order_value.v1"
_METRIC_CANCELLATION_RATE = "bi.metric.sales_cancellation_rate.v1"
_METRIC_SALES_GROWTH_RATE = "bi.metric.sales_growth_rate.v1"
_METRIC_REVENUE_GROSS = "bi.metric.revenue_gross.v1"
METRIC_REVENUE_REFUNDED = "bi.metric.revenue_refunded.v1"
METRIC_REVENUE_NET = "bi.metric.revenue_net.v1"
METRIC_REVENUE_PER_CUSTOMER = "bi.metric.revenue_per_customer.v1"
METRIC_REVENUE_GROWTH_RATE = "bi.metric.revenue_growth_rate.v1"

SALES_METRIC_KEYS = (
    _METRIC_TOTAL_ORDERS, _METRIC_UNITS_SOLD, _METRIC_AVERAGE_ORDER_VALUE,
    _METRIC_CANCELLATION_RATE, _METRIC_SALES_GROWTH_RATE,
)
REVENUE_METRIC_KEYS = (
    _METRIC_REVENUE_GROSS, METRIC_REVENUE_REFUNDED, METRIC_REVENUE_NET,
    METRIC_REVENUE_PER_CUSTOMER, METRIC_REVENUE_GROWTH_RATE,
)

# Fail at import time if the registry ever stops defining a key used here,
# instead of failing later inside a transaction.
for _key in SALES_METRIC_KEYS + REVENUE_METRIC_KEYS:
    metrics.get_metric_definition(metric_key=_key)
del _key


# --------------------------------------------------------------------------
# Closed, versioned calculation-rule table
# --------------------------------------------------------------------------

BASIS_ORDERS_ACCEPTED = "ORDERS_ACCEPTED"
BASIS_REPORTED_CAMPAIGN_ORDERS = "REPORTED_CAMPAIGN_ORDERS"
BASIS_ORDER_ITEMS_ACCEPTED = "ORDER_ITEMS_ACCEPTED"
BASIS_PAYMENTS_RECEIVED = "PAYMENTS_RECEIVED"
BASES = frozenset({
    BASIS_ORDERS_ACCEPTED, BASIS_REPORTED_CAMPAIGN_ORDERS,
    BASIS_ORDER_ITEMS_ACCEPTED, BASIS_PAYMENTS_RECEIVED,
})


@dataclass(frozen=True)
class CalculationRule:
    """One (metric key, basis) pair and the exact rule string it records."""

    metric_key: str
    basis: str
    variant: str
    eligibility: str
    records: bool = True

    @property
    def rule(self):
        return f"{self.metric_key}.{self.variant}"


_VARIANT_RE = re.compile(r"^[a-z0-9_]+$")


def _rule(metric_key, basis, variant, eligibility, *, records=True):
    if basis not in BASES:
        raise RevenueDefinitionError(f"Unknown calculation basis {basis!r}.")
    if not _VARIANT_RE.match(variant):
        # The rule grammar belongs to metrics.py; fail at import, not at write.
        raise RevenueDefinitionError(
            f"Rule variant {variant!r} must be a lowercase identifier."
        )
    definition = CalculationRule(
        metric_key=metric_key, basis=basis, variant=variant,
        eligibility=eligibility, records=records,
    )
    if not eligibility:
        raise RevenueDefinitionError(f"{definition.rule} must document its filter.")
    if len(definition.rule) > _CALCULATION_RULE_MAX:
        raise RevenueDefinitionError(
            f"calculation_rule {definition.rule} exceeds "
            f"{_CALCULATION_RULE_MAX} characters."
        )
    # metrics.py owns the rule grammar; validate against it here so a bad
    # variant cannot reach a write.
    metrics_definition = metrics.get_metric_definition(metric_key=metric_key)
    if metrics_definition.key != metric_key:
        raise RevenueDefinitionError(f"Registry key mismatch for {metric_key}.")
    return definition


def _rule_table(*definitions):
    table = {}
    for definition in definitions:
        identity = (definition.metric_key, definition.basis)
        if identity in table:
            raise RevenueDefinitionError(f"Duplicate rule for {identity}.")
        table[identity] = definition
    variants = {}
    for definition in table.values():
        rule = definition.rule
        if rule in variants:
            raise RevenueDefinitionError(
                f"Rule string {rule} is used by two different bases."
            )
        variants[rule] = definition
    return table


# A distinct variant per differing eligible set or scope derivation, so two
# tickets cannot record one metric key with two meanings.
CALCULATION_RULES = _rule_table(
    _rule(
        _METRIC_TOTAL_ORDERS, BASIS_ORDERS_ACCEPTED, "orders_placed_all_statuses",
        "Orders whose ordered_at is in the period and whose status is part of the "
        "documented lifecycle (business-data.md:110), in one currency scope.",
    ),
    _rule(
        _METRIC_TOTAL_ORDERS, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders_all_statuses",
        "Same counted set, restricted to orders a platform reported for this "
        "campaign through the valid REPORTED_ORDER relationships of T-001.",
    ),
    _rule(
        _METRIC_UNITS_SOLD, BASIS_ORDERS_ACCEPTED, "orders_accepted_items",
        "OrderItem quantities of the period's revenue-eligible orders "
        "(accepted or reversed status), in one currency scope.",
    ),
    _rule(
        _METRIC_UNITS_SOLD, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders_items",
        "Same item quantities, restricted to platform-reported campaign orders.",
    ),
    _rule(
        _METRIC_UNITS_SOLD, BASIS_ORDER_ITEMS_ACCEPTED, "order_items_accepted",
        "Quantities of the order items that reference this product dimension "
        "value inside the period's revenue-eligible orders.",
    ),
    _rule(
        _METRIC_AVERAGE_ORDER_VALUE, BASIS_ORDERS_ACCEPTED, "orders_accepted",
        "Total amount of the period's revenue-eligible orders divided by their "
        "count; UNAVAILABLE when that count is zero.",
    ),
    _rule(
        _METRIC_AVERAGE_ORDER_VALUE, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders",
        "Same average restricted to platform-reported campaign orders; "
        "UNAVAILABLE when the count is zero.",
    ),
    _rule(
        _METRIC_CANCELLATION_RATE, BASIS_ORDERS_ACCEPTED, "orders_placed_all_statuses",
        "CANCELLED orders divided by the period's counted orders, as a fraction; "
        "UNAVAILABLE when no order was counted.",
    ),
    _rule(
        _METRIC_CANCELLATION_RATE, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders_all_statuses",
        "Same fraction restricted to platform-reported campaign orders; "
        "UNAVAILABLE when no order was counted.",
    ),
    _rule(
        _METRIC_REVENUE_GROSS, BASIS_ORDERS_ACCEPTED, "orders_accepted",
        "Sum of Order.total_amount for the period's revenue-eligible orders "
        "(accepted or reversed), before refunds, in one currency scope.",
    ),
    _rule(
        _METRIC_REVENUE_GROSS, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders",
        "Same sum restricted to orders a platform reported for this campaign; "
        "platform-reported, not deterministic attribution (T-006).",
    ),
    _rule(
        _METRIC_REVENUE_GROSS, BASIS_ORDER_ITEMS_ACCEPTED, "order_items_accepted",
        "Sum of OrderItem.total_amount for this product dimension value inside "
        "the period's revenue-eligible orders; excludes shipping, tax and "
        "order-level discount, which are not allocated to items.",
    ),
    _rule(
        _METRIC_REVENUE_GROSS, BASIS_PAYMENTS_RECEIVED, "payments_received",
        "Sum of Payment.amount whose status says money arrived and whose "
        "paid_at is in the period. Reconciliation output only: never recorded, "
        "so one metric key keeps one meaning.",
        records=False,
    ),
    _rule(
        METRIC_REVENUE_REFUNDED, BASIS_ORDERS_ACCEPTED, "refunds_completed",
        "Sum of Refund.amount whose refunded_at is in the period, as a positive "
        "amount, in one currency scope; refund status is reported, not filtered, "
        "because no refund status vocabulary is documented.",
    ),
    _rule(
        METRIC_REVENUE_REFUNDED, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "refunds_completed_reported_campaign",
        "Same completed refunds, restricted to refunds whose order (or whose "
        "payment's order) is a platform-reported order of this campaign.",
    ),
    _rule(
        METRIC_REVENUE_NET, BASIS_ORDERS_ACCEPTED, "orders_accepted_less_refunds",
        "Gross revenue of the period's revenue-eligible orders minus the refunds "
        "completed in the same period and currency scope; may be negative.",
    ),
    _rule(
        METRIC_REVENUE_NET, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders_less_refunds",
        "Same difference restricted to platform-reported campaign orders.",
    ),
    _rule(
        METRIC_REVENUE_NET, BASIS_PAYMENTS_RECEIVED, "payments_received_less_refunds",
        "Received payments minus completed refunds of the period. "
        "Reconciliation output only: never recorded.",
        records=False,
    ),
    _rule(
        METRIC_REVENUE_PER_CUSTOMER, BASIS_ORDERS_ACCEPTED,
        "orders_accepted_resolved_customers",
        "Gross revenue of the period's revenue-eligible orders divided by the "
        "distinct resolved customers who placed them; UNAVAILABLE when that "
        "count is zero. Orders without a resolved customer are reported.",
    ),
    _rule(
        METRIC_REVENUE_PER_CUSTOMER, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders_resolved_customers",
        "Same ratio restricted to platform-reported campaign orders; "
        "UNAVAILABLE when no resolved customer was counted.",
    ),
    _rule(
        _METRIC_SALES_GROWTH_RATE, BASIS_ORDERS_ACCEPTED, "orders_placed_vs_previous",
        "(current - previous) / abs(previous) over the recorded total-orders "
        "observations of two periods; UNAVAILABLE when either is missing or "
        "the previous value is zero.",
    ),
    _rule(
        _METRIC_SALES_GROWTH_RATE, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "reported_campaign_orders_vs_previous",
        "Same fractional change over the recorded platform-reported campaign "
        "total-orders observations of two periods.",
    ),
    _rule(
        METRIC_REVENUE_GROWTH_RATE, BASIS_ORDERS_ACCEPTED,
        "net_orders_accepted_vs_previous",
        "(current - previous) / abs(previous) over the recorded net-revenue "
        "observations of two periods; UNAVAILABLE when either is missing or "
        "the previous value is zero.",
    ),
    _rule(
        METRIC_REVENUE_GROWTH_RATE, BASIS_REPORTED_CAMPAIGN_ORDERS,
        "net_reported_campaign_vs_previous",
        "Same fractional change over the recorded platform-reported campaign "
        "net-revenue observations of two periods.",
    ),
)


def get_calculation_rule(*, metric_key, basis):
    """Return the single documented rule for one (metric key, basis) pair."""
    if not isinstance(metric_key, str) or not isinstance(basis, str):
        raise RevenueValidationError("metric_key and basis must be strings.")
    rule = CALCULATION_RULES.get((metric_key, basis))
    if rule is None:
        raise RevenueValidationError(
            f"No calculation rule is defined for {metric_key} on basis {basis}."
        )
    return rule


# --------------------------------------------------------------------------
# Scope vocabulary
# --------------------------------------------------------------------------

DIMENSION_CURRENCY = "CURRENCY"
DIMENSION_CHANNEL = "CHANNEL"
DIMENSION_CUSTOMER_SEGMENT = "CUSTOMER_SEGMENT"
DIMENSION_CAMPAIGN = "CAMPAIGN"
DIMENSION_PRODUCT = "PRODUCT"
DIMENSION_PRODUCT_VARIANT = "PRODUCT_VARIANT"

# Scopes an order-total based figure can express. PRODUCT/PRODUCT_VARIANT are
# item-based and therefore excluded here on purpose.
ORDER_SCOPE_DIMENSIONS = frozenset({
    None, DIMENSION_CURRENCY, DIMENSION_CHANNEL, DIMENSION_CUSTOMER_SEGMENT,
    DIMENSION_CAMPAIGN,
})

BREAKDOWN_PRODUCT = "PRODUCT"
BREAKDOWN_PRODUCT_VARIANT = "PRODUCT_VARIANT"
BREAKDOWN_PRODUCT_CATEGORY = "PRODUCT_CATEGORY"
BREAKDOWN_CAMPAIGN = "CAMPAIGN"
BREAKDOWN_CHANNEL = "CHANNEL"
BREAKDOWN_CUSTOMER_SEGMENT = "CUSTOMER_SEGMENT"
BREAKDOWN_CURRENCY = "CURRENCY"
BREAKDOWN_CUSTOMER = "CUSTOMER"

# A breakdown maps to the snapshot dimension that can store it, or to None when
# the closed metrics.DIMENSION_TYPES vocabulary cannot express it. A None target
# is computable and returned to the caller but is never recorded, instead of
# being squeezed into an unrelated dimension.
BREAKDOWN_DIMENSIONS = MappingProxyType({
    BREAKDOWN_PRODUCT: DIMENSION_PRODUCT,
    BREAKDOWN_PRODUCT_VARIANT: DIMENSION_PRODUCT_VARIANT,
    BREAKDOWN_CAMPAIGN: DIMENSION_CAMPAIGN,
    BREAKDOWN_CHANNEL: DIMENSION_CHANNEL,
    BREAKDOWN_CUSTOMER_SEGMENT: DIMENSION_CUSTOMER_SEGMENT,
    BREAKDOWN_CURRENCY: DIMENSION_CURRENCY,
    BREAKDOWN_PRODUCT_CATEGORY: None,
    BREAKDOWN_CUSTOMER: None,
})

_ITEM_BASED_BREAKDOWNS = frozenset({
    BREAKDOWN_PRODUCT, BREAKDOWN_PRODUCT_VARIANT, BREAKDOWN_PRODUCT_CATEGORY,
})

_ENTITY_DIMENSION_SCOPES = MappingProxyType({
    DIMENSION_PRODUCT: (models.Product, "business_id"),
    DIMENSION_PRODUCT_VARIANT: (models.ProductVariant, "product__business_id"),
    DIMENSION_CAMPAIGN: (models.Campaign, "business_id"),
})

for _breakdown, _dimension in BREAKDOWN_DIMENSIONS.items():
    if _dimension is not None and _dimension not in metrics.DIMENSION_TYPES:
        raise RevenueDefinitionError(
            f"Breakdown {_breakdown} targets dimension {_dimension}, which the "
            "metric snapshot contract does not define."
        )
del _breakdown, _dimension

for _dimension in ORDER_SCOPE_DIMENSIONS:
    if _dimension is not None and _dimension not in metrics.DIMENSION_TYPES:
        raise RevenueDefinitionError(
            f"Dimension {_dimension} is not in the metric snapshot contract."
        )
del _dimension

# T-001 owns this relationship; its key is read from that service's registry so
# the two modules can never drift apart.
_CAMPAIGN_ORDER_RULE = relationships.RULES["campaign_order"]

CURRENCY_SOURCE_CALLER = "CALLER"
CURRENCY_SOURCE_DIMENSION = "CURRENCY_DIMENSION"
CURRENCY_SOURCE_SINGLE_OBSERVED = "SINGLE_OBSERVED"
CURRENCY_SOURCE_BUSINESS_DEFAULT = "BUSINESS_DEFAULT"
# The per-currency breakdown: each row is one currency, so the view as a whole
# has no single currency scope and its rows are never added together.
CURRENCY_SOURCE_PER_ROW = "PER_ROW"

COMPARISON_PREVIOUS_PERIOD = "PREVIOUS_PERIOD"
COMPARISON_BASELINE_MEAN = "BASELINE_MEAN"

SIGNIFICANCE_NOT_SUPPLIED = "NOT_SUPPLIED"


# --------------------------------------------------------------------------
# Result structures
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CurrencyScope:
    """The single currency one amount observation covers, and where it came from."""

    currency: str
    source: str
    observed: tuple


@dataclass(frozen=True)
class RevenueScope:
    """The business, period bounds, dimension and currency one figure covers."""

    business_id: int
    period_start: datetime.datetime
    period_end: datetime.datetime
    dimension_type: str | None
    dimension_value: str | None
    currency: str
    currency_source: str
    basis: str


@dataclass(frozen=True)
class OrderRevenue:
    """§6 Total Revenue Analysis on the order basis, for one currency scope."""

    scope: RevenueScope
    counted_orders: int
    eligible_orders: int
    accepted_orders: int
    reversed_orders: int
    pending_orders: int
    cancelled_orders: int
    gross_amount: Decimal
    accepted_amount: Decimal
    reversed_amount: Decimal
    units_sold: int
    distinct_customers: int
    orders_without_customer: int
    coverage: MappingProxyType


@dataclass(frozen=True)
class PaymentReceipts:
    """The payment basis: what the payment statuses say actually arrived."""

    scope: RevenueScope
    received_payments: int
    received_amount: Decimal
    not_received_payments: int
    not_received_amount: Decimal
    coverage: MappingProxyType


@dataclass(frozen=True)
class RefundImpact:
    """§6 Refund Impact Analysis: completed refunds of the period."""

    scope: RevenueScope
    refund_count: int
    refunded_amount: Decimal
    refunds_without_order_link: int
    refunds_without_any_order: int
    coverage: MappingProxyType


@dataclass(frozen=True)
class RevenueReconciliation:
    """Order totals reconciled against payments and refunds for one scope."""

    scope: RevenueScope
    orders: OrderRevenue
    payments: PaymentReceipts
    refunds: RefundImpact
    gross_order_amount: Decimal
    received_payment_amount: Decimal
    refunded_amount: Decimal
    net_order_amount: Decimal
    net_received_amount: Decimal
    order_payment_difference: Decimal
    coverage: MappingProxyType


@dataclass(frozen=True)
class RevenueBreakdownRow:
    """One dimension value's revenue contribution inside one currency scope."""

    dimension_type: str | None
    dimension_value: str
    gross_amount: Decimal
    order_count: int
    units: int
    recordable: bool


@dataclass(frozen=True)
class RevenueBreakdown:
    """§6 product / campaign / customer / channel distribution of revenue."""

    scope: RevenueScope
    breakdown: str
    basis: str
    rows: tuple
    total_gross_amount: Decimal
    coverage: MappingProxyType


@dataclass(frozen=True)
class MetricWriteSet:
    """The snapshot write results of one recording operation, by metric key."""

    scope: RevenueScope
    results: MappingProxyType


@dataclass(frozen=True)
class BreakdownWriteSet:
    """The snapshot write results of a recorded breakdown."""

    scope: RevenueScope
    breakdown: str
    results: tuple
    skipped_rows: int


@dataclass(frozen=True)
class RevenueChangeDetection:
    """§6 Revenue Change Detection; significance is the caller's input only."""

    metric_key: str
    calculation_rule: str
    period_type: str
    dimension_type: str | None
    dimension_value: str | None
    comparison_basis: str
    current: metrics.MetricObservation | None
    previous: metrics.MetricObservation | None
    baseline_value: Decimal | None
    baseline_observation_ids: tuple
    absolute_change: Decimal | None
    relative_change: Decimal | None
    direction: str
    is_significant: bool | None
    significance_criteria: MappingProxyType


# --------------------------------------------------------------------------
# Boundary validation
# --------------------------------------------------------------------------

def _require_positive_id(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RevenueValidationError(f"{label} must be a positive integer.")
    return value


def _require_aware(value, label):
    if isinstance(value, datetime.datetime) and timezone.is_aware(value):
        return value
    raise RevenueValidationError(f"{label} must be a timezone-aware datetime.")


def _require_bounds(period_start, period_end):
    """Half-open [period_start, period_end); no calendar alignment is enforced."""
    start = _require_aware(period_start, "period_start")
    end = _require_aware(period_end, "period_end")
    if end <= start:
        raise RevenueValidationError(
            "period_end must be strictly after period_start; periods are "
            "half-open [period_start, period_end)."
        )
    return start, end


def _require_period_type(period_type):
    if not isinstance(period_type, str) or period_type not in metrics.PERIOD_TYPES:
        raise RevenueValidationError(
            f"period_type must be one of {sorted(metrics.PERIOD_TYPES)}."
        )
    return period_type


def _require_currency(currency):
    if currency is None:
        return None
    if not isinstance(currency, str):
        raise RevenueValidationError("currency must be a string when provided.")
    value = currency.strip()
    if not value:
        raise RevenueValidationError("currency must not be empty.")
    if len(value) > _CURRENCY_MAX:
        raise RevenueValidationError(
            f"currency exceeds the {_CURRENCY_MAX} characters the canonical "
            "currency columns store, so it can never match a stored row."
        )
    return value


def _require_dimension(dimension_type, dimension_value, allowed):
    """Both present or both absent, from a closed allowed set."""
    if dimension_type is None and dimension_value is None:
        if None not in allowed:
            raise RevenueScopeError(
                "This figure requires an explicit dimension; the business-wide "
                "scope is not supported for it."
            )
        return None, None
    if dimension_type is None or dimension_value is None:
        raise RevenueValidationError(
            "dimension_type and dimension_value must both be provided or both omitted."
        )
    if not isinstance(dimension_type, str) or dimension_type not in allowed:
        raise RevenueScopeError(
            "dimension_type must be one of "
            f"{sorted(name for name in allowed if name is not None)} for this figure."
        )
    if not isinstance(dimension_value, str):
        raise RevenueValidationError("dimension_value must be a string.")
    value = dimension_value.strip()
    if not value:
        raise RevenueValidationError("dimension_value must not be empty.")
    if metrics.DIMENSION_TYPES[dimension_type] == "ENTITY":
        if not (value.isascii() and value.isdigit()) or value.startswith("0"):
            raise RevenueValidationError(
                f"dimension_value for {dimension_type} must be a canonical "
                "positive entity id written without leading zeros."
            )
    return dimension_type, value


def _require_business(business_id):
    business = models.Business.objects.filter(pk=business_id).first()
    if business is None:
        raise RevenueValidationError("Business does not exist.")
    return business


def _require_dimension_scope(business_id, dimension_type, dimension_value):
    """Never trust a caller-supplied id: the row must live in this business."""
    if dimension_type is None or dimension_type not in _ENTITY_DIMENSION_SCOPES:
        return
    model, scope_field = _ENTITY_DIMENSION_SCOPES[dimension_type]
    exists = model.objects.filter(
        pk=int(dimension_value), **{scope_field: business_id}
    ).exists()
    if not exists:
        raise RevenueValidationError(
            f"{dimension_type} dimension {dimension_value} does not exist in "
            "this business."
        )


def _require_non_negative_decimal(value, label):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise RevenueValidationError(
            f"{label} must be a Decimal; floats, integers and strings are "
            "rejected so no implicit conversion can change a threshold."
        )
    if not value.is_finite() or value < 0:
        raise RevenueValidationError(f"{label} must be a finite, non-negative Decimal.")
    return value


def _require_limit(limit):
    if limit is None:
        return None
    return _require_positive_id(limit, "limit")


# --------------------------------------------------------------------------
# Decimal helpers: Decimal only, division at full precision
# --------------------------------------------------------------------------

def _divide(numerator, denominator):
    """Exact-context division; the caller must have excluded a zero denominator."""
    with localcontext() as context:
        context.prec = _PRECISION
        return numerator / denominator


def _subtract(left, right):
    with localcontext() as context:
        context.prec = _PRECISION
        return left - right


def _add(left, right):
    with localcontext() as context:
        context.prec = _PRECISION
        return left + right


def _sum_amounts(amounts):
    """Sum stored 2-place decimals exactly; report rows with a missing amount."""
    total = Decimal(0)
    missing = 0
    with localcontext() as context:
        context.prec = _PRECISION
        for amount in amounts:
            if amount is None:
                missing += 1
                continue
            total = total + amount
    return total, missing


def _status_counts(counter):
    return {label: count for label, count in sorted(counter.items())}


def _status_label(status):
    if status is None:
        return _BLANK_LABEL
    return status if status.strip() else _BLANK_LABEL


# --------------------------------------------------------------------------
# Currency scope resolution — never sum across currencies
# --------------------------------------------------------------------------

def _distinct_currencies(queryset):
    observed = set()
    blank = 0
    for currency in queryset.values_list("currency", flat=True):
        if currency is None or not currency.strip():
            blank += 1
            continue
        observed.add(currency)
    return tuple(sorted(observed)), blank


def _resolve_currency(business, caller_currency, dimension_type, dimension_value,
                      observed):
    """Resolve the single currency this observation covers, or refuse."""
    if dimension_type == DIMENSION_CURRENCY:
        if caller_currency is not None and caller_currency != dimension_value:
            raise RevenueValidationError(
                "currency and the CURRENCY dimension value must agree."
            )
        return CurrencyScope(
            currency=dimension_value,
            source=CURRENCY_SOURCE_DIMENSION,
            observed=observed,
        )
    if caller_currency is not None:
        return CurrencyScope(
            currency=caller_currency,
            source=CURRENCY_SOURCE_CALLER,
            observed=observed,
        )
    if len(observed) == 1:
        return CurrencyScope(
            currency=observed[0],
            source=CURRENCY_SOURCE_SINGLE_OBSERVED,
            observed=observed,
        )
    if not observed:
        currency = _require_currency(business.currency)
        if currency is None:
            raise RevenueValidationError(
                "The scope contains no money row and the business has no "
                "recorded currency, so no currency scope can be determined."
            )
        return CurrencyScope(
            currency=currency,
            source=CURRENCY_SOURCE_BUSINESS_DEFAULT,
            observed=observed,
        )
    raise RevenueCurrencyMixError(
        "The scope contains more than one currency "
        f"({', '.join(observed)}); amounts are never summed across currencies. "
        "Pass currency=..., use the CURRENCY dimension, or read "
        "summarize_revenue_breakdown(breakdown='CURRENCY')."
    )


def _scope(business_id, start, end, dimension_type, dimension_value, currency_scope,
           basis):
    return RevenueScope(
        business_id=business_id,
        period_start=start,
        period_end=end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
        currency=currency_scope.currency,
        currency_source=currency_scope.source,
        basis=basis,
    )


def _basis_for_dimension(dimension_type):
    if dimension_type == DIMENSION_CAMPAIGN:
        return BASIS_REPORTED_CAMPAIGN_ORDERS
    return BASIS_ORDERS_ACCEPTED


# --------------------------------------------------------------------------
# Order scope construction
# --------------------------------------------------------------------------

def _segment_customer_ids(business_id, tag):
    return set(
        models.CustomerTag.objects.filter(
            customer__business_id=business_id, tag=tag
        ).values_list("customer_id", flat=True)
    )


def _campaign_order_links(business_id, campaign_id=None):
    """Valid platform-reported CAMPAIGN -> ORDER links produced by T-001."""
    query = models.BusinessRelationship.objects.filter(
        business_id=business_id,
        source_entity_type=_CAMPAIGN_ORDER_RULE.source_type,
        relationship_type=_CAMPAIGN_ORDER_RULE.relationship_type,
        target_entity_type=_CAMPAIGN_ORDER_RULE.target_type,
        rule_key=_CAMPAIGN_ORDER_RULE.key,
        relationship_source="DETERMINISTIC",
        valid_to__isnull=True,
    )
    if campaign_id is not None:
        query = query.filter(source_entity_id=campaign_id)
    return tuple(
        sorted(query.values_list("source_entity_id", "target_entity_id").distinct())
    )


def _scoped_orders(business_id, dimension_type, dimension_value):
    """Every order of this business inside the requested dimension scope."""
    queryset = models.Order.objects.filter(business_id=business_id)
    if dimension_type is None:
        return queryset
    if dimension_type == DIMENSION_CURRENCY:
        return queryset.filter(currency=dimension_value)
    if dimension_type == DIMENSION_CHANNEL:
        return queryset.filter(
            integration_connection__business_id=business_id,
            integration_connection__integration_source__key=dimension_value,
        )
    if dimension_type == DIMENSION_CUSTOMER_SEGMENT:
        customer_ids = _segment_customer_ids(business_id, dimension_value)
        return queryset.filter(customer_id__in=sorted(customer_ids))
    if dimension_type == DIMENSION_CAMPAIGN:
        order_ids = {
            order_id for _, order_id
            in _campaign_order_links(business_id, int(dimension_value))
        }
        return queryset.filter(pk__in=sorted(order_ids))
    raise RevenueScopeError(f"Dimension {dimension_type} cannot scope an order set.")


def _order_period_filter(queryset, start, end):
    return queryset.filter(
        **{
            f"{_ORDER_PERIOD_TIMESTAMP_FIELD}__gte": start,
            f"{_ORDER_PERIOD_TIMESTAMP_FIELD}__lt": end,
        }
    )


# --------------------------------------------------------------------------
# §6 Total Revenue Analysis — order basis
# --------------------------------------------------------------------------

def _order_revenue(business, start, end, dimension_type, dimension_value,
                   currency_scope):
    business_id = business.pk
    scoped = _scoped_orders(business_id, dimension_type, dimension_value)
    in_period = _order_period_filter(scoped, start, end)
    currency = currency_scope.currency

    missing_timestamp = scoped.filter(
        **{f"{_ORDER_PERIOD_TIMESTAMP_FIELD}__isnull": True}
    ).count()
    _, blank_currency = _distinct_currencies(in_period)

    rows = list(
        in_period.order_by("pk").values_list(
            "pk", "status", "currency", "total_amount", "customer_id",
        )
    )

    other_currency = 0
    other_currency_amount = Decimal(0)
    counted = []
    eligible = []
    accepted_amounts = []
    reversed_amounts = []
    pending = 0
    cancelled = 0
    unclassified = {}
    unclassified_amount = Decimal(0)
    customers = set()
    without_customer = 0

    with localcontext() as context:
        context.prec = _PRECISION
        for order_id, status, row_currency, total, customer_id in rows:
            if row_currency is None or not row_currency.strip():
                continue  # already reported as blank_currency
            if row_currency != currency:
                other_currency += 1
                if total is not None:
                    other_currency_amount = other_currency_amount + total
                continue
            if status not in COUNTED_ORDER_STATUSES:
                label = _status_label(status)
                unclassified[label] = unclassified.get(label, 0) + 1
                if total is not None:
                    unclassified_amount = unclassified_amount + total
                continue
            counted.append(order_id)
            if status in ORDER_STATUSES_CANCELLED:
                cancelled += 1
                continue
            if status in _ORDER_STATUSES_PENDING:
                pending += 1
                continue
            eligible.append(order_id)
            if status in _ORDER_STATUSES_ACCEPTED:
                accepted_amounts.append(total)
            else:
                reversed_amounts.append(total)
            if customer_id is None:
                without_customer += 1
            else:
                customers.add(customer_id)

    accepted_amount, accepted_missing = _sum_amounts(accepted_amounts)
    reversed_amount, reversed_missing = _sum_amounts(reversed_amounts)
    gross_amount = _add(accepted_amount, reversed_amount)

    eligible_orders_queryset = in_period.filter(
        currency=currency, status__in=sorted(REVENUE_ELIGIBLE_ORDER_STATUSES)
    )
    units, nonpositive_units, items_without_product = _order_units(
        business_id, eligible_orders_queryset
    )

    coverage = {
        "currency": currency,
        "currency_source": currency_scope.source,
        "currencies_observed_in_scope": list(currency_scope.observed),
        "order_period_timestamp_field": _ORDER_PERIOD_TIMESTAMP_FIELD,
        "orders_in_period": len(rows),
        "counted_orders": len(counted),
        "eligible_orders": len(eligible),
        "accepted_orders": len(accepted_amounts),
        "reversed_orders": len(reversed_amounts),
        "pending_orders": pending,
        "cancelled_orders": cancelled,
        "reversed_order_amount": reversed_amount,
        "unclassified_order_statuses": _status_counts(unclassified),
        "unclassified_orders": sum(unclassified.values()),
        "unclassified_order_amount": unclassified_amount,
        "orders_without_period_timestamp": missing_timestamp,
        "orders_without_currency": blank_currency,
        "orders_in_other_currency": other_currency,
        "orders_in_other_currency_amount": other_currency_amount,
        "orders_without_amount": accepted_missing + reversed_missing,
        "orders_without_resolved_customer": without_customer,
        "distinct_resolved_customers": len(customers),
        "order_items_with_nonpositive_quantity": nonpositive_units,
        "order_items_without_product": items_without_product,
        "eligible_order_statuses": sorted(REVENUE_ELIGIBLE_ORDER_STATUSES),
        "counted_order_statuses": sorted(COUNTED_ORDER_STATUSES),
    }
    if dimension_type == DIMENSION_CHANNEL:
        coverage["channel_source_field"] = "integration_source.key"
    if dimension_type == DIMENSION_CAMPAIGN:
        coverage["campaign_link_rule"] = _CAMPAIGN_ORDER_RULE.key
        coverage["campaign_link_provenance"] = "PLATFORM_REPORTED"

    basis = _basis_for_dimension(dimension_type)
    return OrderRevenue(
        scope=_scope(business_id, start, end, dimension_type, dimension_value,
                     currency_scope, basis),
        counted_orders=len(counted),
        eligible_orders=len(eligible),
        accepted_orders=len(accepted_amounts),
        reversed_orders=len(reversed_amounts),
        pending_orders=pending,
        cancelled_orders=cancelled,
        gross_amount=gross_amount,
        accepted_amount=accepted_amount,
        reversed_amount=reversed_amount,
        units_sold=units,
        distinct_customers=len(customers),
        orders_without_customer=without_customer,
        coverage=MappingProxyType(coverage),
    )


def _order_units(business_id, eligible_orders_queryset):
    """Units contained in the eligible orders; item rows stay business-scoped."""
    rows = models.OrderItem.objects.filter(
        order__business_id=business_id, order__in=eligible_orders_queryset
    ).values_list("quantity", "product_id")
    units = 0
    nonpositive = 0
    without_product = 0
    for quantity, product_id in rows:
        if product_id is None:
            without_product += 1
        if quantity is None:
            continue
        if quantity <= 0:
            nonpositive += 1
        units += quantity
    return units, nonpositive, without_product


def compute_order_revenue(*, business_id, period_start, period_end, currency=None,
                          dimension_type=None, dimension_value=None):
    """§6 Total Revenue Analysis on the order basis; read-only, no authorization.

    Returns an ``OrderRevenue`` for one currency scope and the half-open period
    ``[period_start, period_end)``. Gross revenue is the sum of
    ``Order.total_amount`` over the revenue-eligible orders (accepted or
    reversed); the reversal is subtracted only through refunds. Unrecognised
    statuses, missing ``ordered_at`` values, blank currencies and rows in another
    currency are excluded and reported in ``coverage``.
    """
    _require_positive_id(business_id, "business_id")
    start, end = _require_bounds(period_start, period_end)
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    currency = _require_currency(currency)
    with transaction.atomic():
        business = _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        observed, _ = _distinct_currencies(
            _order_period_filter(
                _scoped_orders(business_id, dimension_type, dimension_value), start, end
            )
        )
        currency_scope = _resolve_currency(
            business, currency, dimension_type, dimension_value, observed
        )
        return _order_revenue(
            business, start, end, dimension_type, dimension_value, currency_scope
        )


# --------------------------------------------------------------------------
# Payment basis
# --------------------------------------------------------------------------

def _scoped_payments(business_id, dimension_type, dimension_value):
    """Payments of this business inside the dimension scope, via their order."""
    queryset = models.Payment.objects.filter(business_id=business_id)
    if dimension_type is None:
        return queryset, 0
    if dimension_type == DIMENSION_CURRENCY:
        return queryset.filter(currency=dimension_value), 0
    scoped_orders = _scoped_orders(business_id, dimension_type, dimension_value)
    without_order = queryset.filter(order__isnull=True).count()
    return queryset.filter(order__in=scoped_orders), without_order


def _payment_receipts(business, start, end, dimension_type, dimension_value,
                      currency_scope):
    business_id = business.pk
    scoped, without_order_scope = _scoped_payments(
        business_id, dimension_type, dimension_value
    )
    in_period = scoped.filter(
        **{
            f"{_PAYMENT_PERIOD_TIMESTAMP_FIELD}__gte": start,
            f"{_PAYMENT_PERIOD_TIMESTAMP_FIELD}__lt": end,
        }
    )
    currency = currency_scope.currency
    missing_timestamp = scoped.filter(
        **{f"{_PAYMENT_PERIOD_TIMESTAMP_FIELD}__isnull": True}
    ).count()
    _, blank_currency = _distinct_currencies(in_period)

    received = []
    not_received = []
    unclassified = {}
    unclassified_amount = Decimal(0)
    other_currency = 0
    without_order_link = 0

    with localcontext() as context:
        context.prec = _PRECISION
        for status, row_currency, amount, order_id in in_period.order_by("pk").values_list(
            "status", "currency", "amount", "order_id"
        ):
            if row_currency is None or not row_currency.strip():
                continue
            if row_currency != currency:
                other_currency += 1
                continue
            if order_id is None:
                without_order_link += 1
            if status in PAYMENT_STATUSES_RECEIVED:
                received.append(amount)
            elif status in _PAYMENT_STATUSES_NOT_RECEIVED:
                not_received.append(amount)
            else:
                label = _status_label(status)
                unclassified[label] = unclassified.get(label, 0) + 1
                if amount is not None:
                    unclassified_amount = unclassified_amount + amount

    received_amount, received_missing = _sum_amounts(received)
    not_received_amount, not_received_missing = _sum_amounts(not_received)

    coverage = {
        "currency": currency,
        "currency_source": currency_scope.source,
        "payment_period_timestamp_field": _PAYMENT_PERIOD_TIMESTAMP_FIELD,
        "received_payment_statuses": sorted(PAYMENT_STATUSES_RECEIVED),
        "not_received_payment_statuses": sorted(_PAYMENT_STATUSES_NOT_RECEIVED),
        "received_payments": len(received),
        "not_received_payments": len(not_received),
        "not_received_amount": not_received_amount,
        "unclassified_payment_statuses": _status_counts(unclassified),
        "unclassified_payments": sum(unclassified.values()),
        "unclassified_payment_amount": unclassified_amount,
        "payments_without_period_timestamp": missing_timestamp,
        "payments_without_currency": blank_currency,
        "payments_in_other_currency": other_currency,
        "payments_without_amount": received_missing + not_received_missing,
        "payments_without_order_link": without_order_link,
        "payments_excluded_without_order_scope": without_order_scope,
    }
    return PaymentReceipts(
        scope=_scope(business_id, start, end, dimension_type, dimension_value,
                     currency_scope, BASIS_PAYMENTS_RECEIVED),
        received_payments=len(received),
        received_amount=received_amount,
        not_received_payments=len(not_received),
        not_received_amount=not_received_amount,
        coverage=MappingProxyType(coverage),
    )


def compute_payment_receipts(*, business_id, period_start, period_end, currency=None,
                             dimension_type=None, dimension_value=None):
    """The payment basis of revenue: money the payment statuses say arrived.

    A payment row existing is not receipt. Only ``PAID``,
    ``PARTIALLY_REFUNDED`` and ``REFUNDED`` payments whose ``paid_at`` falls in
    the half-open period contribute; everything else is counted and reported.
    This figure is reconciliation output and is deliberately never recorded
    under ``revenue_gross``, so that metric key keeps exactly one meaning.
    """
    _require_positive_id(business_id, "business_id")
    start, end = _require_bounds(period_start, period_end)
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    currency = _require_currency(currency)
    with transaction.atomic():
        business = _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        scoped, _ = _scoped_payments(business_id, dimension_type, dimension_value)
        observed, _ = _distinct_currencies(
            scoped.filter(
                **{
                    f"{_PAYMENT_PERIOD_TIMESTAMP_FIELD}__gte": start,
                    f"{_PAYMENT_PERIOD_TIMESTAMP_FIELD}__lt": end,
                }
            )
        )
        currency_scope = _resolve_currency(
            business, currency, dimension_type, dimension_value, observed
        )
        return _payment_receipts(
            business, start, end, dimension_type, dimension_value, currency_scope
        )


# --------------------------------------------------------------------------
# §6 Refund Impact Analysis
# --------------------------------------------------------------------------

def _scoped_refunds(business_id, dimension_type, dimension_value):
    """Refunds of this business; a null order link falls back to the payment's.

    ``Refund`` has no business column, so the business scope is the refund's
    payment. A refund whose own ``order`` is null is scoped through
    ``payment.order``; a refund with neither cannot be placed in any order-based
    dimension scope, so it is excluded there and counted.
    """
    queryset = models.Refund.objects.filter(payment__business_id=business_id)
    if dimension_type is None:
        return queryset, 0
    if dimension_type == DIMENSION_CURRENCY:
        return queryset.filter(currency=dimension_value), 0
    scoped_orders = _scoped_orders(business_id, dimension_type, dimension_value)
    in_scope = queryset.filter(
        Q(order__in=scoped_orders)
        | Q(order__isnull=True, payment__order__in=scoped_orders)
    )
    unscopable = queryset.filter(order__isnull=True, payment__order__isnull=True).count()
    return in_scope, unscopable


def _refund_impact(business, start, end, dimension_type, dimension_value,
                   currency_scope):
    business_id = business.pk
    scoped, unscopable = _scoped_refunds(business_id, dimension_type, dimension_value)
    in_period = scoped.filter(
        **{
            f"{_REFUND_COMPLETION_TIMESTAMP_FIELD}__gte": start,
            f"{_REFUND_COMPLETION_TIMESTAMP_FIELD}__lt": end,
        }
    )
    currency = currency_scope.currency
    missing_timestamp = scoped.filter(
        **{f"{_REFUND_COMPLETION_TIMESTAMP_FIELD}__isnull": True}
    ).count()
    _, blank_currency = _distinct_currencies(in_period)

    amounts = []
    statuses = {}
    other_currency = 0
    without_order_link = 0
    without_any_order = 0

    for status, row_currency, amount, order_id, payment_order_id in (
        in_period.order_by("pk").values_list(
            "status", "currency", "amount", "order_id", "payment__order_id"
        )
    ):
        if row_currency is None or not row_currency.strip():
            continue
        if row_currency != currency:
            other_currency += 1
            continue
        label = _status_label(status)
        statuses[label] = statuses.get(label, 0) + 1
        if order_id is None:
            without_order_link += 1
            if payment_order_id is None:
                without_any_order += 1
        amounts.append(amount)

    refunded_amount, missing_amount = _sum_amounts(amounts)

    coverage = {
        "currency": currency,
        "currency_source": currency_scope.source,
        "refund_completion_timestamp_field": _REFUND_COMPLETION_TIMESTAMP_FIELD,
        "refund_status_filter": "NONE_DOCUMENTED",
        "refund_statuses": _status_counts(statuses),
        "refunds_counted": len(amounts),
        "refunds_without_completion_timestamp": missing_timestamp,
        "refunds_without_currency": blank_currency,
        "refunds_in_other_currency": other_currency,
        "refunds_without_amount": missing_amount,
        "refunds_without_order_link": without_order_link,
        "refunds_without_any_order": without_any_order,
        "refunds_excluded_without_order_scope": unscopable,
    }
    basis = _basis_for_dimension(dimension_type)
    return RefundImpact(
        scope=_scope(business_id, start, end, dimension_type, dimension_value,
                     currency_scope, basis),
        refund_count=len(amounts),
        refunded_amount=refunded_amount,
        refunds_without_order_link=without_order_link,
        refunds_without_any_order=without_any_order,
        coverage=MappingProxyType(coverage),
    )


def compute_refund_impact(*, business_id, period_start, period_end, currency=None,
                          dimension_type=None, dimension_value=None):
    """§6 Refund Impact Analysis: the refunds completed inside the period.

    A refund contributes when its ``refunded_at`` falls in the half-open period.
    ``Refund.status`` is reported in ``coverage["refund_statuses"]`` but is not
    used as a filter, because no refund status vocabulary is documented. The
    amount is positive: it is subtracted once, by net revenue.
    """
    _require_positive_id(business_id, "business_id")
    start, end = _require_bounds(period_start, period_end)
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    currency = _require_currency(currency)
    with transaction.atomic():
        business = _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        scoped, _ = _scoped_refunds(business_id, dimension_type, dimension_value)
        observed, _ = _distinct_currencies(
            scoped.filter(
                **{
                    f"{_REFUND_COMPLETION_TIMESTAMP_FIELD}__gte": start,
                    f"{_REFUND_COMPLETION_TIMESTAMP_FIELD}__lt": end,
                }
            )
        )
        currency_scope = _resolve_currency(
            business, currency, dimension_type, dimension_value, observed
        )
        return _refund_impact(
            business, start, end, dimension_type, dimension_value, currency_scope
        )


# --------------------------------------------------------------------------
# Payment / refund reconciliation (T-003 acceptance criterion)
# --------------------------------------------------------------------------

def _joint_currency_scope(business, start, end, dimension_type, dimension_value,
                          currency):
    """One currency scope for orders, payments and refunds together."""
    order_currencies, _ = _distinct_currencies(
        _order_period_filter(
            _scoped_orders(business.pk, dimension_type, dimension_value), start, end
        )
    )
    payments, _ = _scoped_payments(business.pk, dimension_type, dimension_value)
    payment_currencies, _ = _distinct_currencies(
        payments.filter(
            **{
                f"{_PAYMENT_PERIOD_TIMESTAMP_FIELD}__gte": start,
                f"{_PAYMENT_PERIOD_TIMESTAMP_FIELD}__lt": end,
            }
        )
    )
    refunds, _ = _scoped_refunds(business.pk, dimension_type, dimension_value)
    refund_currencies, _ = _distinct_currencies(
        refunds.filter(
            **{
                f"{_REFUND_COMPLETION_TIMESTAMP_FIELD}__gte": start,
                f"{_REFUND_COMPLETION_TIMESTAMP_FIELD}__lt": end,
            }
        )
    )
    observed = tuple(sorted(
        set(order_currencies) | set(payment_currencies) | set(refund_currencies)
    ))
    return _resolve_currency(
        business, currency, dimension_type, dimension_value, observed
    )


def _reconcile(business, start, end, dimension_type, dimension_value, currency_scope):
    orders = _order_revenue(
        business, start, end, dimension_type, dimension_value, currency_scope
    )
    payments = _payment_receipts(
        business, start, end, dimension_type, dimension_value, currency_scope
    )
    refunds = _refund_impact(
        business, start, end, dimension_type, dimension_value, currency_scope
    )
    net_orders = _subtract(orders.gross_amount, refunds.refunded_amount)
    net_received = _subtract(payments.received_amount, refunds.refunded_amount)
    difference = _subtract(orders.gross_amount, payments.received_amount)
    coverage = dict(orders.coverage)
    coverage.update(payments.coverage)
    coverage.update(refunds.coverage)
    coverage["order_payment_difference"] = difference
    coverage["reconciliation_note"] = (
        "The order basis and the payment basis use different period timestamps "
        "(ordered_at vs paid_at), so a non-zero difference is expected whenever "
        "an order is paid in another period, partially paid or unpaid."
    )
    basis = _basis_for_dimension(dimension_type)
    return RevenueReconciliation(
        scope=_scope(business.pk, start, end, dimension_type, dimension_value,
                     currency_scope, basis),
        orders=orders,
        payments=payments,
        refunds=refunds,
        gross_order_amount=orders.gross_amount,
        received_payment_amount=payments.received_amount,
        refunded_amount=refunds.refunded_amount,
        net_order_amount=net_orders,
        net_received_amount=net_received,
        order_payment_difference=difference,
        coverage=MappingProxyType(coverage),
    )


def reconcile_revenue(*, business_id, period_start, period_end, currency=None,
                      dimension_type=None, dimension_value=None):
    """Reconcile order totals against payments and refunds for one scope.

    All three sides are resolved into ONE currency scope first, so the
    reconciliation can never compare amounts in different currencies. The result
    carries both bases, the completed refunds, net revenue on each basis and the
    unreconciled ``order_payment_difference``, plus the merged coverage report.
    """
    _require_positive_id(business_id, "business_id")
    start, end = _require_bounds(period_start, period_end)
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    currency = _require_currency(currency)
    with transaction.atomic():
        business = _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        currency_scope = _joint_currency_scope(
            business, start, end, dimension_type, dimension_value, currency
        )
        return _reconcile(
            business, start, end, dimension_type, dimension_value, currency_scope
        )


# --------------------------------------------------------------------------
# §6 Product / Campaign / Customer / Channel revenue distribution
# --------------------------------------------------------------------------

def _require_breakdown(breakdown):
    if not isinstance(breakdown, str) or breakdown not in BREAKDOWN_DIMENSIONS:
        raise RevenueValidationError(
            f"breakdown must be one of {sorted(BREAKDOWN_DIMENSIONS)}."
        )
    return breakdown


def _item_breakdown_rows(business_id, eligible_orders, breakdown):
    """Item-based grouping; the order total is never split across items."""
    rows = models.OrderItem.objects.filter(
        order__business_id=business_id, order__in=eligible_orders
    ).order_by("pk").values_list(
        "order_id", "product_id", "product_variant_id", "quantity", "total_amount",
        "product__category", "product__business_id",
        "product_variant__product__business_id",
    )
    groups = {}
    without_key = 0
    without_amount = 0
    foreign_product = 0
    with localcontext() as context:
        context.prec = _PRECISION
        for (order_id, product_id, variant_id, quantity, total, category,
             product_business_id, variant_business_id) in rows:
            # An item referencing another business's product is a canonical
            # integrity break: exclude and report it instead of letting the
            # dimension validation abort the whole recording transaction.
            if product_id is not None and product_business_id != business_id:
                foreign_product += 1
                continue
            if variant_id is not None and variant_business_id != business_id:
                foreign_product += 1
                continue
            if breakdown == BREAKDOWN_PRODUCT:
                key = None if product_id is None else str(product_id)
            elif breakdown == BREAKDOWN_PRODUCT_VARIANT:
                key = None if variant_id is None else str(variant_id)
            else:
                key = None if category is None or not category.strip() else category
            if key is None:
                without_key += 1
                continue
            amount, orders, units = groups.get(key, (Decimal(0), set(), 0))
            if total is None:
                without_amount += 1
            else:
                amount = amount + total
            orders = orders | {order_id}
            if quantity is not None:
                units += quantity
            groups[key] = (amount, orders, units)
    return groups, without_key, without_amount, foreign_product


def _order_breakdown_rows(business_id, eligible_orders, breakdown):
    """Order-total grouping for campaign, channel, segment, currency, customer."""
    rows = list(
        eligible_orders.order_by("pk").values_list(
            "pk", "total_amount", "customer_id", "currency",
            "integration_connection_id",
            "integration_connection__business_id",
            "integration_connection__integration_source__key",
        )
    )
    order_ids = [row[0] for row in rows]
    units_by_order = {}
    for order_id, quantity in models.OrderItem.objects.filter(
        order__business_id=business_id, order__in=eligible_orders
    ).values_list("order_id", "quantity"):
        units_by_order[order_id] = units_by_order.get(order_id, 0) + (quantity or 0)

    campaigns_by_order = {}
    multi_campaign_orders = 0
    links_without_campaign_row = 0
    if breakdown == BREAKDOWN_CAMPAIGN:
        valid_campaign_ids = set(
            models.Campaign.objects.filter(business_id=business_id)
            .values_list("pk", flat=True)
        )
        for campaign_id, order_id in _campaign_order_links(business_id):
            # A link whose campaign row is gone cannot be recorded against the
            # CAMPAIGN dimension; exclude and report rather than abort the run.
            if campaign_id not in valid_campaign_ids:
                links_without_campaign_row += 1
                continue
            campaigns_by_order.setdefault(order_id, set()).add(campaign_id)
        multi_campaign_orders = sum(
            1 for order_id in order_ids
            if len(campaigns_by_order.get(order_id, ())) > 1
        )

    tags_by_customer = {}
    if breakdown == BREAKDOWN_CUSTOMER_SEGMENT:
        for customer_id, tag in models.CustomerTag.objects.filter(
            customer__business_id=business_id
        ).values_list("customer_id", "tag"):
            if tag and tag.strip():
                tags_by_customer.setdefault(customer_id, set()).add(tag)

    groups = {}
    without_key = 0
    without_amount = 0
    foreign_connection = 0

    with localcontext() as context:
        context.prec = _PRECISION
        for (order_id, total, customer_id, row_currency, connection_id,
             connection_business_id, source_key) in rows:
            if breakdown == BREAKDOWN_CAMPAIGN:
                keys = sorted(
                    str(campaign_id)
                    for campaign_id in campaigns_by_order.get(order_id, ())
                )
            elif breakdown == BREAKDOWN_CHANNEL:
                if connection_id is None:
                    keys = []
                elif connection_business_id != business_id:
                    foreign_connection += 1
                    keys = []
                elif source_key is None or not source_key.strip():
                    keys = []
                else:
                    keys = [source_key]
            elif breakdown == BREAKDOWN_CUSTOMER_SEGMENT:
                keys = sorted(tags_by_customer.get(customer_id, ()))
            elif breakdown == BREAKDOWN_CURRENCY:
                keys = (
                    [] if row_currency is None or not row_currency.strip()
                    else [row_currency]
                )
            else:  # BREAKDOWN_CUSTOMER
                keys = [] if customer_id is None else [str(customer_id)]
            if not keys:
                without_key += 1
                continue
            if total is None:
                without_amount += 1
            for key in keys:
                amount, orders, units = groups.get(key, (Decimal(0), set(), 0))
                if total is not None:
                    amount = amount + total
                groups[key] = (
                    amount,
                    orders | {order_id},
                    units + units_by_order.get(order_id, 0),
                )
    return (groups, without_key, without_amount, foreign_connection,
            multi_campaign_orders, links_without_campaign_row)


def _breakdown_order_coverage(scoped_orders, in_period, breakdown, currency_scope):
    """Report orders a breakdown excluded before grouping them into rows."""
    missing_timestamp = scoped_orders.filter(
        **{f"{_ORDER_PERIOD_TIMESTAMP_FIELD}__isnull": True}
    ).count()
    unclassified = {}
    other_currency = 0
    for status, row_currency in in_period.order_by("pk").values_list(
        "status", "currency"
    ):
        if row_currency is None or not row_currency.strip():
            continue
        if (
            breakdown != BREAKDOWN_CURRENCY
            and row_currency != currency_scope.currency
        ):
            other_currency += 1
            continue
        if status not in COUNTED_ORDER_STATUSES:
            label = _status_label(status)
            unclassified[label] = unclassified.get(label, 0) + 1
    return {
        "unclassified_order_statuses": _status_counts(unclassified),
        "orders_in_other_currency": other_currency,
        "orders_without_period_timestamp": missing_timestamp,
    }


def _breakdown(business, start, end, breakdown, currency_scope, limit):
    business_id = business.pk
    item_based = breakdown in _ITEM_BASED_BREAKDOWNS
    dimension_type = BREAKDOWN_DIMENSIONS[breakdown]
    basis = (
        BASIS_ORDER_ITEMS_ACCEPTED
        if item_based else _basis_for_dimension(dimension_type)
    )
    scoped_orders = models.Order.objects.filter(business_id=business_id)
    all_orders = _order_period_filter(scoped_orders, start, end)
    eligible = all_orders.filter(status__in=sorted(REVENUE_ELIGIBLE_ORDER_STATUSES))
    if breakdown != BREAKDOWN_CURRENCY:
        # Currency isolation: one scope per observation, except the explicit
        # per-currency breakdown, whose rows are each a single currency.
        eligible = eligible.filter(currency=currency_scope.currency)

    foreign_connection = 0
    multi_campaign_orders = 0
    links_without_campaign_row = 0
    foreign_product = 0
    if item_based:
        groups, without_key, without_amount, foreign_product = _item_breakdown_rows(
            business_id, eligible, breakdown
        )
    else:
        (groups, without_key, without_amount, foreign_connection,
         multi_campaign_orders, links_without_campaign_row) = _order_breakdown_rows(
            business_id, eligible, breakdown
        )

    all_rows = tuple(
        RevenueBreakdownRow(
            dimension_type=dimension_type,
            dimension_value=key,
            gross_amount=amount,
            order_count=len(orders),
            units=units,
            recordable=dimension_type is not None,
        )
        for key, (amount, orders, units)
        in sorted(groups.items(), key=lambda item: (-item[1][0], item[0]))
    )
    # A CURRENCY breakdown deliberately has no aggregate money total: adding
    # its rows would create a value with no currency. Zero is the neutral
    # non-observation used by this fixed Decimal result field and by the stored
    # breakdown context; every actual per-currency amount remains on its row.
    total = (
        Decimal(0)
        if breakdown == BREAKDOWN_CURRENCY
        else _sum_amounts([row.gross_amount for row in all_rows])[0]
    )
    rows = all_rows
    if limit is not None:
        rows = rows[:limit]

    coverage = {
        "currency": currency_scope.currency,
        "currency_source": currency_scope.source,
        "currencies_observed_in_scope": list(currency_scope.observed),
        "breakdown": breakdown,
        "basis": basis,
        "dimension_type": dimension_type or "NOT_EXPRESSIBLE",
        "order_period_timestamp_field": _ORDER_PERIOD_TIMESTAMP_FIELD,
        "eligible_order_statuses": sorted(REVENUE_ELIGIBLE_ORDER_STATUSES),
        "breakdown_rows": len(groups),
        "rows_returned": len(rows),
        "additive": breakdown not in (BREAKDOWN_CAMPAIGN, BREAKDOWN_CUSTOMER_SEGMENT),
    }
    coverage.update(
        _breakdown_order_coverage(
            scoped_orders, all_orders, breakdown, currency_scope
        )
    )
    if item_based:
        coverage["order_items_without_breakdown_key"] = without_key
        coverage["order_items_without_amount"] = without_amount
        coverage["order_items_with_foreign_product"] = foreign_product
        coverage["item_basis_note"] = (
            "Item totals exclude shipping, tax and order-level discount; they do "
            "not add up to the order totals of revenue_gross.orders_accepted."
        )
    else:
        coverage["orders_without_breakdown_key"] = without_key
        coverage["orders_without_amount"] = without_amount
    if breakdown == BREAKDOWN_CHANNEL:
        coverage["orders_without_channel"] = without_key
        coverage["orders_with_foreign_integration_connection"] = foreign_connection
        coverage["channel_source_field"] = "integration_source.key"
    if breakdown == BREAKDOWN_CAMPAIGN:
        coverage["campaign_link_rule"] = _CAMPAIGN_ORDER_RULE.key
        coverage["campaign_link_provenance"] = "PLATFORM_REPORTED"
        coverage["orders_reported_by_multiple_campaigns"] = multi_campaign_orders
        coverage["orders_without_reported_campaign"] = without_key
        coverage["campaign_links_without_campaign_row"] = links_without_campaign_row
    if breakdown == BREAKDOWN_CUSTOMER_SEGMENT:
        coverage["orders_without_segment"] = without_key
        coverage["segment_source"] = "customer_tags.tag"
    if dimension_type is None:
        coverage["not_recordable_reason"] = (
            f"The metric snapshot contract defines no {breakdown} dimension, so "
            "this breakdown is computed and returned but never recorded."
        )
    return RevenueBreakdown(
        scope=_scope(business_id, start, end, None, None, currency_scope, basis),
        breakdown=breakdown,
        basis=basis,
        rows=rows,
        total_gross_amount=total,
        coverage=MappingProxyType(coverage),
    )


def summarize_revenue_breakdown(*, business_id, breakdown, period_start, period_end,
                                currency=None, limit=None):
    """§6 Product / Campaign / Customer / Channel Revenue Analysis; read-only.

    Returns the revenue contribution of every value of one dimension inside the
    half-open period, ordered by descending amount then value, so the ordering is
    deterministic for equal amounts. ``PRODUCT``, ``PRODUCT_VARIANT`` and
    ``PRODUCT_CATEGORY`` are item-based; the others use order totals.
    ``CAMPAIGN`` rows come only from the platform-reported ``REPORTED_ORDER``
    links of T-001 and ``CUSTOMER_SEGMENT`` rows from canonical customer tags, so
    those two breakdowns are NOT additive — one order can appear in several rows.
    ``PRODUCT_CATEGORY`` and ``CUSTOMER`` rows are returned with
    ``recordable=False`` because the snapshot contract defines no such dimension.
    """
    _require_positive_id(business_id, "business_id")
    breakdown = _require_breakdown(breakdown)
    start, end = _require_bounds(period_start, period_end)
    currency = _require_currency(currency)
    limit = _require_limit(limit)
    if breakdown == BREAKDOWN_CURRENCY and currency is not None:
        raise RevenueValidationError(
            "The CURRENCY breakdown is the per-currency view itself; it cannot "
            "also be filtered to one currency. Use the CURRENCY dimension on the "
            "scoped calculations for that."
        )
    with transaction.atomic():
        business = _require_business(business_id)
        observed, _ = _distinct_currencies(
            _order_period_filter(
                models.Order.objects.filter(business_id=business_id), start, end
            )
        )
        if breakdown == BREAKDOWN_CURRENCY:
            # Every row is exactly one currency, so no cross-currency sum can
            # occur and no single scope has to be resolved for the whole view.
            currency_scope = CurrencyScope(
                currency="", source=CURRENCY_SOURCE_PER_ROW, observed=observed
            )
        else:
            currency_scope = _resolve_currency(
                business, currency, None, None, observed
            )
        return _breakdown(business, start, end, breakdown, currency_scope, limit)


# --------------------------------------------------------------------------
# Recording operations
# --------------------------------------------------------------------------

def _inputs(coverage, **extra):
    """Snapshot inputs: the figure's own terms plus the full coverage report."""
    payload = dict(coverage)
    payload.update(extra)
    return payload


def _record(business_id, metric_key, basis, value, period_type, start, end,
            dimension_type, dimension_value, inputs):
    rule = get_calculation_rule(metric_key=metric_key, basis=basis)
    if not rule.records:
        raise RevenueDefinitionError(
            f"{rule.rule} is reconciliation output and must never be recorded."
        )
    return metrics.record_metric_snapshot(
        business_id=business_id,
        metric_key=metric_key,
        value=value,
        period_type=period_type,
        period_start=start,
        period_end=end,
        dimension_type=dimension_type,
        dimension_value=dimension_value,
        calculation_rule=rule.rule,
        inputs=_inputs(inputs, calculation_rule_eligibility=rule.eligibility),
    )


def _require_business_wide_currency_compatible(
        business_id, metric_keys, period_type, start, end, currency):
    """Refuse to reinterpret one dimensionless amount identity in a new currency."""
    rows = models.MetricSnapshot.objects.select_for_update().filter(
        business_id=business_id,
        metric__business_id=business_id,
        metric__key__in=sorted(metric_keys),
        period_type=period_type,
        period_start=start,
        period_end=end,
        dimension_type__isnull=True,
        dimension_value__isnull=True,
    ).order_by("pk")
    for row in rows:
        metadata = row.metadata if isinstance(row.metadata, dict) else {}
        inputs = metadata.get("inputs")
        existing_currency = (
            inputs.get("currency") if isinstance(inputs, dict) else None
        )
        if existing_currency != currency:
            raise RevenueValidationError(
                "A business-wide amount observation already occupies this "
                f"period in currency {existing_currency or '(unknown)'}; it "
                f"cannot be overwritten with currency {currency}. Use the "
                "CURRENCY dimension to record separate currency observations."
            )


def record_sales_metrics(*, business_id, period_type, period_start, period_end,
                         currency=None, dimension_type=None, dimension_value=None):
    """§2 Sales Metrics for one scope and period; no authorization is performed.

    Records total orders, units sold, average order value and the cancellation
    rate in one transaction. Average order value is ``UNAVAILABLE`` when no
    eligible order exists and the cancellation rate is ``UNAVAILABLE`` when no
    order was counted, so a zero denominator never becomes a zero observation.
    Counts of 0 ARE recorded: the population query was complete and an empty
    period is a measured zero. The metric registry must already be synchronized
    for this business (``metrics.sync_metric_registry``).
    """
    _require_positive_id(business_id, "business_id")
    period_type = _require_period_type(period_type)
    start, end = _require_bounds(period_start, period_end)
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    currency = _require_currency(currency)
    with transaction.atomic():
        business = _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        observed, _ = _distinct_currencies(
            _order_period_filter(
                _scoped_orders(business_id, dimension_type, dimension_value), start, end
            )
        )
        currency_scope = _resolve_currency(
            business, currency, dimension_type, dimension_value, observed
        )
        orders = _order_revenue(
            business, start, end, dimension_type, dimension_value, currency_scope
        )
        basis = orders.scope.basis
        coverage = orders.coverage

        average = (
            metrics.UNAVAILABLE if orders.eligible_orders == 0
            else _divide(orders.gross_amount, Decimal(orders.eligible_orders))
        )
        cancellation = (
            metrics.UNAVAILABLE if orders.counted_orders == 0
            else _divide(Decimal(orders.cancelled_orders), Decimal(orders.counted_orders))
        )
        if dimension_type is None and average is not metrics.UNAVAILABLE:
            _require_business_wide_currency_compatible(
                business_id, (_METRIC_AVERAGE_ORDER_VALUE,), period_type,
                start, end, currency_scope.currency,
            )
        results = {
            _METRIC_TOTAL_ORDERS: _record(
                business_id, _METRIC_TOTAL_ORDERS, basis, Decimal(orders.counted_orders),
                period_type, start, end, dimension_type, dimension_value,
                _inputs(coverage, counted_orders=orders.counted_orders),
            ),
            _METRIC_UNITS_SOLD: _record(
                business_id, _METRIC_UNITS_SOLD, basis, Decimal(orders.units_sold),
                period_type, start, end, dimension_type, dimension_value,
                _inputs(coverage, units_sold=orders.units_sold,
                        eligible_orders=orders.eligible_orders),
            ),
            _METRIC_AVERAGE_ORDER_VALUE: _record(
                business_id, _METRIC_AVERAGE_ORDER_VALUE, basis, average,
                period_type, start, end, dimension_type, dimension_value,
                _inputs(coverage, numerator_gross_amount=orders.gross_amount,
                        denominator_eligible_orders=orders.eligible_orders),
            ),
            _METRIC_CANCELLATION_RATE: _record(
                business_id, _METRIC_CANCELLATION_RATE, basis, cancellation,
                period_type, start, end, dimension_type, dimension_value,
                _inputs(coverage, numerator_cancelled_orders=orders.cancelled_orders,
                        denominator_counted_orders=orders.counted_orders),
            ),
        }
        return MetricWriteSet(
            scope=orders.scope, results=MappingProxyType(results)
        )


def record_revenue_metrics(*, business_id, period_type, period_start, period_end,
                           currency=None, dimension_type=None, dimension_value=None):
    """§2 Revenue Metrics and §6 Total Revenue / Refund Impact for one scope.

    Records gross revenue (order basis), refunded revenue, net revenue and
    revenue per customer in one transaction and one currency scope. Revenue per
    customer is ``UNAVAILABLE`` when the period has no resolved customer with an
    eligible order. The payment basis is computed for the reconciliation report
    but never recorded, so ``revenue_gross`` keeps one meaning per scope. The
    metric registry must already be synchronized for this business.
    """
    _require_positive_id(business_id, "business_id")
    period_type = _require_period_type(period_type)
    start, end = _require_bounds(period_start, period_end)
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    currency = _require_currency(currency)
    with transaction.atomic():
        business = _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        currency_scope = _joint_currency_scope(
            business, start, end, dimension_type, dimension_value, currency
        )
        reconciliation = _reconcile(
            business, start, end, dimension_type, dimension_value, currency_scope
        )
        orders = reconciliation.orders
        basis = orders.scope.basis
        coverage = reconciliation.coverage

        per_customer = (
            metrics.UNAVAILABLE if orders.distinct_customers == 0
            else _divide(orders.gross_amount, Decimal(orders.distinct_customers))
        )
        if dimension_type is None:
            _require_business_wide_currency_compatible(
                business_id,
                (
                    _METRIC_REVENUE_GROSS,
                    METRIC_REVENUE_REFUNDED,
                    METRIC_REVENUE_NET,
                    METRIC_REVENUE_PER_CUSTOMER,
                ),
                period_type, start, end, currency_scope.currency,
            )
        gross_coverage = dict(orders.coverage)
        gross_coverage.update(reconciliation.payments.coverage)
        results = {
            _METRIC_REVENUE_GROSS: _record(
                business_id, _METRIC_REVENUE_GROSS, basis, orders.gross_amount,
                period_type, start, end, dimension_type, dimension_value,
                _inputs(gross_coverage, gross_amount=orders.gross_amount,
                        accepted_amount=orders.accepted_amount,
                        reversed_amount=orders.reversed_amount),
            ),
            METRIC_REVENUE_REFUNDED: _record(
                business_id, METRIC_REVENUE_REFUNDED, basis,
                reconciliation.refunded_amount,
                period_type, start, end, dimension_type, dimension_value,
                _inputs(coverage, refunded_amount=reconciliation.refunded_amount),
            ),
            METRIC_REVENUE_NET: _record(
                business_id, METRIC_REVENUE_NET, basis, reconciliation.net_order_amount,
                period_type, start, end, dimension_type, dimension_value,
                _inputs(coverage, gross_amount=orders.gross_amount,
                        refunded_amount=reconciliation.refunded_amount,
                        net_amount=reconciliation.net_order_amount),
            ),
            METRIC_REVENUE_PER_CUSTOMER: _record(
                business_id, METRIC_REVENUE_PER_CUSTOMER, basis, per_customer,
                period_type, start, end, dimension_type, dimension_value,
                _inputs(coverage, numerator_gross_amount=orders.gross_amount,
                        denominator_distinct_customers=orders.distinct_customers),
            ),
        }
        return MetricWriteSet(
            scope=reconciliation.scope, results=MappingProxyType(results)
        )


def record_revenue_breakdown(*, business_id, breakdown, period_type, period_start,
                             period_end, currency=None, limit=None):
    """Record §6's revenue distribution for every value of one dimension.

    Writes ``revenue_gross`` per dimension value, plus ``sales_units_sold`` for
    the item-based product breakdowns. Rows whose dimension the snapshot contract
    cannot express (``PRODUCT_CATEGORY``, ``CUSTOMER``) are skipped and counted
    in ``skipped_rows`` instead of being stored under an unrelated dimension.
    ``revenue_refunded`` and ``revenue_net`` are deliberately NOT written per
    product: a refund is linked to a payment and an order, never to an order
    item, so an item-level refund figure does not exist in this schema.
    """
    _require_positive_id(business_id, "business_id")
    breakdown = _require_breakdown(breakdown)
    period_type = _require_period_type(period_type)
    start, end = _require_bounds(period_start, period_end)
    currency = _require_currency(currency)
    limit = _require_limit(limit)
    with transaction.atomic():
        summary = summarize_revenue_breakdown(
            business_id=business_id, breakdown=breakdown, period_start=start,
            period_end=end, currency=currency, limit=limit,
        )
        dimension_type = BREAKDOWN_DIMENSIONS[breakdown]
        if dimension_type is None:
            return BreakdownWriteSet(
                scope=summary.scope, breakdown=breakdown, results=(),
                skipped_rows=len(summary.rows),
            )
        written = []
        for row in summary.rows:
            inputs = _inputs(
                summary.coverage,
                dimension_value=row.dimension_value,
                row_gross_amount=row.gross_amount,
                row_order_count=row.order_count,
                row_units=row.units,
                breakdown_total_gross_amount=summary.total_gross_amount,
            )
            written.append((
                row.dimension_value,
                _METRIC_REVENUE_GROSS,
                _record(
                    business_id, _METRIC_REVENUE_GROSS, summary.basis, row.gross_amount,
                    period_type, start, end, dimension_type, row.dimension_value,
                    inputs,
                ),
            ))
            if summary.basis == BASIS_ORDER_ITEMS_ACCEPTED:
                written.append((
                    row.dimension_value,
                    _METRIC_UNITS_SOLD,
                    _record(
                        business_id, _METRIC_UNITS_SOLD, summary.basis,
                        Decimal(row.units), period_type, start, end, dimension_type,
                        row.dimension_value, inputs,
                    ),
                ))
        return BreakdownWriteSet(
            scope=summary.scope, breakdown=breakdown, results=tuple(written),
            skipped_rows=0,
        )


# --------------------------------------------------------------------------
# §6 Revenue Trend Analysis / §2 growth-rate metrics
# --------------------------------------------------------------------------

def _record_growth_rate(growth_metric_key, source_metric_key, *, business_id,
                        period_type, current_period_start, current_period_end,
                        previous_period_start, previous_period_end,
                        dimension_type, dimension_value):
    """Fractional change between two already-recorded observations of one scope."""
    _require_positive_id(business_id, "business_id")
    period_type = _require_period_type(period_type)
    current_start, current_end = _require_bounds(
        current_period_start, current_period_end
    )
    previous_start, previous_end = _require_bounds(
        previous_period_start, previous_period_end
    )
    if previous_end > current_start:
        raise RevenueValidationError(
            "previous_period_end must be at or before current_period_start, so "
            "the compared periods never overlap."
        )
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    basis = _basis_for_dimension(dimension_type)
    source_rule = get_calculation_rule(metric_key=source_metric_key, basis=basis)
    with transaction.atomic():
        _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        comparison = metrics.compare_metric_periods(
            business_id=business_id,
            metric_key=source_metric_key,
            period_type=period_type,
            current_period_start=current_start,
            current_period_end=current_end,
            previous_period_start=previous_start,
            previous_period_end=previous_end,
            dimension_type=dimension_type,
            dimension_value=dimension_value,
        )
        current = comparison.current
        previous = comparison.previous
        rule_mismatch = [
            observation.calculation_rule
            for observation in (current, previous)
            if observation is not None and observation.calculation_rule != source_rule.rule
        ]
        if rule_mismatch:
            raise RevenueScopeError(
                f"The recorded {source_metric_key} observations use rule(s) "
                f"{sorted(set(rule_mismatch))} instead of {source_rule.rule}; a "
                "growth rate may not mix two calculation bases."
            )
        unavailable_reason = None
        if current is None or previous is None:
            unavailable_reason = "MISSING_OBSERVATION"
        elif previous.value == 0:
            unavailable_reason = "ZERO_PREVIOUS_VALUE"

        if unavailable_reason is None:
            value = _divide(
                _subtract(current.value, previous.value), previous.value.copy_abs()
            )
        else:
            value = metrics.UNAVAILABLE

        inputs = {
            "source_metric_key": source_metric_key,
            "source_calculation_rule": source_rule.rule,
            "current_snapshot_id": None if current is None else current.snapshot_id,
            "previous_snapshot_id": None if previous is None else previous.snapshot_id,
            "current_value": None if current is None else current.value,
            "previous_value": None if previous is None else previous.value,
            "previous_period_start": previous_start.isoformat(),
            "previous_period_end": previous_end.isoformat(),
            "absolute_change": comparison.absolute_change,
            "direction": comparison.direction,
            "unavailable_reason": unavailable_reason or "NONE",
            "stored_as": "FRACTION_NOT_PERCENTAGE",
        }
        result = _record(
            business_id, growth_metric_key, basis, value, period_type,
            current_start, current_end, dimension_type, dimension_value, inputs,
        )
        return MetricWriteSet(
            scope=RevenueScope(
                business_id=business_id,
                period_start=current_start,
                period_end=current_end,
                dimension_type=dimension_type,
                dimension_value=dimension_value,
                currency="",
                currency_source="NOT_APPLICABLE_RATIO",
                basis=basis,
            ),
            results=MappingProxyType({growth_metric_key: result}),
        )


def record_sales_growth_rate(*, business_id, period_type, current_period_start,
                             current_period_end, previous_period_start,
                             previous_period_end, dimension_type=None,
                             dimension_value=None):
    """§2 sales growth: the fractional change of recorded total-orders observations.

    Both periods must already carry a recorded ``sales_total_orders`` observation
    written by this module with the same calculation rule, so the figure is
    reproducible and cites the two snapshots it used. A missing observation or a
    zero earlier value records ``UNAVAILABLE`` rather than 0 or a division error.
    The result is a fraction, not a percentage.
    """
    return _record_growth_rate(
        _METRIC_SALES_GROWTH_RATE, _METRIC_TOTAL_ORDERS,
        business_id=business_id, period_type=period_type,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        previous_period_start=previous_period_start,
        previous_period_end=previous_period_end,
        dimension_type=dimension_type, dimension_value=dimension_value,
    )


def record_revenue_growth_rate(*, business_id, period_type, current_period_start,
                               current_period_end, previous_period_start,
                               previous_period_end, dimension_type=None,
                               dimension_value=None):
    """§6 Revenue Trend Analysis: fractional change of recorded net revenue.

    Uses the ``revenue_net`` observations this module recorded for both periods,
    so the trend is reproducible from stored observations instead of being
    recalculated from canonical data twice. Missing observations or a zero
    earlier value record ``UNAVAILABLE``. The result is a fraction, not a
    percentage.
    """
    return _record_growth_rate(
        METRIC_REVENUE_GROWTH_RATE, METRIC_REVENUE_NET,
        business_id=business_id, period_type=period_type,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        previous_period_start=previous_period_start,
        previous_period_end=previous_period_end,
        dimension_type=dimension_type, dimension_value=dimension_value,
    )


# --------------------------------------------------------------------------
# §6 Revenue Change Detection
# --------------------------------------------------------------------------

CHANGE_DETECTION_METRICS = frozenset({
    _METRIC_REVENUE_GROSS, METRIC_REVENUE_REFUNDED, METRIC_REVENUE_NET,
    METRIC_REVENUE_PER_CUSTOMER, _METRIC_TOTAL_ORDERS, _METRIC_UNITS_SOLD,
    _METRIC_AVERAGE_ORDER_VALUE,
})


def detect_revenue_change(*, business_id, period_type, current_period_start,
                          current_period_end, metric_key=METRIC_REVENUE_NET,
                          previous_period_start=None, previous_period_end=None,
                          baseline_window_start=None, baseline_window_end=None,
                          dimension_type=None, dimension_value=None,
                          significant_change_ratio=None,
                          significant_absolute_change=None):
    """§6 Revenue Change Detection; read-only, and significance is never ours.

    Compares the recorded observation of ``current_period_*`` either with the
    caller's explicit previous comparison period or with the mean of the
    observations recorded inside the caller's explicit baseline window. Exactly
    one of the two comparison inputs must be given. No period arithmetic is
    performed here: the reporting timezone that would define an aligned previous
    day or month is an open team question, so the caller supplies the bounds.

    Significance is expressed only through ``significant_change_ratio`` (a
    fraction) and/or ``significant_absolute_change``; when neither is supplied
    ``is_significant`` is None and the criteria read ``NOT_SUPPLIED``. Choosing a
    default threshold belongs to the configurable anomaly rules of T-010, and
    turning the result into a statement belongs to the facts and issues of T-011.
    Nothing is written: the returned observation ids are the evidence those
    tickets cite.
    """
    _require_positive_id(business_id, "business_id")
    period_type = _require_period_type(period_type)
    current_start, current_end = _require_bounds(
        current_period_start, current_period_end
    )
    if not isinstance(metric_key, str) or metric_key not in CHANGE_DETECTION_METRICS:
        raise RevenueValidationError(
            "metric_key must be one of the observations this module records: "
            f"{sorted(CHANGE_DETECTION_METRICS)}."
        )
    dimension_type, dimension_value = _require_dimension(
        dimension_type, dimension_value, ORDER_SCOPE_DIMENSIONS
    )
    ratio_threshold = _require_non_negative_decimal(
        significant_change_ratio, "significant_change_ratio"
    )
    absolute_threshold = _require_non_negative_decimal(
        significant_absolute_change, "significant_absolute_change"
    )
    previous_given = (previous_period_start, previous_period_end) != (None, None)
    baseline_given = (baseline_window_start, baseline_window_end) != (None, None)
    if previous_given == baseline_given:
        raise RevenueValidationError(
            "Provide exactly one comparison input: a previous period pair or a "
            "baseline window pair."
        )
    basis = _basis_for_dimension(dimension_type)
    rule = get_calculation_rule(metric_key=metric_key, basis=basis)

    with transaction.atomic():
        _require_business(business_id)
        _require_dimension_scope(business_id, dimension_type, dimension_value)
        current = metrics.get_metric_snapshot(
            business_id=business_id, metric_key=metric_key, period_type=period_type,
            period_start=current_start, period_end=current_end,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )
        if current is not None and current.calculation_rule != rule.rule:
            raise RevenueScopeError(
                f"The recorded observation uses rule {current.calculation_rule} "
                f"instead of {rule.rule}; a change may not mix two bases."
            )
        previous = None
        baseline_value = None
        baseline_ids = ()
        if previous_given:
            comparison_basis = COMPARISON_PREVIOUS_PERIOD
            previous_start, previous_end = _require_bounds(
                previous_period_start, previous_period_end
            )
            if previous_end > current_start:
                raise RevenueValidationError(
                    "previous_period_end must be at or before current_period_start."
                )
            comparison = metrics.compare_metric_periods(
                business_id=business_id, metric_key=metric_key,
                period_type=period_type,
                current_period_start=current_start, current_period_end=current_end,
                previous_period_start=previous_start, previous_period_end=previous_end,
                dimension_type=dimension_type, dimension_value=dimension_value,
            )
            previous = comparison.previous
            if previous is not None and previous.calculation_rule != rule.rule:
                raise RevenueScopeError(
                    f"The recorded previous observation uses rule "
                    f"{previous.calculation_rule} instead of {rule.rule}."
                )
            reference = None if previous is None else previous.value
            absolute_change = comparison.absolute_change
            direction = comparison.direction
        else:
            comparison_basis = COMPARISON_BASELINE_MEAN
            window_start, window_end = _require_bounds(
                baseline_window_start, baseline_window_end
            )
            if window_end > current_start:
                raise RevenueValidationError(
                    "baseline_window_end must be at or before "
                    "current_period_start, so the baseline never includes the "
                    "period under test."
                )
            observations = metrics.list_metric_snapshots(
                business_id=business_id, metric_key=metric_key,
                period_type=period_type, dimension_type=dimension_type,
                dimension_value=dimension_value, window_start=window_start,
                window_end=window_end, calculation_rule=rule.rule,
            )
            baseline_ids = tuple(
                observation.snapshot_id for observation in observations
            )
            if observations:
                total, _ = _sum_amounts(
                    [observation.value for observation in observations]
                )
                baseline_value = _divide(total, Decimal(len(observations)))
            reference = baseline_value
            if current is None or reference is None:
                absolute_change = None
                direction = metrics.DIRECTION_UNAVAILABLE
            else:
                absolute_change = _subtract(current.value, reference)
                if absolute_change > 0:
                    direction = metrics.DIRECTION_INCREASED
                elif absolute_change < 0:
                    direction = metrics.DIRECTION_DECREASED
                else:
                    direction = metrics.DIRECTION_UNCHANGED

        relative_change = None
        if absolute_change is not None and reference is not None and reference != 0:
            relative_change = _divide(absolute_change, reference.copy_abs())

        criteria = {
            "significant_change_ratio": ratio_threshold,
            "significant_absolute_change": absolute_threshold,
            "threshold_source": SIGNIFICANCE_NOT_SUPPLIED,
        }
        triggered = []
        if ratio_threshold is not None:
            criteria["threshold_source"] = "CALLER_SUPPLIED"
            if relative_change is not None:
                triggered.append(relative_change.copy_abs() >= ratio_threshold)
        if absolute_threshold is not None:
            criteria["threshold_source"] = "CALLER_SUPPLIED"
            if absolute_change is not None:
                triggered.append(absolute_change.copy_abs() >= absolute_threshold)
        is_significant = any(triggered) if triggered else None
        criteria["evaluated_criteria"] = len(triggered)
        if relative_change is None:
            criteria["relative_change_unavailable_reason"] = (
                "MISSING_OBSERVATION" if absolute_change is None
                else "ZERO_REFERENCE_VALUE"
            )

        return RevenueChangeDetection(
            metric_key=metric_key,
            calculation_rule=rule.rule,
            period_type=period_type,
            dimension_type=dimension_type,
            dimension_value=dimension_value,
            comparison_basis=comparison_basis,
            current=current,
            previous=previous,
            baseline_value=baseline_value,
            baseline_observation_ids=baseline_ids,
            absolute_change=absolute_change,
            relative_change=relative_change,
            direction=direction,
            is_significant=is_significant,
            significance_criteria=MappingProxyType(criteria),
        )
