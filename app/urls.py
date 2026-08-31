from django.urls import path

from app.views import MessageView

urlpatterns = [
    path('', MessageView.as_view(), name='message'),
]
