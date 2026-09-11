from rest_framework import serializers

from app.models import AiAction, BusinessIssue


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
