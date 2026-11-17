"""Knowledge Base API URL routes."""
from django.urls import path
from .api import KnowledgeDocumentsView, KnowledgeSourcesView

urlpatterns = [
    path("sources/", KnowledgeSourcesView.as_view(), name="knowledge-sources"),
    path("documents/", KnowledgeDocumentsView.as_view(), name="knowledge-documents"),
]
