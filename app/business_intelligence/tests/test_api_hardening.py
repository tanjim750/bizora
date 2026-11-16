"""BI-04, BI-05, BI-07: honest pipeline failures, read-only metric listing and validated request bodies."""

from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase

from app import models
from app.business_intelligence import metrics
from app.business_intelligence.metrics import MetricSnapshotConflictError
from app.business_intelligence.relationships import RelationshipConflictError, RelationshipValidationError
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


class HardeningFixture(TestCase):
    def setUp(self):
        self.business = models.Business.objects.create(
            name="Hardening shop", slug="hardening-shop", currency="BDT", created_at=T0, updated_at=T0)
        self.owner = client_for(make_member(self.business, "OWNER"))

    def url(self, tail):
        return intelligence_url(self.business.pk, tail)


class PipelineFailureTests(HardeningFixture):
    def test_successful_run_keeps_the_documented_response(self):
        response = self.owner.post(self.url("pipeline/run/"), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "COMPLETED")
        self.assertEqual(response.json()["quarantined_records"], 0)
        self.assertEqual(models.BusinessMetric.objects.filter(business=self.business).count(), 42)

    def test_rolled_back_reconciliation_is_a_failure_with_its_reason(self):
        with patch("app.business_intelligence.api.rebuild_relationships", side_effect=RelationshipValidationError("bad row 7")):
            response = self.owner.post(self.url("pipeline/run/"), {})
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["code"], "RELATIONSHIP_RECONCILIATION_FAILED")
        self.assertEqual(body["detail"], "Relationship reconciliation failed.")
        self.assertNotIn("bad row 7", body["detail"])
        self.assertNotIn("status", body)

    def test_conflicts_are_409_not_500(self):
        with patch("app.business_intelligence.api.rebuild_relationships", side_effect=RelationshipConflictError("clash")):
            response = self.owner.post(self.url("pipeline/run/"), {})
        self.assertEqual((response.status_code, response.json()["code"]), (409, "CONFLICT"))
        with patch("app.business_intelligence.api.sync_metric_registry", side_effect=MetricSnapshotConflictError("clash")):
            response = self.owner.post(self.url("pipeline/run/"), {})
        self.assertEqual((response.status_code, response.json()["code"]), (409, "CONFLICT"))
        self.assertNotIn("clash", response.json()["detail"])


class MetricListIsReadOnlyTests(HardeningFixture):
    def test_get_does_not_write_the_registry(self):
        response = self.owner.get(self.url("metrics/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_count"], 0)
        self.assertEqual(models.BusinessMetric.objects.count(), 0)

    def test_registry_is_seeded_by_the_pipeline_then_listed(self):
        self.owner.post(self.url("pipeline/run/"), {})
        self.assertEqual(self.owner.get(self.url("metrics/")).json()["total_count"], 42)

    def test_snapshots_of_an_unseeded_metric_are_a_404_until_the_registry_exists(self):
        key = "bi.metric.revenue_net.v1"
        self.assertEqual(self.owner.get(self.url(f"metrics/{key}/snapshots/")).status_code, 404)
        metrics.sync_metric_registry(business_id=self.business.pk)
        self.assertEqual(self.owner.get(self.url(f"metrics/{key}/snapshots/")).status_code, 200)


class RequestBodyValidationTests(HardeningFixture):
    FACT = {"statement": "Delivery failure rate reached 12%", "fact_type": "DELIVERY_FAILURE_RATE", "value": "0.1200",
            "value_unit": "RATIO", "rule_key": "rule.delivery"}
    ISSUE = {"issue_type": "HIGH_DELIVERY_FAILURE", "title": "Delivery failure spike", "confidence": "0.9500",
             "rule_key": "rule.delivery.gazipur"}

    def assert_rejected(self, call, path, body):
        response = call(self.url(path), body)
        self.assertEqual(response.status_code, 400, (body, response.content))
        self.assertEqual(response.json()["code"], "INVALID_DATA", (body, response.content))
        return response

    def test_fact_bodies(self):
        for body in (
            [self.FACT],
            "text",
            {},
            {**self.FACT, "statement": ""},
            {**self.FACT, "statement": None},
            {**self.FACT, "value": "abc"},
            {**self.FACT, "value": "NaN"},
            {**self.FACT, "value": "1" * 30},
            {**self.FACT, "evidence": ["not", "an", "object"]},
            {**self.FACT, "evidence": "text"},
            {**self.FACT, "fact_type": "T" * 101},
            {**self.FACT, "rule_key": "R" * 101},
        ):
            with self.subTest(body=body):
                self.assert_rejected(self.owner.post, "facts/", body)
        self.assertEqual(models.BusinessFact.all_objects.count(), 0)

    def test_valid_fact_bodies_still_work(self):
        self.assertEqual(self.owner.post(self.url("facts/"), self.FACT).status_code, 201)
        self.assertEqual(self.owner.post(self.url("facts/"), {"statement": "Plain statement"}).status_code, 201)
        numeric = self.owner.post(self.url("facts/"), {**self.FACT, "rule_key": "rule.numeric", "value": 0.12})
        self.assertEqual(numeric.status_code, 201)

    def test_issue_bodies(self):
        for body in (
            [self.ISSUE],
            {},
            {"title": "No type"},
            {"issue_type": "NO_TITLE"},
            {**self.ISSUE, "issue_type": ""},
            {**self.ISSUE, "issue_type": None},
            {**self.ISSUE, "confidence": "abc"},
            {**self.ISSUE, "confidence": "2"},
            {**self.ISSUE, "confidence": "-0.1"},
            {**self.ISSUE, "severity": ["HIGH"]},
            {**self.ISSUE, "fact_ids": "1,2"},
            {**self.ISSUE, "fact_ids": [0]},
            {**self.ISSUE, "fact_ids": ["x"]},
            {**self.ISSUE, "snapshot_ids": [1.5]},
            {**self.ISSUE, "snapshot_ids": {"a": 1}},
            {**self.ISSUE, "title": "T" * 256},
        ):
            with self.subTest(body=body):
                self.assert_rejected(self.owner.post, "issues/", body)
        self.assertEqual(models.BusinessIssue.objects.count(), 0)

    def test_valid_issue_body_still_works(self):
        self.assertEqual(self.owner.post(self.url("issues/"), self.ISSUE).status_code, 201)
        self.assertEqual(self.owner.post(self.url("issues/"), {"issue_type": "X", "title": "Minimal"}).status_code, 201)

    def test_lifecycle_bodies(self):
        fact = self.owner.post(self.url("facts/"), self.FACT).json()["id"]
        issue = self.owner.post(self.url("issues/"), self.ISSUE).json()["id"]
        for path in (f"facts/{fact}/", f"issues/{issue}/"):
            for body in ([], {}, "x", {"reason": "no status"}, {"status": None}, {"status": "S" * 31}):
                with self.subTest(path=path, body=body):
                    self.assert_rejected(self.owner.patch, path, body)
        self.assertEqual(self.owner.patch(self.url(f"facts/{fact}/"), {"status": "EXPIRED"}).status_code, 200)
        self.assertEqual(self.owner.patch(self.url(f"issues/{issue}/"), {"status": "RESOLVED"}).status_code, 200)

    def test_service_level_validation_errors_stay_400(self):
        self.assert_rejected(self.owner.post, "issues/", {**self.ISSUE, "severity": "SEVERE"})
        fact = self.owner.post(self.url("facts/"), self.FACT).json()["id"]
        self.assert_rejected(self.owner.patch, f"facts/{fact}/", {"status": "NOT_A_STATE"})
