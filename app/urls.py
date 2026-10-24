from django.urls import path

from app.views import MessageView

urlpatterns = [
    path('', MessageView.as_view(), name='message'),
]

from app import domain_views as domain

urlpatterns += [
    path('businesses/<int:business_id>/variants/<int:pk>/update/', domain.VariantUpdateView.as_view()),
    path('businesses/<int:business_id>/financial-timeline/', domain.FinancialTimelineView.as_view()),
    path('businesses/<int:business_id>/website-performance/', domain.WebsitePerformanceView.as_view()),
    path('businesses/<int:business_id>/overview/', domain.OverviewView.as_view()),
    path('businesses/<int:business_id>/customers/<int:pk>/360/', domain.Customer360View.as_view()),
    path('businesses/<int:business_id>/support-queue/', domain.SupportQueueView.as_view()),
    path('businesses/<int:business_id>/conversations/<int:pk>/assign/', domain.AssignmentView.as_view()),
    path('businesses/<int:business_id>/conversations/<int:pk>/handover/', domain.HandoverView.as_view()),
    path('businesses/<int:business_id>/identity/<slug:command>/', domain.IdentityView.as_view()),
    path('businesses/<int:business_id>/actions/<int:pk>/review/', domain.ActionReviewView.as_view()),
    path('businesses/<int:business_id>/<slug:name>/<int:pk>/transition/', domain.TransitionView.as_view()),
    path('businesses/<int:business_id>/<slug:name>/<int:pk>/', domain.ResourceDetail.as_view()),
    path('businesses/<int:business_id>/<slug:name>/', domain.ResourceList.as_view()),
]

urlpatterns.append(path('businesses/<int:business_id>/messages/<int:pk>/read/', domain.MessageReadView.as_view()))

urlpatterns += [
    path('businesses/<int:business_id>/conversations/<int:pk>/priority/', domain.PriorityView.as_view()),
    path('businesses/<int:business_id>/conversations/<int:pk>/context/', domain.SupportContextView.as_view()),
    path('businesses/<int:business_id>/visitors/<int:pk>/journey/', domain.JourneyView.as_view()),
    path('businesses/<int:business_id>/customers/<int:pk>/retargeting-context/', domain.RetargetingContextView.as_view()),
    path('businesses/<int:business_id>/operations/<slug:operation>/<int:pk>/prepare/', domain.OutboundPreparationView.as_view()),
]

urlpatterns.append(path('businesses/<int:business_id>/graph-context/<slug:kind>/<int:pk>/', domain.GraphContextView.as_view()))

urlpatterns.append(path('businesses/<int:business_id>/callbacks/<int:pk>/schedule/', domain.CallbackScheduleView.as_view()))

urlpatterns += [
    path('businesses/<int:business_id>/identity/merge-candidates/<int:pk>/dry-run/',domain.MergeDryRunView.as_view()),
    path('businesses/<int:business_id>/products/assess/',domain.ProductAssessmentView.as_view()),
]

urlpatterns.append(path('businesses/<int:business_id>/contracts/<slug:owner>/<slug:capability>/',domain.DomainContractView.as_view()))
