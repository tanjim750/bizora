# Prototype Simulation

## Description

The **Prototype Simulation** domain provides deterministic mock data, external-platform behavior, business scenarios, injected problems, and expected outcomes required to demonstrate and validate Business Brain without depending on live third-party systems.

Its purpose is not merely to generate random demo data. It creates **controlled and reproducible business situations** in which source events flow through integrations, canonical mapping, identity resolution, Business Intelligence, Business Graph, and AI Intelligence. This allows the prototype to demonstrate that Business Brain can correctly reconstruct business reality, detect known problems, connect evidence, and produce grounded recommendations.

Prototype Simulation is **testing and demonstration infrastructure**, not part of the authoritative production business domain.

---

## Features

### 1. Mock Platform Registry

Defines the external platforms that can be simulated inside the prototype.

**Features:**

* **Mock Provider Definition**
  Registers simulated providers such as WooCommerce, Shopify, Meta Ads, WhatsApp, GA4, courier platforms, and Dialyra.

* **Provider Type Classification**
  Classifies mock platforms as commerce, communication, marketing, analytics, courier, calling, or other supported integration types.

* **Provider Capabilities**
  Defines which simulated capabilities a provider supports, such as products, customers, orders, campaigns, messages, shipments, or calls.

* **Provider Identity Rules**
  Defines the external identifier formats used by each simulated platform.

* **Provider Event Types**
  Registers the events a mock provider can generate, such as `ORDER_CREATED`, `MESSAGE_RECEIVED`, `CAMPAIGN_UPDATED`, or `SHIPMENT_FAILED`.

* **Provider Payload Schema**
  Defines the expected structure of simulated provider payloads.

* **Mock Connection Support**
  Allows prototype businesses to appear connected to external platforms without requiring real credentials or API access.

* **Provider Behavior Configuration**
  Supports provider-specific behavior such as event ordering, status values, identifier formats, or simulated API responses.

Example:

```text
Mock Platform Registry

WooCommerce
├── Products
├── Customers
├── Orders
└── Payments

Meta Ads
├── Campaigns
├── Metrics
└── Conversions

WhatsApp
├── Users
├── Messages
└── Delivery Events

GA4
├── Visitors
├── Sessions
└── Events

Steadfast
├── Shipments
├── Tracking
└── Delivery Events

Dialyra
├── Calls
├── Call Events
└── Transcripts
```

---

### 2. Mock Scenarios

Defines complete business stories that Business Brain can simulate from beginning to end.

**Features:**

* **Scenario Definition**
  Represents a named business situation containing source events, entities, expected relationships, problems, and outcomes.

* **Scenario Type**
  Classifies scenarios such as normal operation, marketing problem, delivery failure, customer journey, support escalation, or data-quality problem.

* **Scenario Description**
  Explains the business situation the scenario is intended to demonstrate.

* **Multi-Platform Scenarios**
  Allows one scenario to contain events from several external platforms.

* **Cross-Domain Scenarios**
  Supports scenarios involving marketing, website activity, orders, customers, payments, delivery, support, and calling simultaneously.

* **Scenario Lifecycle**
  Supports states such as draft, ready, running, completed, and failed.

* **Reusable Scenarios**
  Allows the same scenario to be executed repeatedly for demonstrations or validation.

* **Scenario Isolation**
  Keeps events and expected results belonging to one scenario distinguishable from other simulations.

Example scenario:

```text
Scenario:
CAMPAIGN_DELIVERY_FAILURE

Story:

Meta Campaign A
      ↓
Generates Website Traffic
      ↓
Customers Place Orders
      ↓
Orders Increase
      ↓
Courier X Handles Gazipur Orders
      ↓
Delivery Failure Increases
      ↓
Returns Increase
      ↓
Realized Revenue Drops
      ↓
Business Brain Detects Issue
      ↓
AI Recommends Courier Investigation
```

---

### 3. Scenario Configuration

Controls the parameters used to generate and execute a mock business scenario.

**Features:**

* **Scenario Parameters**
  Defines configurable values such as customer count, order count, campaign spend, conversion rate, or shipment volume.

* **Time Range Configuration**
  Defines the simulated period covered by a scenario.

* **Platform Selection**
  Specifies which mock platforms participate in the scenario.

* **Entity Volume Configuration**
  Controls how many products, customers, orders, sessions, messages, calls, or shipments should be generated.

* **Regional Configuration**
  Allows scenarios to focus on specific locations or business regions.

* **Campaign Configuration**
  Defines campaign-level parameters such as spend, traffic, conversion behavior, or target products.

* **Delivery Configuration**
  Controls courier allocation, delivery success rates, return behavior, and regional fulfillment patterns.

* **Support Configuration**
  Defines conversation volume, support issues, AI handling, and escalation behavior.

* **Simulation Mode**
  Allows scenarios to run as batch generation, chronological event playback, or other prototype-supported modes.

* **Configuration Overrides**
  Allows individual demonstrations to modify selected parameters without redefining the complete scenario.

---

### 4. Deterministic Seed Management

Ensures generated prototype data remains reproducible across repeated executions.

**Features:**

* **Scenario Seed**
  Assigns a stable seed value to each deterministic scenario.

* **Reproducible Data Generation**
  Ensures the same seed and configuration generate the same entities, events, identifiers, and expected outcomes.

* **Deterministic Identity Generation**
  Produces predictable customers, products, external IDs, phone numbers, session identifiers, and other test identities.

* **Deterministic Timeline Generation**
  Produces consistent timestamps and event ordering.

* **Deterministic Metric Outcomes**
  Ensures generated business activity results in predictable metric values.

* **Seed Override**
  Allows developers to generate controlled variations by intentionally changing the seed.

* **Debug Reproduction**
  Makes simulation failures reproducible by rerunning the exact scenario with the same seed.

* **Demo Consistency**
  Prevents prototype demonstrations from producing unexpectedly different results between executions.

Example:

```text
Scenario:
DELIVERY_FAILURE_GAZIPUR

Seed:
75001

Run #1
Orders: 500
Failed Deliveries: 87
Issue: HIGH_DELIVERY_FAILURE

Run #2
Orders: 500
Failed Deliveries: 87
Issue: HIGH_DELIVERY_FAILURE
```

The scenario should behave identically unless its seed or configuration changes.

---

### 5. Mock Source Events

Generates chronological external-platform events that represent realistic business activity.

**Features:**

* **Commerce Events**
  Generates product, customer, order, payment, cancellation, and refund events.

* **Marketing Events**
  Generates campaign, metric, conversion, and advertising activity.

* **Website Events**
  Generates visitor, session, page view, product view, cart, checkout, and conversion events.

* **Communication Events**
  Generates incoming messages, outgoing replies, delivery status, and conversation activity.

* **Courier Events**
  Generates shipment submission, pickup, transit, delivery, failure, and return events.

* **Calling Events**
  Generates incoming calls, outgoing calls, call lifecycle events, and transcript data.

* **Chronological Ordering**
  Preserves realistic ordering between related events.

* **Cross-Platform Event Correlation**
  Generates identifiers and values that allow later Identity Resolution and Business Intelligence rules to establish expected relationships.

* **Event Metadata**
  Stores provider, event type, external entity identifier, timestamp, and scenario context.

---

### 6. Provider Payload Simulation

Produces provider-specific payloads that resemble data received from actual external integrations.

**Features:**

* **Provider-Specific Structure**
  Generates different payload structures for WooCommerce, Meta, WhatsApp, couriers, analytics systems, and other mock providers.

* **External Field Names**
  Uses provider-oriented field names rather than directly generating Business Brain canonical objects.

* **Provider Status Values**
  Simulates provider-specific order, payment, message, shipment, or campaign status values.

* **External Identifiers**
  Generates realistic provider-specific IDs for entities and events.

* **Nested Payload Structures**
  Supports provider payloads containing nested products, order items, customer details, campaign information, or event properties.

* **Optional Fields**
  Simulates providers where fields may be absent or conditionally available.

* **Raw Payload Preservation**
  Allows generated payloads to pass through the same raw-payload handling used by the Integration layer.

* **Webhook Payload Simulation**
  Generates event payloads that can enter Business Brain through simulated webhook workflows.

* **API Response Simulation**
  Supports mock provider responses for synchronization or outbound operations.

A key requirement is:

```text
WRONG

Mock Scenario
     ↓
Directly creates canonical order


CORRECT

Mock Scenario
     ↓
WooCommerce-style payload
     ↓
Commerce Integration
     ↓
Order Normalization
     ↓
Canonical Order
```

The prototype should therefore exercise the actual Business Brain transformation path wherever that path represents core functionality.

---

### 7. Canonical Mapping Expectations

Defines what canonical Business Brain entities should result from simulated provider payloads.

**Features:**

* **Expected Canonical Entity**
  Defines whether a provider record should become a customer, product, order, payment, campaign, message, shipment, call, or another canonical entity.

* **Expected Field Mapping**
  Defines important provider-to-canonical field transformations.

* **Expected External References**
  Specifies which provider identifiers should be preserved as external references.

* **Expected Normalization**
  Defines normalized forms of phone numbers, statuses, currencies, identifiers, and other supported values.

* **Expected Entity Relationships**
  Defines deterministic relationships expected after canonical processing.

* **Expected Identity Resolution**
  Defines which external identities should ultimately resolve to the same canonical entity.

* **Expected Failure Mapping**
  Defines cases where intentionally invalid provider payloads should fail canonical validation.

* **Mapping Validation**
  Allows generated canonical entities to be compared with expected outcomes.

Example:

```text
WooCommerce Payload

customer_id: 52
email: customer@example.com
phone: 017XXXXXXXX

Expected:

Canonical Customer:
C1

External Identity:
WooCommerce Customer 52

Expected Identity Link:
WooCommerce Customer 52 → C1
```

---

### 8. Flaw Injection

Intentionally introduces business and data problems into scenarios so Business Brain's detection capabilities can be demonstrated.

**Features:**

* **Delivery Failure Injection**
  Creates abnormal delivery failure patterns for selected couriers, regions, products, or customer groups.

* **Campaign Performance Injection**
  Creates low ROAS, high spend, conversion decline, or poor downstream campaign outcomes.

* **Website Conversion Flaws**
  Introduces cart abandonment, checkout drop-off, poor conversion, or experience problems.

* **Support Flaw Injection**
  Generates increased unresolved conversations, slow response, repeated complaints, or excessive handovers.

* **Refund & Return Injection**
  Produces abnormal refund or return patterns.

* **Customer Retention Flaws**
  Simulates reduced repeat purchases or poor customer retention.

* **Product Performance Flaws**
  Generates underperforming products or product-specific operational problems.

* **Integration Flaws**
  Simulates failed syncs, invalid payloads, stale data, webhook failures, or provider errors.

* **Identity Flaws**
  Generates duplicate or conflicting external identities for testing Identity & Resolution behavior.

* **Cross-Domain Flaws**
  Creates problems whose effects appear across multiple domains.

Example:

```text
Injected Flaw

Courier:
Courier X

Region:
Gazipur

Normal Failure Rate:
8%

Injected Failure Rate:
19%

Expected Business Fact:
Delivery failure increased significantly.

Expected Business Issue:
HIGH_DELIVERY_FAILURE

Expected AI Direction:
Investigate Courier X performance
for Gazipur deliveries.
```

Flaws should be intentionally known before execution so detection can later be validated objectively.

---

### 9. Edge Cases

Provides controlled unusual or ambiguous data conditions that test whether Business Brain handles difficult situations correctly.

**Features:**

* **Missing Fields**
  Simulates provider records with optional or required data missing.

* **Duplicate Events**
  Sends the same webhook or source event multiple times to validate idempotency.

* **Out-of-Order Events**
  Generates events arriving in a different order from when they occurred.

* **Unknown Status Values**
  Simulates new or unsupported provider status values.

* **Duplicate Customers**
  Creates multiple provider identities that may represent the same customer.

* **Identity Conflicts**
  Creates conflicting email, phone, provider ID, or other identity information.

* **Anonymous-to-Known Transition**
  Simulates a website visitor who later identifies themselves during checkout or another interaction.

* **Partial Order Information**
  Generates incomplete order data followed by later updates.

* **Failed Payment Cases**
  Simulates payment attempts that fail before later succeeding or being abandoned.

* **Multiple Refunds**
  Tests partial and repeated refund behavior where supported.

* **Delivery Failure and Retry**
  Simulates failed delivery followed by another attempt.

* **Late Provider Events**
  Generates delayed provider data after newer events have already been processed.

* **Integration Failure Cases**
  Simulates authentication failure, rate limiting, timeout, malformed response, or stale synchronization.

* **Insufficient Analytical Evidence**
  Creates conditions where Business Intelligence should **not** produce a fact or issue because minimum evidence requirements are not satisfied.

The last case is especially important. A good prototype should demonstrate not only when Business Brain detects something, but also when it correctly refuses to over-interpret insufficient data.

---

### 10. Expected Results

Defines the known outcomes that should exist after a deterministic scenario has completed.

**Features:**

* **Expected Canonical Results**
  Defines the customers, products, orders, payments, campaigns, messages, shipments, calls, and other entities expected after processing.

* **Expected Identity Results**
  Defines which external identities should resolve to which canonical identities.

* **Expected Relationships**
  Specifies deterministic Business Relationships that should exist.

* **Expected Metrics**
  Defines metric values or acceptable ranges expected from the scenario.

* **Expected Facts**
  Specifies verified Business Facts that should be generated.

* **Expected Issues**
  Defines Business Issues that should be detected.

* **Expected Graph Structure**
  Defines important nodes, edges, and paths that should appear in the Business Graph.

* **Expected Knowledge Retrieval**
  Defines which policies or knowledge items should be retrievable for selected scenario questions.

* **Expected Recommendation Type**
  Defines the general recommendation category expected from AI without requiring exact natural-language output.

* **Expected Evidence**
  Specifies the facts, issues, relationships, or knowledge that should support a recommendation.

* **Expected Suggested Action**
  Defines structured actions that may reasonably result from the scenario.

* **Negative Expectations**
  Defines outcomes that must **not** occur, such as an invalid identity merge or unsupported Business Issue.

Example:

```text
Scenario:
GAZIPUR_COURIER_FAILURE

Expected Metric:
delivery_failure_rate = 18%

Expected Fact:
DELIVERY_FAILURE_INCREASED

Expected Issue:
HIGH_DELIVERY_FAILURE

Expected Graph Path:
Campaign A
→ Customer
→ Order
→ Shipment
→ Courier X

Expected Recommendation Type:
DELIVERY_OPTIMIZATION

Expected Evidence:
HIGH_DELIVERY_FAILURE
Courier X
Gazipur

Expected Suggested Action:
TEST_ALTERNATIVE_COURIER
```

---

### 11. Scenario Validation

Compares actual Business Brain output against the deterministic expectations defined by the scenario.

**Features:**

* **Canonical Entity Validation**
  Verifies that provider payloads produced the expected canonical entities.

* **Mapping Validation**
  Confirms important provider fields were normalized and mapped correctly.

* **Identity Validation**
  Verifies expected external-to-canonical identity links.

* **Relationship Validation**
  Confirms that expected deterministic Business Relationships were established.

* **Metric Validation**
  Compares calculated metric values with expected results.

* **Fact Validation**
  Confirms expected Business Facts were generated.

* **Issue Validation**
  Verifies that expected Business Issues were detected with appropriate classification.

* **Graph Validation**
  Confirms expected graph nodes, edges, and important paths exist.

* **Negative Validation**
  Verifies that relationships, facts, issues, or identity links that should not exist were not created.

* **Evidence Validation**
  Ensures facts, issues, and recommendations reference the expected supporting evidence.

* **Suggested Action Validation**
  Checks whether structured proposed actions align with the scenario expectation.

* **Validation Summary**
  Produces a clear pass/fail result for each expected outcome.

Example:

```text
Scenario Validation
────────────────────────────────

Canonical Customers          PASS
Canonical Orders             PASS
Identity Resolution          PASS
Business Relationships       PASS
Metrics                      PASS
Business Facts               PASS
Business Issues              PASS
Graph Projection             PASS
Recommendation Evidence      PASS

AI Recommendation Text       NOT EXACT-COMPARED

Overall Scenario             PASS
```

---

## Deterministic Validation Boundary

Not every system output should be validated in exactly the same way.

The deterministic pipeline can be strictly compared:

```text
Provider Payload
      ↓
Canonical Mapping
      ↓
Identity Resolution
      ↓
Business Relationships
      ↓
Metrics
      ↓
Facts
      ↓
Issues
      ↓
Graph Projection
```

These outputs should be reproducible and can therefore be validated against exact expected results where appropriate.

AI output is different:

```text
Verified Context
      ↓
LLM
      ↓
Natural Language
```

Exact wording may change even when the answer remains correct.

Therefore:

```text
STRICT VALIDATION

✓ Canonical entities
✓ Identity links
✓ Relationships
✓ Metric values
✓ Facts
✓ Issues
✓ Graph structure


STRUCTURED / SEMANTIC VALIDATION

✓ Recommendation type
✓ Referenced issue
✓ Supporting evidence
✓ Suggested action type
✓ Target entity
✓ General recommendation outcome


AVOID

✗ Exact AI paragraph comparison
✗ Exact summary wording
✗ Exact explanation wording
```

This keeps prototype validation deterministic without incorrectly treating an LLM as a deterministic string generator.

---

## End-to-End Simulation Flow

The complete prototype simulation should exercise as much of the actual Business Brain architecture as practical.

```text
Mock Scenario
      ↓
Deterministic Seed
      ↓
Scenario Configuration
      ↓
Mock Source Events
      ↓
Provider Payload Simulation
      ↓
Mock External Platforms
      ↓
Integrations
      ↓
Canonical Business Data
      ↓
Identity & Resolution
      ↓
Business Intelligence
      │
      ├── Relationships
      ├── Metrics
      ├── Facts
      └── Issues
      ↓
Business Graph
      ↓
Business Memory
      ↓
AI Intelligence
      │
      ├── Diagnosis
      ├── Recommendation
      └── Suggested Action
      ↓
Overview & Monitoring
      ↓
Business Operations
      ↓
Scenario Validation
```

This is significantly more valuable than directly inserting prepared results into dashboard tables because it demonstrates that the architecture actually produces the expected business understanding.

---

## Example Complete Scenario

Consider a prototype scenario named:

```text
META_GAZIPUR_DELIVERY_PROBLEM
```

### Simulated Source Activity

```text
Meta Ads
Campaign A
Spend +20%
        ↓
GA4
Website sessions +32%
        ↓
WooCommerce
Orders +25%
        ↓
Customers
Many new customers from Gazipur
        ↓
Steadfast / Mock Courier X
Most Gazipur orders assigned
        ↓
Delivery Failure
8% → 19%
        ↓
WooCommerce
Returns increase
        ↓
Payments
Refunded revenue increases
```

### Expected Identity Resolution

```text
WooCommerce Customer 52
WhatsApp +88017XXXXXXXX
GA4 Visitor V9281
Messenger PSID 81723

        ↓

Canonical Customer C1
```

### Expected Business Intelligence

```text
Metrics
────────────────────
Campaign Orders       +25%
Gazipur Orders        +41%
Delivery Failure      19%
Refund Rate           +23%


Facts
────────────────────
Gazipur delivery failure increased.
Courier X handles most failed shipments.
Campaign A generated increased order volume.


Issue
────────────────────
HIGH_DELIVERY_FAILURE

Severity:
HIGH
```

### Expected Business Graph

```text
Campaign A
    ↓
Session
    ↓
Customer C1
    ↓
Order O1024
    ↓
Payment P52
    ↓
Shipment S88
    ↓
Courier X
    ↓
Delivery Failure
    ↓
Refund
```

### Business Memory Context

```text
Business Goal:
Reduce delivery failure below 10%.

Delivery Policy:
Courier Y may be used for Gazipur.

Historical Decision:
Courier X performance in Gazipur
was previously reviewed.
```

### Expected AI Outcome

The exact wording is not predetermined.

However, the recommendation should conceptually be:

```text
Recommendation Type:
DELIVERY_OPTIMIZATION

Target:
Gazipur / Courier X

Evidence:
HIGH_DELIVERY_FAILURE
19% failure rate
Courier concentration
Historical delivery context

Suggested Action:
Test or increase allocation to
an alternative courier.
```

This demonstrates the complete Business Brain value proposition rather than simply showing disconnected mock dashboard values.

---

## Simulation vs Production Architecture

Prototype Simulation must remain clearly separated from production runtime logic.

```text
                 Business Brain
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
Production Inputs          Prototype Simulation
         │                         │
Real Providers             Mock Providers
Real Webhooks              Mock Events
Real API Payloads          Simulated Payloads
         │                         │
         └────────────┬────────────┘
                      ▼
              Integration Boundary
                      ↓
               Canonical Data
                      ↓
             Identity Resolution
                      ↓
          Business Intelligence
                      ↓
                 Graph / AI
```

The important point is that **the input changes, but the core Business Brain processing path should remain as similar as practical**.

This avoids creating a prototype that appears functional only because its final results were manually prepared.

---

## Prototype Simulation Is Not Random Mock Data

There is an important difference between ordinary mock data and Business Brain's simulation architecture.

```text
Random Mock Data
────────────────
Generate 100 customers
Generate 500 orders
Generate random campaigns
Generate random shipments

Purpose:
Fill UI screens.


Deterministic Business Simulation
─────────────────────────────────
Define business story
Generate correlated source activity
Inject known business problem
Process through actual architecture
Calculate deterministic intelligence
Build expected relationships
Detect expected issue
Generate grounded AI recommendation

Purpose:
Demonstrate Business Brain.
```

The second approach is required because Business Brain's main innovation is not displaying business records; it is **connecting fragmented business activity and turning it into understandable, evidence-backed intelligence**.

---

## Scenario Validation Example

A final scenario report could look like:

```text
Scenario
META_GAZIPUR_DELIVERY_PROBLEM

Seed
75001

────────────────────────────────────

SOURCE EVENTS
PASS
1,482 events generated

CANONICAL MAPPING
PASS
Customers: 120
Orders: 318
Shipments: 318

IDENTITY RESOLUTION
PASS
Expected Links: 164
Resolved: 164

BUSINESS RELATIONSHIPS
PASS
Expected: 1,274
Generated: 1,274

BUSINESS METRICS
PASS

BUSINESS FACTS
PASS
3 / 3 expected facts detected

BUSINESS ISSUES
PASS
HIGH_DELIVERY_FAILURE detected

BUSINESS GRAPH
PASS
Expected critical paths found

AI RECOMMENDATION
PASS
Type: DELIVERY_OPTIMIZATION
Evidence: VALID

SUGGESTED ACTION
PASS
TEST_ALTERNATIVE_COURIER

────────────────────────────────────

OVERALL RESULT
PASS
```

Such a report provides concrete evidence that the prototype is producing the expected business understanding.

---

## Domain Boundary

The **Prototype Simulation** domain answers:

**“How can we reproducibly demonstrate and validate Business Brain without requiring every real external platform to be connected?”**

It does not own canonical business entities; those belong to **Business Data**.

It does not perform real provider integrations; those belong to **Integrations**.

It does not perform authoritative identity resolution; that belongs to **Identity & Resolution**.

It does not calculate production business intelligence itself; that belongs to **Business Intelligence**.

It does not independently build authoritative business relationships or graphs.

It does not replace AI Intelligence.

Instead, it supplies **controlled inputs and known expectations** to the actual architecture.

Its primary inputs are:

**Scenario Definitions + Configuration + Deterministic Seeds + Flaw Definitions + Edge Cases**

Its primary outputs are:

**Mock Source Events + Provider Payloads + Expected Results + Validation Reports**

The overall architecture is:

**Scenario → Deterministic Mock Platforms → Real Core Processing Path → Expected Results → Validation**

The core principle is:

**The prototype should mock the external world, not mock Business Brain's intelligence.**

External APIs can be simulated, provider events can be generated, and business scenarios can be synthetic—but canonical mapping, identity resolution, deterministic relationships, metrics, facts, issues, graph construction, evidence retrieval, and grounded AI behavior should demonstrate the actual core idea of Business Brain.
