from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import AiAction, Business, BusinessIssue
from app.serializers import (
    AiActionApprovalSerializer,
    AiActionSerializer,
    BusinessIssueSerializer,
    MessageSerializer,
)
from app.services.actions import approve_action


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
