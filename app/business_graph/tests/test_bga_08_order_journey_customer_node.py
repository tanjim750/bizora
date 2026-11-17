"""BGA-08: build_order_journey must identify the placing customer from the inbound
PLACED_ORDER edge / Order.customer_id, and not overwrite customer_node with another
customer linked via campaign or other 2-hop connections.
"""

from datetime import datetime, timezone
from django.test import TestCase

from app import models
from app.business_graph import project_business_graph
from app.business_graph.journeys import build_order_journey
from app.tests.bi_graph_helpers import client_for, graph_url, make_member

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


class OrderJourneyCustomerNodeTests(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Order Journey Shop",
            slug="order-journey-shop",
            currency="BDT",
            created_at=T0,
            updated_at=T0,
        )
        common = {"business": self.business, "created_at": T0, "updated_at": T0}
        # Customer A: the one who placed the order
        self.customer_a = models.Customer.objects.create(
            first_name="Placing", last_name="Customer", display_name="Placing Customer", **common
        )
        # Customer B: another customer linked to campaign
        self.customer_b = models.Customer.objects.create(
            first_name="Campaign", last_name="Customer", display_name="Campaign Customer", **common
        )
        self.order = models.Order.objects.create(
            customer=self.customer_a, status="PAID", currency="BDT", total_amount=150, ordered_at=T0, **common
        )
        self.campaign = models.Campaign.objects.create(
            name="Promo Campaign", **common
        )

        # Edges:
        # 1. Customer A -> Order (PLACED_ORDER)
        models.BusinessRelationship.objects.create(
            business=self.business,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer_a.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="bi.relationship.customer_order.v1",
            relationship_source="DETERMINISTIC",
            created_at=T0,
            updated_at=T0,
        )
        # 2. Campaign -> Order (REPORTED_ORDER)
        models.BusinessRelationship.objects.create(
            business=self.business,
            source_entity_type="CAMPAIGN",
            source_entity_id=self.campaign.pk,
            relationship_type="REPORTED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="bi.relationship.campaign_order.v1",
            relationship_source="REPORTED",
            created_at=T0,
            updated_at=T0,
        )
        # 3. Campaign -> Customer B (REPORTED_CUSTOMER)
        models.BusinessRelationship.objects.create(
            business=self.business,
            source_entity_type="CAMPAIGN",
            source_entity_id=self.campaign.pk,
            relationship_type="REPORTED_CUSTOMER",
            target_entity_type="CUSTOMER",
            target_entity_id=self.customer_b.pk,
            rule_key="bi.relationship.campaign_customer.v1",
            relationship_source="REPORTED",
            created_at=T0,
            updated_at=T0,
        )
        project_business_graph(business_id=self.business.pk)
        self.owner = client_for(make_member(self.business, "OWNER"))

    def test_placing_customer_returned_when_campaign_reports_another_customer(self):
        """build_order_journey must return Customer A (placing customer), not Customer B."""
        oj = build_order_journey(
            business_id=self.business.pk,
            order_id=self.order.pk,
        )
        self.assertIsNotNone(oj.customer_node, "customer_node must not be None")
        self.assertEqual(
            oj.customer_node.entity_id,
            self.customer_a.pk,
            f"Expected customer_node to be Customer A #{self.customer_a.pk}, got #{oj.customer_node.entity_id}",
        )

        # Also verify via the OrderJourney API view
        url = graph_url(self.business.pk, f"journeys/order/{self.order.pk}/")
        res = self.owner.get(url)
        self.assertEqual(res.status_code, 200, res.content)
        customer_node_id = res.json().get("customer_node_id")
        self.assertIsNotNone(customer_node_id)
        # Verify the returned customer node id in API corresponds to Customer A's GraphNode
        customer_a_node = models.GraphNode.objects.get(
            business=self.business, entity_type="CUSTOMER", entity_id=self.customer_a.pk
        )
        self.assertEqual(customer_node_id, customer_a_node.pk)
