CREATE TABLE "currencies" (
  "code" varchar(3) PRIMARY KEY,
  "name" varchar(100) NOT NULL,
  "minor_unit" int NOT NULL DEFAULT 2
);

CREATE TABLE "businesses" (
  "id" uuid PRIMARY KEY,
  "name" varchar(255) NOT NULL,
  "legal_name" varchar(255),
  "currency_code" varchar(3) NOT NULL,
  "timezone" varchar(100) NOT NULL,
  "country_code" varchar(2),
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "source_systems" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "provider" varchar(100) NOT NULL,
  "name" varchar(255) NOT NULL,
  "source_type" varchar(50) NOT NULL,
  "external_account_id" varchar(255),
  "status" varchar(30) NOT NULL,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "integration_providers" (
  "id" uuid PRIMARY KEY,
  "key" varchar(100) UNIQUE NOT NULL,
  "name" varchar(255) NOT NULL,
  "provider_type" varchar(50) NOT NULL,
  "capabilities" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "integrations" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "provider_id" uuid NOT NULL,
  "source_system_id" uuid,
  "status" varchar(30) NOT NULL,
  "display_name" varchar(255),
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "integration_credentials" (
  "id" uuid PRIMARY KEY,
  "integration_id" uuid NOT NULL,
  "credential_type" varchar(50) NOT NULL,
  "secret_reference" varchar(500) NOT NULL,
  "expires_at" timestamptz,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "integration_permissions" (
  "id" uuid PRIMARY KEY,
  "integration_id" uuid NOT NULL,
  "permission" varchar(255) NOT NULL,
  "granted" boolean NOT NULL DEFAULT false,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "webhook_registrations" (
  "id" uuid PRIMARY KEY,
  "integration_id" uuid NOT NULL,
  "event_type" varchar(255) NOT NULL,
  "external_registration_id" varchar(255),
  "status" varchar(30) NOT NULL,
  "registered_at" timestamptz,
  "last_verified_at" timestamptz
);

CREATE TABLE "sync_states" (
  "id" uuid PRIMARY KEY,
  "integration_id" uuid NOT NULL,
  "entity_type" varchar(100) NOT NULL,
  "status" varchar(30) NOT NULL,
  "cursor" varchar(1000),
  "last_successful_sync_at" timestamptz,
  "last_started_at" timestamptz,
  "last_finished_at" timestamptz,
  "records_synced" bigint DEFAULT 0,
  "error_message" text
);

CREATE TABLE "integration_requests" (
  "id" uuid PRIMARY KEY,
  "integration_id" uuid NOT NULL,
  "request_type" varchar(50) NOT NULL,
  "endpoint" varchar(1000),
  "method" varchar(20),
  "status_code" int,
  "status" varchar(30) NOT NULL,
  "attempt" int NOT NULL DEFAULT 1,
  "rate_limit_remaining" int,
  "error_message" text,
  "requested_at" timestamptz NOT NULL,
  "completed_at" timestamptz
);

CREATE TABLE "raw_payloads" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "source_system_id" uuid,
  "integration_id" uuid,
  "external_event_id" varchar(500),
  "entity_type" varchar(100),
  "payload" jsonb NOT NULL,
  "received_at" timestamptz NOT NULL,
  "processed_at" timestamptz,
  "processing_status" varchar(30) NOT NULL,
  "processing_error" text
);

CREATE TABLE "product_categories" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "parent_id" uuid,
  "name" varchar(255) NOT NULL,
  "slug" varchar(255),
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "products" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "category_id" uuid,
  "name" varchar(500) NOT NULL,
  "sku" varchar(255),
  "description" text,
  "product_type" varchar(50),
  "status" varchar(30) NOT NULL,
  "base_price" numeric(19,4),
  "currency_code" varchar(3),
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "product_variants" (
  "id" uuid PRIMARY KEY,
  "product_id" uuid NOT NULL,
  "sku" varchar(255),
  "name" varchar(255),
  "attributes" jsonb,
  "price" numeric(19,4),
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "product_external_references" (
  "id" uuid PRIMARY KEY,
  "product_id" uuid NOT NULL,
  "variant_id" uuid,
  "source_system_id" uuid NOT NULL,
  "external_product_id" varchar(500) NOT NULL,
  "external_variant_id" varchar(500),
  "external_sku" varchar(255),
  "raw_name" varchar(500),
  "normalized_name" varchar(500),
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "product_merge_candidates" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "product_id_a" uuid NOT NULL,
  "product_id_b" uuid NOT NULL,
  "confidence" numeric(5,4),
  "reason" varchar(1000),
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL,
  "resolved_at" timestamptz
);

CREATE TABLE "customers" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "full_name" varchar(500),
  "first_name" varchar(255),
  "last_name" varchar(255),
  "email" varchar(500),
  "phone" varchar(100),
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "customer_contacts" (
  "id" uuid PRIMARY KEY,
  "customer_id" uuid NOT NULL,
  "contact_type" varchar(30) NOT NULL,
  "contact_value" varchar(500) NOT NULL,
  "normalized_value" varchar(500),
  "is_primary" boolean NOT NULL DEFAULT false,
  "verified_at" timestamptz,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "customer_tags" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "name" varchar(100) NOT NULL
);

CREATE TABLE "customer_tag_assignments" (
  "customer_id" uuid NOT NULL,
  "tag_id" uuid NOT NULL,
  "assigned_at" timestamptz NOT NULL,
  PRIMARY KEY ("customer_id", "tag_id")
);

CREATE TABLE "customer_merge_candidates" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "customer_id_a" uuid NOT NULL,
  "customer_id_b" uuid NOT NULL,
  "confidence" numeric(5,4),
  "reason" varchar(1000),
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL,
  "resolved_at" timestamptz
);

CREATE TABLE "orders" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "customer_id" uuid,
  "source_system_id" uuid,
  "external_order_id" varchar(500),
  "order_number" varchar(255),
  "status" varchar(50) NOT NULL,
  "currency_code" varchar(3) NOT NULL,
  "subtotal" numeric(19,4) NOT NULL DEFAULT 0,
  "discount_total" numeric(19,4) NOT NULL DEFAULT 0,
  "shipping_total" numeric(19,4) NOT NULL DEFAULT 0,
  "tax_total" numeric(19,4) NOT NULL DEFAULT 0,
  "total" numeric(19,4) NOT NULL DEFAULT 0,
  "placed_at" timestamptz,
  "confirmed_at" timestamptz,
  "cancelled_at" timestamptz,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "order_items" (
  "id" uuid PRIMARY KEY,
  "order_id" uuid NOT NULL,
  "product_id" uuid,
  "variant_id" uuid,
  "external_product_id" varchar(500),
  "product_name_snapshot" varchar(500) NOT NULL,
  "sku_snapshot" varchar(255),
  "quantity" numeric(19,4) NOT NULL,
  "unit_price" numeric(19,4) NOT NULL,
  "discount" numeric(19,4) NOT NULL DEFAULT 0,
  "tax" numeric(19,4) NOT NULL DEFAULT 0,
  "line_total" numeric(19,4) NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "order_status_history" (
  "id" uuid PRIMARY KEY,
  "order_id" uuid NOT NULL,
  "status" varchar(50) NOT NULL,
  "source_status" varchar(100),
  "changed_at" timestamptz NOT NULL,
  "source_event_id" varchar(500),
  "metadata" jsonb
);

CREATE TABLE "order_external_references" (
  "id" uuid PRIMARY KEY,
  "order_id" uuid NOT NULL,
  "source_system_id" uuid NOT NULL,
  "external_order_id" varchar(500) NOT NULL,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "payments" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "order_id" uuid,
  "customer_id" uuid,
  "source_system_id" uuid,
  "external_payment_id" varchar(500),
  "transaction_type" varchar(50) NOT NULL,
  "status" varchar(50) NOT NULL,
  "payment_method" varchar(50),
  "currency_code" varchar(3) NOT NULL,
  "amount" numeric(19,4) NOT NULL,
  "paid_at" timestamptz,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "refunds" (
  "id" uuid PRIMARY KEY,
  "payment_id" uuid NOT NULL,
  "order_id" uuid,
  "amount" numeric(19,4) NOT NULL,
  "currency_code" varchar(3) NOT NULL,
  "reason" varchar(500),
  "status" varchar(50) NOT NULL,
  "refunded_at" timestamptz,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "communication_channels" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "source_system_id" uuid,
  "channel_type" varchar(50) NOT NULL,
  "external_channel_id" varchar(500),
  "status" varchar(30) NOT NULL,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "messages" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "channel_id" uuid NOT NULL,
  "source_system_id" uuid,
  "external_message_id" varchar(500),
  "direction" varchar(20) NOT NULL,
  "sender_external_id" varchar(500),
  "receiver_external_id" varchar(500),
  "content_type" varchar(50),
  "content" text,
  "sent_at" timestamptz,
  "received_at" timestamptz,
  "delivery_status" varchar(50),
  "read_status" varchar(50),
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "message_attachments" (
  "id" uuid PRIMARY KEY,
  "message_id" uuid NOT NULL,
  "attachment_type" varchar(50),
  "storage_reference" varchar(1000),
  "mime_type" varchar(255),
  "file_name" varchar(500),
  "file_size" bigint,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "conversations" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "customer_id" uuid,
  "channel_id" uuid,
  "status" varchar(50) NOT NULL,
  "priority" varchar(30),
  "subject" varchar(500),
  "started_at" timestamptz,
  "closed_at" timestamptz,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "conversation_messages" (
  "conversation_id" uuid NOT NULL,
  "message_id" uuid NOT NULL,
  PRIMARY KEY ("conversation_id", "message_id")
);

CREATE TABLE "support_agents" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "name" varchar(255) NOT NULL,
  "email" varchar(500),
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "support_queues" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "name" varchar(255) NOT NULL,
  "status" varchar(30) NOT NULL
);

CREATE TABLE "conversation_assignments" (
  "id" uuid PRIMARY KEY,
  "conversation_id" uuid NOT NULL,
  "agent_id" uuid,
  "queue_id" uuid,
  "assigned_at" timestamptz NOT NULL,
  "unassigned_at" timestamptz
);

CREATE TABLE "conversation_events" (
  "id" uuid PRIMARY KEY,
  "conversation_id" uuid NOT NULL,
  "event_type" varchar(50) NOT NULL,
  "actor_type" varchar(30),
  "actor_id" uuid,
  "from_status" varchar(50),
  "to_status" varchar(50),
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "support_internal_notes" (
  "id" uuid PRIMARY KEY,
  "conversation_id" uuid NOT NULL,
  "agent_id" uuid,
  "note" text NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ad_accounts" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "source_system_id" uuid NOT NULL,
  "external_account_id" varchar(500) NOT NULL,
  "name" varchar(255),
  "currency_code" varchar(3),
  "status" varchar(30),
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "campaigns" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "ad_account_id" uuid,
  "source_system_id" uuid,
  "external_campaign_id" varchar(500),
  "name" varchar(500) NOT NULL,
  "status" varchar(50),
  "objective" varchar(100),
  "started_at" timestamptz,
  "ended_at" timestamptz,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ad_sets" (
  "id" uuid PRIMARY KEY,
  "campaign_id" uuid NOT NULL,
  "external_ad_set_id" varchar(500),
  "name" varchar(500),
  "status" varchar(50),
  "budget" numeric(19,4),
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ads" (
  "id" uuid PRIMARY KEY,
  "ad_set_id" uuid NOT NULL,
  "external_ad_id" varchar(500),
  "name" varchar(500),
  "status" varchar(50),
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "creatives" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "source_system_id" uuid,
  "external_creative_id" varchar(500),
  "name" varchar(500),
  "creative_type" varchar(50),
  "content" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "campaign_metrics" (
  "id" uuid PRIMARY KEY,
  "campaign_id" uuid NOT NULL,
  "metric_date" date NOT NULL,
  "impressions" bigint DEFAULT 0,
  "clicks" bigint DEFAULT 0,
  "spend" numeric(19,4) DEFAULT 0,
  "conversions" numeric(19,4) DEFAULT 0,
  "conversion_value" numeric(19,4) DEFAULT 0,
  "ctr" numeric(12,6),
  "cpc" numeric(19,6),
  "cpa" numeric(19,6),
  "roas" numeric(19,6)
);

CREATE TABLE "website_visitors" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "customer_id" uuid,
  "anonymous_visitor_id" varchar(500),
  "first_seen_at" timestamptz,
  "last_seen_at" timestamptz,
  "device_type" varchar(50),
  "browser" varchar(100),
  "metadata" jsonb
);

CREATE TABLE "website_sessions" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "visitor_id" uuid NOT NULL,
  "customer_id" uuid,
  "source_system_id" uuid,
  "external_session_id" varchar(500),
  "started_at" timestamptz NOT NULL,
  "ended_at" timestamptz,
  "landing_page" varchar(1000),
  "exit_page" varchar(1000),
  "traffic_source" varchar(255),
  "medium" varchar(255),
  "campaign_id" uuid,
  "device_type" varchar(50),
  "browser" varchar(100)
);

CREATE TABLE "website_page_views" (
  "id" uuid PRIMARY KEY,
  "session_id" uuid NOT NULL,
  "url" varchar(2000) NOT NULL,
  "title" varchar(1000),
  "viewed_at" timestamptz NOT NULL,
  "duration_ms" bigint
);

CREATE TABLE "website_events" (
  "id" uuid PRIMARY KEY,
  "session_id" uuid NOT NULL,
  "event_type" varchar(100) NOT NULL,
  "product_id" uuid,
  "order_id" uuid,
  "event_name" varchar(255),
  "event_data" jsonb,
  "occurred_at" timestamptz NOT NULL
);

CREATE TABLE "website_errors" (
  "id" uuid PRIMARY KEY,
  "session_id" uuid,
  "error_type" varchar(100),
  "message" text,
  "url" varchar(2000),
  "occurred_at" timestamptz NOT NULL
);

CREATE TABLE "website_behavior_signals" (
  "id" uuid PRIMARY KEY,
  "session_id" uuid NOT NULL,
  "signal_type" varchar(50) NOT NULL,
  "page_url" varchar(2000),
  "event_data" jsonb,
  "occurred_at" timestamptz NOT NULL
);

CREATE TABLE "courier_providers" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "provider_key" varchar(100) NOT NULL,
  "name" varchar(255) NOT NULL,
  "status" varchar(30) NOT NULL,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "shipments" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "order_id" uuid NOT NULL,
  "courier_provider_id" uuid NOT NULL,
  "external_shipment_id" varchar(500),
  "tracking_number" varchar(500),
  "status" varchar(50) NOT NULL,
  "cod_amount" numeric(19,4),
  "courier_charge" numeric(19,4),
  "shipping_address" jsonb,
  "recipient_name" varchar(500),
  "recipient_phone" varchar(100),
  "created_at" timestamptz NOT NULL,
  "shipped_at" timestamptz,
  "delivered_at" timestamptz,
  "returned_at" timestamptz
);

CREATE TABLE "shipment_events" (
  "id" uuid PRIMARY KEY,
  "shipment_id" uuid NOT NULL,
  "event_type" varchar(50) NOT NULL,
  "status" varchar(50),
  "description" text,
  "occurred_at" timestamptz NOT NULL,
  "raw_payload_id" uuid
);

CREATE TABLE "calls" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "source_system_id" uuid,
  "external_call_id" varchar(500),
  "customer_id" uuid,
  "conversation_id" uuid,
  "order_id" uuid,
  "direction" varchar(20) NOT NULL,
  "caller_number" varchar(100),
  "receiver_number" varchar(100),
  "status" varchar(50),
  "started_at" timestamptz,
  "ended_at" timestamptz,
  "duration_seconds" int,
  "recording_reference" varchar(1000),
  "transcript" text,
  "summary" text,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "call_events" (
  "id" uuid PRIMARY KEY,
  "call_id" uuid NOT NULL,
  "event_type" varchar(50) NOT NULL,
  "event_data" jsonb,
  "occurred_at" timestamptz NOT NULL
);

CREATE TABLE "business_relationships" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "relationship_type" varchar(100) NOT NULL,
  "from_entity_type" varchar(50) NOT NULL,
  "from_entity_id" uuid NOT NULL,
  "to_entity_type" varchar(50) NOT NULL,
  "to_entity_id" uuid NOT NULL,
  "source_type" varchar(30) NOT NULL,
  "confidence" numeric(5,4),
  "is_verified" boolean NOT NULL DEFAULT false,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "attribution_results" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "order_id" uuid,
  "customer_id" uuid,
  "campaign_id" uuid,
  "session_id" uuid,
  "attribution_model" varchar(50) NOT NULL,
  "attribution_weight" numeric(12,8),
  "attributed_revenue" numeric(19,4),
  "evidence" jsonb,
  "calculated_at" timestamptz NOT NULL
);

CREATE TABLE "business_metrics" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "metric_name" varchar(255) NOT NULL,
  "metric_date" date NOT NULL,
  "dimension_type" varchar(100),
  "dimension_id" uuid,
  "value_numeric" numeric(30,10),
  "value_text" text,
  "calculation_version" varchar(100),
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "business_flaw_candidates" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "flaw_type" varchar(100) NOT NULL,
  "title" varchar(500) NOT NULL,
  "description" text,
  "severity" varchar(30),
  "detected_at" timestamptz NOT NULL,
  "status" varchar(30) NOT NULL,
  "confidence" numeric(5,4),
  "evidence" jsonb
);

CREATE TABLE "verified_business_facts" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "fact_type" varchar(100) NOT NULL,
  "subject_entity_type" varchar(50),
  "subject_entity_id" uuid,
  "fact_value" jsonb NOT NULL,
  "confidence" numeric(5,4),
  "calculation_version" varchar(100),
  "valid_from" timestamptz,
  "valid_until" timestamptz,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "evidence_records" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "fact_id" uuid,
  "relationship_id" uuid,
  "source_entity_type" varchar(50),
  "source_entity_id" uuid,
  "raw_payload_id" uuid,
  "evidence_type" varchar(50),
  "evidence_data" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "graph_nodes" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "entity_type" varchar(50) NOT NULL,
  "entity_id" uuid NOT NULL,
  "node_type" varchar(100) NOT NULL,
  "label" varchar(500),
  "properties" jsonb,
  "snapshot_version" varchar(100),
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "graph_edges" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "from_node_id" uuid NOT NULL,
  "to_node_id" uuid NOT NULL,
  "relationship_type" varchar(100) NOT NULL,
  "weight" numeric(19,6),
  "properties" jsonb,
  "evidence_id" uuid,
  "snapshot_version" varchar(100),
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "graph_snapshots" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "version" varchar(100) NOT NULL,
  "generated_at" timestamptz NOT NULL,
  "node_count" bigint,
  "edge_count" bigint,
  "status" varchar(30) NOT NULL
);

CREATE TABLE "memory_documents" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "document_type" varchar(100) NOT NULL,
  "title" varchar(500),
  "source_reference" varchar(1000),
  "version" int NOT NULL DEFAULT 1,
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "memory_chunks" (
  "id" uuid PRIMARY KEY,
  "document_id" uuid NOT NULL,
  "chunk_index" int NOT NULL,
  "content" text NOT NULL,
  "metadata" jsonb,
  "embedding" vector,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "business_memory" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "memory_type" varchar(100) NOT NULL,
  "subject_entity_type" varchar(50),
  "subject_entity_id" uuid,
  "content" text NOT NULL,
  "metadata" jsonb,
  "source_reference" varchar(1000),
  "version" int NOT NULL DEFAULT 1,
  "is_active" boolean NOT NULL DEFAULT true,
  "created_at" timestamptz NOT NULL,
  "updated_at" timestamptz NOT NULL
);

CREATE TABLE "approved_suggestions" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "suggestion_type" varchar(100),
  "title" varchar(500),
  "suggestion" text NOT NULL,
  "approved_by" uuid,
  "approved_at" timestamptz,
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ai_providers" (
  "id" uuid PRIMARY KEY,
  "name" varchar(255) NOT NULL,
  "provider_key" varchar(100) UNIQUE NOT NULL,
  "status" varchar(30) NOT NULL,
  "configuration" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ai_models" (
  "id" uuid PRIMARY KEY,
  "provider_id" uuid NOT NULL,
  "model_name" varchar(255) NOT NULL,
  "model_type" varchar(50),
  "configuration" jsonb,
  "enabled" boolean NOT NULL DEFAULT true,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ai_prompts" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid,
  "name" varchar(255) NOT NULL,
  "version" int NOT NULL,
  "template" text NOT NULL,
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ai_runs" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "model_id" uuid NOT NULL,
  "prompt_id" uuid,
  "task_type" varchar(100) NOT NULL,
  "input_context" jsonb,
  "output" jsonb,
  "confidence" numeric(5,4),
  "status" varchar(30) NOT NULL,
  "started_at" timestamptz NOT NULL,
  "completed_at" timestamptz
);

CREATE TABLE "ai_recommendations" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "run_id" uuid,
  "recommendation_type" varchar(100) NOT NULL,
  "title" varchar(500) NOT NULL,
  "recommendation" text NOT NULL,
  "confidence" numeric(5,4),
  "evidence_summary" jsonb,
  "suggested_action" jsonb,
  "status" varchar(30) NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ai_actions" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "recommendation_id" uuid,
  "integration_id" uuid,
  "action_type" varchar(100) NOT NULL,
  "action_payload" jsonb,
  "approval_status" varchar(30) NOT NULL,
  "approved_by" uuid,
  "approved_at" timestamptz,
  "execution_status" varchar(30),
  "executed_at" timestamptz,
  "execution_result" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "ai_audit_logs" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid NOT NULL,
  "run_id" uuid,
  "action_id" uuid,
  "event_type" varchar(100) NOT NULL,
  "input_hash" varchar(255),
  "output_hash" varchar(255),
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "mock_scenarios" (
  "id" uuid PRIMARY KEY,
  "business_id" uuid,
  "name" varchar(255) NOT NULL,
  "description" text,
  "seed" bigint NOT NULL,
  "scenario_config" jsonb,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "mock_platforms" (
  "id" uuid PRIMARY KEY,
  "scenario_id" uuid NOT NULL,
  "platform_key" varchar(100) NOT NULL,
  "platform_type" varchar(100) NOT NULL,
  "configuration" jsonb
);

CREATE TABLE "mock_entities" (
  "id" uuid PRIMARY KEY,
  "platform_id" uuid NOT NULL,
  "entity_type" varchar(100) NOT NULL,
  "external_id" varchar(500) NOT NULL,
  "payload" jsonb NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE TABLE "mock_expected_results" (
  "id" uuid PRIMARY KEY,
  "scenario_id" uuid NOT NULL,
  "result_type" varchar(100) NOT NULL,
  "expected_value" jsonb NOT NULL,
  "created_at" timestamptz NOT NULL
);

CREATE INDEX ON "businesses" ("name");

CREATE INDEX ON "businesses" ("status");

CREATE INDEX ON "source_systems" ("business_id");

CREATE INDEX ON "source_systems" ("provider");

CREATE UNIQUE INDEX ON "source_systems" ("business_id", "provider", "external_account_id");

CREATE INDEX ON "integrations" ("business_id");

CREATE INDEX ON "integrations" ("provider_id");

CREATE UNIQUE INDEX ON "integrations" ("business_id", "provider_id");

CREATE INDEX ON "integration_permissions" ("integration_id");

CREATE UNIQUE INDEX ON "integration_permissions" ("integration_id", "permission");

CREATE INDEX ON "webhook_registrations" ("integration_id");

CREATE INDEX ON "webhook_registrations" ("event_type");

CREATE INDEX ON "sync_states" ("integration_id");

CREATE UNIQUE INDEX ON "sync_states" ("integration_id", "entity_type");

CREATE INDEX ON "integration_requests" ("integration_id");

CREATE INDEX ON "integration_requests" ("status");

CREATE INDEX ON "integration_requests" ("requested_at");

CREATE INDEX ON "raw_payloads" ("business_id");

CREATE INDEX ON "raw_payloads" ("source_system_id");

CREATE INDEX ON "raw_payloads" ("external_event_id");

CREATE INDEX ON "raw_payloads" ("entity_type");

CREATE INDEX ON "raw_payloads" ("received_at");

CREATE INDEX ON "product_categories" ("business_id");

CREATE INDEX ON "product_categories" ("parent_id");

CREATE UNIQUE INDEX ON "product_categories" ("business_id", "slug");

CREATE INDEX ON "products" ("business_id");

CREATE INDEX ON "products" ("sku");

CREATE INDEX ON "products" ("category_id");

CREATE INDEX ON "product_variants" ("product_id");

CREATE INDEX ON "product_variants" ("sku");

CREATE INDEX ON "product_external_references" ("source_system_id");

CREATE INDEX ON "product_external_references" ("external_product_id");

CREATE UNIQUE INDEX ON "product_external_references" ("source_system_id", "external_product_id", "external_variant_id");

CREATE INDEX ON "customers" ("business_id");

CREATE INDEX ON "customers" ("email");

CREATE INDEX ON "customers" ("phone");

CREATE INDEX ON "customer_contacts" ("customer_id");

CREATE INDEX ON "customer_contacts" ("contact_type");

CREATE INDEX ON "customer_contacts" ("normalized_value");

CREATE INDEX ON "customer_tags" ("business_id");

CREATE UNIQUE INDEX ON "customer_tags" ("business_id", "name");

CREATE INDEX ON "orders" ("business_id");

CREATE INDEX ON "orders" ("customer_id");

CREATE INDEX ON "orders" ("source_system_id");

CREATE INDEX ON "orders" ("external_order_id");

CREATE INDEX ON "orders" ("status");

CREATE INDEX ON "orders" ("placed_at");

CREATE UNIQUE INDEX ON "orders" ("source_system_id", "external_order_id");

CREATE INDEX ON "order_items" ("order_id");

CREATE INDEX ON "order_items" ("product_id");

CREATE INDEX ON "order_items" ("variant_id");

CREATE INDEX ON "order_status_history" ("order_id");

CREATE INDEX ON "order_status_history" ("changed_at");

CREATE UNIQUE INDEX ON "order_external_references" ("source_system_id", "external_order_id");

CREATE INDEX ON "payments" ("business_id");

CREATE INDEX ON "payments" ("order_id");

CREATE INDEX ON "payments" ("customer_id");

CREATE INDEX ON "payments" ("external_payment_id");

CREATE INDEX ON "payments" ("status");

CREATE INDEX ON "payments" ("paid_at");

CREATE INDEX ON "refunds" ("payment_id");

CREATE INDEX ON "refunds" ("order_id");

CREATE INDEX ON "communication_channels" ("business_id");

CREATE INDEX ON "communication_channels" ("source_system_id");

CREATE INDEX ON "communication_channels" ("channel_type");

CREATE INDEX ON "messages" ("business_id");

CREATE INDEX ON "messages" ("channel_id");

CREATE INDEX ON "messages" ("external_message_id");

CREATE INDEX ON "messages" ("sender_external_id");

CREATE INDEX ON "messages" ("sent_at");

CREATE INDEX ON "conversations" ("business_id");

CREATE INDEX ON "conversations" ("customer_id");

CREATE INDEX ON "conversations" ("channel_id");

CREATE INDEX ON "conversations" ("status");

CREATE INDEX ON "conversations" ("priority");

CREATE INDEX ON "support_agents" ("business_id");

CREATE INDEX ON "support_agents" ("status");

CREATE INDEX ON "support_queues" ("business_id");

CREATE UNIQUE INDEX ON "support_queues" ("business_id", "name");

CREATE INDEX ON "conversation_assignments" ("conversation_id");

CREATE INDEX ON "conversation_assignments" ("agent_id");

CREATE INDEX ON "conversation_assignments" ("queue_id");

CREATE INDEX ON "conversation_events" ("conversation_id");

CREATE INDEX ON "conversation_events" ("event_type");

CREATE INDEX ON "conversation_events" ("created_at");

CREATE INDEX ON "ad_accounts" ("business_id");

CREATE INDEX ON "ad_accounts" ("source_system_id");

CREATE UNIQUE INDEX ON "ad_accounts" ("source_system_id", "external_account_id");

CREATE INDEX ON "campaigns" ("business_id");

CREATE INDEX ON "campaigns" ("ad_account_id");

CREATE INDEX ON "campaigns" ("external_campaign_id");

CREATE INDEX ON "campaigns" ("status");

CREATE INDEX ON "ad_sets" ("campaign_id");

CREATE INDEX ON "ad_sets" ("external_ad_set_id");

CREATE INDEX ON "ads" ("ad_set_id");

CREATE INDEX ON "ads" ("external_ad_id");

CREATE INDEX ON "creatives" ("business_id");

CREATE INDEX ON "creatives" ("external_creative_id");

CREATE UNIQUE INDEX ON "campaign_metrics" ("campaign_id", "metric_date");

CREATE INDEX ON "campaign_metrics" ("metric_date");

CREATE INDEX ON "website_visitors" ("business_id");

CREATE INDEX ON "website_visitors" ("customer_id");

CREATE INDEX ON "website_visitors" ("anonymous_visitor_id");

CREATE INDEX ON "website_sessions" ("business_id");

CREATE INDEX ON "website_sessions" ("visitor_id");

CREATE INDEX ON "website_sessions" ("customer_id");

CREATE INDEX ON "website_sessions" ("campaign_id");

CREATE INDEX ON "website_sessions" ("started_at");

CREATE INDEX ON "website_sessions" ("external_session_id");

CREATE INDEX ON "website_page_views" ("session_id");

CREATE INDEX ON "website_page_views" ("viewed_at");

CREATE INDEX ON "website_events" ("session_id");

CREATE INDEX ON "website_events" ("event_type");

CREATE INDEX ON "website_events" ("product_id");

CREATE INDEX ON "website_events" ("order_id");

CREATE INDEX ON "website_events" ("occurred_at");

CREATE INDEX ON "website_errors" ("session_id");

CREATE INDEX ON "website_errors" ("occurred_at");

CREATE INDEX ON "website_behavior_signals" ("session_id");

CREATE INDEX ON "website_behavior_signals" ("signal_type");

CREATE INDEX ON "website_behavior_signals" ("occurred_at");

CREATE INDEX ON "courier_providers" ("business_id");

CREATE INDEX ON "courier_providers" ("provider_key");

CREATE UNIQUE INDEX ON "courier_providers" ("business_id", "provider_key");

CREATE INDEX ON "shipments" ("business_id");

CREATE INDEX ON "shipments" ("order_id");

CREATE INDEX ON "shipments" ("courier_provider_id");

CREATE INDEX ON "shipments" ("tracking_number");

CREATE INDEX ON "shipments" ("external_shipment_id");

CREATE INDEX ON "shipments" ("status");

CREATE INDEX ON "shipment_events" ("shipment_id");

CREATE INDEX ON "shipment_events" ("event_type");

CREATE INDEX ON "shipment_events" ("occurred_at");

CREATE INDEX ON "calls" ("business_id");

CREATE INDEX ON "calls" ("customer_id");

CREATE INDEX ON "calls" ("conversation_id");

CREATE INDEX ON "calls" ("order_id");

CREATE INDEX ON "calls" ("external_call_id");

CREATE INDEX ON "calls" ("started_at");

CREATE INDEX ON "call_events" ("call_id");

CREATE INDEX ON "call_events" ("occurred_at");

CREATE INDEX ON "business_relationships" ("business_id");

CREATE INDEX ON "business_relationships" ("relationship_type");

CREATE INDEX ON "business_relationships" ("from_entity_id");

CREATE INDEX ON "business_relationships" ("to_entity_id");

CREATE INDEX ON "business_relationships" ("is_verified");

CREATE UNIQUE INDEX ON "business_relationships" ("relationship_type", "from_entity_id", "to_entity_id");

CREATE INDEX ON "attribution_results" ("business_id");

CREATE INDEX ON "attribution_results" ("order_id");

CREATE INDEX ON "attribution_results" ("customer_id");

CREATE INDEX ON "attribution_results" ("campaign_id");

CREATE INDEX ON "attribution_results" ("session_id");

CREATE INDEX ON "attribution_results" ("attribution_model");

CREATE INDEX ON "business_metrics" ("business_id");

CREATE INDEX ON "business_metrics" ("metric_name");

CREATE INDEX ON "business_metrics" ("metric_date");

CREATE INDEX ON "business_metrics" ("dimension_id");

CREATE UNIQUE INDEX ON "business_metrics" ("business_id", "metric_name", "metric_date", "dimension_type", "dimension_id");

CREATE INDEX ON "business_flaw_candidates" ("business_id");

CREATE INDEX ON "business_flaw_candidates" ("flaw_type");

CREATE INDEX ON "business_flaw_candidates" ("severity");

CREATE INDEX ON "business_flaw_candidates" ("status");

CREATE INDEX ON "business_flaw_candidates" ("detected_at");

CREATE INDEX ON "verified_business_facts" ("business_id");

CREATE INDEX ON "verified_business_facts" ("fact_type");

CREATE INDEX ON "verified_business_facts" ("subject_entity_id");

CREATE INDEX ON "verified_business_facts" ("valid_from");

CREATE INDEX ON "evidence_records" ("business_id");

CREATE INDEX ON "evidence_records" ("fact_id");

CREATE INDEX ON "evidence_records" ("relationship_id");

CREATE INDEX ON "evidence_records" ("source_entity_id");

CREATE INDEX ON "graph_nodes" ("business_id");

CREATE INDEX ON "graph_nodes" ("entity_type");

CREATE INDEX ON "graph_nodes" ("entity_id");

CREATE INDEX ON "graph_nodes" ("node_type");

CREATE UNIQUE INDEX ON "graph_nodes" ("business_id", "entity_type", "entity_id", "snapshot_version");

CREATE INDEX ON "graph_edges" ("business_id");

CREATE INDEX ON "graph_edges" ("from_node_id");

CREATE INDEX ON "graph_edges" ("to_node_id");

CREATE INDEX ON "graph_edges" ("relationship_type");

CREATE INDEX ON "graph_edges" ("snapshot_version");

CREATE INDEX ON "graph_snapshots" ("business_id");

CREATE UNIQUE INDEX ON "graph_snapshots" ("business_id", "version");

CREATE INDEX ON "memory_documents" ("business_id");

CREATE INDEX ON "memory_documents" ("document_type");

CREATE INDEX ON "memory_documents" ("status");

CREATE INDEX ON "memory_chunks" ("document_id");

CREATE UNIQUE INDEX ON "memory_chunks" ("document_id", "chunk_index");

CREATE INDEX ON "business_memory" ("business_id");

CREATE INDEX ON "business_memory" ("memory_type");

CREATE INDEX ON "business_memory" ("subject_entity_id");

CREATE INDEX ON "business_memory" ("is_active");

CREATE INDEX ON "ai_prompts" ("business_id");

CREATE INDEX ON "ai_prompts" ("name");

CREATE UNIQUE INDEX ON "ai_prompts" ("business_id", "name", "version");

CREATE INDEX ON "ai_recommendations" ("business_id");

CREATE INDEX ON "ai_recommendations" ("recommendation_type");

CREATE INDEX ON "ai_recommendations" ("status");

CREATE INDEX ON "ai_recommendations" ("created_at");

CREATE INDEX ON "ai_audit_logs" ("business_id");

CREATE INDEX ON "ai_audit_logs" ("run_id");

CREATE INDEX ON "ai_audit_logs" ("action_id");

CREATE INDEX ON "ai_audit_logs" ("event_type");

CREATE INDEX ON "ai_audit_logs" ("created_at");

CREATE INDEX ON "mock_platforms" ("scenario_id");

CREATE UNIQUE INDEX ON "mock_platforms" ("scenario_id", "platform_key");

CREATE INDEX ON "mock_entities" ("platform_id");

CREATE INDEX ON "mock_entities" ("entity_type");

CREATE INDEX ON "mock_entities" ("external_id");

CREATE UNIQUE INDEX ON "mock_entities" ("platform_id", "entity_type", "external_id");

CREATE INDEX ON "mock_expected_results" ("scenario_id");

CREATE INDEX ON "mock_expected_results" ("result_type");

ALTER TABLE "businesses" ADD FOREIGN KEY ("currency_code") REFERENCES "currencies" ("code") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "source_systems" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "integrations" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "integrations" ADD FOREIGN KEY ("provider_id") REFERENCES "integration_providers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "integrations" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "integration_credentials" ADD FOREIGN KEY ("integration_id") REFERENCES "integrations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "integration_permissions" ADD FOREIGN KEY ("integration_id") REFERENCES "integrations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "webhook_registrations" ADD FOREIGN KEY ("integration_id") REFERENCES "integrations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "sync_states" ADD FOREIGN KEY ("integration_id") REFERENCES "integrations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "integration_requests" ADD FOREIGN KEY ("integration_id") REFERENCES "integrations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "raw_payloads" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "raw_payloads" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "raw_payloads" ADD FOREIGN KEY ("integration_id") REFERENCES "integrations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_categories" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_categories" ADD FOREIGN KEY ("parent_id") REFERENCES "product_categories" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "products" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "products" ADD FOREIGN KEY ("category_id") REFERENCES "product_categories" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_variants" ADD FOREIGN KEY ("product_id") REFERENCES "products" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_external_references" ADD FOREIGN KEY ("product_id") REFERENCES "products" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_external_references" ADD FOREIGN KEY ("variant_id") REFERENCES "product_variants" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_external_references" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_merge_candidates" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_merge_candidates" ADD FOREIGN KEY ("product_id_a") REFERENCES "products" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "product_merge_candidates" ADD FOREIGN KEY ("product_id_b") REFERENCES "products" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customers" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customer_contacts" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customer_tags" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customer_tag_assignments" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customer_tag_assignments" ADD FOREIGN KEY ("tag_id") REFERENCES "customer_tags" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customer_merge_candidates" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customer_merge_candidates" ADD FOREIGN KEY ("customer_id_a") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "customer_merge_candidates" ADD FOREIGN KEY ("customer_id_b") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "orders" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "orders" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "orders" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order_items" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order_items" ADD FOREIGN KEY ("product_id") REFERENCES "products" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order_items" ADD FOREIGN KEY ("variant_id") REFERENCES "product_variants" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order_status_history" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order_external_references" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order_external_references" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "payments" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "payments" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "payments" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "payments" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "refunds" ADD FOREIGN KEY ("payment_id") REFERENCES "payments" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "refunds" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "communication_channels" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "communication_channels" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "messages" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "messages" ADD FOREIGN KEY ("channel_id") REFERENCES "communication_channels" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "messages" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "message_attachments" ADD FOREIGN KEY ("message_id") REFERENCES "messages" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversations" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversations" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversations" ADD FOREIGN KEY ("channel_id") REFERENCES "communication_channels" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversation_messages" ADD FOREIGN KEY ("conversation_id") REFERENCES "conversations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversation_messages" ADD FOREIGN KEY ("message_id") REFERENCES "messages" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "support_agents" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "support_queues" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversation_assignments" ADD FOREIGN KEY ("conversation_id") REFERENCES "conversations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversation_assignments" ADD FOREIGN KEY ("agent_id") REFERENCES "support_agents" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversation_assignments" ADD FOREIGN KEY ("queue_id") REFERENCES "support_queues" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "conversation_events" ADD FOREIGN KEY ("conversation_id") REFERENCES "conversations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "support_internal_notes" ADD FOREIGN KEY ("conversation_id") REFERENCES "conversations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "support_internal_notes" ADD FOREIGN KEY ("agent_id") REFERENCES "support_agents" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ad_accounts" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ad_accounts" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaigns" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaigns" ADD FOREIGN KEY ("ad_account_id") REFERENCES "ad_accounts" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaigns" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ad_sets" ADD FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ads" ADD FOREIGN KEY ("ad_set_id") REFERENCES "ad_sets" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "creatives" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "creatives" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaign_metrics" ADD FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_visitors" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_visitors" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_sessions" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_sessions" ADD FOREIGN KEY ("visitor_id") REFERENCES "website_visitors" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_sessions" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_sessions" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_sessions" ADD FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_page_views" ADD FOREIGN KEY ("session_id") REFERENCES "website_sessions" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_events" ADD FOREIGN KEY ("session_id") REFERENCES "website_sessions" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_events" ADD FOREIGN KEY ("product_id") REFERENCES "products" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_events" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_errors" ADD FOREIGN KEY ("session_id") REFERENCES "website_sessions" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "website_behavior_signals" ADD FOREIGN KEY ("session_id") REFERENCES "website_sessions" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "courier_providers" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "shipments" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "shipments" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "shipments" ADD FOREIGN KEY ("courier_provider_id") REFERENCES "courier_providers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "shipment_events" ADD FOREIGN KEY ("shipment_id") REFERENCES "shipments" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "shipment_events" ADD FOREIGN KEY ("raw_payload_id") REFERENCES "raw_payloads" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "calls" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "calls" ADD FOREIGN KEY ("source_system_id") REFERENCES "source_systems" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "calls" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "calls" ADD FOREIGN KEY ("conversation_id") REFERENCES "conversations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "calls" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "call_events" ADD FOREIGN KEY ("call_id") REFERENCES "calls" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "business_relationships" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "attribution_results" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "attribution_results" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "attribution_results" ADD FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "attribution_results" ADD FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "attribution_results" ADD FOREIGN KEY ("session_id") REFERENCES "website_sessions" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "business_metrics" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "business_flaw_candidates" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "verified_business_facts" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "evidence_records" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "evidence_records" ADD FOREIGN KEY ("fact_id") REFERENCES "verified_business_facts" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "evidence_records" ADD FOREIGN KEY ("relationship_id") REFERENCES "business_relationships" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "evidence_records" ADD FOREIGN KEY ("raw_payload_id") REFERENCES "raw_payloads" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "graph_nodes" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "graph_edges" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "graph_edges" ADD FOREIGN KEY ("from_node_id") REFERENCES "graph_nodes" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "graph_edges" ADD FOREIGN KEY ("to_node_id") REFERENCES "graph_nodes" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "graph_edges" ADD FOREIGN KEY ("evidence_id") REFERENCES "evidence_records" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "graph_snapshots" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "memory_documents" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "memory_chunks" ADD FOREIGN KEY ("document_id") REFERENCES "memory_documents" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "business_memory" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "approved_suggestions" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_models" ADD FOREIGN KEY ("provider_id") REFERENCES "ai_providers" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_prompts" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_runs" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_runs" ADD FOREIGN KEY ("model_id") REFERENCES "ai_models" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_runs" ADD FOREIGN KEY ("prompt_id") REFERENCES "ai_prompts" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_recommendations" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_recommendations" ADD FOREIGN KEY ("run_id") REFERENCES "ai_runs" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_actions" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_actions" ADD FOREIGN KEY ("recommendation_id") REFERENCES "ai_recommendations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_actions" ADD FOREIGN KEY ("integration_id") REFERENCES "integrations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_audit_logs" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_audit_logs" ADD FOREIGN KEY ("run_id") REFERENCES "ai_runs" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_audit_logs" ADD FOREIGN KEY ("action_id") REFERENCES "ai_actions" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "mock_scenarios" ADD FOREIGN KEY ("business_id") REFERENCES "businesses" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "mock_platforms" ADD FOREIGN KEY ("scenario_id") REFERENCES "mock_scenarios" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "mock_entities" ADD FOREIGN KEY ("platform_id") REFERENCES "mock_platforms" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "mock_expected_results" ADD FOREIGN KEY ("scenario_id") REFERENCES "mock_scenarios" ("id") DEFERRABLE INITIALLY IMMEDIATE;
