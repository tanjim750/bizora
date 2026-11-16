"""Regression test for BIA-12:
Oversized ids -> 500 OverflowError (facts/<25 digits>/, issues/<25 digits>/).
25-digit id must return 404 NOT_FOUND, not 500.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from app import models
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member


class OversizedIdsTests(APITestCase):
    def setUp(self):
        self.biz = models.Business.objects.create(name="Oversized ID Test Biz")
        self.owner = make_member(self.biz, "OWNER")
        self.api = client_for(self.owner)

    def test_25_digit_fact_id_returns_404(self):
        huge_id = 1234567890123456789012345
        resp = self.api.get(intelligence_url(self.biz.pk, f"facts/{huge_id}/"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.json().get("code"), "NOT_FOUND")

    def test_25_digit_issue_id_returns_404(self):
        huge_id = 1234567890123456789012345
        resp = self.api.get(intelligence_url(self.biz.pk, f"issues/{huge_id}/"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.json().get("code"), "NOT_FOUND")
