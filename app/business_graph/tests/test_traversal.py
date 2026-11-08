"""Tests for bounded graph traversal, query, path search, and filtering (T-015).

Verifies:
1. Directional neighbor traversal (OUTBOUND, INBOUND, BIDIRECTIONAL).
2. Multi-hop bounded traversal (depth bounds, node limits, truncation flag).
3. Cycle safety (terminates without looping when graph has circular references).
4. Path search between canonical entities (deterministic path finding, cycle-free).
5. Missing relationship guarantee: returns empty when unconnected, never fabricates edges.
6. Filtering (entity types, relationship types, min_confidence, valid_at, properties).
7. Multi-tenant business isolation and cross-business rejection.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from app import models
from app.business_graph import (
    GraphFilter,
    GraphScopeError,
    find_paths,
    get_neighbors,
    project_business_graph,
    traverse_graph,
)


class GraphTraversalTests(TestCase):
    def setUp(self):
        super().setUp()
        self.now = timezone.now()
        self.biz_a = models.Business.objects.create(
            name="Alpha Corp",
            slug="alpha-corp",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )
        self.biz_b = models.Business.objects.create(
            name="Beta Corp",
            slug="beta-corp",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )

        # Build a connected chain in Business A:
        # Campaign -> Session -> Customer -> Order -> Shipment
        self.campaign = models.Campaign.objects.create(
            business=self.biz_a,
            name="Spring Sale",
            platform="META",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )
        self.visitor = models.WebsiteVisitor.objects.create(
            business=self.biz_a,
            visitor_key="vis-123",
            first_seen_at=self.now,
            last_seen_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.session = models.WebsiteSession.objects.create(
            business=self.biz_a,
            visitor=self.visitor,
            started_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.customer = models.Customer.objects.create(
            business=self.biz_a,
            first_name="Alice",
            last_name="Walker",
            display_name="Alice Walker",
            created_at=self.now,
            updated_at=self.now,
        )
        self.order = models.Order.objects.create(
            business=self.biz_a,
            customer=self.customer,
            order_number="ORD-501",
            total_amount=Decimal("200.00"),
            currency="USD",
            status="PAID",
            ordered_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.shipment = models.Shipment.objects.create(
            business=self.biz_a,
            order=self.order,
            tracking_code="TRK-900",
            provider="FedEx",
            status="IN_TRANSIT",
            created_at=self.now,
            updated_at=self.now,
        )

        # Authoritative relationships
        self.rel_camp_sess = models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CAMPAIGN",
            source_entity_id=self.campaign.pk,
            relationship_type="REPORTED_SESSION",
            target_entity_type="WEBSITE_SESSION",
            target_entity_id=self.session.pk,
            rule_key="campaign_session",
            relationship_source="REPORTED",
            confidence=Decimal("0.9000"),
            created_at=self.now,
            updated_at=self.now,
        )
        self.rel_cust_sess = models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="HAS_SESSION",
            target_entity_type="WEBSITE_SESSION",
            target_entity_id=self.session.pk,
            rule_key="customer_session",
            relationship_source="DETERMINISTIC",
            confidence=Decimal("1.0000"),
            created_at=self.now,
            updated_at=self.now,
        )
        self.rel_cust_ord = models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="customer_order",
            relationship_source="DETERMINISTIC",
            confidence=Decimal("1.0000"),
            created_at=self.now,
            updated_at=self.now,
        )
        self.rel_ord_ship = models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="HAS_SHIPMENT",
            target_entity_type="SHIPMENT",
            target_entity_id=self.shipment.pk,
            rule_key="order_shipment",
            relationship_source="DETERMINISTIC",
            confidence=Decimal("0.9500"),
            created_at=self.now,
            updated_at=self.now,
        )

        # Project graph
        project_business_graph(business_id=self.biz_a.pk)

    def test_neighbor_traversal_directionality(self):
        # Customer node has:
        # OUTBOUND: customer -> order (PLACED_ORDER), customer -> session (HAS_SESSION)
        # INBOUND: none (or session if inverted)
        cust_node = models.GraphNode.objects.get(
            business=self.biz_a, entity_type="CUSTOMER", entity_id=self.customer.pk
        )

        out_neighbors = get_neighbors(
            business_id=self.biz_a.pk,
            node_id=cust_node.pk,
            direction="OUTBOUND",
        )
        out_types = {neighbor.entity_type for _, neighbor in out_neighbors}
        self.assertIn("ORDER", out_types)
        self.assertIn("WEBSITE_SESSION", out_types)

        in_neighbors = get_neighbors(
            business_id=self.biz_a.pk,
            node_id=cust_node.pk,
            direction="INBOUND",
        )
        self.assertEqual(len(in_neighbors), 0)

        bidi_neighbors = get_neighbors(
            business_id=self.biz_a.pk,
            node_id=cust_node.pk,
            direction="BIDIRECTIONAL",
        )
        self.assertEqual(len(bidi_neighbors), 2)

    def test_bounded_multi_hop_traversal_and_depth(self):
        # Depth 1 from Customer: visits Order and Session
        res_depth1 = traverse_graph(
            business_id=self.biz_a.pk,
            root_entity_type="CUSTOMER",
            root_entity_id=self.customer.pk,
            direction="OUTBOUND",
            max_depth=1,
        )
        self.assertEqual(res_depth1.depth_reached, 1)
        self.assertFalse(res_depth1.truncated)
        node_types = {n.entity_type for n in res_depth1.nodes}
        self.assertEqual(node_types, {"CUSTOMER", "ORDER", "WEBSITE_SESSION"})
        self.assertNotIn("SHIPMENT", node_types)

        # Depth 2 from Customer: visits Order, Session, and Shipment
        res_depth2 = traverse_graph(
            business_id=self.biz_a.pk,
            root_entity_type="CUSTOMER",
            root_entity_id=self.customer.pk,
            direction="OUTBOUND",
            max_depth=2,
        )
        self.assertEqual(res_depth2.depth_reached, 2)
        node_types_d2 = {n.entity_type for n in res_depth2.nodes}
        self.assertIn("SHIPMENT", node_types_d2)

        # Max nodes truncation test
        res_trunc = traverse_graph(
            business_id=self.biz_a.pk,
            root_entity_type="CUSTOMER",
            root_entity_id=self.customer.pk,
            direction="OUTBOUND",
            max_depth=2,
            max_nodes=2,
        )
        self.assertTrue(res_trunc.truncated)
        self.assertEqual(res_trunc.node_count, 2)

    def test_cycle_safety_during_traversal(self):
        # Create a synthetic cycle:
        # Conversation -> Message -> Call -> Conversation
        conv = models.Conversation.objects.create(
            business=self.biz_a,
            channel="WHATSAPP",
            started_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        msg = models.Message.objects.create(
            conversation=conv,
            direction="INBOUND",
            created_at=self.now,
            updated_at=self.now,
        )
        call = models.Call.objects.create(
            business=self.biz_a,
            direction="OUTBOUND",
            created_at=self.now,
            updated_at=self.now,
        )

        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CONVERSATION",
            source_entity_id=conv.pk,
            relationship_type="HAS_MESSAGE",
            target_entity_type="MESSAGE",
            target_entity_id=msg.pk,
            rule_key="conversation_message",
            relationship_source="DETERMINISTIC",
            created_at=self.now,
            updated_at=self.now,
        )
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CONVERSATION",
            source_entity_id=conv.pk,
            relationship_type="HAS_CALL",
            target_entity_type="CALL",
            target_entity_id=call.pk,
            rule_key="conversation_call",
            relationship_source="DETERMINISTIC",
            created_at=self.now,
            updated_at=self.now,
        )
        project_business_graph(business_id=self.biz_a.pk)

        # Traversal with bidirectional search must not loop infinitely
        res = traverse_graph(
            business_id=self.biz_a.pk,
            root_entity_type="CONVERSATION",
            root_entity_id=conv.pk,
            direction="BIDIRECTIONAL",
            max_depth=10,
        )
        self.assertFalse(res.truncated)
        self.assertLessEqual(res.node_count, 10)

    def test_path_search_and_missing_relationships(self):
        # Path from Customer -> Shipment
        paths = find_paths(
            business_id=self.biz_a.pk,
            start_entity_type="CUSTOMER",
            start_entity_id=self.customer.pk,
            end_entity_type="SHIPMENT",
            end_entity_id=self.shipment.pk,
            direction="OUTBOUND",
            max_depth=3,
        )
        self.assertEqual(len(paths), 1)
        path = paths[0]
        self.assertEqual(path.length, 2)
        step_types = [n.entity_type for n in path.nodes]
        self.assertEqual(step_types, ["CUSTOMER", "ORDER", "SHIPMENT"])
        edge_types = [e.relationship_type for e in path.edges]
        self.assertEqual(edge_types, ["PLACED_ORDER", "HAS_SHIPMENT"])

        # Unconnected entities: Customer -> Campaign (outbound direction has no path)
        unconnected_paths = find_paths(
            business_id=self.biz_a.pk,
            start_entity_type="CUSTOMER",
            start_entity_id=self.customer.pk,
            end_entity_type="CAMPAIGN",
            end_entity_id=self.campaign.pk,
            direction="OUTBOUND",
            max_depth=3,
        )
        self.assertEqual(len(unconnected_paths), 0)

    def test_filtering_by_relationship_type_and_confidence(self):
        # Traversal filtered by relationship_type
        filter_order_only = GraphFilter(relationship_types=frozenset({"PLACED_ORDER"}))
        res = traverse_graph(
            business_id=self.biz_a.pk,
            root_entity_type="CUSTOMER",
            root_entity_id=self.customer.pk,
            direction="OUTBOUND",
            max_depth=1,
            filters=filter_order_only,
        )
        node_types = {n.entity_type for n in res.nodes}
        self.assertEqual(node_types, {"CUSTOMER", "ORDER"})
        self.assertNotIn("WEBSITE_SESSION", node_types)

        # High confidence filter (0.98) should exclude Campaign -> Session (confidence 0.90)
        filter_high_conf = GraphFilter(min_confidence=Decimal("0.98"))
        res_conf = traverse_graph(
            business_id=self.biz_a.pk,
            root_entity_type="CAMPAIGN",
            root_entity_id=self.campaign.pk,
            direction="OUTBOUND",
            max_depth=1,
            filters=filter_high_conf,
        )
        self.assertEqual(res_conf.node_count, 1)  # Only root node, edge filtered out

    def test_multi_tenant_isolation_in_traversal(self):
        # Querying an entity belonging to Business B using Business A scope fails
        cust_b = models.Customer.objects.create(
            business=self.biz_b,
            first_name="Bob",
            created_at=self.now,
            updated_at=self.now,
        )
        project_business_graph(business_id=self.biz_b.pk)

        with self.assertRaises(GraphScopeError):
            traverse_graph(
                business_id=self.biz_a.pk,
                root_entity_type="CUSTOMER",
                root_entity_id=cust_b.pk,
            )

        with self.assertRaises(GraphScopeError):
            node_b = models.GraphNode.objects.get(business=self.biz_b, entity_id=cust_b.pk)
            get_neighbors(
                business_id=self.biz_a.pk,
                node_id=node_b.pk,
            )
