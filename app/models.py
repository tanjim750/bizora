from django.db import models


class VectorField(models.Field):
    description = "PostgreSQL pgvector field"

    def db_type(self, connection):
        return 'vector'


class Business(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True)
    currency = models.CharField(max_length=10, default='BDT')
    timezone = models.CharField(max_length=100, default='Asia/Dhaka')
    status = models.CharField(max_length=30, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'businesses'


class IntegrationSource(models.Model):
    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50)
    connection_type = models.CharField(max_length=50, null=True)
    description = models.TextField(null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integration_sources'


class IntegrationConnection(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING)
    integration_source = models.ForeignKey('IntegrationSource', models.DO_NOTHING)
    name = models.CharField(max_length=150, null=True)
    status = models.CharField(max_length=30, default='CONNECTED')
    external_account_id = models.CharField(max_length=255, null=True)
    external_account_name = models.CharField(max_length=255, null=True)
    config = models.JSONField(null=True)
    is_mock = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True)
    last_successful_sync_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integration_connections'
        indexes = [
            models.Index(fields=['business', 'integration_source'], name='idx_ic_bi_ed5ceb0a'),
        ]


class IntegrationSyncLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING)
    sync_type = models.CharField(max_length=50, null=True)
    status = models.CharField(max_length=30)
    records_received = models.IntegerField(default=0)
    records_processed = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    error_message = models.TextField(null=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'integration_sync_logs'


class Product(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=150, null=True)
    description = models.TextField(null=True)
    category = models.CharField(max_length=150, null=True)
    status = models.CharField(max_length=30, default='ACTIVE')
    price = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    currency = models.CharField(max_length=10, default='BDT')
    inventory_quantity = models.IntegerField(null=True)
    image_url = models.TextField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['business', 'sku'], name='products_business_id_sku_idx'),
        ]


class ProductVariant(models.Model):
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey('Product', models.DO_NOTHING, db_index=True)
    name = models.CharField(max_length=255, null=True)
    sku = models.CharField(max_length=150, null=True)
    attributes = models.JSONField(null=True)
    price = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    inventory_quantity = models.IntegerField(null=True)
    status = models.CharField(max_length=30, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_variants'
        indexes = [
            models.Index(fields=['product', 'sku'], name='idx_pv_ps_6d6676a7'),
        ]


class ProductExternalReference(models.Model):
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey('Product', models.DO_NOTHING, db_index=True)
    product_variant = models.ForeignKey('ProductVariant', models.DO_NOTHING, null=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, db_index=True)
    external_product_id = models.CharField(max_length=255)
    external_variant_id = models.CharField(max_length=255, null=True)
    external_sku = models.CharField(max_length=150, null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_external_references'
        constraints = [
            models.UniqueConstraint(fields=['integration_connection', 'external_product_id'], name='uniq_per_ie_59b162fe'),
        ]


class Customer(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.CASCADE, db_index=True)
    first_name = models.CharField(max_length=150, null=True)
    last_name = models.CharField(max_length=150, null=True)
    display_name = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=30, default='ACTIVE')
    customer_type = models.CharField(max_length=30, null=True, default='KNOWN')
    notes = models.TextField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['business', 'status'], name='idx_c_bs_ca0ea3d1'),
        ]


class CustomerContact(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, db_index=True)
    contact_type = models.CharField(max_length=30)
    value = models.CharField(max_length=255)
    normalized_value = models.CharField(max_length=255, null=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_contacts'
        indexes = [
            models.Index(fields=['contact_type', 'normalized_value'], name='idx_cc_cn_c0f401e1'),
        ]


class CustomerTag(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, db_index=True)
    tag = models.CharField(max_length=100)
    source = models.CharField(max_length=50, null=True, default='MANUAL')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_tags'
        constraints = [
            models.UniqueConstraint(fields=['customer', 'tag'], name='uniq_ct_ct_7a88ea26'),
        ]


class CustomerExternalReference(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, db_index=True)
    external_customer_id = models.CharField(max_length=255)
    external_username = models.CharField(max_length=255, null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_external_references'
        constraints = [
            models.UniqueConstraint(fields=['integration_connection', 'external_customer_id'], name='uniq_cer_ie_ba4ee2c5'),
        ]


class CustomerTimelineEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50, null=True)
    entity_id = models.BigIntegerField(null=True)
    title = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)
    event_at = models.DateTimeField()
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_timeline_events'
        indexes = [
            models.Index(fields=['customer', 'event_at'], name='idx_cte_ce_e6c9cd11'),
        ]


class Order(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True)
    external_order_id = models.CharField(max_length=255, null=True)
    order_number = models.CharField(max_length=100, null=True)
    status = models.CharField(max_length=50, default='PENDING')
    currency = models.CharField(max_length=10, default='BDT')
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    source_metadata = models.JSONField(null=True)
    ordered_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['business', 'order_number'], name='idx_o_bo_aa20390b'),
            models.Index(fields=['integration_connection', 'external_order_id'], name='idx_o_ie_7dba8af9'),
        ]


class OrderItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, db_index=True)
    product = models.ForeignKey('Product', models.DO_NOTHING, null=True, db_index=True)
    product_variant = models.ForeignKey('ProductVariant', models.DO_NOTHING, null=True)
    external_product_id = models.CharField(max_length=255, null=True)
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=150, null=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=18, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'


class OrderStatusHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, db_index=True)
    from_status = models.CharField(max_length=50, null=True)
    to_status = models.CharField(max_length=50)
    source = models.CharField(max_length=50, default='SYSTEM')
    note = models.TextField(null=True)
    changed_at = models.DateTimeField()
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_status_history'
        indexes = [
            models.Index(fields=['order', 'changed_at'], name='idx_osh_oc_915dee58'),
        ]


class Payment(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True)
    external_payment_id = models.CharField(max_length=255, null=True)
    transaction_reference = models.CharField(max_length=255, null=True)
    payment_method = models.CharField(max_length=50, null=True)
    status = models.CharField(max_length=50, default='PENDING')
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    paid_at = models.DateTimeField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['integration_connection', 'external_payment_id'], name='idx_p_ie_5e48c9ea'),
        ]


class Refund(models.Model):
    id = models.BigAutoField(primary_key=True)
    payment = models.ForeignKey('Payment', models.DO_NOTHING, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    external_refund_id = models.CharField(max_length=255, null=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    status = models.CharField(max_length=50, default='PENDING')
    reason = models.TextField(null=True)
    refunded_at = models.DateTimeField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'refunds'


class Conversation(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True)
    external_conversation_id = models.CharField(max_length=255, null=True)
    channel = models.CharField(max_length=50)
    status = models.CharField(max_length=50, default='OPEN')
    priority = models.CharField(max_length=30, default='NORMAL')
    subject = models.CharField(max_length=255, null=True)
    ai_handover_state = models.CharField(max_length=50, null=True)
    started_at = models.DateTimeField()
    last_message_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        indexes = [
            models.Index(fields=['business', 'status'], name='idx_c_bs_110fd367'),
            models.Index(fields=['integration_connection', 'external_conversation_id'], name='idx_c_ie_d2ff00d8'),
        ]


class ConversationParticipant(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    participant_type = models.CharField(max_length=50)
    external_user_id = models.CharField(max_length=255, null=True)
    display_name = models.CharField(max_length=255, null=True)
    joined_at = models.DateTimeField(null=True)
    left_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conversation_participants'
        indexes = [
            models.Index(fields=['conversation', 'participant_type'], name='idx_cp_cp_6fb687ea'),
        ]


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True)
    external_message_id = models.CharField(max_length=255, null=True)
    direction = models.CharField(max_length=30)
    sender_type = models.CharField(max_length=30)
    message_type = models.CharField(max_length=30, default='TEXT')
    content = models.TextField(null=True)
    delivery_status = models.CharField(max_length=30, null=True)
    read_status = models.CharField(max_length=30, null=True)
    sent_at = models.DateTimeField(null=True)
    delivered_at = models.DateTimeField(null=True)
    read_at = models.DateTimeField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messages'
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='idx_m_cc_c7ae5854'),
            models.Index(fields=['integration_connection', 'external_message_id'], name='idx_m_ie_e794f968'),
        ]


class MessageAttachment(models.Model):
    id = models.BigAutoField(primary_key=True)
    message = models.ForeignKey('Message', models.DO_NOTHING, db_index=True)
    attachment_type = models.CharField(max_length=30)
    file_name = models.CharField(max_length=255, null=True)
    mime_type = models.CharField(max_length=100, null=True)
    url = models.TextField()
    size_bytes = models.BigIntegerField(null=True)
    external_attachment_id = models.CharField(max_length=255, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_attachments'


class ConversationAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, db_index=True)
    assignee_type = models.CharField(max_length=30)
    assignee_id = models.BigIntegerField(null=True)
    assigned_by_type = models.CharField(max_length=30, null=True)
    assigned_by_id = models.BigIntegerField(null=True)
    status = models.CharField(max_length=30, default='ACTIVE')
    assigned_at = models.DateTimeField()
    unassigned_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conversation_assignments'
        indexes = [
            models.Index(fields=['conversation', 'status'], name='idx_ca_cs_2fd44831'),
            models.Index(fields=['assignee_type', 'assignee_id'], name='idx_ca_aa_4a9f40d0'),
        ]


class ConversationNote(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, db_index=True)
    author_type = models.CharField(max_length=30)
    author_id = models.BigIntegerField(null=True)
    content = models.TextField()
    is_ai_generated = models.BooleanField(default=False)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversation_notes'
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='idx_cn_cc_0b99cb2a'),
        ]


class Call(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    conversation = models.ForeignKey('Conversation', models.DO_NOTHING, null=True, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True)
    external_call_id = models.CharField(max_length=255, null=True)
    direction = models.CharField(max_length=30)
    caller_number = models.CharField(max_length=50, null=True)
    receiver_number = models.CharField(max_length=50, null=True)
    status = models.CharField(max_length=30)
    started_at = models.DateTimeField(null=True)
    answered_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)
    duration_seconds = models.IntegerField(null=True)
    recording_url = models.TextField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'calls'
        indexes = [
            models.Index(fields=['integration_connection', 'external_call_id'], name='idx_c_ie_3a15bbbf'),
        ]


class CallEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    call = models.ForeignKey('Call', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=50)
    event_at = models.DateTimeField()
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'call_events'
        indexes = [
            models.Index(fields=['call', 'event_at'], name='idx_ce_ce_a03744df'),
        ]


class CallTranscript(models.Model):
    id = models.BigAutoField(primary_key=True)
    call = models.ForeignKey('Call', models.DO_NOTHING, db_index=True)
    transcript = models.TextField(null=True)
    summary = models.TextField(null=True)
    language = models.CharField(max_length=20, null=True)
    provider = models.CharField(max_length=100, null=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    generated_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'call_transcripts'


class Campaign(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True, db_index=True)
    external_campaign_id = models.CharField(max_length=255, null=True)
    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=50)
    objective = models.CharField(max_length=100, null=True)
    status = models.CharField(max_length=30, default='ACTIVE')
    budget = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    currency = models.CharField(max_length=10, default='BDT')
    started_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'campaigns'
        indexes = [
            models.Index(fields=['integration_connection', 'external_campaign_id'], name='idx_c_ie_4f9caf69'),
        ]


class CampaignMetric(models.Model):
    id = models.BigAutoField(primary_key=True)
    campaign = models.ForeignKey('Campaign', models.DO_NOTHING, db_index=True)
    metric_date = models.DateField()
    impressions = models.BigIntegerField(default=0)
    reach = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    spend = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    conversions = models.BigIntegerField(default=0)
    conversion_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ctr = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    cpc = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    cpm = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    roas = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'campaign_metrics'
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'metric_date'], name='uniq_cm_cm_dc5e6e6f'),
        ]


class CampaignConversion(models.Model):
    id = models.BigAutoField(primary_key=True)
    campaign = models.ForeignKey('Campaign', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True, db_index=True)
    website_session_id = models.BigIntegerField(null=True)
    conversion_type = models.CharField(max_length=50)
    conversion_value = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    currency = models.CharField(max_length=10, null=True, default='BDT')
    attribution_type = models.CharField(max_length=50, null=True)
    converted_at = models.DateTimeField()
    external_conversion_id = models.CharField(max_length=255, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'campaign_conversions'
        indexes = [
            models.Index(fields=['campaign', 'converted_at'], name='idx_cc_cc_426fe84d'),
        ]


class WebsiteVisitor(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    visitor_key = models.CharField(max_length=255)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(null=True)
    is_anonymous = models.BooleanField(default=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'website_visitors'
        constraints = [
            models.UniqueConstraint(fields=['business', 'visitor_key'], name='uniq_wv_bv_1f6e4b60'),
        ]


class WebsiteSession(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    visitor = models.ForeignKey('WebsiteVisitor', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True)
    external_session_id = models.CharField(max_length=255, null=True)
    traffic_source = models.CharField(max_length=100, null=True)
    traffic_medium = models.CharField(max_length=100, null=True)
    utm_source = models.CharField(max_length=150, null=True)
    utm_medium = models.CharField(max_length=150, null=True)
    utm_campaign = models.CharField(max_length=150, null=True)
    utm_term = models.CharField(max_length=150, null=True)
    utm_content = models.CharField(max_length=150, null=True)
    landing_page_url = models.TextField(null=True)
    exit_page_url = models.TextField(null=True)
    device_type = models.CharField(max_length=50, null=True)
    operating_system = models.CharField(max_length=100, null=True)
    browser = models.CharField(max_length=100, null=True)
    country = models.CharField(max_length=100, null=True)
    city = models.CharField(max_length=100, null=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True)
    duration_seconds = models.IntegerField(null=True)
    is_converted = models.BooleanField(default=False)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'website_sessions'
        indexes = [
            models.Index(fields=['integration_connection', 'external_session_id'], name='idx_ws_ie_0ea2c372'),
            models.Index(fields=['business', 'started_at'], name='idx_ws_bs_f81abfb0'),
        ]


class WebsiteEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey('WebsiteSession', models.DO_NOTHING, db_index=True)
    visitor = models.ForeignKey('WebsiteVisitor', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    product = models.ForeignKey('Product', models.DO_NOTHING, null=True, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, null=True)
    event_type = models.CharField(max_length=100)
    page_url = models.TextField(null=True)
    page_title = models.CharField(max_length=255, null=True)
    event_value = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    currency = models.CharField(max_length=10, null=True)
    occurred_at = models.DateTimeField()
    properties = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_events'
        indexes = [
            models.Index(fields=['session', 'occurred_at'], name='idx_we_so_5b5642b4'),
            models.Index(fields=['event_type', 'occurred_at'], name='idx_we_eo_3dfff252'),
        ]


class Shipment(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    order = models.ForeignKey('Order', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True)
    external_shipment_id = models.CharField(max_length=255, null=True)
    tracking_code = models.CharField(max_length=255, null=True, db_index=True)
    provider = models.CharField(max_length=100)
    status = models.CharField(max_length=50, default='PENDING')
    delivery_charge = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cod_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='BDT')
    recipient_name = models.CharField(max_length=255, null=True)
    recipient_phone = models.CharField(max_length=50, null=True)
    delivery_address = models.TextField(null=True)
    submitted_at = models.DateTimeField(null=True)
    picked_up_at = models.DateTimeField(null=True)
    delivered_at = models.DateTimeField(null=True)
    returned_at = models.DateTimeField(null=True)
    source_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shipments'
        indexes = [
            models.Index(fields=['integration_connection', 'external_shipment_id'], name='idx_s_ie_00245bb6'),
        ]


class ShipmentEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    shipment = models.ForeignKey('Shipment', models.DO_NOTHING, db_index=True)
    event_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50, null=True)
    description = models.TextField(null=True)
    location = models.CharField(max_length=255, null=True)
    occurred_at = models.DateTimeField()
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shipment_events'
        indexes = [
            models.Index(fields=['shipment', 'occurred_at'], name='idx_se_so_b50a3e29'),
        ]


class CanonicalIdentity(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    entity_type = models.CharField(max_length=50)
    entity_id = models.BigIntegerField()
    canonical_key = models.CharField(max_length=255)
    status = models.CharField(max_length=30, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'canonical_identities'
        constraints = [
            models.UniqueConstraint(fields=['business', 'canonical_key'], name='uniq_ci_bc_f8e5ee71'),
            models.UniqueConstraint(fields=['business', 'entity_type', 'entity_id'], name='uniq_ci_bee_aeb8e724'),
        ]


class ExternalIdentity(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    integration_connection = models.ForeignKey('IntegrationConnection', models.DO_NOTHING, null=True, db_index=True)
    provider = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    external_id = models.CharField(max_length=255, null=True)
    identity_type = models.CharField(max_length=50, null=True)
    identity_value = models.CharField(max_length=500, null=True)
    normalized_value = models.CharField(max_length=500, null=True)
    metadata = models.JSONField(null=True)
    first_seen_at = models.DateTimeField(null=True)
    last_seen_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'external_identities'
        indexes = [
            models.Index(fields=['business', 'provider', 'entity_type', 'external_id'], name='idx_ei_bpee_f2296c64'),
            models.Index(fields=['business', 'identity_type', 'normalized_value'], name='idx_ei_bin_20e621c2'),
        ]


class IdentityLink(models.Model):
    id = models.BigAutoField(primary_key=True)
    canonical_identity = models.ForeignKey('CanonicalIdentity', models.DO_NOTHING, db_index=True)
    external_identity = models.ForeignKey('ExternalIdentity', models.DO_NOTHING, db_index=True)
    match_type = models.CharField(max_length=50)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    status = models.CharField(max_length=30, default='ACTIVE')
    resolved_by = models.CharField(max_length=30, default='SYSTEM')
    rule_key = models.CharField(max_length=100, null=True)
    linked_at = models.DateTimeField()
    unlinked_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'identity_links'
        constraints = [
            models.UniqueConstraint(fields=['canonical_identity', 'external_identity'], name='uniq_il_ce_06c86f9a'),
        ]


class IdentityMergeCandidate(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    primary_identity = models.ForeignKey('CanonicalIdentity', models.DO_NOTHING, related_name='identity_merge_candidates_as_primary_identity', db_index=True)
    candidate_identity = models.ForeignKey('CanonicalIdentity', models.DO_NOTHING, related_name='identity_merge_candidates_as_candidate_identity', db_index=True)
    match_reason = models.CharField(max_length=255, null=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    status = models.CharField(max_length=30, default='PENDING')
    evidence = models.JSONField(null=True)
    detected_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'identity_merge_candidates'
        constraints = [
            models.UniqueConstraint(fields=['primary_identity', 'candidate_identity'], name='uniq_imc_pc_7b0b2f92'),
        ]


class IdentityConflict(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    external_identity = models.ForeignKey('ExternalIdentity', models.DO_NOTHING, null=True, db_index=True)
    canonical_identity = models.ForeignKey('CanonicalIdentity', models.DO_NOTHING, null=True, db_index=True)
    conflict_type = models.CharField(max_length=100)
    description = models.TextField(null=True)
    conflicting_data = models.JSONField(null=True)
    severity = models.CharField(max_length=30, default='MEDIUM')
    status = models.CharField(max_length=30, default='OPEN')
    detected_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True)
    resolution_note = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'identity_conflicts'
        indexes = [
            models.Index(fields=['business', 'status'], name='idx_ic_bs_998465ad'),
        ]


class BusinessRelationship(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    source_entity_type = models.CharField(max_length=50)
    source_entity_id = models.BigIntegerField()
    relationship_type = models.CharField(max_length=100)
    target_entity_type = models.CharField(max_length=50)
    target_entity_id = models.BigIntegerField()
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    rule_key = models.CharField(max_length=100, null=True)
    relationship_source = models.CharField(max_length=30, default='DETERMINISTIC')
    valid_from = models.DateTimeField(null=True)
    valid_to = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_relationships'
        indexes = [
            models.Index(fields=['business', 'source_entity_type', 'source_entity_id'], name='idx_br_bss_a41d3e19'),
            models.Index(fields=['business', 'target_entity_type', 'target_entity_id'], name='idx_br_btt_57388599'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['business', 'source_entity_type', 'source_entity_id', 'relationship_type', 'target_entity_type', 'target_entity_id'], name='uniq_br_bssrtt_3450c070'),
        ]


class BusinessMetric(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    key = models.CharField(max_length=100)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, db_index=True)
    value_type = models.CharField(max_length=30, default='NUMBER')
    unit = models.CharField(max_length=30, null=True)
    description = models.TextField(null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_metrics'
        constraints = [
            models.UniqueConstraint(fields=['business', 'key'], name='uniq_bm_bk_5e30defb'),
        ]


class MetricSnapshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    metric = models.ForeignKey('BusinessMetric', models.DO_NOTHING, db_index=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    value = models.DecimalField(max_digits=24, decimal_places=6)
    dimension_type = models.CharField(max_length=50, null=True)
    dimension_value = models.CharField(max_length=255, null=True)
    period_type = models.CharField(max_length=30, null=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    calculation_rule = models.CharField(max_length=100, null=True)
    metadata = models.JSONField(null=True)
    calculated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metric_snapshots'
        indexes = [
            models.Index(fields=['business', 'period_start', 'period_end'], name='idx_ms_bpp_447e2dae'),
            models.Index(fields=['metric', 'period_start', 'period_end'], name='idx_ms_mpp_b4c7abee'),
            models.Index(fields=['metric', 'dimension_type', 'dimension_value', 'period_start'], name='idx_ms_mddp_9ac73a17'),
        ]


class BusinessFact(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    fact_type = models.CharField(max_length=100, db_index=True)
    subject_entity_type = models.CharField(max_length=50, null=True)
    subject_entity_id = models.BigIntegerField(null=True)
    statement = models.TextField()
    value = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    value_unit = models.CharField(max_length=30, null=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    status = models.CharField(max_length=30, db_index=True, default='VERIFIED')
    rule_key = models.CharField(max_length=100, null=True)
    valid_from = models.DateTimeField(null=True)
    valid_to = models.DateTimeField(null=True)
    detected_at = models.DateTimeField()
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_facts'
        indexes = [
            models.Index(fields=['business', 'subject_entity_type', 'subject_entity_id'], name='idx_bf_bss_67ae0c41'),
            models.Index(fields=['business', 'detected_at'], name='idx_bf_bd_e755568c'),
        ]


class BusinessFactEvidence(models.Model):
    id = models.BigAutoField(primary_key=True)
    business_fact = models.ForeignKey('BusinessFact', models.DO_NOTHING, db_index=True)
    evidence_type = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50, null=True)
    entity_id = models.BigIntegerField(null=True)
    metric_snapshot = models.ForeignKey('MetricSnapshot', models.DO_NOTHING, null=True, db_index=True)
    relationship = models.ForeignKey('BusinessRelationship', models.DO_NOTHING, null=True, db_index=True)
    description = models.TextField(null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    evidence_data = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'business_fact_evidence'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id'], name='idx_bfe_ee_99359f64'),
        ]


class BusinessIssue(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    issue_type = models.CharField(max_length=100, db_index=True)
    subject_entity_type = models.CharField(max_length=50, null=True)
    subject_entity_id = models.BigIntegerField(null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    severity = models.CharField(max_length=30, db_index=True, default='MEDIUM')
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    status = models.CharField(max_length=30, db_index=True, default='OPEN')
    rule_key = models.CharField(max_length=100, null=True)
    detected_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_issues'
        indexes = [
            models.Index(fields=['business', 'subject_entity_type', 'subject_entity_id'], name='idx_bi_bss_188e9e6e'),
            models.Index(fields=['business', 'detected_at'], name='idx_bi_bd_72bff261'),
        ]


class BusinessIssueEvidence(models.Model):
    id = models.BigAutoField(primary_key=True)
    business_issue = models.ForeignKey('BusinessIssue', models.DO_NOTHING, db_index=True)
    business_fact = models.ForeignKey('BusinessFact', models.DO_NOTHING, null=True, db_index=True)
    metric_snapshot = models.ForeignKey('MetricSnapshot', models.DO_NOTHING, null=True, db_index=True)
    relationship = models.ForeignKey('BusinessRelationship', models.DO_NOTHING, null=True, db_index=True)
    entity_type = models.CharField(max_length=50, null=True)
    entity_id = models.BigIntegerField(null=True)
    evidence_type = models.CharField(max_length=50)
    description = models.TextField(null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    evidence_data = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'business_issue_evidence'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id'], name='idx_bie_ee_8ca4df53'),
        ]


class GraphNode(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    entity_type = models.CharField(max_length=50)
    entity_id = models.BigIntegerField()
    canonical_identity = models.ForeignKey('CanonicalIdentity', models.DO_NOTHING, null=True, db_index=True)
    label = models.CharField(max_length=255, null=True)
    node_type = models.CharField(max_length=50)
    properties = models.JSONField(null=True)
    first_seen_at = models.DateTimeField(null=True)
    last_seen_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graph_nodes'
        indexes = [
            models.Index(fields=['business', 'node_type'], name='idx_gn_bn_f69a85e8'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['business', 'entity_type', 'entity_id'], name='uniq_gn_bee_f646ff19'),
        ]


class GraphEdge(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    source_node = models.ForeignKey('GraphNode', models.DO_NOTHING, related_name='graph_edges_as_source_node', db_index=True)
    target_node = models.ForeignKey('GraphNode', models.DO_NOTHING, related_name='graph_edges_as_target_node', db_index=True)
    relationship_type = models.CharField(max_length=100, db_index=True)
    business_relationship = models.ForeignKey('BusinessRelationship', models.DO_NOTHING, null=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    properties = models.JSONField(null=True)
    valid_from = models.DateTimeField(null=True)
    valid_to = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graph_edges'
        constraints = [
            models.UniqueConstraint(fields=['source_node', 'target_node', 'relationship_type'], name='uniq_ge_str_a4372400'),
        ]


class GraphSnapshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    name = models.CharField(max_length=255, null=True)
    snapshot_type = models.CharField(max_length=50, default='BUSINESS')
    root_entity_type = models.CharField(max_length=50, null=True)
    root_entity_id = models.BigIntegerField(null=True)
    node_count = models.IntegerField(default=0)
    edge_count = models.IntegerField(default=0)
    filters = models.JSONField(null=True)
    snapshot_data = models.JSONField(null=True)
    generated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'graph_snapshots'
        indexes = [
            models.Index(fields=['business', 'generated_at'], name='idx_gs_bg_4e888a8b'),
            models.Index(fields=['business', 'snapshot_type'], name='idx_gs_bs_228b8834'),
        ]


class KnowledgeSource(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, db_index=True)
    knowledge_type = models.CharField(max_length=50, null=True, db_index=True)
    status = models.CharField(max_length=30, default='ACTIVE')
    source_reference = models.TextField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'knowledge_sources'
        indexes = [
            models.Index(fields=['business', 'status'], name='idx_ks_bs_b0940d90'),
        ]


class KnowledgeDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    knowledge_source = models.ForeignKey('KnowledgeSource', models.DO_NOTHING, db_index=True)
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50, null=True)
    content = models.TextField(null=True)
    file_name = models.CharField(max_length=255, null=True)
    file_url = models.TextField(null=True)
    mime_type = models.CharField(max_length=100, null=True)
    status = models.CharField(max_length=30, default='READY')
    version = models.IntegerField(default=1)
    content_hash = models.CharField(max_length=255, null=True)
    metadata = models.JSONField(null=True)
    ingested_at = models.DateTimeField(null=True)
    processed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'knowledge_documents'
        indexes = [
            models.Index(fields=['business', 'status'], name='idx_kd_bs_308ddf8c'),
            models.Index(fields=['knowledge_source', 'version'], name='idx_kd_kv_0d3750ea'),
        ]


class KnowledgeChunk(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    knowledge_document = models.ForeignKey('KnowledgeDocument', models.DO_NOTHING, db_index=True)
    chunk_index = models.IntegerField()
    content = models.TextField()
    token_count = models.IntegerField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'knowledge_chunks'
        constraints = [
            models.UniqueConstraint(fields=['knowledge_document', 'chunk_index'], name='uniq_kc_kc_ccf427c3'),
        ]


class KnowledgeEmbedding(models.Model):
    id = models.BigAutoField(primary_key=True)
    knowledge_chunk = models.ForeignKey('KnowledgeChunk', models.DO_NOTHING, db_index=True)
    model = models.CharField(max_length=150)
    dimensions = models.IntegerField()
    embedding = VectorField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'knowledge_embeddings'
        constraints = [
            models.UniqueConstraint(fields=['knowledge_chunk', 'model'], name='uniq_ke_km_00400001'),
        ]


class AiConversation(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    customer = models.ForeignKey('Customer', models.DO_NOTHING, null=True, db_index=True)
    support_conversation = models.ForeignKey('Conversation', models.DO_NOTHING, null=True, db_index=True)
    conversation_type = models.CharField(max_length=50, default='BUSINESS_ASSISTANT')
    title = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=30, default='ACTIVE')
    context_summary = models.TextField(null=True)
    metadata = models.JSONField(null=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_conversations'
        indexes = [
            models.Index(fields=['business', 'conversation_type'], name='idx_ac_bc_545caf25'),
            models.Index(fields=['business', 'status'], name='idx_ac_bs_5d48b916'),
        ]


class AiMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    ai_conversation = models.ForeignKey('AiConversation', models.DO_NOTHING, db_index=True)
    role = models.CharField(max_length=30, db_index=True)
    content = models.TextField()
    model = models.CharField(max_length=150, null=True)
    prompt_tokens = models.IntegerField(null=True)
    completion_tokens = models.IntegerField(null=True)
    context_reference = models.JSONField(null=True)
    response_metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_messages'
        indexes = [
            models.Index(fields=['ai_conversation', 'created_at'], name='idx_am_ac_b64dab34'),
        ]


class AiRecommendation(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    ai_conversation = models.ForeignKey('AiConversation', models.DO_NOTHING, null=True, db_index=True)
    business_issue = models.ForeignKey('BusinessIssue', models.DO_NOTHING, null=True, db_index=True)
    recommendation_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField()
    rationale = models.TextField(null=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    priority = models.CharField(max_length=30, default='MEDIUM')
    status = models.CharField(max_length=30, default='SUGGESTED')
    suggested_action_type = models.CharField(max_length=100, null=True)
    generated_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_recommendations'
        indexes = [
            models.Index(fields=['business', 'status'], name='idx_ar_bs_2e2d551c'),
            models.Index(fields=['business', 'priority'], name='idx_ar_bp_0669d69c'),
            models.Index(fields=['business', 'generated_at'], name='idx_ar_bg_bed21f61'),
        ]


class AiRecommendationEvidence(models.Model):
    id = models.BigAutoField(primary_key=True)
    ai_recommendation = models.ForeignKey('AiRecommendation', models.DO_NOTHING, db_index=True)
    business_fact = models.ForeignKey('BusinessFact', models.DO_NOTHING, null=True, db_index=True)
    business_issue = models.ForeignKey('BusinessIssue', models.DO_NOTHING, null=True, db_index=True)
    metric_snapshot = models.ForeignKey('MetricSnapshot', models.DO_NOTHING, null=True, db_index=True)
    business_relationship = models.ForeignKey('BusinessRelationship', models.DO_NOTHING, null=True, db_index=True)
    graph_node = models.ForeignKey('GraphNode', models.DO_NOTHING, null=True, db_index=True)
    graph_edge = models.ForeignKey('GraphEdge', models.DO_NOTHING, null=True, db_index=True)
    knowledge_chunk = models.ForeignKey('KnowledgeChunk', models.DO_NOTHING, null=True, db_index=True)
    evidence_type = models.CharField(max_length=50)
    description = models.TextField(null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    metadata = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_recommendation_evidence'


class AiAction(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, db_index=True)
    ai_recommendation = models.ForeignKey('AiRecommendation', models.DO_NOTHING, db_index=True)
    action_type = models.CharField(max_length=100)
    status = models.CharField(max_length=30, db_index=True, default='SUGGESTED')
    target_entity_type = models.CharField(max_length=50, null=True)
    target_entity_id = models.BigIntegerField(null=True)
    action_payload = models.JSONField(null=True)
    approval_note = models.TextField(null=True)
    approved_at = models.DateTimeField(null=True)
    executed_at = models.DateTimeField(null=True)
    execution_result = models.JSONField(null=True)
    is_simulated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_actions'
        indexes = [
            models.Index(fields=['business', 'action_type'], name='idx_aa_ba_a15531c5'),
        ]


class MockScenario(models.Model):
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey('Business', models.DO_NOTHING, null=True, db_index=True)
    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    scenario_type = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=30, db_index=True, default='ACTIVE')
    seed = models.BigIntegerField()
    start_at = models.DateTimeField(null=True)
    end_at = models.DateTimeField(null=True)
    configuration = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mock_scenarios'


class MockScenarioEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    mock_scenario = models.ForeignKey('MockScenario', models.DO_NOTHING, db_index=True)
    sequence_no = models.IntegerField()
    source_type = models.CharField(max_length=50)
    event_type = models.CharField(max_length=100)
    external_entity_type = models.CharField(max_length=50, null=True)
    external_entity_id = models.CharField(max_length=255, null=True)
    event_at = models.DateTimeField()
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mock_scenario_events'
        indexes = [
            models.Index(fields=['mock_scenario', 'event_at'], name='idx_mse_me_31cb993d'),
            models.Index(fields=['source_type', 'event_type'], name='idx_mse_se_111cdfe7'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['mock_scenario', 'sequence_no'], name='uniq_mse_ms_440571ac'),
        ]


class MockExpectedResult(models.Model):
    id = models.BigAutoField(primary_key=True)
    mock_scenario = models.ForeignKey('MockScenario', models.DO_NOTHING, db_index=True)
    result_type = models.CharField(max_length=100, db_index=True)
    result_key = models.CharField(max_length=150, null=True)
    entity_type = models.CharField(max_length=50, null=True)
    entity_reference = models.CharField(max_length=255, null=True)
    expected_value = models.JSONField()
    comparison_type = models.CharField(max_length=30, default='EXACT')
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mock_expected_results'
        indexes = [
            models.Index(fields=['mock_scenario', 'result_key'], name='idx_mer_mr_89ccd74d'),
        ]
