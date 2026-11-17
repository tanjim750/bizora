"""BI-03: the existing metric calculators are run for a business and period by the run_intelligence command."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from app import models
from app.business_intelligence import pipeline

OCT = datetime(2026, 10, 1, tzinfo=timezone.utc)
NOV = datetime(2026, 11, 1, tzinfo=timezone.utc)
D = Decimal


class PeriodHelperTests(SimpleTestCase):
    def test_month_bounds_cover_the_utc_calendar_month(self):
        self.assertEqual(pipeline.month_bounds(datetime(2026, 10, 17, 9, 30, tzinfo=timezone.utc)), (OCT, NOV))
        self.assertEqual(pipeline.month_bounds(datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)),
                         (datetime(2026, 12, 1, tzinfo=timezone.utc), datetime(2027, 1, 1, tzinfo=timezone.utc)))

    def test_default_period_is_the_current_month(self):
        now = datetime(2026, 11, 10, 8, tzinfo=timezone.utc)
        self.assertEqual(pipeline.default_period(now), ("MONTH", NOV, datetime(2026, 12, 1, tzinfo=timezone.utc)))


class PipelineFixture(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Pipeline shop", slug="pipeline-shop", currency="BDT", created_at=OCT, updated_at=OCT)
        self.other = models.Business.objects.create(
            name="Other shop", slug="other-pipeline-shop", currency="BDT", created_at=OCT, updated_at=OCT)

    def seed_october(self, business=None):
        business = business or self.business
        stamp = {"created_at": OCT + timedelta(days=4), "updated_at": OCT + timedelta(days=4)}
        customer = models.Customer.objects.create(
            business=business, first_name="Rina", last_name="Das", display_name="Rina Das", **stamp)
        product = models.Product.objects.create(business=business, name="Tea", **stamp)
        order = models.Order.objects.create(
            business=business, customer=customer, status="CONFIRMED", currency="BDT", subtotal=D("250.00"),
            total_amount=D("250.00"), ordered_at=OCT + timedelta(days=4), **stamp)
        models.OrderItem.objects.create(
            order=order, product=product, product_name="Tea", quantity=2, unit_price=D("125.00"),
            total_amount=D("250.00"), created_at=stamp["created_at"])
        models.Shipment.objects.create(
            business=business, order=order, customer=customer, provider="MOCK", status="FAILED",
            currency="BDT", submitted_at=OCT + timedelta(days=5), **stamp)
        models.Conversation.objects.create(
            business=business, customer=customer, channel="WHATSAPP", status="OPEN",
            started_at=OCT + timedelta(days=6), **stamp)

    def run_october(self, **extra):
        return pipeline.run_metric_calculators(
            business_id=self.business.pk, period_type="MONTH", period_start=OCT, period_end=NOV, **extra)

    def snapshot(self, name):
        return models.MetricSnapshot.objects.get(
            business=self.business, metric__key=f"bi.metric.{name}.v1", period_start=OCT, dimension_type=None)

    def counts(self):
        return {"snapshots": models.MetricSnapshot.objects.count(), "metrics": models.BusinessMetric.objects.count()}


class RunMetricCalculatorsTests(PipelineFixture):
    def test_records_metric_snapshots_from_existing_records(self):
        self.seed_october()
        steps = self.run_october()

        statuses = {step.name: step.status for step in steps}
        self.assertEqual(statuses.pop("campaign_metrics"), pipeline.STEP_SKIPPED)
        self.assertEqual(set(statuses.values()), {pipeline.STEP_COMPLETED})
        self.assertEqual(models.BusinessMetric.objects.filter(business=self.business).count(), 42)
        self.assertEqual(self.snapshot("sales_total_orders").value, D("1"))
        self.assertEqual(self.snapshot("revenue_gross").value, D("250"))
        self.assertEqual(self.snapshot("support_unresolved_cases").value, D("1"))
        self.assertEqual(self.snapshot("delivery_failure_rate").value, D("1"))

    def test_no_facts_or_issues_are_created(self):
        self.seed_october()
        self.run_october()
        self.assertEqual(models.BusinessFact.all_objects.filter(business=self.business).count(), 0)
        self.assertEqual(models.BusinessIssue.objects.filter(business=self.business).count(), 0)

    def test_rerun_is_idempotent(self):
        self.seed_october()
        self.run_october()
        before = self.counts()
        self.run_october()
        self.assertEqual(self.counts(), before)

    def test_tenants_stay_isolated(self):
        self.seed_october(self.other)
        self.run_october()
        self.assertEqual(self.snapshot("sales_total_orders").value, D("0"))
        self.assertFalse(models.MetricSnapshot.objects.filter(business=self.other).exists())

    def test_empty_business_records_only_measured_zeros(self):
        self.run_october()
        self.assertEqual(self.snapshot("sales_total_orders").value, D("0"))
        # Rates with no denominator are not recorded: zero is never substituted for missing data.
        self.assertFalse(models.MetricSnapshot.objects.filter(
            business=self.business, metric__key="bi.metric.delivery_failure_rate.v1").exists())

    def test_failing_recorder_is_reported_and_does_not_stop_the_rest(self):
        self.seed_october()
        with patch("app.business_intelligence.revenue.record_revenue_metrics", side_effect=ValueError("boom")):
            steps = self.run_october()
        failed = [s for s in steps if s.status == pipeline.STEP_FAILED]
        self.assertEqual([s.name for s in failed], ["revenue_metrics"])
        self.assertEqual(failed[0].error, {"code": "ValueError", "detail": "boom"})
        self.assertEqual(self.snapshot("sales_total_orders").value, D("1"))

    def test_failing_registry_sync_is_reported(self):
        with patch("app.business_intelligence.pipeline.metrics.sync_metric_registry", side_effect=ValueError("down")):
            steps = self.run_october()
        self.assertEqual(steps[0].name, "metric_registry")
        self.assertEqual(steps[0].status, pipeline.STEP_FAILED)

    def test_campaign_metrics_run_only_when_the_caller_chooses_an_attribution_window(self):
        steps = self.run_october(attribution_model="LAST_TOUCH", lookback_window=timedelta(days=7))
        self.assertEqual(next(s for s in steps if s.name == "campaign_metrics").status, pipeline.STEP_COMPLETED)

    def test_invalid_period_is_reported_by_every_recorder_not_raised(self):
        steps = pipeline.run_metric_calculators(
            business_id=self.business.pk, period_type="FORTNIGHT", period_start=OCT, period_end=NOV)
        self.assertEqual({s.status for s in steps if s.name != "campaign_metrics"}, {pipeline.STEP_FAILED, pipeline.STEP_COMPLETED})
        self.assertTrue(all(s.error for s in steps if s.status == pipeline.STEP_FAILED))


class RunIntelligenceCommandTests(PipelineFixture):
    def run_command(self, *args):
        out = StringIO()
        call_command("run_intelligence", *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_explicit_period_records_snapshots(self):
        self.seed_october()
        out = self.run_command("--slug", self.business.slug, "--from", "2026-10-01", "--to", "2026-11-01")
        self.assertIn("sales_metrics: COMPLETED", out)
        self.assertIn("CUSTOM 2026-10-01 to 2026-11-01:", out)
        self.assertEqual(
            models.MetricSnapshot.objects.get(
                business=self.business, metric__key="bi.metric.sales_total_orders.v1", period_type="CUSTOM").value, D("1"))
        self.assertTrue(models.BusinessRelationship.objects.filter(business=self.business).exists())

    def test_default_period_is_the_current_month(self):
        self.seed_october()
        with patch("app.management.commands.run_intelligence.default_period", return_value=("MONTH", OCT, NOV)):
            out = self.run_command("--business-id", str(self.business.pk))
        self.assertIn("MONTH 2026-10-01 to 2026-11-01:", out)

    def test_errors_are_loud(self):
        with self.assertRaises(CommandError):
            self.run_command("--slug", "missing-shop")
        with self.assertRaises(CommandError):
            self.run_command("--slug", self.business.slug, "--from", "2026-10-01")
        with self.assertRaises(CommandError):
            self.run_command("--slug", self.business.slug, "--attribution-model", "LAST_TOUCH")
        with self.assertRaises(CommandError):
            self.run_command("--slug", self.business.slug, "--from", "nonsense", "--to", "2026-11-01")
        with patch("app.business_intelligence.revenue.record_revenue_metrics", side_effect=ValueError("boom")):
            with self.assertRaises(CommandError):
                self.run_command("--slug", self.business.slug)
