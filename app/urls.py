from django.urls import include, path

from app.views import MessageView

urlpatterns = [
    path('', MessageView.as_view(), name='message'),
    path('businesses/<int:business_id>/observability/', include('app.observability.urls')),
    path('businesses/<int:business_id>/overview/', include('app.overview.urls')),
]
