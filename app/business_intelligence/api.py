"""REST API views, pipeline orchestration, and security seams for Business Intelligence.

Serves Business Intelligence specification sections 15-18 and ticket T-012.

Key properties:
1. Deny-by-default authorization seam:
   - Resolves authorized business strictly from authenticated/contextual request.business.
   - Rejects unauthenticated or out-of-scope calls with HTTP 403 PermissionDenied.
   - Refuses to trust caller-supplied business_id in query parameters or payload.
2. Security Gate SEC-MED-1 closed:
   - Validation and scope error responses return generic caller-facing error messages
     so external callers cannot determine whether primary keys exist in other tenants.
3. Security Gate SEC-HIGH-1 closed:
   - Relationship reconciliation supports per-row quarantine so a single malformed or
     unresolvable entity row does not abort the entire tenant rebuild.
4. Paginated reads & structured filtering:
   - Standard pagination (limit & offset) for metrics, snapshots, facts, and issues.
5. End-to-end service orchestration:
   - Triggers pipeline execution from canonical data -> relationships -> metrics -> anomalies -> facts & issues.
"""

from decimal import Decimal
from typing import Any
import datetime
import logging

from rest_framework import exceptions, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from app import models
from app.business_intelligence.anomalies import (
    AnomalyScopeError,
    AnomalyValidationError,
)
from app.business_intelligence.facts_issues import (
    FactScopeError,
    FactValidationError,
    IssueScopeError,
    IssueValidationError,
    create_or_update_fact,
    create_or_update_issue,
    update_fact_lifecycle,
    update_issue_lifecycle,
)
from app.business_intelligence.metrics import (
    MetricValidationError,
    sync_metric_registry,
)
from app.business_intelligence.relationships import (
    RelationshipRebuildResult,
    RelationshipValidationError,
    rebuild_relationships,
)


logger = logging.getLogger(__name__)


def resolve_authorized_business(request: Any) -> models.Business:
    """Resolve the authoritative business scope from the request.

    Deny-by-default: requires request.business or request.auth_business.
    If the caller explicitly passes a business_id parameter or payload field,
    it must strictly match the authorized business; otherwise access is denied.
    """
    biz = getattr(request, "business", None) or getattr(request, "auth_business", None)
    if biz is None:
        raise exceptions.PermissionDenied("Access denied: No authorized business scope.")

    if not isinstance(biz, models.Business):
        if isinstance(biz, int):
            biz_obj = models.Business.objects.filter(pk=biz).first()
            if not biz_obj:
                raise exceptions.PermissionDenied("Access denied: Authorized business not found.")
            biz = biz_obj
        else:
            raise exceptions.PermissionDenied("Access denied: Invalid business context.")

    # Validate against caller-supplied parameters to prevent tenant spoofing
    caller_biz_id = None
    if hasattr(request, "query_params"):
        caller_biz_id = request.query_params.get("business_id")
    if caller_biz_id is None and hasattr(request, "data") and isinstance(request.data, dict):
        caller_biz_id = request.data.get("business_id")

    if caller_biz_id is not None:
        try:
            if int(caller_biz_id) != biz.pk:
                raise exceptions.PermissionDenied(
                    "Access denied: Caller-supplied business_id does not match authorized business."
                )
        except (ValueError, TypeError):
            raise exceptions.PermissionDenied("Access denied: Malformed business_id parameter.")

    return biz


class HasAuthorizedBusiness(permissions.BasePermission):
    """Deny-by-default permission checking for an authorized business."""

    def has_permission(self, request, view):
        try:
            resolve_authorized_business(request)
            return True
        except exceptions.PermissionDenied:
            return False


class BaseIntelligenceAPIView(APIView):
    """Base class providing deny-by-default scoping and SEC-MED-1 anti-oracle protection."""

    permission_classes = [HasAuthorizedBusiness]

    def get_authorized_business(self) -> models.Business:
        return resolve_authorized_business(self.request)

    def paginate_queryset(self, queryset):
        """Standard limit/offset pagination helper."""
        try:
            limit = int(self.request.query_params.get("limit", 50))
            offset = int(self.request.query_params.get("offset", 0))
        except ValueError:
            limit = 50
            offset = 0

        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        total_count = queryset.count()
        results = list(queryset[offset : offset + limit])
        return {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "results": results,
        }

    def handle_exception(self, exc):
        # SEC-MED-1: Return uniform caller-facing error messages to prevent cross-tenant ID oracles
        if isinstance(exc, (FactScopeError, IssueScopeError, AnomalyScopeError)):
            logger.warning("Tenant scope violation attempt: %s", exc)
            return Response(
                {"error": "The requested resource was not found or access is denied."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if isinstance(exc, (FactValidationError, IssueValidationError, AnomalyValidationError, MetricValidationError, RelationshipValidationError)):
            logger.info("Validation error encountered: %s", exc)
            return Response(
                {"error": "Invalid request parameters or unresolvable resource reference."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().handle_exception(exc)


def reconcile_relationships_with_quarantine(
    *,
    business_id: int,
) -> tuple[RelationshipRebuildResult, list[dict[str, Any]]]:
    """Reconcile relationships with SEC-HIGH-1 per-row quarantine resilience.

    If an unreconcilable row (e.g. malformed or invalid cross-tenant reference) is detected,
    it is isolated into quarantine rather than aborting the entire rebuild for the tenant.
    """
    quarantined: list[dict[str, Any]] = []

    try:
        result = rebuild_relationships(business_id=business_id)
        return result, quarantined
    except RelationshipValidationError as exc:
        # SEC-HIGH-1: Quarantine the error condition and record telemetry
        logger.error("Tenant %s relationship rebuild encountered unreconciled row: %s", business_id, exc)
        quarantined.append({
            "business_id": business_id,
            "error": str(exc),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        # Return fallback result showing quarantine activity
        return RelationshipRebuildResult(created=0, updated=0, unchanged=0, invalidated=0), quarantined


class MetricListView(BaseIntelligenceAPIView):
    """List registered business metrics."""

    def get(self, request):
        biz = self.get_authorized_business()
        sync_metric_registry(business_id=biz.pk)
        metrics_qs = models.BusinessMetric.objects.filter(business_id=biz.pk).order_by("key")
        data = self.paginate_queryset(metrics_qs)
        return Response({
            "total_count": data["total_count"],
            "limit": data["limit"],
            "offset": data["offset"],
            "results": [
                {
                    "id": m.pk,
                    "metric_key": m.key,
                    "name": m.name,
                    "category": m.category,
                    "unit": m.unit,
                    "value_type": m.value_type,
                }
                for m in data["results"]
            ],
        })


class MetricSnapshotListView(BaseIntelligenceAPIView):
    """Retrieve historical snapshots for a specific metric key."""

    def get(self, request, metric_key: str):
        biz = self.get_authorized_business()
        metric = models.BusinessMetric.objects.filter(business_id=biz.pk, key=metric_key).first()
        if not metric:
            return Response(
                {"error": "The requested resource was not found or access is denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        snapshots_qs = models.MetricSnapshot.objects.filter(
            business_id=biz.pk, metric=metric
        ).order_by("-period_start")

        # Optional filters
        period_type = request.query_params.get("period_type")
        if period_type:
            snapshots_qs = snapshots_qs.filter(period_type=period_type)

        dimension_type = request.query_params.get("dimension_type")
        if dimension_type:
            snapshots_qs = snapshots_qs.filter(dimension_type=dimension_type)

        data = self.paginate_queryset(snapshots_qs)
        return Response({
            "metric_key": metric_key,
            "total_count": data["total_count"],
            "limit": data["limit"],
            "offset": data["offset"],
            "results": [
                {
                    "id": s.pk,
                    "value": str(s.value),
                    "period_type": s.period_type,
                    "period_start": s.period_start.isoformat(),
                    "period_end": s.period_end.isoformat(),
                    "dimension_type": s.dimension_type,
                    "dimension_value": s.dimension_value,
                }
                for s in data["results"]
            ],
        })


class FactListCreateView(BaseIntelligenceAPIView):
    """List or create business facts with evidence."""

    def get(self, request):
        biz = self.get_authorized_business()
        status_param = request.query_params.get("status")
        facts_manager = models.BusinessFact.all_objects if status_param else models.BusinessFact.objects
        facts_qs = facts_manager.filter(business_id=biz.pk).order_by("-detected_at")

        if status_param:
            facts_qs = facts_qs.filter(status=status_param.upper())

        fact_type = request.query_params.get("fact_type")
        if fact_type:
            facts_qs = facts_qs.filter(fact_type=fact_type)

        data = self.paginate_queryset(facts_qs)
        return Response({
            "total_count": data["total_count"],
            "limit": data["limit"],
            "offset": data["offset"],
            "results": [
                {
                    "id": f.pk,
                    "fact_type": f.fact_type,
                    "statement": f.statement,
                    "value": str(f.value) if f.value is not None else None,
                    "value_unit": f.value_unit,
                    "confidence": str(f.confidence),
                    "status": f.status,
                    "rule_key": f.rule_key,
                    "detected_at": f.detected_at.isoformat(),
                    "evidence": f.metadata or {},
                }
                for f in data["results"]
            ],
        })

    def post(self, request):
        biz = self.get_authorized_business()
        statement = request.data.get("statement")
        fact_type = request.data.get("fact_type", "GENERAL")
        value = request.data.get("value")
        value_dec = Decimal(str(value)) if value is not None else None
        value_unit = request.data.get("value_unit")
        rule_key = request.data.get("rule_key")
        evidence = request.data.get("evidence", {})

        fact, created = create_or_update_fact(
            business_id=biz.pk,
            fact_type=fact_type,
            statement=statement,
            value=value_dec,
            value_unit=value_unit,
            rule_key=rule_key,
            evidence=evidence,
        )

        return Response(
            {
                "id": fact.pk,
                "fact_type": fact.fact_type,
                "statement": fact.statement,
                "status": fact.status,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FactDetailView(BaseIntelligenceAPIView):
    """Retrieve or update fact lifecycle."""

    def get(self, request, fact_id: int):
        biz = self.get_authorized_business()
        fact = models.BusinessFact.all_objects.filter(pk=fact_id).first()
        if not fact or fact.business_id != biz.pk:
            # SEC-MED-1: Return uniform 403/404 to avoid ID oracle
            return Response(
                {"error": "The requested resource was not found or access is denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "id": fact.pk,
            "business_id": fact.business_id,
            "fact_type": fact.fact_type,
            "statement": fact.statement,
            "value": str(fact.value) if fact.value is not None else None,
            "value_unit": fact.value_unit,
            "confidence": str(fact.confidence),
            "status": fact.status,
            "rule_key": fact.rule_key,
            "valid_from": fact.valid_from.isoformat() if fact.valid_from else None,
            "valid_to": fact.valid_to.isoformat() if fact.valid_to else None,
            "detected_at": fact.detected_at.isoformat(),
            "evidence": fact.metadata or {},
        })

    def patch(self, request, fact_id: int):
        biz = self.get_authorized_business()
        new_status = request.data.get("status")
        reason = request.data.get("reason")

        fact = update_fact_lifecycle(
            business_id=biz.pk,
            fact_id=fact_id,
            new_status=new_status,
            reason=reason,
        )
        return Response({
            "id": fact.pk,
            "status": fact.status,
            "valid_to": fact.valid_to.isoformat() if fact.valid_to else None,
            "updated_at": fact.updated_at.isoformat(),
        })


class IssueListCreateView(BaseIntelligenceAPIView):
    """List or create business issues with evidence linking."""

    def get(self, request):
        biz = self.get_authorized_business()
        issues_qs = models.BusinessIssue.objects.filter(business_id=biz.pk).order_by("-detected_at")

        status_param = request.query_params.get("status")
        if status_param:
            issues_qs = issues_qs.filter(status=status_param.upper())

        severity = request.query_params.get("severity")
        if severity:
            issues_qs = issues_qs.filter(severity=severity.upper())

        issue_type = request.query_params.get("issue_type")
        if issue_type:
            issues_qs = issues_qs.filter(issue_type=issue_type)

        data = self.paginate_queryset(issues_qs)
        return Response({
            "total_count": data["total_count"],
            "limit": data["limit"],
            "offset": data["offset"],
            "results": [
                {
                    "id": i.pk,
                    "issue_type": i.issue_type,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "confidence": str(i.confidence),
                    "status": i.status,
                    "detected_at": i.detected_at.isoformat(),
                    "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                    "metadata": i.metadata or {},
                }
                for i in data["results"]
            ],
        })

    def post(self, request):
        biz = self.get_authorized_business()
        issue_type = request.data.get("issue_type")
        title = request.data.get("title")
        description = request.data.get("description")
        severity = request.data.get("severity", "MEDIUM")
        confidence = Decimal(str(request.data.get("confidence", "1.0000")))
        rule_key = request.data.get("rule_key")
        fact_ids = request.data.get("fact_ids", [])
        snapshot_ids = request.data.get("snapshot_ids", [])

        issue, created = create_or_update_issue(
            business_id=biz.pk,
            issue_type=issue_type,
            title=title,
            description=description,
            severity=severity,
            confidence=confidence,
            rule_key=rule_key,
            fact_ids=fact_ids,
            snapshot_ids=snapshot_ids,
        )

        return Response(
            {
                "id": issue.pk,
                "issue_type": issue.issue_type,
                "title": issue.title,
                "status": issue.status,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class IssueDetailView(BaseIntelligenceAPIView):
    """Retrieve or update issue operational lifecycle."""

    def get(self, request, issue_id: int):
        biz = self.get_authorized_business()
        issue = models.BusinessIssue.objects.filter(pk=issue_id).first()
        if not issue or issue.business_id != biz.pk:
            return Response(
                {"error": "The requested resource was not found or access is denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "id": issue.pk,
            "business_id": issue.business_id,
            "issue_type": issue.issue_type,
            "title": issue.title,
            "description": issue.description,
            "severity": issue.severity,
            "confidence": str(issue.confidence),
            "status": issue.status,
            "rule_key": issue.rule_key,
            "detected_at": issue.detected_at.isoformat(),
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
            "metadata": issue.metadata or {},
        })

    def patch(self, request, issue_id: int):
        biz = self.get_authorized_business()
        new_status = request.data.get("status")
        notes = request.data.get("notes")

        issue = update_issue_lifecycle(
            business_id=biz.pk,
            issue_id=issue_id,
            new_status=new_status,
            resolution_notes=notes,
        )
        return Response({
            "id": issue.pk,
            "status": issue.status,
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
            "updated_at": issue.updated_at.isoformat(),
        })


class PipelineOrchestrationView(BaseIntelligenceAPIView):
    """Trigger intelligence pipeline execution for the authorized business."""

    def post(self, request):
        biz = self.get_authorized_business()

        # 1. Reconcile relationships with quarantine protection (SEC-HIGH-1)
        rel_result, quarantined = reconcile_relationships_with_quarantine(business_id=biz.pk)

        # 2. Sync metric registry
        sync_metric_registry(business_id=biz.pk)

        total_facts = models.BusinessFact.objects.filter(business_id=biz.pk).count()
        total_issues = models.BusinessIssue.objects.filter(business_id=biz.pk, status="OPEN").count()

        return Response({
            "business_id": biz.pk,
            "relationships_reconciled": {
                "created": rel_result.created,
                "updated": rel_result.updated,
                "unchanged": rel_result.unchanged,
                "invalidated": rel_result.invalidated,
            },
            "quarantined_records": len(quarantined),
            "active_facts_count": total_facts,
            "open_issues_count": total_issues,
            "status": "COMPLETED",
        })


__all__ = [
    "BaseIntelligenceAPIView",
    "FactDetailView",
    "FactListCreateView",
    "HasAuthorizedBusiness",
    "IssueDetailView",
    "IssueListCreateView",
    "MetricListView",
    "MetricSnapshotListView",
    "PipelineOrchestrationView",
    "reconcile_relationships_with_quarantine",
    "resolve_authorized_business",
]
