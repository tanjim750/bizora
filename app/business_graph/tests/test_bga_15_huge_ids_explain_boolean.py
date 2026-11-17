"""BGA-15: Entity IDs above 2**63-1 must return 400 instead of OverflowError 500;
explain parameter in path search must use a strict boolean set instead of silently evaluating invalid strings to false.
"""

from datetime import datetime, timezone
from django.test import TestCase

from app import models
from app.business_graph import project_business_graph
from app.tests.bi_graph_helpers import client_for, graph_url, make_member

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
HUGE_ID = 2**63  # 9223372036854775808 (exceeds signed 64-bit bigint)


class HugeIdsAndExplainBooleanTests(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Graph Limits Co",
            slug="graph-limits-co",
            currency="BDT",
            created_at=T0,
            updated_at=T0,
        )
        common = {"business": self.business, "created_at": T0, "updated_at": T0}
        self.customer = models.Customer.objects.create(
            first_name="Rahim", last_name="Uddin", display_name="Rahim Uddin", **common
        )
        self.order = models.Order.objects.create(
            customer=self.customer, status="PAID", currency="BDT", total_amount=100, ordered_at=T0, **common
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

    def test_huge_entity_id_returns_400(self):
        """Entity IDs exceeding 2**63-1 must return 400 INVALID_DATA, not 500 OverflowError."""
        # 1. Traversal root_entity_id
        res_traversal = self.owner.get(
            self.url(f"traversal/?root_entity_type=CUSTOMER&root_entity_id={HUGE_ID}")
        )
        self.assertEqual(res_traversal.status_code, 400, res_traversal.content)
        self.assertEqual(res_traversal.json().get("code"), "INVALID_DATA")

        # 2. Path search start_entity_id and end_entity_id
        res_path_start = self.owner.get(
            self.url(f"paths/?start_entity_type=CUSTOMER&start_entity_id={HUGE_ID}&end_entity_type=ORDER&end_entity_id={self.order.pk}")
        )
        self.assertEqual(res_path_start.status_code, 400, res_path_start.content)
        self.assertEqual(res_path_start.json().get("code"), "INVALID_DATA")

        res_path_end = self.owner.get(
            self.url(f"paths/?start_entity_type=CUSTOMER&start_entity_id={self.customer.pk}&end_entity_type=ORDER&end_entity_id={HUGE_ID}")
        )
        self.assertEqual(res_path_end.status_code, 400, res_path_end.content)
        self.assertEqual(res_path_end.json().get("code"), "INVALID_DATA")

        # 3. Query subgraph entity_id
        res_query = self.owner.get(
            self.url(f"query/?entity_type=CUSTOMER&entity_id={HUGE_ID}")
        )
        self.assertEqual(res_query.status_code, 400, res_query.content)
        self.assertEqual(res_query.json().get("code"), "INVALID_DATA")

        # 4. Snapshots create root_entity_id
        res_snapshot = self.owner.post(
            self.url("snapshots/"),
            {"snapshot_type": "CUSTOMER", "root_entity_id": HUGE_ID},
        )
        self.assertEqual(res_snapshot.status_code, 400, res_snapshot.content)
        self.assertEqual(res_snapshot.json().get("code"), "INVALID_DATA")

        # 5. Journey URL parameter customer_id
        res_journey = self.owner.get(
            self.url(f"journeys/customer/{HUGE_ID}/")
        )
        self.assertEqual(res_journey.status_code, 400, res_journey.content)
        self.assertEqual(res_journey.json().get("code"), "INVALID_DATA")

    def test_explain_requires_strict_boolean_set(self):
        """explain query parameter must strictly accept boolean values and reject invalid values with 400."""
        pair = f"start_entity_type=CUSTOMER&start_entity_id={self.customer.pk}&end_entity_type=ORDER&end_entity_id={self.order.pk}"

        # Invalid booleans like 'yes', 'no', 'invalid', '2' must return 400
        for bad in ("yes", "no", "invalid", "2"):
            with self.subTest(bad=bad):
                res = self.owner.get(self.url(f"paths/?{pair}&explain={bad}"))
                self.assertEqual(res.status_code, 400, (bad, res.content))
                self.assertEqual(res.json().get("code"), "INVALID_DATA")
                self.assertEqual(res.json().get("detail"), "explain must be a boolean.")

        # Valid booleans 'true', '1' must be accepted and include explanation
        for good in ("true", "1", "True"):
            with self.subTest(good=good):
                res = self.owner.get(self.url(f"paths/?{pair}&explain={good}"))
                self.assertEqual(res.status_code, 200, (good, res.content))
                paths = res.json().get("paths", [])
                self.assertTrue(len(paths) > 0)
                self.assertIn("explanation", paths[0])

        # Valid booleans 'false', '0' must be accepted and omit explanation
        for good in ("false", "0", "False"):
            with self.subTest(good=good):
                res = self.owner.get(self.url(f"paths/?{pair}&explain={good}"))
                self.assertEqual(res.status_code, 200, (good, res.content))
                paths = res.json().get("paths", [])
                self.assertTrue(len(paths) > 0)
                self.assertNotIn("explanation", paths[0])
