# Business Configuration

## Description

The **Business Configuration** domain defines how an individual business wants Business Brain to operate. It provides the administrative settings used to configure business identity, integrations, operational rules, AI behavior, knowledge management, policies, and monitoring preferences.

This domain stores **configuration and control settings**, not operational business events or analytical conclusions. Other domains consume these settings when processing data, applying rules, retrieving knowledge, generating AI responses, monitoring business health, or interacting with external systems.

---

## Features

### 1. Business Profile

Defines the primary identity and operational characteristics of the business using Business Brain.

**Features:**

* **Business Name**
  Stores the official or preferred name used throughout Business Brain.

* **Business Description**
  Provides a concise description of what the business does, its products or services, and its operating model.

* **Business Industry**
  Identifies the primary industry or business category.

* **Business Contact Information**
  Stores general business contact information used for administrative or operational purposes.

* **Business Location**
  Defines the primary operating location and relevant regional context.

* **Operating Regions**
  Specifies geographic areas where the business operates, sells, or delivers.

* **Business Channels**
  Identifies relevant channels such as website, social commerce, marketplaces, physical operations, or direct sales.

* **Default Currency**
  Defines the primary currency used for business-level displays and configuration.

* **Timezone**
  Defines the business timezone used when interpreting dates, reporting periods, schedules, and monitoring windows.

* **Business Metadata**
  Stores additional configurable information that does not require dedicated fields.

> The configuration profile represents editable administrative settings. Durable descriptive knowledge derived from the profile may also be exposed through **Business Memory & Knowledge** for retrieval and AI context.

---

### 2. General Settings

Provides shared settings that control general Business Brain behavior for the business.

**Features:**

* **Locale Settings**
  Defines preferred language, regional formatting, and localization behavior.

* **Date & Time Settings**
  Controls date formats, timezone interpretation, and reporting period boundaries.

* **Currency Settings**
  Defines default currency and display preferences for financial information.

* **Number Formatting**
  Controls decimal, percentage, and numeric display conventions.

* **Default Reporting Period**
  Defines the default analytical timeframe used in dashboards and monitoring views.

* **Business Week Definition**
  Configures how weekly reporting periods are interpreted.

* **Operational Defaults**
  Stores default values used by supported business workflows.

* **Feature Preferences**
  Allows optional Business Brain capabilities to be enabled or disabled where appropriate.

* **Configuration Metadata**
  Maintains additional general-purpose settings required by the business.

---

### 3. Integration Configuration

Provides the administrative interface for configuring external platforms connected to Business Brain.

**Features:**

* **Provider Selection**
  Allows the business to select supported providers such as WooCommerce, Shopify, Meta, WhatsApp, GA4, courier platforms, or calling systems.

* **Connection Setup**
  Configures the information required to establish an integration connection.

* **Credential Configuration**
  Provides secure configuration for API keys, tokens, OAuth credentials, secrets, and other provider authentication information.

* **Integration Scope**
  Defines which provider capabilities or data categories the business authorizes Business Brain to access.

* **Sync Configuration**
  Controls supported synchronization behavior such as full, incremental, scheduled, or manually triggered synchronization.

* **Webhook Configuration**
  Configures webhook endpoints, event subscriptions, secrets, and related settings where required.

* **Entity Sync Selection**
  Allows supported entity types such as products, customers, orders, or campaigns to be included or excluded.

* **Connection Testing**
  Allows configured credentials and provider connectivity to be validated.

* **Connection Enable / Disable**
  Allows integrations to be temporarily disabled without deleting their configuration.

* **Provider-Specific Settings**
  Supports configuration values unique to individual external providers.

* **Mock Integration Configuration**
  Allows prototype scenarios to use simulated integrations without requiring real external credentials.

---

### 4. Business Rules

Defines explicit deterministic rules that control supported Business Brain behavior and business-specific decisions.

**Features:**

* **Rule Definition**
  Allows configurable rules to be represented using conditions, thresholds, parameters, and expected outcomes.

* **Rule Categories**
  Organizes rules by areas such as orders, customers, delivery, marketing, support, payments, or intelligence.

* **Threshold Configuration**
  Defines values used by deterministic detection logic, such as acceptable delivery failure rate or support response time.

* **Condition-Based Rules**
  Supports rules where specific conditions trigger classification, alerts, or operational behavior.

* **Entity-Specific Rules**
  Allows rules to apply to particular products, regions, campaigns, couriers, channels, or other business dimensions.

* **Rule Priority**
  Defines precedence when multiple applicable business rules exist.

* **Rule Enable / Disable**
  Allows rules to be temporarily deactivated without deleting their configuration.

* **Rule Validation**
  Ensures configured conditions and parameters are structurally valid before activation.

* **Rule Versioning**
  Preserves changes to important rules so historical behavior can be explained.

* **Rule Traceability**
  Provides stable rule identifiers that Business Intelligence can reference when producing deterministic relationships, facts, or issues.

Example:

```text id="q6e8yc"
Rule:
HIGH_DELIVERY_FAILURE

Condition:
delivery_failure_rate > 15%

Minimum Orders:
20

Evaluation Period:
Last 30 days

Dimension:
Courier + Region

Severity:
HIGH
```

Business Intelligence can then apply this configuration deterministically rather than asking AI whether the failure rate "looks high."

---

### 5. AI Configuration

Defines how AI capabilities should operate within the business while preserving system-level safety and authority boundaries.

**Features:**

* **AI Enable / Disable**
  Allows supported AI capabilities to be enabled or disabled.

* **AI Provider Configuration**
  Defines the configured AI provider or model infrastructure where multiple options are supported.

* **Model Selection**
  Allows appropriate models to be selected for supported tasks such as business assistance, support, summarization, or recommendations.

* **Business Assistant Configuration**
  Controls settings specific to the general Business Assistant.

* **Customer Support AI Configuration**
  Defines how AI assistance should behave inside customer-support workflows.

* **Marketing Assistant Configuration**
  Controls supported AI assistance for marketing analysis and recommendations.

* **AI Context Configuration**
  Determines which approved categories of business context can be retrieved for particular AI tasks.

* **Response Preferences**
  Defines configurable response characteristics such as preferred language, detail level, or communication behavior.

* **Confidence Thresholds**
  Allows certain AI workflows to require stronger confidence before producing or surfacing specific outputs.

* **Human Escalation Rules**
  Defines when AI-supported customer interactions should be transferred to human support.

* **Suggested Action Configuration**
  Controls which types of actions AI is permitted to propose.

* **Execution Permissions**
  Determines which AI-suggested operations always require approval and which execution capabilities are disabled entirely.

* **Model Parameters**
  Stores supported model-level parameters where configuration is useful.

* **AI Feature Controls**
  Allows specific capabilities such as recommendations, summaries, or suggested replies to be independently enabled or disabled.

> Business-level AI configuration may make the system **more restrictive**, but it should not be able to disable mandatory platform safety or authority guardrails.

---

### 6. Knowledge Configuration

Controls how business documents and organizational knowledge are ingested, processed, retrieved, and made available to AI.

**Features:**

* **Knowledge Source Management**
  Allows administrators to configure approved sources of business knowledge.

* **Knowledge Type Configuration**
  Defines categories such as product knowledge, support information, policies, brand guidance, or internal business documentation.

* **Document Ingestion Settings**
  Controls supported ingestion behavior for uploaded documents, manual text, websites, or other knowledge sources.

* **Chunking Configuration**
  Defines supported chunking parameters used during knowledge processing.

* **Embedding Configuration**
  Selects the embedding model and related settings used for semantic retrieval.

* **Vector Search Configuration**
  Controls supported semantic-search parameters such as retrieval limits and similarity requirements.

* **Keyword Search Configuration**
  Configures lexical retrieval behavior where customization is required.

* **Hybrid Retrieval Configuration**
  Controls how vector, keyword, and metadata signals are combined.

* **Retrieval Limits**
  Defines how many knowledge chunks may be returned for an AI request.

* **Knowledge Scope**
  Determines which knowledge categories are available to specific AI workflows.

* **Archived Knowledge Handling**
  Controls whether historical or superseded knowledge may be retrieved for explicitly historical tasks.

* **Reprocessing Controls**
  Allows documents to be reprocessed or re-embedded when configuration changes.

---

### 7. Policy Configuration

Provides structured administrative management for business policies used by operational and AI workflows.

**Features:**

* **Delivery Policy Configuration**
  Defines delivery coverage, expected times, charges, courier preferences, COD rules, and failure-handling instructions.

* **Return Policy Configuration**
  Defines eligibility requirements, return windows, exclusions, and return procedures.

* **Refund Policy Configuration**
  Defines refund eligibility, methods, approval conditions, and related business rules.

* **Cancellation Policy Configuration**
  Defines when and how customers can cancel orders.

* **Support Policy Configuration**
  Defines customer-service rules, escalation requirements, response expectations, and operational guidance.

* **Product Policy Configuration**
  Stores business rules that apply to particular products or categories.

* **Policy Applicability**
  Allows policies to be scoped by region, product, channel, customer type, or other relevant conditions.

* **Policy Effective Dates**
  Defines when a policy becomes or ceases to be applicable.

* **Policy Status**
  Supports states such as draft, active, superseded, and archived.

* **Policy Versioning**
  Preserves previous policy versions instead of silently overwriting historical business rules.

* **Policy Validation**
  Ensures required policy information is complete before activation.

* **AI Policy Availability**
  Determines which approved policies should be available as grounding context for relevant AI workflows.

---

### 8. Monitoring Configuration

Defines what Business Brain should monitor, how conditions are evaluated, and when operational attention is required.

**Features:**

* **KPI Selection**
  Determines which metrics should appear prominently in Overview & Monitoring.

* **KPI Targets**
  Defines desired values or ranges for selected business indicators.

* **Monitoring Thresholds**
  Configures thresholds for conditions such as delivery failure, conversion decline, support backlog, or refund increases.

* **Alert Severity Rules**
  Defines how monitored conditions map to warning, high, or critical severity levels.

* **Monitoring Windows**
  Defines evaluation periods such as daily, weekly, rolling 7-day, or rolling 30-day windows.

* **Comparison Configuration**
  Determines whether metrics should be compared against previous periods, baselines, targets, or other supported references.

* **Data Freshness Thresholds**
  Defines how long data can remain unchanged before being classified as delayed or stale.

* **Integration Monitoring Preferences**
  Configures which integrations and data sources require active health monitoring.

* **Domain Monitoring**
  Allows monitoring to focus on selected domains such as marketing, website, support, or delivery.

* **Cross-Domain Monitoring Rules**
  Configures supported monitoring scenarios that evaluate related signals across multiple business domains.

* **Issue Visibility Preferences**
  Controls which issue severity levels should appear prominently in monitoring interfaces.

* **Recommendation Visibility**
  Determines which recommendation priorities should be surfaced in overview views.

---

## Configuration Architecture

Business Configuration should primarily control other domains rather than duplicate their runtime data.

```text id="xbrf5m"
                Business Configuration
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
        ▼                ▼                 ▼
  Integrations     Business Intelligence   AI Intelligence
        │                │                 │
        │                │                 │
        ▼                ▼                 ▼
Connection /        Rules / Thresholds    AI Behavior /
Sync Behavior       Monitoring Logic      Retrieval
        │                │                 │
        └────────────────┼─────────────────┘
                         │
                         ▼
                Business Operations
                         │
                         ▼
                Overview & Monitoring
```

Configuration determines **how the system should behave**, while the corresponding domains remain responsible for actually performing that behavior.

---

## Configuration vs Runtime State

An important architectural distinction is the difference between configuration and runtime state.

For example:

```text id="1ifgvs"
CONFIGURATION

WooCommerce:
Sync Orders = Enabled
Sync Interval = 15 minutes


RUNTIME STATE

Last Sync:
12:30 PM

Records Processed:
427

Failed:
3

Status:
COMPLETED_WITH_ERRORS
```

The first belongs to **Business Configuration**.

The second belongs to **Integrations / Integration & Data Observability**.

The same pattern applies across the platform.

---

## Business Profile: Configuration vs Memory

Business Profile appears in both **Business Configuration** and **Business Memory & Knowledge**, but they represent different responsibilities.

```text id="7mz3s1"
Business Configuration
──────────────────────
Editable authoritative settings.

Example:
Business Name: Example Store
Timezone: Asia/Dhaka
Currency: BDT
Operating Region: Bangladesh


Business Memory
───────────────
Retrievable business context.

Example:
Example Store is an online retail
business primarily serving customers
through social commerce and its website.
```

The configuration record should normally be the authoritative source for structured profile settings.

Business Memory may expose a normalized or knowledge-oriented representation of that profile for retrieval and AI grounding.

This avoids maintaining two competing authoritative business profiles.

---

## Policy Configuration vs Business Memory

The same separation applies to policies.

```text id="o54fge"
Policy Configuration
────────────────────
Defines and manages the authoritative policy.

Return Window:
7 days

Condition:
Unused product

Status:
ACTIVE


Business Memory
───────────────
Makes the policy retrievable.

Knowledge Chunk:
"Customers may return unused products
within seven days of delivery."
```

The policy should therefore flow conceptually as:

```text id="umq71k"
Policy Configuration
        ↓
Approved Policy
        ↓
Business Memory
        ↓
Chunking / Embedding
        ↓
Retrieval
        ↓
AI Intelligence
```

AI should retrieve the approved policy rather than maintaining its own independent policy interpretation.

---

## Business Rules vs AI Reasoning

Business Rules should be deterministic whenever they establish authoritative business conditions.

For example:

```text id="kefr0e"
Business Rule

IF:
delivery_failure_rate > 15%

AND:
shipment_count >= 20

THEN:
Create HIGH_DELIVERY_FAILURE issue
```

This flows into:

```text id="v40zop"
Business Configuration
        ↓
Business Rule
        ↓
Business Intelligence
        ↓
Metric Evaluation
        ↓
Verified Fact
        ↓
Business Issue
        ↓
AI Intelligence
        ↓
Explanation / Recommendation
```

The AI may explain the issue or recommend what to do about it, but it should not replace the deterministic rule responsible for declaring the authoritative issue.

---

## Monitoring Configuration vs Monitoring Results

Monitoring configuration defines **what should be watched**.

Overview & Monitoring shows **what is currently happening**.

```text id="e63vkp"
Monitoring Configuration

Delivery Failure Warning:
> 10%

Delivery Failure Critical:
> 20%

Freshness Threshold:
Orders > 30 minutes


Overview & Monitoring

Delivery Failure:
17%

Status:
WARNING


Integration Observability

Order Data Age:
47 minutes

Status:
STALE
```

This separation makes monitoring behavior configurable while keeping observed results outside the configuration domain.

---

## AI Configuration & Guardrail Hierarchy

Not every AI guardrail should be configurable by a business.

A useful hierarchy is:

```text id="4w3ufc"
Platform Guardrails
        │
        │ Mandatory
        ▼
Business AI Configuration
        │
        │ Business-specific restrictions
        ▼
AI Workflow Configuration
        │
        ▼
AI Execution
```

For example, a business may configure:

```text id="wmcnmq"
AI may suggest campaign changes:
YES

AI may suggest courier changes:
YES

Customer support auto-reply:
NO

Human approval before campaign action:
YES
```

But it should not be able to configure:

```text id="vv2y45"
Allow AI to create verified facts
without evidence:
YES
```

because that would violate a core Business Brain architectural guardrail.

---

## Configuration Change Traceability

Important configuration changes should remain traceable, particularly when they influence business decisions.

Examples include:

* Business rule threshold changes
* Policy changes
* AI execution permission changes
* Monitoring threshold changes
* Integration configuration changes
* Knowledge retrieval configuration changes

A configuration change can affect later system behavior:

```text id="szyj3e"
August 1

Delivery Failure Threshold:
15%

        ↓

August 15

Threshold changed:
12%

        ↓

August 20

Failure Rate:
13%

        ↓

Issue Created
```

Without configuration history, it would be difficult to explain why the same metric produced different outcomes at different times.

For the prototype, complete enterprise-grade configuration auditing is not required, but important rule and policy versions should remain explainable.

---

## Example Business Configuration

A configured business might look conceptually like:

```text id="fn6y9w"
Business
────────────────────────
Currency: BDT
Timezone: Asia/Dhaka


Integrations
────────────────────────
WooCommerce     Enabled
Meta Ads        Enabled
WhatsApp        Enabled
GA4             Enabled
Steadfast       Enabled


Business Rules
────────────────────────
Delivery Failure Warning: 10%
Delivery Failure High:    15%

Minimum Sample:
20 shipments


AI
────────────────────────
Business Assistant: Enabled
Support AI:        Enabled
Marketing AI:      Enabled

Automatic External Actions:
Disabled

Approval Required:
Yes


Knowledge
────────────────────────
Vector Search:  Enabled
Keyword Search: Enabled
Hybrid Search:  Enabled


Monitoring
────────────────────────
Revenue
Orders
ROAS
Conversion Rate
Delivery Failure
Refund Rate
Support Backlog
```

These settings influence multiple Business Brain domains while remaining centrally manageable.

---

## Domain Boundary

The **Business Configuration** domain answers:

**“How should Business Brain operate for this particular business?”**

It does not own operational business records; those belong to **Business Data**.

It does not perform provider synchronization; that belongs to **Integrations**.

It does not store integration runtime health; that belongs to **Integration & Data Observability**.

It does not calculate metrics, facts, or issues; those belong to **Business Intelligence**.

It does not generate AI recommendations; that belongs to **AI Intelligence**.

It does not represent current monitoring results; those belong to **Overview & Monitoring**.

Its primary outputs are configuration consumed by other domains:

```text id="3f2fvu"
Business Configuration
        │
        ├──→ Integrations
        ├──→ Business Data
        ├──→ Business Intelligence
        ├──→ Business Memory
        ├──→ AI Intelligence
        ├──→ Business Operations
        └──→ Overview & Monitoring
```

The core principle is:

**Business Configuration defines how Business Brain should behave; the runtime domains remain responsible for actually carrying out, observing, and recording that behavior.**
