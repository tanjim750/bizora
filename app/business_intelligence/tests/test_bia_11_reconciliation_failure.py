"""Regression test for BIA-11:
When relationship reconciliation fails:
Answer HTTP 409 with code RELATIONSHIP_RECONCILIATION_FAILED and detail "Relationship reconciliation failed."
Never quote foreign or raw data/ids in the response. Log specifics on server only.
"""
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from app import models
from app.business_intelligence.relationships import RelationshipValidationError
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member


class ReconciliationFailureAntiOracleTests(APITestCase):
    def setUp(self):
        self.biz = models.Business.objects.create(name="Reconcile Biz", slug="reconcile-biz-test")
        self.owner = make_member(self.biz, "OWNER")
        self.api = client_for(self.owner)

    def test_reconciliation_failure_returns_409_with_generic_body_and_no_data_leak(self):
        leaked_message = "Customer 2 belongs to another business"
        with patch("app.business_intelligence.api.rebuild_relationships", side_effect=RelationshipValidationError(leaked_message)):
            resp = self.api.post(intelligence_url(self.biz.pk, "pipeline/run/"), {})

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        data = resp.json()
        self.assertEqual(data.get("code"), "RELATIONSHIP_RECONCILIATION_FAILED")
        self.assertEqual(data.get("detail"), "Relationship reconciliation failed.")
        self.assertNotIn(leaked_message, str(data))
        self.assertNotIn("Customer 2", str(data))
