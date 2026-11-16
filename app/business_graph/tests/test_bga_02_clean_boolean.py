"""Tests for Card BGA-02: validate clean parameter in rebuild endpoint."""

from datetime import datetime, timezone

from django.test import TestCase

from app import models
from app.business_graph import GraphValidationError, project_business_graph, rebuild_business_graph
from app.tests.bi_graph_helpers import client_for, graph_url, make_member

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


class CleanBooleanValidationTests(TestCase):
    def setUp(self):
        super().setUp()
        self.business = models.Business.objects.create(
            name="Clean Validation Shop",
            slug="clean-validation-shop",
            currency="BDT",
            created_at=T0,
            updated_at=T0,
        )
        self.customer = models.Customer.objects.create(
            business=self.business,
            first_name="Rina",
            last_name="Das",
            display_name="Rina Das",
            created_at=T0,
            updated_at=T0,
        )
        self.order = models.Order.objects.create(
            business=self.business,
            customer=self.customer,
            status="PAID",
            currency="BDT",
            total_amount=10,
            ordered_at=T0,
            created_at=T0,
            updated_at=T0,
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

    def url(self, tail="rebuild/"):
        return graph_url(self.business.pk, tail)

    def test_rebuild_string_false_returns_400_and_node_ids_unchanged(self):
        """Card BGA-02: clean: 'false' -> 400, node ids unchanged."""
        # Get existing node IDs before the rebuild request
        initial_node_ids = set(
            models.GraphNode.objects.filter(business_id=self.business.pk).values_list("id", flat=True)
        )
        self.assertTrue(len(initial_node_ids) > 0)

        # POST {"clean": "false"} as JSON
        resp = self.owner.post(
            self.url(),
            {"clean": "false"},
        )

        self.assertEqual(resp.status_code, 400, resp.content)
        data = resp.json()
        self.assertEqual(data.get("code"), "INVALID_DATA")
        self.assertEqual(data.get("detail"), "clean must be a boolean.")

        # Invariant: node IDs must remain unchanged
        after_node_ids = set(
            models.GraphNode.objects.filter(business_id=self.business.pk).values_list("id", flat=True)
        )
        self.assertEqual(initial_node_ids, after_node_ids)

    def test_rebuild_service_rejects_non_boolean_clean(self):
        """rebuild_business_graph service must reject non-boolean clean parameter."""
        with self.assertRaises(GraphValidationError) as ctx:
            rebuild_business_graph(business_id=self.business.pk, clean="false")
        self.assertEqual(str(ctx.exception), "clean must be a boolean.")
