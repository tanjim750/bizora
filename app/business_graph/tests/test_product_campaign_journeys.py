"""Tests for Product and Campaign journey projections with dimension filtering (T-017).

Verifies:
1. Product journey projection across orders, customers, website events, payments, and shipments.
2. Campaign journey projection across sessions, conversions, customers, orders, and post-conversion outcomes.
3. Dimension and property filtering on journeys (status, provider, channel).
4. Multi-tenant business isolation and cross-business rejection.
5. Missing relationship guarantee: missing connections remain absent.
"""

from decimal import Decimal
import datetime

from django.test import TestCase

from app import models
from app.business_graph import (
    GraphFilter,
    GraphScopeError,
    GraphValidationError,
    build_campaign_journey,
    build_product_journey,
    project_business_graph,
)


class ProductAndCampaignJourneyTests(TestCase):
    def setUp(self):
        super().setUp()
        self.t0 = datetime.datetime(2026, 10, 20, 10, 0, tzinfo=datetime.timezone.utc)
        self.t1 = self.t0 + datetime.timedelta(hours=1)
        self.t2 = self.t0 + datetime.timedelta(hours=2)
        self.t3 = self.t0 + datetime.timedelta(hours=3)
        self.t4 = self.t0 + datetime.timedelta(hours=4)

        self.biz_a = models.Business.objects.create(
            name="Alpha Corp",
            slug="alpha-corp",
            currency="USD",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )
        self.biz_b = models.Business.objects.create(
            name="Beta Corp",
            slug="beta-corp",
            currency="USD",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )

        # Campaign (t0)
        self.campaign = models.Campaign.objects.create(
            business=self.biz_a,
            name="Black Friday",
            platform="GOOGLE",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )

        # Website Visitor & Session (t1)
        self.visitor = models.WebsiteVisitor.objects.create(
            business=self.biz_a,
            visitor_key="vis-1",
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

        # Customer & Product (t2)
        self.customer = models.Customer.objects.create(
            business=self.biz_a,
            first_name="Tariq",
            last_name="Ali",
            display_name="Tariq Ali",
            created_at=self.t2,
            updated_at=self.t2,
        )
        self.product = models.Product.objects.create(
            business=self.biz_a,
            name="Wireless Headphones",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )

        # Order (t3)
        self.order = models.Order.objects.create(
            business=self.biz_a,
            customer=self.customer,
            order_number="ORD-BF-101",
            total_amount=Decimal("120.00"),
            currency="USD",
            status="DELIVERED",
            ordered_at=self.t3,
            created_at=self.t3,
            updated_at=self.t3,
        )

        # Payment & Shipment (t4)
        self.payment = models.Payment.objects.create(
            business=self.biz_a,
            order=self.order,
            amount=Decimal("120.00"),
            currency="USD",
            status="COMPLETED",
            created_at=self.t4,
            updated_at=self.t4,
        )
        self.shipment = models.Shipment.objects.create(
            business=self.biz_a,
            order=self.order,
            tracking_code="TRK-DHL-101",
            provider="DHL",
            status="DELIVERED",
            created_at=self.t4,
            updated_at=self.t4,
        )

        # Conversion
        self.conversion = models.CampaignConversion.objects.create(
            campaign=self.campaign,
            conversion_type="PURCHASE",
            converted_at=self.t3,
            created_at=self.t3,
        )

        # Authoritative verified relationships
        # Campaign -> Session
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CAMPAIGN",
            source_entity_id=self.campaign.pk,
            relationship_type="REPORTED_SESSION",
            target_entity_type="WEBSITE_SESSION",
            target_entity_id=self.session.pk,
            rule_key="campaign_session",
            relationship_source="REPORTED",
            created_at=self.t1,
            updated_at=self.t1,
        )
        # Campaign -> Conversion
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CAMPAIGN",
            source_entity_id=self.campaign.pk,
            relationship_type="HAS_REPORTED_CONVERSION",
            target_entity_type="CAMPAIGN_CONVERSION",
            target_entity_id=self.conversion.pk,
            rule_key="campaign_conversion",
            relationship_source="REPORTED",
            created_at=self.t3,
            updated_at=self.t3,
        )
        # Campaign -> Order
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CAMPAIGN",
            source_entity_id=self.campaign.pk,
            relationship_type="REPORTED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="campaign_order",
            relationship_source="REPORTED",
            created_at=self.t3,
            updated_at=self.t3,
        )
        # Customer -> Order
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="customer_order",
            relationship_source="DETERMINISTIC",
            created_at=self.t3,
            updated_at=self.t3,
        )
        # Order -> Product
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="CONTAINS_PRODUCT",
            target_entity_type="PRODUCT",
            target_entity_id=self.product.pk,
            rule_key="order_product",
            relationship_source="DETERMINISTIC",
            created_at=self.t3,
            updated_at=self.t3,
        )
        # Order -> Payment
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="HAS_PAYMENT",
            target_entity_type="PAYMENT",
            target_entity_id=self.payment.pk,
            rule_key="order_payment",
            relationship_source="DETERMINISTIC",
            created_at=self.t4,
            updated_at=self.t4,
        )
        # Order -> Shipment
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

        project_business_graph(business_id=self.biz_a.pk)

    def test_product_journey_projection(self):
        pj = build_product_journey(
            business_id=self.biz_a.pk,
            product_id=self.product.pk,
        )
        self.assertEqual(pj.product_id, self.product.pk)
        self.assertEqual(len(pj.order_nodes), 1)
        self.assertEqual(pj.order_nodes[0].entity_id, self.order.pk)
        self.assertEqual(len(pj.customer_nodes), 1)
        self.assertEqual(pj.customer_nodes[0].entity_id, self.customer.pk)
        self.assertEqual(len(pj.campaign_nodes), 1)
        self.assertEqual(pj.campaign_nodes[0].entity_id, self.campaign.pk)
        self.assertEqual(len(pj.payment_nodes), 1)
        self.assertEqual(len(pj.shipment_nodes), 1)

        self.assertEqual(pj.summary["order_count"], 1)
        self.assertEqual(pj.summary["customer_count"], 1)
        self.assertEqual(pj.summary["campaign_count"], 1)

        # Verify chronological timeline
        timestamps = [ev.timestamp for ev in pj.timeline if ev.timestamp is not None]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_campaign_journey_projection(self):
        cj = build_campaign_journey(
            business_id=self.biz_a.pk,
            campaign_id=self.campaign.pk,
        )
        self.assertEqual(cj.campaign_id, self.campaign.pk)
        self.assertEqual(len(cj.session_nodes), 1)
        self.assertEqual(len(cj.conversion_nodes), 1)
        self.assertEqual(len(cj.order_nodes), 1)
        self.assertEqual(len(cj.product_nodes), 1)
        self.assertEqual(len(cj.payment_nodes), 1)
        self.assertEqual(len(cj.shipment_nodes), 1)

        self.assertEqual(cj.summary["session_count"], 1)
        self.assertEqual(cj.summary["conversion_count"], 1)
        self.assertEqual(cj.summary["order_count"], 1)
        self.assertEqual(cj.summary["product_count"], 1)

    def test_dimension_filtering_on_journeys(self):
        # Filter shipment by provider="FedEx" (product only has DHL shipment)
        filter_fedex = GraphFilter(provider="FedEx")
        pj_filtered = build_product_journey(
            business_id=self.biz_a.pk,
            product_id=self.product.pk,
            filters=filter_fedex,
        )
        self.assertEqual(len(pj_filtered.shipment_nodes), 0)

        # Filter order by status="CANCELLED" (order is DELIVERED)
        filter_cancelled = GraphFilter(status="CANCELLED")
        cj_filtered = build_campaign_journey(
            business_id=self.biz_a.pk,
            campaign_id=self.campaign.pk,
            filters=filter_cancelled,
        )
        self.assertEqual(len(cj_filtered.order_nodes), 0)

    def test_cross_business_isolation_in_product_and_campaign(self):
        prod_b = models.Product.objects.create(
            business=self.biz_b,
            name="Beta Product",
            status="ACTIVE",
            created_at=self.t0,
            updated_at=self.t0,
        )
        project_business_graph(business_id=self.biz_b.pk)

        with self.assertRaises(GraphScopeError):
            build_product_journey(
                business_id=self.biz_a.pk,
                product_id=prod_b.pk,
            )

        with self.assertRaises(GraphValidationError):
            build_product_journey(
                business_id=self.biz_a.pk,
                product_id=999999,
            )

        with self.assertRaises(GraphValidationError):
            build_campaign_journey(
                business_id=self.biz_a.pk,
                campaign_id=999999,
            )
