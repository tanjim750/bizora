"""Tests for Card BGA-03: truncated traversal returns only edges whose endpoints are in nodes."""

from datetime import datetime, timezone

from django.test import TestCase

from app import models
from app.business_graph import traverse_graph

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


class TruncatedTraversalEdgesTests(TestCase):
    def setUp(self):
        super().setUp()
        self.biz = models.Business.objects.create(
            name="Traversal Hub Biz",
            slug="traversal-hub-biz",
            currency="BDT",
            created_at=T0,
            updated_at=T0,
        )

        # Root hub node (Customer)
        self.hub_node = models.GraphNode.objects.create(
            business_id=self.biz.pk,
            entity_type="CUSTOMER",
            entity_id=1,
            label="Hub Customer",
            first_seen_at=T0,
            last_seen_at=T0,
            created_at=T0,
            updated_at=T0,
        )

        # 20 neighbor nodes (Orders) with edges from hub to each neighbor
        self.neighbor_nodes = []
        self.edges = []
        for i in range(1, 21):
            n_node = models.GraphNode.objects.create(
                business_id=self.biz.pk,
                entity_type="ORDER",
                entity_id=100 + i,
                label=f"Order #{100 + i}",
                first_seen_at=T0,
                last_seen_at=T0,
                created_at=T0,
                updated_at=T0,
            )
            self.neighbor_nodes.append(n_node)

            edge = models.GraphEdge.objects.create(
                business_id=self.biz.pk,
                source_node=self.hub_node,
                target_node=n_node,
                relationship_type="PLACED_ORDER",
                confidence=1.0,
                created_at=T0,
                updated_at=T0,
            )
            self.edges.append(edge)

    def test_truncated_traversal_contains_no_dangling_edges(self):
        """Card BGA-03: Hub with 20 neighbours, max_nodes=5: every edge endpoint inside nodes."""
        result = traverse_graph(
            business_id=self.biz.pk,
            root_entity_type="CUSTOMER",
            root_entity_id=self.hub_node.entity_id,
            direction="OUTBOUND",
            max_depth=1,
            max_nodes=5,
        )

        self.assertTrue(result.truncated, "Expected result.truncated to be True")
        self.assertEqual(len(result.nodes), 5)

        visited_node_ids = {n.pk for n in result.nodes}

        # Invariant: Every edge returned must have both endpoints in result.nodes
        for edge in result.edges:
            self.assertIn(
                edge.source_node_id,
                visited_node_ids,
                f"Edge {edge.pk} source {edge.source_node_id} not in visited nodes",
            )
            self.assertIn(
                edge.target_node_id,
                visited_node_ids,
                f"Edge {edge.pk} target {edge.target_node_id} not in visited nodes",
            )

        # There are 5 nodes visited (1 root + 4 neighbors), so there should be exactly 4 valid edges
        self.assertEqual(
            len(result.edges),
            4,
            f"Expected exactly 4 edges connecting the 5 visited nodes, got {len(result.edges)}",
        )
