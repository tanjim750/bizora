"""BG-03: relationships written by Business Intelligence must project into Graph edges."""

from datetime import datetime, timezone
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from app import models
from app.business_graph import (
    PROJECTABLE_RULE_KEYS,
    SUPPORTED_RELATIONSHIP_RULES,
    canonical_rule_name,
    project_business_graph,
    rebuild_business_graph,
)
from app.business_intelligence import rebuild_relationships
from app.business_intelligence.relationships import RULES
from app.tests.bi_graph_helpers import client_for, graph_url, intelligence_url, make_member

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


class RuleTableAlignmentTests(SimpleTestCase):
    def test_graph_rule_table_matches_the_business_intelligence_registry(self):
        self.assertEqual(
            {name: (r.source_type, r.relationship_type, r.target_type) for name, r in RULES.items()},
            SUPPORTED_RELATIONSHIP_RULES,
        )
        for name, rule in RULES.items():
            with self.subTest(rule=name):
                self.assertIn(rule.key, PROJECTABLE_RULE_KEYS)
                self.assertEqual(canonical_rule_name(rule.key), name)
                self.assertEqual(canonical_rule_name(name), name)

    def test_unknown_keys_are_not_projectable(self):
        for key in ("demo.attribution.v1", "bi.relationship.nope.v1", "bi.relationship.customer_order.v2", "", None):
            with self.subTest(key=key):
                self.assertNotIn(canonical_rule_name(key), SUPPORTED_RELATIONSHIP_RULES)
                self.assertNotIn(key, PROJECTABLE_RULE_KEYS)


class BusinessIntelligenceToGraphTests(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Hand-off shop", slug="hand-off-shop", currency="BDT", created_at=T0, updated_at=T0
        )
        common = {"business": self.business, "created_at": T0, "updated_at": T0}
        self.customer = models.Customer.objects.create(first_name="Rina", last_name="Das", display_name="Rina Das", **common)
        self.product = models.Product.objects.create(name="Tea", **common)
        self.order = models.Order.objects.create(customer=self.customer, order_number="HO-1", total_amount=Decimal("20.00"),
                                                  currency="BDT", status="PAID", ordered_at=T0, **common)
        models.OrderItem.objects.create(order=self.order, product=self.product, product_name="Tea", unit_price=Decimal("20.00"),
                                        total_amount=Decimal("20.00"), created_at=T0)
        self.payment = models.Payment.objects.create(order=self.order, customer=self.customer, amount=Decimal("20.00"), **common)

    def test_relationships_written_by_bi_become_graph_edges(self):
        result = rebuild_relationships(business_id=self.business.pk)
        self.assertGreaterEqual(result.created, 3)
        rows = models.BusinessRelationship.objects.filter(business=self.business)
        self.assertTrue(all(row.rule_key.startswith("bi.relationship.") for row in rows))

        summary = project_business_graph(business_id=self.business.pk)
        self.assertEqual(summary.total_edges, rows.count())
        self.assertEqual(models.GraphEdge.objects.filter(business=self.business).count(), rows.count())
        self.assertEqual(
            set(models.GraphEdge.objects.filter(business=self.business).values_list("relationship_type", flat=True)),
            {"PLACED_ORDER", "CONTAINS_PRODUCT", "HAS_PAYMENT"},
        )

    def test_rebuild_is_idempotent_and_a_clean_rebuild_recreates_the_same_edges(self):
        rebuild_relationships(business_id=self.business.pk)
        first = rebuild_business_graph(business_id=self.business.pk, clean=False)
        again = rebuild_business_graph(business_id=self.business.pk, clean=False)
        clean = rebuild_business_graph(business_id=self.business.pk, clean=True)
        self.assertEqual((first.edges_created, first.total_edges), (3, 3))
        self.assertEqual((again.edges_created, again.edges_pruned, again.total_edges), (0, 0, 3))
        self.assertEqual((clean.edges_created, clean.total_edges), (3, 3))

    def test_pipeline_then_rebuild_then_traversal_over_http(self):
        owner = client_for(make_member(self.business, "OWNER"))
        self.assertEqual(owner.post(intelligence_url(self.business.pk, "pipeline/run/"), {}).status_code, 200)
        rebuilt = owner.post(graph_url(self.business.pk, "rebuild/"), {"clean": False})
        self.assertEqual(rebuilt.status_code, 200)
        self.assertEqual(rebuilt.json()["total_edges"], 3)

        traversal = owner.get(
            graph_url(self.business.pk, f"traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}&max_depth=2")
        )
        self.assertEqual(traversal.status_code, 200)
        data = traversal.json()
        self.assertEqual(data["edge_count"], 3)
        self.assertEqual({n["entity_type"] for n in data["nodes"]}, {"CUSTOMER", "ORDER", "PRODUCT", "PAYMENT"})
