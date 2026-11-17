"""Tests for Card BGA-04: min_confidence parameter validation."""

from datetime import datetime, timezone

from django.test import TestCase

from app import models
from app.business_graph import project_business_graph
from app.tests.bi_graph_helpers import client_for, graph_url, make_member

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


class MinConfidenceValidationTests(TestCase):
    def setUp(self):
        super().setUp()
        self.business = models.Business.objects.create(
            name="Confidence Validation Shop",
            slug="confidence-validation-shop",
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

    def test_min_confidence_query_param_validation(self):
        """Card BGA-04: min_confidence abc, NaN, 1.5 -> 400."""
        root_params = f"root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}"

        for invalid_val in ("abc", "NaN", "Infinity", "-Infinity", "1.5", "-1", "2"):
            with self.subTest(min_confidence=invalid_val):
                url = graph_url(self.business.pk, f"traversal/?{root_params}&min_confidence={invalid_val}")
                resp = self.owner.get(url)
                self.assertEqual(resp.status_code, 400, (invalid_val, resp.content))
                data = resp.json()
                self.assertEqual(data.get("code"), "INVALID_DATA")
                self.assertEqual(data.get("detail"), "min_confidence must be a number between 0 and 1.")

    def test_min_confidence_snapshot_post_validation(self):
        """Card BGA-04: min_confidence in snapshot filters payload rejected with 400 if invalid."""
        for invalid_val in ("abc", "NaN", "1.5", -1, 2):
            with self.subTest(min_confidence=invalid_val):
                payload = {
                    "snapshot_type": "CUSTOMER",
                    "root_entity_id": self.customer.pk,
                    "filters": {"min_confidence": invalid_val},
                }
                resp = self.owner.post(graph_url(self.business.pk, "snapshots/"), payload)
                self.assertEqual(resp.status_code, 400, (invalid_val, resp.content))
                data = resp.json()
                self.assertEqual(data.get("code"), "INVALID_DATA")
                self.assertEqual(data.get("detail"), "min_confidence must be a number between 0 and 1.")
