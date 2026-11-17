from django.urls import path
from .api import TrackingAttemptListView, TrackingSummaryView

urlpatterns = [
    path("summary/", TrackingSummaryView.as_view(), name="tracking-summary"),
    path("attempts/", TrackingAttemptListView.as_view(), name="tracking-attempts"),
]

