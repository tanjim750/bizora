"""Tests for Graph API and Integrated Scenario Tests (T-019).

Verifies:
1. Deny-by-default authorization seam (rejects unauthenticated/mismatched requests with 403).
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
from rest_framework.test import APIRequestFactory

from app import models
from app.business_graph import api
from app.business_graph.projection import project_business_graph
from app.business_graph.snapshots import explain_path
from app.business_graph.traversal import find_paths


class GraphAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
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

    def test_deny_by_default_authorization_seam(self):
        # 1. Request with NO business context must be denied
        view = api.CustomerJourneyAPIView.as_view()
        req = self.factory.get(f"/journeys/customer/{self.customer.pk}/")
        resp = view(req, customer_id=self.customer.pk)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Request with caller-supplied business_id mismatch must be denied
        req_mismatch = self.factory.get(f"/journeys/customer/{self.customer.pk}/?business_id={self.biz_b.pk}")
        req_mismatch.business = self.biz_a  # Authorized for A, but requested B
        resp_mismatch = view(req_mismatch, customer_id=self.customer.pk)
        self.assertEqual(resp_mismatch.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Request with valid matching business context succeeds
        req_valid = self.factory.get(f"/journeys/customer/{self.customer.pk}/")
        req_valid.business = self.biz_a
        resp_valid = view(req_valid, customer_id=self.customer.pk)
        self.assertEqual(resp_valid.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_valid.data["customer_id"], self.customer.pk)

    def test_traversal_api(self):
        view = api.GraphTraversalAPIView.as_view()
        req = self.factory.get(f"/traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}&direction=OUTBOUND&max_depth=2")
        req.business = self.biz_a
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["business_id"], self.biz_a.pk)
        self.assertGreaterEqual(resp.data["node_count"], 3)
        self.assertEqual(resp.data["edge_count"], 2)

    def test_path_search_api(self):
        view = api.GraphPathSearchAPIView.as_view()
        req = self.factory.get(
            f"/paths/?start_entity_type=CUSTOMER&start_entity_id={self.customer.pk}&end_entity_type=PRODUCT&end_entity_id={self.product.pk}&direction=OUTBOUND&max_depth=3"
        )
        req.business = self.biz_a
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["paths_found"], 1)
        self.assertEqual(resp.data["paths"][0]["length"], 2)

    def test_order_product_campaign_journey_apis(self):
        # Order journey
        view_ord = api.OrderJourneyAPIView.as_view()
        req_ord = self.factory.get(f"/journeys/order/{self.order.pk}/")
        req_ord.business = self.biz_a
        resp_ord = view_ord(req_ord, order_id=self.order.pk)
        self.assertEqual(resp_ord.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_ord.data["order_id"], self.order.pk)
        self.assertEqual(resp_ord.data["product_count"], 1)

        # Product journey
        view_prod = api.ProductJourneyAPIView.as_view()
        req_prod = self.factory.get(f"/journeys/product/{self.product.pk}/")
        req_prod.business = self.biz_a
        resp_prod = view_prod(req_prod, product_id=self.product.pk)
        self.assertEqual(resp_prod.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_prod.data["product_id"], self.product.pk)

    def test_snapshot_lifecycle_api(self):
        # Create snapshot
        view_snap = api.GraphSnapshotListCreateAPIView.as_view()
        req_create = self.factory.post("/snapshots/", {"snapshot_type": "BUSINESS", "name": "API Test Snapshot"}, format="json")
        req_create.business = self.biz_a
        resp_create = view_snap(req_create)
        self.assertEqual(resp_create.status_code, status.HTTP_201_CREATED)
        snap_id = resp_create.data["id"]

        # Detail snapshot
        view_detail = api.GraphSnapshotDetailAPIView.as_view()
        req_detail = self.factory.get(f"/snapshots/{snap_id}/")
        req_detail.business = self.biz_a
        resp_detail = view_detail(req_detail, snapshot_id=snap_id)
        self.assertEqual(resp_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_detail.data["id"], snap_id)
        self.assertIn("nodes", resp_detail.data["snapshot_data"])

    def test_rebuild_api(self):
        view_reb = api.GraphRebuildAPIView.as_view()
        req_reb = self.factory.post("/rebuild/", {"clean": False}, format="json")
        req_reb.business = self.biz_a
        resp_reb = view_reb(req_reb)
        self.assertEqual(resp_reb.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_reb.data["business_id"], self.biz_a.pk)
        self.assertGreaterEqual(resp_reb.data["total_nodes"], 3)
        self.assertEqual(resp_reb.data["total_edges"], 2)

    def test_traversal_api_with_filters(self):
        view = api.GraphTraversalAPIView.as_view()
        # Query with status filter matching order status
        req = self.factory.get(
            f"/traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}&status=PAID"
        )
        req.business = self.biz_a
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        node_types = [n["entity_type"] for n in resp.data["nodes"]]
        self.assertIn("ORDER", node_types)

        # Query with non-matching status
        req_nonmatch = self.factory.get(
            f"/traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}&status=CANCELLED"
        )
        req_nonmatch.business = self.biz_a
        resp_nonmatch = view(req_nonmatch)
        self.assertEqual(resp_nonmatch.status_code, status.HTTP_200_OK)
        node_types_nonmatch = [n["entity_type"] for n in resp_nonmatch.data["nodes"]]
        self.assertNotIn("ORDER", node_types_nonmatch)

    def test_path_search_api_with_explain(self):
        # Create fact and issue for order
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

        view = api.GraphPathSearchAPIView.as_view()
        req = self.factory.get(
            f"/paths/?start_entity_type=CUSTOMER&start_entity_id={self.customer.pk}&end_entity_type=PRODUCT&end_entity_id={self.product.pk}&explain=true"
        )
        req.business = self.biz_a
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["paths_found"], 1)
        path = resp.data["paths"][0]
        self.assertIn("explanation", path)
        self.assertEqual(len(path["explanation"]), 3)
        order_step = path["explanation"][1]
        self.assertEqual(order_step["node"]["entity_type"], "ORDER")
        self.assertEqual(len(order_step["node"]["facts"]), 1)
        self.assertEqual(order_step["node"]["facts"][0]["fact_type"], "ORDER_PROFITABILITY")

    def test_subgraph_query_api(self):
        view = api.GraphQueryAPIView.as_view()
        # Query by relationship_type
        req = self.factory.get("/query/?relationship_type=PLACED_ORDER")
        req.business = self.biz_a
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["edge_count"], 1)
        self.assertEqual(resp.data["edges"][0]["relationship_type"], "PLACED_ORDER")

        # Query by non-existent relationship_type
        req_empty = self.factory.get("/query/?relationship_type=NONEXISTENT_TYPE")
        req_empty.business = self.biz_a
        resp_empty = view(req_empty)
        self.assertEqual(resp_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_empty.data["edge_count"], 0)

    def test_journey_api_with_filters(self):
        view = api.CustomerJourneyAPIView.as_view()
        req = self.factory.get(f"/journeys/customer/{self.customer.pk}/?status=PAID")
        req.business = self.biz_a
        resp = view(req, customer_id=self.customer.pk)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["customer_id"], self.customer.pk)

    def test_snapshot_create_with_filters(self):
        view = api.GraphSnapshotListCreateAPIView.as_view()
        payload = {
            "snapshot_type": "CUSTOMER",
            "root_entity_id": self.customer.pk,
            "name": "Filtered Customer Snapshot",
            "filters": {
                "status": "PAID",
                "min_confidence": "0.95",
            },
        }
        req = self.factory.post("/snapshots/", payload, format="json")
        req.business = self.biz_a
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        snap = models.GraphSnapshot.objects.get(pk=resp.data["id"])
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
