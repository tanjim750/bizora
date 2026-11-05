"""URL configuration for Business Intelligence REST API endpoints."""

from django.urls import path

from app.business_intelligence import api

urlpatterns = [
    path("metrics/", api.MetricListView.as_view(), name="intelligence-metrics"),
    path("metrics/<str:metric_key>/snapshots/", api.MetricSnapshotListView.as_view(), name="intelligence-metric-snapshots"),
    path("facts/", api.FactListCreateView.as_view(), name="intelligence-facts"),
    path("facts/<int:fact_id>/", api.FactDetailView.as_view(), name="intelligence-fact-detail"),
    path("issues/", api.IssueListCreateView.as_view(), name="intelligence-issues"),
    path("issues/<int:issue_id>/", api.IssueDetailView.as_view(), name="intelligence-issue-detail"),
    path("pipeline/run/", api.PipelineOrchestrationView.as_view(), name="intelligence-pipeline-run"),
]
