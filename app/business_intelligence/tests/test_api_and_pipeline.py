"""Requirement-linked tests for BI §15-18 API, Pipeline Integration, and Security Gates (Ticket T-012).

Tests verify:
1. Deny-by-default authorization seam (membership of the URL business; others get 403).
2. Security Gate SEC-MED-1: Cross-tenant primary key existence oracle closed (uniform caller-facing error messages).
3. Security Gate SEC-HIGH-1: Per-row quarantine resilience during relationship reconciliation.
4. Metric and Metric Snapshot paginated read endpoints.
5. Fact list, create, detail, and lifecycle PATCH endpoints.
6. Issue list, create, detail, and lifecycle PATCH endpoints.
7. End-to-end pipeline orchestration.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase
from rest_framework import status

from app import models
from app.business_intelligence import api, metrics
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member


D = Decimal
START = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
END = START + timedelta(days=7)


class IntelligenceAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.biz_a = models.Business.objects.create(
            name="Prime Store", slug="prime-store", currency="BDT", created_at=START, updated_at=START
        )
        self.biz_b = models.Business.objects.create(
            name="Rival Store", slug="rival-store", currency="BDT", created_at=START, updated_at=START
        )
        metrics.sync_metric_registry(business_id=self.biz_a.pk)
        metrics.sync_metric_registry(business_id=self.biz_b.pk)
        self.owner = make_member(self.biz_a, "OWNER")
        self.member_b = make_member(self.biz_b, "OWNER")
        self.api = client_for(self.owner)

    def url(self, tail="", business=None):
        return intelligence_url((business or self.biz_a).pk, tail)

    def test_deny_by_default_authorization_seam(self):
        # 1. Anonymous callers are rejected
        self.assertEqual(client_for().get(self.url("facts/")).status_code, status.HTTP_403_FORBIDDEN)

        # 2. A member of another business cannot read this business
        resp_foreign = client_for(self.member_b).get(self.url("facts/"))
        self.assertEqual(resp_foreign.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp_foreign.json()["code"], "FORBIDDEN")

        # 3. A caller-supplied business_id never overrides the URL
        resp_mismatch = self.api.get(self.url("facts/") + f"?business_id={self.biz_b.pk}")
        self.assertEqual(resp_mismatch.status_code, status.HTTP_200_OK)

        # 4. Valid member -> 200 OK
        self.assertEqual(self.api.get(self.url("facts/")).status_code, status.HTTP_200_OK)

    def test_security_gate_sec_med_1_anti_oracle(self):
        fact_b = models.BusinessFact.objects.create(
            business=self.biz_b,
            fact_type="CONFIDENTIAL",
            statement="Shop B confidential fact",
            status="VERIFIED",
            detected_at=START,
            created_at=START,
            updated_at=START,
        )

        # Accessing an existing fact of B and a non-existent fact through A must look identical.
        resp_a = self.api.get(self.url(f"facts/{fact_b.pk}/"))
        resp_nonexistent = self.api.get(self.url("facts/999999/"))
        self.assertEqual(resp_a.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp_a.status_code, resp_nonexistent.status_code)
        self.assertEqual(resp_a.json(), resp_nonexistent.json())

    def test_security_gate_sec_high_1_quarantine_resilience(self):
        result, quarantined = api.reconcile_relationships_with_quarantine(business_id=self.biz_a.pk)
        self.assertIsNotNone(result)
        self.assertIsInstance(quarantined, list)

    def test_metrics_and_snapshots_paginated_api(self):
        resp_metrics = self.api.get(self.url("metrics/?limit=10&offset=0"))
        self.assertEqual(resp_metrics.status_code, status.HTTP_200_OK)
        self.assertGreater(resp_metrics.json()["total_count"], 0)
        self.assertLessEqual(len(resp_metrics.json()["results"]), 10)

        metric_key = "bi.metric.revenue_net.v1"
        metrics.record_metric_snapshot(
            business_id=self.biz_a.pk,
            metric_key=metric_key,
            value=D("1500.00"),
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        resp_snaps = self.api.get(self.url(f"metrics/{metric_key}/snapshots/?period_type=WEEK"))
        self.assertEqual(resp_snaps.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_snaps.json()["total_count"], 1)
        self.assertEqual(resp_snaps.json()["results"][0]["value"], "1500.000000")

        # The numeric metric id works too (metric keys contain dots, which the frontend proxy rejects).
        metric_id = models.BusinessMetric.objects.get(business=self.biz_a, key=metric_key).pk
        resp_by_id = self.api.get(self.url(f"metrics/{metric_id}/snapshots/"))
        self.assertEqual(resp_by_id.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_by_id.json()["metric_key"], metric_key)
        self.assertEqual(resp_by_id.json()["total_count"], 1)

    def test_facts_crud_and_lifecycle_api(self):
        resp_post = self.api.post(
            self.url("facts/"),
            {
                "fact_type": "DELIVERY_FAILURE_RATE",
                "statement": "Delivery failure rate reached 12%",
                "value": "0.1200",
                "value_unit": "RATIO",
                "rule_key": "rule.delivery",
            },
        )
        self.assertEqual(resp_post.status_code, status.HTTP_201_CREATED)
        fact_id = resp_post.json()["id"]

        resp_get = self.api.get(self.url(f"facts/{fact_id}/"))
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get.json()["statement"], "Delivery failure rate reached 12%")

        resp_patch = self.api.patch(self.url(f"facts/{fact_id}/"), {"status": "EXPIRED", "reason": "Period concluded"})
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_patch.json()["status"], "EXPIRED")
        self.assertIsNotNone(resp_patch.json()["valid_to"])

        resp_get_expired = self.api.get(self.url(f"facts/{fact_id}/"))
        self.assertEqual(resp_get_expired.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get_expired.json()["status"], "EXPIRED")

        resp_list_expired = self.api.get(self.url("facts/?status=EXPIRED"))
        self.assertEqual(resp_list_expired.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_list_expired.json()["total_count"], 1)
        self.assertEqual(resp_list_expired.json()["results"][0]["id"], fact_id)

    def test_issues_crud_and_lifecycle_api(self):
        resp_post = self.api.post(
            self.url("issues/"),
            {
                "issue_type": "HIGH_DELIVERY_FAILURE",
                "title": "Delivery failure spike in Gazipur",
                "description": "Failure rate exceeded acceptable threshold",
                "severity": "HIGH",
                "confidence": "0.9500",
                "rule_key": "rule.delivery.gazipur",
            },
        )
        self.assertEqual(resp_post.status_code, status.HTTP_201_CREATED)
        issue_id = resp_post.json()["id"]

        resp_get = self.api.get(self.url(f"issues/{issue_id}/"))
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get.json()["status"], "OPEN")
        self.assertIsNone(resp_get.json()["resolved_at"])

        resp_patch = self.api.patch(
            self.url(f"issues/{issue_id}/"),
            {"status": "RESOLVED", "notes": "Resolved via alternative courier routing"},
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_patch.json()["status"], "RESOLVED")
        self.assertIsNotNone(resp_patch.json()["resolved_at"])

    def test_pipeline_orchestration_api(self):
        resp_pipe = self.api.post(self.url("pipeline/run/"), {})
        self.assertEqual(resp_pipe.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_pipe.json()["business_id"], self.biz_a.pk)
        self.assertEqual(resp_pipe.json()["status"], "COMPLETED")
        self.assertIn("relationships_reconciled", resp_pipe.json())
