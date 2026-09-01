# Integration & Data Observability

## Description

The **Integration & Data Observability** domain provides operational visibility into how reliably Business Brain receives data from and communicates with external platforms. It monitors integration connections, synchronization processes, webhooks, failed records, provider availability, data freshness, and integration-related errors.

This domain does **not** perform the integrations themselves and does not own canonical business data. Instead, it observes the Integration layer and data-ingestion pipeline so users can determine whether connected systems are healthy, synchronized, delayed, degraded, or failing.

---

## Features

### 1. Connection Health

Monitors the current operational state of each external platform connection configured for a business.

**Features:**

* **Connection Status**
  Shows whether an integration connection is connected, disconnected, degraded, expired, disabled, or experiencing errors.

* **Connectivity Testing**
  Performs or displays the result of connection tests against supported external providers.

* **Authentication Health**
  Detects authentication problems such as invalid credentials, revoked permissions, or expired access tokens.

* **Credential Status**
  Indicates whether required API keys, OAuth credentials, secrets, or provider configuration are currently usable.

* **Last Successful Connection**
  Records when Business Brain last successfully communicated with the external platform.

* **Last Failure**
  Displays the most recent failed connection attempt and associated error information.

* **Connection-Level Error Summary**
  Aggregates recent errors associated with a specific integration connection.

* **Degraded Connection Detection**
  Identifies connections that technically remain available but are experiencing increased failures, latency, or synchronization problems.

* **Connection Health View**
  Provides a centralized operational view of all configured external connections.

Example:

```text
Integration Connections

WooCommerce       HEALTHY
Meta Ads          HEALTHY
WhatsApp          HEALTHY
Google Analytics  DEGRADED
Steadfast         ERROR
Dialyra           HEALTHY
```

---

### 2. Sync Monitoring

Provides visibility into currently running and recently executed synchronization processes.

**Features:**

* **Active Sync Visibility**
  Shows synchronization jobs that are currently running.

* **Sync Type Tracking**
  Distinguishes full synchronization, incremental synchronization, manual sync, scheduled sync, and other supported modes.

* **Sync Progress**
  Displays progress information such as records discovered, processed, succeeded, skipped, or failed.

* **Sync Status**
  Tracks states such as pending, running, completed, partially completed, and failed.

* **Entity-Level Sync Monitoring**
  Allows users to identify whether products, customers, orders, campaigns, or other entity types are experiencing synchronization problems.

* **Provider-Level Monitoring**
  Groups synchronization activity by provider and connection.

* **Sync Duration**
  Tracks how long synchronization operations take.

* **Current Cursor State**
  Displays incremental synchronization cursor or checkpoint information where applicable.

* **Manual Sync Trigger Context**
  Provides visibility when a synchronization process was manually requested.

* **Partial Failure Detection**
  Identifies cases where a sync completed but some records could not be processed.

---

### 3. Sync History

Maintains a historical record of synchronization operations for troubleshooting and operational analysis.

**Features:**

* **Historical Sync Records**
  Stores previous synchronization runs for each integration connection.

* **Execution Time**
  Records when each synchronization started and finished.

* **Sync Result Summary**
  Preserves counts for discovered, processed, successful, skipped, and failed records.

* **Sync Type History**
  Shows whether historical executions were full, incremental, scheduled, manual, or replay operations.

* **Failure History**
  Makes previous failed synchronization attempts available for investigation.

* **Duration History**
  Allows users to identify synchronization processes that are becoming slower over time.

* **Provider History**
  Groups synchronization history by provider or integration connection.

* **Entity History**
  Allows users to inspect historical synchronization activity for specific entity types.

* **Retry Visibility**
  Shows when failed synchronization operations were retried.

* **Troubleshooting Context**
  Preserves enough metadata to determine what happened during a particular synchronization run.

---

### 4. Failed Records

Tracks individual external records that could not successfully pass through synchronization, normalization, validation, or canonical processing.

**Features:**

* **Failed Record Capture**
  Records individual provider records that could not be processed successfully.

* **Source Identification**
  Preserves the provider, integration connection, entity type, and external identifier associated with the failure.

* **Raw Payload Reference**
  Maintains access to the original provider payload where available for debugging.

* **Failure Stage**
  Identifies where processing failed, such as retrieval, mapping, normalization, validation, identity resolution input, or persistence.

* **Failure Reason**
  Stores a human-readable explanation of why the record could not be processed.

* **Error Classification**
  Categorizes failures such as invalid data, missing required fields, unsupported values, mapping errors, duplicate conflicts, or internal processing failures.

* **Retry Status**
  Tracks whether the record has been retried and whether subsequent processing succeeded.

* **Manual Review**
  Allows problematic records to be inspected before retry or correction.

* **Resolution Tracking**
  Records when and how a failed record was eventually resolved.

* **Failure Aggregation**
  Groups similar failures so users can identify systemic problems rather than inspecting records individually.

Example:

```text
WooCommerce Sync
────────────────────────────

Processed:  2,431
Successful: 2,417
Failed:        14

Failures:

8 × INVALID_PRODUCT_REFERENCE
3 × MISSING_CUSTOMER_EMAIL
2 × UNSUPPORTED_ORDER_STATUS
1 × NORMALIZATION_ERROR
```

---

### 5. Webhook Monitoring

Monitors incoming webhook traffic from connected platforms and tracks whether webhook events are processed successfully.

**Features:**

* **Webhook Event Log**
  Maintains a record of received webhook events.

* **Provider Identification**
  Identifies which external platform and connection generated each webhook.

* **Webhook Type Tracking**
  Records event types such as order created, payment updated, message received, shipment status changed, or campaign updated.

* **Reception Status**
  Confirms whether Business Brain successfully received the webhook.

* **Validation Status**
  Shows whether webhook signatures, secrets, or other validation mechanisms succeeded.

* **Processing Status**
  Tracks whether the webhook was successfully routed and processed.

* **Webhook Latency**
  Measures the delay between provider event time, webhook reception, and internal processing where timestamps are available.

* **Duplicate Detection**
  Identifies webhook events already processed through idempotency mechanisms.

* **Failed Webhooks**
  Surfaces events that could not be validated, routed, normalized, or processed.

* **Webhook Retry Visibility**
  Tracks retry attempts where webhook processing supports replay or retry.

* **Webhook Replay**
  Allows supported failed webhook events to be reprocessed without requiring the external provider to resend them.

---

### 6. Data Freshness

Determines how recently Business Brain received valid data from each connected source and domain.

**Features:**

* **Last Successful Data Update**
  Records when valid data was most recently received from an integration.

* **Source Freshness**
  Measures freshness separately for WooCommerce, Meta Ads, WhatsApp, couriers, analytics providers, and other sources.

* **Entity-Level Freshness**
  Tracks freshness for different data categories such as orders, products, customers, campaigns, sessions, or shipments.

* **Expected Update Interval**
  Defines how frequently data is expected from a particular integration or entity type.

* **Stale Data Detection**
  Identifies data sources that have exceeded their expected update interval.

* **Freshness Status**
  Classifies data as fresh, delayed, stale, or unavailable.

* **Freshness Age**
  Shows how long it has been since the last successful update.

* **Dashboard Freshness Indicators**
  Allows operational and analytical interfaces to indicate when displayed information may be outdated.

* **AI Freshness Context**
  Makes freshness information available to AI so it does not present stale information as current without qualification.

Example:

```text
Data Freshness

Orders
WooCommerce
Last Updated: 2 minutes ago
Status: FRESH

Campaign Metrics
Meta Ads
Last Updated: 3 hours ago
Status: FRESH

Website Analytics
GA4
Last Updated: 27 hours ago
Status: STALE
```

This distinction is important because a dashboard can technically work while displaying outdated data.

---

### 7. Provider Health

Monitors the operational reliability of external providers independently from individual business connections.

**Features:**

* **Provider Availability**
  Tracks whether a provider appears operational and reachable.

* **API Response Monitoring**
  Observes success and failure patterns from provider API requests.

* **Provider Latency**
  Tracks unusual increases in provider response time.

* **Rate Limit Monitoring**
  Detects when provider rate limits are approaching or have been reached.

* **Provider Error Rate**
  Measures repeated provider-side errors over a selected period.

* **Provider Degradation Detection**
  Identifies patterns indicating that an external service may be degraded.

* **Cross-Connection Impact**
  Distinguishes a provider-wide problem from a problem affecting only one business connection.

* **Provider Capability Health**
  Allows monitoring to distinguish between provider capabilities where one API area may fail while others remain operational.

* **Provider Health Status**
  Provides simplified states such as healthy, degraded, unavailable, or unknown.

A useful distinction is:

```text
Connection Problem
──────────────────
Business A → Meta Ads
Invalid OAuth Token

Only Business A is affected.


Provider Problem
────────────────
Meta Ads API
High 5xx Error Rate

Multiple connections may be affected.
```

---

### 8. Integration Errors

Provides centralized visibility into errors generated throughout integration and external-data processing workflows.

**Features:**

* **Centralized Error Log**
  Collects integration-related failures into a common operational view.

* **Error Classification**
  Categorizes errors such as authentication, connectivity, provider API, rate limit, webhook, sync, mapping, normalization, validation, and internal processing errors.

* **Error Severity**
  Classifies errors according to operational impact.

* **Provider Context**
  Associates errors with the relevant external provider.

* **Connection Context**
  Links errors to the specific business integration connection where applicable.

* **Entity Context**
  Preserves affected entity type and identifier when an error concerns a particular business record.

* **Sync Context**
  Links errors to the synchronization operation that generated them.

* **Webhook Context**
  Links webhook-processing errors to the corresponding webhook event.

* **Raw Error Details**
  Preserves technical error information required for debugging.

* **Human-Readable Error Message**
  Provides a simplified explanation that operational users can understand.

* **Error Deduplication**
  Groups repeated instances of the same underlying failure where appropriate.

* **Occurrence Tracking**
  Records how frequently an error occurs and when it was first and most recently observed.

* **Resolution Status**
  Tracks whether the problem is active, acknowledged, resolved, or ignored.

---

## Observability Flow

Integration & Data Observability monitors the data path without becoming part of the canonical business model.

```text
External Platform
       ↓
Integration Connection
       ↓
┌─────────────────────────────┐
│ Integration & Data          │
│ Observability               │
│                             │
│ • Connection Health         │
│ • Provider Health           │
└─────────────────────────────┘
       ↓
Sync / Webhook
       │
       ├───────────────┐
       │               │
       ▼               ▼
 Sync Monitoring   Webhook Monitoring
       │               │
       └───────┬───────┘
               ↓
       Provider Payload
               ↓
     Domain Processing
               │
        ┌──────┴──────┐
        ▼             ▼
     Success       Failure
        │             │
        ▼             ▼
Canonical Data   Failed Records
                      ↓
              Integration Errors
```

Observability therefore follows the complete path from external connectivity to successful canonical processing.

---

## Connection Health vs Provider Health

These concepts should remain separate because they describe different failure scopes.

```text
Connection Health
─────────────────
"Can this business successfully
communicate with this provider?"

Example:
Business A's WooCommerce API key expired.


Provider Health
───────────────
"Is the external provider itself
operating normally?"

Example:
WooCommerce API endpoint is unavailable.
```

This distinction prevents Business Brain from incorrectly telling users to reconnect an integration when the actual problem belongs to the external provider.

---

## Sync Monitoring vs Data Freshness

A successful sync does not automatically mean all business data is sufficiently fresh.

```text
Sync Monitoring
───────────────
"Did synchronization run correctly?"

Example:
Meta Ads sync completed successfully
at 10:00 AM.


Data Freshness
──────────────
"How current is the data we currently have?"

Example:
It is now 8:00 PM and campaign metrics
have not been updated for 10 hours.
```

Both signals are required for reliable business monitoring.

---

## Failed Record Lifecycle

A provider synchronization may succeed overall while individual records fail.

The lifecycle should therefore support:

```text
Provider Record
      ↓
Processing
      ↓
   Failure
      ↓
Failed Record
      ↓
Failure Classification
      ↓
┌───────────────┐
│ Fix Available?│
└───────┬───────┘
        │
        ▼
      Retry
        ↓
   ┌────┴────┐
   ▼         ▼
Success    Failure
   │         │
   ▼         ▼
Resolved   Review
```

This prevents one malformed record from making the entire integration appear unusable while still ensuring the lost record remains visible.

---

## Data Trust and Freshness

Observability should influence how downstream systems present information.

For example:

```text
Meta Ads
Last Successful Sync:
31 August, 10:00 AM

Current Time:
1 September, 1:00 PM

Status:
STALE
```

Business Intelligence may still contain valid historical metrics, but Overview & Monitoring should indicate that the latest campaign information may be incomplete.

Similarly, AI Intelligence should receive context such as:

```text
Campaign Data Freshness:
STALE

Last Successful Update:
27 hours ago
```

so the assistant can state that its analysis is based on data available up to that point.

---

## Observability Status Model

A simplified prototype status model can be:

```text
HEALTHY
Everything is operating normally.

DEGRADED
The system is operating but experiencing
delays, partial failures, or elevated errors.

ERROR
A significant integration function is failing.

STALE
Data has not been updated within its
expected freshness window.

DISCONNECTED
The integration connection is unavailable.

UNKNOWN
There is not enough recent information
to determine health reliably.
```

These statuses can be reused across monitoring interfaces while the detailed cause remains available underneath.

---

## Example Observability Scenario

Suppose Business Brain normally receives WooCommerce orders through webhooks.

```text
WooCommerce
      ↓
Order Webhook
      ↓
Business Brain
```

Suddenly webhook authentication begins failing.

The observability system can represent:

```text
Connection Health
DEGRADED

Webhook Monitoring
37 validation failures

Data Freshness
Orders last updated 52 minutes ago

Failed Records
37 webhook events pending/rejected

Integration Errors
WEBHOOK_SIGNATURE_INVALID
```

The user should therefore see one coherent operational problem rather than four unrelated technical messages:

```text
WooCommerce Order Integration
─────────────────────────────

Status: DEGRADED

Problem:
Incoming order webhooks are failing validation.

Impact:
New order data may be incomplete.

Last Successful Order Update:
52 minutes ago

Failed Events:
37
```

This is the practical purpose of the observability layer: **turn low-level integration failures into understandable data reliability status.**

---

## Relationship with Overview & Monitoring

Integration & Data Observability monitors the reliability of Business Brain's **inputs**, while Overview & Monitoring primarily monitors the state of the **business**.

```text
Integration & Data Observability
────────────────────────────────
"Can we trust that the data pipeline
is currently working?"

Examples:
- WooCommerce sync failed
- Meta token expired
- GA4 data is stale
- Courier API is degraded


Overview & Monitoring
─────────────────────
"What is happening in the business?"

Examples:
- Revenue decreased
- Delivery failures increased
- Campaign ROAS improved
- Support backlog increased
```

The two domains should interact.

If important source data becomes stale, Overview & Monitoring should display a data-quality warning rather than presenting incomplete metrics as fully current.

---

## Relationship with Business Intelligence

Integration observability problems are not automatically business problems.

For example:

```text
Meta Ads API unavailable
```

is an **integration/provider issue**.

Whereas:

```text
Campaign ROAS dropped by 35%
```

is a **business intelligence issue**.

However, observability information should protect Business Intelligence from misleading conclusions.

Conceptually:

```text
External Data
      ↓
Observability
      ↓
Data Freshness / Reliability
      ↓
Business Intelligence
      ↓
Facts & Issues
```

If required source data is stale or incomplete, analytical results can be marked accordingly or certain analyses can be delayed.

---

## Domain Boundary

The **Integration & Data Observability** domain answers:

**“Are Business Brain's external connections and data pipelines healthy, current, and reliable?”**

It does not establish provider connections or perform synchronization itself; those responsibilities belong to **Integrations**.

It does not own canonical products, customers, orders, campaigns, messages, shipments, or other business entities; those belong to **Business Data**.

It does not determine business performance or create business issues; those belong to **Business Intelligence**.

Its primary inputs are:

**Integration Connections + Sync Operations + Webhook Events + Processing Results + Provider Responses**

Its primary outputs are:

**Health Status + Sync Visibility + Freshness Status + Failed Records + Error Visibility + Reliability Signals**

The overall flow is:

**External Platforms → Integrations → Observability → Canonical Data → Business Intelligence → Overview & Monitoring**

The core principle is:

**Business Brain should not only know what its data says—it should also know whether that data arrived correctly, completely, and recently enough to be trusted.**
