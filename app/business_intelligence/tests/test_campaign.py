from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import attribution, campaign, metrics, relationships


D = Decimal
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = START + timedelta(days=7)
WINDOW = timedelta(days=30)


class CampaignTests(TestCase):
    def setUp(self):
        self.a = self.business("a")
        self.b = self.business("b")
        metrics.sync_metric_registry(business_id=self.a.pk)
        metrics.sync_metric_registry(business_id=self.b.pk)

    def business(self, slug):
        return models.Business.objects.create(
            name=slug, slug=slug, currency="BDT", created_at=START, updated_at=START,
        )

    def camp(self, business=None, name="Campaign", currency="BDT"):
        return models.Campaign.objects.create(
            business=business or self.a, name=name, platform="META", currency=currency,
            created_at=START, updated_at=START,
        )

    def metric(self, camp, day=0, **overrides):
        values = dict(
            impressions=1000, reach=800, clicks=100, spend=D("200"),
            conversions=10, conversion_value=D("500"),
        )
        values.update(overrides)
        return models.CampaignMetric.objects.create(
            campaign=camp, metric_date=(START + timedelta(days=day)).date(),
            created_at=START, updated_at=START, **values,
        )

    def customer(self):
        return models.Customer.objects.create(
            business=self.a, display_name="C", created_at=START, updated_at=START,
        )

    def session(self, customer, when):
        visitor = models.WebsiteVisitor.objects.create(
            business=self.a, customer=customer, visitor_key=f"v-{when.day}",
            first_seen_at=when, created_at=when, updated_at=when,
        )
        return models.WebsiteSession.objects.create(
            business=self.a, visitor=visitor, customer=customer, started_at=when,
            created_at=when, updated_at=when,
        )

    def order(self, customer, when, amount="300", currency="BDT"):
        return models.Order.objects.create(
            business=self.a, customer=customer, status="DELIVERED", currency=currency,
            total_amount=D(amount), ordered_at=when, created_at=when, updated_at=when,
        )

    def relation(self, name, source, target):
        rule = relationships.RULES[name]
        return models.BusinessRelationship.objects.create(
            business=self.a, source_entity_type=rule.source_type,
            source_entity_id=source, relationship_type=rule.relationship_type,
            target_entity_type=rule.target_type, target_entity_id=target,
            rule_key=rule.key, relationship_source="DETERMINISTIC",
            confidence=D("1"), metadata={}, valid_from=START, valid_to=None,
            created_at=START, updated_at=START,
        )

    def analyze(self, **overrides):
        args = dict(
            business_id=self.a.pk, period_type="CUSTOM", period_start=START,
            period_end=END, attribution_model=attribution.MODEL_LAST_TOUCH,
            lookback_window=WINDOW,
        )
        args.update(overrides)
        return campaign.analyze_campaigns(**args)

    def test_recalculates_standard_metrics_exactly(self):
        c = self.camp()
        first = self.metric(c)
        second = self.metric(c, day=1, impressions=1000, reach=700, clicks=50,
                             spend=D("100"), conversions=5, conversion_value=D("200"))
        result = self.analyze().performances[0]
        self.assertEqual(result.source_row_ids, (first.pk, second.pk))
        self.assertEqual((result.impressions, result.reach, result.clicks), (2000, 1500, 150))
        self.assertEqual(result.spend, D("300"))
        self.assertEqual(result.ctr, D("0.075"))
        self.assertEqual(result.cpc, D("2"))
        self.assertEqual(result.cpm, D("150"))
        self.assertEqual(result.conversion_rate, D("0.1"))

    def test_zero_denominators_are_unavailable_not_zero(self):
        c = self.camp()
        self.metric(c, impressions=0, clicks=0, spend=D("0"), conversions=0)
        row = self.analyze().performances[0]
        for value in (row.ctr, row.cpc, row.cpm, row.conversion_rate, row.roas):
            self.assertIs(value, metrics.UNAVAILABLE)

    def test_missing_daily_rows_are_unavailable_not_observed_zero(self):
        self.camp()
        row = self.analyze().performances[0]
        for value in (
                row.impressions, row.reach, row.clicks, row.spend,
                row.reported_conversions, row.reported_conversion_value,
                row.ctr, row.cpc, row.cpm, row.conversion_rate, row.roas):
            self.assertIs(value, metrics.UNAVAILABLE)

    def test_attributed_revenue_and_roas_use_t006_evidence(self):
        c = self.camp()
        self.metric(c, spend=D("100"))
        customer = self.customer()
        session = self.session(customer, START + timedelta(days=1))
        self.order(customer, START + timedelta(days=2), amount="300")
        rel = self.relation("campaign_session", c.pk, session.pk)
        row = self.analyze().performances[0]
        self.assertEqual(row.attributed_orders, 1)
        self.assertEqual(row.attributed_revenue, D("300"))
        self.assertEqual(row.roas, D("3"))
        self.assertEqual(row.attribution_relationship_ids, (rel.pk,))

    def test_other_currency_attribution_is_never_summed(self):
        c = self.camp(currency="BDT")
        self.metric(c, spend=D("100"))
        customer = self.customer()
        session = self.session(customer, START + timedelta(days=1))
        self.order(customer, START + timedelta(days=2), amount="50", currency="USD")
        self.relation("campaign_session", c.pk, session.pk)
        row = self.analyze().performances[0]
        self.assertIs(row.attributed_revenue, metrics.UNAVAILABLE)
        self.assertEqual(row.attributed_revenue_excluded_currencies, (("USD", D("50")),))
        self.assertIs(row.roas, metrics.UNAVAILABLE)

    def test_cross_business_rows_do_not_contribute(self):
        local = self.camp()
        foreign = self.camp(self.b)
        self.metric(local, clicks=2)
        self.metric(foreign, clicks=999, spend=D("999"))
        rows = self.analyze().performances
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].clicks, 2)

    def test_half_open_daily_period(self):
        c = self.camp()
        self.metric(c, day=0, clicks=1)
        self.metric(c, day=6, clicks=2)
        self.metric(c, day=7, clicks=999)
        self.assertEqual(self.analyze().performances[0].clicks, 3)

    def test_low_performance_is_explicitly_unavailable_without_threshold(self):
        self.camp()
        evidence = self.analyze().low_performance_detection
        self.assertFalse(evidence.available)
        self.assertEqual(evidence.reason, campaign.UNAVAILABLE_MISSING_THRESHOLD)

    def test_recording_attempts_ten_metrics_skips_unavailable_and_replays(self):
        c = self.camp()
        self.metric(c)
        args = dict(
            business_id=self.a.pk, period_type="CUSTOM", period_start=START,
            period_end=END, attribution_model=attribution.MODEL_LAST_TOUCH,
            lookback_window=WINDOW,
        )
        first = campaign.record_campaign_metrics(**args)
        second = campaign.record_campaign_metrics(**args)
        self.assertEqual(len(first.snapshots), 10)
        self.assertEqual(models.MetricSnapshot.objects.filter(business=self.a).count(), 8)
        for _, name, write in second.snapshots:
            if name in {"attributed_revenue", "roas"}:
                self.assertEqual(write.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
            else:
                self.assertEqual(write.status, metrics.WRITE_UNCHANGED)
        self.assertTrue(all(write.observation is None for _, name, write in first.snapshots
                            if name in {"attributed_revenue", "roas"}))

    def test_invalid_negative_source_value_fails(self):
        c = self.camp()
        self.metric(c, clicks=-1)
        with self.assertRaises(campaign.CampaignValidationError):
            self.analyze()

    def test_window_and_model_are_required_and_validated(self):
        self.camp()
        with self.assertRaises(attribution.AttributionValidationError):
            self.analyze(lookback_window=None)
        with self.assertRaises(campaign.CampaignValidationError):
            self.analyze(attribution_model="INVENTED")
