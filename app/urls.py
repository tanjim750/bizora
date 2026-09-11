from django.urls import path

from app.views import AiActionApprovalView, BusinessIssueListView, MessageView

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
]
