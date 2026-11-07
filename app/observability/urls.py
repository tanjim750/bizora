from django.urls import path

from .views import (CollectionView, DetailView, GroupsView, OperationView, PayloadDiagnosticView,
                    PolicyView, StatisticsView, SummaryView)


urlpatterns = [path('summary/', SummaryView.as_view(), name='observability-summary'),
               path('policies/', PolicyView.as_view(), name='observability-policies'),
               path('payloads/<int:pk>/', PayloadDiagnosticView.as_view(), name='observability-payload-diagnostic'),
               path('failed-records/groups/', GroupsView.as_view(), name='observability-failure-groups'),
               path('syncs/statistics/', StatisticsView.as_view(), name='observability-sync-statistics')]
for resource in ('connections', 'syncs', 'failed-records', 'webhooks', 'freshness', 'providers', 'errors'):
    urlpatterns.append(path(f'{resource}/', CollectionView.as_view(), {'resource': resource}, name=f'observability-{resource}'))
    if resource != 'freshness':
        urlpatterns.append(path(f'{resource}/<int:pk>/', DetailView.as_view(), {'resource': resource}))
for resource, route, action in [('connections', 'test', 'connection_test'), ('syncs', 'retry', 'sync_retry'),
                                 ('failed-records', 'retry', 'record_retry'), ('webhooks', 'replay', 'webhook_replay')]:
    urlpatterns.append(path(f'{resource}/<int:pk>/{route}/', OperationView.as_view(),
                            {'resource': resource, 'action': action}))
