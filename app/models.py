from django.db import models


class VectorField(models.Field):
    description = "PostgreSQL pgvector field"

    def db_type(self, connection):
        return 'vector'


class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=100)
    minor_unit = models.IntegerField(default=2)

    class Meta:
        db_table = 'currencies'


class Business(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)
    legal_name = models.CharField(max_length=255, null=True)
    currency_code = models.ForeignKey('Currency', models.DO_NOTHING, db_column='currency_code')
    timezone = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2, null=True)
    status = models.CharField(max_length=30, db_index=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'businesses'


class SourceSystem(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    provider = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50)
    external_account_id = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=30)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'source_systems'
        constraints = [
            models.UniqueConstraint(fields=['business', 'provider', 'external_account_id'], name='source_systems_business_id_provider_external_account_id_uniq'),
        ]


class IntegrationProvider(models.Model):
    id = models.UUIDField(primary_key=True)
    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    provider_type = models.CharField(max_length=50)
    capabilities = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'integration_providers'


class Integration(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    provider = models.ForeignKey('IntegrationProvider', models.DO_NOTHING, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True)
    status = models.CharField(max_length=30)
    display_name = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'integrations'
        constraints = [
            models.UniqueConstraint(fields=['business', 'provider'], name='integrations_business_id_provider_id_uniq'),
        ]


class IntegrationCredential(models.Model):
    id = models.UUIDField(primary_key=True)
    integration = models.ForeignKey('Integration', models.DO_NOTHING)
    credential_type = models.CharField(max_length=50)
    secret_reference = models.CharField(max_length=500)
    expires_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'integration_credentials'


class IntegrationPermission(models.Model):
    id = models.UUIDField(primary_key=True)
    integration = models.ForeignKey('Integration', models.DO_NOTHING, db_index=True)
    permission = models.CharField(max_length=255)
    granted = models.BooleanField(default=False)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'integration_permissions'
        constraints = [
            models.UniqueConstraint(fields=['integration', 'permission'], name='integration_permissions_integration_id_permission_uniq'),
        ]


class WebhookRegistration(models.Model):
    id = models.UUIDField(primary_key=True)
    integration = models.ForeignKey('Integration', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=255, db_index=True)
    external_registration_id = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=30)
    registered_at = models.DateTimeField(null=True)
    last_verified_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'webhook_registrations'


class SyncState(models.Model):
    id = models.UUIDField(primary_key=True)
    integration = models.ForeignKey('Integration', models.DO_NOTHING, db_index=True)
    entity_type = models.CharField(max_length=100)
    status = models.CharField(max_length=30)
    cursor = models.CharField(max_length=1000, null=True)
    last_successful_sync_at = models.DateTimeField(null=True)
    last_started_at = models.DateTimeField(null=True)
    last_finished_at = models.DateTimeField(null=True)
    records_synced = models.BigIntegerField(null=True, default=0)
    error_message = models.TextField(null=True)

    class Meta:
        db_table = 'sync_states'
        constraints = [
            models.UniqueConstraint(fields=['integration', 'entity_type'], name='sync_states_integration_id_entity_type_uniq'),
        ]


class IntegrationRequest(models.Model):
    id = models.UUIDField(primary_key=True)
    integration = models.ForeignKey('Integration', models.DO_NOTHING, db_index=True)
    request_type = models.CharField(max_length=50)
    endpoint = models.CharField(max_length=1000, null=True)
    method = models.CharField(max_length=20, null=True)
    status_code = models.IntegerField(null=True)
    status = models.CharField(max_length=30, db_index=True)
    attempt = models.IntegerField(default=1)
    rate_limit_remaining = models.IntegerField(null=True)
    error_message = models.TextField(null=True)
    requested_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'integration_requests'


class RawPayload(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True, db_index=True)
    integration = models.ForeignKey('Integration', models.DO_NOTHING, null=True)
    external_event_id = models.CharField(max_length=500, null=True, db_index=True)
    entity_type = models.CharField(max_length=100, null=True, db_index=True)
    payload = models.JSONField()
    received_at = models.DateTimeField(db_index=True)
    processed_at = models.DateTimeField(null=True)
    processing_status = models.CharField(max_length=30)
    processing_error = models.TextField(null=True)

    class Meta:
        db_table = 'raw_payloads'


class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    parent = models.ForeignKey('ProductCategory', models.DO_NOTHING, null=True, db_index=True)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=30)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'product_categories'
        constraints = [
            models.UniqueConstraint(fields=['business', 'slug'], name='product_categories_business_id_slug_uniq'),
        ]


class Product(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    category = models.ForeignKey('ProductCategory', models.DO_NOTHING, null=True, db_index=True)
    name = models.CharField(max_length=500)
    sku = models.CharField(max_length=255, null=True, db_index=True)
    description = models.TextField(null=True)
    product_type = models.CharField(max_length=50, null=True)
    status = models.CharField(max_length=30)
    base_price = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    currency_code = models.CharField(max_length=3, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'products'


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True)
    product = models.ForeignKey('Product', models.DO_NOTHING, db_index=True)
    sku = models.CharField(max_length=255, null=True, db_index=True)
    name = models.CharField(max_length=255, null=True)
    attributes = models.JSONField(null=True)
    price = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    status = models.CharField(max_length=30)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'product_variants'


class ProductExternalReference(models.Model):
    id = models.UUIDField(primary_key=True)
    product = models.ForeignKey('Product', models.DO_NOTHING)
    variant = models.ForeignKey('ProductVariant', models.DO_NOTHING, null=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, db_index=True)
    external_product_id = models.CharField(max_length=500, db_index=True)
    external_variant_id = models.CharField(max_length=500, null=True)
    external_sku = models.CharField(max_length=255, null=True)
    raw_name = models.CharField(max_length=500, null=True)
    normalized_name = models.CharField(max_length=500, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'product_external_references'
        constraints = [
            models.UniqueConstraint(fields=['source_system', 'external_product_id', 'external_variant_id'], name='product_external_references_source_system_id_external_product_id_external_variant_id_uniq'),
        ]


class ProductMergeCandidate(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING)
    product_id_a = models.ForeignKey('Product', models.DO_NOTHING, db_column='product_id_a', related_name='merge_candidates_as_product_a')
    product_id_b = models.ForeignKey('Product', models.DO_NOTHING, db_column='product_id_b', related_name='merge_candidates_as_product_b')
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    reason = models.CharField(max_length=1000, null=True)
    status = models.CharField(max_length=30)
    created_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'product_merge_candidates'


class Customer(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    full_name = models.CharField(max_length=500, null=True)
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    email = models.CharField(max_length=500, null=True, db_index=True)
    phone = models.CharField(max_length=100, null=True, db_index=True)
    status = models.CharField(max_length=30)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'customers'


class CustomerContact(models.Model):
    id = models.UUIDField(primary_key=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, db_index=True)
    contact_type = models.CharField(max_length=30, db_index=True)
    contact_value = models.CharField(max_length=500)
    normalized_value = models.CharField(max_length=500, null=True, db_index=True)
    is_primary = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'customer_contacts'


class CustomerTag(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'customer_tags'
        constraints = [
            models.UniqueConstraint(fields=['business', 'name'], name='customer_tags_business_id_name_uniq'),
        ]


class CustomerTagAssignment(models.Model):
    # Django 4.2 does not support composite primary keys; preserve it as a unique constraint.
    customer = models.ForeignKey('Customer', models.DO_NOTHING)
    tag = models.ForeignKey('CustomerTag', models.DO_NOTHING)
    assigned_at = models.DateTimeField()

    class Meta:
        db_table = 'customer_tag_assignments'
        constraints = [
            models.UniqueConstraint(fields=['customer', 'tag'], name='customer_tag_assignments_customer_id_tag_id_uniq'),
        ]


class CustomerMergeCandidate(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING)
    customer_id_a = models.ForeignKey('Customer', models.DO_NOTHING, db_column='customer_id_a', related_name='merge_candidates_as_customer_a')
    customer_id_b = models.ForeignKey('Customer', models.DO_NOTHING, db_column='customer_id_b', related_name='merge_candidates_as_customer_b')
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    reason = models.CharField(max_length=1000, null=True)
    status = models.CharField(max_length=30)
    created_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'customer_merge_candidates'


class Order(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True, db_index=True)
    external_order_id = models.CharField(max_length=500, null=True, db_index=True)
    order_number = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=50, db_index=True)
    currency_code = models.CharField(max_length=3)
    subtotal = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    discount_total = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    shipping_total = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    tax_total = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    placed_at = models.DateTimeField(null=True, db_index=True)
    confirmed_at = models.DateTimeField(null=True)
    cancelled_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'orders'
        constraints = [
            models.UniqueConstraint(fields=['source_system', 'external_order_id'], name='orders_source_system_id_external_order_id_uniq'),
        ]


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, db_index=True)
    product = models.ForeignKey('Product', models.DO_NOTHING, null=True, db_index=True)
    variant = models.ForeignKey('ProductVariant', models.DO_NOTHING, null=True, db_index=True)
    external_product_id = models.CharField(max_length=500, null=True)
    product_name_snapshot = models.CharField(max_length=500)
    sku_snapshot = models.CharField(max_length=255, null=True)
    quantity = models.DecimalField(max_digits=19, decimal_places=4)
    unit_price = models.DecimalField(max_digits=19, decimal_places=4)
    discount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    tax = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    line_total = models.DecimalField(max_digits=19, decimal_places=4)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'order_items'


class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, db_index=True)
    status = models.CharField(max_length=50)
    source_status = models.CharField(max_length=100, null=True)
    changed_at = models.DateTimeField(db_index=True)
    source_event_id = models.CharField(max_length=500, null=True)
    metadata = models.JSONField(null=True)

    class Meta:
        db_table = 'order_status_history'


class OrderExternalReference(models.Model):
    id = models.UUIDField(primary_key=True)
    order = models.ForeignKey('Order', models.DO_NOTHING)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING)
    external_order_id = models.CharField(max_length=500)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'order_external_references'
        constraints = [
            models.UniqueConstraint(fields=['source_system', 'external_order_id'], name='order_external_references_source_system_id_external_order_id_uniq'),
        ]


class Payment(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True)
    external_payment_id = models.CharField(max_length=500, null=True, db_index=True)
    transaction_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50, db_index=True)
    payment_method = models.CharField(max_length=50, null=True)
    currency_code = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    paid_at = models.DateTimeField(null=True, db_index=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'payments'


class Refund(models.Model):
    id = models.UUIDField(primary_key=True)
    payment = models.ForeignKey('Payment', models.DO_NOTHING, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency_code = models.CharField(max_length=3)
    reason = models.CharField(max_length=500, null=True)
    status = models.CharField(max_length=50)
    refunded_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'refunds'


class CommunicationChannel(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True, db_index=True)
    channel_type = models.CharField(max_length=50, db_index=True)
    external_channel_id = models.CharField(max_length=500, null=True)
    status = models.CharField(max_length=30)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'communication_channels'


class Message(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    channel = models.ForeignKey('CommunicationChannel', models.DO_NOTHING, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True)
    external_message_id = models.CharField(max_length=500, null=True, db_index=True)
    direction = models.CharField(max_length=20)
    sender_external_id = models.CharField(max_length=500, null=True, db_index=True)
    receiver_external_id = models.CharField(max_length=500, null=True)
    content_type = models.CharField(max_length=50, null=True)
    content = models.TextField(null=True)
    sent_at = models.DateTimeField(null=True, db_index=True)
    received_at = models.DateTimeField(null=True)
    delivery_status = models.CharField(max_length=50, null=True)
    read_status = models.CharField(max_length=50, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'messages'


class MessageAttachment(models.Model):
    id = models.UUIDField(primary_key=True)
    message = models.ForeignKey('Message', models.DO_NOTHING)
    attachment_type = models.CharField(max_length=50, null=True)
    storage_reference = models.CharField(max_length=1000, null=True)
    mime_type = models.CharField(max_length=255, null=True)
    file_name = models.CharField(max_length=500, null=True)
    file_size = models.BigIntegerField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'message_attachments'


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    channel = models.ForeignKey('CommunicationChannel', models.DO_NOTHING, null=True, db_index=True)
    status = models.CharField(max_length=50, db_index=True)
    priority = models.CharField(max_length=30, null=True, db_index=True)
    subject = models.CharField(max_length=500, null=True)
    started_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'conversations'


class ConversationMessage(models.Model):
    # Django 4.2 does not support composite primary keys; preserve it as a unique constraint.
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING)
    message = models.ForeignKey('Message', models.DO_NOTHING)

    class Meta:
        db_table = 'conversation_messages'
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'message'], name='conversation_messages_conversation_id_message_id_uniq'),
        ]


class SupportAgent(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=500, null=True)
    status = models.CharField(max_length=30, db_index=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'support_agents'


class SupportQueue(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=30)

    class Meta:
        db_table = 'support_queues'
        constraints = [
            models.UniqueConstraint(fields=['business', 'name'], name='support_queues_business_id_name_uniq'),
        ]


class ConversationAssignment(models.Model):
    id = models.UUIDField(primary_key=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, db_index=True)
    agent = models.ForeignKey('SupportAgent', models.DO_NOTHING, null=True, db_index=True)
    queue = models.ForeignKey('SupportQueue', models.DO_NOTHING, null=True, db_index=True)
    assigned_at = models.DateTimeField()
    unassigned_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'conversation_assignments'


class ConversationEvent(models.Model):
    id = models.UUIDField(primary_key=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    actor_type = models.CharField(max_length=30, null=True)
    actor_id = models.UUIDField(null=True)
    from_status = models.CharField(max_length=50, null=True)
    to_status = models.CharField(max_length=50, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'conversation_events'


class SupportInternalNote(models.Model):
    id = models.UUIDField(primary_key=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING)
    agent = models.ForeignKey('SupportAgent', models.DO_NOTHING, null=True)
    note = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'support_internal_notes'


class AdAccount(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, db_index=True)
    external_account_id = models.CharField(max_length=500)
    name = models.CharField(max_length=255, null=True)
    currency_code = models.CharField(max_length=3, null=True)
    status = models.CharField(max_length=30, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ad_accounts'
        constraints = [
            models.UniqueConstraint(fields=['source_system', 'external_account_id'], name='ad_accounts_source_system_id_external_account_id_uniq'),
        ]


class Campaign(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    ad_account = models.ForeignKey('AdAccount', models.DO_NOTHING, null=True, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True)
    external_campaign_id = models.CharField(max_length=500, null=True, db_index=True)
    name = models.CharField(max_length=500)
    status = models.CharField(max_length=50, null=True, db_index=True)
    objective = models.CharField(max_length=100, null=True)
    started_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'campaigns'


class AdSet(models.Model):
    id = models.UUIDField(primary_key=True)
    campaign = models.ForeignKey('Campaign', models.DO_NOTHING, db_index=True)
    external_ad_set_id = models.CharField(max_length=500, null=True, db_index=True)
    name = models.CharField(max_length=500, null=True)
    status = models.CharField(max_length=50, null=True)
    budget = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ad_sets'


class Ad(models.Model):
    id = models.UUIDField(primary_key=True)
    ad_set = models.ForeignKey('AdSet', models.DO_NOTHING, db_index=True)
    external_ad_id = models.CharField(max_length=500, null=True, db_index=True)
    name = models.CharField(max_length=500, null=True)
    status = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ads'


class Creative(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True)
    external_creative_id = models.CharField(max_length=500, null=True, db_index=True)
    name = models.CharField(max_length=500, null=True)
    creative_type = models.CharField(max_length=50, null=True)
    content = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'creatives'


class CampaignMetric(models.Model):
    id = models.UUIDField(primary_key=True)
    campaign = models.ForeignKey('Campaign', models.DO_NOTHING)
    metric_date = models.DateField(db_index=True)
    impressions = models.BigIntegerField(null=True, default=0)
    clicks = models.BigIntegerField(null=True, default=0)
    spend = models.DecimalField(max_digits=19, decimal_places=4, null=True, default=0)
    conversions = models.DecimalField(max_digits=19, decimal_places=4, null=True, default=0)
    conversion_value = models.DecimalField(max_digits=19, decimal_places=4, null=True, default=0)
    ctr = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    cpc = models.DecimalField(max_digits=19, decimal_places=6, null=True)
    cpa = models.DecimalField(max_digits=19, decimal_places=6, null=True)
    roas = models.DecimalField(max_digits=19, decimal_places=6, null=True)

    class Meta:
        db_table = 'campaign_metrics'
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'metric_date'], name='campaign_metrics_campaign_id_metric_date_uniq'),
        ]


class WebsiteVisitor(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    anonymous_visitor_id = models.CharField(max_length=500, null=True, db_index=True)
    first_seen_at = models.DateTimeField(null=True)
    last_seen_at = models.DateTimeField(null=True)
    device_type = models.CharField(max_length=50, null=True)
    browser = models.CharField(max_length=100, null=True)
    metadata = models.JSONField(null=True)

    class Meta:
        db_table = 'website_visitors'


class WebsiteSession(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    visitor = models.ForeignKey('WebsiteVisitor', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True)
    external_session_id = models.CharField(max_length=500, null=True, db_index=True)
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True)
    landing_page = models.CharField(max_length=1000, null=True)
    exit_page = models.CharField(max_length=1000, null=True)
    traffic_source = models.CharField(max_length=255, null=True)
    medium = models.CharField(max_length=255, null=True)
    campaign = models.ForeignKey('Campaign', models.DO_NOTHING, null=True, db_index=True)
    device_type = models.CharField(max_length=50, null=True)
    browser = models.CharField(max_length=100, null=True)

    class Meta:
        db_table = 'website_sessions'


class WebsitePageView(models.Model):
    id = models.UUIDField(primary_key=True)
    session = models.ForeignKey('WebsiteSession', models.DO_NOTHING, db_index=True)
    url = models.CharField(max_length=2000)
    title = models.CharField(max_length=1000, null=True)
    viewed_at = models.DateTimeField(db_index=True)
    duration_ms = models.BigIntegerField(null=True)

    class Meta:
        db_table = 'website_page_views'


class WebsiteEvent(models.Model):
    id = models.UUIDField(primary_key=True)
    session = models.ForeignKey('WebsiteSession', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    product = models.ForeignKey('Product', models.DO_NOTHING, null=True, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    event_name = models.CharField(max_length=255, null=True)
    event_data = models.JSONField(null=True)
    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'website_events'


class WebsiteError(models.Model):
    id = models.UUIDField(primary_key=True)
    session = models.ForeignKey('WebsiteSession', models.DO_NOTHING, null=True, db_index=True)
    error_type = models.CharField(max_length=100, null=True)
    message = models.TextField(null=True)
    url = models.CharField(max_length=2000, null=True)
    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'website_errors'


class WebsiteBehaviorSignal(models.Model):
    id = models.UUIDField(primary_key=True)
    session = models.ForeignKey('WebsiteSession', models.DO_NOTHING, db_index=True)
    signal_type = models.CharField(max_length=50, db_index=True)
    page_url = models.CharField(max_length=2000, null=True)
    event_data = models.JSONField(null=True)
    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'website_behavior_signals'


class CourierProvider(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    provider_key = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=30)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'courier_providers'
        constraints = [
            models.UniqueConstraint(fields=['business', 'provider_key'], name='courier_providers_business_id_provider_key_uniq'),
        ]


class Shipment(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, db_index=True)
    courier_provider = models.ForeignKey('CourierProvider', models.DO_NOTHING, db_index=True)
    external_shipment_id = models.CharField(max_length=500, null=True, db_index=True)
    tracking_number = models.CharField(max_length=500, null=True, db_index=True)
    status = models.CharField(max_length=50, db_index=True)
    cod_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    courier_charge = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    shipping_address = models.JSONField(null=True)
    recipient_name = models.CharField(max_length=500, null=True)
    recipient_phone = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField()
    shipped_at = models.DateTimeField(null=True)
    delivered_at = models.DateTimeField(null=True)
    returned_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'shipments'


class ShipmentEvent(models.Model):
    id = models.UUIDField(primary_key=True)
    shipment = models.ForeignKey('Shipment', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=50, null=True)
    description = models.TextField(null=True)
    occurred_at = models.DateTimeField(db_index=True)
    raw_payload = models.ForeignKey('RawPayload', models.DO_NOTHING, null=True)

    class Meta:
        db_table = 'shipment_events'


class Call(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    source_system = models.ForeignKey('SourceSystem', models.DO_NOTHING, null=True)
    external_call_id = models.CharField(max_length=500, null=True, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, null=True, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    direction = models.CharField(max_length=20)
    caller_number = models.CharField(max_length=100, null=True)
    receiver_number = models.CharField(max_length=100, null=True)
    status = models.CharField(max_length=50, null=True)
    started_at = models.DateTimeField(null=True, db_index=True)
    ended_at = models.DateTimeField(null=True)
    duration_seconds = models.IntegerField(null=True)
    recording_reference = models.CharField(max_length=1000, null=True)
    transcript = models.TextField(null=True)
    summary = models.TextField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'calls'


class CallEvent(models.Model):
    id = models.UUIDField(primary_key=True)
    call = models.ForeignKey('Call', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=50)
    event_data = models.JSONField(null=True)
    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'call_events'


class BusinessRelationship(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    relationship_type = models.CharField(max_length=100, db_index=True)
    from_entity_type = models.CharField(max_length=50)
    from_entity_id = models.UUIDField(db_index=True)
    to_entity_type = models.CharField(max_length=50)
    to_entity_id = models.UUIDField(db_index=True)
    source_type = models.CharField(max_length=30)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    is_verified = models.BooleanField(db_index=True, default=False)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'business_relationships'
        constraints = [
            models.UniqueConstraint(fields=['relationship_type', 'from_entity_id', 'to_entity_id'], name='business_relationships_relationship_type_from_entity_id_to_entity_id_uniq'),
        ]


class AttributionResult(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    campaign = models.ForeignKey('Campaign', models.DO_NOTHING, null=True, db_index=True)
    session = models.ForeignKey('WebsiteSession', models.DO_NOTHING, null=True, db_index=True)
    attribution_model = models.CharField(max_length=50, db_index=True)
    attribution_weight = models.DecimalField(max_digits=12, decimal_places=8, null=True)
    attributed_revenue = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    evidence = models.JSONField(null=True)
    calculated_at = models.DateTimeField()

    class Meta:
        db_table = 'attribution_results'


class BusinessMetric(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    metric_name = models.CharField(max_length=255, db_index=True)
    metric_date = models.DateField(db_index=True)
    dimension_type = models.CharField(max_length=100, null=True)
    dimension_id = models.UUIDField(null=True, db_index=True)
    value_numeric = models.DecimalField(max_digits=30, decimal_places=10, null=True)
    value_text = models.TextField(null=True)
    calculation_version = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'business_metrics'
        constraints = [
            models.UniqueConstraint(fields=['business', 'metric_name', 'metric_date', 'dimension_type', 'dimension_id'], name='business_metrics_business_id_metric_name_metric_date_dimension_type_dimension_id_uniq'),
        ]


class BusinessFlawCandidate(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    flaw_type = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True)
    severity = models.CharField(max_length=30, null=True, db_index=True)
    detected_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=30, db_index=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    evidence = models.JSONField(null=True)

    class Meta:
        db_table = 'business_flaw_candidates'


class VerifiedBusinessFact(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    fact_type = models.CharField(max_length=100, db_index=True)
    subject_entity_type = models.CharField(max_length=50, null=True)
    subject_entity_id = models.UUIDField(null=True, db_index=True)
    fact_value = models.JSONField()
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    calculation_version = models.CharField(max_length=100, null=True)
    valid_from = models.DateTimeField(null=True, db_index=True)
    valid_until = models.DateTimeField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'verified_business_facts'


class EvidenceRecord(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    fact = models.ForeignKey('VerifiedBusinessFact', models.DO_NOTHING, null=True, db_index=True)
    relationship = models.ForeignKey('BusinessRelationship', models.DO_NOTHING, null=True, db_index=True)
    source_entity_type = models.CharField(max_length=50, null=True)
    source_entity_id = models.UUIDField(null=True, db_index=True)
    raw_payload = models.ForeignKey('RawPayload', models.DO_NOTHING, null=True)
    evidence_type = models.CharField(max_length=50, null=True)
    evidence_data = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'evidence_records'


class GraphNode(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    node_type = models.CharField(max_length=100, db_index=True)
    label = models.CharField(max_length=500, null=True)
    properties = models.JSONField(null=True)
    snapshot_version = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'graph_nodes'
        constraints = [
            models.UniqueConstraint(fields=['business', 'entity_type', 'entity_id', 'snapshot_version'], name='graph_nodes_business_id_entity_type_entity_id_snapshot_version_uniq'),
        ]


class GraphEdge(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    from_node = models.ForeignKey('GraphNode', models.DO_NOTHING, db_index=True, related_name='outgoing_edges')
    to_node = models.ForeignKey('GraphNode', models.DO_NOTHING, db_index=True, related_name='incoming_edges')
    relationship_type = models.CharField(max_length=100, db_index=True)
    weight = models.DecimalField(max_digits=19, decimal_places=6, null=True)
    properties = models.JSONField(null=True)
    evidence = models.ForeignKey('EvidenceRecord', models.DO_NOTHING, null=True)
    snapshot_version = models.CharField(max_length=100, null=True, db_index=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'graph_edges'


class GraphSnapshot(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    version = models.CharField(max_length=100)
    generated_at = models.DateTimeField()
    node_count = models.BigIntegerField(null=True)
    edge_count = models.BigIntegerField(null=True)
    status = models.CharField(max_length=30)

    class Meta:
        db_table = 'graph_snapshots'
        constraints = [
            models.UniqueConstraint(fields=['business', 'version'], name='graph_snapshots_business_id_version_uniq'),
        ]


class MemoryDocument(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    document_type = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=500, null=True)
    source_reference = models.CharField(max_length=1000, null=True)
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=30, db_index=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'memory_documents'


class MemoryChunk(models.Model):
    id = models.UUIDField(primary_key=True)
    document = models.ForeignKey('MemoryDocument', models.DO_NOTHING, db_index=True)
    chunk_index = models.IntegerField()
    content = models.TextField()
    metadata = models.JSONField(null=True)
    embedding = VectorField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'memory_chunks'
        constraints = [
            models.UniqueConstraint(fields=['document', 'chunk_index'], name='memory_chunks_document_id_chunk_index_uniq'),
        ]


class BusinessMemory(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    memory_type = models.CharField(max_length=100, db_index=True)
    subject_entity_type = models.CharField(max_length=50, null=True)
    subject_entity_id = models.UUIDField(null=True, db_index=True)
    content = models.TextField()
    metadata = models.JSONField(null=True)
    source_reference = models.CharField(max_length=1000, null=True)
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(db_index=True, default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'business_memory'


class ApprovedSuggestion(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING)
    suggestion_type = models.CharField(max_length=100, null=True)
    title = models.CharField(max_length=500, null=True)
    suggestion = models.TextField()
    approved_by = models.UUIDField(null=True)
    approved_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=30)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'approved_suggestions'


class AiProvider(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    provider_key = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30)
    configuration = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ai_providers'


class AiModel(models.Model):
    id = models.UUIDField(primary_key=True)
    provider = models.ForeignKey('AiProvider', models.DO_NOTHING)
    model_name = models.CharField(max_length=255)
    model_type = models.CharField(max_length=50, null=True)
    configuration = models.JSONField(null=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ai_models'


class AiPrompt(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, null=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    version = models.IntegerField()
    template = models.TextField()
    status = models.CharField(max_length=30)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ai_prompts'
        constraints = [
            models.UniqueConstraint(fields=['business', 'name', 'version'], name='ai_prompts_business_id_name_version_uniq'),
        ]


class AiRun(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING)
    model = models.ForeignKey('AiModel', models.DO_NOTHING)
    prompt = models.ForeignKey('AiPrompt', models.DO_NOTHING, null=True)
    task_type = models.CharField(max_length=100)
    input_context = models.JSONField(null=True)
    output = models.JSONField(null=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    status = models.CharField(max_length=30)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'ai_runs'


class AiRecommendation(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    run = models.ForeignKey('AiRun', models.DO_NOTHING, null=True)
    recommendation_type = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=500)
    recommendation = models.TextField()
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    evidence_summary = models.JSONField(null=True)
    suggested_action = models.JSONField(null=True)
    status = models.CharField(max_length=30, db_index=True)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'ai_recommendations'


class AiAction(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING)
    recommendation = models.ForeignKey('AiRecommendation', models.DO_NOTHING, null=True)
    integration = models.ForeignKey('Integration', models.DO_NOTHING, null=True)
    action_type = models.CharField(max_length=100)
    action_payload = models.JSONField(null=True)
    approval_status = models.CharField(max_length=30)
    approved_by = models.UUIDField(null=True)
    approved_at = models.DateTimeField(null=True)
    execution_status = models.CharField(max_length=30, null=True)
    executed_at = models.DateTimeField(null=True)
    execution_result = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ai_actions'


class AiAuditLog(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    run = models.ForeignKey('AiRun', models.DO_NOTHING, null=True, db_index=True)
    action = models.ForeignKey('AiAction', models.DO_NOTHING, null=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    input_hash = models.CharField(max_length=255, null=True)
    output_hash = models.CharField(max_length=255, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'ai_audit_logs'


class MockScenario(models.Model):
    id = models.UUIDField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    seed = models.BigIntegerField()
    scenario_config = models.JSONField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'mock_scenarios'


class MockPlatform(models.Model):
    id = models.UUIDField(primary_key=True)
    scenario = models.ForeignKey('MockScenario', models.DO_NOTHING, db_index=True)
    platform_key = models.CharField(max_length=100)
    platform_type = models.CharField(max_length=100)
    configuration = models.JSONField(null=True)

    class Meta:
        db_table = 'mock_platforms'
        constraints = [
            models.UniqueConstraint(fields=['scenario', 'platform_key'], name='mock_platforms_scenario_id_platform_key_uniq'),
        ]


class MockEntity(models.Model):
    id = models.UUIDField(primary_key=True)
    platform = models.ForeignKey('MockPlatform', models.DO_NOTHING, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    external_id = models.CharField(max_length=500, db_index=True)
    payload = models.JSONField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'mock_entities'
        constraints = [
            models.UniqueConstraint(fields=['platform', 'entity_type', 'external_id'], name='mock_entities_platform_id_entity_type_external_id_uniq'),
        ]


class MockExpectedResult(models.Model):
    id = models.UUIDField(primary_key=True)
    scenario = models.ForeignKey('MockScenario', models.DO_NOTHING, db_index=True)
    result_type = models.CharField(max_length=100, db_index=True)
    expected_value = models.JSONField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'mock_expected_results'
