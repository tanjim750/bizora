"""Regression tests for BIA-05:
Fact POST overwrites unkeyed facts (upsert on type, rule_key null...),
no subject/validity/confidence input, no evidence rows, manual facts default VERIFIED.
"""
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from app import models
from app.tests.bi_graph_helpers import client_for, intelligence_url, make_member


class FactPostUnkeyedEvidenceTests(APITestCase):
    def setUp(self):
        self.biz = models.Business.objects.create(name="Fact Test Biz")
        self.owner = make_member(self.biz, "OWNER")
        self.api = client_for(self.owner)

    def url(self, tail="facts/"):
        return intelligence_url(self.biz.pk, tail)

    def test_two_unkeyed_posts_create_two_rows(self):
        resp1 = self.api.post(self.url(), {"statement": "Fact One", "fact_type": "GENERAL"}, format="json")
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        resp2 = self.api.post(self.url(), {"statement": "Fact Two", "fact_type": "GENERAL"}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)

        facts = models.BusinessFact.all_objects.filter(business_id=self.biz.pk)
        self.assertEqual(facts.count(), 2, f"Expected 2 rows, found {facts.count()}")
        self.assertNotEqual(resp1.json()["id"], resp2.json()["id"])

    def test_manual_fact_without_evidence_defaults_to_candidate(self):
        resp = self.api.post(self.url(), {"statement": "Unverified claim"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        fact = models.BusinessFact.all_objects.get(pk=resp.json()["id"])
        self.assertEqual(fact.status, "CANDIDATE")

    def test_manual_fact_with_evidence_defaults_to_verified_and_creates_evidence_row(self):
        resp = self.api.post(
            self.url(),
            {
                "statement": "Verified revenue claim",
                "evidence": {"source": "bank_statement", "account_ref": "ACC-123"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        fact = models.BusinessFact.all_objects.get(pk=resp.json()["id"])
        self.assertEqual(fact.status, "VERIFIED")

        evidence_rows = models.BusinessFactEvidence.objects.filter(business_fact=fact)
        self.assertTrue(evidence_rows.exists(), "Expected BusinessFactEvidence row to be created")

    def test_post_accepts_subject_validity_confidence(self):
        now = timezone.now()
        resp = self.api.post(
            self.url(),
            {
                "statement": "Order shipped on time",
                "subject_entity_type": "ORDER",
                "subject_entity_id": 99,
                "confidence": "0.8500",
                "valid_from": now.isoformat(),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        fact = models.BusinessFact.all_objects.get(pk=resp.json()["id"])
        self.assertEqual(fact.subject_entity_type, "ORDER")
        self.assertEqual(fact.subject_entity_id, 99)
        self.assertEqual(fact.confidence, Decimal("0.8500"))
