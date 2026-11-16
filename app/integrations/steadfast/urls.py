from django.urls import path

from . import views

urlpatterns = [
    path('shipments/', views.create_shipment, name='steadfast-create-shipment'),
    path('shipments/<int:shipment_id>/refresh/', views.refresh_shipment, name='steadfast-refresh-shipment'),
    path('webhook/', views.webhook, name='steadfast-webhook'),
]
