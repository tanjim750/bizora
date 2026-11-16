"""Regression test for BIA-06:
fact_ids/snapshot_ids unchecked: foreign-tenant fact id and 999999 accepted, stored raw, 0 evidence rows.
Foreign/missing fact id or snapshot id must return 400 INVALID_DATA and store nothing.
Valid fact_ids/snapshot_ids must create BusinessIssueEvidence rows.
"""
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from app import models
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member


class IssueForeignEvidenceTests(APITestCase):
    def setUp(self):
        self.biz_a = models.Business.objects.create(name="Biz A", slug="biz-a-test")
        self.biz_b = models.Business.objects.create(name="Biz B", slug="biz-b-test")
        self.owner_a = make_member(self.biz_a, "OWNER")
        self.api_a = client_for(self.owner_a)

        self.fact_b = models.BusinessFact.all_objects.create(
            business=self.biz_b,
            fact_type="GENERAL",
            statement="Biz B secret fact",
            detected_at=timezone.now(),
        )

        self.metric_b = models.BusinessMetric.objects.create(
            business=self.biz_b,
            key="metric.b",
            name="Metric B",
            category="SALES",
            unit="BDT",
            value_type="CURRENCY",
        )
        self.snapshot_b = models.MetricSnapshot.objects.create(
            business=self.biz_b,
            metric=self.metric_b,
            period_type="DAY",
            period_start=timezone.now(),
            period_end=timezone.now(),
            calculated_at=timezone.now(),
            value=Decimal("100"),
        )

    def test_foreign_fact_id_returns_400_and_nothing_stored(self):
        resp = self.api_a.post(
            intelligence_url(self.biz_a.pk, "issues/"),
            {
                "issue_type": "DATA_INTEGRITY",
                "title": "Issue referencing foreign fact",
                "fact_ids": [self.fact_b.pk],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json().get("code"), "INVALID_DATA")
        self.assertEqual(
            models.BusinessIssue.objects.filter(business_id=self.biz_a.pk).count(),
            0,
            "No issue should be stored when foreign fact id is provided",
        )

    def test_nonexistent_fact_id_returns_400_and_nothing_stored(self):
        resp = self.api_a.post(
            intelligence_url(self.biz_a.pk, "issues/"),
            {
                "issue_type": "DATA_INTEGRITY",
                "title": "Issue referencing 999999",
                "fact_ids": [999999],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            models.BusinessIssue.objects.filter(business_id=self.biz_a.pk).count(),
            0,
        )

    def test_foreign_snapshot_id_returns_400_and_nothing_stored(self):
        resp = self.api_a.post(
            intelligence_url(self.biz_a.pk, "issues/"),
            {
                "issue_type": "DATA_INTEGRITY",
                "title": "Issue referencing foreign snapshot",
                "snapshot_ids": [self.snapshot_b.pk],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            models.BusinessIssue.objects.filter(business_id=self.biz_a.pk).count(),
            0,
        )

    def test_valid_fact_and_snapshot_ids_create_issue_and_evidence_rows(self):
        fact_a = models.BusinessFact.all_objects.create(
            business=self.biz_a,
            fact_type="GENERAL",
            statement="Biz A fact",
            detected_at=timezone.now(),
        )
        metric_a = models.BusinessMetric.objects.create(
            business=self.biz_a,
            key="metric.a",
            name="Metric A",
            category="SALES",
            unit="BDT",
            value_type="CURRENCY",
        )
        snap_a = models.MetricSnapshot.objects.create(
            business=self.biz_a,
            metric=metric_a,
            period_type="DAY",
            period_start=timezone.now(),
            period_end=timezone.now(),
            calculated_at=timezone.now(),
            value=Decimal("200"),
        )

        resp = self.api_a.post(
            intelligence_url(self.biz_a.pk, "issues/"),
            {
                "issue_type": "DATA_INTEGRITY",
                "title": "Valid issue with evidence",
                "fact_ids": [fact_a.pk],
                "snapshot_ids": [snap_a.pk],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        issue_id = resp.json()["id"]

        evidence_rows = models.BusinessIssueEvidence.objects.filter(business_issue_id=issue_id)
        self.assertEqual(evidence_rows.count(), 2)
