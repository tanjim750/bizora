from rest_framework import serializers

from app.models import AiAction, AiRecommendation, AiRecommendationEvidence, BusinessIssue


class AiActionApprovalSerializer(serializers.Serializer):
    approval_note = serializers.CharField(required=True, min_length=3, max_length=1000)


class AiActionSerializer(serializers.ModelSerializer):
    approved_by_username = serializers.CharField(
        source="approved_by.username", read_only=True
    )

    class Meta:
        model = AiAction
        fields = (
            "id",
            "business",
            "ai_recommendation",
            "action_type",
            "status",
            "target_entity_type",
            "target_entity_id",
            "action_payload",
            "approval_note",
            "rejected_by",
            "rejected_at",
            "approved_by",
            "approved_by_username",
            "approved_at",
            "executed_at",
            "execution_result",
            "is_simulated",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "approved_by",
            "approved_at",
            "executed_at",
            "created_at",
            "updated_at",
        )


class AiRecommendationSerializer(serializers.ModelSerializer):
    evidence = serializers.SerializerMethodField()

    class Meta:
        model = AiRecommendation
        fields = ("id", "business", "business_issue", "recommendation_type", "title", "description", "rationale", "confidence", "priority", "status", "suggested_action_type", "generated_at", "evidence")
        read_only_fields = fields

    def get_evidence(self, obj):
        return list(AiRecommendationEvidence.objects.filter(ai_recommendation=obj).values(
            "id", "evidence_type", "description", "business_fact_id", "business_issue_id", "metric_snapshot_id", "knowledge_chunk_id"
        ))


class BusinessIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessIssue
        fields = (
            "id",
            "business",
            "issue_type",
            "subject_entity_type",
            "subject_entity_id",
            "title",
            "description",
            "severity",
            "confidence",
            "status",
            "rule_key",
            "detected_at",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
