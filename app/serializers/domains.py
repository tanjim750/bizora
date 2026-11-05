from rest_framework import serializers


class EventInputSerializer(serializers.Serializer):
    data = serializers.DictField()
    connection_id = serializers.IntegerField(min_value=1, required=False)
    occurred_at = serializers.DateTimeField(required=False)


class TransitionSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=50)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    expected_status = serializers.CharField(required=False, max_length=50)


class AssignmentSerializer(serializers.Serializer):
    assignee_type = serializers.ChoiceField(choices=['AGENT', 'TEAM', 'AI', 'UNASSIGNED'])
    assignee_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class HandoverSerializer(serializers.Serializer):
    target = serializers.ChoiceField(choices=['HUMAN', 'AI'])
    assignee_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    reason = serializers.CharField(max_length=2000)
    summary = serializers.CharField(required=False, allow_blank=True, max_length=10000)


class IdentityCommandSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['ACTIVE', 'INACTIVE', 'SUPERSEDED'], required=False)
    metadata = serializers.DictField(required=False)
    observed_at = serializers.DateTimeField(required=False)
    verification = serializers.BooleanField(required=False)
    external_identity_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    identification_event_id = serializers.IntegerField(min_value=1, required=False)
    connection_id = serializers.IntegerField(min_value=1, required=False)
    entity_type = serializers.CharField(max_length=50, required=False)
    identity_type = serializers.CharField(max_length=50, required=False)
    value = serializers.CharField(max_length=500, required=False)
    external_id = serializers.CharField(max_length=255, required=False)
    verified = serializers.BooleanField(default=False)
    entity_id = serializers.IntegerField(min_value=1, required=False)
    external_identity_id = serializers.IntegerField(min_value=1, required=False)
    canonical_identity_id = serializers.IntegerField(min_value=1, required=False)
    link_id = serializers.IntegerField(min_value=1, required=False)
    contact_id = serializers.IntegerField(min_value=1, required=False)
    visitor_id = serializers.IntegerField(min_value=1, required=False)
    purchase_event_id = serializers.IntegerField(min_value=1, required=False)
    candidate_id = serializers.IntegerField(min_value=1, required=False)
    conflict_id = serializers.IntegerField(min_value=1, required=False)
    decision = serializers.CharField(max_length=30, required=False)
    reason = serializers.CharField(max_length=2000, required=False)


class VariantUpdateSerializer(serializers.Serializer):
    data = serializers.DictField()
    expected_updated_at = serializers.DateTimeField(required=False)


class PrioritySerializer(serializers.Serializer):
    priority = serializers.ChoiceField(choices=['LOW', 'NORMAL', 'HIGH', 'URGENT'])
    reason = serializers.CharField(max_length=2000)
