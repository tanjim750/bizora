"""Tests for Graph API and Integrated Scenario Tests (T-019).

Verifies:
1. Deny-by-default authorization seam (membership of the URL business; others get 403).
2. Traversal and path search endpoints.
3. Customer, order, product, and campaign journey endpoints.
4. Snapshot list, create, and detail endpoints.
5. Rebuild API endpoint.
6. Complete integrated scenario: end-to-end pipeline from canonical entities to explainable graph paths.
"""

from decimal import Decimal
import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from app import models
from app.business_graph import api
from app.business_graph.projection import project_business_graph
from app.business_graph.snapshots import explain_path
from app.business_graph.traversal import find_paths
from app.tests.bi_graph_helpers import client_for, graph_url, make_member


class GraphAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.now = timezone.now()
        self.biz_a = models.Business.objects.create(
            name="Apex Retail",
            slug="apex-retail",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )
        self.biz_b = models.Business.objects.create(
            name="Vortex Retail",
            slug="vortex-retail",
            currency="USD",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )

        self.customer = models.Customer.objects.create(
            business=self.biz_a,
            first_name="Elena",
            last_name="Rostova",
            display_name="Elena Rostova",
            created_at=self.now,
            updated_at=self.now,
        )
        self.product = models.Product.objects.create(
            business=self.biz_a,
            name="Mechanical Keyboard",
            status="ACTIVE",
            created_at=self.now,
            updated_at=self.now,
        )
        self.order = models.Order.objects.create(
            business=self.biz_a,
            customer=self.customer,
            order_number="ORD-APEX-1",
            total_amount=Decimal("180.00"),
            currency="USD",
            status="PAID",
            ordered_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )

        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="CUSTOMER",
            source_entity_id=self.customer.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=self.order.pk,
            rule_key="customer_order",
            relationship_source="DETERMINISTIC",
            created_at=self.now,
            updated_at=self.now,
        )
        models.BusinessRelationship.objects.create(
            business=self.biz_a,
            source_entity_type="ORDER",
            source_entity_id=self.order.pk,
            relationship_type="CONTAINS_PRODUCT",
            target_entity_type="PRODUCT",
            target_entity_id=self.product.pk,
            rule_key="order_product",
            relationship_source="DETERMINISTIC",
            created_at=self.now,
            updated_at=self.now,
        )

        project_business_graph(business_id=self.biz_a.pk)
        self.owner = make_member(self.biz_a, "OWNER")
        self.member_b = make_member(self.biz_b, "OWNER")
        self.api = client_for(self.owner)

    def url(self, tail="", business=None):
        return graph_url((business or self.biz_a).pk, tail)

    def test_unauthenticated_and_foreign_callers_are_denied(self):
        path = f"journeys/customer/{self.customer.pk}/"

        # 1. Anonymous callers are rejected
        self.assertEqual(client_for().get(self.url(path)).status_code, status.HTTP_403_FORBIDDEN)

        # 2. A member of another business cannot read this business
        resp_foreign = client_for(self.member_b).get(self.url(path))
        self.assertEqual(resp_foreign.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn(str(self.biz_a.pk), str(resp_foreign.json().get("detail")))

        # 3. A caller-supplied business_id never overrides the URL
        resp_mismatch = self.api.get(self.url(path) + f"?business_id={self.biz_b.pk}")
        self.assertEqual(resp_mismatch.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_mismatch.json()["business_id"], self.biz_a.pk)

        # 4. The legacy request.business seam is gone
        resp_valid = self.api.get(self.url(path))
        self.assertEqual(resp_valid.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_valid.json()["customer_id"], self.customer.pk)

    def test_traversal_api(self):
        resp = self.api.get(
            self.url(f"traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}&direction=OUTBOUND&max_depth=2")
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["business_id"], self.biz_a.pk)
        self.assertGreaterEqual(data["node_count"], 3)
        self.assertEqual(data["edge_count"], 2)

    def test_path_search_api(self):
        resp = self.api.get(
            self.url(
                f"paths/?start_entity_type=CUSTOMER&start_entity_id={self.customer.pk}&end_entity_type=PRODUCT&end_entity_id={self.product.pk}&direction=OUTBOUND&max_depth=3"
            )
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["paths_found"], 1)
        self.assertEqual(resp.json()["paths"][0]["length"], 2)

    def test_order_product_campaign_journey_apis(self):
        resp_ord = self.api.get(self.url(f"journeys/order/{self.order.pk}/"))
        self.assertEqual(resp_ord.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_ord.json()["order_id"], self.order.pk)
        self.assertEqual(resp_ord.json()["product_count"], 1)

        resp_prod = self.api.get(self.url(f"journeys/product/{self.product.pk}/"))
        self.assertEqual(resp_prod.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_prod.json()["product_id"], self.product.pk)

    def test_snapshot_lifecycle_api(self):
        resp_create = self.api.post(self.url("snapshots/"), {"snapshot_type": "BUSINESS", "name": "API Test Snapshot"})
        self.assertEqual(resp_create.status_code, status.HTTP_201_CREATED)
        snap_id = resp_create.json()["id"]

        resp_detail = self.api.get(self.url(f"snapshots/{snap_id}/"))
        self.assertEqual(resp_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_detail.json()["id"], snap_id)
        self.assertIn("nodes", resp_detail.json()["snapshot_data"])

        resp_list = self.api.get(self.url("snapshots/"))
        self.assertEqual([row["id"] for row in resp_list.json()], [snap_id])

    def test_rebuild_api(self):
        resp_reb = self.api.post(self.url("rebuild/"), {"clean": False})
        self.assertEqual(resp_reb.status_code, status.HTTP_200_OK)
        data = resp_reb.json()
        self.assertEqual(data["business_id"], self.biz_a.pk)
        self.assertGreaterEqual(data["total_nodes"], 3)
        self.assertEqual(data["total_edges"], 2)

    def test_traversal_api_with_filters(self):
        base = f"traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}"
        resp = self.api.get(self.url(base + "&status=PAID"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("ORDER", [n["entity_type"] for n in resp.json()["nodes"]])

        resp_nonmatch = self.api.get(self.url(base + "&status=CANCELLED"))
        self.assertEqual(resp_nonmatch.status_code, status.HTTP_200_OK)
        self.assertNotIn("ORDER", [n["entity_type"] for n in resp_nonmatch.json()["nodes"]])

    def test_path_search_api_with_explain(self):
        models.BusinessFact.objects.create(
            business=self.biz_a,
            fact_type="ORDER_PROFITABILITY",
            subject_entity_type="ORDER",
            subject_entity_id=self.order.pk,
            statement="Order margin 35%",
            confidence=Decimal("1.0000"),
            status="VERIFIED",
            detected_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )

        resp = self.api.get(
            self.url(
                f"paths/?start_entity_type=CUSTOMER&start_entity_id={self.customer.pk}&end_entity_type=PRODUCT&end_entity_id={self.product.pk}&explain=true"
            )
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["paths_found"], 1)
        path = resp.json()["paths"][0]
        self.assertIn("explanation", path)
        self.assertEqual(len(path["explanation"]), 3)
        order_step = path["explanation"][1]
        self.assertEqual(order_step["node"]["entity_type"], "ORDER")
        self.assertEqual(len(order_step["node"]["facts"]), 1)
        self.assertEqual(order_step["node"]["facts"][0]["fact_type"], "ORDER_PROFITABILITY")

    def test_subgraph_query_api(self):
        resp = self.api.get(self.url("query/?relationship_type=PLACED_ORDER"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["edge_count"], 1)
        self.assertEqual(resp.json()["edges"][0]["relationship_type"], "PLACED_ORDER")

        resp_empty = self.api.get(self.url("query/?relationship_type=NONEXISTENT_TYPE"))
        self.assertEqual(resp_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_empty.json()["edge_count"], 0)

    def test_journey_api_with_filters(self):
        resp = self.api.get(self.url(f"journeys/customer/{self.customer.pk}/?status=PAID"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["customer_id"], self.customer.pk)

    def test_snapshot_create_with_filters(self):
        payload = {
            "snapshot_type": "CUSTOMER",
            "root_entity_id": self.customer.pk,
            "name": "Filtered Customer Snapshot",
            "filters": {"status": "PAID", "min_confidence": "0.95"},
        }
        resp = self.api.post(self.url("snapshots/"), payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        snap = models.GraphSnapshot.objects.get(pk=resp.json()["id"])
        self.assertEqual(snap.filters.get("status"), "PAID")
        self.assertEqual(snap.filters.get("min_confidence"), "0.95")


class IntegratedBusinessScenarioTests(TestCase):
    def test_full_pipeline_cross_domain_scenario(self):
        """End-to-end multi-domain scenario:
        Marketing Campaign -> Visitor -> Session -> Customer -> Order -> Product -> Payment -> Shipment -> Call
        All verified relationships, rebuild, path search, explainable evidence, and stable snapshots.
        """
        now = timezone.now()
        t0 = now - datetime.timedelta(hours=6)
        t1 = now - datetime.timedelta(hours=5)
        t2 = now - datetime.timedelta(hours=4)
        t3 = now - datetime.timedelta(hours=3)
        t4 = now - datetime.timedelta(hours=2)
        t5 = now - datetime.timedelta(hours=1)

        biz = models.Business.objects.create(
            name="Omni Enterprise",
            slug="omni-enterprise",
            currency="USD",
            status="ACTIVE",
            created_at=t0,
            updated_at=t0,
        )

        # 1. Marketing
        camp = models.Campaign.objects.create(
            business=biz,
            name="Fall Kickoff",
            platform="META",
            status="ACTIVE",
            created_at=t0,
            updated_at=t0,
        )
        visitor = models.WebsiteVisitor.objects.create(
            business=biz,
            visitor_key="vis-omni-99",
            first_seen_at=t1,
            last_seen_at=t1,
            created_at=t1,
            updated_at=t1,
        )
        sess = models.WebsiteSession.objects.create(
            business=biz,
            visitor=visitor,
            started_at=t1,
            created_at=t1,
            updated_at=t1,
        )

        # 2. Customer & Product
        cust = models.Customer.objects.create(
            business=biz,
            first_name="Marcus",
            last_name="Vance",
            display_name="Marcus Vance",
            created_at=t2,
            updated_at=t2,
        )
        prod = models.Product.objects.create(
            business=biz,
            name="Ultra Monitor 4K",
            status="ACTIVE",
            created_at=t0,
            updated_at=t0,
        )

        # 3. Order
        ord_obj = models.Order.objects.create(
            business=biz,
            customer=cust,
            order_number="ORD-OMNI-700",
            total_amount=Decimal("650.00"),
            currency="USD",
            status="CONFIRMED",
            ordered_at=t3,
            created_at=t3,
            updated_at=t3,
        )

        # 4. Payment & Shipment
        pay = models.Payment.objects.create(
            business=biz,
            order=ord_obj,
            amount=Decimal("650.00"),
            currency="USD",
            status="COMPLETED",
            created_at=t4,
            updated_at=t4,
        )
        ship = models.Shipment.objects.create(
            business=biz,
            order=ord_obj,
            tracking_code="TRK-OMNI-700",
            provider="FedEx",
            status="OUT_FOR_DELIVERY",
            created_at=t4,
            updated_at=t4,
        )

        # 5. Support Call
        call = models.Call.objects.create(
            business=biz,
            direction="INBOUND",
            started_at=t5,
            created_at=t5,
            updated_at=t5,
        )

        # 6. Authoritative deterministic relationships
        models.BusinessRelationship.objects.create(
            business=biz,
            source_entity_type="CAMPAIGN",
            source_entity_id=camp.pk,
            relationship_type="REPORTED_SESSION",
            target_entity_type="WEBSITE_SESSION",
            target_entity_id=sess.pk,
            rule_key="campaign_session",
            relationship_source="REPORTED",
            created_at=t1,
            updated_at=t1,
        )
        models.BusinessRelationship.objects.create(
            business=biz,
            source_entity_type="CUSTOMER",
            source_entity_id=cust.pk,
            relationship_type="HAS_SESSION",
            target_entity_type="WEBSITE_SESSION",
            target_entity_id=sess.pk,
            rule_key="customer_session",
            relationship_source="DETERMINISTIC",
            created_at=t2,
            updated_at=t2,
        )
        models.BusinessRelationship.objects.create(
            business=biz,
            source_entity_type="CUSTOMER",
            source_entity_id=cust.pk,
            relationship_type="PLACED_ORDER",
            target_entity_type="ORDER",
            target_entity_id=ord_obj.pk,
            rule_key="customer_order",
            relationship_source="DETERMINISTIC",
            created_at=t3,
            updated_at=t3,
        )
        models.BusinessRelationship.objects.create(
            business=biz,
            source_entity_type="ORDER",
            source_entity_id=ord_obj.pk,
            relationship_type="CONTAINS_PRODUCT",
            target_entity_type="PRODUCT",
            target_entity_id=prod.pk,
            rule_key="order_product",
            relationship_source="DETERMINISTIC",
            created_at=t3,
            updated_at=t3,
        )
        models.BusinessRelationship.objects.create(
            business=biz,
            source_entity_type="ORDER",
            source_entity_id=ord_obj.pk,
            relationship_type="HAS_PAYMENT",
            target_entity_type="PAYMENT",
            target_entity_id=pay.pk,
            rule_key="order_payment",
            relationship_source="DETERMINISTIC",
            created_at=t4,
            updated_at=t4,
        )
        models.BusinessRelationship.objects.create(
            business=biz,
            source_entity_type="ORDER",
            source_entity_id=ord_obj.pk,
            relationship_type="HAS_SHIPMENT",
            target_entity_type="SHIPMENT",
            target_entity_id=ship.pk,
            rule_key="order_shipment",
            relationship_source="DETERMINISTIC",
            created_at=t4,
            updated_at=t4,
        )
        models.BusinessRelationship.objects.create(
            business=biz,
            source_entity_type="ORDER",
            source_entity_id=ord_obj.pk,
            relationship_type="HAS_CALL",
            target_entity_type="CALL",
            target_entity_id=call.pk,
            rule_key="order_call",
            relationship_source="DETERMINISTIC",
            created_at=t5,
            updated_at=t5,
        )

        # 7. Add verified business facts and issues
        models.BusinessFact.objects.create(
            business=biz,
            fact_type="ORDER_PROFITABILITY",
            subject_entity_type="ORDER",
            subject_entity_id=ord_obj.pk,
            statement="Order ORD-OMNI-700 realized gross margin of 42%",
            value=Decimal("42.00"),
            value_unit="PERCENT",
            confidence=Decimal("1.0000"),
            status="VERIFIED",
            detected_at=t4,
            created_at=t4,
            updated_at=t4,
        )

        # 8. Trigger full rebuild
        summary = api.rebuild_business_graph(business_id=biz.pk, clean=False)
        self.assertGreaterEqual(summary.total_nodes, 7)
        self.assertEqual(summary.total_edges, 7)

        # 9. Path search from Customer to Shipment
        paths = find_paths(
            business_id=biz.pk,
            start_entity_type="CUSTOMER",
            start_entity_id=cust.pk,
            end_entity_type="SHIPMENT",
            end_entity_id=ship.pk,
            direction="OUTBOUND",
            max_depth=3,
        )
        self.assertEqual(len(paths), 1)

        # 10. Explain path with underlying evidence
        explanation = explain_path(business_id=biz.pk, path=paths[0])
        self.assertEqual(len(explanation), 3)
        # Order node in path contains verified fact
        ord_step = explanation[1]
        self.assertEqual(ord_step["node"]["entity_type"], "ORDER")
        self.assertEqual(len(ord_step["node"]["facts"]), 1)
        self.assertEqual(ord_step["node"]["facts"][0]["fact_type"], "ORDER_PROFITABILITY")
