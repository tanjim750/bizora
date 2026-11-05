from django.urls import path
from django.contrib.auth import views as auth
from django.views.decorators.http import require_POST
from app import operations_ui as ui
urlpatterns = [path('', ui.index, name='ops-index'), path('login/', auth.LoginView.as_view(template_name='operations/login.html', next_page='/ops/'), name='ops-login'), path('logout/', require_POST(auth.LogoutView.as_view(next_page='/ops/login/')), name='ops-logout'), path('business/<int:business_id>/financial-timeline/', ui.financial_timeline, name='ops-financial-timeline'), path('business/<int:business_id>/resources/<slug:name>/', ui.resources, name='ops-resources'), path('business/<int:business_id>/records/<slug:name>/<int:pk>/', ui.detail, name='ops-detail'), path('business/<int:business_id>/records/<slug:name>/<int:pk>/<slug:command>/', ui.command, name='ops-command'), path('business/<int:business_id>/<slug:section>/', ui.section, name='ops-section')]
