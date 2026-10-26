"""BI §2 Business Metrics and §3 Metric Snapshots: registry, periods, dimensions,
decimal values, unavailable data, replay/revision and historical comparison.

Every test drives the public service with original inputs against persisted rows;
only the service clock is patched. Findings, thresholds and metric arithmetic are
out of scope here (later tickets): this suite pins how a value is stored, scoped
and read back.
"""

import dataclasses
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from app import models
from app.business_intelligence import (
    CATEGORIES,
    COMPARISON_DIRECTIONS,
    DIMENSION_TYPES,
    DIRECTION_DECREASED,
    DIRECTION_INCREASED,
    DIRECTION_UNAVAILABLE,
    DIRECTION_UNCHANGED,
    METRIC_DEFINITIONS,
    PERIOD_TYPES,
    UNAVAILABLE,
    UNITS,
    VALUE_TYPE_UNITS,
    VALUE_TYPES,
    WRITE_CREATED,
    WRITE_NOT_RECORDED_UNAVAILABLE,
    WRITE_STATUSES,
    WRITE_UNCHANGED,
    WRITE_UPDATED,
    MetricComparison,
    MetricDefinition,
    MetricDefinitionError,
    MetricObservation,
    MetricRegistrySyncResult,
    MetricSnapshotConflictError,
    MetricValidationError,
    SnapshotWriteResult,
    compare_metric_periods,
    get_metric_definition,
    get_metric_observation,
    get_metric_snapshot,
    list_metric_definitions,
    list_metric_snapshots,
    record_metric_snapshot,
    sync_metric_registry,
)
from app.business_intelligence import metrics as metrics_module


T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=1)
T2 = T0 + timedelta(days=2)
T3 = T0 + timedelta(days=3)
T4 = T0 + timedelta(days=4)
NOW = "app.business_intelligence.metrics.timezone.now"
OWNER = "business_intelligence.metrics"

ORDERS = "bi.metric.sales_total_orders.v1"
UNITS_SOLD = "bi.metric.sales_units_sold.v1"
AOV = "bi.metric.sales_average_order_value.v1"
CANCEL_RATE = "bi.metric.sales_cancellation_rate.v1"

CATEGORY_COUNTS = {
    "SALES": 5, "REVENUE": 5, "CUSTOMER": 5, "MARKETING": 10,
    "SUPPORT": 5, "WEBSITE": 6, "DELIVERY": 6,
}

# One entry per concept the specification names in §2, keyed by its category.
SPEC_CONCEPTS = {
    "SALES": ["sales_total_orders", "sales_units_sold", "sales_average_order_value",
              "sales_cancellation_rate", "sales_growth_rate"],
    "REVENUE": ["revenue_gross", "revenue_refunded", "revenue_growth_rate",
                "revenue_per_customer"],
    "CUSTOMER": ["customer_new_customers", "customer_repeat_rate",
                 "customer_purchase_frequency"],
    "MARKETING": ["marketing_spend", "marketing_impressions", "marketing_clicks",
                  "marketing_click_through_rate", "marketing_cost_per_click",
                  "marketing_cost_per_mille", "marketing_conversion_rate",
                  "marketing_return_on_ad_spend"],
    "SUPPORT": ["support_response_time", "support_resolution_time",
                "support_conversation_volume", "support_unresolved_cases",
                "support_escalation_rate"],
    "WEBSITE": ["website_conversion_rate", "website_checkout_completion_rate",
                "website_cart_abandonment_rate", "website_product_view_conversion_rate"],
    "DELIVERY": ["delivery_success_rate", "delivery_failure_rate",
                 "delivery_return_rate", "delivery_time"],
}


class MetricTestCase(TestCase):
    """Shared fixtures: two synchronized businesses and explicit small defaults."""

    def setUp(self):
        self.business = models.Business.objects.create(
            name="Fixture shop", slug="fixture-shop", created_at=T0, updated_at=T0,
        )
        self.other = models.Business.objects.create(
            name="Other shop", slug="other-shop", created_at=T0, updated_at=T0,
        )
        self.sync(self.business)
        self.sync(self.other)

    # -- fixtures ---------------------------------------------------------

    def make(self, model, business=None, **values):
        defaults = {
            models.Product: {"name": "Fixture product"},
            models.Campaign: {"name": "Fixture campaign", "platform": "META"},
        }.get(model, {}).copy()
        fields = {field.name for field in model._meta.fields}
        if "business" in fields:
            defaults["business"] = business or self.business
        for field in ("created_at", "updated_at"):
            if field in fields:
                defaults[field] = T0
        defaults.update(values)
        return model.objects.create(**defaults)

    def sync(self, business=None, at=T0):
        with patch(NOW, return_value=at):
            return sync_metric_registry(business_id=(business or self.business).pk)

    def record(self, *, at=T1, business=None, **overrides):
        params = dict(
            business_id=(business or self.business).pk, metric_key=ORDERS,
            value=Decimal("10"), period_type="DAY", period_start=T0, period_end=T1,
        )
        params.update(overrides)
        with patch(NOW, return_value=at):
            return record_metric_snapshot(**params)

    def metric_row(self, key=ORDERS, business=None):
        return models.BusinessMetric.objects.get(
            business=business or self.business, key=key,
        )

    def raw_snapshot(self, *, metadata, business=None, metric=None, value=Decimal("1"),
                     start=T0, end=T1, period_type="DAY", dimension_type=None,
                     dimension_value=None):
        """A row written behind the service's back (a non-cooperating writer)."""
        business = business or self.business
        return models.MetricSnapshot.objects.create(
            metric=metric or self.metric_row(business=business), business=business,
            value=value, dimension_type=dimension_type, dimension_value=dimension_value,
            period_type=period_type, period_start=start, period_end=end,
            calculation_rule=ORDERS, metadata=metadata, calculated_at=T0, created_at=T0,
        )

    def rows(self):
        return list(models.MetricSnapshot.objects.order_by("pk").values())

    def metric_rows(self):
        return list(models.BusinessMetric.objects.order_by("pk").values())

    def assert_rejected(self, exception=MetricValidationError, **overrides):
        """The call raises and the snapshot table is exactly as it was."""
        before = self.rows()
        with self.assertRaises(exception):
            self.record(**overrides)
        self.assertEqual(self.rows(), before)

    def day(self, index):
        return T0 + timedelta(days=index), T0 + timedelta(days=index + 1)


# ==========================================================================
# §2 Metric Registry
# ==========================================================================

class MetricRegistryDefinitionTests(TestCase):
    """The closed registry: one documented name, category, value type and unit."""

    def test_registry_has_42_definitions_with_consistent_keys(self):
        self.assertEqual(len(METRIC_DEFINITIONS), 42)
        for key, definition in METRIC_DEFINITIONS.items():
            with self.subTest(key=key):
                self.assertIsInstance(definition, MetricDefinition)
                self.assertEqual(definition.key, key)
                self.assertRegex(key, r"^bi\.metric\.[a-z0-9_]+\.v1$")
                self.assertTrue(definition.name.strip())
                self.assertTrue(definition.description.strip())

    def test_every_definition_uses_a_valid_value_type_and_unit_pairing(self):
        for key, definition in METRIC_DEFINITIONS.items():
            with self.subTest(key=key):
                self.assertIn(definition.value_type, VALUE_TYPES)
                self.assertIn(definition.unit, VALUE_TYPE_UNITS[definition.value_type])
                self.assertIn(definition.unit, UNITS)

    def test_unit_conventions_are_fixed_by_value_type(self):
        self.assertEqual(VALUE_TYPES, {"COUNT", "AMOUNT", "RATIO", "DURATION", "NUMBER"})
        self.assertEqual(VALUE_TYPE_UNITS["AMOUNT"], {"CURRENCY"})
        self.assertEqual(VALUE_TYPE_UNITS["RATIO"], {"RATIO"})
        self.assertEqual(VALUE_TYPE_UNITS["DURATION"], {"SECONDS"})
        for key, definition in METRIC_DEFINITIONS.items():
            with self.subTest(key=key):
                if definition.value_type == "AMOUNT":
                    self.assertEqual(definition.unit, "CURRENCY")
                if definition.value_type == "RATIO":
                    self.assertEqual(definition.unit, "RATIO")
                if definition.value_type == "DURATION":
                    self.assertEqual(definition.unit, "SECONDS")
        expected = {
            "sales_total_orders": ("COUNT", "ORDERS"),
            "sales_average_order_value": ("AMOUNT", "CURRENCY"),
            "sales_cancellation_rate": ("RATIO", "RATIO"),
            "customer_purchase_frequency": ("NUMBER", "ORDERS_PER_CUSTOMER"),
            "marketing_click_through_rate": ("RATIO", "RATIO"),
            "marketing_cost_per_click": ("AMOUNT", "CURRENCY"),
            "support_response_time": ("DURATION", "SECONDS"),
            "delivery_time": ("DURATION", "SECONDS"),
            "delivery_shipments": ("COUNT", "SHIPMENTS"),
        }
        for name, pair in expected.items():
            with self.subTest(metric=name):
                definition = METRIC_DEFINITIONS[f"bi.metric.{name}.v1"]
                self.assertEqual((definition.value_type, definition.unit), pair)

    def test_all_seven_documented_categories_are_present_with_exact_counts(self):
        self.assertEqual(
            CATEGORIES,
            {"SALES", "REVENUE", "CUSTOMER", "MARKETING", "SUPPORT", "WEBSITE", "DELIVERY"},
        )
        self.assertEqual({d.category for d in METRIC_DEFINITIONS.values()}, set(CATEGORIES))
        for category, count in CATEGORY_COUNTS.items():
            with self.subTest(category=category):
                listed = list_metric_definitions(category=category)
                self.assertEqual(len(listed), count)
                self.assertTrue(all(d.category == category for d in listed))
        self.assertEqual(sum(CATEGORY_COUNTS.values()), 42)

    def test_every_concept_named_by_the_specification_is_registered_in_its_category(self):
        for category, names in SPEC_CONCEPTS.items():
            listed_keys = {d.key for d in list_metric_definitions(category=category)}
            for name in names:
                with self.subTest(category=category, metric=name):
                    self.assertIn(f"bi.metric.{name}.v1", listed_keys)

    def test_list_definitions_is_a_key_sorted_tuple_and_rejects_unknown_categories(self):
        everything = list_metric_definitions()
        self.assertIsInstance(everything, tuple)
        self.assertEqual([d.key for d in everything], sorted(METRIC_DEFINITIONS))
        self.assertEqual(everything, tuple(METRIC_DEFINITIONS[k] for k in sorted(METRIC_DEFINITIONS)))
        for bad in ("sales", "FINANCE", "", 5):
            with self.subTest(category=bad):
                with self.assertRaises(MetricValidationError):
                    list_metric_definitions(category=bad)

    def test_get_definition_returns_the_documented_definition(self):
        definition = get_metric_definition(metric_key=ORDERS)
        self.assertIs(definition, METRIC_DEFINITIONS[ORDERS])
        self.assertEqual(
            (definition.key, definition.name, definition.category,
             definition.value_type, definition.unit),
            (ORDERS, "Total Orders", "SALES", "COUNT", "ORDERS"),
        )

    def test_get_definition_raises_for_unknown_or_malformed_keys(self):
        cases = {
            "well_formed_but_unregistered": "bi.metric.nope.v1",
            "unregistered_version": "bi.metric.sales_total_orders.v2",
            "missing_prefix": "sales_total_orders",
            "missing_version": "bi.metric.sales_total_orders",
            "uppercase": "BI.METRIC.SALES_TOTAL_ORDERS.V1",
            "empty": "",
            "none": None,
            "integer": 5,
        }
        for name, key in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(MetricValidationError):
                    get_metric_definition(metric_key=key)

    def test_public_calls_are_keyword_only(self):
        with self.assertRaises(TypeError):
            get_metric_definition(ORDERS)
        with self.assertRaises(TypeError):
            list_metric_definitions("SALES")
        with self.assertRaises(TypeError):
            sync_metric_registry(1)

    def test_definitions_and_results_are_frozen(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            METRIC_DEFINITIONS[ORDERS].name = "Changed"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            MetricRegistrySyncResult().created = 1

    def test_inconsistent_definition_is_rejected_loudly(self):
        base = dict(display="Thing", category="SALES", value_type="COUNT",
                    unit="ORDERS", description="Counts a thing.")
        metrics_module._define("thing", **base)
        cases = {
            "unit_not_valid_for_value_type": dict(base, unit="CURRENCY"),
            "unknown_unit": dict(base, unit="PARSECS"),
            "unknown_value_type": dict(base, value_type="PERCENT"),
            "unknown_category": dict(base, category="FINANCE"),
            "empty_description": dict(base, description=""),
            "empty_display": dict(base, display=""),
        }
        for name, params in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(MetricDefinitionError):
                    metrics_module._define("thing", **params)
        for bad_name in ("Thing", "1thing", "a-b", ""):
            with self.subTest(name=bad_name):
                with self.assertRaises(MetricDefinitionError):
                    metrics_module._define(bad_name, **base)


class MetricRegistrySyncTests(MetricTestCase):
    """Materializing the registry per business (§2 Metric Registry)."""

    def test_sync_creates_one_active_row_per_definition_for_that_business_only(self):
        fresh = self.make(models.Business, name="Fresh", slug="fresh", business=None)
        self.assertEqual(models.BusinessMetric.objects.filter(business=fresh).count(), 0)
        result = self.sync(fresh, at=T1)
        self.assertEqual(result, MetricRegistrySyncResult(created=42))
        rows = {row.key: row for row in models.BusinessMetric.objects.filter(business=fresh)}
        self.assertEqual(set(rows), set(METRIC_DEFINITIONS))
        for key, definition in METRIC_DEFINITIONS.items():
            with self.subTest(key=key):
                row = rows[key]
                self.assertEqual(
                    (row.name, row.category, row.value_type, row.unit, row.description,
                     row.is_active, row.created_at, row.updated_at),
                    (definition.name, definition.category, definition.value_type,
                     definition.unit, definition.description, True, T1, T1),
                )
        self.assertEqual(models.BusinessMetric.objects.filter(business=self.business).count(), 42)
        self.assertEqual(models.BusinessMetric.objects.count(), 126)

    def test_sync_replay_reports_unchanged_and_touches_no_row(self):
        before = self.metric_rows()
        self.assertEqual(self.sync(at=T2), MetricRegistrySyncResult(unchanged=42))
        self.assertEqual(self.metric_rows(), before)
        self.assertEqual(len(before), 84)

    def test_sync_repairs_drift_in_name_category_and_unit_only_on_drifted_rows(self):
        models.BusinessMetric.objects.filter(business=self.business, key=ORDERS).update(
            name="Orders (renamed)")
        models.BusinessMetric.objects.filter(business=self.business, key=UNITS_SOLD).update(
            category="REVENUE")
        models.BusinessMetric.objects.filter(business=self.business, key=AOV).update(
            unit="UNITS")
        other_before = list(models.BusinessMetric.objects.filter(business=self.other).values())
        result = self.sync(at=T2)
        self.assertEqual(result, MetricRegistrySyncResult(updated=3, unchanged=39))
        for key in (ORDERS, UNITS_SOLD, AOV):
            with self.subTest(key=key):
                row, definition = self.metric_row(key), METRIC_DEFINITIONS[key]
                self.assertEqual(
                    (row.name, row.category, row.value_type, row.unit, row.is_active,
                     row.created_at, row.updated_at),
                    (definition.name, definition.category, definition.value_type,
                     definition.unit, True, T0, T2),
                )
        untouched = models.BusinessMetric.objects.filter(business=self.business).exclude(
            key__in=[ORDERS, UNITS_SOLD, AOV])
        self.assertEqual(untouched.count(), 39)
        self.assertEqual({row.updated_at for row in untouched}, {T0})
        self.assertEqual(
            list(models.BusinessMetric.objects.filter(business=self.other).values()),
            other_before,
        )

    def test_sync_repairs_value_type_drift(self):
        models.BusinessMetric.objects.filter(business=self.business, key=CANCEL_RATE).update(
            value_type="NUMBER")
        self.assertEqual(self.sync(at=T2), MetricRegistrySyncResult(updated=1, unchanged=41))
        self.assertEqual(self.metric_row(CANCEL_RATE).value_type, "RATIO")

    def test_sync_reactivates_a_definition_that_was_switched_off(self):
        models.BusinessMetric.objects.filter(business=self.business, key=ORDERS).update(
            is_active=False)
        self.assertEqual(self.sync(at=T2), MetricRegistrySyncResult(updated=1, unchanged=41))
        row = self.metric_row(ORDERS)
        self.assertEqual((row.is_active, row.updated_at), (True, T2))

    def test_sync_deactivates_but_never_deletes_a_retired_service_metric(self):
        retired = "bi.metric.retired_thing.v1"
        self.make(
            models.BusinessMetric, key=retired, name="Retired", category="SALES",
            value_type="COUNT", unit="ORDERS", description="gone", is_active=True,
        )
        before_count = models.BusinessMetric.objects.filter(business=self.business).count()
        self.assertEqual(before_count, 43)
        result = self.sync(at=T2)
        self.assertEqual(result, MetricRegistrySyncResult(unchanged=42, deactivated=1))
        row = self.metric_row(retired)
        self.assertEqual((row.is_active, row.updated_at, row.name), (False, T2, "Retired"))
        self.assertEqual(
            models.BusinessMetric.objects.filter(business=self.business).count(), 43)
        # A repeat run neither re-reports nor re-touches the already retired row.
        self.assertEqual(self.sync(at=T3), MetricRegistrySyncResult(unchanged=42))
        self.assertEqual(self.metric_row(retired).updated_at, T2)

    def test_retired_metric_keeps_its_snapshots_and_they_are_hidden_unless_requested(self):
        created = self.record()
        snapshot_id = created.observation.snapshot_id
        retired = "bi.metric.retired_thing.v1"
        models.BusinessMetric.objects.filter(business=self.business, key=ORDERS).update(key=retired)
        result = self.sync(at=T2)
        self.assertEqual(result, MetricRegistrySyncResult(created=1, unchanged=41, deactivated=1))
        self.assertTrue(models.MetricSnapshot.objects.filter(pk=snapshot_id).exists())
        self.assertFalse(self.metric_row(retired).is_active)
        self.assertTrue(self.metric_row(ORDERS).is_active)
        self.assertEqual(
            list_metric_snapshots(business_id=self.business.pk, metric_key=retired), ())
        shown = list_metric_snapshots(
            business_id=self.business.pk, metric_key=retired, include_inactive_metrics=True)
        self.assertEqual([(o.snapshot_id, o.metric_key) for o in shown],
                         [(snapshot_id, retired)])

    def test_sync_leaves_rows_without_the_service_prefix_untouched(self):
        foreign = {
            "custom.margin": True,
            "my.bi.metric.thing.v1": True,
            "legacy_revenue": False,
        }
        for key, active in foreign.items():
            self.make(
                models.BusinessMetric, key=key, name=f"Mine {key}", category="OTHER",
                value_type="NUMBER", unit="WIDGETS", description="owned elsewhere",
                is_active=active,
            )
        before = list(models.BusinessMetric.objects.filter(key__in=foreign).order_by("pk").values())
        self.assertEqual(len(before), 3)
        self.assertEqual(self.sync(at=T2), MetricRegistrySyncResult(unchanged=42))
        self.assertEqual(
            list(models.BusinessMetric.objects.filter(key__in=foreign).order_by("pk").values()),
            before,
        )

    def test_sync_for_one_business_never_touches_another_business(self):
        retired = "bi.metric.retired_thing.v1"
        self.make(models.BusinessMetric, business=self.other, key=retired, name="Retired",
                  category="SALES", value_type="COUNT", unit="ORDERS", is_active=True)
        models.BusinessMetric.objects.filter(business=self.other, key=ORDERS).update(name="Drift")
        other_before = list(models.BusinessMetric.objects.filter(business=self.other).values())
        self.assertEqual(self.sync(at=T2), MetricRegistrySyncResult(unchanged=42))
        self.assertEqual(
            list(models.BusinessMetric.objects.filter(business=self.other).values()),
            other_before,
        )

    def test_sync_rejects_invalid_or_unknown_business_ids(self):
        before = self.metric_rows()
        for bad in (0, -1, True, "1", None, 1.0, 987654):
            with self.subTest(business_id=bad):
                with self.assertRaises(MetricValidationError):
                    sync_metric_registry(business_id=bad)
        self.assertEqual(self.metric_rows(), before)

    def test_writes_to_an_inactive_metric_are_rejected_until_it_is_reactivated(self):
        models.BusinessMetric.objects.filter(business=self.business, key=ORDERS).update(
            is_active=False)
        self.assert_rejected()
        self.assert_rejected(value=UNAVAILABLE)
        self.sync(at=T2)
        self.assertEqual(self.record().status, WRITE_CREATED)

    def test_writes_to_a_metric_not_registered_for_the_business_are_rejected(self):
        fresh = self.make(models.Business, name="Fresh", slug="fresh", business=None)
        with self.assertRaises(MetricValidationError):
            self.record(business=fresh)
        self.assertEqual(self.rows(), [])
        for key in ("bi.metric.nope.v1", ORDERS.replace(".v1", ".v2"), "sales_total_orders"):
            with self.subTest(key=key):
                self.assert_rejected(metric_key=key)

    def test_unknown_business_and_bad_business_ids_are_rejected_on_write(self):
        for bad in (0, -5, True, "1", None, 987654):
            with self.subTest(business_id=bad):
                self.assert_rejected(business_id=bad)

    def test_snapshot_arguments_are_keyword_only_and_calculated_at_is_not_caller_controlled(self):
        with self.assertRaises(TypeError):
            record_metric_snapshot(self.business.pk, ORDERS, Decimal("1"), "DAY", T0, T1)
        with self.assertRaises(TypeError):
            self.record(calculated_at=T4)
        self.assertEqual(self.rows(), [])


# ==========================================================================
# §3 Time-Based Metric Storage
# ==========================================================================

class MetricPeriodTests(MetricTestCase):
    """Half-open [period_start, period_end) with timezone-aware bounds."""

    def test_period_end_must_be_strictly_after_period_start(self):
        cases = {
            "equal": (T1, T1),
            "end_one_microsecond_before_start": (T1, T1 - timedelta(microseconds=1)),
            "end_a_day_before_start": (T2, T1),
        }
        for name, (start, end) in cases.items():
            with self.subTest(case=name):
                self.assert_rejected(period_start=start, period_end=end)

    def test_smallest_positive_period_is_accepted_with_exact_bounds(self):
        end = T0 + timedelta(microseconds=1)
        result = self.record(period_start=T0, period_end=end)
        self.assertEqual(result.status, WRITE_CREATED)
        row = models.MetricSnapshot.objects.get()
        self.assertEqual((row.period_start, row.period_end), (T0, end))

    def test_naive_datetimes_are_rejected(self):
        naive0, naive1 = datetime(2026, 10, 1), datetime(2026, 10, 2)
        cases = {
            "both_naive": (naive0, naive1),
            "naive_start": (naive0, T1),
            "naive_end": (T0, naive1),
        }
        for name, (start, end) in cases.items():
            with self.subTest(case=name):
                self.assert_rejected(period_start=start, period_end=end)

    def test_dates_strings_and_none_are_not_datetimes(self):
        cases = {
            "date_objects": (date(2026, 10, 1), date(2026, 10, 2)),
            "date_start": (date(2026, 10, 1), T1),
            "date_end": (T0, date(2026, 10, 2)),
            "iso_strings": ("2026-10-01T00:00:00+00:00", "2026-10-02T00:00:00+00:00"),
            "none_start": (None, T1),
            "none_end": (T0, None),
            "timestamps": (1790812800, 1790899200),
        }
        for name, (start, end) in cases.items():
            with self.subTest(case=name):
                self.assert_rejected(period_start=start, period_end=end)

    def test_period_type_is_a_closed_label_vocabulary(self):
        self.assertEqual(PERIOD_TYPES, {"HOUR", "DAY", "WEEK", "MONTH", "CUSTOM"})
        for bad in ("YEAR", "day", "", None, 7):
            with self.subTest(period_type=bad):
                self.assert_rejected(period_type=bad)

    def test_every_period_type_stores_a_distinct_logical_observation(self):
        ids = set()
        for period_type in sorted(PERIOD_TYPES):
            with self.subTest(period_type=period_type):
                result = self.record(period_type=period_type, value=Decimal("1"))
                self.assertEqual(result.status, WRITE_CREATED)
                self.assertEqual(result.observation.period_type, period_type)
                ids.add(result.observation.snapshot_id)
        self.assertEqual(len(ids), 5)
        self.assertEqual(models.MetricSnapshot.objects.count(), 5)

    def test_half_open_boundary_adjacent_periods_are_different_logical_rows(self):
        first = self.record(period_start=T0, period_end=T1, value=Decimal("10"))
        second = self.record(period_start=T1, period_end=T2, value=Decimal("20"))
        self.assertEqual((first.status, second.status), (WRITE_CREATED, WRITE_CREATED))
        self.assertNotEqual(first.observation.snapshot_id, second.observation.snapshot_id)
        self.assertEqual(models.MetricSnapshot.objects.count(), 2)
        for start, end, value, snapshot_id in (
            (T0, T1, Decimal("10"), first.observation.snapshot_id),
            (T1, T2, Decimal("20"), second.observation.snapshot_id),
        ):
            with self.subTest(start=start):
                observation = get_metric_snapshot(
                    business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                    period_start=start, period_end=end)
                self.assertEqual((observation.snapshot_id, observation.value), (snapshot_id, value))

    def test_changing_either_bound_by_one_microsecond_is_a_different_observation(self):
        base = self.record()
        later_end = self.record(period_end=T1 + timedelta(microseconds=1))
        later_start = self.record(period_start=T0 + timedelta(microseconds=1))
        self.assertEqual((later_end.status, later_start.status), (WRITE_CREATED, WRITE_CREATED))
        self.assertEqual(
            len({base.observation.snapshot_id, later_end.observation.snapshot_id,
                 later_start.observation.snapshot_id}), 3)
        self.assertEqual(models.MetricSnapshot.objects.count(), 3)

    def test_equal_instants_in_different_utc_offsets_are_one_logical_observation(self):
        dhaka = timezone(timedelta(hours=6))
        first = self.record()
        again = self.record(at=T2, period_start=T0.astimezone(dhaka),
                            period_end=T1.astimezone(dhaka))
        self.assertEqual(again.status, WRITE_UNCHANGED)
        self.assertEqual(again.observation.snapshot_id, first.observation.snapshot_id)
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

    def test_period_is_validated_on_every_read_operation(self):
        base = dict(business_id=self.business.pk, metric_key=ORDERS, period_type="DAY")
        naive = datetime(2026, 10, 1)
        with self.assertRaises(MetricValidationError):
            get_metric_snapshot(**base, period_start=T1, period_end=T1)
        with self.assertRaises(MetricValidationError):
            get_metric_snapshot(**base, period_start=naive, period_end=T1)
        with self.assertRaises(MetricValidationError):
            list_metric_snapshots(business_id=self.business.pk, window_start=naive)
        with self.assertRaises(MetricValidationError):
            list_metric_snapshots(business_id=self.business.pk, window_start=T2, window_end=T2)
        with self.assertRaises(MetricValidationError):
            list_metric_snapshots(business_id=self.business.pk, window_start=T2, window_end=T1)
        with self.assertRaises(MetricValidationError):
            compare_metric_periods(
                **base, current_period_start=T1, current_period_end=T1,
                previous_period_start=T0, previous_period_end=T1)


# ==========================================================================
# §2 Metric Dimensions / §3 Dimension-Based Snapshots
# ==========================================================================

class MetricDimensionTests(MetricTestCase):

    def setUp(self):
        super().setUp()
        self.product = self.make(models.Product)
        self.variant = self.make(models.ProductVariant, product=self.product)
        self.campaign = self.make(models.Campaign)
        self.other_product = self.make(models.Product, business=self.other)
        self.other_variant = self.make(models.ProductVariant, product=self.other_product)
        self.other_campaign = self.make(models.Campaign, business=self.other)

    def test_specification_dimensions_exist_with_entity_and_label_kinds(self):
        self.assertTrue(
            {"PRODUCT", "CAMPAIGN", "REGION", "COURIER", "CHANNEL", "CUSTOMER_SEGMENT"}
            <= set(DIMENSION_TYPES)
        )
        self.assertEqual(
            {name for name, kind in DIMENSION_TYPES.items() if kind == "ENTITY"},
            {"PRODUCT", "PRODUCT_VARIANT", "CAMPAIGN"},
        )
        self.assertEqual(set(DIMENSION_TYPES.values()), {"ENTITY", "LABEL"})

    def test_dimension_type_without_value_and_value_without_type_are_both_rejected(self):
        cases = {
            "type_only_label": dict(dimension_type="REGION"),
            "type_only_entity": dict(dimension_type="PRODUCT"),
            "value_only": dict(dimension_value="Dhaka"),
            "value_only_numeric": dict(dimension_value=str(self.product.pk)),
        }
        for name, params in cases.items():
            with self.subTest(case=name):
                self.assert_rejected(**params)

    def test_dimension_type_outside_the_closed_set_is_rejected(self):
        for bad in ("CUSTOMER", "product", "Region", "REGION ", "", "WAREHOUSE", 5):
            with self.subTest(dimension_type=bad):
                self.assert_rejected(dimension_type=bad, dimension_value="x")

    def test_dimension_value_must_be_a_non_blank_string_of_at_most_255_characters(self):
        for bad in ("", "   ", "x" * 256, 5, b"Dhaka"):
            with self.subTest(dimension_value=bad if not isinstance(bad, str) else len(bad)):
                self.assert_rejected(dimension_type="REGION", dimension_value=bad)
        result = self.record(dimension_type="REGION", dimension_value="x" * 255)
        self.assertEqual(result.status, WRITE_CREATED)
        self.assertEqual(models.MetricSnapshot.objects.get().dimension_value, "x" * 255)

    def test_label_dimension_is_stored_verbatim_after_whitespace_strip_and_case_is_exact(self):
        stripped = self.record(dimension_type="REGION", dimension_value="  Dhaka\t")
        self.assertEqual(stripped.observation.dimension_value, "Dhaka")
        replay = self.record(at=T2, dimension_type="REGION", dimension_value="Dhaka")
        self.assertEqual(replay.status, WRITE_UNCHANGED)
        lower = self.record(dimension_type="REGION", dimension_value="dhaka")
        self.assertEqual(lower.status, WRITE_CREATED)
        self.assertNotEqual(lower.observation.snapshot_id, stripped.observation.snapshot_id)
        self.assertEqual(models.MetricSnapshot.objects.count(), 2)

    def test_entity_dimension_values_must_be_canonical_positive_ids(self):
        for bad in ("0", "007", "00", f"0{self.product.pk}", "-1", "1.5", "abc", "1e3", "+1"):
            with self.subTest(dimension_value=bad):
                self.assert_rejected(dimension_type="PRODUCT", dimension_value=bad)

    def test_entity_dimension_values_must_be_ascii_digits_so_one_id_has_one_spelling(self):
        # A canonical primary-key string has exactly one spelling; a non-ASCII digit
        # string that int() reads as a real product id would create a second logical
        # observation for the same product (or escape the validation entirely).
        arabic_indic = "".join(chr(0x0660 + int(d)) for d in str(self.product.pk))
        fullwidth = "".join(chr(0xFF10 + int(d)) for d in str(self.product.pk))
        for name, bad in {
            "arabic_indic_digits_of_a_real_id": arabic_indic,
            "fullwidth_digits_of_a_real_id": fullwidth,
            "superscript_digit": "²",
        }.items():
            with self.subTest(case=name):
                self.assert_rejected(dimension_type="PRODUCT", dimension_value=bad)
        self.assertEqual(models.MetricSnapshot.objects.count(), 0)

    def test_entity_dimension_in_the_same_business_is_stored_and_replayed(self):
        for dimension_type, entity in (
            ("PRODUCT", self.product), ("PRODUCT_VARIANT", self.variant),
            ("CAMPAIGN", self.campaign),
        ):
            with self.subTest(dimension_type=dimension_type):
                value = str(entity.pk)
                created = self.record(dimension_type=dimension_type, dimension_value=value)
                self.assertEqual(created.status, WRITE_CREATED)
                self.assertEqual(
                    (created.observation.dimension_type, created.observation.dimension_value),
                    (dimension_type, value))
                again = self.record(at=T2, dimension_type=dimension_type, dimension_value=value)
                self.assertEqual(again.status, WRITE_UNCHANGED)
                self.assertEqual(again.observation.snapshot_id, created.observation.snapshot_id)
        self.assertEqual(models.MetricSnapshot.objects.count(), 3)

    def test_entity_dimension_pointing_at_another_business_is_rejected_and_nothing_is_written(self):
        cases = {
            "product": ("PRODUCT", self.other_product),
            "variant_of_other_business_product": ("PRODUCT_VARIANT", self.other_variant),
            "campaign": ("CAMPAIGN", self.other_campaign),
        }
        for name, (dimension_type, entity) in cases.items():
            with self.subTest(case=name):
                metric_rows_before = self.metric_rows()
                self.assert_rejected(dimension_type=dimension_type, dimension_value=str(entity.pk))
                self.assertEqual(models.MetricSnapshot.objects.count(), 0)
                self.assertEqual(self.metric_rows(), metric_rows_before)

    def test_cross_business_guard_is_symmetric_and_also_blocks_unavailable_writes(self):
        before = self.rows()
        with self.assertRaises(MetricValidationError):
            self.record(business=self.other, dimension_type="PRODUCT",
                        dimension_value=str(self.product.pk))
        with self.assertRaises(MetricValidationError):
            self.record(value=UNAVAILABLE, dimension_type="CAMPAIGN",
                        dimension_value=str(self.other_campaign.pk))
        self.assertEqual(self.rows(), before)
        self.assertEqual(
            self.record(business=self.other, dimension_type="PRODUCT",
                        dimension_value=str(self.other_product.pk)).status,
            WRITE_CREATED)

    def test_nonexistent_entity_ids_are_rejected(self):
        missing = max(
            models.Product.objects.order_by("-pk").first().pk,
            models.ProductVariant.objects.order_by("-pk").first().pk,
            models.Campaign.objects.order_by("-pk").first().pk,
        ) + 1000
        for dimension_type in ("PRODUCT", "PRODUCT_VARIANT", "CAMPAIGN"):
            with self.subTest(dimension_type=dimension_type):
                self.assert_rejected(dimension_type=dimension_type, dimension_value=str(missing))

    def test_cross_business_entity_dimension_is_rejected_on_every_read(self):
        scope = dict(dimension_type="PRODUCT", dimension_value=str(self.other_product.pk))
        with self.assertRaises(MetricValidationError):
            get_metric_snapshot(
                business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                period_start=T0, period_end=T1, **scope)
        with self.assertRaises(MetricValidationError):
            list_metric_snapshots(business_id=self.business.pk, **scope)
        with self.assertRaises(MetricValidationError):
            compare_metric_periods(
                business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                current_period_start=T1, current_period_end=T2,
                previous_period_start=T0, previous_period_end=T1, **scope)

    def test_dimension_scope_is_part_of_the_logical_identity(self):
        wide = self.record(value=Decimal("100"))
        product = self.record(value=Decimal("40"), dimension_type="PRODUCT",
                              dimension_value=str(self.product.pk))
        region = self.record(value=Decimal("60"), dimension_type="REGION", dimension_value="Dhaka")
        courier = self.record(value=Decimal("5"), dimension_type="COURIER", dimension_value="Dhaka")
        self.assertEqual(
            len({r.observation.snapshot_id for r in (wide, product, region, courier)}), 4)
        self.assertEqual([r.status for r in (wide, product, region, courier)], [WRITE_CREATED] * 4)
        wide_read = get_metric_snapshot(
            business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
            period_start=T0, period_end=T1)
        self.assertEqual((wide_read.value, wide_read.dimension_type, wide_read.dimension_value),
                         (Decimal("100"), None, None))
        region_read = get_metric_snapshot(
            business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
            period_start=T0, period_end=T1, dimension_type="REGION", dimension_value="Dhaka")
        self.assertEqual(region_read.value, Decimal("60"))


# ==========================================================================
# §3 Decimal values
# ==========================================================================

class MetricValueTests(MetricTestCase):

    def test_only_decimals_are_accepted_as_values(self):
        cases = {
            "float": 1.5,
            "float_zero": 0.0,
            "int": 5,
            "int_zero": 0,
            "bool": True,
            "numeric_string": "1.5",
            "none": None,
            "nan": Decimal("NaN"),
            "signaling_nan": Decimal("sNaN"),
            "infinity": Decimal("Infinity"),
            "negative_infinity": Decimal("-Infinity"),
        }
        for name, value in cases.items():
            with self.subTest(case=name):
                self.assert_rejected(value=value)
        self.assertEqual(models.MetricSnapshot.objects.count(), 0)

    def test_none_is_not_the_unavailable_sentinel(self):
        self.assert_rejected(value=None)
        result = self.record(value=UNAVAILABLE)
        self.assertEqual(result.status, WRITE_NOT_RECORDED_UNAVAILABLE)

    def test_extra_precision_is_quantized_half_even_and_the_exact_input_is_preserved(self):
        cases = [
            ("1.2345675", "1.234568"),        # tie, previous digit odd -> up
            ("1.2345665", "1.234566"),        # tie, previous digit even -> stays
            ("1.23456650001", "1.234567"),    # above the tie -> up
            ("0.0000015", "0.000002"),
            ("0.0000025", "0.000002"),
            ("-0.0000035", "-0.000004"),
            ("0.0000005", "0.000000"),
            ("123.4567891", "123.456789"),
        ]
        for index, (given, stored) in enumerate(cases):
            with self.subTest(value=given):
                start, end = self.day(index)
                result = self.record(value=Decimal(given), period_start=start, period_end=end)
                self.assertEqual(result.status, WRITE_CREATED)
                self.assertEqual(result.observation.value, Decimal(stored))
                row = models.MetricSnapshot.objects.get(pk=result.observation.snapshot_id)
                self.assertEqual(row.value, Decimal(stored))
                self.assertEqual(Decimal(row.metadata["rounded_from"]), Decimal(given))
        # The caller's literal input is recorded verbatim for an ordinary decimal.
        first = models.MetricSnapshot.objects.order_by("pk").first()
        self.assertEqual(first.metadata["rounded_from"], "1.2345675")

    def test_values_the_column_can_hold_exactly_do_not_claim_rounding(self):
        for index, given in enumerate(["12.5", "12.500000", "1.2300000", "-0.000001", "7"]):
            with self.subTest(value=given):
                start, end = self.day(index)
                result = self.record(value=Decimal(given), period_start=start, period_end=end)
                row = models.MetricSnapshot.objects.get(pk=result.observation.snapshot_id)
                self.assertEqual(row.value, Decimal(given))
                self.assertNotIn("rounded_from", row.metadata)

    def test_negative_values_are_stored_as_signed_decimals(self):
        result = self.record(metric_key="bi.metric.sales_growth_rate.v1",
                             value=Decimal("-0.25"))
        row = models.MetricSnapshot.objects.get(pk=result.observation.snapshot_id)
        self.assertEqual(row.value, Decimal("-0.250000"))

    def test_magnitude_at_or_above_the_column_limit_is_rejected_not_truncated(self):
        cases = {
            "ten_to_the_eighteenth": Decimal(10) ** 18,
            "negative_ten_to_the_eighteenth": -(Decimal(10) ** 18),
            "rounds_up_to_the_limit": Decimal("999999999999999999.9999995"),
            "far_above": Decimal("1E+30"),
            "many_digits": Decimal("12345678901234567890"),
        }
        for name, value in cases.items():
            with self.subTest(case=name):
                self.assert_rejected(value=value)
        self.assertEqual(models.MetricSnapshot.objects.count(), 0)

    def test_largest_storable_magnitudes_are_accepted(self):
        # The result is checked in memory: SQLite keeps ~15 significant digits for
        # NUMERIC columns, so this boundary is a service decision, not a read-back.
        cases = [
            (Decimal("999999999999999999.999999"), Decimal("999999999999999999.999999")),
            (Decimal("-999999999999999999.999999"), Decimal("-999999999999999999.999999")),
            (Decimal("999999999999999999.9999994"), Decimal("999999999999999999.999999")),
        ]
        for index, (given, stored) in enumerate(cases):
            with self.subTest(value=given):
                start, end = self.day(index)
                result = self.record(value=given, period_start=start, period_end=end)
                self.assertEqual(result.status, WRITE_CREATED)
                self.assertEqual(result.observation.value, stored)
        self.assertEqual(models.MetricSnapshot.objects.count(), 3)

    def test_a_measured_zero_is_written_and_is_distinguishable_from_unavailable(self):
        zero_start, zero_end = self.day(0)
        gap_start, gap_end = self.day(1)
        written = self.record(value=Decimal("0"), period_start=zero_start, period_end=zero_end)
        self.assertEqual(written.status, WRITE_CREATED)
        self.assertEqual(written.observation.value, Decimal("0"))
        row = models.MetricSnapshot.objects.get()
        self.assertEqual(row.value, Decimal("0"))
        self.assertIs(row.metadata["data_available"], True)

        gap = self.record(value=UNAVAILABLE, period_start=gap_start, period_end=gap_end)
        self.assertEqual(gap.status, WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

        scope = dict(business_id=self.business.pk, metric_key=ORDERS, period_type="DAY")
        measured = get_metric_snapshot(**scope, period_start=zero_start, period_end=zero_end)
        missing = get_metric_snapshot(**scope, period_start=gap_start, period_end=gap_end)
        self.assertIsNotNone(measured)
        self.assertEqual(measured.value, Decimal("0"))
        self.assertIsNone(missing)

    def test_zero_is_a_real_previous_value_when_the_zero_is_later_revised(self):
        self.record(value=Decimal("0"))
        revised = self.record(at=T2, value=Decimal("5"))
        self.assertEqual(revised.status, WRITE_UPDATED)
        self.assertEqual(revised.previous_value, Decimal("0"))
        self.assertIsNotNone(revised.previous_value)
        self.assertEqual(revised.observation.revision, 2)

    def test_replaying_a_zero_is_unchanged_not_unavailable(self):
        first = self.record(value=Decimal("0"))
        again = self.record(at=T2, value=Decimal("0.000"))
        self.assertEqual(again.status, WRITE_UNCHANGED)
        self.assertEqual(again.observation.snapshot_id, first.observation.snapshot_id)
        self.assertEqual(again.observation.value, Decimal("0"))

    def test_calculation_inputs_are_json_safe_float_free_and_order_independent(self):
        first = self.record(inputs={"orders": 3, "net": Decimal("1.50"), "nested": {"b": [1, 2], "a": "x"}})
        row = models.MetricSnapshot.objects.get()
        self.assertEqual(
            row.metadata["inputs"],
            {"nested": {"a": "x", "b": [1, 2]}, "net": "1.50", "orders": 3},
        )
        reordered = self.record(at=T2, inputs={"nested": {"a": "x", "b": [1, 2]}, "orders": 3, "net": Decimal("1.50")})
        self.assertEqual(reordered.status, WRITE_UNCHANGED)
        self.assertEqual(reordered.observation.snapshot_id, first.observation.snapshot_id)
        for name, bad in {
            "float": {"rate": 0.5},
            "nested_float": {"a": [{"b": 1.5}]},
            "non_finite_decimal": {"a": Decimal("NaN")},
            "not_a_mapping": [1, 2],
            "empty_key": {"": 1},
            "non_string_key": {1: "a"},
            "arbitrary_object": {"a": object()},
        }.items():
            with self.subTest(case=name):
                self.assert_rejected(at=T2, inputs=bad)

    def test_empty_inputs_leave_no_inputs_marker(self):
        self.record(inputs={})
        self.assertNotIn("inputs", models.MetricSnapshot.objects.get().metadata)

    def test_calculation_rule_is_the_metric_key_or_a_documented_variant(self):
        default = self.record()
        self.assertEqual(default.observation.calculation_rule, ORDERS)
        self.assertEqual(models.MetricSnapshot.objects.get().calculation_rule, ORDERS)
        variant = self.record(at=T2, calculation_rule=f"{ORDERS}.paid_orders")
        self.assertEqual(variant.status, WRITE_UPDATED)
        self.assertEqual(variant.observation.calculation_rule, f"{ORDERS}.paid_orders")
        for name, bad in {
            "other_metric": UNITS_SOLD,
            "other_metric_variant": f"{UNITS_SOLD}.paid",
            "free_text": "count the paid orders",
            "empty": "",
            "trailing_dot": f"{ORDERS}.",
            "uppercase_variant": f"{ORDERS}.PAID",
            "variant_with_dash": f"{ORDERS}.paid-orders",
            "too_long": f"{ORDERS}." + "a" * 100,
            "integer": 5,
        }.items():
            with self.subTest(case=name):
                self.assert_rejected(at=T3, calculation_rule=bad)


# ==========================================================================
# §3 Unavailable data
# ==========================================================================

class MetricUnavailableTests(MetricTestCase):

    def test_unavailable_with_no_prior_observation_writes_nothing(self):
        result = self.record(value=UNAVAILABLE)
        self.assertEqual(
            result,
            SnapshotWriteResult(
                status=WRITE_NOT_RECORDED_UNAVAILABLE, observation=None,
                previous_value=None, existing_snapshot_id=None),
        )
        self.assertIn(result.status, WRITE_STATUSES)
        self.assertEqual(models.MetricSnapshot.objects.count(), 0)

    def test_unavailable_with_a_prior_observation_neither_deletes_nor_rewrites_it(self):
        created = self.record(value=Decimal("10"))
        before = self.rows()
        result = self.record(at=T3, value=UNAVAILABLE)
        self.assertEqual(result.status, WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertIsNone(result.observation)
        self.assertEqual(result.existing_snapshot_id, created.observation.snapshot_id)
        self.assertEqual(result.previous_value, Decimal("10"))
        self.assertEqual(self.rows(), before)
        survivor = get_metric_snapshot(
            business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
            period_start=T0, period_end=T1)
        self.assertEqual(survivor, created.observation)

    def test_unavailable_after_a_measured_zero_keeps_the_zero(self):
        created = self.record(value=Decimal("0"))
        result = self.record(at=T3, value=UNAVAILABLE)
        self.assertEqual(result.existing_snapshot_id, created.observation.snapshot_id)
        self.assertEqual(result.previous_value, Decimal("0"))
        self.assertEqual(models.MetricSnapshot.objects.get().value, Decimal("0"))

    def test_unavailable_only_matches_its_own_scope(self):
        self.record(value=Decimal("10"))
        for name, overrides in {
            "next_period": dict(period_start=T1, period_end=T2),
            "other_dimension": dict(dimension_type="REGION", dimension_value="Dhaka"),
            "other_period_type": dict(period_type="CUSTOM"),
            "other_metric": dict(metric_key=UNITS_SOLD),
        }.items():
            with self.subTest(case=name):
                result = self.record(at=T3, value=UNAVAILABLE, **overrides)
                self.assertIsNone(result.existing_snapshot_id)
                self.assertIsNone(result.previous_value)
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

    def test_unavailable_runs_still_validate_their_scope(self):
        self.assert_rejected(value=UNAVAILABLE, period_start=T1, period_end=T1)
        self.assert_rejected(value=UNAVAILABLE, period_start=datetime(2026, 10, 1))
        self.assert_rejected(value=UNAVAILABLE, dimension_type="REGION")
        self.assert_rejected(value=UNAVAILABLE, metric_key="bi.metric.nope.v1")

    def test_reads_of_unavailable_data_return_none_or_empty_never_a_zero(self):
        self.record(value=UNAVAILABLE)
        scope = dict(business_id=self.business.pk, metric_key=ORDERS, period_type="DAY")
        self.assertIsNone(get_metric_snapshot(**scope, period_start=T0, period_end=T1))
        self.assertEqual(list_metric_snapshots(business_id=self.business.pk), ())
        self.assertEqual(list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS), ())
        self.assertIsNone(get_metric_observation(business_id=self.business.pk, snapshot_id=1))

    def test_reading_an_unsynced_metric_raises_but_a_registered_metric_without_data_returns_none(self):
        # "Not registered / not synced" (a caller error) must never look like
        # "registered, nothing recorded" (a legitimate absence of data).
        fresh = self.make(models.Business, name="Fresh", slug="fresh", business=None)
        scope = dict(metric_key=ORDERS, period_type="DAY")
        with self.assertRaises(MetricValidationError):
            get_metric_snapshot(
                business_id=fresh.pk, period_start=T0, period_end=T1, **scope)
        with self.assertRaises(MetricValidationError):
            list_metric_snapshots(business_id=fresh.pk, metric_key=ORDERS)
        with self.assertRaises(MetricValidationError):
            compare_metric_periods(
                business_id=fresh.pk, current_period_start=T1, current_period_end=T2,
                previous_period_start=T0, previous_period_end=T1, **scope)
        # A business-wide list with no metric_key names no metric, so it is simply empty.
        self.assertEqual(list_metric_snapshots(business_id=fresh.pk), ())
        # The same reads on a synchronized business with no observation are not errors.
        self.assertIsNone(get_metric_snapshot(
            business_id=self.business.pk, period_start=T0, period_end=T1, **scope))
        self.assertEqual(
            list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS), ())
        comparison = compare_metric_periods(
            business_id=self.business.pk, current_period_start=T1, current_period_end=T2,
            previous_period_start=T0, previous_period_end=T1, **scope)
        self.assertEqual(comparison.direction, DIRECTION_UNAVAILABLE)
        self.assertEqual(self.rows(), [])

    def test_reading_a_metric_the_registry_does_not_define_raises(self):
        for key in ("bi.metric.nope.v1", ORDERS.replace(".v1", ".v2"), "sales_total_orders"):
            with self.subTest(metric_key=key):
                with self.assertRaises(MetricValidationError):
                    get_metric_snapshot(
                        business_id=self.business.pk, metric_key=key, period_type="DAY",
                        period_start=T0, period_end=T1)
                with self.assertRaises(MetricValidationError):
                    list_metric_snapshots(business_id=self.business.pk, metric_key=key)
                with self.assertRaises(MetricValidationError):
                    compare_metric_periods(
                        business_id=self.business.pk, metric_key=key, period_type="DAY",
                        current_period_start=T1, current_period_end=T2,
                        previous_period_start=T0, previous_period_end=T1)

    def test_reads_for_an_unknown_business_are_rejected(self):
        with self.assertRaises(MetricValidationError):
            get_metric_snapshot(
                business_id=987654, metric_key=ORDERS, period_type="DAY",
                period_start=T0, period_end=T1)
        with self.assertRaises(MetricValidationError):
            list_metric_snapshots(business_id=987654)
        with self.assertRaises(MetricValidationError):
            get_metric_observation(business_id=987654, snapshot_id=1)


# ==========================================================================
# §3 Reproducible analysis: idempotency and revision
# ==========================================================================

class MetricReplayAndRevisionTests(MetricTestCase):

    def test_first_write_creates_one_fully_described_row(self):
        result = self.record(at=T1, value=Decimal("10"))
        row = models.MetricSnapshot.objects.get()
        self.assertEqual(result.status, WRITE_CREATED)
        self.assertIsNone(result.previous_value)
        self.assertIsNone(result.existing_snapshot_id)
        self.assertEqual(
            result.observation,
            MetricObservation(
                snapshot_id=row.pk, business_id=self.business.pk, metric_key=ORDERS,
                value=Decimal("10"), value_type="COUNT", unit="ORDERS", period_type="DAY",
                period_start=T0, period_end=T1, dimension_type=None, dimension_value=None,
                calculation_rule=ORDERS, revision=1, calculated_at=T1),
        )
        self.assertEqual(
            (row.metric_id, row.business_id, row.value, row.dimension_type,
             row.dimension_value, row.period_type, row.period_start, row.period_end,
             row.calculation_rule, row.calculated_at, row.created_at),
            (self.metric_row().pk, self.business.pk, Decimal("10"), None, None,
             "DAY", T0, T1, ORDERS, T1, T1),
        )
        self.assertEqual(row.metadata, {
            "service": OWNER, "metric_key": ORDERS, "calculation_rule": ORDERS,
            "value_type": "COUNT", "unit": "ORDERS", "data_available": True, "revision": 1,
        })

    def test_identical_replay_is_unchanged_and_preserves_id_and_every_timestamp(self):
        first = self.record(at=T1)
        before = self.rows()
        again = self.record(at=T3)
        self.assertEqual(again.status, WRITE_UNCHANGED)
        self.assertEqual(again.observation, first.observation)
        self.assertEqual(again.observation.snapshot_id, first.observation.snapshot_id)
        self.assertEqual(again.existing_snapshot_id, first.observation.snapshot_id)
        self.assertIsNone(again.previous_value)
        self.assertEqual(again.observation.calculated_at, T1)
        self.assertEqual(self.rows(), before)
        self.assertEqual(before[0]["calculated_at"], T1)
        self.assertEqual(before[0]["created_at"], T1)
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

    def test_many_replays_never_append_a_second_row(self):
        first = self.record(at=T1)
        for hour in range(1, 6):
            with self.subTest(replay=hour):
                result = self.record(at=T1 + timedelta(hours=hour))
                self.assertEqual(result.status, WRITE_UNCHANGED)
                self.assertEqual(result.observation.snapshot_id, first.observation.snapshot_id)
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

    def test_replay_with_the_same_number_written_at_another_scale_is_unchanged(self):
        self.record(value=Decimal("10"))
        again = self.record(at=T2, value=Decimal("10.0000000"))
        self.assertEqual(again.status, WRITE_UNCHANGED)
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

    def test_changed_value_updates_the_same_row_and_keeps_the_superseded_value(self):
        first = self.record(at=T1, value=Decimal("10"))
        result = self.record(at=T2, value=Decimal("12"))
        self.assertEqual(result.status, WRITE_UPDATED)
        self.assertEqual(result.observation.snapshot_id, first.observation.snapshot_id)
        self.assertEqual(result.existing_snapshot_id, first.observation.snapshot_id)
        self.assertEqual(result.previous_value, Decimal("10"))
        self.assertEqual((result.observation.value, result.observation.revision,
                          result.observation.calculated_at), (Decimal("12"), 2, T2))
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)
        row = models.MetricSnapshot.objects.get()
        self.assertEqual((row.value, row.created_at, row.calculated_at), (Decimal("12"), T1, T2))
        self.assertEqual(row.metadata["revision"], 2)
        self.assertEqual(row.metadata["supersedes"], {
            "revision": 1, "value": "10.000000", "calculation_rule": ORDERS,
            "calculated_at": T1.isoformat(),
        })
        self.assertEqual(row.metadata["service"], OWNER)
        self.assertIs(row.metadata["data_available"], True)

    def test_only_the_immediately_previous_observation_is_retained_while_revision_counts_up(self):
        self.record(at=T1, value=Decimal("10"))
        self.record(at=T2, value=Decimal("12"))
        third = self.record(at=T3, value=Decimal("15"))
        self.assertEqual(third.status, WRITE_UPDATED)
        self.assertEqual(third.previous_value, Decimal("12"))
        row = models.MetricSnapshot.objects.get()
        self.assertEqual(row.metadata["revision"], 3)
        self.assertEqual(row.metadata["supersedes"], {
            "revision": 2, "value": "12.000000", "calculation_rule": ORDERS,
            "calculated_at": T2.isoformat(),
        })
        # Going back to a value held earlier is still a revision, never a no-op.
        fourth = self.record(at=T4, value=Decimal("10"))
        self.assertEqual(fourth.status, WRITE_UPDATED)
        row.refresh_from_db()
        self.assertEqual(row.metadata["revision"], 4)
        self.assertEqual(row.metadata["supersedes"]["value"], "15.000000")
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

    def test_a_replay_after_a_revision_is_unchanged_and_keeps_the_revision(self):
        self.record(at=T1, value=Decimal("10"))
        self.record(at=T2, value=Decimal("12"))
        before = self.rows()
        again = self.record(at=T4, value=Decimal("12"))
        self.assertEqual(again.status, WRITE_UNCHANGED)
        self.assertEqual(again.observation.revision, 2)
        self.assertEqual(again.observation.calculated_at, T2)
        self.assertEqual(self.rows(), before)

    def test_changed_calculation_rule_or_inputs_with_the_same_value_is_a_traceable_revision(self):
        self.record(at=T1, value=Decimal("10"), inputs={"orders": 10})
        by_rule = self.record(at=T2, value=Decimal("10"), inputs={"orders": 10},
                              calculation_rule=f"{ORDERS}.paid_orders")
        self.assertEqual(by_rule.status, WRITE_UPDATED)
        self.assertEqual(by_rule.previous_value, Decimal("10"))
        row = models.MetricSnapshot.objects.get()
        self.assertEqual(row.calculation_rule, f"{ORDERS}.paid_orders")
        self.assertEqual(row.metadata["supersedes"]["calculation_rule"], ORDERS)
        by_inputs = self.record(at=T3, value=Decimal("10"), inputs={"orders": 11},
                                calculation_rule=f"{ORDERS}.paid_orders")
        self.assertEqual(by_inputs.status, WRITE_UPDATED)
        row.refresh_from_db()
        self.assertEqual((row.metadata["revision"], row.metadata["inputs"]), (3, {"orders": 11}))
        self.assertEqual(models.MetricSnapshot.objects.count(), 1)

    def test_every_identity_component_creates_a_separate_row_when_it_differs(self):
        product = self.make(models.Product)
        self.record()
        variations = {
            "metric": dict(metric_key=UNITS_SOLD),
            "dimension_type": dict(dimension_type="CHANNEL", dimension_value="web"),
            "dimension_value": dict(dimension_type="CHANNEL", dimension_value="chat"),
            "entity_dimension": dict(dimension_type="PRODUCT", dimension_value=str(product.pk)),
            "period_type": dict(period_type="CUSTOM"),
            "period_start": dict(period_start=T0 - timedelta(hours=1)),
            "period_end": dict(period_end=T2),
        }
        expected_rows = 1
        for name, overrides in variations.items():
            with self.subTest(component=name):
                result = self.record(**overrides)
                expected_rows += 1
                self.assertEqual(result.status, WRITE_CREATED)
                self.assertEqual(models.MetricSnapshot.objects.count(), expected_rows)
        self.assertEqual(expected_rows, 8)

    def test_the_same_scope_in_two_businesses_is_two_independent_observations(self):
        mine = self.record(value=Decimal("10"))
        theirs = self.record(business=self.other, value=Decimal("99"))
        self.assertEqual((mine.status, theirs.status), (WRITE_CREATED, WRITE_CREATED))
        self.assertNotEqual(mine.observation.snapshot_id, theirs.observation.snapshot_id)
        self.assertEqual(theirs.observation.business_id, self.other.pk)
        before_other = list(models.MetricSnapshot.objects.filter(business=self.other).values())
        self.assertEqual(self.record(at=T2, value=Decimal("11")).status, WRITE_UPDATED)
        self.assertEqual(
            list(models.MetricSnapshot.objects.filter(business=self.other).values()),
            before_other)
        self.assertEqual(
            models.MetricSnapshot.objects.get(business=self.other).metric_id,
            self.metric_row(business=self.other).pk)
        self.assertEqual(models.MetricSnapshot.objects.count(), 2)

    def test_two_rows_sharing_one_logical_identity_raise_a_conflict_and_nothing_changes(self):
        first = self.record()
        original = models.MetricSnapshot.objects.get(pk=first.observation.snapshot_id)
        duplicate = self.raw_snapshot(metadata=dict(original.metadata), value=Decimal("77"))
        before = self.rows()
        self.assertEqual(len(before), 2)
        for name, value in {"same_value": Decimal("10"), "other_value": Decimal("55")}.items():
            with self.subTest(case=name):
                with self.assertRaises(MetricSnapshotConflictError):
                    self.record(at=T3, value=value)
        with self.assertRaises(MetricSnapshotConflictError):
            self.record(at=T3, value=UNAVAILABLE)
        with self.assertRaises(MetricSnapshotConflictError):
            get_metric_snapshot(
                business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                period_start=T0, period_end=T1)
        with self.assertRaises(MetricSnapshotConflictError):
            compare_metric_periods(
                business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                current_period_start=T0, current_period_end=T1,
                previous_period_start=T0 - timedelta(days=1), previous_period_end=T0)
        self.assertEqual(self.rows(), before)
        self.assertEqual(
            [row["id"] for row in before], [original.pk, duplicate.pk])

    def test_a_row_without_this_services_marker_raises_a_conflict_and_is_never_overwritten(self):
        markers = {
            "no_metadata": None,
            "empty_metadata": {},
            "other_service": {"service": "someone.else"},
            "marker_in_wrong_key": {"owner": OWNER},
            "list_metadata": [],
        }
        for name, metadata in markers.items():
            with self.subTest(case=name):
                models.MetricSnapshot.objects.all().delete()
                foreign = self.raw_snapshot(metadata=metadata, value=Decimal("3"))
                before = self.rows()
                with self.assertRaises(MetricSnapshotConflictError):
                    self.record(value=Decimal("10"))
                with self.assertRaises(MetricSnapshotConflictError):
                    self.record(value=Decimal("3"))
                with self.assertRaises(MetricSnapshotConflictError):
                    get_metric_snapshot(
                        business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                        period_start=T0, period_end=T1)
                with self.assertRaises(MetricSnapshotConflictError):
                    get_metric_observation(
                        business_id=self.business.pk, snapshot_id=foreign.pk)
                self.assertEqual(self.rows(), before)
                self.assertEqual(
                    list_metric_snapshots(business_id=self.business.pk), ())

    def test_a_foreign_row_does_not_block_other_scopes(self):
        self.raw_snapshot(metadata=None)
        result = self.record(period_start=T1, period_end=T2)
        self.assertEqual(result.status, WRITE_CREATED)
        self.assertEqual(models.MetricSnapshot.objects.count(), 2)


# ==========================================================================
# §3 Reads
# ==========================================================================

class MetricReadTests(MetricTestCase):

    def test_get_snapshot_returns_the_exact_observation_written(self):
        created = self.record(value=Decimal("12.5"), dimension_type="REGION",
                              dimension_value="Dhaka")
        read = get_metric_snapshot(
            business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
            period_start=T0, period_end=T1, dimension_type="REGION", dimension_value="Dhaka")
        self.assertEqual(read, created.observation)
        self.assertEqual(read.value, Decimal("12.5"))
        for name, params in {
            "other_period_type": dict(period_type="WEEK"),
            "other_dimension": dict(dimension_value="Sylhet"),
            "no_dimension": dict(dimension_type=None, dimension_value=None),
            "other_end": dict(period_end=T2),
            "other_metric": dict(metric_key=UNITS_SOLD),
        }.items():
            with self.subTest(case=name):
                scope = dict(
                    business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                    period_start=T0, period_end=T1, dimension_type="REGION",
                    dimension_value="Dhaka")
                scope.update(params)
                self.assertIsNone(get_metric_snapshot(**scope))

    def test_get_observation_resolves_the_exact_cited_observation_including_revisions(self):
        created = self.record(at=T1, value=Decimal("10"))
        cited = get_metric_observation(
            business_id=self.business.pk, snapshot_id=created.observation.snapshot_id)
        self.assertEqual(cited, created.observation)
        self.assertEqual((cited.revision, cited.calculated_at), (1, T1))
        self.record(at=T2, value=Decimal("12"))
        revised = get_metric_observation(
            business_id=self.business.pk, snapshot_id=created.observation.snapshot_id)
        self.assertEqual((revised.value, revised.revision, revised.calculated_at),
                         (Decimal("12"), 2, T2))
        self.assertEqual(revised.snapshot_id, cited.snapshot_id)

    def test_get_observation_never_returns_another_businesses_snapshot(self):
        mine = self.record(value=Decimal("10"))
        theirs = self.record(business=self.other, value=Decimal("99"))
        self.assertIsNone(get_metric_observation(
            business_id=self.business.pk, snapshot_id=theirs.observation.snapshot_id))
        self.assertIsNone(get_metric_observation(
            business_id=self.other.pk, snapshot_id=mine.observation.snapshot_id))
        self.assertEqual(
            get_metric_observation(
                business_id=self.other.pk, snapshot_id=theirs.observation.snapshot_id).value,
            Decimal("99"))
        self.assertIsNone(get_metric_observation(
            business_id=self.business.pk, snapshot_id=987654))

    def test_get_observation_rejects_malformed_ids(self):
        for bad in (0, -1, True, "1", None, 1.0):
            with self.subTest(snapshot_id=bad):
                with self.assertRaises(MetricValidationError):
                    get_metric_observation(business_id=self.business.pk, snapshot_id=bad)
            with self.subTest(business_id=bad):
                with self.assertRaises(MetricValidationError):
                    get_metric_observation(business_id=bad, snapshot_id=1)

    def test_snapshot_whose_metric_belongs_to_another_business_is_a_conflict_not_a_leak(self):
        foreign_metric = self.metric_row(business=self.other)
        broken = self.raw_snapshot(
            metadata={"service": OWNER, "revision": 1}, metric=foreign_metric)
        with self.assertRaises(MetricSnapshotConflictError):
            get_metric_observation(business_id=self.business.pk, snapshot_id=broken.pk)
        self.assertEqual(list_metric_snapshots(business_id=self.business.pk), ())
        self.assertEqual(list_metric_snapshots(business_id=self.other.pk), ())

    def _seed_history(self):
        """Five daily rows recorded out of order, plus another business's rows."""
        written = {}
        for index in (3, 0, 4, 1, 2):
            start, end = self.day(index)
            written[index] = self.record(
                value=Decimal(index + 1), period_start=start, period_end=end,
            ).observation.snapshot_id
        for index in range(5):
            start, end = self.day(index)
            self.record(business=self.other, value=Decimal(100 + index),
                        period_start=start, period_end=end)
        return written

    def test_list_returns_the_scope_in_chronological_order_and_never_another_business(self):
        written = self._seed_history()
        listed = list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS)
        self.assertIsInstance(listed, tuple)
        self.assertEqual([o.period_start for o in listed], [T0, T1, T2, T3, T4])
        self.assertEqual([o.value for o in listed], [Decimal(n) for n in (1, 2, 3, 4, 5)])
        self.assertEqual([o.snapshot_id for o in listed], [written[i] for i in range(5)])
        self.assertEqual({o.business_id for o in listed}, {self.business.pk})
        theirs = list_metric_snapshots(business_id=self.other.pk, metric_key=ORDERS)
        self.assertEqual([o.value for o in theirs], [Decimal(100 + i) for i in range(5)])
        self.assertEqual(
            {o.snapshot_id for o in listed} & {o.snapshot_id for o in theirs}, set())

    def test_list_window_is_half_open_on_period_start(self):
        self._seed_history()
        cases = {
            "start_inclusive_end_exclusive": ((T1, T3), [T1, T2]),
            "end_equal_to_a_start_excludes_it": ((T0, T4), [T0, T1, T2, T3]),
            "start_only": ((T3, None), [T3, T4]),
            "end_only": ((None, T2), [T0, T1]),
            "window_between_starts": ((T1 + timedelta(hours=1), T3 + timedelta(hours=1)), [T2, T3]),
            "start_after_everything": ((T4 + timedelta(seconds=1), None), []),
            "end_at_first_start": ((None, T0), []),
        }
        for name, ((start, end), expected) in cases.items():
            with self.subTest(case=name):
                listed = list_metric_snapshots(
                    business_id=self.business.pk, metric_key=ORDERS,
                    window_start=start, window_end=end)
                self.assertEqual([o.period_start for o in listed], expected)

    def test_list_ordering_is_period_start_then_period_end_then_snapshot_id(self):
        a = self.record(period_type="DAY", period_start=T2, period_end=T3)
        b = self.record(period_type="DAY", period_start=T0, period_end=T1)
        c = self.record(period_type="CUSTOM", period_start=T1, period_end=T3)
        d = self.record(period_type="DAY", period_start=T1, period_end=T2)
        e = self.record(period_type="CUSTOM", period_start=T1, period_end=T2)
        f = self.record(period_type="WEEK", period_start=T1, period_end=T2)
        listed = list_metric_snapshots(business_id=self.business.pk)
        self.assertEqual(
            [o.snapshot_id for o in listed],
            [r.observation.snapshot_id for r in (b, d, e, f, c, a)],
        )
        self.assertEqual(listed, list_metric_snapshots(business_id=self.business.pk))

    def test_list_filters_by_metric_period_type_dimension_and_exact_rule(self):
        self.record(value=Decimal("1"))
        self.record(value=Decimal("2"), metric_key=UNITS_SOLD)
        self.record(value=Decimal("3"), period_type="WEEK")
        self.record(value=Decimal("4"), dimension_type="REGION", dimension_value="Dhaka")
        self.record(value=Decimal("5"), dimension_type="REGION", dimension_value="Sylhet")
        self.record(value=Decimal("6"), period_start=T1, period_end=T2,
                    calculation_rule=f"{ORDERS}.paid_orders")
        def values(**filters):
            return sorted(
                o.value for o in list_metric_snapshots(business_id=self.business.pk, **filters))
        # No dimension given means the business-wide series only (rows 4 and 5 are
        # dimensioned); every scope is read only when explicitly requested.
        self.assertEqual(values(), [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("6")])
        self.assertEqual(values(any_dimension=True), [Decimal(n) for n in range(1, 7)])
        self.assertEqual(values(metric_key=UNITS_SOLD), [Decimal("2")])
        self.assertEqual(values(metric_key=ORDERS, period_type="WEEK"), [Decimal("3")])
        self.assertEqual(
            values(metric_key=ORDERS, dimension_type="REGION", dimension_value="Dhaka"),
            [Decimal("4")])
        self.assertEqual(
            values(dimension_type="REGION", dimension_value="Sylhet"), [Decimal("5")])
        self.assertEqual(values(dimension_type="REGION", dimension_value="dhaka"), [])
        self.assertEqual(values(calculation_rule=f"{ORDERS}.paid_orders"), [Decimal("6")])
        self.assertEqual(values(calculation_rule=ORDERS), [Decimal("1"), Decimal("3")])
        self.assertEqual(
            values(calculation_rule=ORDERS, any_dimension=True),
            [Decimal("1"), Decimal("3"), Decimal("4"), Decimal("5")])
        self.assertEqual(values(calculation_rule=f"{ORDERS}.paid"), [])

    def test_unfiltered_list_is_the_business_wide_series_never_interleaved_with_dimensions(self):
        product = self.make(models.Product)
        campaign = self.make(models.Campaign)
        wide = {}
        for index in range(3):
            start, end = self.day(index)
            wide[index] = self.record(
                value=Decimal(10 + index), period_start=start, period_end=end,
            ).observation.snapshot_id
        # Dimensioned rows share the very same periods as the business-wide rows.
        scoped = {}
        for index in range(3):
            start, end = self.day(index)
            for dimension_type, dimension_value in (
                ("PRODUCT", str(product.pk)), ("CAMPAIGN", str(campaign.pk)),
                ("REGION", "Dhaka"),
            ):
                scoped[(index, dimension_type)] = self.record(
                    value=Decimal(500 + index), period_start=start, period_end=end,
                    dimension_type=dimension_type, dimension_value=dimension_value,
                ).observation.snapshot_id
        self.assertEqual(models.MetricSnapshot.objects.count(), 12)

        default = list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS)
        self.assertEqual([o.snapshot_id for o in default], [wide[i] for i in range(3)])
        self.assertEqual([o.value for o in default], [Decimal(10), Decimal(11), Decimal(12)])
        self.assertEqual({(o.dimension_type, o.dimension_value) for o in default}, {(None, None)})
        # The default read is also what an unscoped metric-less read returns.
        self.assertEqual(
            [o.snapshot_id for o in list_metric_snapshots(business_id=self.business.pk)],
            [wide[i] for i in range(3)])
        self.assertEqual(
            [o.snapshot_id for o in list_metric_snapshots(
                business_id=self.business.pk, metric_key=ORDERS, any_dimension=False)],
            [wide[i] for i in range(3)])

    def test_any_dimension_reads_every_scope_in_period_then_snapshot_id_order(self):
        product = self.make(models.Product)
        ids = []
        for index in (1, 0):
            start, end = self.day(index)
            ids.append((index, "wide", self.record(
                value=Decimal(index), period_start=start, period_end=end,
            ).observation.snapshot_id))
            ids.append((index, "product", self.record(
                value=Decimal(100 + index), period_start=start, period_end=end,
                dimension_type="PRODUCT", dimension_value=str(product.pk),
            ).observation.snapshot_id))
            ids.append((index, "region", self.record(
                value=Decimal(200 + index), period_start=start, period_end=end,
                dimension_type="REGION", dimension_value="Dhaka",
            ).observation.snapshot_id))
        expected = [snapshot_id for _, _, snapshot_id in sorted(ids, key=lambda r: (r[0], r[2]))]
        listed = list_metric_snapshots(
            business_id=self.business.pk, metric_key=ORDERS, any_dimension=True)
        self.assertEqual([o.snapshot_id for o in listed], expected)
        self.assertEqual(
            [(o.period_start, o.dimension_type) for o in listed],
            [(T0, None), (T0, "PRODUCT"), (T0, "REGION"),
             (T1, None), (T1, "PRODUCT"), (T1, "REGION")])
        self.assertEqual(
            list_metric_snapshots(
                business_id=self.business.pk, metric_key=ORDERS, any_dimension=True, limit=4),
            listed[:4])
        # Another business's rows never join an any_dimension read.
        self.record(business=self.other, value=Decimal("999"))
        again = list_metric_snapshots(
            business_id=self.business.pk, metric_key=ORDERS, any_dimension=True)
        self.assertEqual(again, listed)

    def test_any_dimension_cannot_be_combined_with_an_explicit_dimension(self):
        product = self.make(models.Product)
        self.record(dimension_type="REGION", dimension_value="Dhaka")
        before = self.rows()
        for name, params in {
            "label_dimension": dict(dimension_type="REGION", dimension_value="Dhaka"),
            "entity_dimension": dict(dimension_type="PRODUCT", dimension_value=str(product.pk)),
        }.items():
            with self.subTest(case=name):
                with self.assertRaises(MetricValidationError):
                    list_metric_snapshots(
                        business_id=self.business.pk, metric_key=ORDERS,
                        any_dimension=True, **params)
        for bad in ("yes", 1, None):
            with self.subTest(any_dimension=bad):
                with self.assertRaises(MetricValidationError):
                    list_metric_snapshots(business_id=self.business.pk, any_dimension=bad)
        self.assertEqual(self.rows(), before)
        # An explicit dimension without the flag is still the normal scoped read.
        scoped = list_metric_snapshots(
            business_id=self.business.pk, metric_key=ORDERS,
            dimension_type="REGION", dimension_value="Dhaka")
        self.assertEqual([o.dimension_value for o in scoped], ["Dhaka"])

    def test_limit_is_applied_after_the_ownership_filter(self):
        first = self.record(period_start=T0, period_end=T1)
        # Foreign-writer rows sit between the owned ones in the very same window.
        self.raw_snapshot(metadata=None, start=T1, end=T2)
        self.raw_snapshot(metadata={"service": "someone.else"}, start=T2, end=T3)
        third = self.record(period_start=T3, period_end=T4)
        fourth = self.record(period_start=T4, period_end=T4 + timedelta(days=1))
        listed = list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS, limit=2)
        self.assertEqual(
            [o.snapshot_id for o in listed],
            [first.observation.snapshot_id, third.observation.snapshot_id])
        everything = list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS)
        self.assertEqual(
            [o.snapshot_id for o in everything],
            [first.observation.snapshot_id, third.observation.snapshot_id,
             fourth.observation.snapshot_id])
        self.assertEqual(
            len(list_metric_snapshots(business_id=self.business.pk, limit=3)), 3)

    def test_list_limit_keeps_the_earliest_rows_in_order(self):
        written = self._seed_history()
        listed = list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS, limit=2)
        self.assertEqual([o.snapshot_id for o in listed], [written[0], written[1]])
        everything = list_metric_snapshots(business_id=self.business.pk, limit=50)
        self.assertEqual(len(everything), 5)

    def test_list_rejects_invalid_filters(self):
        base = dict(business_id=self.business.pk)
        bad_filters = {
            "metric_key": dict(metric_key="sales_total_orders"),
            "period_type": dict(period_type="YEAR"),
            "dimension_type_only": dict(dimension_type="REGION"),
            "dimension_value_only": dict(dimension_value="Dhaka"),
            "unknown_dimension": dict(dimension_type="WAREHOUSE", dimension_value="a"),
            "naive_window": dict(window_start=datetime(2026, 10, 1)),
            "empty_rule": dict(calculation_rule=""),
            "long_rule": dict(calculation_rule="x" * 101),
            "string_include_inactive": dict(include_inactive_metrics="yes"),
            "zero_limit": dict(limit=0),
            "negative_limit": dict(limit=-3),
            "bool_limit": dict(limit=True),
        }
        for name, params in bad_filters.items():
            with self.subTest(case=name):
                with self.assertRaises(MetricValidationError):
                    list_metric_snapshots(**base, **params)
        for bad in (0, -1, True, "1", None):
            with self.subTest(business_id=bad):
                with self.assertRaises(MetricValidationError):
                    list_metric_snapshots(business_id=bad)

    def test_list_hides_rows_the_service_does_not_own(self):
        owned = self.record(period_start=T0, period_end=T1)
        self.raw_snapshot(metadata=None, start=T1, end=T2)
        self.raw_snapshot(metadata={"service": "someone.else"}, start=T2, end=T3)
        listed = list_metric_snapshots(business_id=self.business.pk)
        self.assertEqual([o.snapshot_id for o in listed], [owned.observation.snapshot_id])

    def test_list_for_a_scope_with_no_observations_is_an_empty_tuple(self):
        self.record(business=self.other)
        listed = list_metric_snapshots(business_id=self.business.pk, metric_key=ORDERS)
        self.assertEqual(listed, ())
        self.assertIsInstance(listed, tuple)


# ==========================================================================
# §3 Historical comparison
# ==========================================================================

class MetricComparisonTests(MetricTestCase):

    def put(self, previous=None, current=None, **overrides):
        if previous is not None:
            self.record(value=previous, period_start=T0, period_end=T1, **overrides)
        if current is not None:
            self.record(value=current, period_start=T1, period_end=T2, **overrides)

    def compare(self, **overrides):
        params = dict(
            business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
            current_period_start=T1, current_period_end=T2,
            previous_period_start=T0, previous_period_end=T1,
        )
        params.update(overrides)
        return compare_metric_periods(**params)

    def test_comparison_exposes_no_derived_relative_change(self):
        # Section 3 "Historical Comparison" is direction plus absolute change; a
        # percentage growth is the registered growth-rate metric's job, so the
        # comparison result must not carry a second answer for it.
        self.put(previous=Decimal("10"), current=Decimal("15"))
        result = self.compare()
        self.assertEqual(
            {field.name for field in dataclasses.fields(MetricComparison)},
            {"metric_key", "period_type", "dimension_type", "dimension_value",
             "current", "previous", "absolute_change", "direction"})
        self.assertFalse(hasattr(result, "relative_change"))

    def test_increase_reports_exact_absolute_change_direction_and_both_observations(self):
        self.put(previous=Decimal("10"), current=Decimal("15"))
        result = self.compare()
        self.assertIsInstance(result, MetricComparison)
        self.assertEqual(
            (result.metric_key, result.period_type, result.dimension_type,
             result.dimension_value),
            (ORDERS, "DAY", None, None))
        self.assertEqual(result.absolute_change, Decimal("5"))
        self.assertEqual(result.direction, DIRECTION_INCREASED)
        self.assertEqual((result.current.value, result.current.period_start), (Decimal("15"), T1))
        self.assertEqual((result.previous.value, result.previous.period_start), (Decimal("10"), T0))
        self.assertEqual(
            result.current,
            get_metric_snapshot(
                business_id=self.business.pk, metric_key=ORDERS, period_type="DAY",
                period_start=T1, period_end=T2))

    def test_decrease_unchanged_and_negative_baselines(self):
        cases = {
            "decrease": (Decimal("20"), Decimal("15"), Decimal("-5"), DIRECTION_DECREASED),
            "unchanged": (Decimal("8"), Decimal("8"), Decimal("0"), DIRECTION_UNCHANGED),
            "unchanged_at_another_scale": (
                Decimal("8"), Decimal("8.000"), Decimal("0"), DIRECTION_UNCHANGED),
            "negative_baseline_rising": (
                Decimal("-10"), Decimal("-5"), Decimal("5"), DIRECTION_INCREASED),
            "negative_baseline_falling": (
                Decimal("-10"), Decimal("-15"), Decimal("-5"), DIRECTION_DECREASED),
            "negative_to_positive": (
                Decimal("-2.5"), Decimal("1.25"), Decimal("3.75"), DIRECTION_INCREASED),
            "to_zero": (Decimal("5"), Decimal("0"), Decimal("-5"), DIRECTION_DECREASED),
            "fractional_difference": (
                Decimal("0.333333"), Decimal("0.5"), Decimal("0.166667"), DIRECTION_INCREASED),
            "smallest_storable_step_up": (
                Decimal("1"), Decimal("1.000001"), Decimal("0.000001"), DIRECTION_INCREASED),
            "smallest_storable_step_down": (
                Decimal("1"), Decimal("0.999999"), Decimal("-0.000001"), DIRECTION_DECREASED),
        }
        for name, (previous, current, absolute, direction) in cases.items():
            with self.subTest(case=name):
                models.MetricSnapshot.objects.all().delete()
                self.put(previous=previous, current=current)
                result = self.compare()
                self.assertEqual(result.absolute_change, absolute)
                self.assertEqual(result.direction, direction)

    def test_unchanged_comparison_reports_a_zero_absolute_change_not_none(self):
        self.put(previous=Decimal("8"), current=Decimal("8"))
        result = self.compare()
        self.assertIsNotNone(result.absolute_change)
        self.assertEqual(result.absolute_change, 0)
        self.assertEqual(result.direction, DIRECTION_UNCHANGED)

    def test_zero_previous_value_still_has_an_exact_absolute_change_and_direction(self):
        self.put(previous=Decimal("0"), current=Decimal("5"))
        result = self.compare()
        self.assertEqual(result.absolute_change, Decimal("5"))
        self.assertEqual(result.direction, DIRECTION_INCREASED)
        self.assertEqual(result.previous.value, Decimal("0"))
        self.assertIsNotNone(result.previous)

    def test_zero_current_value_after_a_positive_previous_is_a_real_decrease(self):
        self.put(previous=Decimal("5"), current=Decimal("0"))
        result = self.compare()
        self.assertEqual(result.absolute_change, Decimal("-5"))
        self.assertEqual(result.direction, DIRECTION_DECREASED)
        self.assertEqual(result.current.value, Decimal("0"))

    def test_zero_to_zero_is_unchanged(self):
        self.put(previous=Decimal("0"), current=Decimal("0"))
        result = self.compare()
        self.assertEqual(result.absolute_change, Decimal("0"))
        self.assertIsNotNone(result.absolute_change)
        self.assertEqual(result.direction, DIRECTION_UNCHANGED)

    def test_missing_previous_period_is_unavailable_with_none_change_not_zero(self):
        self.put(current=Decimal("5"))
        result = self.compare()
        self.assertEqual(result.direction, DIRECTION_UNAVAILABLE)
        self.assertIn(result.direction, COMPARISON_DIRECTIONS)
        self.assertIsNone(result.absolute_change)
        self.assertIsNone(result.previous)
        self.assertEqual(result.current.value, Decimal("5"))

    def test_missing_current_period_and_missing_both_are_unavailable_too(self):
        self.put(previous=Decimal("5"))
        result = self.compare()
        self.assertEqual(
            (result.direction, result.absolute_change, result.current),
            (DIRECTION_UNAVAILABLE, None, None))
        self.assertEqual(result.previous.value, Decimal("5"))
        models.MetricSnapshot.objects.all().delete()
        neither = self.compare()
        self.assertEqual(
            (neither.direction, neither.absolute_change, neither.current, neither.previous),
            (DIRECTION_UNAVAILABLE, None, None, None))

    def test_previous_period_recorded_as_unavailable_is_not_a_zero_baseline(self):
        self.record(value=UNAVAILABLE, period_start=T0, period_end=T1)
        self.record(value=Decimal("5"), period_start=T1, period_end=T2)
        result = self.compare()
        self.assertEqual(result.direction, DIRECTION_UNAVAILABLE)
        self.assertIsNone(result.absolute_change)
        self.assertIsNone(result.previous)

    def test_overlapping_or_misordered_previous_period_is_rejected(self):
        self.put(previous=Decimal("10"), current=Decimal("15"))
        cases = {
            "previous_overlaps_current_start": dict(
                previous_period_start=T0, previous_period_end=T1 + timedelta(microseconds=1)),
            "previous_inside_current": dict(
                previous_period_start=T1, previous_period_end=T2),
            "previous_contains_current": dict(
                previous_period_start=T0, previous_period_end=T3),
            "previous_after_current": dict(
                previous_period_start=T2, previous_period_end=T3),
            "identical_periods": dict(
                previous_period_start=T1, previous_period_end=T2),
        }
        for name, overrides in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(MetricValidationError):
                    self.compare(**overrides)

    def test_adjacent_and_gapped_previous_periods_are_accepted(self):
        self.record(value=Decimal("10"), period_start=T0, period_end=T1)
        self.record(value=Decimal("30"), period_start=T3, period_end=T4)
        adjacent = self.compare(
            current_period_start=T1, current_period_end=T2,
            previous_period_start=T0, previous_period_end=T1)
        self.assertEqual(adjacent.direction, DIRECTION_UNAVAILABLE)  # current T1-T2 not recorded
        self.record(value=Decimal("12"), period_start=T1, period_end=T2)
        adjacent = self.compare()
        self.assertEqual((adjacent.direction, adjacent.absolute_change),
                         (DIRECTION_INCREASED, Decimal("2")))
        gapped = self.compare(
            current_period_start=T3, current_period_end=T4,
            previous_period_start=T0, previous_period_end=T1)
        self.assertEqual((gapped.direction, gapped.absolute_change),
                         (DIRECTION_INCREASED, Decimal("20")))

    def test_invalid_period_bounds_are_rejected_on_either_side(self):
        for name, overrides in {
            "current_end_equals_start": dict(current_period_end=T1),
            "previous_end_equals_start": dict(previous_period_end=T0),
            "naive_current": dict(current_period_start=datetime(2026, 10, 2)),
            "naive_previous": dict(previous_period_start=datetime(2026, 10, 1)),
            "unknown_period_type": dict(period_type="YEAR"),
        }.items():
            with self.subTest(case=name):
                with self.assertRaises(MetricValidationError):
                    self.compare(**overrides)

    def test_comparison_follows_the_dimension_scope(self):
        product = self.make(models.Product)
        self.put(previous=Decimal("100"), current=Decimal("50"))
        self.put(previous=Decimal("4"), current=Decimal("6"),
                 dimension_type="PRODUCT", dimension_value=str(product.pk))
        wide = self.compare()
        scoped = self.compare(dimension_type="PRODUCT", dimension_value=str(product.pk))
        self.assertEqual((wide.direction, wide.absolute_change),
                         (DIRECTION_DECREASED, Decimal("-50")))
        self.assertEqual(
            (scoped.dimension_type, scoped.dimension_value, scoped.direction,
             scoped.absolute_change),
            ("PRODUCT", str(product.pk), DIRECTION_INCREASED, Decimal("2")))
        other_scope = self.compare(dimension_type="REGION", dimension_value="Dhaka")
        self.assertEqual(other_scope.direction, DIRECTION_UNAVAILABLE)

    def test_comparison_never_reads_another_businesses_observations(self):
        self.put(previous=Decimal("10"), current=Decimal("20"), business=self.other)
        result = self.compare()
        self.assertEqual(result.direction, DIRECTION_UNAVAILABLE)
        self.assertIsNone(result.current)
        self.assertIsNone(result.previous)
        theirs = self.compare(business_id=self.other.pk)
        self.assertEqual((theirs.direction, theirs.absolute_change),
                         (DIRECTION_INCREASED, Decimal("10")))

    def test_comparison_uses_the_latest_revision_of_each_period(self):
        self.put(previous=Decimal("10"), current=Decimal("15"))
        self.record(at=T3, value=Decimal("20"), period_start=T0, period_end=T1)
        result = self.compare()
        self.assertEqual(result.previous.revision, 2)
        self.assertEqual(result.absolute_change, Decimal("-5"))
        self.assertEqual(result.direction, DIRECTION_DECREASED)

    def test_comparison_results_are_immutable(self):
        self.put(previous=Decimal("10"), current=Decimal("15"))
        result = self.compare()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.direction = DIRECTION_DECREASED
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.current.value = Decimal("0")

    def test_comparison_directions_are_the_documented_closed_set(self):
        self.assertEqual(
            COMPARISON_DIRECTIONS,
            {DIRECTION_INCREASED, DIRECTION_DECREASED, DIRECTION_UNCHANGED,
             DIRECTION_UNAVAILABLE})
        self.assertEqual(
            (DIRECTION_INCREASED, DIRECTION_DECREASED, DIRECTION_UNCHANGED,
             DIRECTION_UNAVAILABLE),
            ("INCREASED", "DECREASED", "UNCHANGED", "UNAVAILABLE"))
        self.assertEqual(
            WRITE_STATUSES,
            {WRITE_CREATED, WRITE_UPDATED, WRITE_UNCHANGED, WRITE_NOT_RECORDED_UNAVAILABLE})
        self.assertEqual(
            (WRITE_CREATED, WRITE_UPDATED, WRITE_UNCHANGED, WRITE_NOT_RECORDED_UNAVAILABLE),
            ("CREATED", "UPDATED", "UNCHANGED", "NOT_RECORDED_UNAVAILABLE"))
