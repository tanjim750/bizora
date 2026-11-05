"""URL configuration for Business Graph endpoints."""

from django.urls import path

from app.business_graph import api

urlpatterns = [
    path("traversal/", api.GraphTraversalAPIView.as_view(), name="graph-traversal"),
    path("paths/", api.GraphPathSearchAPIView.as_view(), name="graph-paths"),
    path("query/", api.GraphQueryAPIView.as_view(), name="graph-query"),
    path("journeys/customer/<int:customer_id>/", api.CustomerJourneyAPIView.as_view(), name="graph-customer-journey"),
    path("journeys/order/<int:order_id>/", api.OrderJourneyAPIView.as_view(), name="graph-order-journey"),
    path("journeys/product/<int:product_id>/", api.ProductJourneyAPIView.as_view(), name="graph-product-journey"),
    path("journeys/campaign/<int:campaign_id>/", api.CampaignJourneyAPIView.as_view(), name="graph-campaign-journey"),
    path("snapshots/", api.GraphSnapshotListCreateAPIView.as_view(), name="graph-snapshots"),
    path("snapshots/<int:snapshot_id>/", api.GraphSnapshotDetailAPIView.as_view(), name="graph-snapshot-detail"),
    path("rebuild/", api.GraphRebuildAPIView.as_view(), name="graph-rebuild"),
]
