"""BI §6 Revenue Analysis and the §2 Sales / Revenue metric families (T-003).

Every test drives the public ``revenue`` service with original canonical rows
(orders, items, payments, refunds, customers, campaigns, T-001 relationships)
and reads the result back from the §3 snapshot store. Findings, thresholds and
LLM wording are out of scope. The only patched collaborator is the snapshot
service clock, so replay timestamps can be told apart.

Expected values are derived from the specification and the module's documented
contract (revenue.py docstring), not from running the code. Tests marked
``SPEC:`` assert behaviour the documentation requires even where the current
implementation may disagree; a failure there is a suspected product defect, not
a test error.
"""

import dataclasses
import inspect
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from app import models
from app.business_intelligence import metrics, relationships, revenue

D = Decimal
UTC = timezone.utc

STAMP = datetime(2026, 9, 1, tzinfo=UTC)  # ingestion time of every fixture row
START = datetime(2026, 10, 10, tzinfo=UTC)
DAY = timedelta(days=1)
END = START + DAY
MID = START + timedelta(hours=12)
CLOCK_A = datetime(2026, 10, 20, 8, tzinfo=UTC)
CLOCK_B = datetime(2026, 10, 21, 9, tzinfo=UTC)
NOW = "app.business_intelligence.metrics.timezone.now"

TOTAL_ORDERS = "bi.metric.sales_total_orders.v1"
UNITS_SOLD = "bi.metric.sales_units_sold.v1"
AOV = "bi.metric.sales_average_order_value.v1"
CANCELLATION = "bi.metric.sales_cancellation_rate.v1"
SALES_GROWTH = "bi.metric.sales_growth_rate.v1"
GROSS = "bi.metric.revenue_gross.v1"
REFUNDED = "bi.metric.revenue_refunded.v1"
NET = "bi.metric.revenue_net.v1"
PER_CUSTOMER = "bi.metric.revenue_per_customer.v1"
REVENUE_GROWTH = "bi.metric.revenue_growth_rate.v1"
MARKETING_ATTRIBUTED = "bi.metric.marketing_attributed_revenue.v1"

SALES_KEYS = (TOTAL_ORDERS, UNITS_SOLD, AOV, CANCELLATION)
REVENUE_KEYS = (GROSS, REFUNDED, NET, PER_CUSTOMER)

ORDERS = revenue.BASIS_ORDERS_ACCEPTED
CAMPAIGN_ORDERS = revenue.BASIS_REPORTED_CAMPAIGN_ORDERS
ITEMS = revenue.BASIS_ORDER_ITEMS_ACCEPTED

CALCULATIONS = (
    "compute_order_revenue", "compute_payment_receipts",
    "compute_refund_impact", "reconcile_revenue",
)
RECORDINGS = ("record_sales_metrics", "record_revenue_metrics")
BREAKDOWNS = ("summarize_revenue_breakdown", "record_revenue_breakdown")
NEEDS_PERIOD_TYPE = RECORDINGS + ("record_revenue_breakdown",)


def day(index):
    return START + index * DAY, START + (index + 1) * DAY


def at(index, hours=12):
    return START + index * DAY + timedelta(hours=hours)


def rule(metric_key, basis=ORDERS):
    return revenue.get_calculation_rule(metric_key=metric_key, basis=basis).rule


# ==========================================================================
# Closed vocabulary and calculation-rule table (no database)
# ==========================================================================

class VocabularyAndRuleTableTests(SimpleTestCase):
    """Status vocabulary is exactly business-data.md lines 110 and 145."""

    def test_order_status_sets_match_business_data_line_110(self):
        self.assertEqual(revenue.COUNTED_ORDER_STATUSES, frozenset({
            "PENDING", "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED",
            "CANCELLED", "RETURNED", "REFUNDED",
        }))
        self.assertEqual(revenue.REVENUE_ELIGIBLE_ORDER_STATUSES, frozenset({
            "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "RETURNED", "REFUNDED",
        }))
        self.assertEqual(revenue.ORDER_STATUSES_CANCELLED, frozenset({"CANCELLED"}))
        self.assertTrue(
            revenue.ORDER_STATUSES_CANCELLED.isdisjoint(
                revenue.REVENUE_ELIGIBLE_ORDER_STATUSES
            )
        )
        self.assertNotIn("PENDING", revenue.REVENUE_ELIGIBLE_ORDER_STATUSES)
        self.assertLessEqual(
            revenue.REVENUE_ELIGIBLE_ORDER_STATUSES, revenue.COUNTED_ORDER_STATUSES
        )

    def test_payment_received_statuses_match_business_data_line_145(self):
        self.assertEqual(
            revenue.PAYMENT_STATUSES_RECEIVED,
            frozenset({"PAID", "PARTIALLY_REFUNDED", "REFUNDED"}),
        )
        for status in ("AUTHORIZED", "PENDING", "FAILED", "CANCELLED"):
            with self.subTest(status=status):
                self.assertNotIn(status, revenue.PAYMENT_STATUSES_RECEIVED)

    def test_bases_and_comparison_vocabulary(self):
        self.assertEqual(revenue.BASES, frozenset({
            "ORDERS_ACCEPTED", "REPORTED_CAMPAIGN_ORDERS",
            "ORDER_ITEMS_ACCEPTED", "PAYMENTS_RECEIVED",
        }))
        self.assertEqual(revenue.COMPARISON_PREVIOUS_PERIOD, "PREVIOUS_PERIOD")
        self.assertEqual(revenue.COMPARISON_BASELINE_MEAN, "BASELINE_MEAN")

    def test_breakdown_selectors_map_to_snapshot_dimensions_or_none(self):
        self.assertEqual(dict(revenue.BREAKDOWN_DIMENSIONS), {
            "PRODUCT": "PRODUCT", "PRODUCT_VARIANT": "PRODUCT_VARIANT",
            "CAMPAIGN": "CAMPAIGN", "CHANNEL": "CHANNEL",
            "CUSTOMER_SEGMENT": "CUSTOMER_SEGMENT", "CURRENCY": "CURRENCY",
            "PRODUCT_CATEGORY": None, "CUSTOMER": None,
        })
        for dimension in revenue.BREAKDOWN_DIMENSIONS.values():
            if dimension is not None:
                self.assertIn(dimension, metrics.DIMENSION_TYPES)

    def test_exported_metric_constants_are_the_registry_keys(self):
        self.assertEqual(revenue.METRIC_REVENUE_REFUNDED, REFUNDED)
        self.assertEqual(revenue.METRIC_REVENUE_NET, NET)
        self.assertEqual(revenue.METRIC_REVENUE_PER_CUSTOMER, PER_CUSTOMER)
        self.assertEqual(revenue.METRIC_REVENUE_GROWTH_RATE, REVENUE_GROWTH)
        self.assertEqual(
            revenue.SALES_METRIC_KEYS,
            (TOTAL_ORDERS, UNITS_SOLD, AOV, CANCELLATION, SALES_GROWTH),
        )

    def test_rule_table_is_closed_unique_and_registry_backed(self):
        seen = {}
        for (metric_key, basis), definition in revenue.CALCULATION_RULES.items():
            with self.subTest(metric_key=metric_key, basis=basis):
                self.assertIn(metric_key, metrics.METRIC_DEFINITIONS)
                self.assertIn(basis, revenue.BASES)
                self.assertEqual(definition.rule, f"{metric_key}.{definition.variant}")
                self.assertNotIn(definition.rule, seen)
                seen[definition.rule] = definition
                self.assertTrue(definition.eligibility.strip())
                self.assertLessEqual(
                    len(definition.rule),
                    models.MetricSnapshot._meta.get_field("calculation_rule").max_length,
                )
        self.assertEqual(len(seen), len(revenue.CALCULATION_RULES))

    def test_only_sales_and_revenue_metrics_have_rules(self):
        for metric_key in {key for key, _ in revenue.CALCULATION_RULES}:
            with self.subTest(metric_key=metric_key):
                self.assertIn(
                    metrics.METRIC_DEFINITIONS[metric_key].category, {"SALES", "REVENUE"}
                )
                self.assertNotIn("attributed", metric_key)

    def test_get_calculation_rule_returns_the_documented_strings(self):
        self.assertEqual(
            rule(NET), "bi.metric.revenue_net.v1.orders_accepted_less_refunds"
        )
        self.assertEqual(
            rule(GROSS, CAMPAIGN_ORDERS),
            "bi.metric.revenue_gross.v1.reported_campaign_orders",
        )
        self.assertEqual(
            rule(GROSS, ITEMS), "bi.metric.revenue_gross.v1.order_items_accepted"
        )
        self.assertEqual(
            rule(TOTAL_ORDERS), "bi.metric.sales_total_orders.v1.orders_placed_all_statuses"
        )

    def test_payment_basis_rules_are_reconciliation_only(self):
        payments = [
            definition for (_, basis), definition in revenue.CALCULATION_RULES.items()
            if basis == revenue.BASIS_PAYMENTS_RECEIVED
        ]
        self.assertEqual(
            sorted(definition.rule for definition in payments),
            [
                "bi.metric.revenue_gross.v1.payments_received",
                "bi.metric.revenue_net.v1.payments_received_less_refunds",
            ],
        )
        for definition in payments:
            self.assertFalse(definition.records)
        for (_, basis), definition in revenue.CALCULATION_RULES.items():
            if basis != revenue.BASIS_PAYMENTS_RECEIVED:
                self.assertTrue(definition.records)

    def test_get_calculation_rule_rejects_unknown_pairs_and_non_strings(self):
        bad = [
            (UNITS_SOLD, "PAYMENTS_RECEIVED"),
            (CANCELLATION, ITEMS),
            ("bi.metric.nope.v1", ORDERS),
            (GROSS, "orders_accepted"),
            (None, ORDERS),
            (GROSS, None),
            (5, ORDERS),
        ]
        for metric_key, basis in bad:
            with self.subTest(metric_key=metric_key, basis=basis):
                with self.assertRaises(revenue.RevenueValidationError):
                    revenue.get_calculation_rule(metric_key=metric_key, basis=basis)

    def test_exception_hierarchy(self):
        self.assertTrue(issubclass(revenue.RevenueValidationError, ValueError))
        self.assertTrue(
            issubclass(revenue.RevenueCurrencyMixError, revenue.RevenueValidationError)
        )
        self.assertTrue(
            issubclass(revenue.RevenueScopeError, revenue.RevenueValidationError)
        )
        self.assertTrue(issubclass(revenue.RevenueDefinitionError, ValueError))
        self.assertFalse(
            issubclass(revenue.RevenueDefinitionError, revenue.RevenueValidationError)
        )

    def test_no_default_significance_threshold_exists_anywhere(self):
        signature = inspect.signature(revenue.detect_revenue_change)
        for name in ("significant_change_ratio", "significant_absolute_change"):
            with self.subTest(parameter=name):
                self.assertIsNone(signature.parameters[name].default)
        self.assertEqual(
            [name for name in dir(revenue) if "THRESHOLD" in name.upper()], []
        )
        self.assertEqual(revenue.SIGNIFICANCE_NOT_SUPPLIED, "NOT_SUPPLIED")


# ==========================================================================
# Shared fixtures
# ==========================================================================

class RevenueTestCase(TestCase):
    """Two synchronized businesses plus small deterministic row builders."""

    def setUp(self):
        self.business = self.make_business("Fixture shop", "fixture-shop")
        self.other = self.make_business("Other shop", "other-shop")

    # -- builders ---------------------------------------------------------

    def make_business(self, name, slug, currency="BDT", sync=True):
        business = models.Business.objects.create(
            name=name, slug=slug, currency=currency, created_at=STAMP, updated_at=STAMP,
        )
        if sync:
            metrics.sync_metric_registry(business_id=business.pk)
        return business

    def order(self, status="DELIVERED", total="100.00", *, at=MID, currency="BDT",
              business=None, customer=None, connection=None):
        row = models.Order.objects.create(
            business=business or self.business, customer=customer,
            integration_connection=connection, status=status, currency=currency,
            subtotal=D(total), total_amount=D(total), ordered_at=at,
            created_at=MID, updated_at=MID,
        )
        models.Order.objects.filter(pk=row.pk).update(created_at=MID, updated_at=MID)
        row.refresh_from_db()
        return row

    def bulk_orders(self, status, count, *, at=MID):
        models.Order.objects.bulk_create([
            models.Order(
                business=self.business, status=status, currency="BDT",
                ordered_at=at, created_at=MID, updated_at=MID,
            )
            for _ in range(count)
        ])

    def item(self, order, product=None, quantity=1, total="10.00", variant=None):
        if quantity <= 0:
            from django.db import connection
            if connection.vendor == 'sqlite':
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA ignore_check_constraints = ON")
                    cursor.execute(
                        "INSERT INTO order_items (order_id, product_id, product_variant_id, product_name, quantity, unit_price, discount_amount, total_amount, created_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s)",
                        [order.pk, product.pk if product else None, variant.pk if variant else None, "Fixture item", quantity, str(total), str(total), STAMP]
                    )
                    cursor.execute("PRAGMA ignore_check_constraints = OFF")
                    item_id = cursor.lastrowid
                return models.OrderItem.objects.get(pk=item_id)
        return models.OrderItem.objects.create(
            order=order, product=product, product_variant=variant,
            product_name="Fixture item", quantity=quantity, unit_price=D(total),
            total_amount=D(total), created_at=STAMP,
        )

    def payment(self, order=None, status="PAID", amount="100.00", *, currency="BDT",
                paid_at=MID, business=None):
        return models.Payment.objects.create(
            business=business or self.business, order=order, status=status,
            amount=D(amount), currency=currency, paid_at=paid_at,
            created_at=STAMP, updated_at=STAMP,
        )

    def refund(self, payment, amount="10.00", *, order=None, currency="BDT",
               at=MID, status="COMPLETED"):
        return models.Refund.objects.create(
            payment=payment, order=order, amount=D(amount), currency=currency,
            status=status, refunded_at=at, created_at=STAMP, updated_at=STAMP,
        )

    def product(self, name="Widget", *, business=None, category=None):
        return models.Product.objects.create(
            business=business or self.business, name=name, category=category,
            created_at=STAMP, updated_at=STAMP,
        )

    def variant(self, product, name="Variant"):
        return models.ProductVariant.objects.create(
            product=product, name=name, created_at=STAMP, updated_at=STAMP,
        )

    def customer(self, *, business=None):
        return models.Customer.objects.create(
            business=business or self.business, created_at=STAMP, updated_at=STAMP,
        )

    def tag(self, customer, label):
        return models.CustomerTag.objects.create(
            customer=customer, tag=label, created_at=STAMP,
        )

    def connection(self, source_key, *, business=None):
        source, _ = models.IntegrationSource.objects.get_or_create(
            key=source_key,
            defaults=dict(
                name=source_key, category="COMMERCE", created_at=STAMP, updated_at=STAMP,
            ),
        )
        return models.IntegrationConnection.objects.create(
            business=business or self.business, integration_source=source,
            created_at=STAMP, updated_at=STAMP,
        )

    def campaign(self, name="Campaign", *, business=None):
        return models.Campaign.objects.create(
            business=business or self.business, name=name, platform="META",
            created_at=STAMP, updated_at=STAMP,
        )

    def convert(self, campaign, order, *, external=None):
        return models.CampaignConversion.objects.create(
            campaign=campaign, order=order, conversion_type="PURCHASE",
            converted_at=MID, external_conversion_id=external, created_at=STAMP,
        )

    def rebuild(self, business=None):
        return relationships.rebuild_relationships(
            business_id=(business or self.business).pk
        )

    # -- service shortcuts --------------------------------------------------

    def call(self, name, **overrides):
        params = {
            "business_id": self.business.pk, "period_start": START, "period_end": END,
        }
        if name in NEEDS_PERIOD_TYPE:
            params["period_type"] = "DAY"
        if name in BREAKDOWNS:
            params["breakdown"] = "PRODUCT"
        params.update(overrides)
        return getattr(revenue, name)(**params)

    def calc(self, **overrides):
        return self.call("compute_order_revenue", **overrides)

    def sales(self, **overrides):
        return self.call("record_sales_metrics", **overrides)

    def revenue_metrics(self, **overrides):
        return self.call("record_revenue_metrics", **overrides)

    def breakdown(self, name, **overrides):
        return self.call("summarize_revenue_breakdown", breakdown=name, **overrides)

    def record_breakdown(self, name, **overrides):
        return self.call("record_revenue_breakdown", breakdown=name, **overrides)

    # -- snapshot reads -------------------------------------------------------

    def obs(self, key, *, start=START, end=END, dimension_type=None,
            dimension_value=None, period_type="DAY", business=None):
        return metrics.get_metric_snapshot(
            business_id=(business or self.business).pk, metric_key=key,
            period_type=period_type, period_start=start, period_end=end,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )

    def row(self, key, **scope):
        observation = self.obs(key, **scope)
        self.assertIsNotNone(observation, f"no snapshot was recorded for {key}")
        return models.MetricSnapshot.objects.get(pk=observation.snapshot_id)

    def inputs(self, key, **scope):
        return self.row(key, **scope).metadata["inputs"]

    def snapshot_count(self):
        return models.MetricSnapshot.objects.count()

    def seed(self, key, value, *, start, end, basis=ORDERS, dimension_type=None,
             dimension_value=None, calculation_rule="TABLE"):
        if calculation_rule == "TABLE":
            calculation_rule = rule(key, basis)
        return metrics.record_metric_snapshot(
            business_id=self.business.pk, metric_key=key, value=D(value),
            period_type="DAY", period_start=start, period_end=end,
            dimension_type=dimension_type, dimension_value=dimension_value,
            calculation_rule=calculation_rule,
        )

    # -- invariants -------------------------------------------------------------

    def assert_order_coverage_reconciles(self, coverage):
        """Nothing in the period is silently dropped from the coverage report."""
        self.assertEqual(
            coverage["orders_in_period"],
            coverage["counted_orders"] + coverage["unclassified_orders"]
            + coverage["orders_without_currency"] + coverage["orders_in_other_currency"],
        )

    def mixed_world(self):
        """BDT and USD money in the same business, period and scope."""
        self.o_bdt = self.order("DELIVERED", "100.00")
        self.o_usd = self.order("DELIVERED", "40.00", currency="USD")
        self.o_usd2 = self.order("CONFIRMED", "10.00", currency="USD")
        self.p_bdt = self.payment(self.o_bdt, "PAID", "60.00")
        self.p_usd = self.payment(self.o_usd, "PAID", "40.00", currency="USD")
        self.refund(self.p_bdt, "5.00", order=self.o_bdt)
        self.refund(self.p_usd, "4.00", order=self.o_usd, currency="USD")


# ==========================================================================
# 1. Exact decimals
# ==========================================================================

class ExactDecimalTests(RevenueTestCase):
    """Stored money has 2 places and snapshots 6: sums exact, divisions rounded."""

    def test_amount_sums_are_exact_decimal_and_never_binary_floats(self):
        for _ in range(10):
            self.order("DELIVERED", "0.10")
        for _ in range(2):
            self.order("CONFIRMED", "0.20")
        result = self.calc()
        self.assertIsInstance(result.gross_amount, Decimal)
        self.assertEqual(result.gross_amount, D("1.40"))
        self.assertEqual(result.accepted_amount, D("1.40"))
        self.revenue_metrics()
        self.assertEqual(self.obs(GROSS).value, D("1.400000"))
        self.assertNotIn("rounded_from", self.row(GROSS).metadata)

    def test_half_a_cent_average_is_exact_and_not_marked_rounded(self):
        self.order("DELIVERED", "0.01")
        self.order("DELIVERED", "0.00")
        self.sales()
        self.assertEqual(self.obs(AOV).value, D("0.005000"))
        self.assertNotIn("rounded_from", self.row(AOV).metadata)
        inputs = self.inputs(AOV)
        self.assertEqual(D(inputs["numerator_gross_amount"]), D("0.01"))
        self.assertEqual(inputs["denominator_eligible_orders"], 2)

    def test_one_third_is_quantized_to_six_places_and_keeps_the_exact_input(self):
        self.order("DELIVERED", "0.50")
        self.order("DELIVERED", "0.25")
        self.order("DELIVERED", "0.25")
        self.sales()
        self.assertEqual(self.obs(AOV).value, D("0.333333"))
        metadata = self.row(AOV).metadata
        exact = D(metadata["rounded_from"])
        self.assertGreater(exact, D("0.3333333333"))
        self.assertLess(exact, D("0.3333333334"))
        self.assertNotEqual(exact, D("0.333333"))
        self.assertEqual(D(metadata["inputs"]["numerator_gross_amount"]), D("1.00"))
        self.assertEqual(metadata["inputs"]["denominator_eligible_orders"], 3)

    def test_revenue_per_customer_one_third_is_rounded_with_exact_input_kept(self):
        for total in ("5.00", "3.00", "2.00"):
            self.order("DELIVERED", total, customer=self.customer())
        self.revenue_metrics()
        self.assertEqual(self.obs(PER_CUSTOMER).value, D("3.333333"))
        exact = D(self.row(PER_CUSTOMER).metadata["rounded_from"])
        self.assertGreater(exact, D("3.3333333333"))
        self.assertLess(exact, D("3.3333333334"))

    def test_cancellation_rate_tie_rounds_half_even_downwards(self):
        # 1 / 128 = 0.0078125 exactly: the seventh decimal is a tie after ...2.
        self.bulk_orders("CANCELLED", 1)
        self.bulk_orders("PENDING", 127)
        self.sales()
        self.assertEqual(self.obs(CANCELLATION).value, D("0.007812"))
        metadata = self.row(CANCELLATION).metadata
        self.assertEqual(D(metadata["rounded_from"]), D("0.0078125"))
        self.assertEqual(metadata["inputs"]["numerator_cancelled_orders"], 1)
        self.assertEqual(metadata["inputs"]["denominator_counted_orders"], 128)

    def test_cancellation_rate_tie_rounds_half_even_upwards(self):
        # 3 / 128 = 0.0234375 exactly: a tie after an odd digit rounds up.
        self.bulk_orders("CANCELLED", 3)
        self.bulk_orders("PENDING", 125)
        self.sales()
        self.assertEqual(self.obs(CANCELLATION).value, D("0.023438"))
        self.assertEqual(D(self.row(CANCELLATION).metadata["rounded_from"]), D("0.0234375"))

    def test_growth_rate_ties_follow_banker_rounding_and_preserve_the_input(self):
        base_start, base_end = day(0)
        self.seed(NET, "2.000000", start=base_start, end=base_end)
        self.seed(NET, "2.000005", start=day(1)[0], end=day(1)[1])
        self.seed(NET, "2.000007", start=day(2)[0], end=day(2)[1])
        cases = (
            (1, D("0.000002"), D("0.0000025")),
            (2, D("0.000004"), D("0.0000035")),
        )
        for index, stored, exact in cases:
            with self.subTest(index=index):
                result = revenue.record_revenue_growth_rate(
                    business_id=self.business.pk, period_type="DAY",
                    current_period_start=day(index)[0], current_period_end=day(index)[1],
                    previous_period_start=base_start, previous_period_end=base_end,
                )
                self.assertEqual(result.results[REVENUE_GROWTH].status, metrics.WRITE_CREATED)
                growth = self.obs(
                    REVENUE_GROWTH, start=day(index)[0], end=day(index)[1]
                )
                self.assertEqual(growth.value, stored)
                self.assertEqual(
                    D(self.row(
                        REVENUE_GROWTH, start=day(index)[0], end=day(index)[1]
                    ).metadata["rounded_from"]),
                    exact,
                )

    def test_growth_one_third_is_quantized_and_keeps_the_exact_input(self):
        self.seed(NET, "3", start=day(0)[0], end=day(0)[1])
        self.seed(NET, "4", start=day(1)[0], end=day(1)[1])
        revenue.record_revenue_growth_rate(
            business_id=self.business.pk, period_type="DAY",
            current_period_start=day(1)[0], current_period_end=day(1)[1],
            previous_period_start=day(0)[0], previous_period_end=day(0)[1],
        )
        scope = dict(start=day(1)[0], end=day(1)[1])
        self.assertEqual(self.obs(REVENUE_GROWTH, **scope).value, D("0.333333"))
        exact = D(self.row(REVENUE_GROWTH, **scope).metadata["rounded_from"])
        self.assertGreater(exact, D("0.3333333333"))
        self.assertLess(exact, D("0.3333333334"))


# ==========================================================================
# 2. Currency isolation
# ==========================================================================

class CurrencyIsolationTests(RevenueTestCase):

    def test_mixed_currencies_without_a_choice_raise_for_every_operation(self):
        self.mixed_world()
        for name in CALCULATIONS + RECORDINGS + BREAKDOWNS:
            with self.subTest(operation=name):
                with self.assertRaises(revenue.RevenueCurrencyMixError) as caught:
                    self.call(name)
                self.assertIn("BDT", str(caught.exception))
                self.assertIn("USD", str(caught.exception))
        self.assertEqual(self.snapshot_count(), 0)

    def test_a_currency_mix_is_a_validation_error_not_a_silent_total(self):
        self.mixed_world()
        with self.assertRaises(revenue.RevenueValidationError):
            self.calc()

    def test_caller_currency_selects_one_currency_and_counts_the_rest(self):
        self.mixed_world()
        result = self.calc(currency="USD")
        self.assertEqual(result.scope.currency, "USD")
        self.assertEqual(result.scope.currency_source, revenue.CURRENCY_SOURCE_CALLER)
        self.assertEqual(result.gross_amount, D("50.00"))
        self.assertEqual(result.counted_orders, 2)
        self.assertEqual(result.eligible_orders, 2)
        coverage = result.coverage
        self.assertEqual(coverage["orders_in_other_currency"], 1)
        self.assertEqual(coverage["orders_in_other_currency_amount"], D("100.00"))
        self.assertEqual(coverage["currencies_observed_in_scope"], ["BDT", "USD"])
        self.assert_order_coverage_reconciles(coverage)

        bdt = self.calc(currency="BDT")
        self.assertEqual(bdt.gross_amount, D("100.00"))
        self.assertEqual(bdt.coverage["orders_in_other_currency"], 2)
        self.assertEqual(bdt.coverage["orders_in_other_currency_amount"], D("50.00"))

    def test_currency_dimension_resolves_the_same_scope_as_the_caller_currency(self):
        self.mixed_world()
        by_caller = self.calc(currency="USD")
        by_dimension = self.calc(dimension_type="CURRENCY", dimension_value="USD")
        self.assertEqual(by_dimension.scope.currency, "USD")
        self.assertEqual(
            by_dimension.scope.currency_source, revenue.CURRENCY_SOURCE_DIMENSION
        )
        self.assertEqual(by_dimension.scope.dimension_type, "CURRENCY")
        self.assertEqual(by_dimension.gross_amount, by_caller.gross_amount)
        self.assertEqual(by_dimension.counted_orders, by_caller.counted_orders)

    def test_caller_currency_and_currency_dimension_must_agree(self):
        self.mixed_world()
        with self.assertRaises(revenue.RevenueValidationError) as caught:
            self.calc(currency="BDT", dimension_type="CURRENCY", dimension_value="USD")
        self.assertNotIsInstance(caught.exception, revenue.RevenueCurrencyMixError)
        agreeing = self.calc(
            currency="USD", dimension_type="CURRENCY", dimension_value="USD"
        )
        self.assertEqual(agreeing.gross_amount, D("50.00"))

    def test_every_money_basis_agrees_on_one_currency(self):
        self.mixed_world()
        reconciliation = self.call("reconcile_revenue", currency="USD")
        self.assertEqual(reconciliation.scope.currency, "USD")
        self.assertEqual(reconciliation.gross_order_amount, D("50.00"))
        self.assertEqual(reconciliation.received_payment_amount, D("40.00"))
        self.assertEqual(reconciliation.refunded_amount, D("4.00"))
        self.assertEqual(reconciliation.net_order_amount, D("46.00"))
        self.assertEqual(reconciliation.net_received_amount, D("36.00"))
        self.assertEqual(reconciliation.order_payment_difference, D("10.00"))
        self.assertEqual(reconciliation.coverage["payments_in_other_currency"], 1)
        self.assertEqual(reconciliation.coverage["refunds_in_other_currency"], 1)
        by_dimension = self.call(
            "reconcile_revenue", dimension_type="CURRENCY", dimension_value="USD"
        )
        self.assertEqual(by_dimension.net_order_amount, D("46.00"))
        self.assertEqual(by_dimension.net_received_amount, D("36.00"))

    def test_recording_in_one_currency_writes_that_currency_only(self):
        self.mixed_world()
        self.revenue_metrics(currency="USD")
        self.assertEqual(self.obs(GROSS).value, D("50.000000"))
        self.assertEqual(self.obs(REFUNDED).value, D("4.000000"))
        self.assertEqual(self.obs(NET).value, D("46.000000"))
        inputs = self.inputs(GROSS)
        self.assertEqual(inputs["currency"], "USD")
        self.assertEqual(inputs["currency_source"], "CALLER")

    def test_currency_dimension_records_each_currency_under_its_own_identity(self):
        self.mixed_world()
        for code, gross in (("USD", "50.000000"), ("BDT", "100.000000")):
            with self.subTest(currency=code):
                self.revenue_metrics(dimension_type="CURRENCY", dimension_value=code)
                observation = self.obs(
                    GROSS, dimension_type="CURRENCY", dimension_value=code
                )
                self.assertEqual(observation.value, D(gross))
        self.assertIsNone(self.obs(GROSS))  # no business-wide row was invented

    def test_a_stray_payment_in_another_currency_blocks_recording_until_named(self):
        """All three money sides resolve into one scope before anything is written."""
        order = self.order("DELIVERED", "100.00")
        self.payment(order, "PAID", "100.00")
        self.payment(None, "PAID", "9.00", currency="USD")
        self.assertEqual(self.calc().scope.currency, "BDT")  # orders alone are unambiguous
        with self.assertRaises(revenue.RevenueCurrencyMixError):
            self.revenue_metrics()
        self.assertEqual(self.snapshot_count(), 0)
        self.revenue_metrics(currency="BDT")
        self.assertEqual(self.obs(GROSS).value, D("100.000000"))

    def test_empty_scope_falls_back_to_the_business_currency_and_records_zero(self):
        euro = self.make_business("Euro shop", "euro-shop", currency="EUR")
        result = revenue.compute_order_revenue(
            business_id=euro.pk, period_start=START, period_end=END
        )
        self.assertEqual(result.scope.currency, "EUR")
        self.assertEqual(result.scope.currency_source, revenue.CURRENCY_SOURCE_BUSINESS_DEFAULT)
        self.assertEqual(result.gross_amount, D("0"))
        self.assertEqual(result.counted_orders, 0)

        written = revenue.record_revenue_metrics(
            business_id=euro.pk, period_type="DAY", period_start=START, period_end=END
        )
        for key in (GROSS, REFUNDED, NET):
            with self.subTest(metric=key):
                self.assertEqual(written.results[key].status, metrics.WRITE_CREATED)
                self.assertEqual(written.results[key].observation.value, D("0.000000"))
        self.assertEqual(
            written.results[PER_CUSTOMER].status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE
        )
        row = models.MetricSnapshot.objects.get(
            pk=written.results[GROSS].observation.snapshot_id
        )
        self.assertIs(row.metadata["data_available"], True)
        self.assertEqual(row.metadata["inputs"]["currency"], "EUR")
        self.assertEqual(row.metadata["inputs"]["currency_source"], "BUSINESS_DEFAULT")

    def test_single_observed_currency_is_used_without_a_caller_choice(self):
        self.order("DELIVERED", "70.00", currency="USD")
        result = self.calc()
        self.assertEqual(result.scope.currency, "USD")
        self.assertEqual(result.scope.currency_source, revenue.CURRENCY_SOURCE_SINGLE_OBSERVED)
        self.assertEqual(result.gross_amount, D("70.00"))

    def test_currency_arguments_are_validated(self):
        bad = ["", "   ", "TOOLONGCODE", 840, b"USD", ["USD"]]
        for value in bad:
            with self.subTest(currency=value):
                with self.assertRaises(revenue.RevenueValidationError):
                    self.calc(currency=value)
        self.order("DELIVERED", "5.00", currency="USD")
        self.assertEqual(self.calc(currency=" USD ").scope.currency, "USD")

    def test_currency_comparison_is_exact_not_case_folded(self):
        self.order("DELIVERED", "10.00", currency="usd")
        self.order("DELIVERED", "20.00", currency="USD")
        with self.assertRaises(revenue.RevenueCurrencyMixError):
            self.calc()
        self.assertEqual(self.calc(currency="USD").gross_amount, D("20.00"))
        self.assertEqual(self.calc(currency="usd").gross_amount, D("10.00"))

    def test_blank_currency_order_is_reported_only_as_without_currency(self):
        """Pins the current behaviour: the currency check precedes classification."""
        self.order("DELIVERED", "100.00")
        self.order("DELIVERED", "50.00", currency="")
        self.order("DELIVERED", "25.00", currency="  ")
        self.order(" PAID", "7.00", currency="")
        result = self.calc()
        coverage = result.coverage
        self.assertEqual(result.scope.currency, "BDT")
        self.assertEqual(result.counted_orders, 1)
        self.assertEqual(result.gross_amount, D("100.00"))
        self.assertEqual(coverage["orders_without_currency"], 3)
        self.assertEqual(coverage["unclassified_orders"], 0)
        self.assertEqual(coverage["unclassified_order_statuses"], {})
        self.assertEqual(coverage["orders_in_other_currency"], 0)
        self.assertEqual(coverage["orders_in_period"], 4)
        self.assert_order_coverage_reconciles(coverage)
        self.sales()
        inputs = self.inputs(TOTAL_ORDERS)
        self.assertEqual(inputs["orders_without_currency"], 3)
        self.assertEqual(inputs["unclassified_order_statuses"], {})

    def test_blank_currency_payment_and_refund_are_reported_and_excluded(self):
        order = self.order("DELIVERED", "100.00")
        paid = self.payment(order, "PAID", "100.00")
        self.payment(order, "PAID", "30.00", currency="")
        self.refund(paid, "10.00", order=order)
        self.refund(paid, "99.00", order=order, currency="")
        receipts = self.call("compute_payment_receipts")
        self.assertEqual(receipts.received_amount, D("100.00"))
        self.assertEqual(receipts.coverage["payments_without_currency"], 1)
        refunds = self.call("compute_refund_impact")
        self.assertEqual(refunds.refunded_amount, D("10.00"))
        self.assertEqual(refunds.coverage["refunds_without_currency"], 1)

    def test_business_wide_amounts_in_two_currencies_do_not_overwrite_each_other(self):
        """SPEC: metrics.py says a business-wide AMOUNT snapshot has no currency
        column, so a second currency may not silently replace the first one.
        """
        self.mixed_world()
        self.revenue_metrics(currency="BDT")
        self.assertEqual(self.obs(GROSS).value, D("100.000000"))
        try:
            self.revenue_metrics(currency="USD")
        except revenue.RevenueValidationError:
            pass  # refusing the second currency is acceptable
        stored = self.obs(GROSS)
        self.assertEqual(stored.value, D("100.000000"))
        self.assertEqual(stored.revision, 1)
        self.assertEqual(self.inputs(GROSS)["currency"], "BDT")


# ==========================================================================
# 3. Refunds
# ==========================================================================

class RefundImpactTests(RevenueTestCase):

    def refund_world(self):
        self.shopify = self.connection("shopify")
        self.o1 = self.order("DELIVERED", "100.00", connection=self.shopify)
        self.o2 = self.order("DELIVERED", "50.00")
        self.p1 = self.payment(self.o1, "PAID", "100.00")
        self.orphan = self.payment(None, "PAID", "20.00")
        self.r_direct = self.refund(self.p1, "10.00", order=self.o1)
        self.r_via_payment = self.refund(self.p1, "5.00", order=None)
        self.r_unattributed = self.refund(self.orphan, "3.00", order=None)
        self.r_other_currency = self.refund(self.p1, "7.00", order=self.o1, currency="USD")
        self.r_no_timestamp = self.refund(self.p1, "11.00", order=self.o1, at=None)
        self.r_at_end = self.refund(self.p1, "13.00", order=self.o1, at=END)
        self.r_at_start = self.refund(self.p1, "17.00", order=self.o1, at=START)
        # Another business: must never contribute anywhere.
        foreign_order = self.order("DELIVERED", "999.00", business=self.other)
        foreign_payment = self.payment(foreign_order, "PAID", "999.00", business=self.other)
        self.refund(foreign_payment, "99.00", order=foreign_order)

    def test_business_wide_refund_total_includes_every_completed_refund_once(self):
        self.refund_world()
        impact = self.call("compute_refund_impact", currency="BDT")
        # 10 direct + 5 via payment.order + 3 with no order anywhere + 17 at period_start
        self.assertEqual(impact.refunded_amount, D("35.00"))
        self.assertEqual(impact.refund_count, 4)
        self.assertEqual(impact.refunds_without_order_link, 2)
        self.assertEqual(impact.refunds_without_any_order, 1)
        coverage = impact.coverage
        self.assertEqual(coverage["refunds_counted"], 4)
        self.assertEqual(coverage["refund_statuses"], {"COMPLETED": 4})
        self.assertEqual(coverage["refund_completion_timestamp_field"], "refunded_at")
        self.assertEqual(coverage["refund_status_filter"], "NONE_DOCUMENTED")

    def test_refund_in_another_currency_is_excluded_and_counted(self):
        self.refund_world()
        impact = self.call("compute_refund_impact", currency="BDT")
        self.assertEqual(impact.coverage["refunds_in_other_currency"], 1)
        usd = self.call("compute_refund_impact", currency="USD")
        self.assertEqual(usd.refunded_amount, D("7.00"))
        self.assertEqual(usd.refund_count, 1)

    def test_refund_without_completion_timestamp_is_excluded_and_counted(self):
        self.refund_world()
        impact = self.call("compute_refund_impact", currency="BDT")
        self.assertEqual(impact.coverage["refunds_without_completion_timestamp"], 1)
        self.assertNotEqual(impact.refunded_amount, D("46.00"))

    def test_refund_period_boundaries_are_half_open(self):
        self.refund_world()
        before = self.call("compute_refund_impact", currency="BDT")
        self.assertEqual(before.refund_count, 4)  # includes START, excludes END
        later = self.call(
            "compute_refund_impact", currency="BDT",
            period_start=END, period_end=END + DAY,
        )
        self.assertEqual(later.refunded_amount, D("13.00"))
        self.assertEqual(later.refund_count, 1)

    def test_refund_with_a_null_order_is_attributed_through_its_payment_order(self):
        self.refund_world()
        scoped = self.call(
            "compute_refund_impact", currency="BDT",
            dimension_type="CHANNEL", dimension_value="shopify",
        )
        # direct 10 + via payment.order 5 + 17 at period_start; the unattributed 3 is out
        self.assertEqual(scoped.refunded_amount, D("32.00"))
        self.assertEqual(scoped.refund_count, 3)
        self.assertEqual(scoped.refunds_without_order_link, 1)
        self.assertEqual(scoped.refunds_without_any_order, 0)

    def test_refund_with_no_order_anywhere_is_reported_unattributed_in_a_dimension(self):
        self.refund_world()
        scoped = self.call(
            "compute_refund_impact", currency="BDT",
            dimension_type="CHANNEL", dimension_value="shopify",
        )
        self.assertEqual(scoped.coverage["refunds_excluded_without_order_scope"], 1)
        business_wide = self.call("compute_refund_impact", currency="BDT")
        self.assertEqual(business_wide.coverage["refunds_excluded_without_order_scope"], 0)
        by_currency = self.call(
            "compute_refund_impact", dimension_type="CURRENCY", dimension_value="BDT"
        )
        self.assertEqual(by_currency.refunded_amount, D("35.00"))

    def test_foreign_business_refund_never_contributes(self):
        self.refund_world()
        for scope in ({}, {"dimension_type": "CURRENCY", "dimension_value": "BDT"}):
            with self.subTest(scope=scope):
                impact = self.call("compute_refund_impact", currency="BDT", **scope)
                self.assertNotIn(impact.refunded_amount, (D("134.00"), D("99.00")))
        self.assertEqual(
            self.call("compute_refund_impact", business_id=self.other.pk).refunded_amount,
            D("99.00"),
        )

    def test_net_revenue_subtracts_each_refund_exactly_once(self):
        self.refund_world()
        self.revenue_metrics(currency="BDT")
        self.assertEqual(self.obs(GROSS).value, D("150.000000"))
        self.assertEqual(self.obs(REFUNDED).value, D("35.000000"))
        self.assertEqual(self.obs(NET).value, D("115.000000"))
        inputs = self.inputs(NET)
        self.assertEqual(D(inputs["gross_amount"]), D("150.00"))
        self.assertEqual(D(inputs["refunded_amount"]), D("35.00"))
        self.assertEqual(D(inputs["net_amount"]), D("115.00"))

    def test_payment_dimension_scope_reports_payments_without_an_order(self):
        self.refund_world()
        scoped = self.call(
            "compute_payment_receipts", currency="BDT",
            dimension_type="CHANNEL", dimension_value="shopify",
        )
        self.assertEqual(scoped.received_amount, D("100.00"))
        self.assertEqual(scoped.coverage["payments_excluded_without_order_scope"], 1)

    def test_refund_status_is_reported_not_filtered(self):
        order = self.order("DELIVERED", "100.00")
        paid = self.payment(order, "PAID", "100.00")
        self.refund(paid, "10.00", order=order, status="COMPLETED")
        self.refund(paid, "20.00", order=order, status="FAILED")
        self.refund(paid, "30.00", order=order, status="PENDING")
        impact = self.call("compute_refund_impact")
        self.assertEqual(impact.refunded_amount, D("60.00"))
        self.assertEqual(
            impact.coverage["refund_statuses"],
            {"COMPLETED": 1, "FAILED": 1, "PENDING": 1},
        )


# ==========================================================================
# 4. Unrecognised statuses
# ==========================================================================

class UnclassifiedStatusTests(RevenueTestCase):

    def test_unrecognised_order_statuses_are_excluded_and_counted_exactly(self):
        self.order("CONFIRMED", "100.00")
        self.order("paid", "10.00")
        self.order(" PAID", "20.00")
        self.order("", "30.00")
        self.order("cancelled", "40.00")
        result = self.calc()
        self.assertEqual(result.counted_orders, 1)
        self.assertEqual(result.eligible_orders, 1)
        self.assertEqual(result.cancelled_orders, 0)  # matching is exact, no case folding
        self.assertEqual(result.gross_amount, D("100.00"))
        coverage = result.coverage
        self.assertEqual(
            coverage["unclassified_order_statuses"],
            {"paid": 1, " PAID": 1, "(blank)": 1, "cancelled": 1},
        )
        self.assertEqual(coverage["unclassified_orders"], 4)
        self.assertEqual(coverage["unclassified_order_amount"], D("100.00"))
        self.assert_order_coverage_reconciles(coverage)

    def test_unrecognised_statuses_never_count_as_a_sale_or_a_cancellation(self):
        self.order("DELIVERED", "100.00")
        for status in ("paid", " PAID", ""):
            self.order(status, "50.00")
        self.sales()
        self.assertEqual(self.obs(TOTAL_ORDERS).value, D("1.000000"))
        self.assertEqual(self.obs(AOV).value, D("100.000000"))
        self.assertEqual(self.obs(CANCELLATION).value, D("0.000000"))

    def test_coverage_counts_are_written_into_the_snapshot_inputs(self):
        self.order("DELIVERED", "100.00")
        self.order("paid", "10.00")
        self.order(" PAID", "20.00")
        self.order("", "30.00")
        self.sales()
        self.revenue_metrics()
        expected = {"paid": 1, " PAID": 1, "(blank)": 1}
        for key in SALES_KEYS + REVENUE_KEYS:
            observation = self.obs(key)
            if observation is None:
                continue  # an UNAVAILABLE figure writes no row, so carries no inputs
            with self.subTest(metric=key):
                inputs = self.inputs(key)
                self.assertEqual(inputs["unclassified_order_statuses"], expected)
                self.assertEqual(inputs["unclassified_orders"], 3)
                self.assertEqual(D(inputs["unclassified_order_amount"]), D("60.00"))
        self.assertIsNotNone(self.obs(TOTAL_ORDERS))
        self.assertIsNotNone(self.obs(GROSS))

    def test_eligibility_filters_are_recorded_in_every_snapshot(self):
        self.order("DELIVERED", "100.00", customer=self.customer())
        self.sales()
        self.revenue_metrics()
        eligible = sorted(revenue.REVENUE_ELIGIBLE_ORDER_STATUSES)
        counted = sorted(revenue.COUNTED_ORDER_STATUSES)
        for key in SALES_KEYS + REVENUE_KEYS:
            with self.subTest(metric=key):
                inputs = self.inputs(key)
                self.assertEqual(inputs["eligible_order_statuses"], eligible)
                self.assertEqual(inputs["counted_order_statuses"], counted)
                self.assertEqual(inputs["order_period_timestamp_field"], "ordered_at")
                self.assertTrue(inputs["calculation_rule_eligibility"])
                self.assertEqual(
                    self.row(key).calculation_rule, rule(key, ORDERS)
                )

    def test_unrecognised_payment_statuses_are_excluded_from_both_totals(self):
        self.payment(None, "PAID", "10.00")
        self.payment(None, "paid", "5.00")
        self.payment(None, " PAID", "6.00")
        self.payment(None, "", "7.00")
        self.payment(None, "SETTLED", "8.00")
        receipts = self.call("compute_payment_receipts")
        self.assertEqual(receipts.received_payments, 1)
        self.assertEqual(receipts.received_amount, D("10.00"))
        self.assertEqual(receipts.not_received_payments, 0)
        self.assertEqual(receipts.not_received_amount, D("0"))
        coverage = receipts.coverage
        self.assertEqual(
            coverage["unclassified_payment_statuses"],
            {"paid": 1, " PAID": 1, "(blank)": 1, "SETTLED": 1},
        )
        self.assertEqual(coverage["unclassified_payments"], 4)
        self.assertEqual(coverage["unclassified_payment_amount"], D("26.00"))

    def test_unrecognised_payment_statuses_reach_the_reconciliation_coverage(self):
        self.order("DELIVERED", "100.00")
        self.payment(None, "paid", "5.00")
        self.revenue_metrics()
        inputs = self.inputs(GROSS)
        self.assertEqual(inputs["unclassified_payment_statuses"], {"paid": 1})
        self.assertEqual(inputs["unclassified_payments"], 1)

    def test_breakdown_coverage_also_reports_excluded_orders(self):
        """SPEC: revenue.py states the coverage of excluded rows is written into
        every snapshot's inputs; breakdown snapshots are snapshots too.
        """
        product = self.product("Alpha")
        sold = self.order("DELIVERED", "40.00")
        self.item(sold, product, 1, "40.00")
        for status in ("paid", " PAID"):
            ignored = self.order(status, "15.00")
            self.item(ignored, product, 1, "15.00")
        late = self.order("DELIVERED", "15.00", at=None)
        self.item(late, product, 1, "15.00")
        other_currency = self.order("DELIVERED", "15.00", currency="USD")
        self.item(other_currency, product, 1, "15.00")
        summary = self.breakdown("PRODUCT", currency="BDT")
        self.assertEqual(summary.total_gross_amount, D("40.00"))
        expectations = {
            "unclassified_order_statuses": {"paid": 1, " PAID": 1},
            "orders_without_period_timestamp": 1,
            "orders_in_other_currency": 1,
        }
        for key, value in expectations.items():
            with self.subTest(key=key):
                self.assertEqual(summary.coverage.get(key), value)
        self.record_breakdown("PRODUCT", currency="BDT")
        stored = self.inputs(
            GROSS, dimension_type="PRODUCT", dimension_value=str(product.pk)
        )
        for key, value in expectations.items():
            with self.subTest(snapshot_key=key):
                self.assertEqual(stored.get(key), value)


# ==========================================================================
# 5. Zero denominators, measured zeros and negatives
# ==========================================================================

class ZeroDenominatorTests(RevenueTestCase):

    def test_pending_only_period_counts_orders_but_has_no_average_order_value(self):
        self.order("PENDING", "10.00")
        self.order("PENDING", "20.00")
        written = self.sales()
        self.assertEqual(written.results[TOTAL_ORDERS].status, metrics.WRITE_CREATED)
        self.assertEqual(written.results[TOTAL_ORDERS].observation.value, D("2.000000"))
        self.assertEqual(written.results[UNITS_SOLD].observation.value, D("0.000000"))
        self.assertEqual(
            written.results[AOV].status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE
        )
        self.assertIsNone(written.results[AOV].observation)
        self.assertEqual(written.results[CANCELLATION].observation.value, D("0.000000"))
        self.assertIsNone(self.obs(AOV))

    def test_zero_counted_orders_make_the_cancellation_rate_unavailable(self):
        self.order(" PAID", "10.00")  # unclassified, so never counted
        written = self.sales()
        self.assertEqual(written.results[TOTAL_ORDERS].observation.value, D("0.000000"))
        self.assertEqual(
            written.results[CANCELLATION].status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE
        )
        self.assertEqual(
            written.results[AOV].status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE
        )
        self.assertIsNone(self.obs(CANCELLATION))

    def test_a_period_with_no_orders_records_measured_zero_counts(self):
        written = self.sales()
        for key in (TOTAL_ORDERS, UNITS_SOLD):
            with self.subTest(metric=key):
                self.assertEqual(written.results[key].status, metrics.WRITE_CREATED)
                self.assertEqual(written.results[key].observation.value, D("0.000000"))
                self.assertIs(self.row(key).metadata["data_available"], True)
        self.assertEqual(self.snapshot_count(), 2)

    def test_no_resolved_customer_makes_revenue_per_customer_unavailable(self):
        self.order("DELIVERED", "100.00")
        written = self.revenue_metrics()
        self.assertEqual(
            written.results[PER_CUSTOMER].status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE
        )
        self.assertIsNone(self.obs(PER_CUSTOMER))
        self.assertEqual(written.results[GROSS].observation.value, D("100.000000"))
        inputs = self.inputs(GROSS)
        self.assertEqual(inputs["distinct_resolved_customers"], 0)
        self.assertEqual(inputs["orders_without_resolved_customer"], 1)

    def test_revenue_per_customer_uses_the_documented_numerator_and_reports_guests(self):
        """Pins revenue.py rule: ALL eligible gross over distinct resolved customers.

        A guest order inflates the ratio (1000 / 1 customer); the guest count is
        exposed in the inputs. Flagged to the owner in the report as a concern.
        """
        self.order("DELIVERED", "100.00", customer=self.customer())
        self.order("DELIVERED", "900.00")
        self.revenue_metrics()
        self.assertEqual(self.obs(PER_CUSTOMER).value, D("1000.000000"))
        inputs = self.inputs(PER_CUSTOMER)
        self.assertEqual(D(inputs["numerator_gross_amount"]), D("1000.00"))
        self.assertEqual(inputs["denominator_distinct_customers"], 1)
        self.assertEqual(inputs["orders_without_resolved_customer"], 1)

    def test_distinct_customers_are_counted_once_each(self):
        buyer = self.customer()
        self.order("DELIVERED", "30.00", customer=buyer)
        self.order("SHIPPED", "30.00", customer=buyer)
        self.order("DELIVERED", "40.00", customer=self.customer())
        self.revenue_metrics()
        self.assertEqual(self.obs(PER_CUSTOMER).value, D("50.000000"))
        self.assertEqual(
            self.inputs(PER_CUSTOMER)["denominator_distinct_customers"], 2
        )

    def test_a_period_without_revenue_records_a_measured_zero_not_an_absence(self):
        self.order("PENDING", "10.00")
        written = self.revenue_metrics()
        for key in (GROSS, REFUNDED, NET):
            with self.subTest(metric=key):
                self.assertEqual(written.results[key].status, metrics.WRITE_CREATED)
                self.assertEqual(written.results[key].observation.value, D("0.000000"))
                self.assertIs(self.row(key).metadata["data_available"], True)

    def test_negative_net_revenue_is_recorded_as_a_fact(self):
        paid = self.payment(None, "PAID", "25.00")
        self.refund(paid, "25.00")
        written = self.revenue_metrics()
        self.assertEqual(written.results[GROSS].observation.value, D("0.000000"))
        self.assertEqual(written.results[REFUNDED].observation.value, D("25.000000"))
        self.assertEqual(written.results[NET].status, metrics.WRITE_CREATED)
        self.assertEqual(written.results[NET].observation.value, D("-25.000000"))
        self.assertEqual(self.obs(NET).value, D("-25.000000"))

    def test_unavailable_rerun_never_deletes_or_zeroes_the_earlier_observation(self):
        order = self.order("DELIVERED", "100.00")
        self.sales()
        first = self.obs(AOV)
        self.assertEqual(first.value, D("100.000000"))
        order.status = "PENDING"
        order.save(update_fields=["status"])
        again = self.sales()
        self.assertEqual(
            again.results[AOV].status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE
        )
        self.assertEqual(again.results[AOV].existing_snapshot_id, first.snapshot_id)
        self.assertEqual(self.obs(AOV).value, D("100.000000"))

    def test_gross_falls_to_a_recorded_zero_when_all_orders_leave_eligibility(self):
        order = self.order("DELIVERED", "100.00")
        self.revenue_metrics()
        order.status = "CANCELLED"
        order.save(update_fields=["status"])
        again = self.revenue_metrics()
        self.assertEqual(again.results[GROSS].status, metrics.WRITE_UPDATED)
        self.assertEqual(again.results[GROSS].previous_value, D("100.000000"))
        self.assertEqual(again.results[GROSS].observation.value, D("0.000000"))


# ==========================================================================
# 6. Replay and revision
# ==========================================================================

class ReplayTests(RevenueTestCase):

    def replay_world(self):
        self.buyer = self.customer()
        self.sold = self.order("DELIVERED", "100.00", customer=self.buyer)
        self.item(self.sold, self.product(), 2, "100.00")
        self.paid = self.payment(self.sold, "PAID", "100.00")
        self.refund(self.paid, "10.00", order=self.sold)

    def test_replay_reports_unchanged_with_the_same_rows_and_timestamps(self):
        self.replay_world()
        with patch(NOW, return_value=CLOCK_A):
            first_sales = self.sales()
            first_revenue = self.revenue_metrics()
        self.assertEqual(self.snapshot_count(), 8)
        for result in (first_sales, first_revenue):
            for key, written in result.results.items():
                with self.subTest(first=key):
                    self.assertEqual(written.status, metrics.WRITE_CREATED)
        before = list(models.MetricSnapshot.objects.order_by("pk").values())

        with patch(NOW, return_value=CLOCK_B):
            second_sales = self.sales()
            second_revenue = self.revenue_metrics()
        for first, second in ((first_sales, second_sales), (first_revenue, second_revenue)):
            for key, written in second.results.items():
                with self.subTest(replay=key):
                    self.assertEqual(written.status, metrics.WRITE_UNCHANGED)
                    self.assertEqual(
                        written.observation.snapshot_id,
                        first.results[key].observation.snapshot_id,
                    )
                    self.assertEqual(written.observation.calculated_at, CLOCK_A)
                    self.assertEqual(written.observation.revision, 1)
        self.assertEqual(self.snapshot_count(), 8)
        self.assertEqual(list(models.MetricSnapshot.objects.order_by("pk").values()), before)
        for row in models.MetricSnapshot.objects.all():
            self.assertNotIn("supersedes", row.metadata)

    def test_late_refund_updates_with_a_revision_and_a_supersedes_record(self):
        self.replay_world()
        with patch(NOW, return_value=CLOCK_A):
            self.revenue_metrics()
        refunded_id = self.obs(REFUNDED).snapshot_id
        net_id = self.obs(NET).snapshot_id
        self.refund(self.paid, "15.00", order=self.sold)

        with patch(NOW, return_value=CLOCK_B):
            again = self.revenue_metrics()
        self.assertEqual(self.snapshot_count(), 4)

        refunded = again.results[REFUNDED]
        self.assertEqual(refunded.status, metrics.WRITE_UPDATED)
        self.assertEqual(refunded.previous_value, D("10.000000"))
        self.assertEqual(refunded.observation.snapshot_id, refunded_id)
        self.assertEqual(refunded.observation.value, D("25.000000"))
        self.assertEqual(refunded.observation.revision, 2)
        self.assertEqual(refunded.observation.calculated_at, CLOCK_B)
        metadata = self.row(REFUNDED).metadata
        self.assertEqual(metadata["revision"], 2)
        self.assertEqual(metadata["supersedes"], {
            "revision": 1,
            "value": "10.000000",
            "calculation_rule": rule(REFUNDED),
            "calculated_at": CLOCK_A.isoformat(),
        })

        net = again.results[NET]
        self.assertEqual(net.status, metrics.WRITE_UPDATED)
        self.assertEqual(net.observation.snapshot_id, net_id)
        self.assertEqual(net.previous_value, D("90.000000"))
        self.assertEqual(net.observation.value, D("75.000000"))
        self.assertEqual(net.observation.revision, 2)

    def test_gross_revenue_is_not_revised_by_a_late_refund(self):
        """SPEC: metrics.py says a replay producing the same value and rule
        touches nothing. A refund cannot change gross, so gross must stay at
        revision 1 and keep its calculation time.
        """
        self.replay_world()
        with patch(NOW, return_value=CLOCK_A):
            self.revenue_metrics()
        self.refund(self.paid, "15.00", order=self.sold)
        with patch(NOW, return_value=CLOCK_B):
            again = self.revenue_metrics()
        gross = again.results[GROSS]
        self.assertEqual(gross.observation.value, D("100.000000"))
        self.assertEqual(gross.status, metrics.WRITE_UNCHANGED)
        self.assertEqual(gross.observation.revision, 1)
        self.assertEqual(gross.observation.calculated_at, CLOCK_A)

    def test_late_order_updates_the_count_and_keeps_one_row(self):
        self.replay_world()
        with patch(NOW, return_value=CLOCK_A):
            self.sales()
        self.order("CONFIRMED", "50.00", customer=self.buyer)
        with patch(NOW, return_value=CLOCK_B):
            again = self.sales()
        written = again.results[TOTAL_ORDERS]
        self.assertEqual(written.status, metrics.WRITE_UPDATED)
        self.assertEqual(written.previous_value, D("1.000000"))
        self.assertEqual(written.observation.value, D("2.000000"))
        self.assertEqual(written.observation.revision, 2)
        self.assertEqual(self.snapshot_count(), 4)

    def test_unchanged_data_changes_nothing_across_many_replays(self):
        self.replay_world()
        self.sales()
        self.revenue_metrics()
        before = list(models.MetricSnapshot.objects.order_by("pk").values())
        for _ in range(3):
            self.sales()
            self.revenue_metrics()
        self.assertEqual(list(models.MetricSnapshot.objects.order_by("pk").values()), before)

    def test_payment_basis_is_never_recorded(self):
        self.replay_world()
        self.revenue_metrics()
        self.assertEqual(
            models.MetricSnapshot.objects.filter(
                calculation_rule__contains="payments_received"
            ).count(),
            0,
        )
        for row in models.MetricSnapshot.objects.select_related("metric"):
            self.assertIn(row.metric.key, SALES_KEYS + REVENUE_KEYS)


# ==========================================================================
# 7. Period boundaries
# ==========================================================================

class PeriodBoundaryTests(RevenueTestCase):

    def test_period_is_half_open_on_ordered_at(self):
        self.order("DELIVERED", "100.00", at=START)
        self.order("DELIVERED", "200.00", at=END)
        self.order("DELIVERED", "300.00", at=START - timedelta(microseconds=1))
        self.order("DELIVERED", "400.00", at=END - timedelta(microseconds=1))
        result = self.calc()
        self.assertEqual(result.counted_orders, 2)
        self.assertEqual(result.gross_amount, D("500.00"))
        following = self.calc(period_start=END, period_end=END + DAY)
        self.assertEqual(following.counted_orders, 1)
        self.assertEqual(following.gross_amount, D("200.00"))

    def test_adjacent_periods_never_double_count_the_boundary_order(self):
        self.order("DELIVERED", "75.00", at=END)
        first = self.calc(period_start=START, period_end=END)
        second = self.calc(period_start=END, period_end=END + DAY)
        self.assertEqual(first.counted_orders + second.counted_orders, 1)
        self.assertEqual(first.gross_amount + second.gross_amount, D("75.00"))

    def test_order_without_ordered_at_belongs_to_no_period(self):
        """created_at is inside the period but is never substituted for ordered_at."""
        undated = self.order("DELIVERED", "500.00", at=None)
        self.assertGreaterEqual(undated.created_at, START)
        self.assertLess(undated.created_at, END)
        self.order("DELIVERED", "100.00", at=START)
        result = self.calc()
        self.assertEqual(result.counted_orders, 1)
        self.assertEqual(result.gross_amount, D("100.00"))
        self.assertEqual(result.coverage["orders_without_period_timestamp"], 1)
        self.assertEqual(result.coverage["order_period_timestamp_field"], "ordered_at")
        elsewhere = self.calc(period_start=day(5)[0], period_end=day(5)[1])
        self.assertEqual(elsewhere.counted_orders, 0)
        self.assertEqual(elsewhere.gross_amount, D("0"))

    def test_an_order_dated_before_the_period_is_not_pulled_in_by_created_at(self):
        early = self.order("DELIVERED", "600.00", at=START - timedelta(hours=1))
        self.assertGreaterEqual(early.created_at, START)
        result = self.calc()
        self.assertEqual(result.counted_orders, 0)
        self.assertEqual(result.gross_amount, D("0"))

    def test_undated_orders_are_reported_in_every_snapshot(self):
        self.order("DELIVERED", "500.00", at=None)
        self.order("DELIVERED", "100.00", at=START)
        self.sales()
        self.revenue_metrics()
        for key in (TOTAL_ORDERS, UNITS_SOLD, AOV, CANCELLATION, GROSS, REFUNDED, NET):
            with self.subTest(metric=key):
                self.assertEqual(self.inputs(key)["orders_without_period_timestamp"], 1)
        self.assertEqual(self.obs(TOTAL_ORDERS).value, D("1.000000"))
        self.assertEqual(self.obs(GROSS).value, D("100.000000"))

    def test_reimport_that_rewrites_created_at_does_not_move_orders_between_periods(self):
        order = self.order("DELIVERED", "100.00", at=START)
        self.revenue_metrics()
        models.Order.objects.filter(pk=order.pk).update(created_at=END + 10 * DAY)
        again = self.revenue_metrics()
        self.assertEqual(again.results[GROSS].status, metrics.WRITE_UNCHANGED)
        self.assertEqual(self.obs(GROSS).value, D("100.000000"))

    def test_payment_receipt_period_is_half_open_on_paid_at(self):
        self.payment(None, "PAID", "10.00", paid_at=START)
        self.payment(None, "PAID", "20.00", paid_at=END)
        self.payment(None, "PAID", "30.00", paid_at=None)
        receipts = self.call("compute_payment_receipts")
        self.assertEqual(receipts.received_amount, D("10.00"))
        self.assertEqual(receipts.received_payments, 1)
        self.assertEqual(receipts.coverage["payments_without_period_timestamp"], 1)
        self.assertEqual(receipts.coverage["payment_period_timestamp_field"], "paid_at")

    def test_period_type_is_a_label_and_bounds_are_the_authority(self):
        self.order("DELIVERED", "100.00", at=START + timedelta(days=3))
        written = self.revenue_metrics(
            period_type="WEEK", period_start=START, period_end=START + 7 * DAY
        )
        self.assertEqual(written.results[GROSS].observation.value, D("100.000000"))
        self.assertEqual(written.results[GROSS].observation.period_type, "WEEK")


# ==========================================================================
# 8. Eligibility, reversal and payment receipt
# ==========================================================================

class EligibilityTests(RevenueTestCase):

    def status_world(self):
        amounts = {
            "PENDING": "10.00", "CONFIRMED": "20.00", "PROCESSING": "30.00",
            "SHIPPED": "40.00", "DELIVERED": "50.00", "CANCELLED": "60.00",
            "RETURNED": "70.00", "REFUNDED": "80.00",
        }
        self.by_status = {
            status: self.order(status, total) for status, total in amounts.items()
        }

    def test_every_documented_status_is_classified_exactly(self):
        self.status_world()
        result = self.calc()
        self.assertEqual(result.counted_orders, 8)
        self.assertEqual(result.eligible_orders, 6)
        self.assertEqual(result.accepted_orders, 4)
        self.assertEqual(result.reversed_orders, 2)
        self.assertEqual(result.pending_orders, 1)
        self.assertEqual(result.cancelled_orders, 1)
        self.assertEqual(result.gross_amount, D("290.00"))
        self.assertEqual(result.accepted_amount, D("140.00"))
        self.assertEqual(result.reversed_amount, D("150.00"))
        self.assertEqual(result.coverage["reversed_order_amount"], D("150.00"))
        self.assertEqual(result.coverage["unclassified_orders"], 0)
        self.assert_order_coverage_reconciles(result.coverage)

    def test_sales_metrics_use_counted_and_eligible_sets_respectively(self):
        self.status_world()
        self.sales()
        self.assertEqual(self.obs(TOTAL_ORDERS).value, D("8.000000"))
        self.assertEqual(self.obs(CANCELLATION).value, D("0.125000"))
        self.assertEqual(self.obs(AOV).value, D("48.333333"))
        self.assertEqual(D(self.row(AOV).metadata["rounded_from"]) > D("48.3333333333"), True)

    def test_cancelled_orders_are_only_the_cancellation_numerator(self):
        self.order("CANCELLED", "500.00")
        self.order("DELIVERED", "100.00")
        self.sales()
        self.revenue_metrics()
        self.assertEqual(self.obs(CANCELLATION).value, D("0.500000"))
        self.assertEqual(self.obs(GROSS).value, D("100.000000"))
        self.assertEqual(self.obs(AOV).value, D("100.000000"))

    def test_units_come_from_eligible_orders_only(self):
        for status, quantity in (
            ("PENDING", 5), ("DELIVERED", 2), ("CANCELLED", 7), ("RETURNED", 1),
        ):
            self.item(self.order(status, "10.00"), self.product(status), quantity, "10.00")
        result = self.calc()
        self.assertEqual(result.units_sold, 3)
        self.sales()
        self.assertEqual(self.obs(UNITS_SOLD).value, D("3.000000"))

    def test_nonpositive_quantities_and_items_without_product_are_reported(self):
        order = self.order("DELIVERED", "30.00")
        self.item(order, self.product(), 3, "10.00")
        self.item(order, None, 0, "0.00")
        result = self.calc()
        self.assertEqual(result.units_sold, 3)
        self.assertEqual(result.coverage["order_items_with_nonpositive_quantity"], 1)
        self.assertEqual(result.coverage["order_items_without_product"], 1)

    def test_returned_order_with_its_refund_is_subtracted_exactly_once(self):
        self.order("DELIVERED", "100.00")
        returned = self.order("RETURNED", "70.00")
        paid = self.payment(returned, "REFUNDED", "70.00")
        self.refund(paid, "70.00", order=returned)
        reconciliation = self.call("reconcile_revenue")
        self.assertEqual(reconciliation.gross_order_amount, D("170.00"))
        self.assertEqual(reconciliation.refunded_amount, D("70.00"))
        self.assertEqual(reconciliation.net_order_amount, D("100.00"))
        self.revenue_metrics()
        self.assertEqual(self.obs(NET).value, D("100.000000"))

    def test_refunded_status_order_is_also_subtracted_exactly_once(self):
        refunded = self.order("REFUNDED", "80.00")
        paid = self.payment(refunded, "REFUNDED", "80.00")
        self.refund(paid, "80.00", order=refunded)
        self.revenue_metrics()
        self.assertEqual(self.obs(GROSS).value, D("80.000000"))
        self.assertEqual(self.obs(NET).value, D("0.000000"))

    def test_unrefunded_return_stays_in_net_and_is_visible_as_reversed_amount(self):
        self.order("DELIVERED", "100.00")
        self.order("RETURNED", "70.00")
        reconciliation = self.call("reconcile_revenue")
        self.assertEqual(reconciliation.net_order_amount, D("170.00"))
        self.assertEqual(reconciliation.orders.reversed_amount, D("70.00"))
        self.assertEqual(reconciliation.coverage["reversed_order_amount"], D("70.00"))
        self.revenue_metrics()
        self.assertEqual(D(self.inputs(NET)["reversed_order_amount"]), D("70.00"))
        self.assertEqual(D(self.inputs(GROSS)["reversed_amount"]), D("70.00"))
        self.assertEqual(D(self.inputs(GROSS)["accepted_amount"]), D("100.00"))

    def test_payment_receipt_follows_the_documented_payment_states(self):
        for status, amount in (
            ("PAID", "10.00"), ("PARTIALLY_REFUNDED", "20.00"), ("REFUNDED", "30.00"),
            ("AUTHORIZED", "40.00"), ("PENDING", "50.00"), ("FAILED", "60.00"),
            ("CANCELLED", "70.00"),
        ):
            self.payment(None, status, amount)
        receipts = self.call("compute_payment_receipts")
        self.assertEqual(receipts.received_payments, 3)
        self.assertEqual(receipts.received_amount, D("60.00"))
        self.assertEqual(receipts.not_received_payments, 4)
        self.assertEqual(receipts.not_received_amount, D("220.00"))
        self.assertEqual(receipts.coverage["unclassified_payments"], 0)

    def test_authorized_payment_is_not_money_received(self):
        order = self.order("DELIVERED", "100.00")
        self.payment(order, "AUTHORIZED", "100.00")
        reconciliation = self.call("reconcile_revenue")
        self.assertEqual(reconciliation.received_payment_amount, D("0"))
        self.assertEqual(reconciliation.order_payment_difference, D("100.00"))

    def test_reconciliation_reports_the_unreconciled_difference(self):
        paid_order = self.order("DELIVERED", "200.00")
        self.order("CONFIRMED", "100.00")
        self.payment(paid_order, "PAID", "200.00")
        self.payment(None, "PARTIALLY_REFUNDED", "50.00")
        self.payment(None, "PENDING", "999.00")
        reconciliation = self.call("reconcile_revenue")
        self.assertEqual(reconciliation.gross_order_amount, D("300.00"))
        self.assertEqual(reconciliation.received_payment_amount, D("250.00"))
        self.assertEqual(reconciliation.order_payment_difference, D("50.00"))
        self.assertEqual(
            reconciliation.coverage["order_payment_difference"], D("50.00")
        )
        self.assertEqual(reconciliation.refunded_amount, D("0"))
        self.assertEqual(reconciliation.net_order_amount, D("300.00"))
        self.assertEqual(reconciliation.net_received_amount, D("250.00"))

    def test_reconciliation_nets_refunds_against_both_bases(self):
        order = self.order("DELIVERED", "100.00")
        paid = self.payment(order, "PARTIALLY_REFUNDED", "100.00")
        self.refund(paid, "30.00", order=order)
        reconciliation = self.call("reconcile_revenue")
        self.assertEqual(reconciliation.net_order_amount, D("70.00"))
        self.assertEqual(reconciliation.net_received_amount, D("70.00"))
        self.assertEqual(reconciliation.order_payment_difference, D("0.00"))
        self.assertEqual(reconciliation.scope.basis, ORDERS)


# ==========================================================================
# 9. Growth and change detection
# ==========================================================================

class GrowthTests(RevenueTestCase):

    def record_orders(self, index, count, total="10.00"):
        for _ in range(count):
            self.order("DELIVERED", total, at=at(index))
        return self.sales(period_start=day(index)[0], period_end=day(index)[1])

    def grow_sales(self, current, previous, **overrides):
        params = dict(
            business_id=self.business.pk, period_type="DAY",
            current_period_start=day(current)[0], current_period_end=day(current)[1],
            previous_period_start=day(previous)[0], previous_period_end=day(previous)[1],
        )
        params.update(overrides)
        return revenue.record_sales_growth_rate(**params)

    def grow_revenue(self, current, previous, **overrides):
        params = dict(
            business_id=self.business.pk, period_type="DAY",
            current_period_start=day(current)[0], current_period_end=day(current)[1],
            previous_period_start=day(previous)[0], previous_period_end=day(previous)[1],
        )
        params.update(overrides)
        return revenue.record_revenue_growth_rate(**params)

    def growth(self, key, index):
        return self.obs(key, start=day(index)[0], end=day(index)[1])

    def test_sales_growth_is_the_fractional_change_of_recorded_order_counts(self):
        self.record_orders(0, 4)
        self.record_orders(1, 6)
        written = self.grow_sales(1, 0)
        result = written.results[SALES_GROWTH]
        self.assertEqual(result.status, metrics.WRITE_CREATED)
        self.assertEqual(result.observation.value, D("0.500000"))
        self.assertEqual(result.observation.calculation_rule, rule(SALES_GROWTH))
        self.assertEqual(written.scope.currency_source, "NOT_APPLICABLE_RATIO")

        current = self.obs(TOTAL_ORDERS, start=day(1)[0], end=day(1)[1])
        previous = self.obs(TOTAL_ORDERS, start=day(0)[0], end=day(0)[1])
        inputs = self.row(SALES_GROWTH, start=day(1)[0], end=day(1)[1]).metadata["inputs"]
        self.assertEqual(inputs["source_metric_key"], TOTAL_ORDERS)
        self.assertEqual(inputs["source_calculation_rule"], rule(TOTAL_ORDERS))
        self.assertEqual(inputs["current_snapshot_id"], current.snapshot_id)
        self.assertEqual(inputs["previous_snapshot_id"], previous.snapshot_id)
        self.assertEqual(D(inputs["current_value"]), D("6"))
        self.assertEqual(D(inputs["previous_value"]), D("4"))
        self.assertEqual(D(inputs["absolute_change"]), D("2"))
        self.assertEqual(inputs["direction"], metrics.DIRECTION_INCREASED)
        self.assertEqual(inputs["unavailable_reason"], "NONE")
        self.assertEqual(inputs["stored_as"], "FRACTION_NOT_PERCENTAGE")
        self.assertEqual(inputs["previous_period_start"], day(0)[0].isoformat())
        self.assertEqual(inputs["previous_period_end"], day(0)[1].isoformat())

    def test_a_decrease_is_a_negative_fraction(self):
        self.record_orders(0, 4)
        self.record_orders(2, 3)
        self.grow_sales(2, 0)
        self.assertEqual(self.growth(SALES_GROWTH, 2).value, D("-0.250000"))
        inputs = self.row(SALES_GROWTH, start=day(2)[0], end=day(2)[1]).metadata["inputs"]
        self.assertEqual(inputs["direction"], metrics.DIRECTION_DECREASED)

    def test_growth_replay_is_unchanged(self):
        self.record_orders(0, 4)
        self.record_orders(1, 6)
        with patch(NOW, return_value=CLOCK_A):
            first = self.grow_sales(1, 0)
        with patch(NOW, return_value=CLOCK_B):
            second = self.grow_sales(1, 0)
        self.assertEqual(second.results[SALES_GROWTH].status, metrics.WRITE_UNCHANGED)
        self.assertEqual(
            second.results[SALES_GROWTH].observation.snapshot_id,
            first.results[SALES_GROWTH].observation.snapshot_id,
        )
        self.assertEqual(second.results[SALES_GROWTH].observation.calculated_at, CLOCK_A)

    def test_growth_follows_a_late_correction_of_either_period(self):
        self.record_orders(0, 4)
        self.record_orders(1, 6)
        self.grow_sales(1, 0)
        self.order("DELIVERED", "10.00", at=at(1))
        self.order("DELIVERED", "10.00", at=at(1))
        self.sales(period_start=day(1)[0], period_end=day(1)[1])
        written = self.grow_sales(1, 0)
        self.assertEqual(written.results[SALES_GROWTH].status, metrics.WRITE_UPDATED)
        self.assertEqual(written.results[SALES_GROWTH].observation.value, D("1.000000"))
        self.assertEqual(written.results[SALES_GROWTH].observation.revision, 2)

    def test_previous_value_of_zero_is_unavailable_not_zero_or_infinite(self):
        self.sales(period_start=day(0)[0], period_end=day(0)[1])  # measured zero orders
        self.assertEqual(
            self.obs(TOTAL_ORDERS, start=day(0)[0], end=day(0)[1]).value, D("0.000000")
        )
        self.record_orders(1, 2)
        written = self.grow_sales(1, 0)
        result = written.results[SALES_GROWTH]
        self.assertEqual(result.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertIsNone(result.observation)
        self.assertIsNone(self.growth(SALES_GROWTH, 1))

    def test_missing_previous_observation_is_unavailable(self):
        self.record_orders(1, 2)
        result = self.grow_sales(1, 0).results[SALES_GROWTH]
        self.assertEqual(result.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertIsNone(self.growth(SALES_GROWTH, 1))

    def test_missing_current_observation_is_unavailable(self):
        self.record_orders(0, 2)
        result = self.grow_sales(1, 0).results[SALES_GROWTH]
        self.assertEqual(result.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertIsNone(self.growth(SALES_GROWTH, 1))

    def test_no_observations_at_all_is_unavailable(self):
        result = self.grow_sales(1, 0).results[SALES_GROWTH]
        self.assertEqual(result.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertEqual(self.snapshot_count(), 0)

    def test_unavailable_growth_keeps_an_earlier_growth_observation(self):
        self.record_orders(0, 4)
        self.record_orders(1, 6)
        self.grow_sales(1, 0)
        first = self.growth(SALES_GROWTH, 1)
        models.MetricSnapshot.objects.filter(
            metric__key=TOTAL_ORDERS, period_start=day(0)[0]
        ).delete()
        again = self.grow_sales(1, 0).results[SALES_GROWTH]
        self.assertEqual(again.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertEqual(again.existing_snapshot_id, first.snapshot_id)
        self.assertEqual(self.growth(SALES_GROWTH, 1).value, D("0.500000"))

    def test_previous_snapshot_under_a_different_rule_is_refused(self):
        self.record_orders(1, 6)
        # Written by another path under the bare registry rule, same metric key.
        self.seed(
            TOTAL_ORDERS, "4", start=day(0)[0], end=day(0)[1], calculation_rule=None
        )
        with self.assertRaises(revenue.RevenueScopeError):
            self.grow_sales(1, 0)
        self.assertIsNone(self.growth(SALES_GROWTH, 1))

    def test_current_snapshot_under_a_different_rule_is_refused(self):
        self.record_orders(0, 4)
        self.seed(
            TOTAL_ORDERS, "6", start=day(1)[0], end=day(1)[1],
            calculation_rule="bi.metric.sales_total_orders.v1.some_other_variant",
        )
        with self.assertRaises(revenue.RevenueScopeError):
            self.grow_sales(1, 0)
        self.assertIsNone(self.growth(SALES_GROWTH, 1))

    def test_overlapping_or_reversed_comparison_periods_are_a_validation_error(self):
        self.record_orders(0, 4)
        self.record_orders(1, 6)
        overlapping = (
            dict(previous_period_start=day(0)[0], previous_period_end=day(1)[0] + DAY),
            dict(previous_period_start=day(1)[0], previous_period_end=day(1)[1]),
            dict(previous_period_start=day(2)[0], previous_period_end=day(2)[1]),
        )
        for overrides in overlapping:
            with self.subTest(overrides=overrides):
                with self.assertRaises(revenue.RevenueValidationError):
                    self.grow_sales(1, 0, **overrides)
        self.assertIsNone(self.growth(SALES_GROWTH, 1))

    def test_adjacent_comparison_periods_are_allowed(self):
        self.record_orders(0, 2)
        self.record_orders(1, 3)
        result = self.grow_sales(1, 0).results[SALES_GROWTH]
        self.assertEqual(result.observation.value, D("0.500000"))

    def test_revenue_growth_uses_recorded_net_revenue(self):
        order = self.order("DELIVERED", "100.00", at=at(0))
        paid = self.payment(order, "PAID", "100.00", paid_at=at(0))
        self.refund(paid, "20.00", order=order, at=at(0))
        self.order("DELIVERED", "130.00", at=at(1))
        for index in (0, 1):
            self.revenue_metrics(period_start=day(index)[0], period_end=day(index)[1])
        self.assertEqual(self.obs(NET, start=day(0)[0], end=day(0)[1]).value, D("80.000000"))
        self.assertEqual(self.obs(NET, start=day(1)[0], end=day(1)[1]).value, D("130.000000"))
        result = self.grow_revenue(1, 0).results[REVENUE_GROWTH]
        self.assertEqual(result.status, metrics.WRITE_CREATED)
        self.assertEqual(result.observation.value, D("0.625000"))
        self.assertEqual(result.observation.calculation_rule, rule(REVENUE_GROWTH))
        inputs = self.row(REVENUE_GROWTH, start=day(1)[0], end=day(1)[1]).metadata["inputs"]
        self.assertEqual(inputs["source_metric_key"], NET)
        self.assertEqual(inputs["source_calculation_rule"], rule(NET))

    def test_growth_over_a_negative_previous_net_uses_the_absolute_denominator(self):
        for index, amount in ((0, "100.00"), (1, "50.00")):
            paid = self.payment(None, "PAID", amount, paid_at=at(index))
            self.refund(paid, amount, at=at(index))
            self.revenue_metrics(period_start=day(index)[0], period_end=day(index)[1])
        self.assertEqual(self.obs(NET, start=day(0)[0], end=day(0)[1]).value, D("-100.000000"))
        self.assertEqual(self.obs(NET, start=day(1)[0], end=day(1)[1]).value, D("-50.000000"))
        # (-50 - -100) / |-100| = +0.5: the loss shrank, so the change is positive.
        self.grow_revenue(1, 0)
        self.assertEqual(self.growth(REVENUE_GROWTH, 1).value, D("0.500000"))

    def test_revenue_growth_with_a_zero_previous_net_is_unavailable(self):
        self.revenue_metrics(period_start=day(0)[0], period_end=day(0)[1])  # measured 0
        self.order("DELIVERED", "130.00", at=at(1))
        self.revenue_metrics(period_start=day(1)[0], period_end=day(1)[1])
        result = self.grow_revenue(1, 0).results[REVENUE_GROWTH]
        self.assertEqual(result.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertIsNone(self.growth(REVENUE_GROWTH, 1))

    def test_growth_arguments_are_validated(self):
        cases = {
            "naive current": dict(current_period_start=datetime(2026, 10, 11)),
            "bad period type": dict(period_type="YEAR"),
            "bool business": dict(business_id=True),
            "unknown business": dict(business_id=10 ** 9),
            "half dimension": dict(dimension_type="CURRENCY"),
            "disallowed dimension": dict(dimension_type="PRODUCT", dimension_value="1"),
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(revenue.RevenueValidationError):
                    self.grow_sales(1, 0, **overrides)
        self.assertEqual(self.snapshot_count(), 0)

    def test_growth_dimension_must_belong_to_the_business(self):
        foreign = self.campaign("Foreign", business=self.other)
        for grow in (self.grow_sales, self.grow_revenue):
            with self.subTest(function=grow.__name__):
                with self.assertRaises(revenue.RevenueValidationError):
                    grow(
                        1, 0, dimension_type="CAMPAIGN", dimension_value=str(foreign.pk)
                    )
        self.assertEqual(self.snapshot_count(), 0)


class ChangeDetectionTests(RevenueTestCase):

    def net_world(self):
        """Net revenue: day 0 = 80, day 1 = 130, day 2 = 40."""
        order = self.order("DELIVERED", "100.00", at=at(0))
        paid = self.payment(order, "PAID", "100.00", paid_at=at(0))
        self.refund(paid, "20.00", order=order, at=at(0))
        self.order("DELIVERED", "130.00", at=at(1))
        self.order("DELIVERED", "40.00", at=at(2))
        for index in range(3):
            self.revenue_metrics(period_start=day(index)[0], period_end=day(index)[1])

    def detect(self, current=1, previous=0, **overrides):
        params = dict(
            business_id=self.business.pk, period_type="DAY",
            current_period_start=day(current)[0], current_period_end=day(current)[1],
        )
        if previous is not None:
            params.update(
                previous_period_start=day(previous)[0],
                previous_period_end=day(previous)[1],
            )
        params.update(overrides)
        return revenue.detect_revenue_change(**params)

    def test_previous_period_comparison_reports_exact_change(self):
        self.net_world()
        change = self.detect()
        self.assertEqual(change.metric_key, NET)
        self.assertEqual(change.calculation_rule, rule(NET))
        self.assertEqual(change.comparison_basis, revenue.COMPARISON_PREVIOUS_PERIOD)
        self.assertEqual(change.current.value, D("130.000000"))
        self.assertEqual(change.previous.value, D("80.000000"))
        self.assertEqual(change.absolute_change, D("50.000000"))
        self.assertEqual(change.relative_change, D("0.625"))
        self.assertEqual(change.direction, metrics.DIRECTION_INCREASED)
        self.assertIsNone(change.baseline_value)
        self.assertEqual(change.baseline_observation_ids, ())

    def test_decrease_is_reported_with_a_negative_relative_change(self):
        self.net_world()
        change = self.detect(current=2, previous=1)
        self.assertEqual(change.absolute_change, D("-90.000000"))
        self.assertEqual(change.direction, metrics.DIRECTION_DECREASED)
        self.assertLess(abs(change.relative_change + D("0.6923076923")), D("0.000000001"))

    def test_unchanged_value_is_reported_as_unchanged(self):
        self.order("DELIVERED", "60.00", at=at(0))
        self.order("DELIVERED", "60.00", at=at(1))
        for index in (0, 1):
            self.revenue_metrics(period_start=day(index)[0], period_end=day(index)[1])
        change = self.detect()
        self.assertEqual(change.direction, metrics.DIRECTION_UNCHANGED)
        self.assertEqual(change.absolute_change, D("0.000000"))
        self.assertEqual(change.relative_change, D("0"))

    def test_without_a_supplied_threshold_significance_is_not_decided(self):
        self.net_world()
        change = self.detect()
        self.assertIsNone(change.is_significant)
        criteria = change.significance_criteria
        self.assertEqual(criteria["threshold_source"], "NOT_SUPPLIED")
        self.assertIsNone(criteria["significant_change_ratio"])
        self.assertIsNone(criteria["significant_absolute_change"])
        self.assertEqual(criteria["evaluated_criteria"], 0)

    def test_ratio_threshold_is_the_callers_and_inclusive(self):
        self.net_world()
        cases = (
            (D("0.625"), True), (D("0.624999"), True), (D("0.626"), False),
            (D("0"), True), (D("5"), False),
        )
        for threshold, expected in cases:
            with self.subTest(ratio=threshold):
                change = self.detect(significant_change_ratio=threshold)
                self.assertIs(change.is_significant, expected)
                self.assertEqual(change.significance_criteria["threshold_source"], "CALLER_SUPPLIED")
                self.assertEqual(change.significance_criteria["evaluated_criteria"], 1)

    def test_absolute_threshold_is_the_callers_and_inclusive(self):
        self.net_world()
        cases = ((D("50"), True), (D("49.99"), True), (D("50.01"), False))
        for threshold, expected in cases:
            with self.subTest(absolute=threshold):
                change = self.detect(significant_absolute_change=threshold)
                self.assertIs(change.is_significant, expected)

    def test_two_thresholds_are_alternatives(self):
        self.net_world()
        both_fail = self.detect(
            significant_change_ratio=D("0.9"), significant_absolute_change=D("90")
        )
        self.assertIs(both_fail.is_significant, False)
        self.assertEqual(both_fail.significance_criteria["evaluated_criteria"], 2)
        one_passes = self.detect(
            significant_change_ratio=D("0.9"), significant_absolute_change=D("10")
        )
        self.assertIs(one_passes.is_significant, True)

    def test_thresholds_must_be_non_negative_finite_decimals(self):
        self.net_world()
        bad = [0.5, 1, "0.5", True, D("-0.1"), D("NaN"), D("Infinity")]
        for value in bad:
            for parameter in ("significant_change_ratio", "significant_absolute_change"):
                with self.subTest(parameter=parameter, value=value):
                    with self.assertRaises(revenue.RevenueValidationError):
                        self.detect(**{parameter: value})

    def test_missing_previous_observation_is_unavailable_even_with_thresholds(self):
        self.net_world()
        change = self.detect(  # day -1 ends before day 1 starts but has no snapshot
            current=1, previous=-1, significant_change_ratio=D("0.1"),
            significant_absolute_change=D("1"),
        )
        self.assertIsNone(change.previous)
        self.assertIsNone(change.absolute_change)
        self.assertIsNone(change.relative_change)
        self.assertEqual(change.direction, metrics.DIRECTION_UNAVAILABLE)
        self.assertIsNone(change.is_significant)
        criteria = change.significance_criteria
        self.assertEqual(criteria["threshold_source"], "CALLER_SUPPLIED")
        self.assertEqual(criteria["evaluated_criteria"], 0)
        self.assertEqual(criteria["relative_change_unavailable_reason"], "MISSING_OBSERVATION")

    def test_missing_current_observation_is_unavailable(self):
        self.net_world()
        change = self.detect(current=6, previous=0)
        self.assertIsNone(change.current)
        self.assertEqual(change.direction, metrics.DIRECTION_UNAVAILABLE)
        self.assertIsNone(change.absolute_change)
        self.assertIsNone(change.is_significant)

    def test_zero_previous_value_has_no_relative_change_but_keeps_the_absolute(self):
        self.revenue_metrics(period_start=day(0)[0], period_end=day(0)[1])  # measured 0
        self.order("DELIVERED", "130.00", at=at(1))
        self.revenue_metrics(period_start=day(1)[0], period_end=day(1)[1])
        change = self.detect()
        self.assertEqual(change.previous.value, D("0.000000"))
        self.assertEqual(change.absolute_change, D("130.000000"))
        self.assertIsNone(change.relative_change)
        self.assertEqual(
            change.significance_criteria["relative_change_unavailable_reason"],
            "ZERO_REFERENCE_VALUE",
        )
        self.assertIsNone(self.detect(significant_change_ratio=D("0.1")).is_significant)
        self.assertIs(
            self.detect(significant_absolute_change=D("100")).is_significant, True
        )

    def test_baseline_mean_of_recorded_observations(self):
        self.seed(NET, "100", start=day(0)[0], end=day(0)[1])
        self.seed(NET, "101", start=day(1)[0], end=day(1)[1])
        self.seed(NET, "150.75", start=day(2)[0], end=day(2)[1])
        change = self.detect(
            current=2, previous=None,
            baseline_window_start=day(0)[0], baseline_window_end=day(2)[0],
        )
        self.assertEqual(change.comparison_basis, revenue.COMPARISON_BASELINE_MEAN)
        self.assertEqual(change.baseline_value, D("100.5"))
        self.assertEqual(len(change.baseline_observation_ids), 2)
        self.assertEqual(
            change.baseline_observation_ids,
            tuple(
                self.obs(NET, start=day(i)[0], end=day(i)[1]).snapshot_id for i in (0, 1)
            ),
        )
        self.assertIsNone(change.previous)
        self.assertEqual(change.absolute_change, D("50.25"))
        self.assertEqual(change.relative_change, D("0.5"))
        self.assertEqual(change.direction, metrics.DIRECTION_INCREASED)
        self.assertIsNone(change.is_significant)

    def test_baseline_ignores_other_rules_period_types_and_dimensions(self):
        self.seed(NET, "100", start=day(0)[0], end=day(0)[1])
        self.seed(NET, "101", start=day(1)[0], end=day(1)[1])
        self.seed(NET, "150.75", start=day(2)[0], end=day(2)[1])
        # In the window but not comparable: bare rule, other period type, other scope.
        self.seed(
            NET, "9999", start=day(0)[0] + timedelta(hours=1),
            end=day(0)[0] + timedelta(hours=2), calculation_rule=None,
        )
        metrics.record_metric_snapshot(
            business_id=self.business.pk, metric_key=NET, value=D("9999"),
            period_type="WEEK", period_start=day(0)[0], period_end=day(0)[0] + 7 * DAY,
            calculation_rule=rule(NET),
        )
        self.seed(
            NET, "9999", start=day(1)[0], end=day(1)[1],
            dimension_type="CURRENCY", dimension_value="BDT",
        )
        change = self.detect(
            current=2, previous=None,
            baseline_window_start=day(0)[0], baseline_window_end=day(2)[0],
        )
        self.assertEqual(len(change.baseline_observation_ids), 2)
        self.assertEqual(change.baseline_value, D("100.5"))

    def test_baseline_window_may_end_at_but_not_after_the_current_period_start(self):
        self.seed(NET, "100", start=day(0)[0], end=day(0)[1])
        self.seed(NET, "150", start=day(1)[0], end=day(1)[1])
        touching = self.detect(
            current=1, previous=None,
            baseline_window_start=day(0)[0], baseline_window_end=day(1)[0],
        )
        self.assertEqual(touching.baseline_value, D("100"))
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(
                current=1, previous=None,
                baseline_window_start=day(0)[0], baseline_window_end=day(1)[0] + DAY,
            )
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(
                current=1, previous=None,
                baseline_window_start=day(1)[0], baseline_window_end=day(2)[0],
            )

    def test_empty_baseline_is_unavailable(self):
        self.seed(NET, "150", start=day(5)[0], end=day(5)[1])
        change = self.detect(
            current=5, previous=None,
            baseline_window_start=day(0)[0], baseline_window_end=day(5)[0],
            significant_change_ratio=D("0.1"),
        )
        self.assertIsNone(change.baseline_value)
        self.assertEqual(change.baseline_observation_ids, ())
        self.assertIsNone(change.absolute_change)
        self.assertIsNone(change.relative_change)
        self.assertEqual(change.direction, metrics.DIRECTION_UNAVAILABLE)
        self.assertIsNone(change.is_significant)
        self.assertEqual(change.current.value, D("150.000000"))

    def test_exactly_one_comparison_input_is_required(self):
        self.net_world()
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(
                baseline_window_start=day(0)[0], baseline_window_end=day(1)[0],
            )
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(previous=None)
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(previous=None, previous_period_start=day(0)[0])

    def test_previous_period_overlapping_the_current_one_is_refused(self):
        self.net_world()
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(current=1, previous=1)
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(current=1, previous=2)

    def test_snapshots_under_another_rule_are_refused(self):
        self.seed(NET, "100", start=day(0)[0], end=day(0)[1], calculation_rule=None)
        self.seed(NET, "130", start=day(1)[0], end=day(1)[1])
        with self.assertRaises(revenue.RevenueScopeError):
            self.detect()  # previous written under the bare rule
        self.seed(NET, "100", start=day(2)[0], end=day(2)[1])
        self.seed(NET, "130", start=day(3)[0], end=day(3)[1], calculation_rule=None)
        with self.assertRaises(revenue.RevenueScopeError):
            self.detect(current=3, previous=2)  # current written under the bare rule

    def test_metric_key_choice_is_closed_to_recorded_observations(self):
        self.net_world()
        self.assertEqual(self.detect(metric_key=GROSS).metric_key, GROSS)
        self.assertEqual(self.detect(metric_key=GROSS).current.value, D("130.000000"))
        for bad in (REVENUE_GROWTH, SALES_GROWTH, "bi.metric.nope.v1", None, 5):
            with self.subTest(metric_key=bad):
                with self.assertRaises(revenue.RevenueValidationError):
                    self.detect(metric_key=bad)

    def test_detection_is_read_only(self):
        self.net_world()
        before = list(models.MetricSnapshot.objects.order_by("pk").values())
        self.detect(significant_change_ratio=D("0.1"))
        self.detect(
            current=2, previous=None,
            baseline_window_start=day(0)[0], baseline_window_end=day(2)[0],
        )
        self.assertEqual(list(models.MetricSnapshot.objects.order_by("pk").values()), before)

    def test_detection_rejects_a_dimension_from_another_business(self):
        foreign = self.campaign("Foreign", business=self.other)
        with self.assertRaises(revenue.RevenueValidationError):
            self.detect(dimension_type="CAMPAIGN", dimension_value=str(foreign.pk))


# ==========================================================================
# 10. Campaign revenue (platform-reported, T-001 relationships only)
# ==========================================================================

class CampaignRevenueTests(RevenueTestCase):

    def campaign_world(self):
        self.buyer1 = self.customer()
        self.buyer2 = self.customer()
        self.c1 = self.campaign("C1")
        self.c2 = self.campaign("C2")
        self.o1 = self.order("DELIVERED", "100.00", customer=self.buyer1)
        self.o2 = self.order("CONFIRMED", "50.00", customer=self.buyer2)
        self.o3 = self.order("DELIVERED", "30.00", customer=self.buyer1)  # reported twice
        self.o4 = self.order("DELIVERED", "1000.00")  # reported by no campaign
        self.item(self.o1, self.product("A"), 2, "100.00")
        self.item(self.o3, self.product("B"), 1, "30.00")
        self.convert(self.c1, self.o1, external="a")
        self.convert(self.c1, self.o1, external="b")  # duplicate report, same order
        self.convert(self.c1, self.o3, external="c")
        self.convert(self.c2, self.o3, external="d")
        self.convert(self.c2, self.o2, external="e")
        self.rebuild()

    def scope(self, campaign):
        return dict(dimension_type="CAMPAIGN", dimension_value=str(campaign.pk))

    def test_campaign_scope_uses_only_reported_order_relationships(self):
        self.campaign_world()
        first = self.calc(**self.scope(self.c1))
        self.assertEqual(first.counted_orders, 2)  # o1 once despite two reports, and o3
        self.assertEqual(first.gross_amount, D("130.00"))
        self.assertEqual(first.units_sold, 3)
        self.assertEqual(first.distinct_customers, 1)
        self.assertEqual(first.scope.basis, CAMPAIGN_ORDERS)
        coverage = first.coverage
        self.assertEqual(coverage["campaign_link_rule"], "bi.relationship.campaign_order.v1")
        self.assertEqual(coverage["campaign_link_provenance"], "PLATFORM_REPORTED")
        second = self.calc(**self.scope(self.c2))
        self.assertEqual(second.gross_amount, D("80.00"))
        self.assertEqual(second.distinct_customers, 2)
        self.assertEqual(self.calc().gross_amount, D("1180.00"))

    def test_campaign_figures_are_recorded_under_the_reported_campaign_rules(self):
        self.campaign_world()
        scope = self.scope(self.c1)
        self.sales(**scope)
        self.revenue_metrics(**scope)
        dims = dict(dimension_type="CAMPAIGN", dimension_value=str(self.c1.pk))
        expected = {
            TOTAL_ORDERS: ("2.000000", "bi.metric.sales_total_orders.v1.reported_campaign_orders_all_statuses"),
            UNITS_SOLD: ("3.000000", "bi.metric.sales_units_sold.v1.reported_campaign_orders_items"),
            AOV: ("65.000000", "bi.metric.sales_average_order_value.v1.reported_campaign_orders"),
            CANCELLATION: ("0.000000", "bi.metric.sales_cancellation_rate.v1.reported_campaign_orders_all_statuses"),
            GROSS: ("130.000000", "bi.metric.revenue_gross.v1.reported_campaign_orders"),
            REFUNDED: ("0.000000", "bi.metric.revenue_refunded.v1.refunds_completed_reported_campaign"),
            NET: ("130.000000", "bi.metric.revenue_net.v1.reported_campaign_orders_less_refunds"),
            PER_CUSTOMER: ("130.000000", "bi.metric.revenue_per_customer.v1.reported_campaign_orders_resolved_customers"),
        }
        for key, (value, calculation_rule) in expected.items():
            with self.subTest(metric=key):
                observation = self.obs(key, **dims)
                self.assertEqual(observation.value, D(value))
                self.assertEqual(observation.calculation_rule, calculation_rule)
                self.assertEqual(observation.dimension_type, "CAMPAIGN")
        self.assertIsNone(self.obs(GROSS))  # nothing leaked into the business-wide scope

    def test_nothing_is_ever_written_to_marketing_attributed_revenue(self):
        self.campaign_world()
        for campaign in (self.c1, self.c2):
            self.sales(**self.scope(campaign))
            self.revenue_metrics(**self.scope(campaign))
        self.record_breakdown("CAMPAIGN")
        self.assertGreater(self.snapshot_count(), 0)
        self.assertEqual(
            models.MetricSnapshot.objects.filter(metric__key=MARKETING_ATTRIBUTED).count(), 0
        )
        self.assertEqual(
            models.MetricSnapshot.objects.filter(metric__key__contains="attributed").count(), 0
        )
        written_keys = set(
            models.MetricSnapshot.objects.values_list("metric__key", flat=True)
        )
        self.assertLessEqual(written_keys, set(SALES_KEYS + REVENUE_KEYS))
        for row in models.MetricSnapshot.objects.all():
            self.assertNotIn("attributed", row.calculation_rule)

    def test_orders_reported_by_two_campaigns_count_in_each_and_are_flagged(self):
        self.campaign_world()
        summary = self.breakdown("CAMPAIGN")
        self.assertEqual(summary.breakdown, "CAMPAIGN")
        rows = {row.dimension_value: row for row in summary.rows}
        self.assertEqual(set(rows), {str(self.c1.pk), str(self.c2.pk)})
        first, second = rows[str(self.c1.pk)], rows[str(self.c2.pk)]
        self.assertEqual((first.gross_amount, first.order_count, first.units), (D("130.00"), 2, 3))
        self.assertEqual((second.gross_amount, second.order_count, second.units), (D("80.00"), 2, 1))
        self.assertEqual([row.dimension_value for row in summary.rows],
                         [str(self.c1.pk), str(self.c2.pk)])  # descending amount
        for row in summary.rows:
            self.assertEqual(row.dimension_type, "CAMPAIGN")
            self.assertTrue(row.recordable)
        coverage = summary.coverage
        self.assertIs(coverage["additive"], False)
        self.assertEqual(coverage["orders_reported_by_multiple_campaigns"], 1)
        self.assertEqual(coverage["orders_without_reported_campaign"], 1)
        self.assertEqual(coverage["campaign_link_provenance"], "PLATFORM_REPORTED")
        self.assertEqual(coverage["campaign_link_rule"], "bi.relationship.campaign_order.v1")
        # The sum of the rows (210) exceeds the revenue those campaigns reported (180).
        self.assertEqual(sum(row.gross_amount for row in summary.rows), D("210.00"))

    def test_recorded_campaign_breakdown_carries_the_non_additive_flags(self):
        self.campaign_world()
        written = self.record_breakdown("CAMPAIGN")
        self.assertEqual(written.skipped_rows, 0)
        self.assertEqual(len(written.results), 2)  # revenue_gross only, no item metrics
        inputs = self.inputs(
            GROSS, dimension_type="CAMPAIGN", dimension_value=str(self.c1.pk)
        )
        self.assertIs(inputs["additive"], False)
        self.assertEqual(inputs["orders_reported_by_multiple_campaigns"], 1)
        self.assertEqual(inputs["campaign_link_provenance"], "PLATFORM_REPORTED")
        self.assertEqual(
            self.obs(GROSS, dimension_type="CAMPAIGN", dimension_value=str(self.c1.pk)).value,
            D("130.000000"),
        )

    def test_campaign_breakdown_snapshots_use_the_reported_campaign_rule(self):
        """SPEC: revenue.py says campaign variants carry ``reported_campaign`` so
        platform-reported revenue is never mistaken for another basis; the
        breakdown must record under the same rule as the campaign scope.
        """
        self.campaign_world()
        self.record_breakdown("CAMPAIGN")
        recorded = self.obs(
            GROSS, dimension_type="CAMPAIGN", dimension_value=str(self.c1.pk)
        )
        self.assertEqual(recorded.calculation_rule, rule(GROSS, CAMPAIGN_ORDERS))
        self.assertIn("reported_campaign", recorded.calculation_rule)

    def test_expired_relationship_no_longer_counts(self):
        self.campaign_world()
        models.CampaignConversion.objects.filter(campaign=self.c1, order=self.o3).delete()
        self.rebuild()
        link = models.BusinessRelationship.objects.get(
            source_entity_type="CAMPAIGN", source_entity_id=self.c1.pk,
            relationship_type="REPORTED_ORDER", target_entity_type="ORDER",
            target_entity_id=self.o3.pk,
        )
        self.assertIsNotNone(link.valid_to)
        self.assertEqual(self.calc(**self.scope(self.c1)).gross_amount, D("100.00"))
        self.assertEqual(self.calc(**self.scope(self.c2)).gross_amount, D("80.00"))

    def test_only_deterministic_campaign_order_rule_links_are_used(self):
        self.campaign_world()
        common = dict(
            business_id=self.business.pk, source_entity_type="CAMPAIGN",
            source_entity_id=self.c1.pk, relationship_type="REPORTED_ORDER",
            target_entity_type="ORDER", confidence=D("1.0000"), metadata={},
            valid_from=STAMP, valid_to=None, created_at=STAMP, updated_at=STAMP,
        )
        models.BusinessRelationship.objects.create(
            target_entity_id=self.o4.pk, rule_key="bi.relationship.campaign_order.v1",
            relationship_source="MANUAL", **common,
        )
        models.BusinessRelationship.objects.create(
            target_entity_id=self.o2.pk, rule_key="bi.relationship.some_other_rule.v1",
            relationship_source="DETERMINISTIC", **common,
        )
        result = self.calc(**self.scope(self.c1))
        self.assertEqual(result.gross_amount, D("130.00"))
        self.assertEqual(result.counted_orders, 2)

    def test_campaign_refunds_follow_the_order_or_the_payments_order(self):
        self.campaign_world()
        p1 = self.payment(self.o1, "PAID", "100.00")
        p3 = self.payment(self.o3, "PAID", "30.00")
        orphan = self.payment(None, "PAID", "9.00")
        self.refund(p1, "10.00", order=self.o1)
        self.refund(p3, "5.00", order=None)  # attributed through payment.order = o3
        self.refund(orphan, "9.00", order=None)  # attributable to no campaign
        first = self.call("compute_refund_impact", **self.scope(self.c1))
        self.assertEqual(first.refunded_amount, D("15.00"))
        self.assertEqual(first.refund_count, 2)
        self.assertEqual(first.coverage["refunds_excluded_without_order_scope"], 1)
        second = self.call("compute_refund_impact", **self.scope(self.c2))
        self.assertEqual(second.refunded_amount, D("5.00"))
        self.revenue_metrics(**self.scope(self.c1))
        dims = dict(dimension_type="CAMPAIGN", dimension_value=str(self.c1.pk))
        self.assertEqual(self.obs(REFUNDED, **dims).value, D("15.000000"))
        self.assertEqual(self.obs(NET, **dims).value, D("115.000000"))

    def test_campaign_reconciliation_scopes_payments_through_reported_orders(self):
        self.campaign_world()
        self.payment(self.o1, "PAID", "100.00")
        self.payment(self.o3, "PAID", "30.00")
        self.payment(self.o4, "PAID", "1000.00")
        self.payment(None, "PAID", "9.00")
        reconciliation = self.call("reconcile_revenue", **self.scope(self.c1))
        self.assertEqual(reconciliation.gross_order_amount, D("130.00"))
        self.assertEqual(reconciliation.received_payment_amount, D("130.00"))
        self.assertEqual(reconciliation.order_payment_difference, D("0.00"))
        self.assertEqual(
            reconciliation.coverage["payments_excluded_without_order_scope"], 1
        )

    def test_campaign_without_reported_orders_is_an_empty_scope_not_a_leak(self):
        self.campaign_world()
        quiet = self.campaign("Quiet")
        result = self.calc(**self.scope(quiet))
        self.assertEqual(result.counted_orders, 0)
        self.assertEqual(result.gross_amount, D("0"))
        self.assertEqual(self.call("compute_payment_receipts", **self.scope(quiet)).received_amount, D("0"))
        self.assertEqual(self.call("compute_refund_impact", **self.scope(quiet)).refunded_amount, D("0"))
        written = self.revenue_metrics(**self.scope(quiet))
        self.assertEqual(written.results[GROSS].observation.value, D("0.000000"))
        self.assertEqual(
            written.results[PER_CUSTOMER].status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE
        )


# ==========================================================================
# 11. Tenant isolation
# ==========================================================================

class TenantIsolationTests(RevenueTestCase):

    def foreign_world(self):
        """Everything lives in the other business."""
        self.f_product = self.product("Foreign product", business=self.other)
        self.f_order = self.order("DELIVERED", "777.00", business=self.other)
        self.item(self.f_order, self.f_product, 9, "777.00")
        self.f_payment = self.payment(self.f_order, "PAID", "777.00", business=self.other)
        self.refund(self.f_payment, "77.00", order=self.f_order)
        self.f_campaign = self.campaign("Foreign", business=self.other)
        self.convert(self.f_campaign, self.f_order)
        self.f_customer = self.customer(business=self.other)
        self.tag(self.f_customer, "VIP")
        self.rebuild(self.other)

    def test_another_business_contributes_to_no_figure(self):
        self.foreign_world()
        order = self.order("DELIVERED", "100.00")
        self.payment(order, "PAID", "100.00")
        result = self.calc()
        self.assertEqual(result.gross_amount, D("100.00"))
        self.assertEqual(result.counted_orders, 1)
        self.assertEqual(result.units_sold, 0)
        self.assertEqual(self.call("compute_payment_receipts").received_amount, D("100.00"))
        self.assertEqual(self.call("compute_refund_impact").refunded_amount, D("0"))
        self.assertEqual(self.call("reconcile_revenue").net_order_amount, D("100.00"))

    def test_empty_business_sees_empty_scopes_not_the_other_tenants_data(self):
        self.foreign_world()
        self.assertEqual(self.calc().counted_orders, 0)
        self.assertEqual(self.calc().gross_amount, D("0"))
        self.assertEqual(self.call("compute_payment_receipts").received_amount, D("0"))
        self.assertEqual(self.call("compute_refund_impact").refunded_amount, D("0"))
        for name in ("PRODUCT", "CAMPAIGN", "CHANNEL", "CUSTOMER_SEGMENT", "CURRENCY", "CUSTOMER"):
            with self.subTest(breakdown=name):
                self.assertEqual(self.breakdown(name).rows, ())
        self.sales()
        self.revenue_metrics()
        self.assertEqual(self.obs(TOTAL_ORDERS).value, D("0.000000"))
        self.assertEqual(self.obs(GROSS).value, D("0.000000"))
        self.assertEqual(self.obs(NET).value, D("0.000000"))
        self.assertEqual(
            models.MetricSnapshot.objects.exclude(business=self.business).count(), 0
        )
        for row in models.MetricSnapshot.objects.select_related("metric"):
            self.assertEqual(row.business_id, self.business.pk)
            self.assertEqual(row.metric.business_id, self.business.pk)

    def test_caller_supplied_foreign_campaign_id_is_rejected_everywhere(self):
        self.foreign_world()
        scope = dict(dimension_type="CAMPAIGN", dimension_value=str(self.f_campaign.pk))
        for name in CALCULATIONS + RECORDINGS:
            with self.subTest(operation=name):
                with self.assertRaises(revenue.RevenueValidationError):
                    self.call(name, **scope)
        self.assertEqual(self.snapshot_count(), 0)

    def test_nonexistent_campaign_id_is_rejected_like_a_foreign_one(self):
        for name in CALCULATIONS + RECORDINGS:
            with self.subTest(operation=name):
                with self.assertRaises(revenue.RevenueValidationError):
                    self.call(name, dimension_type="CAMPAIGN", dimension_value="999999")

    def test_item_referencing_another_businesss_product_is_excluded_and_counted(self):
        foreign_product = self.product("Foreign", business=self.other)
        own_product = self.product("Own")
        order = self.order("DELIVERED", "90.00")
        self.item(order, own_product, 1, "40.00")
        self.item(order, foreign_product, 5, "50.00")
        summary = self.breakdown("PRODUCT")
        self.assertEqual([row.dimension_value for row in summary.rows], [str(own_product.pk)])
        self.assertEqual(summary.rows[0].gross_amount, D("40.00"))
        self.assertEqual(summary.coverage["order_items_with_foreign_product"], 1)
        written = self.record_breakdown("PRODUCT")  # must not abort the transaction
        self.assertEqual(len(written.results), 2)
        self.assertEqual(
            models.MetricSnapshot.objects.filter(
                dimension_type="PRODUCT", dimension_value=str(foreign_product.pk)
            ).count(),
            0,
        )

    def test_item_referencing_another_businesss_variant_is_excluded_and_counted(self):
        foreign_variant = self.variant(self.product("Foreign", business=self.other))
        own_variant = self.variant(self.product("Own"))
        order = self.order("DELIVERED", "90.00")
        self.item(order, None, 1, "40.00", variant=own_variant)
        self.item(order, None, 1, "50.00", variant=foreign_variant)
        summary = self.breakdown("PRODUCT_VARIANT")
        self.assertEqual([row.dimension_value for row in summary.rows], [str(own_variant.pk)])
        self.assertEqual(summary.coverage["order_items_with_foreign_product"], 1)

    def test_order_on_another_businesss_connection_has_no_channel_here(self):
        foreign_connection = self.connection("shopify", business=self.other)
        own_connection = self.connection("shopify")
        self.order("DELIVERED", "10.00", connection=foreign_connection)
        self.order("DELIVERED", "20.00", connection=own_connection)
        scoped = self.calc(dimension_type="CHANNEL", dimension_value="shopify")
        self.assertEqual(scoped.gross_amount, D("20.00"))
        summary = self.breakdown("CHANNEL")
        self.assertEqual(len(summary.rows), 1)
        self.assertEqual(summary.rows[0].gross_amount, D("20.00"))
        self.assertEqual(summary.coverage["orders_with_foreign_integration_connection"], 1)

    def test_segment_tags_of_another_businesss_customers_do_not_scope_orders(self):
        foreign_customer = self.customer(business=self.other)
        self.tag(foreign_customer, "VIP")
        self.order("DELIVERED", "10.00", customer=foreign_customer)  # integrity break
        own = self.customer()
        self.order("DELIVERED", "20.00", customer=own)
        scoped = self.calc(dimension_type="CUSTOMER_SEGMENT", dimension_value="VIP")
        self.assertEqual(scoped.counted_orders, 0)
        self.assertEqual(self.breakdown("CUSTOMER_SEGMENT").rows, ())

    def test_unsynchronized_registry_is_refused_but_calculations_still_read(self):
        bare = self.make_business("Bare shop", "bare-shop", sync=False)
        self.order("DELIVERED", "50.00", business=bare)
        read = revenue.compute_order_revenue(
            business_id=bare.pk, period_start=START, period_end=END
        )
        self.assertEqual(read.gross_amount, D("50.00"))
        for function in (revenue.record_sales_metrics, revenue.record_revenue_metrics):
            with self.subTest(function=function.__name__):
                with self.assertRaises(metrics.MetricValidationError):
                    function(
                        business_id=bare.pk, period_type="DAY",
                        period_start=START, period_end=END,
                    )
        self.assertEqual(self.snapshot_count(), 0)


# ==========================================================================
# 12. Breakdowns: product, variant, category, customer, channel, segment, currency
# ==========================================================================

class BreakdownTests(RevenueTestCase):

    def product_world(self):
        self.alpha = self.product("Alpha", category="Shoes")
        self.beta = self.product("Beta", category="Shoes")
        self.gamma = self.product("Gamma", category="Hats")
        self.sale_a = self.order("DELIVERED", "120.00")  # 100.00 of items + 20.00 shipping
        self.item(self.sale_a, self.alpha, 2, "100.00")
        self.sale_b = self.order("CONFIRMED", "80.00")
        self.item(self.sale_b, self.beta, 1, "40.00")
        self.item(self.sale_b, self.gamma, 4, "40.00")
        self.pending = self.order("PENDING", "500.00")
        self.item(self.pending, self.alpha, 9, "500.00")
        self.cancelled = self.order("CANCELLED", "500.00")
        self.item(self.cancelled, self.beta, 9, "500.00")
        self.generic = self.order("DELIVERED", "10.00")
        self.item(self.generic, None, 1, "10.00")

    def test_product_breakdown_is_item_based_ordered_and_deterministic(self):
        self.product_world()
        summary = self.breakdown("PRODUCT")
        self.assertEqual(summary.basis, ITEMS)
        top = summary.rows[0]
        self.assertEqual(
            (top.dimension_value, top.gross_amount, top.order_count, top.units),
            (str(self.alpha.pk), D("100.00"), 1, 2),
        )
        tied = {str(self.beta.pk): (D("40.00"), 1, 1), str(self.gamma.pk): (D("40.00"), 1, 4)}
        self.assertEqual(
            [row.dimension_value for row in summary.rows[1:]], sorted(tied)
        )
        for row in summary.rows[1:]:
            self.assertEqual((row.gross_amount, row.order_count, row.units), tied[row.dimension_value])
        self.assertEqual(summary.total_gross_amount, D("180.00"))
        coverage = summary.coverage
        self.assertEqual(coverage["breakdown_rows"], 3)
        self.assertEqual(coverage["rows_returned"], 3)
        self.assertEqual(coverage["order_items_without_breakdown_key"], 1)
        self.assertEqual(coverage["dimension_type"], "PRODUCT")
        self.assertIs(coverage["additive"], True)
        self.assertIn("item_basis_note", coverage)

    def test_item_totals_exclude_shipping_so_they_differ_from_order_gross(self):
        self.product_world()
        self.assertEqual(self.calc().gross_amount, D("210.00"))
        self.assertEqual(self.breakdown("PRODUCT").total_gross_amount, D("180.00"))

    def test_pending_and_cancelled_orders_never_contribute_to_product_revenue(self):
        self.product_world()
        values = {row.dimension_value: row for row in self.breakdown("PRODUCT").rows}
        self.assertEqual(values[str(self.alpha.pk)].gross_amount, D("100.00"))
        self.assertEqual(values[str(self.beta.pk)].gross_amount, D("40.00"))

    def test_product_category_breakdown_is_returned_but_not_recordable(self):
        self.product_world()
        summary = self.breakdown("PRODUCT_CATEGORY")
        self.assertEqual(
            [(row.dimension_value, row.gross_amount, row.order_count, row.units) for row in summary.rows],
            [("Shoes", D("140.00"), 2, 3), ("Hats", D("40.00"), 1, 4)],
        )
        for row in summary.rows:
            self.assertFalse(row.recordable)
            self.assertIsNone(row.dimension_type)
        self.assertEqual(summary.coverage["dimension_type"], "NOT_EXPRESSIBLE")
        self.assertIn("not_recordable_reason", summary.coverage)

    def test_unrecordable_breakdowns_are_skipped_and_counted_not_squeezed(self):
        self.product_world()
        written = self.record_breakdown("PRODUCT_CATEGORY")
        self.assertEqual(written.results, ())
        self.assertEqual(written.skipped_rows, 2)
        self.assertEqual(self.snapshot_count(), 0)
        customer = self.customer()
        self.order("DELIVERED", "30.00", customer=customer)
        by_customer = self.record_breakdown("CUSTOMER")
        self.assertEqual(by_customer.results, ())
        self.assertEqual(by_customer.skipped_rows, 1)
        self.assertEqual(self.snapshot_count(), 0)

    def test_customer_breakdown_groups_by_resolved_customer(self):
        first, second = self.customer(), self.customer()
        self.order("DELIVERED", "30.00", customer=first)
        self.order("DELIVERED", "20.00", customer=first)
        self.order("DELIVERED", "40.00", customer=second)
        self.order("DELIVERED", "5.00")
        summary = self.breakdown("CUSTOMER")
        self.assertEqual(
            [(row.dimension_value, row.gross_amount, row.order_count) for row in summary.rows],
            [(str(first.pk), D("50.00"), 2), (str(second.pk), D("40.00"), 1)],
        )
        self.assertEqual(summary.coverage["orders_without_breakdown_key"], 1)

    def test_recorded_product_breakdown_writes_revenue_and_units_per_product(self):
        self.product_world()
        written = self.record_breakdown("PRODUCT")
        self.assertEqual(written.skipped_rows, 0)
        self.assertEqual(len(written.results), 6)
        dims = lambda product: dict(  # noqa: E731
            dimension_type="PRODUCT", dimension_value=str(product.pk)
        )
        expectations = (
            (self.alpha, "100.000000", "2.000000"),
            (self.beta, "40.000000", "1.000000"),
            (self.gamma, "40.000000", "4.000000"),
        )
        for product, money, units in expectations:
            with self.subTest(product=product.name):
                gross = self.obs(GROSS, **dims(product))
                self.assertEqual(gross.value, D(money))
                self.assertEqual(gross.calculation_rule, rule(GROSS, ITEMS))
                sold = self.obs(UNITS_SOLD, **dims(product))
                self.assertEqual(sold.value, D(units))
                self.assertEqual(sold.calculation_rule, rule(UNITS_SOLD, ITEMS))
        inputs = self.inputs(GROSS, **dims(self.alpha))
        self.assertEqual(D(inputs["row_gross_amount"]), D("100.00"))
        self.assertEqual(inputs["row_order_count"], 1)
        self.assertEqual(inputs["row_units"], 2)
        self.assertEqual(inputs["dimension_value"], str(self.alpha.pk))

    def test_product_breakdown_never_records_refund_or_net_per_product(self):
        self.product_world()
        paid = self.payment(self.sale_a, "PAID", "120.00")
        self.refund(paid, "20.00", order=self.sale_a)
        self.record_breakdown("PRODUCT")
        self.assertEqual(
            models.MetricSnapshot.objects.filter(
                metric__key__in=[REFUNDED, NET, PER_CUSTOMER]
            ).count(),
            0,
        )

    def test_recorded_breakdown_replay_is_unchanged(self):
        self.product_world()
        with patch(NOW, return_value=CLOCK_A):
            first = self.record_breakdown("PRODUCT")
        count = self.snapshot_count()
        with patch(NOW, return_value=CLOCK_B):
            second = self.record_breakdown("PRODUCT")
        self.assertEqual(self.snapshot_count(), count)
        self.assertEqual(len(first.results), len(second.results))
        for (value_a, key_a, written_a), (value_b, key_b, written_b) in zip(
            first.results, second.results
        ):
            self.assertEqual((value_a, key_a), (value_b, key_b))
            self.assertEqual(written_a.status, metrics.WRITE_CREATED)
            self.assertEqual(written_b.status, metrics.WRITE_UNCHANGED)
            self.assertEqual(
                written_a.observation.snapshot_id, written_b.observation.snapshot_id
            )

    def test_product_variant_breakdown(self):
        product = self.product("Shirt")
        small, large = self.variant(product, "S"), self.variant(product, "L")
        order = self.order("DELIVERED", "90.00")
        self.item(order, product, 1, "30.00", variant=small)
        self.item(order, product, 2, "60.00", variant=large)
        summary = self.breakdown("PRODUCT_VARIANT")
        self.assertEqual(
            [(row.dimension_value, row.gross_amount, row.units) for row in summary.rows],
            [(str(large.pk), D("60.00"), 2), (str(small.pk), D("30.00"), 1)],
        )
        self.assertEqual(summary.basis, ITEMS)
        self.record_breakdown("PRODUCT_VARIANT")
        self.assertEqual(
            self.obs(GROSS, dimension_type="PRODUCT_VARIANT", dimension_value=str(large.pk)).value,
            D("60.000000"),
        )

    def test_limit_returns_the_top_rows_and_reports_how_many_exist(self):
        self.product_world()
        summary = self.breakdown("PRODUCT", limit=1)
        self.assertEqual([row.dimension_value for row in summary.rows], [str(self.alpha.pk)])
        self.assertEqual(summary.coverage["breakdown_rows"], 3)
        self.assertEqual(summary.coverage["rows_returned"], 1)

    def test_limited_breakdown_total_still_covers_every_row(self):
        """SPEC: ``total_gross_amount`` is the base a row's share is measured
        against (§6 product/channel distribution); truncating the list for
        display must not shrink that base to the returned rows.
        """
        self.product_world()
        summary = self.breakdown("PRODUCT", limit=1)
        self.assertEqual(summary.total_gross_amount, D("180.00"))

    def test_channel_breakdown_uses_the_integration_source_key(self):
        shopify, facebook = self.connection("shopify"), self.connection("facebook")
        self.order("DELIVERED", "100.00", connection=shopify)
        self.order("DELIVERED", "50.00", connection=shopify)
        self.order("DELIVERED", "30.00", connection=facebook)
        self.order("DELIVERED", "25.00")
        summary = self.breakdown("CHANNEL")
        self.assertEqual(
            [(row.dimension_value, row.gross_amount, row.order_count) for row in summary.rows],
            [("shopify", D("150.00"), 2), ("facebook", D("30.00"), 1)],
        )
        self.assertEqual(summary.coverage["orders_without_channel"], 1)
        self.assertEqual(summary.coverage["channel_source_field"], "integration_source.key")
        self.assertIs(summary.coverage["additive"], True)
        scoped = self.calc(dimension_type="CHANNEL", dimension_value="shopify")
        self.assertEqual(scoped.gross_amount, D("150.00"))
        self.assertEqual(scoped.coverage["channel_source_field"], "integration_source.key")
        self.record_breakdown("CHANNEL")
        self.assertEqual(
            self.obs(GROSS, dimension_type="CHANNEL", dimension_value="shopify").value,
            D("150.000000"),
        )

    def test_channel_scope_figures_are_recorded_under_the_channel_dimension(self):
        shopify = self.connection("shopify")
        self.order("DELIVERED", "100.00", connection=shopify)
        self.order("DELIVERED", "999.00")
        self.revenue_metrics(dimension_type="CHANNEL", dimension_value="shopify")
        dims = dict(dimension_type="CHANNEL", dimension_value="shopify")
        self.assertEqual(self.obs(GROSS, **dims).value, D("100.000000"))
        self.assertEqual(self.obs(GROSS, **dims).calculation_rule, rule(GROSS, ORDERS))
        self.assertIsNone(self.obs(GROSS))

    def test_customer_segment_breakdown_is_not_additive(self):
        both, vip_only, untagged = self.customer(), self.customer(), self.customer()
        self.tag(both, "VIP")
        self.tag(both, "REPEAT_BUYER")
        self.tag(vip_only, "VIP")
        self.order("DELIVERED", "100.00", customer=both)
        self.order("DELIVERED", "50.00", customer=vip_only)
        self.order("DELIVERED", "20.00", customer=untagged)
        self.order("DELIVERED", "10.00")
        summary = self.breakdown("CUSTOMER_SEGMENT")
        self.assertEqual(
            [(row.dimension_value, row.gross_amount, row.order_count) for row in summary.rows],
            [("VIP", D("150.00"), 2), ("REPEAT_BUYER", D("100.00"), 1)],
        )
        self.assertIs(summary.coverage["additive"], False)
        self.assertEqual(summary.coverage["orders_without_segment"], 2)
        self.assertEqual(summary.coverage["segment_source"], "customer_tags.tag")
        scoped = self.calc(dimension_type="CUSTOMER_SEGMENT", dimension_value="VIP")
        self.assertEqual(scoped.gross_amount, D("150.00"))
        self.assertEqual(scoped.distinct_customers, 2)

    def test_unknown_segment_is_an_empty_scope_for_every_basis(self):
        self.order("DELIVERED", "100.00", customer=self.customer())
        scope = dict(dimension_type="CUSTOMER_SEGMENT", dimension_value="NO_SUCH_TAG")
        self.assertEqual(self.calc(**scope).counted_orders, 0)
        self.assertEqual(self.call("compute_payment_receipts", **scope).received_amount, D("0"))
        self.assertEqual(self.call("compute_refund_impact", **scope).refunded_amount, D("0"))
        self.assertEqual(self.call("reconcile_revenue", **scope).net_order_amount, D("0"))
        written = self.revenue_metrics(**scope)
        self.assertEqual(written.results[GROSS].observation.value, D("0.000000"))

    def test_currency_breakdown_shows_each_currency_without_adding_them(self):
        self.order("DELIVERED", "100.00")
        self.order("DELIVERED", "40.00", currency="USD")
        self.order("DELIVERED", "5.00", currency="USD")
        summary = self.breakdown("CURRENCY")
        self.assertEqual(summary.scope.currency_source, revenue.CURRENCY_SOURCE_PER_ROW)
        self.assertEqual(
            [(row.dimension_value, row.gross_amount, row.order_count) for row in summary.rows],
            [("BDT", D("100.00"), 1), ("USD", D("45.00"), 2)],
        )

    def test_currency_breakdown_total_is_never_a_cross_currency_sum(self):
        """SPEC: revenue.py — "rows are never added together"."""
        self.order("DELIVERED", "100.00")
        self.order("DELIVERED", "45.00", currency="USD")
        summary = self.breakdown("CURRENCY")
        self.assertNotEqual(summary.total_gross_amount, D("145.00"))
        self.record_breakdown("CURRENCY")
        stored = self.inputs(GROSS, dimension_type="CURRENCY", dimension_value="BDT")
        self.assertNotEqual(D(stored["breakdown_total_gross_amount"]), D("145.00"))

    def test_recorded_currency_breakdown_gives_each_currency_its_own_row(self):
        self.order("DELIVERED", "100.00")
        self.order("DELIVERED", "45.00", currency="USD")
        written = self.record_breakdown("CURRENCY")
        self.assertEqual(len(written.results), 2)
        self.assertEqual(
            self.obs(GROSS, dimension_type="CURRENCY", dimension_value="BDT").value,
            D("100.000000"),
        )
        self.assertEqual(
            self.obs(GROSS, dimension_type="CURRENCY", dimension_value="USD").value,
            D("45.000000"),
        )
        self.assertIsNone(self.obs(GROSS))

    def test_currency_breakdown_cannot_be_filtered_to_one_currency(self):
        self.order("DELIVERED", "100.00")
        with self.assertRaises(revenue.RevenueValidationError):
            self.breakdown("CURRENCY", currency="BDT")

    def test_non_currency_breakdown_of_mixed_money_requires_a_currency(self):
        product = self.product("Alpha")
        for currency, total in (("BDT", "10.00"), ("USD", "20.00")):
            self.item(self.order("DELIVERED", total, currency=currency), product, 1, total)
        with self.assertRaises(revenue.RevenueCurrencyMixError):
            self.breakdown("PRODUCT")
        usd = self.breakdown("PRODUCT", currency="USD")
        self.assertEqual(usd.total_gross_amount, D("20.00"))
        self.assertEqual(usd.scope.currency, "USD")

    def test_breakdown_ordering_is_stable_across_calls(self):
        self.product_world()
        first = [row.dimension_value for row in self.breakdown("PRODUCT").rows]
        second = [row.dimension_value for row in self.breakdown("PRODUCT").rows]
        self.assertEqual(first, second)

    def test_breakdown_arguments_are_validated(self):
        cases = {
            "unknown breakdown": dict(breakdown="REGION"),
            "lowercase": dict(breakdown="product"),
            "non string": dict(breakdown=None),
            "zero limit": dict(limit=0),
            "negative limit": dict(limit=-1),
            "bool limit": dict(limit=True),
            "string limit": dict(limit="3"),
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(revenue.RevenueValidationError):
                    self.call("summarize_revenue_breakdown", **overrides)
                with self.assertRaises(revenue.RevenueValidationError):
                    self.call("record_revenue_breakdown", **overrides)
        self.assertEqual(self.snapshot_count(), 0)


# ==========================================================================
# 13. Boundary validation and atomicity
# ==========================================================================

class ValidationAndAtomicityTests(RevenueTestCase):

    ALL = CALCULATIONS + RECORDINGS + BREAKDOWNS

    def test_period_bounds_are_validated_by_every_operation(self):
        naive = datetime(2026, 10, 10)
        cases = {
            "naive start": dict(period_start=naive),
            "naive end": dict(period_end=datetime(2026, 10, 11)),
            "empty period": dict(period_end=START),
            "reversed period": dict(period_start=END, period_end=START),
            "date not datetime": dict(period_start=START.date()),
            "string": dict(period_start="2026-10-10"),
        }
        for label, overrides in cases.items():
            for name in self.ALL:
                with self.subTest(case=label, operation=name):
                    with self.assertRaises(revenue.RevenueValidationError):
                        self.call(name, **overrides)
        self.assertEqual(self.snapshot_count(), 0)

    def test_business_id_is_validated_by_every_operation(self):
        for value in (True, 0, -4, "1", None, 1.0, 10 ** 9):
            for name in self.ALL:
                with self.subTest(business_id=value, operation=name):
                    with self.assertRaises(revenue.RevenueValidationError):
                        self.call(name, business_id=value)

    def test_period_type_is_validated_by_recording_operations(self):
        for value in ("YEAR", "day", None, 5, ""):
            for name in NEEDS_PERIOD_TYPE:
                with self.subTest(period_type=value, operation=name):
                    with self.assertRaises(revenue.RevenueValidationError):
                        self.call(name, period_type=value)
        self.assertEqual(self.snapshot_count(), 0)

    def test_dimension_arguments_are_validated(self):
        campaign = self.campaign("Own")
        cases = {
            "type only": dict(dimension_type="CURRENCY"),
            "value only": dict(dimension_value="BDT"),
            "leading zero id": dict(dimension_type="CAMPAIGN", dimension_value=f"0{campaign.pk}"),
            "non numeric id": dict(dimension_type="CAMPAIGN", dimension_value="abc"),
            "blank value": dict(dimension_type="CHANNEL", dimension_value="   "),
            "non string value": dict(dimension_type="CAMPAIGN", dimension_value=campaign.pk),
        }
        for label, overrides in cases.items():
            for name in CALCULATIONS + RECORDINGS:
                with self.subTest(case=label, operation=name):
                    with self.assertRaises(revenue.RevenueValidationError):
                        self.call(name, **overrides)
        self.assertEqual(self.snapshot_count(), 0)

    def test_item_and_unsupported_dimensions_cannot_scope_an_order_total(self):
        product = self.product("Alpha")
        for dimension_type, value in (
            ("PRODUCT", str(product.pk)), ("PRODUCT_VARIANT", "1"),
            ("REGION", "north"), ("COURIER", "x"), ("NOPE", "x"),
        ):
            for name in CALCULATIONS + RECORDINGS:
                with self.subTest(dimension=dimension_type, operation=name):
                    with self.assertRaises(revenue.RevenueScopeError):
                        self.call(name, dimension_type=dimension_type, dimension_value=value)

    def test_a_failed_late_write_rolls_back_the_earlier_snapshots_of_the_operation(self):
        self.order("DELIVERED", "100.00", customer=self.customer())
        models.BusinessMetric.objects.filter(
            business=self.business, key=CANCELLATION
        ).update(is_active=False)
        with self.assertRaises(metrics.MetricValidationError):
            self.sales()
        self.assertEqual(self.snapshot_count(), 0)

    def test_a_failed_revenue_write_rolls_back_gross_and_refunded(self):
        self.order("DELIVERED", "100.00", customer=self.customer())
        models.BusinessMetric.objects.filter(business=self.business, key=NET).update(
            is_active=False
        )
        with self.assertRaises(metrics.MetricValidationError):
            self.revenue_metrics()
        self.assertEqual(self.snapshot_count(), 0)

    def test_a_failed_breakdown_write_rolls_back_every_row(self):
        product = self.product("Alpha")
        self.item(self.order("DELIVERED", "10.00"), product, 1, "10.00")
        models.BusinessMetric.objects.filter(
            business=self.business, key=UNITS_SOLD
        ).update(is_active=False)
        with self.assertRaises(metrics.MetricValidationError):
            self.record_breakdown("PRODUCT")
        self.assertEqual(self.snapshot_count(), 0)

    def test_read_only_calculations_write_nothing(self):
        self.mixed_world()
        for name in CALCULATIONS:
            self.call(name, currency="BDT")
        self.breakdown("CURRENCY")
        self.assertEqual(self.snapshot_count(), 0)

    def test_results_are_immutable_value_objects(self):
        self.order("DELIVERED", "10.00")
        result = self.calc()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.gross_amount = D("1")
        with self.assertRaises(TypeError):
            result.coverage["counted_orders"] = 99
