"""Requirement-linked tests for Business Graph node and edge projection (Ticket T-013).

Tests verify:
- Canonical entity projection into GraphNode with labels, properties, and timestamps.
- Authoritative BusinessRelationship projection into GraphEdge with direction and confidence.
- Cross-business corruption rejection (GraphCrossBusinessError).
- Unknown or mismatched relationship rules rejection (GraphValidationError).
- SEC-MED-2: Authority derived from rule_key and relationship_source, not metadata.service.
- Expired relationship pruning.
- Idempotent repeated projections.
- Full scoped graph projection.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_graph import projection as subject

D = Decimal
DEFAULT_CONFIDENCE = D("1.0000")
NOW = datetime.now(UTC)
PAST = NOW - timedelta(days=7)
FUTURE = NOW + timedelta(days=7)


class GraphProjectionTestCase(TestCase):
    def setUp(self):
        self.a = models.Business.objects.create(
            name="Store A", slug="store-a", currency="BDT", created_at=PAST, updated_at=PAST,
        )
        self.b = models.Business.objects.create(
            name="Store B", slug="store-b", currency="BDT", created_at=PAST, updated_at=PAST,
        )

    def customer(self, business=None, name="Customer Rahim"):
        return models.Customer.objects.create(
            business=business or self.a, display_name=name,
            created_at=PAST, updated_at=PAST,
        )

    def order(self, customer, business=None):
        return models.Order.objects.create(
            business=business or self.a,
            customer=customer,
            order_number=f"ORD-{models.Order.objects.count() + 1}",
            status="DELIVERED",
            currency="BDT",
            total_amount=D("1250.00"),
            ordered_at=PAST,
            created_at=PAST,
            updated_at=PAST,
        )

    def product(self, business=None, name="Denim Jacket"):
        return models.Product.objects.create(
            business=business or self.a,
            name=name,
            created_at=PAST,
            updated_at=PAST,
        )

    def relationship(
        self,
        *,
        business=None,
        rule_key="customer_order",
        source_type="CUSTOMER",
        source_id=None,
        target_type="ORDER",
        target_id=None,
        rel_type="PLACED_ORDER",
        confidence=DEFAULT_CONFIDENCE,
        source="DETERMINISTIC",
        valid_from=None,
        valid_to=None,
        metadata=None,
    ):
        return models.BusinessRelationship.objects.create(
            business=business or self.a,
            rule_key=rule_key,
            source_entity_type=source_type,
            source_entity_id=source_id,
            relationship_type=rel_type,
            target_entity_type=target_type,
            target_entity_id=target_id,
            confidence=confidence,
            relationship_source=source,
            valid_from=valid_from,
            valid_to=valid_to,
            metadata=metadata or {},
            created_at=PAST,
            updated_at=PAST,
        )

    def test_canonical_entity_node_projection(self):
        cust = self.customer(name="Anika Rahman")
        node, created = subject.project_entity_node(
            business_id=self.a.pk,
            entity_type="CUSTOMER",
            entity_id=cust.pk,
        )

        self.assertTrue(created)
        self.assertEqual(node.business_id, self.a.pk)
        self.assertEqual(node.entity_type, "CUSTOMER")
        self.assertEqual(node.entity_id, cust.pk)
        self.assertEqual(node.label, "Anika Rahman")
        self.assertEqual(node.node_type, "CUSTOMER")

        # Repeated call updates in place without duplicating
        node2, created2 = subject.project_entity_node(
            business_id=self.a.pk,
            entity_type="CUSTOMER",
            entity_id=cust.pk,
        )
        self.assertFalse(created2)
        self.assertEqual(node2.pk, node.pk)
        self.assertEqual(models.GraphNode.objects.filter(business_id=self.a.pk).count(), 1)

    def test_relationship_edge_projection_with_direction_and_confidence(self):
        cust = self.customer()
        ord1 = self.order(cust)

        rel = self.relationship(
            rule_key="customer_order",
            source_type="CUSTOMER",
            source_id=cust.pk,
            target_type="ORDER",
            target_id=ord1.pk,
            rel_type="PLACED_ORDER",
            confidence=D("0.9500"),
        )

        edge, created = subject.project_relationship_edge(
            business_id=self.a.pk,
            relationship=rel,
        )

        self.assertTrue(created)
        self.assertIsNotNone(edge)
        self.assertEqual(edge.business_id, self.a.pk)
        self.assertEqual(edge.source_node.entity_type, "CUSTOMER")
        self.assertEqual(edge.source_node.entity_id, cust.pk)
        self.assertEqual(edge.target_node.entity_type, "ORDER")
        self.assertEqual(edge.target_node.entity_id, ord1.pk)
        self.assertEqual(edge.relationship_type, "PLACED_ORDER")
        self.assertEqual(edge.confidence, D("0.9500"))
        self.assertEqual(edge.business_relationship_id, rel.pk)

        # Repeated projection is idempotent
        edge2, created2 = subject.project_relationship_edge(
            business_id=self.a.pk,
            relationship=rel,
        )
        self.assertFalse(created2)
        self.assertEqual(edge2.pk, edge.pk)
        self.assertEqual(models.GraphEdge.objects.filter(business_id=self.a.pk).count(), 1)

    def test_cross_business_corruption_rejection(self):
        # Customer in Store A, Order in Store B
        cust_a = self.customer(business=self.a)
        ord_b = self.order(cust_a, business=self.b)

        # Malformed relationship claiming to belong to Store A but pointing to Store B order
        rel_cross = self.relationship(
            business=self.a,
            rule_key="customer_order",
            source_type="CUSTOMER",
            source_id=cust_a.pk,
            target_type="ORDER",
            target_id=ord_b.pk,
            rel_type="PLACED_ORDER",
        )

        with self.assertRaises(subject.GraphCrossBusinessError):
            subject.project_relationship_edge(
                business_id=self.a.pk,
                relationship=rel_cross,
            )

    def test_foreign_entity_scope_rejection(self):
        cust_b = self.customer(business=self.b)
        with self.assertRaises(subject.GraphScopeError):
            subject.project_entity_node(
                business_id=self.a.pk,
                entity_type="CUSTOMER",
                entity_id=cust_b.pk,
            )

    def test_unsupported_or_mismatched_rule_rejection(self):
        cust = self.customer()
        ord1 = self.order(cust)

        # Flipped triplet: ORDER -> PLACED_ORDER -> CUSTOMER (violates customer_order rule)
        rel_flipped = self.relationship(
            rule_key="customer_order",
            source_type="ORDER",
            source_id=ord1.pk,
            target_type="CUSTOMER",
            target_id=cust.pk,
            rel_type="PLACED_ORDER",
        )

        with self.assertRaises(subject.GraphValidationError):
            subject.project_relationship_edge(
                business_id=self.a.pk,
                relationship=rel_flipped,
            )

        # Unknown rule_key
        rel_unknown = self.relationship(
            rule_key="unknown_ai_inferred_rule",
            source_type="CUSTOMER",
            source_id=cust.pk,
            target_type="ORDER",
            target_id=ord1.pk,
            rel_type="PLACED_ORDER",
        )

        with self.assertRaises(subject.GraphValidationError):
            subject.project_relationship_edge(
                business_id=self.a.pk,
                relationship=rel_unknown,
            )

    def test_expired_relationship_pruning(self):
        cust = self.customer()
        ord1 = self.order(cust)

        # 1. Project active edge
        rel = self.relationship(
            rule_key="customer_order",
            source_type="CUSTOMER",
            source_id=cust.pk,
            target_type="ORDER",
            target_id=ord1.pk,
            rel_type="PLACED_ORDER",
            valid_to=FUTURE,
        )
        edge, _ = subject.project_relationship_edge(
            business_id=self.a.pk,
            relationship=rel,
        )
        self.assertIsNotNone(edge)
        self.assertEqual(models.GraphEdge.objects.filter(business_id=self.a.pk).count(), 1)

        # 2. Relationship expires: valid_to in the past
        rel.valid_to = PAST
        rel.save()

        # Re-projection prunes the edge
        edge_expired, _ = subject.project_relationship_edge(
            business_id=self.a.pk,
            relationship=rel,
        )
        self.assertIsNone(edge_expired)
        self.assertEqual(models.GraphEdge.objects.filter(business_id=self.a.pk).count(), 0)

    def test_full_business_graph_projection(self):
        cust = self.customer()
        ord1 = self.order(cust)
        prod = self.product()

        self.relationship(
            rule_key="customer_order",
            source_type="CUSTOMER",
            source_id=cust.pk,
            target_type="ORDER",
            target_id=ord1.pk,
            rel_type="PLACED_ORDER",
        )
        self.relationship(
            rule_key="order_product",
            source_type="ORDER",
            source_id=ord1.pk,
            target_type="PRODUCT",
            target_id=prod.pk,
            rel_type="CONTAINS_PRODUCT",
        )

        summary = subject.project_business_graph(business_id=self.a.pk)

        self.assertEqual(summary.business_id, self.a.pk)
        self.assertEqual(summary.total_nodes, 3)  # Customer, Order, Product
        self.assertEqual(summary.total_edges, 2)  # PLACED_ORDER, CONTAINS_PRODUCT
        self.assertEqual(summary.nodes_created, 3)
        self.assertEqual(summary.edges_created, 2)

        # Second projection is idempotent: 0 created, all updated
        summary2 = subject.project_business_graph(business_id=self.a.pk)
        self.assertEqual(summary2.nodes_created, 0)
        self.assertEqual(summary2.nodes_updated, 3)
        self.assertEqual(summary2.edges_created, 0)
        self.assertEqual(summary2.edges_updated, 2)
        self.assertEqual(summary2.total_nodes, 3)
        self.assertEqual(summary2.total_edges, 2)
