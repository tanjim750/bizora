"""Requirement-linked tests for BI §15, §16, §17, §18 (Facts, Issues, and Evidence Lifecycle) - Ticket T-011.

Tests verify:
1. Structured fact creation with rule traceability and evidence linking (BI §15 & §16).
2. Fact lifecycle transitions (CANDIDATE, VERIFIED, INVALIDATED, EXPIRED) and expiry timestamping.
3. Business issue detection with separate severity and confidence (BI §17 & §18).
4. Safe repetition and deduplication (updating active issues, fresh rows for historical resolved issues).
5. Issue lifecycle state preservation (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED) and resolution tracking (resolved_at).
6. Documented issue classifications (HIGH_DELIVERY_FAILURE, LOW_CAMPAIGN_ROAS, etc.).
7. Cross-tenant business isolation and error enforcement.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import (
    DOCUMENTED_ISSUE_TYPES,
    FACT_STATUS_CANDIDATE,
    FACT_STATUS_EXPIRED,
    FACT_STATUS_VERIFIED,
    FACT_TYPE_CUSTOMER_LTV,
    FACT_TYPE_DELIVERY_FAILURE_RATE,
    FACT_TYPE_REVENUE_CHANGE,
    FactScopeError,
    FactValidationError,
    ISSUE_SEVERITY_HIGH,
    ISSUE_SEVERITY_MEDIUM,
    ISSUE_STATUS_ACKNOWLEDGED,
    ISSUE_STATUS_OPEN,
    ISSUE_STATUS_RESOLVED,
    ISSUE_TYPE_HIGH_DELIVERY_FAILURE,
    ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
    ISSUE_TYPE_REVENUE_DECLINE,
    IssueScopeError,
    create_or_update_fact,
    create_or_update_issue,
    update_fact_lifecycle,
    update_issue_lifecycle,
)


D = Decimal
START = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
END = START + timedelta(days=7)


class FactsAndIssuesTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.biz_a = models.Business.objects.create(
            name="Shop A", slug="shop-a", currency="BDT", created_at=START, updated_at=START
        )
        self.biz_b = models.Business.objects.create(
            name="Shop B", slug="shop-b", currency="BDT", created_at=START, updated_at=START
        )

    def test_verified_fact_creation_and_evidence(self):
        fact, created = create_or_update_fact(
            business_id=self.biz_a.pk,
            fact_type=FACT_TYPE_DELIVERY_FAILURE_RATE,
            statement="Delivery failure rate in Gazipur reached 17%",
            value=D("0.1700"),
            value_unit="RATIO",
            confidence=D("0.9500"),
            status=FACT_STATUS_VERIFIED,
            rule_key="bi.rule.delivery_anomaly",
            subject_entity_type="REGION",
            subject_entity_id=101,
            valid_from=START,
            valid_to=END,
            evidence={"previous_rate": "0.0900", "courier": "Pathao", "metric_snapshot_id": 42},
        )
        self.assertTrue(created)
        self.assertEqual(fact.business_id, self.biz_a.pk)
        self.assertEqual(fact.status, FACT_STATUS_VERIFIED)
        self.assertEqual(fact.value, D("0.1700"))
        self.assertEqual(fact.metadata["courier"], "Pathao")

        # Idempotent replay: updates in place, returns created=False
        fact2, created2 = create_or_update_fact(
            business_id=self.biz_a.pk,
            fact_type=FACT_TYPE_DELIVERY_FAILURE_RATE,
            statement="Delivery failure rate in Gazipur updated to 18%",
            value=D("0.1800"),
            value_unit="RATIO",
            confidence=D("0.9600"),
            status=FACT_STATUS_VERIFIED,
            rule_key="bi.rule.delivery_anomaly",
            subject_entity_type="REGION",
            subject_entity_id=101,
            valid_from=START,
            valid_to=END,
        )
        self.assertFalse(created2)
        self.assertEqual(fact2.pk, fact.pk)
        self.assertEqual(fact2.value, D("0.1800"))

    def test_fact_lifecycle_transitions(self):
        fact, _ = create_or_update_fact(
            business_id=self.biz_a.pk,
            fact_type=FACT_TYPE_REVENUE_CHANGE,
            statement="Revenue decreased by 12%",
            status=FACT_STATUS_CANDIDATE,
        )
        self.assertEqual(fact.status, FACT_STATUS_CANDIDATE)

        # Transition to VERIFIED
        fact_v = update_fact_lifecycle(
            business_id=self.biz_a.pk,
            fact_id=fact.pk,
            new_status=FACT_STATUS_VERIFIED,
            reason="Confirmed by reconciliation",
        )
        self.assertEqual(fact_v.status, FACT_STATUS_VERIFIED)
        self.assertEqual(fact_v.metadata["status_change_reason"], "Confirmed by reconciliation")

        # Transition to EXPIRED sets valid_to
        fact_exp = update_fact_lifecycle(
            business_id=self.biz_a.pk,
            fact_id=fact.pk,
            new_status=FACT_STATUS_EXPIRED,
        )
        self.assertEqual(fact_exp.status, FACT_STATUS_EXPIRED)
        self.assertIsNotNone(fact_exp.valid_to)

        # Invalid status rejected
        with self.assertRaises(FactValidationError):
            update_fact_lifecycle(
                business_id=self.biz_a.pk,
                fact_id=fact.pk,
                new_status="UNKNOWN_STATUS",
            )

    def test_issue_detection_separate_severity_and_confidence(self):
        issue, created = create_or_update_issue(
            business_id=self.biz_a.pk,
            issue_type=ISSUE_TYPE_HIGH_DELIVERY_FAILURE,
            title="High delivery failure rate in Gazipur",
            description="Failure rate jumped to 17% exceeding 10% threshold",
            severity=ISSUE_SEVERITY_HIGH,
            confidence=D("0.9500"),
            rule_key="bi.issue_rule.high_delivery_failure",
            subject_entity_type="REGION",
            subject_entity_id=101,
            fact_ids=[1, 2],
            snapshot_ids=[10, 20],
        )
        self.assertTrue(created)
        self.assertEqual(issue.status, ISSUE_STATUS_OPEN)
        self.assertEqual(issue.severity, ISSUE_SEVERITY_HIGH)
        self.assertEqual(issue.confidence, D("0.9500"))
        self.assertIsNone(issue.resolved_at)
        self.assertEqual(issue.metadata["fact_ids"], [1, 2])
        self.assertEqual(issue.metadata["snapshot_ids"], [10, 20])

    def test_safe_repetition_and_deduplication(self):
        # 1. Create active OPEN issue
        issue1, created1 = create_or_update_issue(
            business_id=self.biz_a.pk,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            title="Low ROAS on Meta Fall Campaign",
            severity=ISSUE_SEVERITY_MEDIUM,
            rule_key="bi.issue.roas",
            subject_entity_type="CAMPAIGN",
            subject_entity_id=55,
            fact_ids=[10],
        )
        self.assertTrue(created1)

        # 2. Re-detect while OPEN: updates existing issue in place without duplicate row!
        issue2, created2 = create_or_update_issue(
            business_id=self.biz_a.pk,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            title="Low ROAS on Meta Fall Campaign - Escalated",
            severity=ISSUE_SEVERITY_HIGH,
            rule_key="bi.issue.roas",
            subject_entity_type="CAMPAIGN",
            subject_entity_id=55,
            fact_ids=[11],
        )
        self.assertFalse(created2)
        self.assertEqual(issue2.pk, issue1.pk)
        self.assertEqual(issue2.severity, ISSUE_SEVERITY_HIGH)
        self.assertEqual(issue2.metadata["fact_ids"], [10, 11])
        self.assertEqual(models.BusinessIssue.objects.filter(business=self.biz_a).count(), 1)

        # 3. Acknowledge issue and re-detect: preserves ACKNOWLEDGED status!
        update_issue_lifecycle(
            business_id=self.biz_a.pk,
            issue_id=issue1.pk,
            new_status=ISSUE_STATUS_ACKNOWLEDGED,
        )
        issue3, created3 = create_or_update_issue(
            business_id=self.biz_a.pk,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            title="Low ROAS on Meta Fall Campaign",
            rule_key="bi.issue.roas",
            subject_entity_type="CAMPAIGN",
            subject_entity_id=55,
        )
        self.assertFalse(created3)
        self.assertEqual(issue3.status, ISSUE_STATUS_ACKNOWLEDGED)

        # 4. Resolve issue: sets resolved_at
        issue_res = update_issue_lifecycle(
            business_id=self.biz_a.pk,
            issue_id=issue1.pk,
            new_status=ISSUE_STATUS_RESOLVED,
            resolution_notes="Budget adjusted, ROAS restored",
        )
        self.assertEqual(issue_res.status, ISSUE_STATUS_RESOLVED)
        self.assertIsNotNone(issue_res.resolved_at)

        # 5. Subsequent detection after RESOLVED creates a new fresh OPEN issue
        # while preserving historical resolved issue!
        issue4, created4 = create_or_update_issue(
            business_id=self.biz_a.pk,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            title="Low ROAS on Meta Fall Campaign (Recurring)",
            severity=ISSUE_SEVERITY_HIGH,
            rule_key="bi.issue.roas",
            subject_entity_type="CAMPAIGN",
            subject_entity_id=55,
        )
        self.assertTrue(created4)
        self.assertNotEqual(issue4.pk, issue1.pk)
        self.assertEqual(issue4.status, ISSUE_STATUS_OPEN)
        self.assertIsNone(issue4.resolved_at)
        self.assertEqual(models.BusinessIssue.objects.filter(business=self.biz_a).count(), 2)

    def test_documented_issue_types(self):
        # Verify all 5 documented issue types can be detected
        for itype in DOCUMENTED_ISSUE_TYPES:
            issue, _ = create_or_update_issue(
                business_id=self.biz_a.pk,
                issue_type=itype,
                title=f"Test issue for {itype}",
                rule_key=f"rule.{itype}",
            )
            self.assertEqual(issue.issue_type, itype)

    def test_cross_tenant_isolation(self):
        fact_a, _ = create_or_update_fact(
            business_id=self.biz_a.pk,
            fact_type=FACT_TYPE_CUSTOMER_LTV,
            statement="Shop A Fact",
        )
        with self.assertRaises(FactScopeError):
            update_fact_lifecycle(
                business_id=self.biz_b.pk,
                fact_id=fact_a.pk,
                new_status=FACT_STATUS_EXPIRED,
            )

        issue_a, _ = create_or_update_issue(
            business_id=self.biz_a.pk,
            issue_type=ISSUE_TYPE_REVENUE_DECLINE,
            title="Shop A Issue",
        )
        with self.assertRaises(IssueScopeError):
            update_issue_lifecycle(
                business_id=self.biz_b.pk,
                issue_id=issue_a.pk,
                new_status=ISSUE_STATUS_RESOLVED,
            )
