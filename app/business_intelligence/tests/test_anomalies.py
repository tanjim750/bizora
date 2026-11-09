"""Requirement-linked tests for BI §14 (Anomaly Detection) - Ticket T-010.

Tests verify:
- Threshold-based detection (upper and lower bound breaches).
- Period-over-period detection (relative and absolute shifts).
- Small or missing baselines handling (suppressing unsupported conclusions).
- Baseline deviation detection against multi-period historical averages.
- Insufficient historical baseline data handling.
- Trend break detection (direction breaks after established multi-period trend).
- Cross-domain anomaly detection (e.g. rising spend with falling conversions).
- Dimension-level anomaly detection.
- Metric snapshot evidence preservation in AnomalyDetectionResult.
- Cross-tenant business isolation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import anomalies as subject, metrics


D = Decimal
DEFAULT_VALUE = D("0.0500")
START = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
END = START + timedelta(days=7)
PREV_START = START - timedelta(days=7)
PREV_END = START


class AnomalyDetectionTestCase(TestCase):
    def setUp(self):
        self.a = self.business("shop-a")
        self.b = self.business("shop-b")
        for b in (self.a, self.b):
            metrics.sync_metric_registry(business_id=b.pk)

    def business(self, slug):
        return models.Business.objects.create(
            name=slug, slug=slug, currency="BDT", created_at=START, updated_at=START,
        )

    def snapshot(
        self,
        *,
        business=None,
        metric_key="bi.metric.delivery_failure_rate.v1",
        value=DEFAULT_VALUE,
        period_type="WEEK",
        period_start=START,
        period_end=END,
        dimension_type=None,
        dimension_value=None,
    ):
        return metrics.record_metric_snapshot(
            business_id=(business or self.a).pk,
            metric_key=metric_key,
            value=value,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            dimension_type=dimension_type,
            dimension_value=dimension_value,
            calculation_rule=f"{metric_key}.test_rule",
        )

    def test_threshold_based_detection_upper_and_lower(self):
        rule_upper = subject.AnomalyRuleConfig(
            rule_id="test.threshold.upper",
            rule_type=subject.RULE_TYPE_THRESHOLD,
            metric_key="bi.metric.delivery_failure_rate.v1",
            upper_bound=D("0.1000"),
            severity=subject.SEVERITY_HIGH,
        )

        # 1. Normal snapshot: 5% failure rate (below 10%)
        self.snapshot(value=D("0.0500"))
        res_normal = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule_upper,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertFalse(res_normal.is_anomaly)
        self.assertEqual(res_normal.status, subject.STATUS_NORMAL)
        self.assertEqual(len(res_normal.evidence_snapshot_ids), 1)

        # 2. Breached upper threshold: 18% failure rate
        self.snapshot(value=D("0.1800"))
        res_breach = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule_upper,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertTrue(res_breach.is_anomaly)
        self.assertEqual(res_breach.status, subject.STATUS_ANOMALY_DETECTED)
        self.assertEqual(res_breach.severity, subject.SEVERITY_HIGH)
        self.assertEqual(res_breach.current_value, D("0.1800"))
        self.assertEqual(res_breach.comparison_value, D("0.1000"))
        self.assertEqual(len(res_breach.evidence_snapshot_ids), 1)

        # 3. Breached lower threshold: ROAS below 1.0
        rule_lower = subject.AnomalyRuleConfig(
            rule_id="test.threshold.lower",
            rule_type=subject.RULE_TYPE_THRESHOLD,
            metric_key="bi.metric.marketing_return_on_ad_spend.v1",
            lower_bound=D("1.0000"),
            severity=subject.SEVERITY_CRITICAL,
        )
        self.snapshot(metric_key="bi.metric.marketing_return_on_ad_spend.v1", value=D("0.7500"))
        res_low = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule_lower,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertTrue(res_low.is_anomaly)
        self.assertEqual(res_low.status, subject.STATUS_ANOMALY_DETECTED)
        self.assertEqual(res_low.severity, subject.SEVERITY_CRITICAL)

    def test_period_over_period_detection(self):
        rule = subject.AnomalyRuleConfig(
            rule_id="test.pop.revenue_drop",
            rule_type=subject.RULE_TYPE_PERIOD_COMPARISON,
            metric_key="bi.metric.revenue_net.v1",
            expected_direction=subject.DIRECTION_DECREASING,
            significant_change_ratio=D("0.2500"),  # 25% drop
            severity=subject.SEVERITY_HIGH,
        )

        # Previous period: 10,000 BDT
        self.snapshot(
            metric_key="bi.metric.revenue_net.v1",
            value=D("10000.0000"),
            period_start=PREV_START,
            period_end=PREV_END,
        )

        # Current period: 6,000 BDT (40% drop -> anomaly!)
        self.snapshot(
            metric_key="bi.metric.revenue_net.v1",
            value=D("6000.0000"),
            period_start=START,
            period_end=END,
        )

        res = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            previous_period_start=PREV_START,
            previous_period_end=PREV_END,
        )

        self.assertTrue(res.is_anomaly)
        self.assertEqual(res.status, subject.STATUS_ANOMALY_DETECTED)
        self.assertEqual(res.relative_change, D("-0.4000"))
        self.assertEqual(res.absolute_change, D("-4000.0000"))
        self.assertEqual(len(res.evidence_snapshot_ids), 2)

    def test_small_and_missing_baselines_suppress_unsupported_conclusions(self):
        rule = subject.AnomalyRuleConfig(
            rule_id="test.pop.small_baseline",
            rule_type=subject.RULE_TYPE_PERIOD_COMPARISON,
            metric_key="bi.metric.revenue_net.v1",
            significant_change_ratio=D("0.5000"),
            min_baseline_value=D("100.0000"),
        )

        # 1. Missing previous period baseline snapshot
        self.snapshot(metric_key="bi.metric.revenue_net.v1", value=D("500.0000"))
        res_missing = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            previous_period_start=PREV_START,
            previous_period_end=PREV_END,
        )
        self.assertFalse(res_missing.is_anomaly)
        self.assertEqual(res_missing.status, subject.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(res_missing.details.get("reason"), subject.REASON_MISSING_BASELINE)

        # 2. Zero baseline (e.g. previous was 0) -> no division by zero, suppresses anomaly
        self.snapshot(
            metric_key="bi.metric.revenue_net.v1",
            value=D("0.0000"),
            period_start=PREV_START,
            period_end=PREV_END,
        )
        res_zero = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            previous_period_start=PREV_START,
            previous_period_end=PREV_END,
        )
        self.assertFalse(res_zero.is_anomaly)
        self.assertEqual(res_zero.status, subject.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(res_zero.details.get("reason"), subject.REASON_SMALL_BASELINE)

        # 3. Small baseline volume below min_baseline_value (e.g. 10 BDT baseline with min 100)
        self.snapshot(
            metric_key="bi.metric.revenue_net.v1",
            value=D("10.0000"),
            period_start=PREV_START,
            period_end=PREV_END,
        )
        res_small = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            previous_period_start=PREV_START,
            previous_period_end=PREV_END,
        )
        self.assertFalse(res_small.is_anomaly)
        self.assertEqual(res_small.status, subject.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(res_small.details.get("reason"), subject.REASON_SMALL_BASELINE)

    def test_baseline_deviation_detection_and_insufficient_periods(self):
        rule = subject.AnomalyRuleConfig(
            rule_id="test.baseline.deviation",
            rule_type=subject.RULE_TYPE_BASELINE_DEVIATION,
            metric_key="bi.metric.support_conversation_volume.v1",
            significant_change_ratio=D("0.5000"),  # 50% deviation
            min_baseline_periods=3,
            min_baseline_value=D("5.0000"),
            severity=subject.SEVERITY_HIGH,
        )

        b_win_start = START - timedelta(days=21)
        b_win_end = START

        # 1. Only 2 historical periods available (less than min_baseline_periods=3)
        self.snapshot(
            metric_key="bi.metric.support_conversation_volume.v1",
            value=D("10.0000"),
            period_start=START - timedelta(days=14),
            period_end=START - timedelta(days=7),
        )
        self.snapshot(
            metric_key="bi.metric.support_conversation_volume.v1",
            value=D("12.0000"),
            period_start=START - timedelta(days=7),
            period_end=START,
        )
        self.snapshot(
            metric_key="bi.metric.support_conversation_volume.v1",
            value=D("50.0000"),
            period_start=START,
            period_end=END,
        )

        res_insufficient = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            baseline_window_start=b_win_start,
            baseline_window_end=b_win_end,
        )
        self.assertFalse(res_insufficient.is_anomaly)
        self.assertEqual(res_insufficient.status, subject.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(res_insufficient.details.get("reason"), subject.REASON_INSUFFICIENT_PERIODS)

        # 2. Add 3rd historical period -> mean = (8 + 10 + 12) / 3 = 10.0000
        self.snapshot(
            metric_key="bi.metric.support_conversation_volume.v1",
            value=D("8.0000"),
            period_start=START - timedelta(days=21),
            period_end=START - timedelta(days=14),
        )

        # Current period is 50 -> deviation of (50 - 10) / 10 = +4.0000 (+400%) -> ANOMALY!
        res_deviation = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            baseline_window_start=b_win_start,
            baseline_window_end=b_win_end,
        )
        self.assertTrue(res_deviation.is_anomaly)
        self.assertEqual(res_deviation.status, subject.STATUS_ANOMALY_DETECTED)
        self.assertEqual(res_deviation.comparison_value, D("10.0000"))
        self.assertEqual(res_deviation.relative_change, D("4.0000"))
        self.assertEqual(len(res_deviation.evidence_snapshot_ids), 4)

    def test_trend_break_detection(self):
        rule = subject.AnomalyRuleConfig(
            rule_id="test.trend.break",
            rule_type=subject.RULE_TYPE_TREND_BREAK,
            metric_key="bi.metric.website_conversion_rate.v1",
            min_trend_periods=3,
            significant_change_ratio=D("0.2000"),
            severity=subject.SEVERITY_MEDIUM,
        )

        # 3 consecutive periods of steady increase: 1.0% -> 2.0% -> 3.0%
        p1 = (START - timedelta(days=21), START - timedelta(days=14))
        p2 = (START - timedelta(days=14), START - timedelta(days=7))
        p3 = (START - timedelta(days=7), START)

        self.snapshot(metric_key="bi.metric.website_conversion_rate.v1", value=D("0.0100"), period_start=p1[0], period_end=p1[1])
        self.snapshot(metric_key="bi.metric.website_conversion_rate.v1", value=D("0.0200"), period_start=p2[0], period_end=p2[1])
        self.snapshot(metric_key="bi.metric.website_conversion_rate.v1", value=D("0.0300"), period_start=p3[0], period_end=p3[1])

        # Current period: sharp drop to 0.0150 (50% drop breaking the upward trend!)
        self.snapshot(metric_key="bi.metric.website_conversion_rate.v1", value=D("0.0150"), period_start=START, period_end=END)

        res = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            historical_periods=[p1, p2, p3],
        )

        self.assertTrue(res.is_anomaly)
        self.assertEqual(res.status, subject.STATUS_ANOMALY_DETECTED)
        self.assertEqual(res.relative_change, D("-0.5000"))
        self.assertEqual(len(res.evidence_snapshot_ids), 4)

    def test_cross_domain_anomaly_detection(self):
        rule = subject.AnomalyRuleConfig(
            rule_id="test.cross_domain.spend_up_conversions_down",
            rule_type=subject.RULE_TYPE_CROSS_DOMAIN,
            metric_key="bi.metric.marketing_spend.v1",
            secondary_metric_key="bi.metric.marketing_conversions.v1",
            expected_direction=subject.DIRECTION_INCREASING,
            secondary_expected_direction=subject.DIRECTION_DECREASING,
            significant_change_ratio=D("0.2000"),  # Spend up >= 20%
            secondary_change_ratio=D("0.1000"),    # Conversions down >= 10%
            severity=subject.SEVERITY_HIGH,
        )

        # Previous period: Spend = 1000, Conversions = 50
        self.snapshot(metric_key="bi.metric.marketing_spend.v1", value=D("1000.0000"), period_start=PREV_START, period_end=PREV_END)
        self.snapshot(metric_key="bi.metric.marketing_conversions.v1", value=D("50.0000"), period_start=PREV_START, period_end=PREV_END)

        # Current period: Spend = 1500 (+50%), Conversions = 35 (-30%) -> CROSS DOMAIN ANOMALY!
        self.snapshot(metric_key="bi.metric.marketing_spend.v1", value=D("1500.0000"), period_start=START, period_end=END)
        self.snapshot(metric_key="bi.metric.marketing_conversions.v1", value=D("35.0000"), period_start=START, period_end=END)

        res = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
            previous_period_start=PREV_START,
            previous_period_end=PREV_END,
        )

        self.assertTrue(res.is_anomaly)
        self.assertEqual(res.status, subject.STATUS_ANOMALY_DETECTED)
        self.assertEqual(res.severity, subject.SEVERITY_HIGH)
        self.assertEqual(len(res.evidence_snapshot_ids), 4)

    def test_dimension_level_anomaly_detection(self):
        # High delivery failure rate specifically for courier 'REDX'
        rule_courier = subject.AnomalyRuleConfig(
            rule_id="test.courier.failure_rate",
            rule_type=subject.RULE_TYPE_THRESHOLD,
            metric_key="bi.metric.delivery_failure_rate.v1",
            dimension_type="COURIER",
            dimension_value="REDX",
            upper_bound=D("0.1200"),
            severity=subject.SEVERITY_HIGH,
        )

        # Business-wide failure rate is 8% (normal)
        self.snapshot(value=D("0.0800"))
        # STEADFAST failure rate is 6% (normal)
        self.snapshot(value=D("0.0600"), dimension_type="COURIER", dimension_value="STEADFAST")
        # REDX failure rate is 20% (breached!)
        self.snapshot(value=D("0.2000"), dimension_type="COURIER", dimension_value="REDX")

        res = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule_courier,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        self.assertTrue(res.is_anomaly)
        self.assertEqual(res.dimension_type, "COURIER")
        self.assertEqual(res.dimension_value, "REDX")
        self.assertEqual(res.current_value, D("0.2000"))

    def test_multi_tenant_isolation(self):
        rule = subject.AnomalyRuleConfig(
            rule_id="test.isolation.threshold",
            rule_type=subject.RULE_TYPE_THRESHOLD,
            metric_key="bi.metric.delivery_failure_rate.v1",
            upper_bound=D("0.1000"),
        )

        # shop-a has failure rate of 5% (normal)
        self.snapshot(business=self.a, value=D("0.0500"))
        # shop-b has failure rate of 25% (breached)
        self.snapshot(business=self.b, value=D("0.2500"))

        res_a = subject.evaluate_anomaly_rule(
            business_id=self.a.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertFalse(res_a.is_anomaly)
        self.assertEqual(res_a.current_value, D("0.0500"))

        res_b = subject.evaluate_anomaly_rule(
            business_id=self.b.pk,
            rule=rule,
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )
        self.assertTrue(res_b.is_anomaly)
        self.assertEqual(res_b.current_value, D("0.2500"))

    def test_validation_errors(self):
        rule = subject.STANDARD_ANOMALY_RULES["delivery_failure_high"]

        # Invalid business ID
        with self.assertRaises(subject.AnomalyValidationError):
            subject.evaluate_anomaly_rule(
                business_id=-1,
                rule=rule,
                period_type="WEEK",
                period_start=START,
                period_end=END,
            )

        # Nonexistent business
        with self.assertRaises(subject.AnomalyScopeError):
            subject.evaluate_anomaly_rule(
                business_id=999999,
                rule=rule,
                period_type="WEEK",
                period_start=START,
                period_end=END,
            )

        # Inverted period
        with self.assertRaises(subject.AnomalyValidationError):
            subject.evaluate_anomaly_rule(
                business_id=self.a.pk,
                rule=rule,
                period_type="WEEK",
                period_start=END,
                period_end=START,
            )

        # Naive datetime
        naive_dt = datetime(2026, 10, 1, 0, 0)
        with self.assertRaises(subject.AnomalyValidationError):
            subject.evaluate_anomaly_rule(
                business_id=self.a.pk,
                rule=rule,
                period_type="WEEK",
                period_start=naive_dt,
                period_end=END,
            )
