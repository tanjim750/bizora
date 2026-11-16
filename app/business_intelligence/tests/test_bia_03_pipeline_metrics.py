"""Regression test for BIA-03:
POST pipeline/run/ must compute metric snapshots using existing calculators for the default period (current UTC month).
Response must keep existing keys, have status "COMPLETED", and include "metrics_computed" (int).
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from app import models
from app.business_intelligence.pipeline import default_period
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member


class PipelineMetricsCalculationTests(APITestCase):
    def setUp(self):
        self.biz = models.Business.objects.create(name="Pipeline Biz", slug="pipeline-biz-test")
        self.owner = make_member(self.biz, "OWNER")
        self.api = client_for(self.owner)

    def test_pipeline_run_computes_metric_snapshots_for_default_period(self):
        # Before pipeline run: no snapshots exist
        self.assertEqual(models.MetricSnapshot.objects.filter(business=self.biz).count(), 0)

        resp = self.api.post(intelligence_url(self.biz.pk, "pipeline/run/"), {})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        # Check existing keys are preserved
        self.assertEqual(data["business_id"], self.biz.pk)
        self.assertEqual(data["status"], "COMPLETED")
        self.assertIn("relationships_reconciled", data)
        self.assertIn("quarantined_records", data)
        self.assertIn("active_facts_count", data)
        self.assertIn("open_issues_count", data)

        # Check allowed addition: metrics_computed
        self.assertIn("metrics_computed", data)
        self.assertIsInstance(data["metrics_computed"], int)
        self.assertGreater(data["metrics_computed"], 0)

        # Verify snapshots actually exist in the database for the default period
        period_type, start, end = default_period()
        snapshots = models.MetricSnapshot.objects.filter(
            business=self.biz,
            period_type=period_type,
            period_start=start,
            period_end=end,
        )
        self.assertEqual(snapshots.count(), data["metrics_computed"])
        self.assertGreater(snapshots.count(), 0)
