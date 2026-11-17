from datetime import datetime, timezone
from decimal import Decimal

from django.test import TestCase

from app import models
from app.business_intelligence import (
    ISSUE_SEVERITY_MEDIUM,
    ISSUE_STATUS_OPEN,
    ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
    create_or_update_issue,
)


class BusinessIssuePersistenceTests(TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        self.biz = models.Business.objects.create(
            name="Test Biz",
            slug="test-biz",
            created_at=now,
            updated_at=now,
        )

    def test_two_open_issues_same_type_different_rule_keys_persist(self):
        """Card BIA-04: Two OPEN issues, same type, different rule keys both persist."""
        now = datetime.now(timezone.utc)

        # Create first OPEN issue with rule_key "k1"
        issue1 = models.BusinessIssue.objects.create(
            business=self.biz,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            rule_key="bi.rule.k1",
            title="Low ROAS Rule 1",
            severity=ISSUE_SEVERITY_MEDIUM,
            confidence=Decimal("1.0000"),
            status=ISSUE_STATUS_OPEN,
            detected_at=now,
        )

        # Create second OPEN issue with same issue_type but rule_key "k2"
        issue2 = models.BusinessIssue.objects.create(
            business=self.biz,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            rule_key="bi.rule.k2",
            title="Low ROAS Rule 2",
            severity=ISSUE_SEVERITY_MEDIUM,
            confidence=Decimal("1.0000"),
            status=ISSUE_STATUS_OPEN,
            detected_at=now,
        )

        self.assertIsNotNone(issue1.pk)
        self.assertIsNotNone(issue2.pk)
        self.assertNotEqual(
            issue1.pk,
            issue2.pk,
            "Issue with rule_key 'k2' adopted pk of issue with rule_key 'k1'",
        )

        open_issues = models.BusinessIssue.objects.filter(
            business=self.biz,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            status=ISSUE_STATUS_OPEN,
        )
        self.assertEqual(open_issues.count(), 2)

        persisted_k1 = models.BusinessIssue.objects.get(pk=issue1.pk)
        persisted_k2 = models.BusinessIssue.objects.get(pk=issue2.pk)
        self.assertEqual(persisted_k1.rule_key, "bi.rule.k1")
        self.assertEqual(persisted_k2.rule_key, "bi.rule.k2")

    def test_create_or_update_issue_distinct_rule_keys_persist(self):
        """create_or_update_issue should persist distinct active issues when rule_keys differ."""
        issue1, created1 = create_or_update_issue(
            business_id=self.biz.pk,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            title="Low ROAS Campaign A",
            rule_key="bi.rule.k1",
        )
        self.assertTrue(created1)

        issue2, created2 = create_or_update_issue(
            business_id=self.biz.pk,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            title="Low ROAS Campaign B",
            rule_key="bi.rule.k2",
        )
        self.assertTrue(created2)
        self.assertNotEqual(issue1.pk, issue2.pk)

        count = models.BusinessIssue.objects.filter(
            business=self.biz,
            issue_type=ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
            status=ISSUE_STATUS_OPEN,
        ).count()
        self.assertEqual(count, 2)
