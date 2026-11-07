from django.urls import path

from .views import CollectionView, ConfigurationView, DetailView, EntityView


urlpatterns = [path('configuration/', ConfigurationView.as_view(), {'resource': 'configuration'}, name='overview-configuration'),
               path('entities/<str:entity_type>/<int:pk>/', EntityView.as_view(), name='overview-entity')]
for resource in ('summary', 'kpis', 'trends', 'issues', 'health', 'activity', 'recommendations', 'cross-domain', 'catalog'):
    urlpatterns.append(path(f'{resource}/', CollectionView.as_view(), {'resource': resource}, name=f'overview-{resource}'))
for resource in ('issues', 'recommendations'):
    urlpatterns.append(path(f'{resource}/<int:pk>/', DetailView.as_view(), {'resource': resource}))
for resource in ('facts', 'snapshots', 'relationships', 'nodes', 'edges', 'knowledge'):
    urlpatterns.append(path(f'evidence/{resource}/<int:pk>/', DetailView.as_view(), {'resource': resource}))
