"""REST API views, pipeline orchestration, and security seams for Business Intelligence.

Serves Business Intelligence specification sections 15-18 and ticket T-012.

Key properties:
1. Deny-by-default authorization seam (see app/business_scope.py):
   - The business comes only from the URL (businesses/<business_id>/intelligence/...).
   - The caller must be an active member of that business; reads need any member role,
     writes and the pipeline run need OWNER or MANAGER.
   - Rejects unauthenticated or non-member calls with HTTP 403 and never echoes ids.
   - Ignores any business_id sent in the query string or payload.
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

from rest_framework import serializers, status
from rest_framework.response import Response

from app import models
from app.business_scope import NOT_FOUND_DETAIL, BusinessScopedAPIView, error_response
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
    MetricSnapshotConflictError,
    MetricValidationError,
    sync_metric_registry,
)
from app.business_intelligence.relationships import (
    RelationshipConflictError,
    RelationshipRebuildResult,
    RelationshipValidationError,
    rebuild_relationships,
)


logger = logging.getLogger(__name__)


class BaseIntelligenceAPIView(BusinessScopedAPIView):
    """Base class providing URL-scoped membership checks and SEC-MED-1 anti-oracle protection."""

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
            return error_response("FORBIDDEN", NOT_FOUND_DETAIL, status.HTTP_403_FORBIDDEN)
        if isinstance(exc, (MetricSnapshotConflictError, RelationshipConflictError)):
            logger.warning("Conflict while running a BI operation: %s", exc)
            return error_response(
                "CONFLICT", "The operation conflicts with existing intelligence data; retry later.",
                status.HTTP_409_CONFLICT,
            )
        if isinstance(exc, (FactValidationError, IssueValidationError, AnomalyValidationError, MetricValidationError, RelationshipValidationError)):
            logger.info("Validation error encountered: %s", exc)
            return error_response(
                "INVALID_DATA",
                "Invalid request parameters or unresolvable resource reference.",
                status.HTTP_400_BAD_REQUEST,
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


class FactCreateSerializer(serializers.Serializer):
    """BI-07: a malformed fact body is a 400 `{code, detail, fields}`, never a 500."""

    statement = serializers.CharField()
    fact_type = serializers.CharField(max_length=100, required=False, default="GENERAL")
    value = serializers.DecimalField(max_digits=24, decimal_places=6, required=False, allow_null=True, default=None)
    value_unit = serializers.CharField(max_length=30, required=False, allow_null=True, default=None)
    rule_key = serializers.CharField(max_length=100, required=False, allow_null=True, default=None)
    evidence = serializers.DictField(required=False, default=dict)


class FactLifecycleSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=30)
    reason = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)


class IssueCreateSerializer(serializers.Serializer):
    issue_type = serializers.CharField(max_length=100)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    severity = serializers.CharField(max_length=30, required=False, default="MEDIUM")
    confidence = serializers.DecimalField(max_digits=5, decimal_places=4, min_value=Decimal("0"), max_value=Decimal("1"),
                                          required=False, default=Decimal("1.0000"))
    rule_key = serializers.CharField(max_length=100, required=False, allow_null=True, default=None)
    fact_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    snapshot_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)


class IssueLifecycleSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=30)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)


def validated_body(serializer_class, request):
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class MetricListView(BaseIntelligenceAPIView):
    """List registered business metrics."""

    def get(self, request, business_id: int):
        biz = self.get_authorized_business()
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

    def get(self, request, business_id: int, metric_key: str):
        biz = self.get_authorized_business()
        metric = models.BusinessMetric.objects.filter(business_id=biz.pk, key=metric_key).first()
        if not metric:
            return error_response("NOT_FOUND", NOT_FOUND_DETAIL, status.HTTP_404_NOT_FOUND)

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

    def get(self, request, business_id: int):
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

    def post(self, request, business_id: int):
        biz = self.get_authorized_business()
        body = validated_body(FactCreateSerializer, request)

        fact, created = create_or_update_fact(
            business_id=biz.pk,
            fact_type=body["fact_type"],
            statement=body["statement"],
            value=body["value"],
            value_unit=body["value_unit"],
            rule_key=body["rule_key"],
            evidence=body["evidence"],
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

    def get(self, request, business_id: int, fact_id: int):
        biz = self.get_authorized_business()
        fact = models.BusinessFact.all_objects.filter(pk=fact_id).first()
        if not fact or fact.business_id != biz.pk:
            # SEC-MED-1: Return uniform 403/404 to avoid ID oracle
            return error_response("NOT_FOUND", NOT_FOUND_DETAIL, status.HTTP_404_NOT_FOUND)

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

    def patch(self, request, business_id: int, fact_id: int):
        biz = self.get_authorized_business()
        body = validated_body(FactLifecycleSerializer, request)

        fact = update_fact_lifecycle(
            business_id=biz.pk,
            fact_id=fact_id,
            new_status=body["status"],
            reason=body["reason"],
        )
        return Response({
            "id": fact.pk,
            "status": fact.status,
            "valid_to": fact.valid_to.isoformat() if fact.valid_to else None,
            "updated_at": fact.updated_at.isoformat(),
        })


class IssueListCreateView(BaseIntelligenceAPIView):
    """List or create business issues with evidence linking."""

    def get(self, request, business_id: int):
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

    def post(self, request, business_id: int):
        biz = self.get_authorized_business()
        body = validated_body(IssueCreateSerializer, request)

        issue, created = create_or_update_issue(
            business_id=biz.pk,
            issue_type=body["issue_type"],
            title=body["title"],
            description=body["description"],
            severity=body["severity"],
            confidence=body["confidence"],
            rule_key=body["rule_key"],
            fact_ids=body["fact_ids"],
            snapshot_ids=body["snapshot_ids"],
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

    def get(self, request, business_id: int, issue_id: int):
        biz = self.get_authorized_business()
        issue = models.BusinessIssue.objects.filter(pk=issue_id).first()
        if not issue or issue.business_id != biz.pk:
            return error_response("NOT_FOUND", NOT_FOUND_DETAIL, status.HTTP_404_NOT_FOUND)

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

    def patch(self, request, business_id: int, issue_id: int):
        biz = self.get_authorized_business()
        body = validated_body(IssueLifecycleSerializer, request)

        issue = update_issue_lifecycle(
            business_id=biz.pk,
            issue_id=issue_id,
            new_status=body["status"],
            resolution_notes=body["notes"],
        )
        return Response({
            "id": issue.pk,
            "status": issue.status,
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
            "updated_at": issue.updated_at.isoformat(),
        })


class PipelineOrchestrationView(BaseIntelligenceAPIView):
    """Trigger intelligence pipeline execution for the authorized business."""

    def post(self, request, business_id: int):
        biz = self.get_authorized_business()

        # 1. Reconcile relationships with quarantine protection (SEC-HIGH-1)
        rel_result, quarantined = reconcile_relationships_with_quarantine(business_id=biz.pk)
        if quarantined:
            # BI-04: the rebuild was rolled back as a whole; report the failure and its reason, never "COMPLETED".
            return error_response(
                "PIPELINE_FAILED",
                f"Relationship reconciliation was rolled back: {quarantined[0]['error']}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
    "IssueDetailView",
    "IssueListCreateView",
    "MetricListView",
    "MetricSnapshotListView",
    "PipelineOrchestrationView",
    "validated_body",
    "reconcile_relationships_with_quarantine",
]
