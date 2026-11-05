"""Requirement-linked scenarios for BI §§7, 9 and 10 (T-005).

These tests exercise canonical rows through ``customer_product``.  They pin
exact Decimal arithmetic, half-open periods, resolved-customer semantics,
verified relationship provenance, deterministic journeys, tenant isolation,
and replay/rollback behavior.  Where the feature specification names an
analysis but supplies no event mapping, threshold, acquisition rule, region
field, or refund allocation rule, the required result is explicit
unavailability rather than an invented policy.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from app import models
from app.business_intelligence import metrics, relationships
from app.business_intelligence import customer_product as subject


D = Decimal
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = START + timedelta(days=7)


class CustomerProductTestCase(TestCase):
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

    def source(self, key="shopify"):
        return models.IntegrationSource.objects.create(
            key=key, name=key, category="COMMERCE",
            created_at=START, updated_at=START,
        )

    def connection(self, business=None, key="shopify"):
        return models.IntegrationConnection.objects.create(
            business=business or self.a, integration_source=self.source(key),
            created_at=START, updated_at=START,
        )

    def product(self, business=None, name="Product"):
        return models.Product.objects.create(
            business=business or self.a, name=name,
            created_at=START, updated_at=START,
        )

    def order(self, *, business=None, customer=None, when=None, status="DELIVERED",
              currency="BDT", total="100.00", connection=None):
        return models.Order.objects.create(
            business=business or self.a, customer=customer, ordered_at=when,
            status=status, currency=currency, total_amount=D(total),
            integration_connection=connection, created_at=START, updated_at=START,
        )

    def item(self, order, product, quantity=1, total="10.00"):
        return models.OrderItem.objects.create(
            order=order, product=product, product_name=product.name,
            quantity=quantity, unit_price=D(total) / quantity,
            total_amount=D(total), created_at=START,
        )

    def relationship(self, name, source_id, target_id, *, business=None,
                     valid_to=None, rule_key=None, relationship_source="DETERMINISTIC"):
        rule = relationships.RULES[name]
        return models.BusinessRelationship.objects.create(
            business=business or self.a, source_entity_type=rule.source_type,
            source_entity_id=source_id, relationship_type=rule.relationship_type,
            target_entity_type=rule.target_type, target_entity_id=target_id,
            confidence=D("1"), rule_key=rule_key or rule.key,
            relationship_source=relationship_source, valid_from=START,
            valid_to=valid_to, created_at=START, updated_at=START,
        )

    def args(self, **extra):
        result = dict(business_id=self.a.pk, period_type="CUSTOM",
                      period_start=START, period_end=END)
        result.update(extra)
        return result


class ProductAnalysisTests(CustomerProductTestCase):
    def test_exact_units_distinct_orders_frequency_and_per_currency_values(self):
        product = self.product()
        first = self.order(when=START, currency="BDT", total="20")
        second = self.order(when=START + timedelta(days=1), currency="USD", total="30")
        third = self.order(when=END, currency="BDT", total="999")
        for order, quantity, amount in ((first, 2, "12.50"), (second, 3, "7.25"),
                                        (third, 9, "999")):
            self.item(order, product, quantity, amount)
            self.relationship("order_product", order.pk, product.pk)

        result = subject.analyze_products(**self.args())

        self.assertEqual(result.eligible_orders, 2)
        self.assertEqual(len(result.products), 1)
        row = result.products[0]
        self.assertEqual((row.units_sold, row.order_count), (5, 2))
        self.assertEqual(row.order_frequency, D("1"))
        self.assertEqual(row.revenue_by_currency, (("BDT", D("12.50")), ("USD", D("7.25"))))
        self.assertEqual(row.order_ids, (first.pk, second.pk))
        self.assertTrue(all(isinstance(value, Decimal) for _, value in row.revenue_by_currency))

    def test_blank_currency_unclassified_status_missing_time_and_unresolved_product_are_visible(self):
        product = self.product()
        blank = self.order(when=START, currency="", status="DELIVERED")
        self.item(blank, product, 1, "4")
        self.relationship("order_product", blank.pk, product.pk)
        self.order(when=START + timedelta(hours=1), status="ALIEN")
        self.order(when=None, status="DELIVERED")
        unresolved = self.order(when=START + timedelta(hours=2))

        result = subject.analyze_products(**self.args())

        self.assertEqual(result.products[0].revenue_by_currency, ())
        self.assertEqual(result.unclassified_order_statuses, ("ALIEN",))
        self.assertEqual(result.orders_without_timestamp, 1)
        self.assertEqual(result.orders_without_resolved_product, 1)
        self.assertIn(unresolved.pk, [row.pk for row in models.Order.objects.all()])

    def test_only_live_exact_verified_relationships_supply_campaign_and_delivery_context(self):
        product = self.product()
        customer = self.customer()
        order = self.order(customer=customer, when=START + timedelta(hours=1))
        self.item(order, product)
        self.relationship("order_product", order.pk, product.pk)
        campaign = models.Campaign.objects.create(
            business=self.a, name="Campaign", platform="META",
            created_at=START, updated_at=START,
        )
        valid = self.relationship("campaign_order", campaign.pk, order.pk)
        other_campaign = models.Campaign.objects.create(
            business=self.a, name="Old", platform="META", created_at=START, updated_at=START,
        )
        self.relationship("campaign_order", other_campaign.pk, order.pk,
                          valid_to=START + timedelta(hours=1))
        shipment = models.Shipment.objects.create(
            business=self.a, order=order, customer=customer, provider="P",
            status="FAILED", submitted_at=START + timedelta(hours=2),
            created_at=START, updated_at=START,
        )
        shipment_link = self.relationship("order_shipment", order.pk, shipment.pk)

        context = subject.analyze_products(**self.args()).contexts[0]

        self.assertEqual(context.campaign_outcomes,
                         ((campaign.pk, order.pk, valid.pk, "PLATFORM_REPORTED",
                           relationships.RULES["campaign_order"].key),))
        self.assertEqual(context.delivery_outcomes[0][0:5],
                         (shipment.pk, order.pk, "FAILED", True, False))
        self.assertEqual(context.delivery_outcomes[0][5], shipment_link.pk)

    def test_product_policies_without_documented_contract_are_explicitly_unavailable(self):
        product = self.product()
        customer = self.customer()
        order = self.order(customer=customer, when=START)
        self.item(order, product)
        self.relationship("order_product", order.pk, product.pk)
        visitor = models.WebsiteVisitor.objects.create(
            business=self.a, visitor_key="v", first_seen_at=START,
            created_at=START, updated_at=START,
        )
        session = models.WebsiteSession.objects.create(
            business=self.a, visitor=visitor, started_at=START,
            created_at=START, updated_at=START,
        )
        models.WebsiteEvent.objects.create(
            session=session, visitor=visitor, product=product, event_type="VIEW",
            occurred_at=START, created_at=START,
        )

        result = subject.analyze_products(**self.args())

        for evidence in (result.conversion_performance, result.trend_classification,
                         result.high_performing_detection, result.underperforming_detection):
            self.assertFalse(evidence.available)
            self.assertEqual(evidence.reason, subject.UNAVAILABLE_MISSING_CONTRACT)
            self.assertTrue(evidence.required_contract)
        self.assertEqual(result.conversion_performance.observed_count, 1)
        # The spec requires product revenue performance, while the canonical
        # refund model has no item allocation.  The service must expose that
        # limitation instead of silently presenting gross item value as net.
        self.assertTrue(hasattr(result, "refund_allocation"))
        self.assertFalse(result.refund_allocation.available)
        self.assertEqual(result.refund_allocation.reason,
                         subject.UNAVAILABLE_MISSING_CONTRACT)

    def test_cross_business_items_products_and_relationships_never_cross_scope(self):
        foreign_product = self.product(self.b, "Foreign")
        local_order = self.order(when=START)
        self.item(local_order, foreign_product)
        # A corrupt relationship carrying the local tenant id must not bless a
        # target entity actually owned by another tenant.
        self.relationship("order_product", local_order.pk, foreign_product.pk, business=self.a)
        foreign_order = self.order(business=self.b, when=START)
        local_product = self.product(self.a, "Local")
        self.item(foreign_order, local_product)
        self.relationship("order_product", foreign_order.pk, local_product.pk, business=self.a)

        result = subject.analyze_products(**self.args())

        self.assertEqual(result.products, ())
        self.assertEqual(result.orders_without_resolved_product, 1)


class CustomerAnalysisTests(CustomerProductTestCase):
    def test_previous_purchase_makes_customer_repeat_and_same_time_orders_use_id_order_with_zero_gap(self):
        customer = self.customer()
        self.order(customer=customer, when=START - timedelta(days=1))
        first = self.order(customer=customer, when=START + timedelta(hours=1), total="10")
        second = self.order(customer=customer, when=START + timedelta(hours=1), total="20")

        result = subject.analyze_customers(**self.args())

        purchase = result.customers[0]
        self.assertEqual(purchase.segment, subject.SEGMENT_REPEAT)
        self.assertEqual(tuple(row[1] for row in purchase.ordered_purchases), (first.pk, second.pk))
        self.assertEqual(purchase.consecutive_gap_seconds, (D("0"),))
        self.assertEqual(purchase.total_by_currency, (("BDT", D("30")),))

    def test_first_purchase_in_window_is_new_and_guest_is_never_inferred(self):
        known = self.customer()
        self.order(customer=known, when=START)
        self.order(customer=None, when=START + timedelta(hours=1))

        result = subject.analyze_customers(**self.args())

        self.assertEqual([(row.customer_id, row.segment) for row in result.customers],
                         [(known.pk, subject.SEGMENT_NEW)])
        self.assertEqual(result.orders_without_customer, 1)
        self.assertFalse(result.acquisition_channel.available)
        self.assertEqual(result.acquisition_channel.reason,
                         subject.UNAVAILABLE_MISSING_CONTRACT)

    def test_journey_is_deduplicated_deterministic_and_reports_missing_timestamps(self):
        customer = self.customer()
        order = self.order(customer=customer, when=START + timedelta(hours=1))
        payment = models.Payment.objects.create(
            business=self.a, customer=customer, order=order, status="PAID", amount=D("10"),
            paid_at=order.ordered_at, created_at=START, updated_at=START,
        )
        missing_payment = models.Payment.objects.create(
            business=self.a, customer=customer, order=order, amount=D("2"), paid_at=None,
            created_at=START, updated_at=START,
        )
        call = models.Call.objects.create(
            business=self.a, customer=customer, direction="INBOUND", status="MISSED",
            started_at=None, created_at=START, updated_at=START,
        )

        result = subject.analyze_customers(**self.args())
        activity = result.activities[0]

        self.assertEqual(activity.journey,
                         ((order.ordered_at, "ORDER", order.pk),
                          (payment.paid_at, "PAYMENT", payment.pk)))
        self.assertEqual(len(activity.journey), len(set(activity.journey)))
        self.assertEqual(result.missing_activity_timestamps,
                         ((customer.pk, "CALL", call.pk, "started_at"),
                          (customer.pk, "PAYMENT", missing_payment.pk, "paid_at")))

    def test_raw_risk_counts_and_unknown_statuses_are_not_labeled_or_thresholded(self):
        customer = self.customer()
        cancelled = self.order(customer=customer, when=START, status="CANCELLED")
        eligible = self.order(customer=customer, when=START + timedelta(hours=1))
        models.Shipment.objects.create(
            business=self.a, order=eligible, customer=customer, provider="P", status="MYSTERY",
            submitted_at=START, created_at=START, updated_at=START,
        )
        models.Conversation.objects.create(
            business=self.a, customer=customer, channel="EMAIL", status="ESCALATED",
            started_at=START, created_at=START, updated_at=START,
        )

        risk = subject.analyze_customers(**self.args()).risk_signals[0]

        self.assertEqual(risk.cancelled_orders, 1)
        self.assertEqual(risk.unclassified_shipment_statuses, ("MYSTERY",))
        self.assertEqual(risk.unclassified_conversation_statuses, ("ESCALATED",))
        self.assertFalse(hasattr(risk, "risk_level"))
        self.assertIsNotNone(cancelled.pk)

    def test_cross_business_corrupt_activity_links_are_excluded(self):
        local = self.customer(self.a, "Local")
        foreign = self.customer(self.b, "Foreign")
        local_order = self.order(customer=local, when=START)
        self.order(business=self.a, customer=foreign, when=START + timedelta(hours=1))
        foreign_order = self.order(business=self.b, customer=foreign, when=START)
        models.Payment.objects.create(
            business=self.b, customer=local, order=foreign_order, amount=D("9"), paid_at=START,
            created_at=START, updated_at=START,
        )
        models.Conversation.objects.create(
            business=self.b, customer=local, channel="EMAIL", started_at=START,
            created_at=START, updated_at=START,
        )
        models.Call.objects.create(
            business=self.b, customer=local, direction="INBOUND", status="DONE",
            started_at=START, created_at=START, updated_at=START,
        )
        models.Shipment.objects.create(
            business=self.b, order=local_order, customer=local, provider="P",
            submitted_at=START, created_at=START, updated_at=START,
        )
        visitor = models.WebsiteVisitor.objects.create(
            business=self.b, customer=local, visitor_key="cross-tenant",
            first_seen_at=START, created_at=START, updated_at=START,
        )
        session = models.WebsiteSession.objects.create(
            business=self.b, visitor=visitor, customer=local, started_at=START,
            created_at=START, updated_at=START,
        )
        models.WebsiteEvent.objects.create(
            session=session, visitor=visitor, customer=local, event_type="VIEW",
            occurred_at=START, created_at=START,
        )

        result = subject.analyze_customers(**self.args())
        activity = next(row for row in result.activities if row.customer_id == local.pk)

        self.assertNotIn(foreign.pk, [row.customer_id for row in result.customers])
        self.assertEqual(activity.orders, (local_order.pk,))
        self.assertEqual(activity.payments, ())
        self.assertEqual(activity.website_sessions, ())
        self.assertEqual(activity.website_events, ())
        self.assertEqual(activity.conversations, ())
        self.assertEqual(activity.calls, ())
        self.assertEqual(activity.shipments, ())


class RetentionAnalysisTests(CustomerProductTestCase):
    def test_repeat_rate_uses_resolved_period_customers_and_frequency_is_orders_per_customer(self):
        repeat = self.customer(name="Repeat")
        single = self.customer(name="Single")
        self.order(customer=repeat, when=START)
        self.order(customer=repeat, when=START + timedelta(days=1))
        self.order(customer=single, when=START + timedelta(days=2))
        self.order(customer=None, when=START + timedelta(days=3))

        result = subject.analyze_retention(**self.args())

        self.assertEqual((result.customers, result.repeat_customers, result.order_count), (2, 1, 3))
        self.assertEqual(result.repeat_rate, D("0.5"))
        self.assertEqual(result.purchase_frequency, D("1.5"))
        self.assertEqual(result.period_orders_without_customer, 1)

    def test_zero_resolved_customers_is_unavailable_not_zero(self):
        self.order(customer=None, when=START)

        result = subject.analyze_retention(**self.args())

        self.assertEqual(result.customers, 0)
        self.assertIs(result.repeat_rate, metrics.UNAVAILABLE)
        self.assertIs(result.purchase_frequency, metrics.UNAVAILABLE)

    def test_product_repeat_requires_period_orders_and_campaign_retention_requires_live_provenance(self):
        customer = self.customer()
        product = self.product()
        first = self.order(customer=customer, when=START)
        second = self.order(customer=customer, when=START + timedelta(days=1))
        for order in (first, second):
            self.item(order, product)
            self.relationship("order_product", order.pk, product.pk)
        campaign = models.Campaign.objects.create(
            business=self.a, name="C", platform="META", created_at=START, updated_at=START,
        )
        evidence = self.relationship("campaign_order", campaign.pk, first.pk)
        stale_campaign = models.Campaign.objects.create(
            business=self.a, name="Stale", platform="META", created_at=START, updated_at=START,
        )
        self.relationship("campaign_order", stale_campaign.pk, second.pk, valid_to=END)

        result = subject.analyze_retention(**self.args())

        self.assertEqual(result.product_repeat, ((product.pk, 1, 1, D("1")),))
        self.assertEqual(len(result.campaign_retention), 1)
        campaign_row = result.campaign_retention[0]
        self.assertEqual((campaign_row.campaign_id, campaign_row.repeat_rate), (campaign.pk, D("1")))
        self.assertEqual(campaign_row.evidence_relationship_ids, (evidence.pk,))
        self.assertEqual(campaign_row.provenance, "PLATFORM_REPORTED")

    def test_multi_campaign_links_remain_separate_and_region_and_trend_rules_are_unavailable(self):
        customer = self.customer()
        order = self.order(customer=customer, when=START)
        campaigns = []
        for name in ("A", "B"):
            campaign = models.Campaign.objects.create(
                business=self.a, name=name, platform="META", created_at=START, updated_at=START,
            )
            self.relationship("campaign_order", campaign.pk, order.pk)
            campaigns.append(campaign.pk)

        result = subject.analyze_retention(**self.args())

        self.assertEqual([row.campaign_id for row in result.campaign_retention], campaigns)
        self.assertEqual(result.unavailable_segments[0][0], subject.DIMENSION_REGION)
        self.assertEqual(result.unavailable_segments[0][1].reason,
                         subject.UNAVAILABLE_MISSING_CONTRACT)
        self.assertEqual(result.trend_classification.reason,
                         subject.UNAVAILABLE_MISSING_CONTRACT)

    def test_cross_business_campaign_entity_is_not_accepted_as_retention_provenance(self):
        customer = self.customer()
        order = self.order(customer=customer, when=START)
        foreign_campaign = models.Campaign.objects.create(
            business=self.b, name="Foreign", platform="META",
            created_at=START, updated_at=START,
        )
        self.relationship("campaign_order", foreign_campaign.pk, order.pk, business=self.a)

        result = subject.analyze_retention(**self.args())

        self.assertEqual(result.campaign_retention, ())
        self.assertNotIn(
            (subject.DIMENSION_CAMPAIGN, str(foreign_campaign.pk)),
            [(row.dimension_type, row.dimension_value) for row in result.segments],
        )


class CustomerMetricRecordingTests(CustomerProductTestCase):
    def test_records_all_five_metrics_with_exact_values_and_currency_identity(self):
        repeat = self.customer(name="Repeat")
        single = self.customer(name="Single")
        self.order(customer=repeat, when=START, total="10.10", currency="BDT")
        self.order(customer=repeat, when=START + timedelta(days=1), total="20.20", currency="BDT")
        self.order(customer=single, when=START + timedelta(days=2), total="3.30", currency="USD")

        result = subject.record_customer_metrics(**self.args())

        self.assertEqual(result.average_value_by_currency,
                         (("BDT", D("30.30")), ("USD", D("3.30"))))
        self.assertEqual({name for name, _ in result.snapshots}, {
            "new_customers", "active_customers", "repeat_rate", "purchase_frequency",
            "average_value:BDT", "average_value:USD",
        })
        expected = {
            "bi.metric.customer_new_customers.v1": D("2"),
            "bi.metric.customer_active_customers.v1": D("2"),
            "bi.metric.customer_repeat_rate.v1": D("0.5"),
            "bi.metric.customer_purchase_frequency.v1": D("1.5"),
        }
        for key, value in expected.items():
            snapshot = models.MetricSnapshot.objects.get(business=self.a, metric__key=key)
            self.assertEqual(snapshot.value, value)
            self.assertIsInstance(snapshot.value, Decimal)
        average_rows = models.MetricSnapshot.objects.filter(
            business=self.a, metric__key="bi.metric.customer_average_value.v1",
        ).order_by("dimension_value")
        self.assertEqual([(row.dimension_type, row.dimension_value, row.value)
                          for row in average_rows],
                         [("CURRENCY", "BDT", D("30.300000")),
                          ("CURRENCY", "USD", D("3.300000"))])

    def test_replay_is_unchanged_and_transaction_rolls_back_partial_recording(self):
        customer = self.customer()
        self.order(customer=customer, when=START)
        first = subject.record_customer_metrics(**self.args())
        second = subject.record_customer_metrics(**self.args())
        self.assertEqual(models.MetricSnapshot.objects.filter(business=self.a).count(), 5)
        self.assertTrue(all(write.status == metrics.WRITE_UNCHANGED for _, write in second.snapshots))
        self.assertTrue(all(write.status == metrics.WRITE_CREATED for _, write in first.snapshots))

        models.MetricSnapshot.objects.filter(business=self.a).delete()
        original = metrics.record_metric_snapshot
        calls = {"count": 0}

        def fail_third(**kwargs):
            calls["count"] += 1
            if calls["count"] == 3:
                raise RuntimeError("fault")
            return original(**kwargs)

        with patch.object(metrics, "record_metric_snapshot", side_effect=fail_third):
            with self.assertRaisesRegex(RuntimeError, "fault"):
                subject.record_customer_metrics(**self.args())
        self.assertEqual(models.MetricSnapshot.objects.filter(business=self.a).count(), 0)

    def test_rule_collision_fails_closed(self):
        customer = self.customer()
        self.order(customer=customer, when=START)
        metrics.record_metric_snapshot(
            business_id=self.a.pk, metric_key="bi.metric.customer_new_customers.v1",
            value=D("1"), period_type="CUSTOM", period_start=START, period_end=END,
            calculation_rule="bi.metric.customer_new_customers.v1.foreign",
            inputs={"seed": True},
        )

        with self.assertRaises(metrics.MetricSnapshotConflictError):
            subject.record_customer_metrics(**self.args())

    def test_selected_currency_with_no_resolved_customers_is_not_recorded_as_observed_zero(self):
        self.order(customer=None, when=START, currency="USD")

        result = subject.record_customer_metrics(**self.args(currency="USD"))

        average = dict(result.snapshots)["average_value:USD"]
        self.assertEqual(average.status, metrics.WRITE_NOT_RECORDED_UNAVAILABLE)
        self.assertIsNone(average.observation)
        self.assertEqual(models.MetricSnapshot.objects.filter(
            business=self.a, metric__key="bi.metric.customer_average_value.v1",
        ).count(), 0)

