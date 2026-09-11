"""
DRF Serializers for AI Intelligence Features.
Handles validation for:
- Business Assistant queries
- Customer Support replies & escalations
- Marketing Assistant campaign explanations
- Business Diagnosis
- Conversation & Call summarization
"""

from rest_framework import serializers


class BusinessAssistantQuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=2000, required=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    intent = serializers.CharField(max_length=100, required=False, default="business_performance_inquiry")


class SupportReplyRequestSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=True)
    order_id = serializers.IntegerField(required=False, allow_null=True)
    intent = serializers.CharField(max_length=100, required=False, default="refund_inquiry")


class SupportEscalationRequestSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=True)
    customer_message = serializers.CharField(max_length=2000, required=True)


class SupportHandoverRequestSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=True)


class CampaignExplanationRequestSerializer(serializers.Serializer):
    campaign_id = serializers.IntegerField(required=True)


class BusinessDiagnosisRequestSerializer(serializers.Serializer):
    issue_id = serializers.IntegerField(required=True)


class ConversationSummaryRequestSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=True)


class CallSummaryRequestSerializer(serializers.Serializer):
    call_id = serializers.IntegerField(required=True)
