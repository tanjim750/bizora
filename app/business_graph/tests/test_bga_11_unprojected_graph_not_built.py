"""Regression tests for BGA-11:
When the business has no graph nodes at all (the graph was never rebuilt), traversal and the four journey
endpoints answer 409 with code GRAPH_NOT_BUILT and generic detail.
When the graph exists, missing or foreign entity answers 404 NOT_FOUND.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from app import models
from app.business_graph import projection
from app.tests.bi_graph_helpers import client_for, graph_url, make_member


class UnprojectedGraphNotBuiltTests(APITestCase):
    def setUp(self):
        self.biz = models.Business.objects.create(name="Unprojected Biz")
        self.owner = make_member(self.biz, "OWNER")
        self.api = client_for(self.owner)

        self.customer = models.Customer.objects.create(
            business=self.biz,
            first_name="Alice",
            last_name="Smith",
        )
        self.product = models.Product.objects.create(
            business=self.biz,
            name="Widget",
        )
        self.order = models.Order.objects.create(
            business=self.biz,
            customer=self.customer,
            order_number="ORD-101",
            status="PENDING",
        )
        self.campaign = models.Campaign.objects.create(
            business=self.biz,
            name="Spring Sale",
        )

    def url(self, tail=""):
        return graph_url(self.biz.pk, tail)

    def test_unprojected_customer_journey_returns_409_graph_not_built(self):
        resp = self.api.get(self.url(f"journeys/customer/{self.customer.pk}/"))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        data = resp.json()
        self.assertEqual(data.get("code"), "GRAPH_NOT_BUILT")
        self.assertEqual(
            data.get("detail"),
            "The business graph has not been built yet. Rebuild it first.",
        )

    def test_unprojected_traversal_returns_409_graph_not_built(self):
        resp = self.api.get(
            self.url(f"traversal/?root_entity_type=CUSTOMER&root_entity_id={self.customer.pk}")
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        data = resp.json()
        self.assertEqual(data.get("code"), "GRAPH_NOT_BUILT")
        self.assertEqual(
            data.get("detail"),
            "The business graph has not been built yet. Rebuild it first.",
        )

    def test_order_product_campaign_journeys_return_409_when_graph_not_built(self):
        resp_ord = self.api.get(self.url(f"journeys/order/{self.order.pk}/"))
        self.assertEqual(resp_ord.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp_ord.json().get("code"), "GRAPH_NOT_BUILT")
        self.assertEqual(
            resp_ord.json().get("detail"),
            "The business graph has not been built yet. Rebuild it first.",
        )

        resp_prod = self.api.get(self.url(f"journeys/product/{self.product.pk}/"))
        self.assertEqual(resp_prod.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp_prod.json().get("code"), "GRAPH_NOT_BUILT")
        self.assertEqual(
            resp_prod.json().get("detail"),
            "The business graph has not been built yet. Rebuild it first.",
        )

        resp_camp = self.api.get(self.url(f"journeys/campaign/{self.campaign.pk}/"))
        self.assertEqual(resp_camp.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp_camp.json().get("code"), "GRAPH_NOT_BUILT")
        self.assertEqual(
            resp_camp.json().get("detail"),
            "The business graph has not been built yet. Rebuild it first.",
        )

    def test_when_graph_exists_missing_entity_returns_404(self):
        # Project existing entities so graph exists
        projection.project_business_graph(business_id=self.biz.pk)
        self.assertTrue(models.GraphNode.objects.filter(business_id=self.biz.pk).exists())

        # Non-existent customer should return 404, not 409
        resp = self.api.get(self.url("journeys/customer/999999/"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.json().get("code"), "NOT_FOUND")

        # Customer exists in DB but was not projected into graph -> 404 NOT_FOUND
        new_cust = models.Customer.objects.create(
            business=self.biz,
            first_name="Bob",
            last_name="Unprojected",
        )
        resp_unproj = self.api.get(self.url(f"journeys/customer/{new_cust.pk}/"))
        self.assertEqual(resp_unproj.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_unproj.json().get("code"), "NOT_FOUND")

        # Non-existent traversal root entity should return 404, not 409
        resp_trav = self.api.get(
            self.url("traversal/?root_entity_type=CUSTOMER&root_entity_id=999999")
        )
        self.assertEqual(resp_trav.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_trav.json().get("code"), "NOT_FOUND")
