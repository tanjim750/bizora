from django.urls import path

from app.views import (
    AiActionApprovalView,
    BusinessAssistantChatView,
    BusinessDiagnosisView,
    BusinessIssueListView,
    CallSummaryView,
    ConversationSummaryView,
    MarketingAssistantView,
    MessageView,
    SupportEscalationView,
    SupportHandoverView,
    SupportReplyView,
)

urlpatterns = [
    path("", MessageView.as_view(), name="message"),
    path(
        "actions/<int:pk>/approve/",
        AiActionApprovalView.as_view(),
        name="action-approve",
    ),
    path(
        "businesses/<int:business_id>/issues/",
        BusinessIssueListView.as_view(),
        name="business-issues",
    ),
    path(
        "businesses/<int:business_id>/ai/assistant/query/",
        BusinessAssistantChatView.as_view(),
        name="ai-assistant-query",
    ),
    path(
        "businesses/<int:business_id>/ai/support/suggest-reply/",
        SupportReplyView.as_view(),
        name="ai-support-reply",
    ),
    path(
        "businesses/<int:business_id>/ai/support/escalate/",
        SupportEscalationView.as_view(),
        name="ai-support-escalate",
    ),
    path(
        "businesses/<int:business_id>/ai/support/handover/",
        SupportHandoverView.as_view(),
        name="ai-support-handover",
    ),
    path(
        "businesses/<int:business_id>/ai/marketing/explain-campaign/",
        MarketingAssistantView.as_view(),
        name="ai-marketing-explain",
    ),
    path(
        "businesses/<int:business_id>/ai/diagnosis/diagnose-issue/",
        BusinessDiagnosisView.as_view(),
        name="ai-business-diagnosis",
    ),
    path(
        "businesses/<int:business_id>/ai/summarization/conversation/",
        ConversationSummaryView.as_view(),
        name="ai-summarize-conversation",
    ),
    path(
        "businesses/<int:business_id>/ai/summarization/call/",
        CallSummaryView.as_view(),
        name="ai-summarize-call",
    ),
]

