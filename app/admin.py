
from app.models import (BusinessAccess, ConnectionCheck, FailedRecord, IntegrationError,
                        MonitoringPolicy, ObservationReceipt, ObservabilityAudit,
                        OperationAttempt, ProviderRequest, SourceFreshness,
                        WebhookDelivery, WebhookObservation)


class SuperuserAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


class EvidenceAdmin(SuperuserAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]


@admin.register(BusinessAccess)
class BusinessAccessAdmin(SuperuserAdmin):
    list_display = ['business', 'user', 'role']
    list_filter = ['role']


@admin.register(MonitoringPolicy)
class MonitoringPolicyAdmin(SuperuserAdmin):
    list_display = ['business', 'connection', 'entity_type', 'delayed_seconds', 'stale_seconds', 'enabled']
    list_filter = ['enabled', 'entity_type']


for model in (ConnectionCheck, FailedRecord, IntegrationError, ObservationReceipt, ObservabilityAudit,
              OperationAttempt, ProviderRequest, SourceFreshness, WebhookDelivery, WebhookObservation):
    admin.site.register(model, EvidenceAdmin)
