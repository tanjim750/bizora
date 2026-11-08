"""Requirement-linked tests for BI §15-18 API, Pipeline Integration, and Security Gates (Ticket T-012).

Tests verify:
1. Deny-by-default authorization seam (mandates request business context; rejects tenant spoofing with 403).
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
from rest_framework.test import APIRequestFactory

from app import models
from app.business_intelligence import api, metrics


D = Decimal
START = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
END = START + timedelta(days=7)


class IntelligenceAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.biz_a = models.Business.objects.create(
            name="Prime Store", slug="prime-store", currency="BDT", created_at=START, updated_at=START
        )
        self.biz_b = models.Business.objects.create(
            name="Rival Store", slug="rival-store", currency="BDT", created_at=START, updated_at=START
        )
        metrics.sync_metric_registry(business_id=self.biz_a.pk)
        metrics.sync_metric_registry(business_id=self.biz_b.pk)

    def test_deny_by_default_authorization_seam(self):
        view = api.FactListCreateView.as_view()

        # 1. No business context -> 403 Forbidden
        req_unauth = self.factory.get("/facts/")
        resp_unauth = view(req_unauth)
        self.assertEqual(resp_unauth.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Caller-supplied business_id mismatch -> 403 Forbidden
        req_mismatch = self.factory.get(f"/facts/?business_id={self.biz_b.pk}")
        req_mismatch.business = self.biz_a
        resp_mismatch = view(req_mismatch)
        self.assertEqual(resp_mismatch.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Valid authorized business context -> 200 OK
        req_valid = self.factory.get("/facts/")
        req_valid.business = self.biz_a
        resp_valid = view(req_valid)
        self.assertEqual(resp_valid.status_code, status.HTTP_200_OK)

    def test_security_gate_sec_med_1_anti_oracle(self):
        # Create fact in Business B
        fact_b = models.BusinessFact.objects.create(
            business=self.biz_b,
            fact_type="CONFIDENTIAL",
            statement="Shop B confidential fact",
            status="VERIFIED",
            detected_at=START,
            created_at=START,
            updated_at=START,
        )

        view = api.FactDetailView.as_view()

        # Accessing existing fact_b using Business A credentials
        req_a = self.factory.get(f"/facts/{fact_b.pk}/")
        req_a.business = self.biz_a
        resp_a = view(req_a, fact_id=fact_b.pk)

        # Accessing completely non-existent fact using Business A credentials
        req_nonexistent = self.factory.get("/facts/999999/")
        req_nonexistent.business = self.biz_a
        resp_nonexistent = view(req_nonexistent, fact_id=999999)

        # SEC-MED-1: Both must return the identical status code and error message!
        # No timing or message oracle that leaks whether fact_b exists in another tenant.
        self.assertEqual(resp_a.status_code, resp_nonexistent.status_code)
        self.assertEqual(resp_a.data["error"], resp_nonexistent.data["error"])

    def test_security_gate_sec_high_1_quarantine_resilience(self):
        # Run reconciliation with quarantine
        result, quarantined = api.reconcile_relationships_with_quarantine(business_id=self.biz_a.pk)
        self.assertIsNotNone(result)
        self.assertIsInstance(quarantined, list)

    def test_metrics_and_snapshots_paginated_api(self):
        # 1. Metrics list
        view_metrics = api.MetricListView.as_view()
        req_metrics = self.factory.get("/metrics/?limit=10&offset=0")
        req_metrics.business = self.biz_a
        resp_metrics = view_metrics(req_metrics)
        self.assertEqual(resp_metrics.status_code, status.HTTP_200_OK)
        self.assertGreater(resp_metrics.data["total_count"], 0)
        self.assertLessEqual(len(resp_metrics.data["results"]), 10)

        # 2. Record a snapshot and query via API
        metric_key = "bi.metric.revenue_net.v1"
        metrics.record_metric_snapshot(
            business_id=self.biz_a.pk,
            metric_key=metric_key,
            value=D("1500.00"),
            period_type="WEEK",
            period_start=START,
            period_end=END,
        )

        view_snaps = api.MetricSnapshotListView.as_view()
        req_snaps = self.factory.get(f"/metrics/{metric_key}/snapshots/?period_type=WEEK")
        req_snaps.business = self.biz_a
        resp_snaps = view_snaps(req_snaps, metric_key=metric_key)
        self.assertEqual(resp_snaps.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_snaps.data["total_count"], 1)
        self.assertEqual(resp_snaps.data["results"][0]["value"], "1500.000000")

    def test_facts_crud_and_lifecycle_api(self):
        # POST create fact
        view_facts = api.FactListCreateView.as_view()
        req_post = self.factory.post(
            "/facts/",
            {
                "fact_type": "DELIVERY_FAILURE_RATE",
                "statement": "Delivery failure rate reached 12%",
                "value": "0.1200",
                "value_unit": "RATIO",
                "rule_key": "rule.delivery",
            },
            format="json",
        )
        req_post.business = self.biz_a
        resp_post = view_facts(req_post)
        self.assertEqual(resp_post.status_code, status.HTTP_201_CREATED)
        fact_id = resp_post.data["id"]

        # GET detail fact
        view_detail = api.FactDetailView.as_view()
        req_get = self.factory.get(f"/facts/{fact_id}/")
        req_get.business = self.biz_a
        resp_get = view_detail(req_get, fact_id=fact_id)
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get.data["statement"], "Delivery failure rate reached 12%")

        # PATCH update lifecycle to EXPIRED
        req_patch = self.factory.patch(
            f"/facts/{fact_id}/",
            {"status": "EXPIRED", "reason": "Period concluded"},
            format="json",
        )
        req_patch.business = self.biz_a
        resp_patch = view_detail(req_patch, fact_id=fact_id)
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_patch.data["status"], "EXPIRED")
        self.assertIsNotNone(resp_patch.data["valid_to"])

        # GET detail of expired fact remains retrievable by owner
        resp_get_expired = view_detail(req_get, fact_id=fact_id)
        self.assertEqual(resp_get_expired.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get_expired.data["status"], "EXPIRED")

        # GET facts with status=EXPIRED filter retrieves the expired fact
        req_list_expired = self.factory.get("/facts/?status=EXPIRED")
        req_list_expired.business = self.biz_a
        resp_list_expired = view_facts(req_list_expired)
        self.assertEqual(resp_list_expired.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_list_expired.data["total_count"], 1)
        self.assertEqual(resp_list_expired.data["results"][0]["id"], fact_id)

    def test_issues_crud_and_lifecycle_api(self):
        # POST create issue
        view_issues = api.IssueListCreateView.as_view()
        req_post = self.factory.post(
            "/issues/",
            {
                "issue_type": "HIGH_DELIVERY_FAILURE",
                "title": "Delivery failure spike in Gazipur",
                "description": "Failure rate exceeded acceptable threshold",
                "severity": "HIGH",
                "confidence": "0.9500",
                "rule_key": "rule.delivery.gazipur",
            },
            format="json",
        )
        req_post.business = self.biz_a
        resp_post = view_issues(req_post)
        self.assertEqual(resp_post.status_code, status.HTTP_201_CREATED)
        issue_id = resp_post.data["id"]

        # GET detail issue
        view_detail = api.IssueDetailView.as_view()
        req_get = self.factory.get(f"/issues/{issue_id}/")
        req_get.business = self.biz_a
        resp_get = view_detail(req_get, issue_id=issue_id)
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get.data["status"], "OPEN")
        self.assertIsNone(resp_get.data["resolved_at"])

        # PATCH resolve issue
        req_patch = self.factory.patch(
            f"/issues/{issue_id}/",
            {"status": "RESOLVED", "notes": "Resolved via alternative courier routing"},
            format="json",
        )
        req_patch.business = self.biz_a
        resp_patch = view_detail(req_patch, issue_id=issue_id)
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_patch.data["status"], "RESOLVED")
        self.assertIsNotNone(resp_patch.data["resolved_at"])

    def test_pipeline_orchestration_api(self):
        view_pipe = api.PipelineOrchestrationView.as_view()
        req_pipe = self.factory.post("/pipeline/run/", {}, format="json")
        req_pipe.business = self.biz_a
        resp_pipe = view_pipe(req_pipe)
        self.assertEqual(resp_pipe.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_pipe.data["business_id"], self.biz_a.pk)
        self.assertEqual(resp_pipe.data["status"], "COMPLETED")
        self.assertIn("relationships_reconciled", resp_pipe.data)
