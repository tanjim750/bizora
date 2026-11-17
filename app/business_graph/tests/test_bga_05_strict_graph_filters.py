"""BGA-05: Strict filter validation for entity types, relationship types,
paired entity_type/entity_id in queries, lowercase relationship_type handling,
and filter application/persistence in BUSINESS snapshots.
"""

from datetime import datetime, timezone
from django.test import TestCase

from app import models
from app.business_graph import project_business_graph
from app.business_graph.snapshots import create_graph_snapshot
from app.business_graph.traversal import GraphFilter
from app.tests.bi_graph_helpers import client_for, graph_url, make_member

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


class StrictGraphFiltersTests(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Filter Test Shop",
            slug="filter-test-shop",
            currency="BDT",
            created_at=T0,
            updated_at=T0,
        )
        common = {"business": self.business, "created_at": T0, "updated_at": T0}
        self.customer = models.Customer.objects.create(
            first_name="Sadia", last_name="Afrin", display_name="Sadia Afrin", **common
        )
        self.order = models.Order.objects.create(
            customer=self.customer, status="PAID", currency="BDT", total_amount=50, ordered_at=T0, **common
        )
        models.BusinessRelationship.objects.create(
            business=self.business,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="bi.relationship.customer_order.v1",
            relationship_source="DETERMINISTIC",
            created_at=T0,
            updated_at=T0,
        )
        project_business_graph(business_id=self.business.pk)
        self.owner = client_for(make_member(self.business, "OWNER"))

    def url(self, tail):
        return graph_url(self.business.pk, tail)

    def test_bogus_entity_types_rejected(self):
        """Bogus entity_types in query filters must return 400 INVALID_DATA instead of being ignored."""
        res = self.owner.get(self.url(f"traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}&entity_types=BOGUS"))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json().get("code"), "INVALID_DATA")

        res_comma = self.owner.get(self.url(f"query/?entity_types=CUSTOMER,INVALID_TYPE"))
        self.assertEqual(res_comma.status_code, 400, res_comma.content)
        self.assertEqual(res_comma.json().get("code"), "INVALID_DATA")

    def test_bogus_relationship_types_rejected(self):
        """Bogus relationship_types in query filters must return 400 INVALID_DATA instead of being ignored."""
        res = self.owner.get(self.url(f"traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}&relationship_types=BOGUS_REL"))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json().get("code"), "INVALID_DATA")

        res_comma = self.owner.get(self.url("query/?relationship_types=PLACED_ORDER,INVALID_REL"))
        self.assertEqual(res_comma.status_code, 400, res_comma.content)
        self.assertEqual(res_comma.json().get("code"), "INVALID_DATA")

    def test_lowercase_relationship_type_returns_matches(self):
        """Lowercase relationship_type in query/ should be uppercased and find matching edges."""
        res = self.owner.get(self.url("query/?relationship_type=placed_order"))
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["edge_count"], 1)
        self.assertEqual(res.json()["edges"][0]["relationship_type"], "PLACED_ORDER")

    def test_unpaired_entity_type_or_entity_id_rejected(self):
        """In query/, providing entity_type without entity_id or vice versa must return 400, not whole graph."""
        res_type_only = self.owner.get(self.url("query/?entity_type=CUSTOMER"))
        self.assertEqual(res_type_only.status_code, 400, res_type_only.content)
        self.assertEqual(res_type_only.json().get("code"), "INVALID_DATA")

        res_id_only = self.owner.get(self.url(f"query/?entity_id={self.customer.pk}"))
        self.assertEqual(res_id_only.status_code, 400, res_id_only.content)
        self.assertEqual(res_id_only.json().get("code"), "INVALID_DATA")

        res_bogus_type = self.owner.get(self.url(f"query/?entity_type=BOGUS&entity_id={self.customer.pk}"))
        self.assertEqual(res_bogus_type.status_code, 400, res_bogus_type.content)
        self.assertEqual(res_bogus_type.json().get("code"), "INVALID_DATA")

    def test_business_snapshot_applies_and_saves_filters(self):
        """BUSINESS snapshot must filter nodes/edges by provided filters and persist time filters."""
        snap = create_graph_snapshot(
            business_id=self.business.pk,
            snapshot_type="BUSINESS",
            filters=GraphFilter(
                entity_types=frozenset({"ORDER"}),
                time_from=T0,
                valid_at=T0,
            ),
        )
        # Snapshot must only have ORDER nodes
        node_types = {n["entity_type"] for n in snap.snapshot_data["nodes"]}
        self.assertEqual(node_types, {"ORDER"})
        self.assertEqual(snap.node_count, 1)

        # Stored filters must record time_from and valid_at
        self.assertIsNotNone(snap.filters)
        self.assertIn("time_from", snap.filters)
        self.assertIn("valid_at", snap.filters)
        self.assertEqual(snap.filters["entity_types"], ["ORDER"])
