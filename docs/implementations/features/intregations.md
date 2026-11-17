# Integrations

## Description

The **Integrations** domain is the external connectivity layer of Business Brain. It connects the system with commerce platforms, communication channels, advertising platforms, analytics tools, courier services, calling systems, and other external providers.

Its primary responsibility is to manage connections, receive or retrieve provider data, preserve raw source information, and deliver that data to the appropriate Business Data domain for normalization. Integrations should not become the source of canonical business logic; they act as the controlled boundary between external systems and Business Brain.

---

## Features

### 1. Commerce Integrations

Connects Business Brain with external e-commerce platforms and custom commerce systems so products, customers, orders, payments, and related commerce data can enter the appropriate canonical domains.

**Features:**

* **WooCommerce Integration**
  Connects WooCommerce stores and receives or retrieves product, customer, order, payment, and relevant commerce events.

* **Shopify Integration**
  Provides the integration boundary for Shopify stores and transforms Shopify-specific payloads into inputs suitable for Business Brain domain processing.

* **Custom Website Integration**
  Allows businesses with custom-built commerce systems to send business data through standardized APIs or webhooks.

* **Commerce Data Retrieval**
  Retrieves required commerce records through provider APIs when webhook delivery alone is insufficient.

* **Commerce Webhook Handling**
  Receives provider events such as product updates, customer creation, order creation, order status changes, and other supported commerce events.

* **Raw Payload Preservation**
  Preserves original provider payloads and metadata when required for traceability, debugging, reprocessing, and mapping verification.

* **Domain Routing**
  Routes received commerce data to the appropriate Product, Customer, Order, or Payment processing pipeline instead of implementing canonical business logic inside the connector.

---

### 2. Communication Integrations

Connects external messaging platforms with the Communication domain, allowing Business Brain to receive and send messages through multiple communication channels.

**Features:**

* **Messenger Integration**
  Connects Facebook Messenger communication and handles supported incoming messages, outgoing messages, delivery events, and external user references.

* **WhatsApp Integration**
  Connects supported WhatsApp business messaging services for customer communication and message status tracking.

* **Instagram Integration**
  Receives and sends supported Instagram messaging interactions through the connected provider.

* **Telegram Integration**
  Provides connectivity for Telegram conversations, users, incoming messages, and outgoing responses.

* **Website Chat Integration**
  Connects a business's website chat interface directly with the canonical Communication and Customer Support layers.

* **Incoming Message Transport**
  Receives provider-specific messages and forwards them to Communication for canonical message normalization.

* **Outgoing Message Transport**
  Accepts canonical outgoing communication requests and delivers them using the required provider API.

* **Message Status Events**
  Processes provider callbacks for message delivery, failure, read status, and other supported lifecycle events.

* **Attachment Transport**
  Handles external images, audio, video, documents, and other supported message attachments.

* **Channel User References**
  Preserves provider-specific user identifiers such as Messenger PSIDs, Telegram user IDs, or communication-specific identifiers for later identity resolution.

---

### 3. Marketing Integrations

Connects Business Brain with advertising and marketing platforms to collect campaign structures, performance metrics, conversions, and related marketing information.

**Features:**

* **Meta Ads Integration**
  Connects Meta advertising accounts and retrieves campaign structures, performance metrics, spend, conversions, and related advertising data.

* **Google Ads Integration**
  Provides connectivity with Google advertising data required for campaign monitoring and cross-domain analysis.

* **TikTok Ads Integration**
  Retrieves supported TikTok advertising campaign and performance information.

* **Ad Account Connectivity**
  Associates external advertising accounts with their corresponding Business Brain integration connections.

* **Campaign Data Retrieval**
  Retrieves campaigns and associated platform data while preserving external campaign identifiers.

* **Campaign Metric Retrieval**
  Collects impressions, reach, clicks, spend, conversions, conversion value, and other supported provider metrics.

* **Conversion Event Integration**
  Receives or retrieves conversion information that can later be connected with customers, website sessions, and orders.

* **Tracking Event Connectivity**
  Supports provider-side event mechanisms such as pixels, conversion APIs, or equivalent event interfaces where applicable. Server-side outbound tracking event connectivity is implemented for Meta Conversions API (`meta_ads`) and TikTok Events API (`tiktok_ads`), mapping canonical `WebsiteEvent` rows to standard provider funnel stages (`PageView`, `ViewContent`, `AddToCart`, `InitiateCheckout`, `Purchase`/`CompletePayment`). Executes in prepared-only mode by default for mock connections; live sending uses bounded `urllib.request` with server-side credential references (`resolve_credentials`), strict PII suppression, idempotent `OperationAttempt` logging, and observability receipts via `record_observation(kind='provider_request')`. Driven via the `send_tracking_events` management command.

* **Marketing Data Routing**
  Passes collected marketing information to the Marketing domain for canonical normalization instead of treating provider schemas as the internal business model.

---

### 4. Analytics Integrations

Connects website analytics and behavior-tracking platforms with Business Brain to collect visitor, session, event, acquisition, conversion, and experience data.

**Features:**

* **GA4 Integration**
  Retrieves or receives supported Google Analytics 4 visitor, session, traffic, event, and conversion information. Supports outbound server-side event transmission via the GA4 Measurement Protocol (`/mp/collect` for live collection, `/debug/mp/collect` for validation in test mode) using credentials resolved server-side from `api_key` (`api_secret`).

* **Microsoft Clarity Integration**
  Provides access to supported website experience and behavioral signals collected through Microsoft Clarity.

* **Custom Analytics Integration**
  Allows custom websites or tracking systems to send standardized behavioral events directly into Business Brain.

* **Visitor Data Collection**
  Receives external visitor identifiers and associated metadata required to construct canonical website visitors.

* **Session Data Collection**
  Collects session boundaries, traffic sources, landing pages, device context, and related browsing information.

* **Website Event Collection**
  Processes events such as page views, product views, search, add-to-cart, checkout, purchase, and custom behavioral events.

* **UTM & Acquisition Data**
  Preserves campaign parameters and traffic-source information required for attribution and marketing analysis.

* **Experience Signal Collection**
  Supports available behavioral signals such as rage clicks, dead clicks, quick backs, errors, and performance indicators.

* **Behavior Data Routing**
  Routes analytics information into Website Behavior for canonical processing and later Identity, Intelligence, and Graph analysis.

---

### 5. Courier Integrations

Connects Business Brain with external delivery providers and supports the operational exchange required to create, track, update, cancel, and monitor shipments.

**Features:**

* **Steadfast Integration**
  Provides connectivity for supported Steadfast shipment creation, tracking, status updates, COD information, and delivery events.

* **RedX Integration**
  Connects supported RedX courier operations with the canonical Courier domain.

* **Pathao Integration**
  Provides an integration boundary for supported Pathao Courier shipment and tracking operations.

* **CarryBee Integration**
  Connects supported CarryBee delivery operations with Business Brain.

* **Shipment Submission**
  Converts an internal shipment request into the provider-specific request required to create a courier delivery.

* **Shipment Tracking**
  Retrieves or receives tracking information and routes updates into the canonical shipment lifecycle.

* **Delivery Status Updates**
  Processes provider events for pickup, transit, delivery attempts, successful delivery, failures, returns, and cancellation.

* **COD Information Retrieval**
  Collects provider COD-related information required for payment and delivery analysis.

* **Courier Charge Retrieval**
  Preserves provider delivery charges and related financial information.

* **Provider Error Handling**
  Captures courier API failures, rejected requests, invalid payloads, and provider-specific errors for operational monitoring.

---

### 6. Calling Integrations

Connects Business Brain with telephony and calling platforms so voice interactions can become part of the unified business context.

**Features:**

* **Dialyra Integration**
  Provides the primary calling integration for receiving call events, recordings, metadata, transcripts, and supported call operations from Dialyra.

* **Incoming Call Events**
  Receives information about customer-initiated calls and forwards it to the canonical Calling domain.

* **Outgoing Call Operations**
  Supports initiation or synchronization of business-initiated calls where the connected calling provider allows it.

* **Call Lifecycle Events**
  Processes events such as initiated, ringing, answered, transferred, completed, missed, busy, and failed.

* **Call Recording Retrieval**
  Retrieves or stores references to available call recordings for later support and AI processing.

* **Transcript Retrieval**
  Receives or retrieves call transcripts when transcription is supplied by the calling platform or related service.

* **Caller References**
  Preserves caller numbers and provider-specific caller identifiers required for later customer identity resolution.

* **Call Context Transport**
  Transfers provider call information into Calling so calls can later be connected with customers, conversations, and orders.

---

### 7. Integration Management

Provides the shared operational infrastructure used to register providers and manage individual business connections without embedding domain-specific processing inside the connection layer.

**Features:**

* **Provider Registry**
  Maintains the list of supported external providers together with their category, connection type, capabilities, and availability.

* **Business Connections**
  Represents each business's connection to an external provider independently from the global provider definition.

* **Connection Configuration**
  Stores provider-specific configuration required to operate an integration.

* **Credential Management**
  Manages API keys, secrets, access tokens, and other authentication information required by external providers.

* **OAuth Management**
  Supports OAuth authorization, token acquisition, token refresh, expiry handling, and connected account information where required.

* **Scope Management**
  Tracks permissions or scopes granted to Business Brain by external providers.

* **Connection Status**
  Maintains operational states such as connected, disconnected, syncing, and error.

* **Connection Testing**
  Allows a provider connection to be checked before it is relied upon for synchronization or business operations.

* **Provider Capability Mapping**
  Identifies which operations and data types a particular provider supports.

* **Rate Limit Handling**
  Tracks and responds to external provider request limits where required.

* **Connection Health**
  Maintains operational information that can later be surfaced through Integration & Data Observability.

* **Mock Connections**
  Supports simulated integration connections so the prototype can demonstrate complete workflows without requiring every external platform to be connected live.

> Integration Management owns the **operational lifecycle of external connections**. Product, customer, order, campaign, communication, shipment, or other domain-specific business processing remains inside the corresponding Business Data domains.

---

### 8. Sync & Webhooks

Provides the shared synchronization and event-ingestion mechanisms used by external integrations to keep Business Brain synchronized with connected platforms.

**Features:**

* **Full Synchronization**
  Supports initial or explicit synchronization of a complete supported dataset from an external provider.

* **Incremental Synchronization**
  Retrieves only records that changed since a previous successful synchronization when supported by the provider.

* **Sync Cursor Management**
  Maintains provider cursors, timestamps, pagination state, or equivalent checkpoints required for incremental synchronization.

* **Webhook Reception**
  Provides shared endpoints and processing infrastructure for receiving asynchronous provider events.

* **Webhook Validation**
  Validates webhook signatures, secrets, event structures, and provider requirements before accepting incoming events.

* **Webhook Event Routing**
  Determines the provider and event type and routes accepted payloads to the appropriate integration and Business Data pipeline.

* **Raw Payload Capture**
  Preserves original webhook or synchronization payloads when needed for debugging, replay, audit, or mapping verification.

* **Idempotent Processing**
  Prevents repeated webhook delivery or synchronization retries from unnecessarily creating duplicate business records.

* **Retry Handling**
  Retries recoverable synchronization or webhook-processing failures according to configured rules.

* **Failure Tracking**
  Records failed records, provider errors, validation errors, and processing failures for later investigation.

* **Sync History**
  Records synchronization runs including start time, completion time, status, received records, processed records, and failed records.

* **Data Freshness Tracking**
  Maintains the most recent successful synchronization information so Business Brain can determine whether connected data is current.

* **Replay & Reprocessing**
  Allows previously captured events or payloads to be processed again when mappings, processing logic, or temporary failures require recovery.

* **Mock Synchronization**
  Allows deterministic mock platform events to pass through the same conceptual synchronization pipeline used by real integrations.

---

## Domain Boundary

The **Integrations** domain answers:

**“How does Business Brain communicate with an external system?”**

It should not answer:

**“What does this external data mean inside the business?”**

That responsibility belongs to the appropriate Business Data domain.

For example:

**WooCommerce API → Commerce Integration → Raw Order Payload → Order Normalization → Canonical Order**

Similarly:

**Meta Ads → Marketing Integration → Campaign Payload → Marketing Normalization → Canonical Campaign**

and:

**WhatsApp → Communication Integration → Incoming Payload → Communication Normalization → Canonical Message**

The overall inbound flow is therefore:

**External Platform → Integration Connection → Sync/Webhook → Provider Adapter → Business Data Normalization → Canonical Data**

For outbound operations, the direction is reversed:

**Business Operation → Canonical Request → Integration Adapter → Provider API → External Platform**

This boundary keeps Business Brain provider-independent and prevents external platform schemas and APIs from leaking throughout the rest of the architecture.
