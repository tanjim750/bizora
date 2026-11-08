"""Requirement-linked tests for BI §4 (Attribution) - Ticket T-006.

Tests exercise:
- Direct, first-touch, and last-touch attribution models.
- Campaign, session, customer, and order attribution evidence linking.
- Strict temporal ordering (future touchpoints excluded).
- Configurable lookback windows.
- Unresolved identity (guest orders without direct sessions stay unattributed).
- Platform-reported attribution kept strictly distinct from deterministic attribution.
- Cross-tenant business isolation.
- Currency isolation for attributed revenue totals.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import attribution as subject
from app.business_intelligence import metrics, relationships


D = Decimal
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = START + timedelta(days=14)
WINDOW = timedelta(days=30)


class AttributionTestCase(TestCase):
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

    def campaign(self, business=None, name="Campaign", platform="META"):
        return models.Campaign.objects.create(
            business=business or self.a, name=name, platform=platform,
            created_at=START, updated_at=START,
        )

    def visitor(self, business=None, customer=None, key=None):
        self._visitor_counter = getattr(self, "_visitor_counter", 0) + 1
        visitor_key = key or f"v_{self._visitor_counter}"
        return models.WebsiteVisitor.objects.create(
            business=business or self.a, customer=customer, visitor_key=visitor_key,
            first_seen_at=START, created_at=START, updated_at=START,
        )

    def session(self, *, business=None, customer=None, visitor=None, when=None,
                utm_campaign="", utm_source="google", traffic_source="search"):
        biz = business or self.a
        vis = visitor or self.visitor(biz, customer)
        return models.WebsiteSession.objects.create(
            business=biz, customer=customer, visitor=vis, started_at=when or START,
            utm_campaign=utm_campaign, utm_source=utm_source, traffic_source=traffic_source,
            created_at=START, updated_at=START,
        )

    def order(self, *, business=None, customer=None, when=None, total="100.00", currency="BDT", status="DELIVERED"):
        return models.Order.objects.create(
            business=business or self.a, customer=customer, ordered_at=when or (START + timedelta(days=5)),
            total_amount=D(total), currency=currency, status=status,
            created_at=START, updated_at=START,
        )

    def relationship(self, name, source_id, target_id, *, business=None, valid_to=None,
                      relationship_source="DETERMINISTIC", confidence=D("1.0")):
        rule = relationships.RULES[name]
        return models.BusinessRelationship.objects.create(
            business=business or self.a, source_entity_type=rule.source_type,
            source_entity_id=source_id, relationship_type=rule.relationship_type,
            target_entity_type=rule.target_type, target_entity_id=target_id,
            confidence=confidence, rule_key=rule.key,
            relationship_source=relationship_source, valid_from=START,
            valid_to=valid_to, created_at=START, updated_at=START,
        )


class DirectAttributionTests(AttributionTestCase):
    def test_direct_session_attribution_via_relationship(self):
        customer = self.customer()
        session = self.session(customer=customer, when=START + timedelta(days=1))
        order = self.order(customer=customer, when=START + timedelta(days=2), total="250.00")
        rel = self.relationship("session_order", session.pk, order.pk)

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        self.assertTrue(oa.direct.is_attributed)
        self.assertEqual(oa.direct.model, subject.MODEL_DIRECT)
        self.assertEqual(oa.direct.touchpoint.touchpoint_id, session.pk)
        self.assertEqual(oa.direct.evidence_relationships, (rel.pk,))
        self.assertEqual(oa.direct.provenance, subject.PROVENANCE_DETERMINISTIC)
        self.assertEqual(oa.direct.amount, D("250.00"))

    def test_direct_session_attribution_via_event_fallback(self):
        customer = self.customer()
        session = self.session(customer=customer, when=START + timedelta(days=1))
        order = self.order(customer=customer, when=START + timedelta(days=2))
        event = models.WebsiteEvent.objects.create(
            session=session, visitor=session.visitor, customer=customer, order=order,
            event_type="PURCHASE", occurred_at=order.ordered_at, created_at=START,
        )

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        self.assertTrue(oa.direct.is_attributed)
        self.assertEqual(oa.direct.touchpoint.touchpoint_id, session.pk)
        self.assertEqual(oa.direct.evidence_event_ids, (event.pk,))

    def test_non_service_relationship_source_is_not_authority(self):
        customer = self.customer()
        session = self.session(customer=customer, when=START + timedelta(days=1))
        order = self.order(customer=customer, when=START + timedelta(days=2))
        self.relationship(
            "session_order", session.pk, order.pk,
            relationship_source="MANUAL",
        )

        result = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        self.assertFalse(result.direct.is_attributed)


class FirstAndLastTouchAttributionTests(AttributionTestCase):
    def test_first_touch_and_last_touch_chronological_selection(self):
        customer = self.customer()
        camp1 = self.campaign(name="Spring_Sale")
        camp2 = self.campaign(name="Retargeting_Ads")

        # Session 1: Day 1 with Spring_Sale campaign
        s1 = self.session(customer=customer, when=START + timedelta(days=1), utm_campaign="Spring_Sale")
        # Session 2: Day 3 without campaign
        self.session(customer=customer, when=START + timedelta(days=3))
        # Session 3: Day 5 with Retargeting_Ads campaign
        s3 = self.session(customer=customer, when=START + timedelta(days=5), utm_campaign="Retargeting_Ads")
        self.relationship("campaign_session", camp1.pk, s1.pk)
        self.relationship("campaign_session", camp2.pk, s3.pk)

        # Order placed on Day 6
        order = self.order(customer=customer, when=START + timedelta(days=6), total="500.00")

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        # First touch should be s1
        self.assertTrue(oa.first_touch.is_attributed)
        self.assertEqual(oa.first_touch.touchpoint.touchpoint_id, s1.pk)
        self.assertEqual(oa.first_touch.touchpoint.campaign_name, "Spring_Sale")
        self.assertEqual(oa.first_touch.touchpoint.campaign_id, camp1.pk)

        # Last touch should be s3
        self.assertTrue(oa.last_touch.is_attributed)
        self.assertEqual(oa.last_touch.touchpoint.touchpoint_id, s3.pk)
        self.assertEqual(oa.last_touch.touchpoint.campaign_name, "Retargeting_Ads")
        self.assertEqual(oa.last_touch.touchpoint.campaign_id, camp2.pk)

        self.assertEqual(oa.first_touch.candidate_touchpoint_count, 3)
        self.assertEqual(oa.last_touch.candidate_touchpoint_count, 3)

    def test_future_touchpoints_are_never_eligible(self):
        customer = self.customer()
        s_past = self.session(customer=customer, when=START + timedelta(days=1))
        order = self.order(customer=customer, when=START + timedelta(days=2))
        # Session in the future relative to the order
        self.session(customer=customer, when=START + timedelta(days=3))

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        self.assertEqual(oa.first_touch.touchpoint.touchpoint_id, s_past.pk)
        self.assertEqual(oa.last_touch.touchpoint.touchpoint_id, s_past.pk)
        self.assertEqual(oa.first_touch.candidate_touchpoint_count, 1)

    def test_lookback_window_boundary_excludes_older_touchpoints(self):
        customer = self.customer()
        # Session on day 1 (9 days before order)
        self.session(customer=customer, when=START + timedelta(days=1))
        # Session on day 8 (2 days before order)
        s_recent = self.session(customer=customer, when=START + timedelta(days=8))
        # Order on day 10
        order = self.order(customer=customer, when=START + timedelta(days=10))

        # With 5-day lookback window, s_old must be excluded
        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=timedelta(days=5)
        )

        self.assertEqual(oa.first_touch.touchpoint.touchpoint_id, s_recent.pk)
        self.assertEqual(oa.last_touch.touchpoint.touchpoint_id, s_recent.pk)
        self.assertEqual(oa.first_touch.candidate_touchpoint_count, 1)

    def test_direct_relationship_also_obeys_the_lookback_window(self):
        customer = self.customer()
        old = self.session(customer=customer, when=START + timedelta(days=1))
        order = self.order(customer=customer, when=START + timedelta(days=10))
        self.relationship("session_order", old.pk, order.pk)

        result = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk,
            lookback_window=timedelta(days=5),
        )

        self.assertFalse(result.direct.is_attributed)
        self.assertFalse(result.first_touch.is_attributed)
        self.assertFalse(result.last_touch.is_attributed)

    def test_utm_text_alone_does_not_create_campaign_authority(self):
        customer = self.customer()
        campaign = self.campaign(name="Same_Text")
        session = self.session(
            customer=customer, when=START + timedelta(days=1),
            utm_campaign="Same_Text",
        )
        order = self.order(customer=customer, when=START + timedelta(days=2))

        result = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        self.assertEqual(result.first_touch.touchpoint.touchpoint_id, session.pk)
        self.assertIsNone(result.first_touch.touchpoint.campaign_id)
        self.assertEqual(result.first_touch.touchpoint.utm_campaign, campaign.name)


class IdentityResolutionAndUnattributedTests(AttributionTestCase):
    def test_guest_order_without_direct_session_is_unattributed(self):
        customer = self.customer()
        self.session(customer=customer, when=START + timedelta(days=1))
        # Guest order with no customer_id and no direct session link
        guest_order = self.order(customer=None, when=START + timedelta(days=2))

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=guest_order.pk, lookback_window=WINDOW,
        )

        self.assertFalse(oa.direct.is_attributed)
        self.assertFalse(oa.first_touch.is_attributed)
        self.assertFalse(oa.last_touch.is_attributed)
        self.assertIsNone(oa.first_touch.touchpoint)
        self.assertEqual(oa.first_touch.provenance, subject.PROVENANCE_UNATTRIBUTED)

    def test_guest_order_with_direct_session_is_attributed_to_that_session_only(self):
        vis = self.visitor(customer=None, key="anonymous_1")
        session = self.session(customer=None, visitor=vis, when=START + timedelta(days=1), utm_campaign="Promo")
        order = self.order(customer=None, when=START + timedelta(days=2))
        self.relationship("session_order", session.pk, order.pk)

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        self.assertTrue(oa.direct.is_attributed)
        self.assertTrue(oa.first_touch.is_attributed)
        self.assertEqual(oa.first_touch.touchpoint.touchpoint_id, session.pk)


class PlatformReportedAttributionTests(AttributionTestCase):
    def test_platform_reported_attribution_is_preserved_and_distinct(self):
        customer = self.customer()
        camp = self.campaign(name="Meta_DPA", platform="META")
        order = self.order(customer=customer, when=START + timedelta(days=3), total="300.00")

        # T-001 campaign_order relationship representing platform-reported attribution
        rel = self.relationship(
            "campaign_order", camp.pk, order.pk, confidence=D("0.8500"),
        )

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order.pk, lookback_window=WINDOW,
        )

        # Deterministic models are unattributed because customer had no website session
        self.assertFalse(oa.first_touch.is_attributed)
        self.assertFalse(oa.last_touch.is_attributed)

        # Platform reported is preserved and flagged
        self.assertEqual(len(oa.platform_reported), 1)
        pr = oa.platform_reported[0]
        self.assertTrue(pr.is_attributed)
        self.assertEqual(pr.model, subject.MODEL_PLATFORM_REPORTED)
        self.assertEqual(pr.provenance, subject.PROVENANCE_PLATFORM_REPORTED)
        self.assertEqual(pr.touchpoint.campaign_id, camp.pk)
        self.assertEqual(pr.touchpoint.platform, "META")
        self.assertEqual(pr.evidence_relationships, (rel.pk,))


class MultiOrderAndSummaryTests(AttributionTestCase):
    def test_attribute_orders_period_summary_and_campaign_summaries(self):
        customer = self.customer()
        camp = self.campaign(name="Summer_Kickoff")

        s1 = self.session(customer=customer, when=START + timedelta(days=1), utm_campaign="Summer_Kickoff")
        self.relationship("campaign_session", camp.pk, s1.pk)
        self.order(customer=customer, when=START + timedelta(days=2), total="100.00", currency="BDT")
        self.order(customer=customer, when=START + timedelta(days=4), total="150.00", currency="BDT")

        summary = subject.attribute_orders(
            business_id=self.a.pk, period_type="CUSTOM", period_start=START, period_end=END,
            lookback_window=WINDOW,
        )

        self.assertEqual(summary.eligible_orders_count, 2)
        self.assertEqual(summary.attributed_counts_by_model[subject.MODEL_FIRST_TOUCH], 2)
        self.assertEqual(summary.attributed_counts_by_model[subject.MODEL_LAST_TOUCH], 2)

        # Campaign summary
        camp_sum = summary.campaign_summaries[0]
        self.assertEqual(camp_sum.campaign_id, camp.pk)
        self.assertEqual(camp_sum.attributed_orders_count, 2)
        self.assertEqual(camp_sum.attributed_revenue_by_currency, (("BDT", D("250.00")),))
        self.assertEqual(camp_sum.unique_customers_count, 1)

    def test_attribute_customer_journey(self):
        customer = self.customer()
        s1 = self.session(customer=customer, when=START + timedelta(days=1))
        s2 = self.session(customer=customer, when=START + timedelta(days=3))
        order = self.order(customer=customer, when=START + timedelta(days=4))
        self.relationship("session_order", s2.pk, order.pk)

        journey = subject.attribute_customer_journey(
            business_id=self.a.pk, customer_id=customer.pk,
            lookback_window=WINDOW,
        )

        self.assertEqual(journey.customer_id, customer.pk)
        self.assertEqual(len(journey.touchpoints), 2)
        self.assertEqual(journey.first_touchpoint.touchpoint_id, s1.pk)
        self.assertEqual(journey.last_touchpoint.touchpoint_id, s2.pk)
        self.assertEqual(journey.direct_attributions_count, 1)


class CrossTenantIsolationTests(AttributionTestCase):
    def test_cross_tenant_touchpoints_and_relationships_are_ignored(self):
        cust_a = self.customer(self.a, "CustomerA")
        cust_b = self.customer(self.b, "CustomerB")

        # Session in business b
        self.session(business=self.b, customer=cust_b, when=START + timedelta(days=1))
        # Order in business a
        order_a = self.order(business=self.a, customer=cust_a, when=START + timedelta(days=2))

        oa = subject.attribute_order(
            business_id=self.a.pk, order_id=order_a.pk, lookback_window=WINDOW,
        )

        self.assertFalse(oa.first_touch.is_attributed)
        self.assertFalse(oa.last_touch.is_attributed)

    def test_accessing_other_business_order_raises_scope_error(self):
        order_b = self.order(business=self.b, when=START + timedelta(days=2))

        with self.assertRaises(subject.AttributionScopeError):
            subject.attribute_order(
                business_id=self.a.pk, order_id=order_b.pk,
                lookback_window=WINDOW,
            )

    def test_local_order_with_foreign_customer_fails_closed(self):
        foreign_customer = self.customer(self.b, "Foreign")
        corrupt = self.order(
            business=self.a, customer=foreign_customer,
            when=START + timedelta(days=2),
        )

        with self.assertRaises(subject.AttributionScopeError):
            subject.attribute_order(
                business_id=self.a.pk, order_id=corrupt.pk,
                lookback_window=WINDOW,
            )


class ValidationTests(AttributionTestCase):
    def test_invalid_parameters_raise_validation_error(self):
        order = self.order(when=START + timedelta(days=1))
        with self.assertRaisesRegex(
                subject.AttributionValidationError, "lookback_window is required"):
            subject.attribute_order(business_id=self.a.pk, order_id=order.pk)
        with self.assertRaises(subject.AttributionValidationError):
            subject.attribute_order(business_id="invalid", order_id=1)
        with self.assertRaises(subject.AttributionValidationError):
            subject.attribute_order(business_id=self.a.pk, order_id=1, lookback_window=-10)
        with self.assertRaises(subject.AttributionValidationError):
            subject.attribute_orders(
                business_id=self.a.pk, period_type="CUSTOM", period_start=END,
                period_end=START, lookback_window=WINDOW,
            )
