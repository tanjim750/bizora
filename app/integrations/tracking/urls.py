from django.urls import path
from .api import TrackingAttemptListView, TrackingSettingsView, TrackingSummaryView

urlpatterns = [
    path("summary/", TrackingSummaryView.as_view(), name="tracking-summary"),
    path("attempts/", TrackingAttemptListView.as_view(), name="tracking-attempts"),
    path(
        "connections/<int:connection_id>/settings/",
        TrackingSettingsView.as_view(),
        name="tracking-settings",
    ),
]


