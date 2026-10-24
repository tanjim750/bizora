from django.core.exceptions import PermissionDenied, ValidationError
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
    AiRecommendationSerializer,
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
    SupportResumeAiRequestSerializer,
)
from app.services.actions import approve_action, execute_action, reject_action
from app.services.ai import (
    ask_business_assistant,
    diagnose_business_issue,
    evaluate_escalation,
    explain_campaign_performance,
    generate_handover_summary,
    generate_suggested_reply,
    resume_ai_handling,
    summarize_call,
    summarize_support_conversation,
)
from app.services.authorization import require_business_access


class BusinessScopedAPIView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        business_id = kwargs.get("business_id")
        if business_id is not None:
            business = get_object_or_404(Business, pk=business_id)
            require_business_access(request.user, business)
            self.business = business


class MessageView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        serializer = MessageSerializer({"message": "Bizora API is running."})
        return Response(serializer.data)


class AiActionApprovalView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        action = get_object_or_404(AiAction, pk=pk)

        try:
            require_business_access(request.user, action.business, roles={"OWNER", "ADMIN", "OPERATOR"})
        except PermissionDenied:
            return Response({"error": "Business access required."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AiActionApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            approved_action = approve_action(
                action=action,
                user=request.user,
                approval_note=serializer.validated_data["approval_note"],
            )
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            AiActionSerializer(approved_action).data, status=status.HTTP_200_OK
        )


class AiActionRejectView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        action = get_object_or_404(AiAction, pk=pk)
        try:
            require_business_access(request.user, action.business, roles={"OWNER", "ADMIN", "OPERATOR"})
            from app.serializers.action import AiActionApprovalSerializer
            serializer = AiActionApprovalSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            rejected = reject_action(action, request.user, serializer.validated_data["approval_note"])
        except PermissionDenied:
            return Response({"error": "Business access required."}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(AiActionSerializer(rejected).data, status=status.HTTP_200_OK)


class AiActionExecuteView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        action = get_object_or_404(AiAction, pk=pk)
        try:
            require_business_access(request.user, action.business, roles={"OWNER", "ADMIN", "OPERATOR"})
            executed = execute_action(action)
        except PermissionDenied:
            return Response({"error": "Business operator access required."}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(AiActionSerializer(executed).data, status=status.HTTP_200_OK)


class AiRecommendationListView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, business_id):
        from app.models import AiRecommendation
        rows = AiRecommendation.objects.filter(business_id=business_id)
        return Response(AiRecommendationSerializer(rows, many=True).data)


class AiActionListView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, business_id):
        rows = AiAction.objects.filter(business_id=business_id).order_by("-created_at")
        return Response(AiActionSerializer(rows, many=True).data)


class BusinessIssueListView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, business_id):
        issues = BusinessIssue.objects.filter(business_id=business_id, status="OPEN")
        serializer = BusinessIssueSerializer(issues, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BusinessAssistantChatView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business

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


class SupportReplyView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
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
                pk=serializer.validated_data["order_id"], business=business,
                customer_id=conversation.customer_id,
            ).first()

        result = generate_suggested_reply(
            business=business,
            conversation=conversation,
            order=order,
            intent=serializer.validated_data.get("intent", "refund_inquiry"),
        )
        return Response(result, status=status.HTTP_200_OK)


class SupportEscalationView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
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


class SupportHandoverView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
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


class SupportResumeAiView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
        serializer = SupportResumeAiRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        conversation = get_object_or_404(
            Conversation,
            pk=serializer.validated_data["conversation_id"],
            business=business,
        )
        result = resume_ai_handling(
            business=business,
            conversation=conversation,
            agent_notes=serializer.validated_data.get("agent_notes"),
        )
        return Response(result, status=status.HTTP_200_OK)



class MarketingAssistantView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
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


class BusinessDiagnosisView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
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


class ConversationSummaryView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
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


class CallSummaryView(BusinessScopedAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, business_id):
        business = self.business
        serializer = CallSummaryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        call = get_object_or_404(
            Call, pk=serializer.validated_data["call_id"], business=business
        )
        result = summarize_call(call=call)
        return Response(result, status=status.HTTP_200_OK)
