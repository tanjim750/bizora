from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import (
    AiAction,
    Business,
    BusinessIssue,
    Call,
    Campaign,
    Conversation,
    Order,
)
from app.serializers import (
    AiActionApprovalSerializer,
    AiActionSerializer,
    BusinessIssueSerializer,
    MessageSerializer,
)
from app.serializers.ai import (
    BusinessAssistantQuerySerializer,
    BusinessDiagnosisRequestSerializer,
    CallSummaryRequestSerializer,
    CampaignExplanationRequestSerializer,
    ConversationSummaryRequestSerializer,
    SupportEscalationRequestSerializer,
    SupportHandoverRequestSerializer,
    SupportReplyRequestSerializer,
)
from app.services.actions import approve_action
from app.services.ai import (
    ask_business_assistant,
    diagnose_business_issue,
    evaluate_escalation,
    explain_campaign_performance,
    generate_handover_summary,
    generate_suggested_reply,
    summarize_call,
    summarize_support_conversation,
)


class MessageView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        serializer = MessageSerializer({"message": "Bizora API is running."})
        return Response(serializer.data)


class AiActionApprovalView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        action = get_object_or_404(AiAction, pk=pk)

        # Tenant isolation check if user has business context
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and action.business_id != user_business_id:
            return Response(
                {
                    "error": "You do not have permission to approve actions for another business."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AiActionApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        approved_action = approve_action(
            action=action,
            user=request.user,
            approval_note=serializer.validated_data["approval_note"],
        )
        return Response(
            AiActionSerializer(approved_action).data, status=status.HTTP_200_OK
        )


class BusinessIssueListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, business_id):
        get_object_or_404(Business, pk=business_id)

        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )

        issues = BusinessIssue.objects.filter(business_id=business_id, status="OPEN")
        serializer = BusinessIssueSerializer(issues, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BusinessAssistantChatView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BusinessAssistantQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = ask_business_assistant(
            business=business,
            user_query=serializer.validated_data["query"],
            conversation_id=serializer.validated_data.get("conversation_id"),
            intent=serializer.validated_data.get(
                "intent", "business_performance_inquiry"
            ),
        )
        return Response(result, status=status.HTTP_200_OK)


class SupportReplyView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SupportReplyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        conversation = get_object_or_404(
            Conversation,
            pk=serializer.validated_data["conversation_id"],
            business=business,
        )
        order = None
        if serializer.validated_data.get("order_id"):
            order = Order.objects.filter(
                pk=serializer.validated_data["order_id"], business=business
            ).first()

        result = generate_suggested_reply(
            business=business,
            conversation=conversation,
            order=order,
            intent=serializer.validated_data.get("intent", "refund_inquiry"),
        )
        return Response(result, status=status.HTTP_200_OK)


class SupportEscalationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SupportEscalationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        conversation = get_object_or_404(
            Conversation,
            pk=serializer.validated_data["conversation_id"],
            business=business,
        )
        result = evaluate_escalation(
            business=business,
            conversation=conversation,
            customer_message=serializer.validated_data["customer_message"],
        )
        return Response(result, status=status.HTTP_200_OK)


class SupportHandoverView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SupportHandoverRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        conversation = get_object_or_404(
            Conversation,
            pk=serializer.validated_data["conversation_id"],
            business=business,
        )
        result = generate_handover_summary(
            business=business,
            conversation=conversation,
        )
        return Response(result, status=status.HTTP_200_OK)


class MarketingAssistantView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CampaignExplanationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        campaign = get_object_or_404(
            Campaign,
            pk=serializer.validated_data["campaign_id"],
            business=business,
        )
        result = explain_campaign_performance(
            business=business, campaign=campaign
        )
        return Response(result, status=status.HTTP_200_OK)


class BusinessDiagnosisView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BusinessDiagnosisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        issue = get_object_or_404(
            BusinessIssue,
            pk=serializer.validated_data["issue_id"],
            business=business,
        )
        result = diagnose_business_issue(business=business, issue=issue)
        return Response(result, status=status.HTTP_200_OK)


class ConversationSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ConversationSummaryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        conversation = get_object_or_404(
            Conversation,
            pk=serializer.validated_data["conversation_id"],
            business=business,
        )
        result = summarize_support_conversation(conversation=conversation)
        return Response(result, status=status.HTTP_200_OK)


class CallSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user_business_id = getattr(request.user, "business_id", None)
        if user_business_id is not None and business_id != user_business_id:
            return Response(
                {"error": "Cross-tenant access forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CallSummaryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        call = get_object_or_404(
            Call, pk=serializer.validated_data["call_id"], business=business
        )
        result = summarize_call(call=call)
        return Response(result, status=status.HTTP_200_OK)

