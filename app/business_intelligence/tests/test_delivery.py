"""BI §13 Delivery Analysis (T-004) and the §2 Delivery Metrics family.

Every test seeds original Business / Order / Shipment / Product / Customer rows
and drives the public service in ``app.business_intelligence.delivery`` against
them; snapshots are read back from ``MetricSnapshot`` and nothing is mocked.
Expected numbers are chosen so every ratio and mean is an exact Decimal
(denominators 2, 4, 8, 10, 20), so assertions are exact, never approximate.

Areas pinned (the numbering follows the T-004 review brief):

1. Mechanical: the ``.only(...)`` loading and the snapshot ``inputs`` payload.
2. Replay: identical re-run is UNCHANGED, changed data updates in place.
3. Denominator / classification: in-flight, cancelled and unknown statuses.
4. Boundaries: half-open periods, zero shipments, single unknown status.
5. Timing: segments, missing/out-of-order/equal timestamps.
6. Cohort: unsubmitted shipments are never moved to ``created_at``.
7. Currency: one currency per amount, order value counted once.
8. Region and courier resolution.
9. Product grouping through CONTAINS_PRODUCT relationships.
10. Tenant isolation.
11. CUSTOMER_SEGMENT rejection and the unrecorded customer analysis.

Section 13 of docs/implementations/features/business-intelligence.md is the
requirement source; the status vocabulary is business-data.md line 364.
"""

import dataclasses
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import (
    METRIC_DEFINITIONS,
    UNAVAILABLE,
    WRITE_CREATED,
    WRITE_NOT_RECORDED_UNAVAILABLE,
    WRITE_UNCHANGED,
    WRITE_UPDATED,
    MetricValidationError,
    rebuild_relationships,
    sync_metric_registry,
)
from app.business_intelligence import delivery


START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = START + timedelta(days=7)
INSIDE = START + timedelta(hours=1)

DOCUMENTED_STATUSES = (
    "PENDING", "SUBMITTED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY",
    "DELIVERED", "FAILED", "RETURNING", "RETURNED", "CANCELLED",
)


def at(**delta):
    """A moment relative to the start of the fixture period."""
    return START + timedelta(**delta)


class DeliveryTestCase(TestCase):
    """Shared fixtures: two registered businesses and small explicit builders."""

    def setUp(self):
        self.a = self.make_business("shop-a")
        self.b = self.make_business("shop-b")
        for business in (self.a, self.b):
            sync_metric_registry(business_id=business.pk)

    # -- fixtures ---------------------------------------------------------

    def make_business(self, slug, currency="BDT"):
        return models.Business.objects.create(
            name=slug, slug=slug, currency=currency, created_at=START, updated_at=START,
        )

    def make_customer(self, business=None, name="Customer"):
        return models.Customer.objects.create(
            business=business or self.a, display_name=name,
            created_at=START, updated_at=START,
        )

    def make_order(self, business=None, customer=None, currency="BDT", total="100.00"):
        return models.Order.objects.create(
            business=business or self.a, customer=customer, currency=currency,
            total_amount=Decimal(total), created_at=START, updated_at=START,
        )

    def make_product(self, business=None, name="Product"):
        return models.Product.objects.create(
            business=business or self.a, name=name, created_at=START, updated_at=START,
        )

    def add_item(self, order, product):
        return models.OrderItem.objects.create(
            order=order, product=product, product_name=product.name, quantity=1,
            unit_price=Decimal("10.00"), total_amount=Decimal("10.00"), created_at=START,
        )

    def ship(self, status="DELIVERED", *, business=None, order=None, customer=None,
             provider="Pathao", charge="0.00", currency="BDT", submitted=INSIDE,
             picked=None, delivered=None, created=INSIDE, metadata=None):
        business = business or self.a
        if order is None:
            order = self.make_order(business=business)
        row = models.Shipment.objects.create(
            business=business, order=order, customer=customer, provider=provider,
            status=status, delivery_charge=Decimal(charge), currency=currency,
            submitted_at=submitted, picked_up_at=picked, delivered_at=delivered,
            source_metadata=metadata, created_at=created, updated_at=created,
        )
        models.Shipment.objects.filter(pk=row.pk).update(created_at=created, updated_at=created)
        row.refresh_from_db()
        return row

    # -- service calls ----------------------------------------------------

    def args(self, **overrides):
        business = overrides.pop("business", None) or self.a
        args = dict(
            business_id=business.pk, period_type="CUSTOM",
            period_start=START, period_end=END,
        )
        args.update(overrides)
        return args

    def run_rates(self, **kw):
        return delivery.calculate_delivery_outcome_rates(**self.args(**kw))

    def run_time(self, **kw):
        return delivery.calculate_delivery_time(**self.args(**kw))

    def run_cost(self, **kw):
        return delivery.calculate_delivery_cost(**self.args(**kw))

    def run_couriers(self, **kw):
        return delivery.compare_couriers(**self.args(**kw))

    def run_regions(self, **kw):
        kw.setdefault("region_metadata_key", "region")
        return delivery.analyze_regional_delivery(**self.args(**kw))

    def run_products(self, **kw):
        return delivery.analyze_product_delivery(**self.args(**kw))

    def run_customers(self, **kw):
        return delivery.analyze_customer_delivery(**self.args(**kw))

    # -- reading snapshots back ------------------------------------------

    def table(self):
        return list(models.MetricSnapshot.objects.order_by("pk").values())

    def snapshots(self, business=None, **filters):
        return list(
            models.MetricSnapshot.objects.filter(
                business=business or self.a, **filters
            ).order_by("pk")
        )

    def snapshot(self, metric_key, dimension_type=None, dimension_value=None,
                 business=None):
        return models.MetricSnapshot.objects.get(
            business=business or self.a, metric__key=metric_key,
            dimension_type=dimension_type, dimension_value=dimension_value,
        )

    def outcome_snapshots(self, outcome):
        return {
            delivery.METRIC_SHIPMENTS: outcome.shipments_snapshot,
            delivery.METRIC_SUCCESS_RATE: outcome.success_rate_snapshot,
            delivery.METRIC_FAILURE_RATE: outcome.failure_rate_snapshot,
            delivery.METRIC_RETURN_RATE: outcome.return_rate_snapshot,
        }

    def assert_counts(self, counts, **expected):
        """Exact status counts; every count not named must be zero."""
        base = dict(
            shipments=0, delivered=0, failed=0, returning=0, returned=0,
            in_flight=0, cancelled=0, unclassified=0,
        )
        base.update(expected)
        actual = {name: getattr(counts, name) for name in base}
        self.assertEqual(actual, base)
        self.assertEqual(
            counts.delivered + counts.failed + counts.returns + counts.in_flight
            + counts.cancelled + counts.unclassified,
            counts.shipments,
        )


# ==========================================================================
# 1. Mechanical: loading, result shape and the snapshot inputs payload
# ==========================================================================

class OutcomeRateMechanicsTests(DeliveryTestCase):
    """One plain call proves the shipment query, the arithmetic and the writes."""

    def test_exact_rates_snapshots_and_persisted_inputs(self):
        for status in ("DELIVERED", "DELIVERED", "FAILED", "RETURNED"):
            self.ship(status)

        result = self.run_rates()

        self.assert_counts(result.counts, shipments=4, delivered=2, failed=1, returned=1)
        self.assertEqual(result.counts.unclassified_statuses, ())
        self.assertEqual(result.success_rate, Decimal("0.5"))
        self.assertEqual(result.failure_rate, Decimal("0.25"))
        self.assertEqual(result.return_rate, Decimal("0.25"))
        for rate in (result.success_rate, result.failure_rate, result.return_rate):
            self.assertIsInstance(rate, Decimal)
        self.assertEqual(result.scope.business_id, self.a.pk)
        self.assertEqual(result.scope.cohort, delivery.COHORT_SUBMITTED)
        self.assertEqual(result.scope.period_start, START)
        self.assertEqual(result.scope.period_end, END)
        self.assertIsNone(result.scope.dimension_type)
        self.assertIsNone(result.scope.dimension_value)
        self.assertEqual(result.cohort_excluded_unsubmitted_business_wide, 0)

        expected = {
            delivery.METRIC_SHIPMENTS: Decimal("4"),
            delivery.METRIC_SUCCESS_RATE: Decimal("0.5"),
            delivery.METRIC_FAILURE_RATE: Decimal("0.25"),
            delivery.METRIC_RETURN_RATE: Decimal("0.25"),
        }
        snapshots = self.outcome_snapshots(result)
        self.assertEqual(len(self.table()), 4)
        for key, value in expected.items():
            with self.subTest(metric=key):
                write = snapshots[key]
                self.assertEqual(write.status, WRITE_CREATED)
                self.assertEqual(write.observation.metric_key, key)
                self.assertEqual(write.observation.value, value)
                self.assertEqual(write.observation.revision, 1)
                rule = delivery.get_delivery_rule(
                    metric_key=key, cohort=delivery.COHORT_SUBMITTED
                )
                self.assertEqual(write.observation.calculation_rule, rule.calculation_rule)
                row = self.snapshot(key)
                self.assertEqual(row.value, value)
                self.assertEqual(row.calculation_rule, rule.calculation_rule)
                self.assertEqual(row.period_start, START)
                self.assertEqual(row.period_end, END)
                self.assertEqual(row.period_type, "CUSTOM")
                self.assertTrue(row.metadata["data_available"])
                # The persisted evidence is exactly what the result reports.
                self.assertEqual(row.metadata["inputs"], dict(result.inputs))

        inputs = result.inputs
        self.assertEqual(inputs["cohort"], "COHORT_SUBMITTED")
        self.assertEqual(inputs["cohort_field"], "submitted_at")
        self.assertEqual(
            inputs["scope"],
            {"dimension_type": None, "dimension_value": None, "region_metadata_key": None},
        )
        self.assertEqual(
            (inputs["shipments"], inputs["delivered"], inputs["failed"],
             inputs["returning"], inputs["returned"], inputs["in_flight"],
             inputs["cancelled"], inputs["unclassified"]),
            (4, 2, 1, 0, 1, 0, 0, 0),
        )
        self.assertEqual(inputs["unclassified_statuses"], [])
        self.assertEqual(inputs["status_set_version"], "s1")
        self.assertEqual(inputs["denominator"], "ALL_COHORT_SHIPMENTS_IN_SCOPE")
        self.assertIs(inputs["denominator_includes_in_flight"], True)
        self.assertEqual(inputs["cohort_excluded_unsubmitted_business_wide"], 0)
        self.assertEqual(inputs["status_sets"]["success"], ["DELIVERED"])
        self.assertEqual(inputs["status_sets"]["failure"], ["FAILED"])
        self.assertEqual(inputs["status_sets"]["return"], ["RETURNED", "RETURNING"])
        self.assertEqual(
            inputs["status_sets"]["in_flight"],
            ["IN_TRANSIT", "OUT_FOR_DELIVERY", "PENDING", "PICKED_UP", "SUBMITTED"],
        )
        self.assertEqual(inputs["status_sets"]["cancelled"], ["CANCELLED"])

    def test_result_and_inputs_are_immutable(self):
        self.ship("DELIVERED")
        result = self.run_rates(record=False)
        with self.assertRaises(TypeError):
            result.inputs["shipments"] = 0
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.success_rate = Decimal("0")

    def test_time_cost_and_rows_load_with_deferred_columns(self):
        """Time and cost read the same ``.only()`` rows as the rates do."""
        order = self.make_order(total="500.00")
        self.ship("DELIVERED", order=order, charge="60.00", delivered=INSIDE + timedelta(hours=1))
        self.assertEqual(self.run_time().measured, 1)
        self.assertEqual(self.run_cost().total_charge, Decimal("60.00"))
        self.assertEqual(self.run_customers().shipments, 1)

    def test_snapshot_inputs_hold_no_float_and_decimals_are_strings(self):
        self.ship("DELIVERED", charge="12.50", delivered=INSIDE + timedelta(seconds=90))
        self.run_time()
        self.run_cost()
        time_inputs = self.snapshot(delivery.METRIC_TIME).metadata["inputs"]
        cost_inputs = self.snapshot(delivery.METRIC_COST).metadata["inputs"]
        self.assertIsInstance(time_inputs["total_seconds"], str)
        self.assertEqual(Decimal(time_inputs["total_seconds"]), Decimal("90"))
        self.assertIsInstance(cost_inputs["total_charge"], str)
        self.assertEqual(Decimal(cost_inputs["total_charge"]), Decimal("12.50"))


# ==========================================================================
# 2. Replay and revision
# ==========================================================================

class ReplayTests(DeliveryTestCase):

    def seed_four(self):
        for status in ("DELIVERED", "DELIVERED", "FAILED", "RETURNED"):
            self.ship(status)

    def test_identical_second_run_is_unchanged_and_appends_no_rows(self):
        self.seed_four()
        first = self.run_rates()
        before = self.table()
        self.assertEqual(len(before), 4)

        second = self.run_rates()

        first_writes = self.outcome_snapshots(first)
        second_writes = self.outcome_snapshots(second)
        for key in first_writes:
            with self.subTest(metric=key):
                self.assertEqual(first_writes[key].status, WRITE_CREATED)
                self.assertEqual(second_writes[key].status, WRITE_UNCHANGED)
                self.assertEqual(
                    second_writes[key].observation.snapshot_id,
                    first_writes[key].observation.snapshot_id,
                )
                self.assertEqual(second_writes[key].observation.revision, 1)
        # Same rows, same ids, same timestamps, same metadata: nothing touched.
        self.assertEqual(self.table(), before)

    def test_changed_data_updates_the_same_rows_with_incremented_revision(self):
        self.seed_four()
        first = self.run_rates()
        ids = {key: write.observation.snapshot_id
               for key, write in self.outcome_snapshots(first).items()}

        self.ship("DELIVERED")
        second = self.run_rates()

        expected = {
            delivery.METRIC_SHIPMENTS: (Decimal("5"), Decimal("4")),
            delivery.METRIC_SUCCESS_RATE: (Decimal("0.6"), Decimal("0.5")),
            delivery.METRIC_FAILURE_RATE: (Decimal("0.2"), Decimal("0.25")),
            delivery.METRIC_RETURN_RATE: (Decimal("0.2"), Decimal("0.25")),
        }
        writes = self.outcome_snapshots(second)
        self.assertEqual(len(self.table()), 4)
        for key, (value, previous) in expected.items():
            with self.subTest(metric=key):
                self.assertEqual(writes[key].status, WRITE_UPDATED)
                self.assertEqual(writes[key].observation.value, value)
                self.assertEqual(writes[key].previous_value, previous)
                self.assertEqual(writes[key].observation.revision, 2)
                self.assertEqual(writes[key].observation.snapshot_id, ids[key])
                row = self.snapshot(key)
                self.assertEqual(row.pk, ids[key])
                self.assertEqual(row.value, value)
                self.assertEqual(row.metadata["revision"], 2)
                self.assertEqual(Decimal(row.metadata["supersedes"]["value"]), previous)
                self.assertEqual(row.metadata["inputs"]["shipments"], 5)

    def test_incomplete_period_rate_rises_as_shipments_resolve(self):
        self.ship("DELIVERED")
        for status in ("PENDING", "IN_TRANSIT", "OUT_FOR_DELIVERY"):
            self.ship(status)

        early = self.run_rates()
        self.assert_counts(early.counts, shipments=4, delivered=1, in_flight=3)
        self.assertEqual(early.success_rate, Decimal("0.25"))
        # In-flight shipments are never failures: a measured zero, not UNAVAILABLE.
        self.assertEqual(early.failure_rate, Decimal("0"))
        self.assertEqual(early.return_rate, Decimal("0"))
        self.assertEqual(early.failure_rate_snapshot.status, WRITE_CREATED)
        self.assertEqual(early.inputs["in_flight"], 3)

        models.Shipment.objects.exclude(status="DELIVERED").update(status="DELIVERED")
        late = self.run_rates()

        self.assert_counts(late.counts, shipments=4, delivered=4)
        self.assertEqual(late.success_rate, Decimal("1"))
        self.assertEqual(late.success_rate_snapshot.status, WRITE_UPDATED)
        self.assertEqual(late.success_rate_snapshot.previous_value, Decimal("0.25"))
        self.assertEqual(late.success_rate_snapshot.observation.revision, 2)
        self.assertEqual(late.failure_rate, Decimal("0"))
        self.assertEqual(self.snapshot(delivery.METRIC_SUCCESS_RATE).metadata["inputs"]["in_flight"], 0)
        self.assertEqual(len(self.table()), 4)

    def test_time_and_cost_replay_is_unchanged(self):
        self.ship("DELIVERED", charge="60.00", delivered=INSIDE + timedelta(seconds=3600))
        self.ship("DELIVERED", charge="40.00", delivered=INSIDE + timedelta(seconds=7200))

        first_time, first_cost = self.run_time(), self.run_cost()
        before = self.table()
        second_time, second_cost = self.run_time(), self.run_cost()

        self.assertEqual(first_time.snapshot.status, WRITE_CREATED)
        self.assertEqual(first_time.average_seconds, Decimal("5400"))
        self.assertEqual(first_cost.snapshot.status, WRITE_CREATED)
        self.assertEqual(first_cost.total_charge, Decimal("100.00"))
        self.assertEqual(second_time.snapshot.status, WRITE_UNCHANGED)
        self.assertEqual(second_cost.snapshot.status, WRITE_UNCHANGED)
        self.assertEqual(len(before), 2)
        self.assertEqual(self.table(), before)

    def test_courier_comparison_replay_appends_no_rows(self):
        self.ship("DELIVERED", provider="Pathao", charge="10.00", delivered=INSIDE + timedelta(seconds=60))
        self.ship("DELIVERED", provider="Pathao", charge="10.00", delivered=INSIDE + timedelta(seconds=120))
        self.ship("FAILED", provider="RedX", charge="20.00")

        first = self.run_couriers()
        before = self.table()
        self.assertGreater(len(before), 0)
        second = self.run_couriers()

        def writes(comparison):
            found = []
            for courier in comparison.couriers:
                found.extend(self.outcome_snapshots(courier.outcomes).values())
                found.append(courier.timing.snapshot)
                found.append(courier.cost.snapshot)
            return found

        self.assertTrue(any(w.status == WRITE_CREATED for w in writes(first)))
        for write in writes(second):
            self.assertIn(write.status, {WRITE_UNCHANGED, WRITE_NOT_RECORDED_UNAVAILABLE})
        self.assertEqual(self.table(), before)

    def test_record_false_computes_without_writing(self):
        self.seed_four()
        result = self.run_rates(record=False)
        self.assertEqual(result.success_rate, Decimal("0.5"))
        for write in self.outcome_snapshots(result).values():
            self.assertIsNone(write)
        self.assertEqual(self.table(), [])


# ==========================================================================
# 3. Denominator and status classification
# ==========================================================================

class ClassificationTests(DeliveryTestCase):

    def test_each_documented_status_lands_in_exactly_one_class(self):
        for status in DOCUMENTED_STATUSES:
            self.ship(status)

        result = self.run_rates()

        self.assert_counts(
            result.counts, shipments=10, delivered=1, failed=1, returning=1,
            returned=1, in_flight=5, cancelled=1,
        )
        self.assertEqual(result.success_rate, Decimal("0.1"))
        self.assertEqual(result.failure_rate, Decimal("0.1"))
        self.assertEqual(result.return_rate, Decimal("0.2"))

    def test_in_flight_cancelled_and_unknown_are_in_denominator_and_no_numerator(self):
        statuses = (
            ["DELIVERED"] * 4 + ["FAILED"] * 2 + ["RETURNING", "RETURNED"]
            + ["PENDING", "SUBMITTED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY"]
            + ["CANCELLED"] * 3 + ["LOST", "LOST", "delivered", "Failed"]
        )
        self.assertEqual(len(statuses), 20)
        for status in statuses:
            self.ship(status)

        result = self.run_rates()

        self.assert_counts(
            result.counts, shipments=20, delivered=4, failed=2, returning=1,
            returned=1, in_flight=5, cancelled=3, unclassified=4,
        )
        self.assertEqual(result.success_rate, Decimal("0.2"))
        self.assertEqual(result.failure_rate, Decimal("0.1"))
        self.assertEqual(result.return_rate, Decimal("0.1"))
        # What is in no numerator is still in the denominator: 12 of 20.
        remaining = (
            result.counts.in_flight + result.counts.cancelled + result.counts.unclassified
        )
        self.assertEqual(Decimal(remaining) / Decimal(20), Decimal("0.6"))
        self.assertEqual(
            result.counts.unclassified_statuses,
            (("Failed", 1), ("LOST", 2), ("delivered", 1)),
        )
        expected_unclassified = [
            {"status": "Failed", "count": 1},
            {"status": "LOST", "count": 2},
            {"status": "delivered", "count": 1},
        ]
        self.assertEqual(result.inputs["unclassified_statuses"], expected_unclassified)
        self.assertEqual(result.inputs["in_flight"], 5)
        self.assertEqual(result.inputs["cancelled"], 3)
        self.assertEqual(result.inputs["unclassified"], 4)
        self.assertEqual(result.inputs["shipments"], 20)
        # The same verbatim evidence is persisted on every recorded observation.
        for key in (delivery.METRIC_SHIPMENTS, delivery.METRIC_SUCCESS_RATE,
                    delivery.METRIC_FAILURE_RATE, delivery.METRIC_RETURN_RATE):
            with self.subTest(metric=key):
                persisted = self.snapshot(key).metadata["inputs"]
                self.assertEqual(persisted["unclassified_statuses"], expected_unclassified)
                self.assertEqual(persisted["shipments"], 20)
        self.assertEqual(self.snapshot(delivery.METRIC_SHIPMENTS).value, Decimal("20"))
        self.assertEqual(self.snapshot(delivery.METRIC_SUCCESS_RATE).value, Decimal("0.2"))
        self.assertEqual(self.snapshot(delivery.METRIC_FAILURE_RATE).value, Decimal("0.1"))
        self.assertEqual(self.snapshot(delivery.METRIC_RETURN_RATE).value, Decimal("0.1"))

    def test_single_unknown_status_gives_zero_rates_and_names_the_status(self):
        self.ship("LOST")

        result = self.run_rates()

        self.assert_counts(result.counts, shipments=1, unclassified=1)
        self.assertEqual(result.counts.unclassified_statuses, (("LOST", 1),))
        for rate in (result.success_rate, result.failure_rate, result.return_rate):
            self.assertIsNot(rate, UNAVAILABLE)
            self.assertEqual(rate, Decimal("0"))
        # A rate of zero over one counted shipment is a measured zero and recorded.
        for key, write in self.outcome_snapshots(result).items():
            self.assertEqual(write.status, WRITE_CREATED, key)
        self.assertEqual(self.snapshot(delivery.METRIC_SHIPMENTS).value, Decimal("1"))
        self.assertEqual(self.snapshot(delivery.METRIC_FAILURE_RATE).value, Decimal("0"))
        self.assertEqual(
            self.snapshot(delivery.METRIC_FAILURE_RATE).metadata["inputs"]["unclassified_statuses"],
            [{"status": "LOST", "count": 1}],
        )

    def test_status_matching_is_exact_without_case_folding_or_trimming(self):
        for status in ("delivered", "Delivered", "DELIVERED ", "failed"):
            self.ship(status)
        for status in ("DELIVERED", "DELIVERED", "FAILED", "RETURNED"):
            self.ship(status)

        result = self.run_rates()

        self.assert_counts(
            result.counts, shipments=8, delivered=2, failed=1, returned=1, unclassified=4,
        )
        self.assertEqual(result.success_rate, Decimal("0.25"))
        self.assertEqual(result.failure_rate, Decimal("0.125"))
        self.assertEqual(result.return_rate, Decimal("0.125"))
        self.assertEqual(
            result.counts.unclassified_statuses,
            (("DELIVERED ", 1), ("Delivered", 1), ("delivered", 1), ("failed", 1)),
        )

    def test_failure_rate_never_counts_cancelled_or_returns(self):
        for status in ("CANCELLED", "CANCELLED", "RETURNED", "RETURNING"):
            self.ship(status)
        result = self.run_rates()
        self.assertEqual(result.failure_rate, Decimal("0"))
        self.assertEqual(result.success_rate, Decimal("0"))
        self.assertEqual(result.return_rate, Decimal("0.5"))


# ==========================================================================
# 4. Boundaries and zero data
# ==========================================================================

class BoundaryTests(DeliveryTestCase):

    def test_submitted_cohort_period_is_half_open(self):
        self.ship("DELIVERED", submitted=START)
        self.ship("FAILED", submitted=END)
        self.ship("RETURNED", submitted=END - timedelta(microseconds=1))
        self.ship("CANCELLED", submitted=START - timedelta(microseconds=1))

        result = self.run_rates()

        self.assert_counts(result.counts, shipments=2, delivered=1, returned=1)
        self.assertEqual(result.success_rate, Decimal("0.5"))
        self.assertEqual(result.failure_rate, Decimal("0"))
        self.assertEqual(result.return_rate, Decimal("0.5"))

    def test_created_cohort_period_is_half_open(self):
        self.ship("DELIVERED", created=START)
        self.ship("FAILED", created=END)
        self.ship("RETURNED", created=END - timedelta(microseconds=1))
        self.ship("CANCELLED", created=START - timedelta(microseconds=1))

        result = self.run_rates(cohort=delivery.COHORT_CREATED)

        self.assert_counts(result.counts, shipments=2, delivered=1, returned=1)
        self.assertEqual(result.success_rate, Decimal("0.5"))
        self.assertEqual(result.return_rate, Decimal("0.5"))

    def test_zero_shipments_rates_are_unavailable_and_only_the_count_is_recorded(self):
        # A shipment outside the period is not in scope.
        self.ship("DELIVERED", submitted=END)

        result = self.run_rates()

        self.assert_counts(result.counts, shipments=0)
        self.assertIs(result.success_rate, UNAVAILABLE)
        self.assertIs(result.failure_rate, UNAVAILABLE)
        self.assertIs(result.return_rate, UNAVAILABLE)
        self.assertEqual(result.shipments_snapshot.status, WRITE_CREATED)
        self.assertEqual(result.shipments_snapshot.observation.value, Decimal("0"))
        for write in (result.success_rate_snapshot, result.failure_rate_snapshot,
                      result.return_rate_snapshot):
            self.assertEqual(write.status, WRITE_NOT_RECORDED_UNAVAILABLE)
            self.assertIsNone(write.observation)
        rows = self.snapshots()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].metric.key, delivery.METRIC_SHIPMENTS)
        self.assertEqual(rows[0].value, Decimal("0"))
        self.assertIs(rows[0].metadata["data_available"], True)

    def test_zero_shipments_time_and_cost_are_unavailable_not_zero(self):
        timing = self.run_time()
        cost = self.run_cost()

        self.assertEqual((timing.shipments, timing.measured), (0, 0))
        self.assertIs(timing.average_seconds, UNAVAILABLE)
        self.assertEqual(timing.snapshot.status, WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertEqual(cost.shipments, 0)
        self.assertEqual(cost.shipments_in_currency, 0)
        self.assertEqual(cost.total_charge, Decimal("0"))
        self.assertIs(cost.charge_share_of_order_value, UNAVAILABLE)
        self.assertEqual(cost.snapshot.status, WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertIsNone(cost.snapshot.observation)
        self.assertEqual(self.table(), [])

    def test_only_other_currency_shipments_make_cost_unavailable(self):
        self.ship("DELIVERED", currency="USD", charge="5.00")

        cost = self.run_cost()

        self.assertEqual(cost.shipments, 1)
        self.assertEqual(cost.shipments_in_currency, 0)
        self.assertEqual(cost.shipments_excluded_other_currency, 1)
        self.assertEqual(cost.excluded_currencies, (("USD", 1),))
        self.assertEqual(cost.snapshot.status, WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertEqual(self.table(), [])

    def test_zero_charge_in_scope_currency_is_a_measured_zero(self):
        self.ship("DELIVERED", charge="0.00")
        self.ship("CANCELLED", charge="0.00")

        cost = self.run_cost()

        self.assertEqual(cost.shipments_in_currency, 2)
        self.assertEqual(cost.total_charge, Decimal("0"))
        self.assertEqual(cost.snapshot.status, WRITE_CREATED)
        self.assertEqual(cost.snapshot.observation.value, Decimal("0"))
        self.assertEqual(self.snapshot(delivery.METRIC_COST).value, Decimal("0"))


# ==========================================================================
# 5. Delivery time analysis
# ==========================================================================

class TimingTests(DeliveryTestCase):

    def seed_matrix(self):
        """Eight shipments covering every exclusion in each of the three segments."""
        self.ship("DELIVERED", submitted=at(hours=0), picked=at(hours=1), delivered=at(hours=4))  # A
        self.ship("DELIVERED", submitted=at(hours=2), picked=at(hours=3),
                  delivered=at(hours=2, seconds=1800, microseconds=500000))  # B
        self.ship("DELIVERED", submitted=at(hours=5), picked=at(hours=6), delivered=None)  # C
        self.ship("DELIVERED", submitted=at(hours=8), picked=None, delivered=at(hours=9))  # D
        self.ship("IN_TRANSIT", submitted=at(hours=10), picked=at(hours=10), delivered=None)  # E
        self.ship("DELIVERED", submitted=at(hours=12), picked=at(hours=14), delivered=at(hours=11))  # F
        self.ship("DELIVERED", submitted=at(hours=13), picked=None, delivered=at(hours=13))  # G
        self.ship("IN_TRANSIT", submitted=at(hours=14), picked=None, delivered=None)  # H

    def assert_partition(self, result):
        self.assertEqual(
            result.measured + result.excluded_missing_start
            + result.excluded_missing_end + result.excluded_out_of_order,
            result.shipments,
        )

    def test_submission_to_delivery_exact_mean_and_exclusions(self):
        self.seed_matrix()

        result = self.run_time(segment=delivery.SEGMENT_SUBMISSION_TO_DELIVERY)

        self.assertEqual((result.start_field, result.end_field), ("submitted_at", "delivered_at"))
        self.assertEqual(result.shipments, 8)
        # A 14400 + B 1800.5 + D 3600 + G 0 (equal timestamps) over 4 shipments.
        self.assertEqual(result.measured, 4)
        self.assertEqual(result.total_seconds, Decimal("19800.5"))
        self.assertEqual(result.average_seconds, Decimal("4950.125"))
        self.assertEqual(result.excluded_missing_start, 0)
        self.assertEqual(result.excluded_missing_end, 3)  # C, E, H
        self.assertEqual(result.excluded_out_of_order, 1)  # F
        self.assertEqual(result.excluded_success_without_end_timestamp, 1)  # C only
        self.assert_partition(result)
        self.assertEqual(result.snapshot.status, WRITE_CREATED)
        self.assertEqual(result.snapshot.observation.value, Decimal("4950.125"))
        row = self.snapshot(delivery.METRIC_TIME)
        self.assertEqual(row.value, Decimal("4950.125"))
        self.assertEqual(
            row.calculation_rule,
            "bi.metric.delivery_time.v1.submission_to_delivery_cohort_submitted",
        )
        inputs = row.metadata["inputs"]
        self.assertEqual(inputs["segment"], "SUBMISSION_TO_DELIVERY")
        self.assertEqual((inputs["start_field"], inputs["end_field"]),
                         ("submitted_at", "delivered_at"))
        self.assertEqual(
            (inputs["shipments"], inputs["measured"], inputs["excluded_missing_start"],
             inputs["excluded_missing_end"], inputs["excluded_out_of_order"],
             inputs["excluded_success_without_end_timestamp"]),
            (8, 4, 0, 3, 1, 1),
        )
        self.assertEqual(Decimal(inputs["total_seconds"]), Decimal("19800.5"))

    def test_submission_to_pickup_mean_and_exclusions(self):
        self.seed_matrix()

        result = self.run_time(segment=delivery.SEGMENT_SUBMISSION_TO_PICKUP, record=False)

        self.assertEqual((result.start_field, result.end_field), ("submitted_at", "picked_up_at"))
        # A, B, C 3600 each, E 0 (equal), F 7200.
        self.assertEqual(result.measured, 5)
        self.assertEqual(result.total_seconds, Decimal("18000"))
        self.assertEqual(result.average_seconds, Decimal("3600"))
        self.assertEqual(result.excluded_missing_start, 0)
        self.assertEqual(result.excluded_missing_end, 3)  # D, G, H
        self.assertEqual(result.excluded_out_of_order, 0)
        self.assert_partition(result)

    def test_pickup_to_delivery_mean_and_exclusions(self):
        self.seed_matrix()

        result = self.run_time(segment=delivery.SEGMENT_PICKUP_TO_DELIVERY, record=False)

        self.assertEqual((result.start_field, result.end_field), ("picked_up_at", "delivered_at"))
        self.assertEqual(result.measured, 1)  # only A: 10800
        self.assertEqual(result.total_seconds, Decimal("10800"))
        self.assertEqual(result.average_seconds, Decimal("10800"))
        self.assertEqual(result.excluded_missing_start, 3)  # D, G, H (no pickup)
        self.assertEqual(result.excluded_missing_end, 2)  # C, E
        self.assertEqual(result.excluded_out_of_order, 2)  # B, F
        self.assertEqual(result.excluded_success_without_end_timestamp, 1)  # C
        self.assert_partition(result)

    def test_each_segment_uses_the_timestamps_it_reports(self):
        self.ship(
            "DELIVERED", submitted=INSIDE,
            picked=INSIDE + timedelta(seconds=100),
            delivered=INSIDE + timedelta(seconds=1000),
        )
        expected = {
            delivery.SEGMENT_SUBMISSION_TO_DELIVERY: ("submitted_at", "delivered_at", "1000"),
            delivery.SEGMENT_SUBMISSION_TO_PICKUP: ("submitted_at", "picked_up_at", "100"),
            delivery.SEGMENT_PICKUP_TO_DELIVERY: ("picked_up_at", "delivered_at", "900"),
        }
        for segment, (start_field, end_field, seconds) in expected.items():
            with self.subTest(segment=segment):
                result = self.run_time(segment=segment, record=False)
                self.assertEqual((result.start_field, result.end_field), (start_field, end_field))
                self.assertEqual(result.inputs["start_field"], start_field)
                self.assertEqual(result.inputs["end_field"], end_field)
                self.assertEqual(result.measured, 1)
                self.assertEqual(result.average_seconds, Decimal(seconds))

    def test_default_segment_is_submission_to_delivery(self):
        self.ship("DELIVERED", delivered=INSIDE + timedelta(seconds=42))
        result = self.run_time(record=False)
        self.assertEqual(result.segment, delivery.SEGMENT_SUBMISSION_TO_DELIVERY)
        self.assertEqual(result.average_seconds, Decimal("42"))

    def test_delivered_without_delivery_timestamp_contributes_no_duration(self):
        self.ship("DELIVERED", delivered=INSIDE + timedelta(seconds=600))
        # created_at is a day after submission; it must never stand in for delivered_at.
        self.ship("DELIVERED", delivered=None, created=INSIDE + timedelta(days=1))

        result = self.run_time()

        self.assertEqual(result.shipments, 2)
        self.assertEqual(result.measured, 1)
        self.assertEqual(result.total_seconds, Decimal("600"))
        self.assertEqual(result.average_seconds, Decimal("600"))
        self.assertEqual(result.excluded_missing_end, 1)
        self.assertEqual(result.excluded_success_without_end_timestamp, 1)
        self.assert_partition(result)
        self.assertEqual(
            self.snapshot(delivery.METRIC_TIME).metadata["inputs"]
            ["excluded_success_without_end_timestamp"],
            1,
        )

    def test_delivery_before_submission_is_excluded_as_out_of_order(self):
        self.ship("DELIVERED", delivered=INSIDE - timedelta(seconds=1))

        result = self.run_time()

        self.assertEqual(result.measured, 0)
        self.assertEqual(result.excluded_out_of_order, 1)
        self.assertEqual(result.excluded_missing_end, 0)
        self.assertEqual(result.total_seconds, Decimal("0"))
        self.assertIs(result.average_seconds, UNAVAILABLE)
        self.assertEqual(result.snapshot.status, WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertEqual(self.table(), [])

    def test_equal_timestamps_are_a_measured_zero_not_an_exclusion(self):
        self.ship("DELIVERED", delivered=INSIDE)

        result = self.run_time()

        self.assertEqual(result.measured, 1)
        self.assertEqual(result.excluded_out_of_order, 0)
        self.assertEqual(result.average_seconds, Decimal("0"))
        self.assertIsNot(result.average_seconds, UNAVAILABLE)
        self.assertEqual(result.snapshot.status, WRITE_CREATED)
        self.assertEqual(self.snapshot(delivery.METRIC_TIME).value, Decimal("0"))

    def test_durations_keep_microsecond_precision_without_float(self):
        self.ship("DELIVERED", delivered=INSIDE + timedelta(seconds=1, microseconds=250000))
        self.ship("DELIVERED", delivered=INSIDE + timedelta(seconds=2, microseconds=250000))
        result = self.run_time(record=False)
        self.assertEqual(result.total_seconds, Decimal("3.5"))
        self.assertEqual(result.average_seconds, Decimal("1.75"))
        self.assertIsInstance(result.average_seconds, Decimal)

    def test_multi_day_duration_is_exact_seconds(self):
        self.ship("DELIVERED", delivered=INSIDE + timedelta(days=2, seconds=5))
        result = self.run_time(record=False)
        self.assertEqual(result.average_seconds, Decimal("172805"))


# ==========================================================================
# 6. Cohort selection
# ==========================================================================

class CohortTests(DeliveryTestCase):

    def seed_cohorts(self):
        outside_created = START - timedelta(days=1)
        self.ship("DELIVERED", submitted=INSIDE, created=INSIDE)  # f1
        self.ship("DELIVERED", submitted=None, created=INSIDE)  # f2
        self.ship("FAILED", submitted=None, created=INSIDE)  # f3
        self.ship("FAILED", submitted=INSIDE, created=INSIDE)  # f4
        self.ship("RETURNED", submitted=INSIDE, created=outside_created)  # f5
        self.ship("DELIVERED", submitted=INSIDE, created=outside_created)  # f6

    def test_submitted_cohort_excludes_unsubmitted_and_never_uses_created_at(self):
        self.seed_cohorts()

        result = self.run_rates(cohort=delivery.COHORT_SUBMITTED)

        # f1, f4, f5, f6 carry a submission time inside the period.
        self.assert_counts(result.counts, shipments=4, delivered=2, failed=1, returned=1)
        self.assertEqual(result.success_rate, Decimal("0.5"))
        self.assertEqual(result.failure_rate, Decimal("0.25"))
        self.assertEqual(result.return_rate, Decimal("0.25"))
        # f2 and f3 were created in the period but never submitted: reported, not moved.
        self.assertEqual(result.cohort_excluded_unsubmitted_business_wide, 2)
        self.assertEqual(result.inputs["cohort_excluded_unsubmitted_business_wide"], 2)
        self.assertEqual(
            self.snapshot(delivery.METRIC_SUCCESS_RATE)
            .metadata["inputs"]["cohort_excluded_unsubmitted_business_wide"],
            2,
        )
        self.assertEqual(
            result.success_rate_snapshot.observation.calculation_rule,
            "bi.metric.delivery_success_rate.v1.cohort_submitted_s1",
        )

    def test_created_cohort_uses_created_at_and_reports_no_exclusion(self):
        self.seed_cohorts()

        result = self.run_rates(cohort=delivery.COHORT_CREATED)

        # f1..f4 were created inside the period (f2, f3 without submission).
        self.assert_counts(result.counts, shipments=4, delivered=2, failed=2)
        self.assertEqual(result.success_rate, Decimal("0.5"))
        self.assertEqual(result.failure_rate, Decimal("0.5"))
        self.assertEqual(result.return_rate, Decimal("0"))
        self.assertEqual(result.cohort_excluded_unsubmitted_business_wide, 0)
        self.assertEqual(result.inputs["cohort_excluded_unsubmitted_business_wide"], 0)
        self.assertEqual(result.inputs["cohort"], "COHORT_CREATED")
        self.assertEqual(result.inputs["cohort_field"], "created_at")
        self.assertEqual(
            result.success_rate_snapshot.observation.calculation_rule,
            "bi.metric.delivery_success_rate.v1.cohort_created_s1",
        )

    def test_unsubmitted_count_respects_the_period_of_created_at(self):
        self.ship("DELIVERED", submitted=INSIDE)
        self.ship("FAILED", submitted=None, created=START)  # counted: start included
        self.ship("FAILED", submitted=None, created=END)  # not counted: end excluded
        self.ship("FAILED", submitted=None, created=START - timedelta(microseconds=1))  # before

        result = self.run_rates()

        self.assert_counts(result.counts, shipments=1, delivered=1)
        self.assertEqual(result.cohort_excluded_unsubmitted_business_wide, 1)
        self.assertEqual(result.failure_rate, Decimal("0"))

    def test_unsubmitted_only_period_has_zero_shipments_and_unavailable_rates(self):
        self.ship("DELIVERED", submitted=None)

        result = self.run_rates()

        self.assert_counts(result.counts, shipments=0)
        self.assertIs(result.success_rate, UNAVAILABLE)
        self.assertEqual(result.cohort_excluded_unsubmitted_business_wide, 1)

    def test_timing_and_cost_use_the_same_cohort(self):
        self.ship("DELIVERED", submitted=None, charge="99.00", delivered=INSIDE + timedelta(seconds=10))
        self.ship("DELIVERED", submitted=INSIDE, charge="1.00", delivered=INSIDE + timedelta(seconds=20))

        timing = self.run_time(record=False)
        cost = self.run_cost(record=False)

        self.assertEqual(timing.shipments, 1)
        self.assertEqual(timing.average_seconds, Decimal("20"))
        self.assertEqual(cost.total_charge, Decimal("1.00"))
        self.assertEqual(cost.shipments, 1)


# ==========================================================================
# 7. Currency and order economics
# ==========================================================================

class CostCurrencyTests(DeliveryTestCase):

    def seed_mixed_currencies(self):
        for charge in ("60.00", "70.50", "9.25"):
            self.ship("DELIVERED", charge=charge, currency="BDT")
        for charge in ("5.00", "6.00"):
            self.ship("DELIVERED", charge=charge, currency="USD")
        self.ship("DELIVERED", charge="1.00", currency="EUR")

    def test_mixed_currencies_are_excluded_and_counted_in_the_business_currency(self):
        self.seed_mixed_currencies()

        result = self.run_cost()

        self.assertEqual(result.currency, "BDT")
        self.assertEqual(result.shipments, 6)
        self.assertEqual(result.shipments_in_currency, 3)
        self.assertEqual(result.shipments_excluded_other_currency, 3)
        self.assertEqual(result.excluded_currencies, (("EUR", 1), ("USD", 2)))
        self.assertEqual(result.total_charge, Decimal("139.75"))
        self.assertEqual(result.snapshot.status, WRITE_CREATED)
        self.assertEqual(result.snapshot.observation.value, Decimal("139.75"))
        row = self.snapshot(delivery.METRIC_COST)
        self.assertEqual(row.value, Decimal("139.75"))
        self.assertIsNone(row.dimension_type)
        self.assertEqual(
            row.calculation_rule, "bi.metric.delivery_cost.v1.cohort_submitted"
        )
        inputs = row.metadata["inputs"]
        self.assertEqual(inputs["currency"], "BDT")
        self.assertEqual(inputs["shipments_in_currency"], 3)
        self.assertEqual(inputs["shipments_excluded_other_currency"], 3)
        self.assertEqual(
            inputs["excluded_currencies"],
            [{"currency": "EUR", "shipments": 1}, {"currency": "USD", "shipments": 2}],
        )
        self.assertEqual(Decimal(inputs["total_charge"]), Decimal("139.75"))

    def test_explicit_currency_argument_selects_another_single_currency(self):
        self.seed_mixed_currencies()

        result = self.run_cost(currency="USD", record=False)

        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.shipments_in_currency, 2)
        self.assertEqual(result.total_charge, Decimal("11.00"))
        self.assertEqual(result.shipments_excluded_other_currency, 4)
        self.assertEqual(result.excluded_currencies, (("BDT", 3), ("EUR", 1)))

    def test_currency_dimension_records_a_separate_observation(self):
        self.seed_mixed_currencies()

        business_wide = self.run_cost()
        usd = self.run_cost(dimension_type=delivery.DIMENSION_CURRENCY, dimension_value="USD")

        self.assertEqual(business_wide.total_charge, Decimal("139.75"))
        self.assertEqual(usd.currency, "USD")
        self.assertEqual(usd.total_charge, Decimal("11.00"))
        self.assertEqual(usd.shipments_in_currency, 2)
        self.assertEqual(usd.snapshot.status, WRITE_CREATED)
        self.assertEqual(len(self.table()), 2)
        row = self.snapshot(delivery.METRIC_COST, "CURRENCY", "USD")
        self.assertEqual(row.value, Decimal("11.00"))
        self.assertEqual(row.metadata["inputs"]["currency"], "USD")
        # The business-wide observation was not overwritten.
        self.assertEqual(self.snapshot(delivery.METRIC_COST).value, Decimal("139.75"))

    def test_currency_argument_contradicting_the_currency_dimension_is_rejected(self):
        self.seed_mixed_currencies()
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_cost(
                dimension_type=delivery.DIMENSION_CURRENCY, dimension_value="USD",
                currency="EUR",
            )
        self.assertEqual(self.table(), [])
        agreeing = self.run_cost(
            dimension_type=delivery.DIMENSION_CURRENCY, dimension_value="USD",
            currency="USD", record=False,
        )
        self.assertEqual(agreeing.total_charge, Decimal("11.00"))

    def test_order_paying_for_several_shipments_is_counted_once(self):
        shared = self.make_order(total="1000.00")
        single = self.make_order(total="1500.00")
        self.ship("DELIVERED", order=shared, charge="60.00")
        self.ship("DELIVERED", order=shared, charge="40.00")
        self.ship("DELIVERED", order=single, charge="100.00")

        result = self.run_cost()

        self.assertEqual(result.total_charge, Decimal("200.00"))
        self.assertEqual(result.shipments_in_currency, 3)
        self.assertEqual(result.orders_matched, 2)
        self.assertEqual(result.orders_excluded_currency_mismatch, 0)
        self.assertEqual(result.order_value_total, Decimal("2500.00"))
        self.assertEqual(result.charge_share_of_order_value, Decimal("0.08"))
        row = self.snapshot(delivery.METRIC_COST)
        self.assertEqual(row.value, Decimal("200.00"))
        self.assertEqual(Decimal(row.metadata["inputs"]["order_value_total"]), Decimal("2500.00"))
        self.assertEqual(Decimal(row.metadata["inputs"]["charge_share_of_order_value"]), Decimal("0.08"))
        self.assertEqual(row.metadata["inputs"]["orders_matched"], 2)

    def test_order_in_another_currency_is_excluded_from_order_economics(self):
        matched = self.make_order(total="1000.00", currency="BDT")
        mismatched = self.make_order(total="50.00", currency="USD")
        self.ship("DELIVERED", order=matched, charge="100.00", currency="BDT")
        self.ship("DELIVERED", order=mismatched, charge="25.00", currency="BDT")

        result = self.run_cost(record=False)

        self.assertEqual(result.total_charge, Decimal("125.00"))
        self.assertEqual(result.orders_matched, 1)
        self.assertEqual(result.orders_excluded_currency_mismatch, 1)
        # The USD order value is never added to a BDT total.
        self.assertEqual(result.order_value_total, Decimal("1000.00"))

    def test_order_belonging_to_another_business_never_contributes_value(self):
        foreign_order = self.make_order(business=self.b, total="777.00")
        self.ship("DELIVERED", order=foreign_order, charge="30.00")

        result = self.run_cost(record=False)

        self.assertEqual(result.total_charge, Decimal("30.00"))
        self.assertEqual(result.orders_matched, 0)
        self.assertEqual(result.orders_excluded_currency_mismatch, 0)
        self.assertEqual(result.order_value_total, Decimal("0"))
        self.assertIs(result.charge_share_of_order_value, UNAVAILABLE)

    def test_business_without_a_currency_requires_an_explicit_one(self):
        blank = self.make_business("blank-currency", currency="")
        sync_metric_registry(business_id=blank.pk)
        self.ship("DELIVERED", business=blank, charge="10.00", currency="BDT")

        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_cost(business=blank)
        explicit = self.run_cost(business=blank, currency="BDT")
        self.assertEqual(explicit.total_charge, Decimal("10.00"))
        self.assertEqual(explicit.snapshot.status, WRITE_CREATED)

    def test_blank_currency_argument_is_rejected(self):
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_cost(currency="   ")


# ==========================================================================
# 8. Courier and region resolution
# ==========================================================================

class CourierComparisonTests(DeliveryTestCase):

    def seed_couriers(self):
        sec = lambda seconds: INSIDE + timedelta(seconds=seconds)  # noqa: E731
        self.ship("DELIVERED", provider="Pathao", charge="60.00", delivered=sec(3600))
        self.ship("DELIVERED", provider="Pathao", charge="70.00", delivered=sec(7200))
        self.ship("FAILED", provider="Pathao", charge="50.00")
        self.ship("RETURNED", provider=" Pathao ", charge="30.00")
        self.ship("DELIVERED", provider="RedX", charge="100.00", delivered=sec(1800))
        self.ship("CANCELLED", provider="RedX", charge="0.00")
        self.ship("PENDING", provider="pathao", charge="5.00")
        # Blank providers cannot carry a dimension label.
        self.ship("DELIVERED", provider="", charge="999.00", delivered=sec(60))
        self.ship("DELIVERED", provider="   ", charge="999.00")

    def test_comparison_per_provider_with_exact_values(self):
        self.seed_couriers()
        # Business-wide count of unsubmitted shipments, in no courier's cohort.
        self.ship("FAILED", provider="Pathao", submitted=None, created=INSIDE)

        comparison = self.run_couriers()

        self.assertEqual([c.courier for c in comparison.couriers], ["Pathao", "RedX", "pathao"])
        self.assertEqual(comparison.unresolved_courier_shipments, 2)
        self.assertEqual(comparison.couriers_below_minimum, 0)
        self.assertIsNone(comparison.minimum_shipments)
        by_name = {c.courier: c for c in comparison.couriers}

        pathao = by_name["Pathao"]
        self.assert_counts(pathao.outcomes.counts, shipments=4, delivered=2, failed=1, returned=1)
        self.assertEqual(pathao.outcomes.success_rate, Decimal("0.5"))
        self.assertEqual(pathao.outcomes.failure_rate, Decimal("0.25"))
        self.assertEqual(pathao.outcomes.return_rate, Decimal("0.25"))
        self.assertEqual(pathao.outcomes.scope.dimension_type, "COURIER")
        self.assertEqual(pathao.outcomes.scope.dimension_value, "Pathao")
        self.assertEqual(pathao.timing.measured, 2)
        self.assertEqual(pathao.timing.total_seconds, Decimal("10800"))
        self.assertEqual(pathao.timing.average_seconds, Decimal("5400"))
        self.assertEqual(pathao.timing.excluded_missing_end, 2)
        self.assertEqual(pathao.cost.total_charge, Decimal("210.00"))
        self.assertEqual(pathao.cost.shipments_in_currency, 4)

        redx = by_name["RedX"]
        self.assert_counts(redx.outcomes.counts, shipments=2, delivered=1, cancelled=1)
        self.assertEqual(redx.outcomes.success_rate, Decimal("0.5"))
        self.assertEqual(redx.outcomes.failure_rate, Decimal("0"))
        self.assertEqual(redx.outcomes.return_rate, Decimal("0"))
        self.assertEqual(redx.timing.average_seconds, Decimal("1800"))
        self.assertEqual(redx.cost.total_charge, Decimal("100.00"))

        lower = by_name["pathao"]
        self.assert_counts(lower.outcomes.counts, shipments=1, in_flight=1)
        self.assertEqual(lower.outcomes.success_rate, Decimal("0"))
        self.assertIs(lower.timing.average_seconds, UNAVAILABLE)
        self.assertEqual(lower.cost.total_charge, Decimal("5.00"))

        # The unsubmitted shipment is business-wide context, repeated per courier.
        for courier in comparison.couriers:
            self.assertEqual(courier.outcomes.cohort_excluded_unsubmitted_business_wide, 1)

    def test_snapshots_exist_only_for_resolved_providers(self):
        self.seed_couriers()

        self.run_couriers()

        rows = self.table()
        # Pathao and RedX: shipments, three rates, time and cost; pathao has no time.
        self.assertEqual(len(rows), 6 + 6 + 5)
        self.assertEqual({row["dimension_type"] for row in rows}, {"COURIER"})
        self.assertEqual(
            {row["dimension_value"] for row in rows}, {"Pathao", "RedX", "pathao"},
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_COST, "COURIER", "Pathao").value, Decimal("210.00")
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_COST, "COURIER", "RedX").value, Decimal("100.00")
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_SUCCESS_RATE, "COURIER", "Pathao").value,
            Decimal("0.5"),
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_TIME, "COURIER", "RedX").value, Decimal("1800")
        )
        self.assertFalse(
            models.MetricSnapshot.objects.filter(value=Decimal("999.00")).exists()
        )

    def test_blank_providers_are_unresolved_and_never_merged(self):
        self.ship("DELIVERED", provider="", charge="10.00")
        self.ship("FAILED", provider="   ", charge="20.00")

        comparison = self.run_couriers()

        self.assertEqual(comparison.couriers, ())
        self.assertEqual(comparison.unresolved_courier_shipments, 2)
        self.assertEqual(self.table(), [])

    def test_minimum_shipments_is_a_reporting_floor_with_no_default(self):
        self.seed_couriers()

        comparison = self.run_couriers(minimum_shipments=2)

        self.assertEqual([c.courier for c in comparison.couriers], ["Pathao", "RedX"])
        self.assertEqual(comparison.couriers_below_minimum, 1)
        self.assertEqual(comparison.minimum_shipments, 2)
        self.assertEqual(comparison.unresolved_courier_shipments, 2)
        self.assertFalse(
            models.MetricSnapshot.objects.filter(dimension_value="pathao").exists()
        )

    def test_segment_choice_is_passed_to_every_provider_timing(self):
        self.ship("DELIVERED", provider="Pathao", picked=INSIDE + timedelta(seconds=300))
        self.ship("DELIVERED", provider="RedX", picked=INSIDE + timedelta(seconds=500))

        comparison = self.run_couriers(
            segment=delivery.SEGMENT_SUBMISSION_TO_PICKUP, record=False,
        )

        self.assertEqual(
            [(c.timing.segment, c.timing.start_field, c.timing.end_field,
              c.timing.average_seconds) for c in comparison.couriers],
            [("SUBMISSION_TO_PICKUP", "submitted_at", "picked_up_at", Decimal("300")),
             ("SUBMISSION_TO_PICKUP", "submitted_at", "picked_up_at", Decimal("500"))],
        )

    def test_courier_dimension_scope_for_single_operations(self):
        self.ship("DELIVERED", provider="Pathao", charge="10.00",
                  delivered=INSIDE + timedelta(seconds=600))
        self.ship("FAILED", provider="RedX", charge="20.00")

        rates = self.run_rates(dimension_type="COURIER", dimension_value=" Pathao ")
        timing = self.run_time(dimension_type="COURIER", dimension_value="Pathao")
        cost = self.run_cost(dimension_type="COURIER", dimension_value="Pathao")

        self.assert_counts(rates.counts, shipments=1, delivered=1)
        self.assertEqual(rates.success_rate, Decimal("1"))
        self.assertEqual(rates.failure_rate, Decimal("0"))
        self.assertEqual(rates.scope.dimension_value, "Pathao")
        self.assertEqual(timing.average_seconds, Decimal("600"))
        self.assertEqual(cost.total_charge, Decimal("10.00"))
        self.assertEqual(
            self.snapshot(delivery.METRIC_SUCCESS_RATE, "COURIER", "Pathao").value,
            Decimal("1"),
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_COST, "COURIER", "Pathao").value, Decimal("10.00")
        )
        # Provider labels are never case-folded.
        lower = self.run_rates(dimension_type="COURIER", dimension_value="pathao", record=False)
        self.assertEqual(lower.counts.shipments, 0)
        self.assertIs(lower.success_rate, UNAVAILABLE)


class RegionalAnalysisTests(DeliveryTestCase):

    def seed_regions(self):
        sec = lambda seconds: INSIDE + timedelta(seconds=seconds)  # noqa: E731
        self.ship("DELIVERED", metadata={"region": "Dhaka"}, delivered=sec(7200))  # r1
        self.ship("FAILED", metadata={"region": " Dhaka "})  # r2
        self.ship("DELIVERED", metadata={"region": "Chattogram"})  # r3
        self.ship("DELIVERED", metadata=None)  # r4 missing metadata
        self.ship("DELIVERED", metadata={"city": "Dhaka"})  # r5 missing key
        self.ship("DELIVERED", metadata={"region": 12})  # r6 not a string
        self.ship("DELIVERED", metadata={"region": "   "})  # r7 blank
        self.ship("DELIVERED", metadata={"region": "R" * 256})  # r8 too long
        self.ship("DELIVERED", metadata=["Dhaka"])  # r9 metadata not an object
        self.ship("DELIVERED", metadata={"region": None})  # r10 not a string
        self.ship("DELIVERED", metadata={"region": {"name": "Dhaka"}})  # r11 not a string
        self.ship("DELIVERED", metadata={"region": "dhaka"})  # r12 distinct label

    def test_regions_are_grouped_by_metadata_label_and_unresolved_are_not_bucketed(self):
        self.seed_regions()

        analysis = self.run_regions()

        self.assertEqual(analysis.region_metadata_key, "region")
        self.assertEqual(
            [r.region for r in analysis.regions], ["Chattogram", "Dhaka", "dhaka"]
        )
        by_region = {r.region: r for r in analysis.regions}

        dhaka = by_region["Dhaka"]
        self.assert_counts(dhaka.outcomes.counts, shipments=2, delivered=1, failed=1)
        self.assertEqual(dhaka.outcomes.success_rate, Decimal("0.5"))
        self.assertEqual(dhaka.outcomes.failure_rate, Decimal("0.5"))
        self.assertEqual(dhaka.outcomes.return_rate, Decimal("0"))
        self.assertEqual(dhaka.outcomes.scope.dimension_type, "REGION")
        self.assertEqual(dhaka.outcomes.inputs["scope"]["region_metadata_key"], "region")
        self.assertEqual(dhaka.timing.measured, 1)
        self.assertEqual(dhaka.timing.average_seconds, Decimal("7200"))
        self.assertEqual(dhaka.timing.excluded_missing_end, 1)

        chattogram = by_region["Chattogram"]
        self.assert_counts(chattogram.outcomes.counts, shipments=1, delivered=1)
        self.assertEqual(chattogram.outcomes.success_rate, Decimal("1"))
        self.assertIs(chattogram.timing.average_seconds, UNAVAILABLE)

        self.assert_counts(by_region["dhaka"].outcomes.counts, shipments=1, delivered=1)

        self.assertEqual(analysis.unresolved_shipments, 8)
        self.assertEqual(
            analysis.unresolved_reasons,
            (("MISSING_METADATA", 2), ("MISSING_KEY", 1), ("NOT_A_STRING", 3),
             ("BLANK", 1), ("TOO_LONG", 1)),
        )
        grouped = sum(r.outcomes.counts.shipments for r in analysis.regions)
        self.assertEqual(grouped + analysis.unresolved_shipments, 12)
        self.assertEqual(analysis.regions_below_minimum, 0)

    def test_only_resolved_regions_are_recorded(self):
        self.seed_regions()

        self.run_regions()

        rows = self.table()
        self.assertEqual(len(rows), 5 + 4 + 4)
        self.assertEqual({row["dimension_type"] for row in rows}, {"REGION"})
        self.assertEqual(
            {row["dimension_value"] for row in rows}, {"Chattogram", "Dhaka", "dhaka"},
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_FAILURE_RATE, "REGION", "Dhaka").value,
            Decimal("0.5"),
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_TIME, "REGION", "Dhaka").value, Decimal("7200")
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_SHIPMENTS, "REGION", "Dhaka")
            .metadata["inputs"]["scope"],
            {"dimension_type": "REGION", "dimension_value": "Dhaka",
             "region_metadata_key": "region"},
        )

    def test_nothing_resolvable_yields_no_regions_and_no_rows(self):
        self.ship("DELIVERED", metadata=None)
        self.ship("FAILED", metadata={"other": "Dhaka"})

        analysis = self.run_regions()

        self.assertEqual(analysis.regions, ())
        self.assertEqual(analysis.unresolved_shipments, 2)
        self.assertEqual(
            analysis.unresolved_reasons, (("MISSING_METADATA", 1), ("MISSING_KEY", 1)),
        )
        self.assertEqual(self.table(), [])

    def test_delivery_address_is_never_parsed_into_a_region(self):
        shipment = self.ship("DELIVERED", metadata=None)
        shipment.delivery_address = "House 1, Road 2, Dhaka"
        shipment.save(update_fields=["delivery_address"])

        analysis = self.run_regions()

        self.assertEqual(analysis.regions, ())
        self.assertEqual(analysis.unresolved_shipments, 1)

    def test_minimum_shipments_is_a_reporting_floor(self):
        self.seed_regions()

        analysis = self.run_regions(minimum_shipments=2, record=False)

        self.assertEqual([r.region for r in analysis.regions], ["Dhaka"])
        self.assertEqual(analysis.regions_below_minimum, 2)
        self.assertEqual(analysis.minimum_shipments, 2)
        self.assertEqual(analysis.unresolved_shipments, 8)

    def test_region_dimension_scope_for_single_operations(self):
        self.seed_regions()
        key = {"region_metadata_key": "region", "record": False}

        dhaka = self.run_rates(dimension_type="REGION", dimension_value="Dhaka", **key)
        lower = self.run_rates(dimension_type="REGION", dimension_value="dhaka", **key)
        missing = self.run_rates(dimension_type="REGION", dimension_value="Sylhet", **key)

        self.assert_counts(dhaka.counts, shipments=2, delivered=1, failed=1)
        self.assertEqual(dhaka.inputs["scope"]["region_metadata_key"], "region")
        self.assert_counts(lower.counts, shipments=1, delivered=1)
        self.assert_counts(missing.counts, shipments=0)
        self.assertIs(missing.success_rate, UNAVAILABLE)

    def test_region_scope_requires_a_key_and_a_key_requires_the_region_dimension(self):
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(dimension_type="REGION", dimension_value="Dhaka")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(dimension_type="COURIER", dimension_value="Pathao",
                           region_metadata_key="region")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(region_metadata_key="region")
        self.assertEqual(self.table(), [])

    def test_invalid_region_metadata_keys_are_rejected(self):
        for key in (None, "", "   ", " region", "region ", 5):
            with self.subTest(key=key):
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_regions(region_metadata_key=key)
        self.assertEqual(self.table(), [])


# ==========================================================================
# 9. Product grouping through relationships
# ==========================================================================

class ProductDeliveryTests(DeliveryTestCase):

    def seed_products(self):
        self.p1 = self.make_product(name="P1")
        self.p2 = self.make_product(name="P2")
        self.o1 = self.make_order()
        self.o2 = self.make_order()
        self.o3 = self.make_order()
        self.o4 = self.make_order()  # no items at all
        for order, product in ((self.o1, self.p1), (self.o1, self.p2),
                               (self.o2, self.p1), (self.o3, self.p2)):
            self.add_item(order, product)
        self.ship("DELIVERED", order=self.o1)
        self.ship("FAILED", order=self.o1)
        self.ship("DELIVERED", order=self.o2)
        self.ship("FAILED", order=self.o2)
        self.ship("RETURNED", order=self.o3)
        self.ship("DELIVERED", order=self.o3)
        self.ship("DELIVERED", order=self.o4)

    def test_shipments_count_once_per_product_and_scopes_overlap(self):
        self.seed_products()
        rebuild_relationships(business_id=self.a.pk)

        analysis = self.run_products()

        self.assertEqual([p.product_id for p in analysis.products], [self.p1.pk, self.p2.pk])
        self.assertEqual(analysis.relationship_rule_key, "bi.relationship.order_product.v1")
        self.assertEqual(analysis.shipments_without_product_relationship, 1)
        first, second = analysis.products

        self.assert_counts(first.outcomes.counts, shipments=4, delivered=2, failed=2)
        self.assertEqual(first.outcomes.success_rate, Decimal("0.5"))
        self.assertEqual(first.outcomes.failure_rate, Decimal("0.5"))
        self.assertEqual(first.outcomes.return_rate, Decimal("0"))
        self.assertEqual(first.outcomes.scope.dimension_type, "PRODUCT")
        self.assertEqual(first.outcomes.scope.dimension_value, str(self.p1.pk))

        self.assert_counts(second.outcomes.counts, shipments=4, delivered=2, failed=1, returned=1)
        self.assertEqual(second.outcomes.success_rate, Decimal("0.5"))
        self.assertEqual(second.outcomes.failure_rate, Decimal("0.25"))
        self.assertEqual(second.outcomes.return_rate, Decimal("0.25"))

        # The first order's two shipments belong to both products: scopes overlap.
        business_wide = self.run_rates(record=False)
        self.assertEqual(business_wide.counts.shipments, 7)
        per_product = sum(p.outcomes.counts.shipments for p in analysis.products)
        self.assertEqual(per_product, 8)
        self.assertNotEqual(per_product, business_wide.counts.shipments)

        rows = self.table()
        self.assertEqual(len(rows), 8)
        self.assertEqual({row["dimension_type"] for row in rows}, {"PRODUCT"})
        self.assertEqual(
            {row["dimension_value"] for row in rows}, {str(self.p1.pk), str(self.p2.pk)},
        )
        self.assertEqual(
            self.snapshot(delivery.METRIC_SHIPMENTS, "PRODUCT", str(self.p2.pk)).value,
            Decimal("4"),
        )

    def test_without_rebuilt_relationships_the_analysis_says_so(self):
        self.seed_products()
        # relationships.rebuild_relationships is deliberately never run.

        analysis = self.run_products()

        self.assertEqual(analysis.products, ())
        self.assertEqual(analysis.shipments_without_product_relationship, 7)
        self.assertEqual(analysis.relationship_rule_key, "bi.relationship.order_product.v1")
        self.assertEqual(self.table(), [])

    def test_product_dimension_filter_matches_the_analysis(self):
        self.seed_products()
        rebuild_relationships(business_id=self.a.pk)

        scoped = self.run_rates(
            dimension_type="PRODUCT", dimension_value=str(self.p1.pk), record=False,
        )

        self.assert_counts(scoped.counts, shipments=4, delivered=2, failed=2)
        self.assertEqual(scoped.success_rate, Decimal("0.5"))

    def test_expired_and_unowned_relationships_are_not_used(self):
        self.seed_products()
        rebuild_relationships(business_id=self.a.pk)
        # The relationship of the third order expired.
        models.BusinessRelationship.objects.filter(
            source_entity_type="ORDER", source_entity_id=self.o3.pk,
            relationship_type="CONTAINS_PRODUCT",
        ).update(valid_to=START)
        # A manual link on the fourth order is not the service's relationship.
        models.BusinessRelationship.objects.create(
            business=self.a, source_entity_type="ORDER", source_entity_id=self.o4.pk,
            relationship_type="CONTAINS_PRODUCT", target_entity_type="PRODUCT",
            target_entity_id=self.p1.pk, confidence=Decimal("1"),
            rule_key="manual.order_product", relationship_source="MANUAL",
            created_at=START, updated_at=START,
        )

        analysis = self.run_products(record=False)

        self.assertEqual(analysis.shipments_without_product_relationship, 3)
        by_id = {p.product_id: p for p in analysis.products}
        self.assert_counts(by_id[self.p1.pk].outcomes.counts, shipments=4, delivered=2, failed=2)
        # Only the first order's two shipments remain for the second product.
        self.assert_counts(by_id[self.p2.pk].outcomes.counts, shipments=2, delivered=1, failed=1)

    def test_minimum_shipments_is_a_reporting_floor(self):
        self.seed_products()
        rebuild_relationships(business_id=self.a.pk)

        analysis = self.run_products(minimum_shipments=5, record=False)

        self.assertEqual(analysis.products, ())
        self.assertEqual(analysis.products_below_minimum, 2)
        self.assertEqual(analysis.minimum_shipments, 5)

    def test_product_of_another_business_cannot_be_a_dimension_scope(self):
        self.seed_products()
        rebuild_relationships(business_id=self.a.pk)
        foreign = self.make_product(business=self.b, name="Foreign")

        unrecorded = self.run_rates(
            dimension_type="PRODUCT", dimension_value=str(foreign.pk), record=False,
        )
        self.assert_counts(unrecorded.counts, shipments=0)
        self.assertIs(unrecorded.success_rate, UNAVAILABLE)
        with self.assertRaises(MetricValidationError):
            self.run_rates(dimension_type="PRODUCT", dimension_value=str(foreign.pk))
        self.assertEqual(self.table(), [])


# ==========================================================================
# 10. Tenant isolation
# ==========================================================================

class TenantIsolationTests(DeliveryTestCase):

    def seed_two_businesses(self):
        self.ca = self.make_customer(self.a, "A customer")
        self.cb = self.make_customer(self.b, "B customer")
        self.pa = self.make_product(self.a, "A product")
        self.pb = self.make_product(self.b, "B product")
        order_a = self.make_order(self.a, self.ca)
        order_b = self.make_order(self.b, self.cb)
        self.add_item(order_a, self.pa)
        self.add_item(order_b, self.pb)
        self.ship("DELIVERED", business=self.a, order=order_a, customer=self.ca,
                  provider="Pathao", charge="60.00", metadata={"region": "Dhaka"},
                  delivered=INSIDE + timedelta(seconds=3600))
        self.ship("FAILED", business=self.a, order=order_a, customer=self.ca,
                  provider="Pathao", charge="40.00", metadata={"region": "Dhaka"})
        for _ in range(3):
            self.ship("FAILED", business=self.b, order=order_b, customer=self.cb,
                      provider="RedX", charge="999.00", currency="USD",
                      metadata={"region": "Sylhet"})
        rebuild_relationships(business_id=self.a.pk)
        rebuild_relationships(business_id=self.b.pk)

    def test_every_operation_reads_only_the_requested_business(self):
        self.seed_two_businesses()

        rates = self.run_rates()
        timing = self.run_time()
        cost = self.run_cost()
        couriers = self.run_couriers()
        regions = self.run_regions()
        products = self.run_products()
        customers = self.run_customers()

        self.assert_counts(rates.counts, shipments=2, delivered=1, failed=1)
        self.assertEqual(rates.success_rate, Decimal("0.5"))
        self.assertEqual(rates.failure_rate, Decimal("0.5"))
        self.assertEqual((timing.shipments, timing.measured), (2, 1))
        self.assertEqual(timing.average_seconds, Decimal("3600"))
        self.assertEqual(cost.shipments, 2)
        self.assertEqual(cost.shipments_in_currency, 2)
        self.assertEqual(cost.shipments_excluded_other_currency, 0)
        self.assertEqual(cost.excluded_currencies, ())
        self.assertEqual(cost.total_charge, Decimal("100.00"))
        self.assertEqual([c.courier for c in couriers.couriers], ["Pathao"])
        self.assertEqual(couriers.couriers[0].outcomes.counts.shipments, 2)
        self.assertEqual([r.region for r in regions.regions], ["Dhaka"])
        self.assertEqual(regions.unresolved_shipments, 0)
        self.assertEqual([p.product_id for p in products.products], [self.pa.pk])
        self.assertEqual(products.products[0].outcomes.counts.shipments, 2)
        self.assertEqual(products.shipments_without_product_relationship, 0)
        self.assertEqual([c.customer_id for c in customers.customers], [self.ca.pk])
        self.assertEqual(customers.shipments, 2)
        self.assertEqual(customers.shipments_without_customer, 0)

        # No observation was written for the other business, and every row written
        # for this one belongs to it.
        self.assertEqual(self.snapshots(business=self.b), [])
        self.assertGreater(len(self.snapshots(business=self.a)), 0)
        for row in self.snapshots(business=self.a):
            self.assertNotEqual(row.dimension_value, "RedX")
            self.assertNotEqual(row.dimension_value, "Sylhet")
            self.assertNotEqual(row.dimension_value, str(self.pb.pk))

        # The other business gets exactly its own numbers.
        other_rates = self.run_rates(business=self.b)
        other_cost = self.run_cost(business=self.b, currency="USD")
        self.assert_counts(other_rates.counts, shipments=3, failed=3)
        self.assertEqual(other_rates.failure_rate, Decimal("1"))
        self.assertEqual(other_cost.total_charge, Decimal("2997.00"))
        self.assertEqual(other_cost.shipments_in_currency, 3)

    def test_business_with_no_shipments_gets_an_empty_scope_not_another_tenant(self):
        for _ in range(3):
            self.ship("FAILED", business=self.b, provider="RedX", charge="999.00",
                      metadata={"region": "Sylhet"})

        rates = self.run_rates()
        timing = self.run_time()
        cost = self.run_cost()
        couriers = self.run_couriers()
        regions = self.run_regions()
        products = self.run_products()
        customers = self.run_customers()

        self.assert_counts(rates.counts, shipments=0)
        self.assertIs(rates.success_rate, UNAVAILABLE)
        self.assertIs(rates.failure_rate, UNAVAILABLE)
        self.assertEqual(timing.shipments, 0)
        self.assertIs(timing.average_seconds, UNAVAILABLE)
        self.assertEqual(cost.shipments, 0)
        self.assertEqual(cost.total_charge, Decimal("0"))
        self.assertEqual(couriers.couriers, ())
        self.assertEqual(couriers.unresolved_courier_shipments, 0)
        self.assertEqual(regions.regions, ())
        self.assertEqual(regions.unresolved_shipments, 0)
        self.assertEqual(products.products, ())
        self.assertEqual(products.shipments_without_product_relationship, 0)
        self.assertEqual(customers.customers, ())
        self.assertEqual(customers.shipments, 0)
        self.assertEqual(customers.shipments_without_customer, 0)
        # Only the measured zero count was written, for the requested business.
        rows = self.snapshots(business=self.a)
        self.assertEqual([row.metric.key for row in rows], [delivery.METRIC_SHIPMENTS])
        self.assertEqual(rows[0].value, Decimal("0"))
        self.assertEqual(self.snapshots(business=self.b), [])

    def test_unknown_business_is_rejected(self):
        for call in (self.run_rates, self.run_time, self.run_cost, self.run_couriers,
                     self.run_regions, self.run_products, self.run_customers):
            with self.subTest(call=call.__name__):
                with self.assertRaises(delivery.DeliveryValidationError):
                    call(business=type("Missing", (), {"pk": 999999})())
        self.assertEqual(self.table(), [])

    def test_business_without_a_synced_registry_cannot_record(self):
        unsynced = self.make_business("unsynced")
        self.ship("DELIVERED", business=unsynced)

        with self.assertRaises(MetricValidationError):
            self.run_rates(business=unsynced)
        self.assertEqual(self.table(), [])
        computed = self.run_rates(business=unsynced, record=False)
        self.assertEqual(computed.counts.shipments, 1)
        self.assertEqual(computed.success_rate, Decimal("1"))


# ==========================================================================
# 11. Dimensions and the customer analysis
# ==========================================================================

class DimensionAndCustomerTests(DeliveryTestCase):

    def test_customer_segment_dimension_is_rejected_with_an_explicit_error(self):
        self.ship("DELIVERED")
        operations = {
            "rates": self.run_rates, "time": self.run_time, "cost": self.run_cost,
        }
        for name, call in operations.items():
            with self.subTest(operation=name):
                with self.assertRaises(delivery.DeliveryValidationError) as caught:
                    call(dimension_type="CUSTOMER_SEGMENT", dimension_value="VIP")
                self.assertIn("CUSTOMER_SEGMENT", str(caught.exception))
        self.assertEqual(self.table(), [])

    def test_other_registry_dimensions_without_a_shipment_meaning_are_rejected(self):
        self.ship("DELIVERED")
        for dimension in ("CHANNEL", "CAMPAIGN", "PRODUCT_VARIANT", "WAREHOUSE"):
            with self.subTest(dimension=dimension):
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_rates(dimension_type=dimension, dimension_value="1")
        self.assertEqual(self.table(), [])

    def test_dimension_type_and_value_must_come_together(self):
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(dimension_type="COURIER")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(dimension_value="Pathao")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(dimension_type="COURIER", dimension_value="   ")
        self.assertEqual(self.table(), [])

    def test_product_dimension_value_must_be_a_canonical_id(self):
        for value in ("01", "abc", "1.5", "-1", "0"):
            with self.subTest(value=value):
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_rates(dimension_type="PRODUCT", dimension_value=value)
        self.assertEqual(self.table(), [])

    def seed_customers(self):
        self.c1 = self.make_customer(name="C1")
        self.c2 = self.make_customer(name="C2")
        self.c3 = self.make_customer(name="C3")
        for status in ("FAILED", "FAILED", "DELIVERED"):
            self.ship(status, customer=self.c1)
        for status in ("RETURNING", "RETURNED", "DELIVERED"):
            self.ship(status, customer=self.c2)
        self.ship("DELIVERED", customer=self.c3)
        self.ship("DELIVERED", customer=None)
        self.ship("FAILED", customer=None)
        # Never submitted: outside the submitted cohort, so never counted.
        self.ship("FAILED", customer=self.c1, submitted=None)

    def test_customer_analysis_counts_outcomes_per_resolved_customer(self):
        self.seed_customers()

        analysis = self.run_customers()

        self.assertEqual(analysis.shipments, 9)
        self.assertEqual(analysis.shipments_without_customer, 2)
        self.assertEqual(analysis.customers_below_minimum, 0)
        self.assertIsNone(analysis.minimum_failed_or_returned)
        self.assertEqual(
            [c.customer_id for c in analysis.customers],
            [self.c1.pk, self.c2.pk, self.c3.pk],
        )
        first, second, third = analysis.customers
        self.assert_counts(first.counts, shipments=3, delivered=1, failed=2)
        self.assertEqual(first.failed_or_returned, 2)
        self.assert_counts(second.counts, shipments=3, delivered=1, returning=1, returned=1)
        self.assertEqual(second.counts.returns, 2)
        self.assertEqual(second.failed_or_returned, 2)
        self.assert_counts(third.counts, shipments=1, delivered=1)
        self.assertEqual(third.failed_or_returned, 0)
        self.assertEqual(analysis.scope.business_id, self.a.pk)
        self.assertIsNone(analysis.scope.dimension_type)

    def test_customer_analysis_makes_no_judgement_and_records_no_snapshot(self):
        self.seed_customers()

        analysis = self.run_customers()

        self.assertEqual(self.table(), [])
        self.assertEqual(
            {f.name for f in dataclasses.fields(analysis.customers[0])},
            {"customer_id", "counts", "failed_or_returned"},
        )
        self.assertEqual(
            {f.name for f in dataclasses.fields(analysis)},
            {"scope", "customers", "shipments", "shipments_without_customer",
             "customers_below_minimum", "minimum_failed_or_returned"},
        )

    def test_customer_minimum_failed_or_returned_is_a_reporting_floor(self):
        self.seed_customers()

        analysis = self.run_customers(minimum_failed_or_returned=2)

        self.assertEqual(
            [c.customer_id for c in analysis.customers], [self.c1.pk, self.c2.pk],
        )
        self.assertEqual(analysis.customers_below_minimum, 1)
        self.assertEqual(analysis.minimum_failed_or_returned, 2)
        self.assertEqual(analysis.shipments, 9)

    def test_customer_minimum_must_be_positive(self):
        for value in (0, -1, True, "2"):
            with self.subTest(value=value):
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_customers(minimum_failed_or_returned=value)


# ==========================================================================
# Boundary validation and the closed rule registry
# ==========================================================================

class ValidationTests(DeliveryTestCase):

    def test_invalid_business_ids_are_rejected(self):
        for value in (0, -1, True, "1", None, 1.0):
            with self.subTest(value=value):
                with self.assertRaises(delivery.DeliveryValidationError):
                    delivery.calculate_delivery_outcome_rates(
                        business_id=value, period_type="CUSTOM",
                        period_start=START, period_end=END,
                    )
        self.assertEqual(self.table(), [])

    def test_invalid_periods_are_rejected(self):
        naive = datetime(2026, 10, 1)
        cases = {
            "naive start": dict(period_start=naive),
            "naive end": dict(period_end=naive + timedelta(days=1)),
            "end equals start": dict(period_end=START),
            "end before start": dict(period_end=START - timedelta(days=1)),
            "unknown period type": dict(period_type="YEAR"),
            "non-datetime": dict(period_start="2026-10-01"),
        }
        self.ship("DELIVERED")
        for name, override in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_rates(**override)
        self.assertEqual(self.table(), [])

    def test_invalid_cohort_segment_and_flag_are_rejected(self):
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(cohort="COHORT_BOGUS")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_time(segment="DELIVERY_TO_RETURN")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_couriers(segment="NOT_A_SEGMENT")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_rates(record="yes")
        with self.assertRaises(delivery.DeliveryValidationError):
            self.run_customers(cohort="COHORT_BOGUS")
        self.assertEqual(self.table(), [])

    def test_invalid_minimum_shipments_are_rejected(self):
        for value in (0, -3, True, "2"):
            with self.subTest(value=value):
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_couriers(minimum_shipments=value)
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_regions(minimum_shipments=value)
                with self.assertRaises(delivery.DeliveryValidationError):
                    self.run_products(minimum_shipments=value)


class RuleRegistryTests(DeliveryTestCase):

    def test_metric_keys_are_registered_delivery_definitions(self):
        keys = {
            delivery.METRIC_SHIPMENTS: ("COUNT", "SHIPMENTS"),
            delivery.METRIC_SUCCESS_RATE: ("RATIO", "RATIO"),
            delivery.METRIC_FAILURE_RATE: ("RATIO", "RATIO"),
            delivery.METRIC_RETURN_RATE: ("RATIO", "RATIO"),
            delivery.METRIC_TIME: ("DURATION", "SECONDS"),
            delivery.METRIC_COST: ("AMOUNT", "CURRENCY"),
        }
        for key, (value_type, unit) in keys.items():
            with self.subTest(key=key):
                definition = METRIC_DEFINITIONS[key]
                self.assertEqual(definition.category, "DELIVERY")
                self.assertEqual((definition.value_type, definition.unit), (value_type, unit))

    def test_documented_rule_strings(self):
        cases = [
            (delivery.METRIC_SHIPMENTS, delivery.COHORT_SUBMITTED, None,
             "bi.metric.delivery_shipments.v1.cohort_submitted"),
            (delivery.METRIC_SHIPMENTS, delivery.COHORT_CREATED, None,
             "bi.metric.delivery_shipments.v1.cohort_created"),
            (delivery.METRIC_SUCCESS_RATE, delivery.COHORT_SUBMITTED, None,
             "bi.metric.delivery_success_rate.v1.cohort_submitted_s1"),
            (delivery.METRIC_FAILURE_RATE, delivery.COHORT_CREATED, None,
             "bi.metric.delivery_failure_rate.v1.cohort_created_s1"),
            (delivery.METRIC_RETURN_RATE, delivery.COHORT_SUBMITTED, None,
             "bi.metric.delivery_return_rate.v1.cohort_submitted_s1"),
            (delivery.METRIC_COST, delivery.COHORT_SUBMITTED, None,
             "bi.metric.delivery_cost.v1.cohort_submitted"),
            (delivery.METRIC_TIME, delivery.COHORT_SUBMITTED,
             delivery.SEGMENT_SUBMISSION_TO_PICKUP,
             "bi.metric.delivery_time.v1.submission_to_pickup_cohort_submitted"),
            (delivery.METRIC_TIME, delivery.COHORT_CREATED,
             delivery.SEGMENT_PICKUP_TO_DELIVERY,
             "bi.metric.delivery_time.v1.pickup_to_delivery_cohort_created"),
        ]
        for metric_key, cohort, segment, expected in cases:
            with self.subTest(rule=expected):
                rule = delivery.get_delivery_rule(
                    metric_key=metric_key, cohort=cohort, segment=segment
                )
                self.assertEqual(rule.calculation_rule, expected)
                self.assertEqual(rule.metric_key, metric_key)
                self.assertEqual(rule.cohort, cohort)
                self.assertEqual(rule.segment, segment)

    def test_every_combination_resolves_to_a_distinct_valid_rule(self):
        seen = {}
        for cohort in (delivery.COHORT_SUBMITTED, delivery.COHORT_CREATED):
            for metric_key in (delivery.METRIC_SHIPMENTS, delivery.METRIC_SUCCESS_RATE,
                               delivery.METRIC_FAILURE_RATE, delivery.METRIC_RETURN_RATE,
                               delivery.METRIC_COST):
                rule = delivery.get_delivery_rule(metric_key=metric_key, cohort=cohort)
                seen[(metric_key, cohort, None)] = rule.calculation_rule
            for segment in (delivery.SEGMENT_SUBMISSION_TO_DELIVERY,
                            delivery.SEGMENT_SUBMISSION_TO_PICKUP,
                            delivery.SEGMENT_PICKUP_TO_DELIVERY):
                rule = delivery.get_delivery_rule(
                    metric_key=delivery.METRIC_TIME, cohort=cohort, segment=segment
                )
                seen[(delivery.METRIC_TIME, cohort, segment)] = rule.calculation_rule
        self.assertEqual(len(seen), 16)
        self.assertEqual(len(set(seen.values())), 16)
        for rule in seen.values():
            self.assertRegex(rule, r"^bi\.metric\.delivery_[a-z_]+\.v1\.[a-z0-9_]+$")
            self.assertLessEqual(len(rule), 100)

    def test_invalid_rule_requests_are_rejected(self):
        bad = [
            dict(metric_key="bi.metric.sales_total_orders.v1", cohort=delivery.COHORT_SUBMITTED),
            dict(metric_key="nonsense", cohort=delivery.COHORT_SUBMITTED),
            dict(metric_key=delivery.METRIC_SUCCESS_RATE, cohort="COHORT_BOGUS"),
            dict(metric_key=delivery.METRIC_TIME, cohort=delivery.COHORT_SUBMITTED),
            dict(metric_key=delivery.METRIC_COST, cohort=delivery.COHORT_SUBMITTED,
                 segment=delivery.SEGMENT_SUBMISSION_TO_DELIVERY),
            dict(metric_key=delivery.METRIC_TIME, cohort=delivery.COHORT_SUBMITTED,
                 segment="BOGUS"),
        ]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(delivery.DeliveryValidationError):
                    delivery.get_delivery_rule(**kwargs)

    def test_recorded_rule_resolves_back_to_its_definition(self):
        self.ship("DELIVERED", delivered=INSIDE + timedelta(seconds=5))
        self.run_time(segment=delivery.SEGMENT_PICKUP_TO_DELIVERY, record=False)
        self.run_time()
        row = self.snapshot(delivery.METRIC_TIME)
        match = re.match(r"^(bi\.metric\.delivery_time\.v1)\.(.+)$", row.calculation_rule)
        self.assertIsNotNone(match)
        rule = delivery.get_delivery_rule(
            metric_key=delivery.METRIC_TIME, cohort=delivery.COHORT_SUBMITTED,
            segment=delivery.SEGMENT_SUBMISSION_TO_DELIVERY,
        )
        self.assertEqual(row.calculation_rule, rule.calculation_rule)
        self.assertEqual((rule.value_type, rule.unit), ("DURATION", "SECONDS"))
