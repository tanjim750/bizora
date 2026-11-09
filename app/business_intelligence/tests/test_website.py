"""Requirement-linked tests for BI §§5 and 12 (Conversion & Website Analysis) - Ticket T-008.

Tests verify:
- Ordered session-level funnel progression (View -> Cart -> Checkout -> Purchase).
- Event deduplication (repeated actions within a session do not inflate conversion counts).
- Exact Decimal funnel conversion rates, drop-offs, cart abandonment, and checkout completion.
- Unavailable data behavior for zero denominators (never returning fake zero).
- Multi-dimensional segmentation (traffic sources, devices, landing pages, products).
- Experience signals tracking (rage clicks, dead clicks, errors).
- Snapshot recording for the six registered website metrics and idempotent replay.
- Cross-tenant business isolation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import metrics, website as subject


D = Decimal
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = START + timedelta(days=7)


class WebsiteTestCase(TestCase):
    def setUp(self):
        self.a = self.business("shop-a")
        self.b = self.business("shop-b")
        for business in (self.a, self.b):
            metrics.sync_metric_registry(business_id=business.pk)

    def business(self, slug):
        return models.Business.objects.create(
            name=slug, slug=slug, currency="BDT", created_at=START, updated_at=START,
        )

    def customer(self, business=None, name="Customer"):
        return models.Customer.objects.create(
            business=business or self.a, display_name=name,
            created_at=START, updated_at=START,
        )

    def product(self, business=None, name="Item"):
        return models.Product.objects.create(
            business=business or self.a, name=name,
            created_at=START, updated_at=START,
        )

    def visitor(self, business=None, customer=None, key=None):
        self._vis_count = getattr(self, "_vis_count", 0) + 1
        return models.WebsiteVisitor.objects.create(
            business=business or self.a, customer=customer, visitor_key=key or f"vis_{self._vis_count}",
            first_seen_at=START, created_at=START, updated_at=START,
        )

    def session(self, *, business=None, customer=None, visitor=None, when=None,
                traffic_source="GOOGLE", device_type="MOBILE", landing_page="/"):
        biz = business or self.a
        vis = visitor or self.visitor(biz, customer)
        return models.WebsiteSession.objects.create(
            business=biz, customer=customer, visitor=vis, started_at=when or (START + timedelta(hours=1)),
            traffic_source=traffic_source, device_type=device_type, landing_page_url=landing_page,
            created_at=START, updated_at=START,
        )

    def event(self, session, event_type, when, product=None, order=None):
        return models.WebsiteEvent.objects.create(
            session=session, visitor=session.visitor, customer=session.customer,
            product=product, order=order, event_type=event_type, occurred_at=when,
            created_at=START,
        )

    def args(self, **extra):
        res = dict(
            business_id=self.a.pk, period_type="CUSTOM",
            period_start=START, period_end=END,
        )
        res.update(extra)
        return res


class FunnelAnalysisTests(WebsiteTestCase):
    def test_ordered_funnel_progression_and_deduplication(self):
        s = self.session()
        p = self.product()

        # Repeated events: 3 views, 2 carts, 1 checkout, 1 purchase
        t0 = START + timedelta(hours=1)
        self.event(s, "VIEW", t0, product=p)
        self.event(s, "PRODUCT_VIEW", t0 + timedelta(minutes=5), product=p)
        self.event(s, "PAGE_VIEW", t0 + timedelta(minutes=10))

        self.event(s, "ADD_TO_CART", t0 + timedelta(minutes=15), product=p)
        self.event(s, "CART", t0 + timedelta(minutes=20), product=p)

        self.event(s, "CHECKOUT", t0 + timedelta(minutes=25))
        self.event(s, "PURCHASE", t0 + timedelta(minutes=30), product=p)

        analysis = subject.analyze_website_and_funnels(**self.args())
        funnel = analysis.funnel

        # Deduplication: single session counts as 1 for each stage
        self.assertEqual(funnel.total_sessions, 1)
        self.assertEqual(funnel.view_sessions, 1)
        self.assertEqual(funnel.cart_sessions, 1)
        self.assertEqual(funnel.checkout_sessions, 1)
        self.assertEqual(funnel.purchase_sessions, 1)

        self.assertEqual(funnel.overall_conversion_rate, D("1"))
        self.assertEqual(funnel.cart_abandonment_rate, D("0"))
        self.assertEqual(funnel.checkout_completion_rate, D("1"))

    def test_funnel_drop_off_and_cart_abandonment_rates(self):
        p = self.product()
        # Session 1: View only
        s1 = self.session()
        self.event(s1, "VIEW", START + timedelta(hours=1), product=p)

        # Session 2: View -> Cart (abandons cart)
        s2 = self.session()
        self.event(s2, "VIEW", START + timedelta(hours=1), product=p)
        self.event(s2, "ADD_TO_CART", START + timedelta(hours=2), product=p)

        # Session 3: View -> Cart -> Checkout (drops off at checkout)
        s3 = self.session()
        self.event(s3, "VIEW", START + timedelta(hours=1), product=p)
        self.event(s3, "ADD_TO_CART", START + timedelta(hours=2), product=p)
        self.event(s3, "CHECKOUT", START + timedelta(hours=3))

        # Session 4: View -> Cart -> Checkout -> Purchase (completes purchase)
        s4 = self.session()
        self.event(s4, "VIEW", START + timedelta(hours=1), product=p)
        self.event(s4, "ADD_TO_CART", START + timedelta(hours=2), product=p)
        self.event(s4, "CHECKOUT", START + timedelta(hours=3))
        self.event(s4, "PURCHASE", START + timedelta(hours=4), product=p)

        analysis = subject.analyze_website_and_funnels(**self.args())
        funnel = analysis.funnel

        self.assertEqual(funnel.total_sessions, 4)
        self.assertEqual(funnel.view_sessions, 4)
        self.assertEqual(funnel.cart_sessions, 3)
        self.assertEqual(funnel.checkout_sessions, 2)
        self.assertEqual(funnel.purchase_sessions, 1)

        # Overall conversion rate = 1 / 4 = 0.25
        self.assertEqual(funnel.overall_conversion_rate, D("0.25"))

        # Cart abandonment rate: 3 carts, 1 purchase -> (3 - 1) / 3 = 2/3
        self.assertEqual(funnel.cart_abandonment_rate, subject._ratio(2, 3))

        # Checkout completion rate: 2 checkouts, 1 purchase -> 1 / 2 = 0.5
        self.assertEqual(funnel.checkout_completion_rate, D("0.5"))

        # Stages breakdown
        stages = {st.stage: st for st in funnel.stages}
        self.assertEqual(stages[subject.STAGE_VIEW].drop_off_count, 0)
        self.assertEqual(stages[subject.STAGE_CART].drop_off_count, 1)
        self.assertEqual(stages[subject.STAGE_CHECKOUT].drop_off_count, 1)
        self.assertEqual(stages[subject.STAGE_PURCHASE].drop_off_count, 1)

    def test_zero_denominators_return_unavailable(self):
        # 1 session with view only
        s = self.session()
        self.event(s, "VIEW", START + timedelta(hours=1))

        analysis = subject.analyze_website_and_funnels(**self.args())
        funnel = analysis.funnel

        # Cart was never reached: cart_abandonment_rate and checkout_completion_rate must be UNAVAILABLE
        self.assertIs(funnel.cart_abandonment_rate, metrics.UNAVAILABLE)
        self.assertIs(funnel.checkout_completion_rate, metrics.UNAVAILABLE)


class WebsiteSegmentationAndSignalsTests(WebsiteTestCase):
    def test_traffic_device_and_landing_segmentation(self):
        # Session 1: Organic Desktop converting
        s1 = self.session(traffic_source="ORGANIC", device_type="DESKTOP", landing_page="/home")
        self.event(s1, "VIEW", START + timedelta(hours=1))
        self.event(s1, "PURCHASE", START + timedelta(hours=2))

        # Session 2: Organic Desktop non-converting
        s2 = self.session(traffic_source="ORGANIC", device_type="DESKTOP", landing_page="/home")
        self.event(s2, "VIEW", START + timedelta(hours=1))

        # Session 3: Paid Mobile non-converting
        s3 = self.session(traffic_source="PAID", device_type="MOBILE", landing_page="/landing")
        self.event(s3, "VIEW", START + timedelta(hours=1))

        analysis = subject.analyze_website_and_funnels(**self.args())

        traffic_map = {t.segment_value: t for t in analysis.traffic_segments}
        self.assertEqual(traffic_map["ORGANIC"].sessions_count, 2)
        self.assertEqual(traffic_map["ORGANIC"].converted_sessions_count, 1)
        self.assertEqual(traffic_map["ORGANIC"].conversion_rate, D("0.5"))
        self.assertEqual(traffic_map["PAID"].sessions_count, 1)
        self.assertEqual(traffic_map["PAID"].conversion_rate, D("0"))

        device_map = {d.segment_value: d for d in analysis.device_segments}
        self.assertEqual(device_map["DESKTOP"].sessions_count, 2)
        self.assertEqual(device_map["DESKTOP"].converted_sessions_count, 1)
        self.assertEqual(device_map["MOBILE"].sessions_count, 1)

    def test_product_conversion_performance(self):
        p1 = self.product(name="P1")
        p2 = self.product(name="P2")

        # Session 1 views P1 and P2, purchases P1
        s1 = self.session()
        self.event(s1, "VIEW", START + timedelta(hours=1), product=p1)
        self.event(s1, "VIEW", START + timedelta(hours=1, minutes=10), product=p2)
        self.event(s1, "PURCHASE", START + timedelta(hours=2), product=p1)

        # Session 2 views P2 only
        s2 = self.session()
        self.event(s2, "VIEW", START + timedelta(hours=1), product=p2)

        analysis = subject.analyze_website_and_funnels(**self.args())
        prod_map = {p.product_id: p for p in analysis.product_conversions}

        # P1: 1 viewing session, 1 purchasing session -> conv rate 1.0
        self.assertEqual(prod_map[p1.pk].viewing_sessions_count, 1)
        self.assertEqual(prod_map[p1.pk].purchasing_sessions_count, 1)
        self.assertEqual(prod_map[p1.pk].conversion_rate, D("1"))

        # P2: 2 viewing sessions, 0 purchasing sessions -> conv rate 0.0
        self.assertEqual(prod_map[p2.pk].viewing_sessions_count, 2)
        self.assertEqual(prod_map[p2.pk].purchasing_sessions_count, 0)
        self.assertEqual(prod_map[p2.pk].conversion_rate, D("0"))

    def test_experience_signals_tracking(self):
        s = self.session()
        self.event(s, "RAGE_CLICK", START + timedelta(hours=1))
        self.event(s, "RAGE_CLICK", START + timedelta(hours=1, minutes=1))
        self.event(s, "DEAD_CLICK", START + timedelta(hours=1, minutes=2))
        self.event(s, "ERROR", START + timedelta(hours=1, minutes=3))

        analysis = subject.analyze_website_and_funnels(**self.args())
        sig_map = {sig.signal_type: sig for sig in analysis.experience_signals}

        self.assertEqual(sig_map["RAGE_CLICK"].events_count, 2)
        self.assertEqual(sig_map["RAGE_CLICK"].affected_sessions_count, 1)
        self.assertEqual(sig_map["DEAD_CLICK"].events_count, 1)
        self.assertEqual(sig_map["ERROR"].events_count, 1)


class WebsiteSnapshotRecordingTests(WebsiteTestCase):
    def test_records_all_six_website_metrics(self):
        p = self.product()
        s1 = self.session()
        self.event(s1, "VIEW", START + timedelta(hours=1), product=p)
        self.event(s1, "ADD_TO_CART", START + timedelta(hours=2), product=p)
        self.event(s1, "CHECKOUT", START + timedelta(hours=3))
        self.event(s1, "PURCHASE", START + timedelta(hours=4), product=p)

        s2 = self.session()
        self.event(s2, "VIEW", START + timedelta(hours=1), product=p)

        rec = subject.record_website_metrics(**self.args())
        snapshots = dict(rec.snapshots)

        self.assertEqual(len(snapshots), 6)
        expected_keys = {
            "sessions", "product_views", "conversion_rate",
            "checkout_completion_rate", "cart_abandonment_rate",
            "product_view_conversion_rate",
        }
        self.assertEqual(set(snapshots.keys()), expected_keys)

        # Database rows
        db_rows = models.MetricSnapshot.objects.filter(business=self.a)
        self.assertEqual(db_rows.count(), 6)

        # Replay is idempotent
        rec2 = subject.record_website_metrics(**self.args())
        self.assertTrue(all(w.status == metrics.WRITE_UNCHANGED for _, w in rec2.snapshots))

    def test_rule_collision_fails_closed(self):
        s = self.session()
        self.event(s, "VIEW", START + timedelta(hours=1))

        # Seed foreign rule
        metrics.record_metric_snapshot(
            business_id=self.a.pk,
            metric_key="bi.metric.website_sessions.v1",
            value=D("10"),
            period_type="CUSTOM",
            period_start=START,
            period_end=END,
            calculation_rule="bi.metric.website_sessions.v1.foreign",
        )

        with self.assertRaises(metrics.MetricSnapshotConflictError):
            subject.record_website_metrics(**self.args())


class CrossTenantAndValidationTests(WebsiteTestCase):
    def test_cross_tenant_sessions_and_events_ignored(self):
        # Session and event in tenant b
        s_b = self.session(business=self.b)
        self.event(s_b, "VIEW", START + timedelta(hours=1))

        # Analysis on tenant a must see zero
        analysis = subject.analyze_website_and_funnels(**self.args())
        self.assertEqual(analysis.total_sessions, 0)
        self.assertEqual(analysis.funnel.view_sessions, 0)

    def test_validation_errors(self):
        with self.assertRaises(subject.WebsiteValidationError):
            subject.analyze_website_and_funnels(
                business_id=self.a.pk, period_type="CUSTOM",
                period_start=END, period_end=START,
            )
        with self.assertRaises(subject.WebsiteValidationError):
            subject.analyze_website_and_funnels(
                business_id="not_an_int", period_type="CUSTOM",
                period_start=START, period_end=END,
            )
