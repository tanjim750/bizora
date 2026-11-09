"""Tests for Customer and Order journey projections (T-016).

Verifies:
1. Multi-channel customer journey projection and chronological timeline.
2. Full lifecycle order journey projection and stage categorization.
3. Missing relationship guarantee: missing connections remain missing.
4. Multi-tenant business isolation and cross-business rejection.
5. Error handling on nonexistent entities or missing scopes.
"""

from decimal import Decimal
import datetime

from django.test import TestCase

from app import models
from app.business_graph import (
    GraphScopeError,
    GraphValidationError,
    build_customer_journey,
    build_order_journey,
    project_business_graph,
)


class CustomerAndOrderJourneyTests(TestCase):
    def setUp(self):
        super().setUp()
        self.t0 = datetime.datetime(2026, 10, 20, 10, 0, tzinfo=datetime.timezone.utc)
        self.t1 = self.t0 + datetime.timedelta(hours=1)
        self.t2 = self.t0 + datetime.timedelta(hours=2)
        self.t3 = self.t0 + datetime.timedelta(hours=3)
        self.t4 = self.t0 + datetime.timedelta(hours=4)
        self.t5 = self.t0 + datetime.timedelta(hours=5)

        self.biz_a = models.Business.objects.create(
            name="Alpha Store",
            slug="alpha-store",
            currency="USD",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )
        self.biz_b = models.Business.objects.create(
            name="Beta Store",
            slug="beta-store",
            currency="USD",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )

        # 1. Customer
        self.customer = models.Customer.objects.create(
            business=self.biz_a,
            first_name="Zoya",
            last_name="Khan",
            display_name="Zoya Khan",
            created_at=self.t0,
            updated_at=self.t0,
        )

        # 2. Marketing / Website touchpoint (t1)
        self.visitor = models.WebsiteVisitor.objects.create(
            business=self.biz_a,
            visitor_key="vis-zoya",
            first_seen_at=self.t1,
            last_seen_at=self.t1,
            created_at=self.t1,
            updated_at=self.t1,
        )
        self.session = models.WebsiteSession.objects.create(
            business=self.biz_a,
            visitor=self.visitor,
            started_at=self.t1,
            created_at=self.t1,
            updated_at=self.t1,
        )

        # 3. Product & Order (t2)
        self.product = models.Product.objects.create(
            business=self.biz_a,
            name="Smart Watch",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )
        self.order = models.Order.objects.create(
            business=self.biz_a,
            customer=self.customer,
            order_number="ORD-777",
            total_amount=Decimal("250.00"),
            currency="USD",
            status="PROCESSING",
            ordered_at=self.t2,
            created_at=self.t2,
            updated_at=self.t2,
        )

        # 4. Payment (t3)
        self.payment = models.Payment.objects.create(
            business=self.biz_a,
            order=self.order,
            amount=Decimal("250.00"),
            currency="USD",
            status="COMPLETED",
            payment_method="CARD",
            created_at=self.t3,
            updated_at=self.t3,
        )

        # 5. Shipment (t4)
        self.shipment = models.Shipment.objects.create(
            business=self.biz_a,
            order=self.order,
            tracking_code="TRK-777",
            provider="DHL",
            status="DELIVERED",
            created_at=self.t4,
            updated_at=self.t4,
        )

        # 6. Support Call (t5)
        self.call = models.Call.objects.create(
            business=self.biz_a,
            direction="INBOUND",
            started_at=self.t5,
            created_at=self.t5,
            updated_at=self.t5,
        )

        # Verified Relationships in Business A
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="HAS_SESSION",
            target_entity_type="WEBSITE_SESSION",
            target_entity_id=self.session.pk,
            rule_key="customer_session",
            relationship_source="DETERMINISTIC",
            created_at=self.t1,
            updated_at=self.t1,
        )
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="customer_order",
            relationship_source="DETERMINISTIC",
            created_at=self.t2,
            updated_at=self.t2,
        )
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="CONTAINS_PRODUCT",
            target_entity_type="PRODUCT",
            target_entity_id=self.product.pk,
            rule_key="order_product",
            relationship_source="DETERMINISTIC",
            created_at=self.t2,
            updated_at=self.t2,
        )
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="HAS_PAYMENT",
            target_entity_type="PAYMENT",
            target_entity_id=self.payment.pk,
            rule_key="order_payment",
            relationship_source="DETERMINISTIC",
            created_at=self.t3,
            updated_at=self.t3,
        )
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="HAS_SHIPMENT",
            target_entity_type="SHIPMENT",
            target_entity_id=self.shipment.pk,
            rule_key="order_shipment",
            relationship_source="DETERMINISTIC",
            created_at=self.t4,
            updated_at=self.t4,
        )
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="HAS_CALL",
            target_entity_type="CALL",
            target_entity_id=self.call.pk,
            rule_key="order_call",
            relationship_source="DETERMINISTIC",
            created_at=self.t5,
            updated_at=self.t5,
        )

        project_business_graph(business_id=self.biz_a.pk)

    def test_customer_journey_multi_channel_and_chronology(self):
        journey = build_customer_journey(
            business_id=self.biz_a.pk,
            customer_id=self.customer.pk,
        )
        self.assertEqual(journey.customer_id, self.customer.pk)
        self.assertEqual(journey.summary["order_count"], 1)
        self.assertEqual(journey.summary["session_count"], 1)
        self.assertEqual(journey.summary["payment_count"], 1)
        self.assertEqual(journey.summary["shipment_count"], 1)
        self.assertEqual(journey.summary["call_count"], 1)

        # Verify chronological ordering of timeline
        timestamps = [ev.timestamp for ev in journey.timeline if ev.timestamp is not None]
        self.assertEqual(timestamps, sorted(timestamps))
        stages = [ev.stage for ev in journey.timeline]
        self.assertIn("CUSTOMER", stages)
        self.assertIn("WEBSITE", stages)
        self.assertIn("COMMERCE", stages)
        self.assertIn("PAYMENT", stages)
        self.assertIn("FULFILLMENT", stages)
        self.assertIn("CALLING", stages)

    def test_order_journey_lifecycle_and_categorization(self):
        oj = build_order_journey(
            business_id=self.biz_a.pk,
            order_id=self.order.pk,
        )
        self.assertEqual(oj.order_id, self.order.pk)
        self.assertIsNotNone(oj.customer_node)
        self.assertEqual(oj.customer_node.entity_id, self.customer.pk)
        self.assertEqual(len(oj.product_nodes), 1)
        self.assertEqual(oj.product_nodes[0].entity_id, self.product.pk)
        self.assertEqual(len(oj.payment_nodes), 1)
        self.assertEqual(oj.payment_nodes[0].entity_id, self.payment.pk)
        self.assertEqual(len(oj.shipment_nodes), 1)
        self.assertEqual(oj.shipment_nodes[0].entity_id, self.shipment.pk)
        self.assertEqual(len(oj.communication_nodes), 1)
        self.assertEqual(oj.communication_nodes[0].entity_id, self.call.pk)

        # Total amount and status
        self.assertEqual(oj.status, "PROCESSING")
        self.assertEqual(oj.total_amount, "250.00")

    def test_missing_relationships_remain_missing(self):
        # Create an isolated order with NO payments, NO shipments, NO calls
        isolated_order = models.Order.objects.create(
            business=self.biz_a,
            order_number="ORD-ISOLATED",
            total_amount=Decimal("50.00"),
            currency="USD",
            status="PENDING",
            ordered_at=self.t2,
            created_at=self.t2,
            updated_at=self.t2,
        )
        project_business_graph(business_id=self.biz_a.pk)

        oj = build_order_journey(
            business_id=self.biz_a.pk,
            order_id=isolated_order.pk,
        )
        self.assertIsNone(oj.customer_node)
        self.assertEqual(len(oj.product_nodes), 0)
        self.assertEqual(len(oj.payment_nodes), 0)
        self.assertEqual(len(oj.shipment_nodes), 0)
        self.assertEqual(len(oj.communication_nodes), 0)
        self.assertEqual(oj.node_count if hasattr(oj, "node_count") else len(oj.nodes), 1)

    def test_cross_business_isolation_in_journeys(self):
        # Entity belonging to Business B queried under Business A scope
        cust_b = models.Customer.objects.create(
            business=self.biz_b,
            first_name="Bilal",
            created_at=self.t0,
            updated_at=self.t0,
        )
        project_business_graph(business_id=self.biz_b.pk)

        with self.assertRaises(GraphScopeError):
            build_customer_journey(
                business_id=self.biz_a.pk,
                customer_id=cust_b.pk,
            )

        with self.assertRaises(GraphValidationError):
            build_customer_journey(
                business_id=self.biz_a.pk,
                customer_id=999999,
            )
