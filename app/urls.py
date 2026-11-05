from django.urls import include, path

from app.views import (
    AiActionApprovalView,
    AiActionExecuteView,
    AiActionListView,
    AiActionRejectView,
    AiRecommendationListView,
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
    SupportResumeAiView,
)

urlpatterns = [
    path("", MessageView.as_view(), name="message"),
    path(
        "actions/<int:pk>/approve/",
        AiActionApprovalView.as_view(),
        name="action-approve",
    ),
    path("actions/<int:pk>/reject/", AiActionRejectView.as_view(), name="action-reject"),
    path("actions/<int:pk>/execute/", AiActionExecuteView.as_view(), name="action-execute"),
    path("businesses/<int:business_id>/ai/recommendations/", AiRecommendationListView.as_view(), name="ai-recommendations"),
    path("businesses/<int:business_id>/ai/actions/", AiActionListView.as_view(), name="ai-actions"),
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
        "businesses/<int:business_id>/ai/support/resume/",
        SupportResumeAiView.as_view(),
        name="ai-support-resume",
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

from app import domain_views as domain

urlpatterns += [
    path('businesses/<int:business_id>/variants/<int:pk>/update/', domain.VariantUpdateView.as_view()),
    path('businesses/<int:business_id>/financial-timeline/', domain.FinancialTimelineView.as_view()),
    path('businesses/<int:business_id>/website-performance/', domain.WebsitePerformanceView.as_view()),
    path('businesses/<int:business_id>/overview/', domain.OverviewView.as_view()),
    path('businesses/<int:business_id>/customers/<int:pk>/360/', domain.Customer360View.as_view()),
    path('businesses/<int:business_id>/support-queue/', domain.SupportQueueView.as_view()),
    path('businesses/<int:business_id>/conversations/<int:pk>/assign/', domain.AssignmentView.as_view()),
    path('businesses/<int:business_id>/conversations/<int:pk>/handover/', domain.HandoverView.as_view()),
    path('businesses/<int:business_id>/identity/<slug:command>/', domain.IdentityView.as_view()),
    path('businesses/<int:business_id>/actions/<int:pk>/review/', domain.ActionReviewView.as_view()),
    path('businesses/<int:business_id>/<slug:name>/<int:pk>/transition/', domain.TransitionView.as_view()),
    path('businesses/<int:business_id>/<slug:name>/<int:pk>/', domain.ResourceDetail.as_view()),
    path('businesses/<int:business_id>/<slug:name>/', domain.ResourceList.as_view()),
]

urlpatterns.append(path('businesses/<int:business_id>/messages/<int:pk>/read/', domain.MessageReadView.as_view()))

urlpatterns += [
    path('businesses/<int:business_id>/conversations/<int:pk>/priority/', domain.PriorityView.as_view()),
    path('businesses/<int:business_id>/conversations/<int:pk>/context/', domain.SupportContextView.as_view()),
    path('businesses/<int:business_id>/visitors/<int:pk>/journey/', domain.JourneyView.as_view()),
    path('businesses/<int:business_id>/customers/<int:pk>/retargeting-context/', domain.RetargetingContextView.as_view()),
    path('businesses/<int:business_id>/operations/<slug:operation>/<int:pk>/prepare/', domain.OutboundPreparationView.as_view()),
]

urlpatterns.append(path('businesses/<int:business_id>/graph-context/<slug:kind>/<int:pk>/', domain.GraphContextView.as_view()))

urlpatterns.append(path('businesses/<int:business_id>/callbacks/<int:pk>/schedule/', domain.CallbackScheduleView.as_view()))

urlpatterns += [
    path('businesses/<int:business_id>/identity/merge-candidates/<int:pk>/dry-run/',domain.MergeDryRunView.as_view()),
    path('businesses/<int:business_id>/products/assess/',domain.ProductAssessmentView.as_view()),
]

urlpatterns.append(path('businesses/<int:business_id>/contracts/<slug:owner>/<slug:capability>/',domain.DomainContractView.as_view()))
