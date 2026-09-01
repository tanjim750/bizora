# Business Operations

## Description

The **Business Operations** domain is the user-facing operational layer of Business Brain. It turns canonical business data, resolved identities, verified intelligence, graph context, and AI assistance into practical workflows that business users can inspect, manage, and act on.

This domain does **not** become a second source of truth. Instead, it provides operational projections and interfaces over underlying domains such as Business Data, Business Intelligence, Business Graph, and AI Intelligence. Its purpose is to help users understand the business state and perform day-to-day actions from one unified environment.

---

## Features

### 1. Business Overview

Provides a consolidated operational view of the most important business activity, current performance, active issues, and recommendations.

**Features:**

* **Cross-Domain Summary**
  Brings together sales, customers, marketing, website, support, delivery, payments, and calling information into one operational view.

* **Key Business Indicators**
  Displays important metrics such as revenue, orders, conversion rate, delivery success, campaign performance, and support workload.

* **Active Business Issues**
  Surfaces open Business Intelligence issues that currently require attention.

* **Recent Business Activity**
  Shows important recent events such as orders, payments, failed deliveries, customer conversations, and calls.

* **Recommendation Summary**
  Displays relevant AI-generated recommendations that are supported by verified evidence.

* **Operational Drill-Down**
  Allows users to move from a summary metric or issue into the underlying customer, order, campaign, shipment, or other operational context.

---

### 2. Customer 360

Provides a unified operational view of a customer across all connected business channels and domains.

**Features:**

* **Unified Customer Profile**
  Displays canonical customer information, contacts, tags, status, and relevant profile details.

* **Cross-Source Identity Context**
  Shows the resolved external identities associated with the same canonical customer.

* **Order History**
  Displays the customer's previous and active orders.

* **Payment History**
  Shows payment, refund, and transaction-related activity associated with the customer.

* **Conversation History**
  Brings together support conversations and messages across supported communication channels.

* **Call History**
  Displays incoming and outgoing calls associated with the customer.

* **Delivery History**
  Shows shipments, successful deliveries, failures, returns, and courier activity.

* **Website Journey**
  Displays known website sessions, product views, checkout events, and conversions associated with the customer.

* **Marketing Context**
  Shows campaign touchpoints and attribution relationships where verified.

* **Customer Timeline**
  Presents important customer activity chronologically across all supported domains.

* **Customer Graph View**
  Allows users to explore the customer's connected Business Graph journey.

* **AI Customer Context**
  Enables support or business users to ask AI questions about the customer using grounded customer context.

---

### 3. Product Operations

Provides an operational interface for viewing and managing canonical products and their connected business performance.

**Features:**

* **Product Catalog View**
  Displays canonical products, SKUs, categories, variants, prices, inventory, and statuses.

* **Product Variant Management**
  Provides access to product variations and their attributes.

* **External Mapping View**
  Shows how a canonical product maps to products in external commerce platforms.

* **Product Performance Context**
  Displays verified sales, revenue, conversion, and other Business Intelligence metrics.

* **Product Order History**
  Shows orders containing the selected product.

* **Product Customer Context**
  Displays customers associated with the product through purchases and other verified relationships.

* **Product Marketing Context**
  Shows campaigns and marketing outcomes related to the product.

* **Product Delivery Context**
  Surfaces delivery failures, returns, and courier outcomes associated with orders containing the product.

* **Product Support Context**
  Displays related customer support issues or conversations when a verified relationship exists.

* **Product Graph View**
  Provides a graph-based journey showing how the product connects across marketing, customers, orders, and fulfillment.

---

### 4. Order Operations

Provides a unified operational interface for managing and investigating the complete order lifecycle.

**Features:**

* **Order List**
  Displays canonical orders with customer, amount, status, source, and timing information.

* **Order Detail View**
  Provides complete order information including items, totals, customer, and external references.

* **Order Status Management**
  Shows and, where authorized, allows operational handling of order status transitions.

* **Order Lifecycle History**
  Displays historical order status changes in chronological order.

* **Customer Context**
  Links directly to the customer associated with the order.

* **Payment Context**
  Displays related payments, payment status, and refunds.

* **Shipment Context**
  Shows courier information, tracking status, delivery events, failures, and returns.

* **Conversation Context**
  Displays support conversations linked with the order.

* **Call Context**
  Shows order-related calls such as confirmation or delivery calls.

* **Campaign Attribution Context**
  Displays verified campaign or website-session relationships associated with the order.

* **Order Graph View**
  Presents the full order journey across customer, product, payment, campaign, support, and delivery.

---

### 5. Payment Operations

Provides operational visibility into payments, refunds, and order-related financial activity.

**Features:**

* **Payment List**
  Displays canonical payment records with customer, order, amount, method, status, and source information.

* **Payment Detail View**
  Shows transaction references, payment method, amount, currency, timestamps, and provider metadata.

* **Order Mapping**
  Displays the order associated with each payment.

* **Customer Mapping**
  Provides direct access to the customer associated with a payment.

* **Payment Status Tracking**
  Shows whether a payment is pending, authorized, paid, failed, cancelled, partially refunded, or refunded.

* **Refund Management View**
  Displays refund amounts, reasons, statuses, and related payment information.

* **Payment Failure Investigation**
  Allows users to inspect failed payment records and relevant source metadata.

* **Financial Timeline**
  Shows payment and refund activity chronologically within the related order or customer journey.

---

### 6. Unified Inbox

Provides one operational inbox for customer communication coming from multiple external messaging channels.

**Features:**

* **Multi-Channel Inbox**
  Combines conversations from Messenger, WhatsApp, Instagram, Telegram, Website Chat, and future channels.

* **Conversation List**
  Displays active and historical conversations with customer, channel, status, priority, assignment, and last-message information.

* **Conversation View**
  Shows complete canonical message history independent of the originating communication platform.

* **Customer Context Panel**
  Displays relevant customer, order, payment, and delivery information alongside the conversation.

* **Attachment Support**
  Allows users to view supported message images, audio, video, files, and documents.

* **Message Delivery State**
  Displays sent, delivered, failed, and read information where supported.

* **Internal Notes**
  Allows support users to maintain internal information that is not sent to the customer.

* **AI Suggested Replies**
  Provides grounded suggested responses using conversation, customer, order, and policy context.

* **Conversation Search & Filtering**
  Allows inbox filtering by channel, status, priority, customer, assignment, and time.

---

### 7. Support Queue

Organizes conversations that require support attention and helps teams prioritize operational workload.

**Features:**

* **Open Conversation Queue**
  Displays unresolved customer conversations that require action.

* **Priority-Based Queueing**
  Sorts and filters conversations using priorities such as low, normal, high, and urgent.

* **Assignment-Based Views**
  Allows agents or teams to view only conversations assigned to them.

* **Unassigned Queue**
  Identifies conversations that have not yet been assigned.

* **Pending Conversations**
  Separates conversations waiting on a customer, agent, or external event where appropriate.

* **Overdue Support Detection**
  Surfaces conversations that exceed expected response or resolution periods.

* **AI Escalation Signals**
  Highlights conversations where AI or support rules indicate that human attention is required.

* **Queue Metrics**
  Displays support volume, unresolved count, response delays, and other operational support measures.

---

### 8. Conversation Assignment

Controls who currently owns or handles a support conversation.

**Features:**

* **Agent Assignment**
  Assigns a conversation to a specific support agent.

* **Team Assignment**
  Assigns conversations to a team or support group where team structures are available.

* **AI Assignment**
  Allows suitable conversations to be owned temporarily by AI support.

* **Assignment History**
  Preserves previous ownership changes for audit and support context.

* **Reassignment**
  Allows conversations to move from one agent or team to another.

* **Assignment Release**
  Removes current ownership and returns the conversation to an available queue.

* **Automatic Assignment Hooks**
  Provides the operational foundation for later routing rules such as workload, category, priority, or skill-based assignment.

* **Assignment Metadata**
  Records who assigned the conversation, when it was assigned, and why where available.

---

### 9. AI ↔ Human Handover

Manages transitions between AI-supported customer service and human agents without losing conversation context.

**Features:**

* **AI-to-Human Escalation**
  Transfers conversations to human support when AI cannot safely or confidently continue.

* **Human-to-AI Return**
  Allows suitable conversations to return to AI handling after human intervention.

* **Handover Reason**
  Records why a transfer occurred, such as policy restriction, low confidence, customer request, or complex issue.

* **Conversation Summary**
  Provides the receiving agent or AI with a concise summary of the previous interaction.

* **Context Preservation**
  Maintains relevant customer, order, payment, delivery, and policy information during handover.

* **Ownership Update**
  Synchronizes the current support assignment with the handover state.

* **Customer Transparency**
  Supports communication that informs the customer when they are being transferred where appropriate.

* **Handover History**
  Records AI-to-human and human-to-AI transitions for later support analysis.

---

### 10. Marketing Operations

Provides an operational interface for reviewing campaign activity, performance, issues, and recommended actions.

**Features:**

* **Campaign List**
  Displays canonical campaigns across supported advertising platforms.

* **Campaign Detail View**
  Shows campaign objective, status, budget, spend, conversions, and related provider information.

* **Campaign Metrics**
  Displays standardized metrics such as impressions, clicks, CTR, CPC, CPM, conversions, and ROAS.

* **Attributed Revenue View**
  Shows revenue and orders deterministically attributed to a campaign.

* **Campaign Performance Trends**
  Displays metric snapshots across selected analytical periods.

* **Campaign Issue Indicators**
  Highlights active Business Intelligence issues such as low ROAS or conversion decline.

* **Cross-Domain Outcome View**
  Shows downstream delivery, refund, retention, or customer outcomes associated with campaign-generated orders.

* **AI Marketing Recommendations**
  Displays grounded campaign optimization suggestions and their supporting evidence.

* **Suggested Marketing Actions**
  Allows users to review proposed actions such as pausing or adjusting campaigns.

* **Approval Flow**
  Supports explicit approval before configured marketing actions are executed.

---

### 11. Website Performance

Provides an operational and analytical view of website traffic, behavior, conversion, and user-experience signals.

**Features:**

* **Traffic Overview**
  Displays visitor, session, page-view, and acquisition activity.

* **Traffic Source Performance**
  Compares organic, paid, direct, social, referral, and other acquisition sources.

* **Conversion Funnel View**
  Shows progression through product view, add-to-cart, checkout, and purchase.

* **Cart Abandonment View**
  Identifies where users add products to carts but fail to complete checkout.

* **Checkout Drop-Off View**
  Highlights sessions that begin checkout but do not convert.

* **Landing Page Performance**
  Compares landing pages based on engagement and conversion.

* **Product Behavior View**
  Shows product views, cart activity, and purchase outcomes.

* **Device & Browser Performance**
  Compares behavior and conversion across devices, browsers, and operating systems.

* **Experience Signals**
  Surfaces available rage clicks, dead clicks, quick backs, errors, and performance issues.

* **Website Issues**
  Displays Business Intelligence findings related to conversion drops, abandonment, or abnormal behavior.

* **AI Website Recommendations**
  Provides grounded suggestions for areas requiring investigation or optimization.

---

### 12. Delivery Operations

Provides an operational interface for managing and investigating shipments across connected courier providers.

**Features:**

* **Shipment List**
  Displays active and historical shipments with provider, order, customer, tracking code, status, and COD information.

* **Shipment Detail View**
  Shows recipient information, delivery charges, COD amount, status, and provider metadata.

* **Tracking Timeline**
  Displays shipment events such as submitted, picked up, in transit, delivery attempt, delivered, failed, and returned.

* **Order Context**
  Links each shipment to the corresponding canonical order.

* **Customer Context**
  Provides access to the customer associated with a shipment.

* **Failed Delivery Queue**
  Surfaces unsuccessful deliveries requiring operational attention.

* **Return Tracking**
  Displays shipments currently returning or already returned.

* **Courier Performance Context**
  Shows verified courier performance metrics such as success, failure, and return rates.

* **Regional Delivery Context**
  Highlights regions associated with abnormal delivery performance.

* **AI Delivery Recommendations**
  Displays evidence-backed suggestions such as investigating or testing alternative courier providers.

* **Suggested Courier Actions**
  Allows supported operational actions to be reviewed before execution.

---

### 13. Call Operations

Provides an operational interface for viewing and managing incoming and outgoing business calls.

**Features:**

* **Call List**
  Displays calls with customer, direction, caller, receiver, status, duration, and timestamps.

* **Call Detail View**
  Shows complete call metadata and related business context.

* **Incoming Call History**
  Provides visibility into customer-initiated calls.

* **Outgoing Call History**
  Displays business-initiated, automated, and agent-initiated calls.

* **Call Status Tracking**
  Shows lifecycle states such as ringing, answered, completed, missed, busy, and failed.

* **Call Event Timeline**
  Displays detailed events such as answer, hold, transfer, completion, and failure.

* **Recording Access**
  Provides access to available call recordings where permitted.

* **Transcript View**
  Displays generated call transcripts when available.

* **AI Call Summary**
  Shows concise summaries of long call transcripts.

* **Customer Context**
  Connects the call with the resolved canonical customer.

* **Order Context**
  Shows related orders when calls concern confirmation, cancellation, delivery, or support.

* **Conversation Context**
  Connects calls with the relevant support conversation where appropriate.

---

## Operational Projection Model

Business Operations should not create duplicate copies of domain state merely for UI convenience.

The preferred structure is:

```text
Business Data
      +
Identity & Resolution
      +
Business Intelligence
      +
Business Graph
      +
AI Intelligence
      ↓
Operational Queries / Projections
      ↓
Business Operations
```

For example, **Customer 360** is not a separate customer database.

It is a projection over:

```text
Customer
   +
Resolved Identities
   +
Orders
   +
Payments
   +
Website Sessions
   +
Campaign Relationships
   +
Conversations
   +
Calls
   +
Shipments
   +
Business Facts
   +
Graph Context
```

The same principle applies to Order Operations, Marketing Operations, Delivery Operations, and other operational interfaces.

---

## Example Unified Operational Flow

A customer may appear in the system through several separate operational events:

```text
Meta Campaign
      ↓
Website Visit
      ↓
Product View
      ↓
Order
      ↓
Payment
      ↓
Shipment
      ↓
Delivery Failure
      ↓
WhatsApp Message
      ↓
Unified Inbox
      ↓
AI Support
      ↓
Human Handover
      ↓
Support Resolution
```

Business Operations allows users to work with this journey from practical interfaces such as:

```text
Business Overview

Customer 360

Order Operations

Unified Inbox

Delivery Operations

Call Operations
```

without requiring users to understand the underlying domain architecture.

---

## Business Operations vs Business Data

The distinction between these domains is important.

```text
Business Data
-------------
Canonical source of operational state.

Examples:
Customer
Order
Payment
Conversation
Shipment
Call


Business Operations
-------------------
User-facing workflow and projection.

Examples:
Customer 360
Order management screen
Unified Inbox
Failed-delivery queue
Call history
```

An order remains owned by **Order Core / Business Data** even when it is modified through the Order Operations interface.

Similarly, conversations remain canonical Customer Support data even though users interact with them through the Unified Inbox.

---

## Business Operations vs Business Intelligence

Business Operations presents analytical findings but should not independently calculate or establish authoritative business conclusions.

For example:

```text
Business Intelligence

Issue:
HIGH_DELIVERY_FAILURE

Evidence:
Gazipur failure rate = 18%


Business Operations

Delivery Operations:
Displays a warning on the
Gazipur shipment queue.

Business Overview:
Shows the issue as HIGH severity.

Customer 360:
Shows affected shipments.
```

The analytical conclusion remains owned by Business Intelligence.

---

## Business Operations vs AI Intelligence

AI Intelligence generates explanations, summaries, recommendations, and suggested actions.

Business Operations provides the interface through which users interact with those outputs.

For example:

```text
AI Intelligence
      ↓
Recommendation:
"Test Courier Y for Gazipur."

      ↓

Business Operations
      ↓
Delivery Operations
      ↓
Review Recommendation
      ↓
Approve Suggested Action
      ↓
Integration
      ↓
Courier Provider
```

This keeps AI reasoning, user authorization, and operational execution clearly separated.

---

## Domain Boundary

The **Business Operations** domain answers:

**“How does a business user inspect, manage, and act on everything Business Brain knows?”**

It does not replace the source-of-truth domains underneath it.

Its primary inputs are:

**Business Data + Identity & Resolution + Business Intelligence + Business Graph + AI Intelligence**

Its primary outputs are:

**User workflows + operational views + approved actions**

The overall architecture is:

**Canonical Business State → Intelligence & Context → Operational Projection → User Decision → Approved Operation → Integration Execution**

The core principle is:

**Business Operations is where Business Brain becomes usable for day-to-day work, while the underlying domains remain authoritative for data, identity, intelligence, graph structure, and AI reasoning.**
