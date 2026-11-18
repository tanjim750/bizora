"""Knowledge Base API URL routes."""
from django.urls import path
from .api import KnowledgeDocumentsView, KnowledgeSourcesView
from .search import KnowledgeSearchView

urlpatterns = [
    path("sources/", KnowledgeSourcesView.as_view(), name="knowledge-sources"),
    path("documents/", KnowledgeDocumentsView.as_view(), name="knowledge-documents"),
    path("search/", KnowledgeSearchView.as_view(), name="knowledge-search"),
]

