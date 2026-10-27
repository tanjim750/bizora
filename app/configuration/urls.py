from django.urls import path

from app.observability.views import OperationView, PolicyView
from app.overview.views import ConfigurationView
from .views import (ChangesView, ConnectionsView, EffectiveView, HistoryView, MonitoringHistoryView, ProvidersView,
                    ReprocessingView, ResourceView, SectionView, SourcesView)


urlpatterns = [path('changes/', ChangesView.as_view()), path('effective/', EffectiveView.as_view()),
               path('monitoring/', ConfigurationView.as_view(), {'resource': 'configuration'}),
               path('monitoring/history/', MonitoringHistoryView.as_view()),
               path('freshness/<int:pk>/history/', HistoryView.as_view(), {'section': 'freshness'}),
               path('freshness/', PolicyView.as_view()), path('providers/', ProvidersView.as_view()),
               path('connections/', ConnectionsView.as_view()), path('connections/<int:pk>/', ConnectionsView.as_view()),
               path('connections/<int:pk>/history/', HistoryView.as_view(), {'section': 'connections'}),
               path('connections/<int:pk>/test/', OperationView.as_view(), {'resource': 'connections', 'action': 'connection_test'}),
               path('sources/', SourcesView.as_view()), path('sources/<int:pk>/', SourcesView.as_view()),
               path('sources/<int:pk>/history/', HistoryView.as_view(), {'section': 'sources'}),
               path('reprocessing/', ReprocessingView.as_view())]
for section in ('profile', 'general', 'ai', 'knowledge'):
    urlpatterns += [path(f'{section}/', SectionView.as_view(), {'section': section}),
                    path(f'{section}/history/', HistoryView.as_view(), {'section': section})]
for section in ('rules', 'policies'):
    urlpatterns += [path(f'{section}/', ResourceView.as_view(), {'section': section}),
                    path(f'{section}/<slug:key>/', ResourceView.as_view(), {'section': section}),
                    path(f'{section}/<slug:key>/history/', HistoryView.as_view(), {'section': section})]
