"""Tests for Business Graph synchronization, pruning, and full rebuild (T-014).

Verifies:
1. Incremental entity synchronization (upsert, update, delete).
2. Incremental relationship synchronization (upsert, delete).
3. Stale projection cleanup when canonical entities or relationships are deleted.
4. Pruning of expired relationships.
5. Full rebuild idempotency and clean mode.
6. Multi-tenant isolation and cross-business rejection.
7. Error handling on invalid actions or nonexistent entities.
"""

from decimal import Decimal
import datetime

from django.test import TestCase
from django.utils import timezone

from app import models
from app.business_graph import (
    GraphCrossBusinessError,
    GraphScopeError,
    GraphValidationError,
    prune_stale_projections,
    rebuild_business_graph,
    sync_entity_node,
    sync_relationship_edge,
)


class BusinessGraphSyncTests(TestCase):
    def setUp(self):
        super().setUp()
        self.now = timezone.now()
        self.biz_a = models.Business.objects.create(
            name="Retailer Alpha",
            slug="retailer-alpha",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )
        self.biz_b = models.Business.objects.create(
            name="Retailer Beta",
            slug="retailer-beta",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )

        self.customer_a = models.Customer.objects.create(
            business=self.biz_a,
            first_name="Jane",
            last_name="Doe",
            display_name="Jane Doe",
            created_at=self.now,
            updated_at=self.now,
        )
        self.order_a = models.Order.objects.create(
            business=self.biz_a,
            customer=self.customer_a,
            order_number="ORD-1001",
            total_amount=Decimal("150.00"),
            currency="USD",
            status="CONFIRMED",
            ordered_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )

        self.rel_a = models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer_a.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order_a.pk,
            rule_key="customer_order",
            relationship_source="DETERMINISTIC",
            confidence=Decimal("1.0000"),
            created_at=self.now,
            updated_at=self.now,
        )

    def test_sync_entity_node_upsert_and_delete(self):
        # 1. Upsert: creates GraphNode
        node, created = sync_entity_node(
            business_id=self.biz_a.pk,
            entity_type="CUSTOMER",
            entity_id=self.customer_a.pk,
            action="upsert",
        )
        self.assertTrue(created)
        self.assertIsNotNone(node)
        self.assertEqual(node.label, "Jane Doe")

        # 2. Update canonical customer and re-sync
        self.customer_a.display_name = "Jane Smith"
        self.customer_a.save()
        node2, created2 = sync_entity_node(
            business_id=self.biz_a.pk,
            entity_type="CUSTOMER",
            entity_id=self.customer_a.pk,
            action="upsert",
        )
        self.assertFalse(created2)
        self.assertEqual(node2.pk, node.pk)
        self.assertEqual(node2.label, "Jane Smith")

        # 3. Delete action: deletes node and associated edges
        sync_relationship_edge(
            business_id=self.biz_a.pk,
            relationship_id=self.rel_a.pk,
            action="upsert",
        )
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 1)

        del_node, was_deleted = sync_entity_node(
            business_id=self.biz_a.pk,
            entity_type="CUSTOMER",
            entity_id=self.customer_a.pk,
            action="delete",
        )
        self.assertIsNone(del_node)
        self.assertTrue(was_deleted)
        self.assertFalse(
            models.GraphNode.objects.filter(
                business=self.biz_a,
                entity_type="CUSTOMER",
                entity_id=self.customer_a.pk,
            ).exists()
        )
        # Connected edge must also be removed
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 0)

    def test_sync_relationship_edge_upsert_and_delete(self):
        # 1. Upsert edge
        edge, created = sync_relationship_edge(
            business_id=self.biz_a.pk,
            relationship_id=self.rel_a.pk,
            action="upsert",
        )
        self.assertTrue(created)
        self.assertIsNotNone(edge)
        self.assertEqual(edge.relationship_type, "PLACED_ORDER")
        self.assertEqual(edge.source_node.entity_id, self.customer_a.pk)
        self.assertEqual(edge.target_node.entity_id, self.order_a.pk)

        # 2. Delete edge
        edge_del, deleted = sync_relationship_edge(
            business_id=self.biz_a.pk,
            relationship_id=self.rel_a.pk,
            action="delete",
        )
        self.assertIsNone(edge_del)
        self.assertTrue(deleted)
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 0)

    def test_prune_stale_projections_canonical_entity_deleted(self):
        # Initial projection
        sync_entity_node(
            business_id=self.biz_a.pk,
            entity_type="CUSTOMER",
            entity_id=self.customer_a.pk,
        )
        sync_entity_node(
            business_id=self.biz_a.pk,
            entity_type="ORDER",
            entity_id=self.order_a.pk,
        )
        sync_relationship_edge(
            business_id=self.biz_a.pk,
            relationship_id=self.rel_a.pk,
        )
        self.assertEqual(models.GraphNode.objects.filter(business=self.biz_a).count(), 2)
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 1)

        # Delete canonical order directly in DB
        self.order_a.delete()

        prune_res = prune_stale_projections(business_id=self.biz_a.pk)
        self.assertEqual(prune_res.stale_nodes_pruned, 1)
        self.assertEqual(prune_res.stale_edges_pruned, 1)

        self.assertFalse(
            models.GraphNode.objects.filter(
                business=self.biz_a,
                entity_type="ORDER",
            ).exists()
        )
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 0)
        # Customer node should remain
        self.assertTrue(
            models.GraphNode.objects.filter(
                business=self.biz_a,
                entity_type="CUSTOMER",
            ).exists()
        )

    def test_prune_stale_projections_expired_and_deleted_relationships(self):
        sync_relationship_edge(
            business_id=self.biz_a.pk,
            relationship_id=self.rel_a.pk,
        )
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 1)

        # Expire the relationship
        self.rel_a.valid_to = self.now - datetime.timedelta(hours=1)
        self.rel_a.save()

        # Update edge's valid_to as well to simulate pre-expiry projection
        models.GraphEdge.objects.filter(business_relationship=self.rel_a).update(valid_to=self.rel_a.valid_to)

        prune_res = prune_stale_projections(business_id=self.biz_a.pk)
        self.assertEqual(prune_res.stale_edges_pruned, 1)
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 0)

        # Test deleted relationship directly
        self.rel_a.valid_to = None
        self.rel_a.save()
        sync_relationship_edge(
            business_id=self.biz_a.pk,
            relationship_id=self.rel_a.pk,
        )
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 1)

        self.rel_a.delete()
        prune_res2 = prune_stale_projections(business_id=self.biz_a.pk)
        self.assertEqual(prune_res2.stale_edges_pruned, 1)
        self.assertEqual(models.GraphEdge.objects.filter(business=self.biz_a).count(), 0)

    def test_rebuild_business_graph_idempotency_and_clean_mode(self):
        # 1. Standard rebuild
        res1 = rebuild_business_graph(business_id=self.biz_a.pk, clean=False)
        self.assertGreaterEqual(res1.nodes_created, 2)
        self.assertEqual(res1.edges_created, 1)

        # 2. Idempotent replay: nodes_updated, 0 created
        res2 = rebuild_business_graph(business_id=self.biz_a.pk, clean=False)
        self.assertEqual(res2.nodes_created, 0)
        self.assertEqual(res2.edges_created, 0)
        self.assertEqual(res2.total_nodes, res1.total_nodes)
        self.assertEqual(res2.total_edges, res1.total_edges)

        # 3. Clean rebuild: wipes and rebuilds
        res3 = rebuild_business_graph(business_id=self.biz_a.pk, clean=True)
        self.assertEqual(res3.nodes_pruned, res1.total_nodes)
        self.assertEqual(res3.edges_pruned, res1.total_edges)
        self.assertEqual(res3.total_nodes, res1.total_nodes)
        self.assertEqual(res3.total_edges, res1.total_edges)

    def test_cross_business_isolation_in_sync_and_rebuild(self):
        # Attempting to sync Business B entity using Business A scope fails
        cust_b = models.Customer.objects.create(
            business=self.biz_b,
            first_name="Bob",
            created_at=self.now,
            updated_at=self.now,
        )
        with self.assertRaises(GraphScopeError):
            sync_entity_node(
                business_id=self.biz_a.pk,
                entity_type="CUSTOMER",
                entity_id=cust_b.pk,
            )

        # Attempting to sync cross-business relationship fails
        rel_cross = models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=cust_b.pk,  # B's customer in A's relationship
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order_a.pk,
            rule_key="customer_order",
            relationship_source="DETERMINISTIC",
            created_at=self.now,
            updated_at=self.now,
        )
        with self.assertRaises(GraphCrossBusinessError):
            sync_relationship_edge(
                business_id=self.biz_a.pk,
                relationship_id=rel_cross.pk,
            )

    def test_validation_errors_on_invalid_actions_and_missing_scopes(self):
        with self.assertRaises(GraphValidationError):
            sync_entity_node(
                business_id=self.biz_a.pk,
                entity_type="CUSTOMER",
                entity_id=self.customer_a.pk,
                action="invalid_action",
            )

        with self.assertRaises(GraphValidationError):
            sync_relationship_edge(
                business_id=self.biz_a.pk,
                relationship_id=999999,
                action="upsert",
            )

        with self.assertRaises(GraphScopeError):
            rebuild_business_graph(business_id=999999)
