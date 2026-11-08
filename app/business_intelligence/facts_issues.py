"""Business Facts, Business Issues, and Evidence Lifecycle services.

Serves Business Intelligence specification sections 15 (Business Facts),
16 (Fact Evidence), 17 (Business Issue Detection), and 18 (Issue Evidence)
for ticket T-011.

Key principles enforced:
1. Supported observations produce verified facts:
   - Facts are created only when deterministic analysis and evidence satisfy explicit rules.
   - Preserves rule traceability, validity period, confidence, and metric/relationship evidence.
2. Fact lifecycle:
   - States: CANDIDATE, VERIFIED, INVALIDATED, EXPIRED.
3. Issue lifecycle & resolution tracking:
   - States: OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED.
   - Records resolved_at timestamp when resolved/dismissed.
   - Preserves state transitions.
4. Separate severity and confidence:
   - Severity (LOW, MEDIUM, HIGH, CRITICAL) represents business impact.
   - Confidence (0 to 1) represents analytical certainty.
5. Safe repetition (Deduplication):
   - Re-evaluating an active condition updates existing OPEN/ACKNOWLEDGED issues
     rather than spamming duplicate records.
   - If an issue was previously RESOLVED or DISMISSED, a subsequent occurrence
     creates a fresh OPEN issue while preserving historical records.
6. Multi-tenant isolation:
   - All queries, creation, and state updates strictly enforce business scope.
"""

from decimal import Decimal
from typing import Any
import datetime

from django.db import transaction
from django.utils import timezone

from app import models


class FactError(Exception):
    """Base exception for Business Facts operations."""


class FactScopeError(FactError):
    """Fact does not belong to the requested business."""


class FactValidationError(FactError):
    """Fact parameters or constraints are invalid."""


class IssueError(Exception):
    """Base exception for Business Issues operations."""


class IssueScopeError(IssueError):
    """Issue does not belong to the requested business."""


class IssueValidationError(IssueError):
    """Issue parameters or constraints are invalid."""


# Fact Lifecycle States (BI §15)
FACT_STATUS_CANDIDATE = "CANDIDATE"
FACT_STATUS_VERIFIED = "VERIFIED"
FACT_STATUS_INVALIDATED = "INVALIDATED"
FACT_STATUS_EXPIRED = "EXPIRED"
FACT_STATUSES = frozenset({
    FACT_STATUS_CANDIDATE,
    FACT_STATUS_VERIFIED,
    FACT_STATUS_INVALIDATED,
    FACT_STATUS_EXPIRED,
})

# Documented Fact Types (BI §15)
FACT_TYPE_REVENUE_CHANGE = "REVENUE_CHANGE"
FACT_TYPE_DELIVERY_FAILURE_RATE = "DELIVERY_FAILURE_RATE"
FACT_TYPE_CAMPAIGN_PERFORMANCE = "CAMPAIGN_PERFORMANCE"
FACT_TYPE_CONVERSION_DECLINE = "CONVERSION_DECLINE"
FACT_TYPE_SUPPORT_DELAY = "SUPPORT_DELAY"
FACT_TYPE_CUSTOMER_LTV = "CUSTOMER_LTV"
FACT_TYPE_ANOMALY_DETECTED = "ANOMALY_DETECTED"

# Issue Severities (BI §17)
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"
ISSUE_SEVERITIES = frozenset({
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
})

# Issue Lifecycle States (BI §17)
ISSUE_STATUS_OPEN = "OPEN"
ISSUE_STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
ISSUE_STATUS_RESOLVED = "RESOLVED"
ISSUE_STATUS_DISMISSED = "DISMISSED"
ISSUE_STATUSES = frozenset({
    ISSUE_STATUS_OPEN,
    ISSUE_STATUS_ACKNOWLEDGED,
    ISSUE_STATUS_RESOLVED,
    ISSUE_STATUS_DISMISSED,
})

# Documented Issue Types (BI §17)
ISSUE_TYPE_HIGH_DELIVERY_FAILURE = "HIGH_DELIVERY_FAILURE"
ISSUE_TYPE_LOW_CAMPAIGN_ROAS = "LOW_CAMPAIGN_ROAS"
ISSUE_TYPE_HIGH_CART_ABANDONMENT = "HIGH_CART_ABANDONMENT"
ISSUE_TYPE_SUPPORT_RESPONSE_DELAY = "SUPPORT_RESPONSE_DELAY"
ISSUE_TYPE_REVENUE_DECLINE = "REVENUE_DECLINE"
DOCUMENTED_ISSUE_TYPES = frozenset({
    ISSUE_TYPE_HIGH_DELIVERY_FAILURE,
    ISSUE_TYPE_LOW_CAMPAIGN_ROAS,
    ISSUE_TYPE_HIGH_CART_ABANDONMENT,
    ISSUE_TYPE_SUPPORT_RESPONSE_DELAY,
    ISSUE_TYPE_REVENUE_DECLINE,
})


def create_or_update_fact(
    *,
    business_id: int,
    fact_type: str,
    statement: str,
    value: Decimal | None = None,
    value_unit: str | None = None,
    confidence: Decimal = Decimal("1.0000"),
    status: str = FACT_STATUS_VERIFIED,
    rule_key: str | None = None,
    subject_entity_type: str | None = None,
    subject_entity_id: int | None = None,
    valid_from: datetime.datetime | None = None,
    valid_to: datetime.datetime | None = None,
    detected_at: datetime.datetime | None = None,
    evidence: dict[str, Any] | None = None,
) -> tuple[models.BusinessFact, bool]:
    """Create or update a verified business fact. Idempotent and scoped."""
    if not isinstance(business_id, int) or business_id <= 0:
        raise FactValidationError("business_id must be a positive integer")

    if not statement or not statement.strip():
        raise FactValidationError("Fact statement cannot be empty")

    status = (status or FACT_STATUS_VERIFIED).upper()
    if status not in FACT_STATUSES:
        raise FactValidationError(f"Invalid fact status {status!r}; expected one of {sorted(FACT_STATUSES)}")

    if not (Decimal("0.0000") <= confidence <= Decimal("1.0000")):
        raise FactValidationError("confidence must be between 0 and 1")

    now = timezone.now()
    detected = detected_at or now

    metadata = dict(evidence or {})

    with transaction.atomic():
        # Look for existing fact matching scope, rule, type, entity, and validity
        lookup_kwargs = {
            "business_id": business_id,
            "fact_type": fact_type,
            "rule_key": rule_key,
            "subject_entity_type": subject_entity_type,
            "subject_entity_id": subject_entity_id,
            "valid_from": valid_from,
            "valid_to": valid_to,
        }
        fact = models.BusinessFact.all_objects.filter(**lookup_kwargs).first()

        if fact is not None:
            # Update in place
            fact.statement = statement
            fact.value = value
            fact.value_unit = value_unit
            fact.confidence = confidence
            fact.status = status
            fact.detected_at = detected
            fact.metadata = metadata
            fact.updated_at = now
            fact.save()
            return fact, False

        fact = models.BusinessFact.all_objects.create(
            business_id=business_id,
            fact_type=fact_type,
            subject_entity_type=subject_entity_type,
            subject_entity_id=subject_entity_id,
            statement=statement,
            value=value,
            value_unit=value_unit,
            confidence=confidence,
            status=status,
            rule_key=rule_key,
            valid_from=valid_from,
            valid_to=valid_to,
            detected_at=detected,
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )
        return fact, True


def update_fact_lifecycle(
    *,
    business_id: int,
    fact_id: int,
    new_status: str,
    reason: str | None = None,
) -> models.BusinessFact:
    """Transition a fact's lifecycle state (CANDIDATE, VERIFIED, INVALIDATED, EXPIRED)."""
    if not isinstance(business_id, int) or business_id <= 0:
        raise FactValidationError("business_id must be a positive integer")

    new_status = (new_status or "").upper()
    if new_status not in FACT_STATUSES:
        raise FactValidationError(f"Invalid fact status {new_status!r}; expected one of {sorted(FACT_STATUSES)}")

    fact = models.BusinessFact.all_objects.filter(pk=fact_id).first()
    if fact is None:
        raise FactValidationError(f"BusinessFact #{fact_id} does not exist.")

    if fact.business_id != business_id:
        raise FactScopeError(f"BusinessFact #{fact_id} belongs to business {fact.business_id}, not {business_id}.")

    now = timezone.now()
    fact.status = new_status
    fact.updated_at = now
    if reason:
        meta = dict(fact.metadata or {})
        meta["status_change_reason"] = reason
        fact.metadata = meta

    if new_status == FACT_STATUS_EXPIRED and fact.valid_to is None:
        fact.valid_to = now

    fact.save()
    return fact


def create_or_update_issue(
    *,
    business_id: int,
    issue_type: str,
    title: str,
    description: str | None = None,
    severity: str = SEVERITY_MEDIUM,
    confidence: Decimal = Decimal("1.0000"),
    rule_key: str | None = None,
    subject_entity_type: str | None = None,
    subject_entity_id: int | None = None,
    detected_at: datetime.datetime | None = None,
    fact_ids: list[int] | None = None,
    snapshot_ids: list[int] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[models.BusinessIssue, bool]:
    """Create or update a detected business issue.

    Safe repetition rule:
    - If an issue with identical (business_id, rule_key, issue_type, entity) is currently
      OPEN or ACKNOWLEDGED, updates the existing issue (detected_at, evidence links, severity)
      without creating duplicate rows.
    - If the previous issue is RESOLVED or DISMISSED, a subsequent occurrence creates
      a new active OPEN issue, preserving historical resolution tracking.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise IssueValidationError("business_id must be a positive integer")

    if not title or not title.strip():
        raise IssueValidationError("Issue title cannot be empty")

    severity = (severity or SEVERITY_MEDIUM).upper()
    if severity not in ISSUE_SEVERITIES:
        raise IssueValidationError(f"Invalid severity {severity!r}; expected one of {sorted(ISSUE_SEVERITIES)}")

    if not (Decimal("0.0000") <= confidence <= Decimal("1.0000")):
        raise IssueValidationError("confidence must be between 0 and 1")

    now = timezone.now()
    detected = detected_at or now

    meta = dict(metadata or {})
    if fact_ids:
        meta["fact_ids"] = sorted(set(fact_ids))
    if snapshot_ids:
        meta["snapshot_ids"] = sorted(set(snapshot_ids))

    with transaction.atomic():
        # Check for currently ACTIVE issue (OPEN or ACKNOWLEDGED)
        active_issue = models.BusinessIssue.objects.filter(
            business_id=business_id,
            issue_type=issue_type,
            rule_key=rule_key,
            subject_entity_type=subject_entity_type,
            subject_entity_id=subject_entity_id,
            status__in=[ISSUE_STATUS_OPEN, ISSUE_STATUS_ACKNOWLEDGED],
        ).first()

        if active_issue is not None:
            # Update existing active issue safely
            active_issue.title = title
            active_issue.description = description or active_issue.description
            active_issue.severity = severity
            active_issue.confidence = confidence
            active_issue.detected_at = detected

            # Merge evidence links in metadata
            existing_meta = dict(active_issue.metadata or {})
            combined_facts = set(existing_meta.get("fact_ids", [])) | set(meta.get("fact_ids", []))
            combined_snaps = set(existing_meta.get("snapshot_ids", [])) | set(meta.get("snapshot_ids", []))
            existing_meta.update(meta)
            if combined_facts:
                existing_meta["fact_ids"] = sorted(combined_facts)
            if combined_snaps:
                existing_meta["snapshot_ids"] = sorted(combined_snaps)

            active_issue.metadata = existing_meta
            active_issue.updated_at = now
            active_issue.save()
            return active_issue, False

        # No active issue found (or previous was RESOLVED/DISMISSED): create fresh OPEN issue
        new_issue = models.BusinessIssue.objects.create(
            business_id=business_id,
            issue_type=issue_type,
            subject_entity_type=subject_entity_type,
            subject_entity_id=subject_entity_id,
            title=title,
            description=description,
            severity=severity,
            confidence=confidence,
            status=ISSUE_STATUS_OPEN,
            rule_key=rule_key,
            detected_at=detected,
            resolved_at=None,
            metadata=meta or None,
            created_at=now,
            updated_at=now,
        )
        return new_issue, True


def update_issue_lifecycle(
    *,
    business_id: int,
    issue_id: int,
    new_status: str,
    resolution_notes: str | None = None,
) -> models.BusinessIssue:
    """Transition an issue's operational state (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED).

    Sets resolved_at when transitioning to RESOLVED or DISMISSED.
    Clears resolved_at when reopening to OPEN or ACKNOWLEDGED.
    """
    if not isinstance(business_id, int) or business_id <= 0:
        raise IssueValidationError("business_id must be a positive integer")

    new_status = (new_status or "").upper()
    if new_status not in ISSUE_STATUSES:
        raise IssueValidationError(f"Invalid issue status {new_status!r}; expected one of {sorted(ISSUE_STATUSES)}")

    issue = models.BusinessIssue.objects.filter(pk=issue_id).first()
    if issue is None:
        raise IssueValidationError(f"BusinessIssue #{issue_id} does not exist.")

    if issue.business_id != business_id:
        raise IssueScopeError(f"BusinessIssue #{issue_id} belongs to business {issue.business_id}, not {business_id}.")

    now = timezone.now()
    issue.status = new_status
    issue.updated_at = now

    if new_status in (ISSUE_STATUS_RESOLVED, ISSUE_STATUS_DISMISSED):
        issue.resolved_at = now
    else:
        issue.resolved_at = None

    if resolution_notes:
        meta = dict(issue.metadata or {})
        meta["resolution_notes"] = resolution_notes
        issue.metadata = meta

    issue.save()
    return issue


__all__ = [
    "DOCUMENTED_ISSUE_TYPES",
    "FACT_STATUSES",
    "FACT_STATUS_CANDIDATE",
    "FACT_STATUS_EXPIRED",
    "FACT_STATUS_INVALIDATED",
    "FACT_STATUS_VERIFIED",
    "FACT_TYPE_ANOMALY_DETECTED",
    "FACT_TYPE_CAMPAIGN_PERFORMANCE",
    "FACT_TYPE_CONVERSION_DECLINE",
    "FACT_TYPE_CUSTOMER_LTV",
    "FACT_TYPE_DELIVERY_FAILURE_RATE",
    "FACT_TYPE_REVENUE_CHANGE",
    "FACT_TYPE_SUPPORT_DELAY",
    "FactError",
    "FactScopeError",
    "FactValidationError",
    "ISSUE_SEVERITIES",
    "ISSUE_STATUSES",
    "ISSUE_STATUS_ACKNOWLEDGED",
    "ISSUE_STATUS_DISMISSED",
    "ISSUE_STATUS_OPEN",
    "ISSUE_STATUS_RESOLVED",
    "ISSUE_TYPE_HIGH_CART_ABANDONMENT",
    "ISSUE_TYPE_HIGH_DELIVERY_FAILURE",
    "ISSUE_TYPE_LOW_CAMPAIGN_ROAS",
    "ISSUE_TYPE_REVENUE_DECLINE",
    "ISSUE_TYPE_SUPPORT_RESPONSE_DELAY",
    "IssueError",
    "IssueScopeError",
    "IssueValidationError",
    "SEVERITY_CRITICAL",
    "SEVERITY_HIGH",
    "SEVERITY_LOW",
    "SEVERITY_MEDIUM",
    "create_or_update_fact",
    "create_or_update_issue",
    "update_fact_lifecycle",
    "update_issue_lifecycle",
]
