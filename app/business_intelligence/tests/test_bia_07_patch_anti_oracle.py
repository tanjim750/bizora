"""Regression test for BIA-07:
PATCH oracle: foreign fact -> 403, unknown -> 400, GET gives 404 for both (contradicts SEC-MED-1).
Filter by business in update_*_lifecycle, identical 404 with code NOT_FOUND for both foreign and unknown IDs.
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from app import models
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member


class PatchAntiOracleTests(APITestCase):
    def setUp(self):
        self.biz_a = models.Business.objects.create(name="Biz A", slug="biz-a-test")
        self.biz_b = models.Business.objects.create(name="Biz B", slug="biz-b-test")
        self.owner_a = make_member(self.biz_a, "OWNER")
        self.api_a = client_for(self.owner_a)

        self.fact_b = models.BusinessFact.all_objects.create(
            business=self.biz_b,
            fact_type="GENERAL",
            statement="Biz B secret fact",
            status="VERIFIED",
            detected_at=timezone.now(),
        )

        self.issue_b = models.BusinessIssue.objects.create(
            business=self.biz_b,
            issue_type="REVENUE_DECLINE",
            title="Biz B secret issue",
            severity="HIGH",
            status="OPEN",
            detected_at=timezone.now(),
        )

    def test_patch_fact_foreign_and_unknown_both_return_404_not_found(self):
        # Foreign fact PATCH
        resp_foreign = self.api_a.patch(
            intelligence_url(self.biz_a.pk, f"facts/{self.fact_b.pk}/"),
            {"status": "INVALIDATED", "reason": "Test patch"},
            format="json",
        )
        self.assertEqual(resp_foreign.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_foreign.json().get("code"), "NOT_FOUND")

        # Unknown fact PATCH
        resp_unknown = self.api_a.patch(
            intelligence_url(self.biz_a.pk, "facts/999999/"),
            {"status": "INVALIDATED", "reason": "Test patch"},
            format="json",
        )
        self.assertEqual(resp_unknown.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_unknown.json().get("code"), "NOT_FOUND")

        # Anti-oracle check: exact same response payload
        self.assertEqual(resp_foreign.json(), resp_unknown.json())

    def test_patch_issue_foreign_and_unknown_both_return_404_not_found(self):
        # Foreign issue PATCH
        resp_foreign = self.api_a.patch(
            intelligence_url(self.biz_a.pk, f"issues/{self.issue_b.pk}/"),
            {"status": "RESOLVED", "notes": "Resolved notes"},
            format="json",
        )
        self.assertEqual(resp_foreign.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_foreign.json().get("code"), "NOT_FOUND")

        # Unknown issue PATCH
        resp_unknown = self.api_a.patch(
            intelligence_url(self.biz_a.pk, "issues/999999/"),
            {"status": "RESOLVED", "notes": "Resolved notes"},
            format="json",
        )
        self.assertEqual(resp_unknown.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_unknown.json().get("code"), "NOT_FOUND")

        # Anti-oracle check: exact same response payload
        self.assertEqual(resp_foreign.json(), resp_unknown.json())
