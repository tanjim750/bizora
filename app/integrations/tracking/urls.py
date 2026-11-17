from django.urls import path
from .api import TrackingSummaryView

urlpatterns = [
    path("summary/", TrackingSummaryView.as_view(), name="tracking-summary"),
]
