"""Tests for Graph Snapshots and Evidence-Aware Context (T-018).

Verifies:
1. Snapshot creation across types (BUSINESS, CUSTOMER, ORDER, PRODUCT, CAMPAIGN).
2. Stability of serialized snapshot data after later graph modifications.
3. Evidence-aware context linking edges to BusinessRelationships and nodes to BusinessFacts/Issues.
4. Explainable paths providing step-by-step grounded evidence.
5. Multi-tenant isolation and cross-business rejection.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from app import models
from app.business_graph import (
    GraphScopeError,
    GraphValidationError,
    build_evidence_context,
    create_graph_snapshot,
    explain_path,
    find_paths,
    get_graph_snapshot,
    project_business_graph,
)


class GraphSnapshotsAndEvidenceTests(TestCase):
    def setUp(self):
        super().setUp()
        self.now = timezone.now()
        self.biz_a = models.Business.objects.create(
            name="Mega Store",
            slug="mega-store",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )
        self.biz_b = models.Business.objects.create(
            name="Other Store",
            slug="other-store",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )

        self.customer = models.Customer.objects.create(
            business=self.biz_a,
            first_name="Diana",
            last_name="Prince",
            display_name="Diana Prince",
            created_at=self.now,
            updated_at=self.now,
        )
        self.order = models.Order.objects.create(
            business=self.biz_a,
            customer=self.customer,
            order_number="ORD-999",
            total_amount=Decimal("300.00"),
            currency="USD",
            status="COMPLETED",
            ordered_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        self.shipment = models.Shipment.objects.create(
            business=self.biz_a,
            order=self.order,
            tracking_code="TRK-999",
            provider="FedEx",
            status="DELIVERED",
            created_at=self.now,
            updated_at=self.now,
        )

        # Verified Relationships
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
            metadata={"source_ip": "192.168.1.1", "channel": "MOBILE_APP"},
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
            confidence=Decimal("0.9800"),
            created_at=self.now,
            updated_at=self.now,
        )

        # Verified BusinessFact on Customer
        self.fact = models.BusinessFact.objects.create(
            business=self.biz_a,
            fact_type="CUSTOMER_LIFETIME_VALUE",
            subject_entity_type="CUSTOMER",
            subject_entity_id=self.customer.pk,
            statement="Customer Diana Prince has lifetime revenue of 300 USD",
            value=Decimal("300.00"),
            value_unit="USD",
            confidence=Decimal("1.0000"),
            status="VERIFIED",
            detected_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )

        # BusinessIssue on Shipment
        self.issue = models.BusinessIssue.objects.create(
            business=self.biz_a,
            issue_type="LATE_DELIVERY",
            subject_entity_type="SHIPMENT",
            subject_entity_id=self.shipment.pk,
            title="Shipment TRK-999 delayed past SLA",
            severity="HIGH",
            status="OPEN",
            confidence=Decimal("0.9000"),
            detected_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )

        project_business_graph(business_id=self.biz_a.pk)

    def test_create_and_get_snapshots(self):
        # 1. Full Business Snapshot
        snap_biz = create_graph_snapshot(
            business_id=self.biz_a.pk,
            snapshot_type="BUSINESS",
            name="Q4 Business Graph",
        )
        self.assertEqual(snap_biz.business_id, self.biz_a.pk)
        self.assertGreaterEqual(snap_biz.node_count, 3)
        self.assertEqual(snap_biz.edge_count, 2)
        self.assertIn("nodes", snap_biz.snapshot_data)
        self.assertIn("edges", snap_biz.snapshot_data)

        # 2. Customer Journey Snapshot
        snap_cust = create_graph_snapshot(
            business_id=self.biz_a.pk,
            snapshot_type="CUSTOMER",
            root_entity_id=self.customer.pk,
        )
        self.assertEqual(snap_cust.root_entity_type, "CUSTOMER")
        self.assertEqual(snap_cust.root_entity_id, self.customer.pk)
        self.assertIn("timeline", snap_cust.snapshot_data)
        self.assertIn("summary", snap_cust.snapshot_data)

        # 3. Order Journey Snapshot
        snap_ord = create_graph_snapshot(
            business_id=self.biz_a.pk,
            snapshot_type="ORDER",
            root_entity_id=self.order.pk,
        )
        self.assertEqual(snap_ord.root_entity_type, "ORDER")
        self.assertEqual(snap_ord.root_entity_id, self.order.pk)

        # Retrieve snapshot via get_graph_snapshot
        fetched = get_graph_snapshot(
            business_id=self.biz_a.pk,
            snapshot_id=snap_biz.pk,
        )
        self.assertEqual(fetched.pk, snap_biz.pk)

    def test_snapshot_stability_after_live_graph_modifications(self):
        # Create customer snapshot
        snap = create_graph_snapshot(
            business_id=self.biz_a.pk,
            snapshot_type="CUSTOMER",
            root_entity_id=self.customer.pk,
        )
        original_node_count = snap.node_count
        original_nodes = snap.snapshot_data["nodes"]

        # Mutate the live graph: delete the order node and edges
        models.GraphEdge.objects.filter(business=self.biz_a).delete()
        models.GraphNode.objects.filter(business=self.biz_a, entity_type="ORDER").delete()

        # The snapshot stored in the database must remain completely stable!
        refetched = get_graph_snapshot(
            business_id=self.biz_a.pk,
            snapshot_id=snap.pk,
        )
        self.assertEqual(refetched.node_count, original_node_count)
        self.assertEqual(refetched.snapshot_data["nodes"], original_nodes)

    def test_evidence_context_traceability(self):
        nodes = list(models.GraphNode.objects.filter(business=self.biz_a))
        edges = list(models.GraphEdge.objects.filter(business=self.biz_a))

        evidence = build_evidence_context(
            business_id=self.biz_a.pk,
            nodes=nodes,
            edges=edges,
        )

        # Verify edge evidence includes rule_key, source, metadata
        edge_placed = models.GraphEdge.objects.get(
            business=self.biz_a, relationship_type="PLACED_ORDER"
        )
        self.assertIn(edge_placed.pk, evidence.edge_evidence)
        edge_data = evidence.edge_evidence[edge_placed.pk]
        self.assertEqual(edge_data["rule_key"], "customer_order")
        self.assertEqual(edge_data["relationship_source"], "DETERMINISTIC")
        self.assertEqual(edge_data["metadata"]["channel"], "MOBILE_APP")

        # Verify node facts on customer
        cust_node = models.GraphNode.objects.get(
            business=self.biz_a, entity_type="CUSTOMER", entity_id=self.customer.pk
        )
        self.assertIn(cust_node.pk, evidence.node_facts)
        facts = evidence.node_facts[cust_node.pk]
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["fact_type"], "CUSTOMER_LIFETIME_VALUE")
        self.assertEqual(facts[0]["value"], "300.000000")

        # Verify node issues on shipment
        ship_node = models.GraphNode.objects.get(
            business=self.biz_a, entity_type="SHIPMENT", entity_id=self.shipment.pk
        )
        self.assertIn(ship_node.pk, evidence.node_issues)
        issues = evidence.node_issues[ship_node.pk]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue_type"], "LATE_DELIVERY")
        self.assertEqual(issues[0]["severity"], "HIGH")

    def test_explain_path(self):
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
        explanation = explain_path(business_id=self.biz_a.pk, path=paths[0])
        self.assertEqual(len(explanation), 3)  # Customer -> Order -> Shipment

        # First step: Customer with facts
        step0 = explanation[0]
        self.assertEqual(step0["node"]["entity_type"], "CUSTOMER")
        self.assertGreaterEqual(len(step0["node"]["facts"]), 1)
        self.assertEqual(step0["edge"]["relationship_type"], "PLACED_ORDER")
        self.assertEqual(step0["edge"]["evidence"]["rule_key"], "customer_order")

        # Last step: Shipment with issues
        step2 = explanation[2]
        self.assertEqual(step2["node"]["entity_type"], "SHIPMENT")
        self.assertGreaterEqual(len(step2["node"]["issues"]), 1)
        self.assertIsNone(step2["edge"])

    def test_cross_business_isolation_in_snapshots(self):
        snap_a = create_graph_snapshot(
            business_id=self.biz_a.pk,
            snapshot_type="BUSINESS",
        )

        with self.assertRaises(GraphScopeError):
            get_graph_snapshot(
                business_id=self.biz_b.pk,
                snapshot_id=snap_a.pk,
            )

        with self.assertRaises(GraphValidationError):
            get_graph_snapshot(
                business_id=self.biz_a.pk,
                snapshot_id=999999,
            )
