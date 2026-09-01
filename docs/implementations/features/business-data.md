# Business Data

## Description

The **Business Data** domain is the canonical data foundation of Business Brain. It converts business information coming from different platforms and operational channels into consistent, platform-independent business entities.

The domain provides the structured business state required by downstream systems such as **Identity & Resolution, Business Intelligence, Business Graph, Business Memory, AI Intelligence, and Business Operations**. Each subdomain owns the canonical representation and lifecycle of its respective business entity.

---

## Features

### 1. Product

Provides a unified representation of products regardless of where they originate, such as WooCommerce, Shopify, custom websites, or imported datasets.

**Features:**

* **Canonical Product Model**
  Maintains a platform-independent product structure containing common product information such as name, SKU, description, category, price, inventory, status, and images.

* **Product Variants**
  Represents variations of a product such as size, color, weight, pack, or other configurable attributes while maintaining their relationship with the parent product.

* **Product Normalization**
  Converts provider-specific product payloads into the canonical Product model so downstream systems do not depend on individual platform schemas.

* **Product Validation**
  Validates required fields, supported values, identifiers, pricing information, and structural consistency before product data enters the canonical layer.

* **External Product References**
  Maps canonical products and variants to their corresponding external platform identifiers, allowing the same product to be traced across multiple systems.

* **Product Deduplication**
  Detects duplicate or repeated product records using deterministic identifiers and matching rules before creating unnecessary canonical records.

* **Source Metadata Preservation**
  Retains provider-specific information that does not belong directly in the canonical model but may still be useful for auditing, debugging, or later processing.

* **Product Query & Lookup**
  Provides utilities for finding, filtering, matching, and retrieving canonical products using identifiers such as product ID, SKU, category, status, or external reference.

---

### 2. Customer

Provides a unified canonical representation of customers collected from commerce platforms, communication channels, websites, support interactions, and other business systems.

**Features:**

* **Canonical Customer Model**
  Stores the core platform-independent customer representation including name, status, customer type, notes, and other normalized customer information.

* **Customer Profile**
  Maintains structured customer information that can later power Customer 360, support operations, analytics, and AI-assisted interactions.

* **Customer Contacts**
  Stores customer communication identifiers such as email addresses, phone numbers, and WhatsApp numbers along with normalized and primary-contact information.

* **Contact Normalization**
  Standardizes values such as phone numbers and email addresses so equivalent contact information can be consistently compared and queried.

* **Customer Validation**
  Validates customer attributes and contact information before accepting them into the canonical Customer layer.

* **Customer Status Management**
  Maintains operational customer states such as active, inactive, or blocked.

* **Customer Tags**
  Supports business classifications such as `VIP`, `REPEAT_BUYER`, `HIGH_VALUE`, `DELIVERY_RISK`, and `NEW_CUSTOMER`.

* **External Customer References**
  Maintains provider-specific customer identifiers while keeping the canonical customer independent from individual external platforms.

* **Customer Timeline**
  Builds a chronological view of important customer activities such as orders, payments, conversations, calls, website activity, shipment failures, and campaign conversions.

* **Customer Query & Lookup**
  Provides reusable mechanisms for finding and filtering customers using canonical identifiers, contact information, tags, status, or source references.

> Cross-source identity resolution is intentionally **not** owned by Customer. Determining whether identities from WooCommerce, Messenger, WhatsApp, GA4, and other systems represent the same real-world customer belongs to the **Identity & Resolution** domain.

---

### 3. Order

Owns the canonical representation and lifecycle of customer orders regardless of which commerce platform or business system originally created them.

**Features:**

* **Canonical Order Model**
  Represents orders using a consistent structure containing customer, status, currency, totals, timestamps, source information, and external references.

* **Order Items**
  Stores the products and variants purchased within an order together with quantity, unit price, discount, and calculated item totals.

* **Order Item Snapshots**
  Preserves important product information such as product name and SKU at the time of purchase so historical orders remain accurate even if the product changes later.

* **Order Normalization**
  Converts provider-specific orders from systems such as WooCommerce, Shopify, or custom commerce systems into the canonical Order model.

* **Order Validation**
  Ensures order structure, totals, items, identifiers, currency, and other required fields are valid before canonical processing.

* **Order Deduplication**
  Prevents repeated webhooks, syncs, or imports from creating duplicate canonical orders.

* **Order Status Management**
  Supports lifecycle states such as `PENDING`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `RETURNED`, and `REFUNDED`.

* **Order Lifecycle History**
  Records order status transitions over time, including where the transition originated and when it occurred.

* **Customer & Product References**
  Connects orders with their canonical customers, products, and product variants for downstream analysis.

* **Order Totals**
  Maintains subtotal, discounts, shipping charges, taxes, and final order totals in a consistent representation.

* **External Order Mapping**
  Preserves the originating provider and external order identifier so canonical orders can be traced back to their source systems.

---

### 4. Payment

Standardizes payment and refund information associated with business transactions and connects financial activity with canonical customers and orders.

**Features:**

* **Canonical Payment Model**
  Provides a normalized representation containing transaction references, amount, currency, payment method, status, customer, order, and provider information.

* **Payment Normalization**
  Converts different gateway, commerce platform, COD, or imported payment representations into a common Payment structure.

* **Payment Validation**
  Validates transaction amounts, currencies, payment methods, references, and required relationships before accepting payment data.

* **Payment Method Management**
  Supports methods such as cash, COD, card, mobile banking, bank transfer, wallet, and other payment mechanisms.

* **Payment Status Management**
  Tracks states such as `PENDING`, `AUTHORIZED`, `PAID`, `FAILED`, `CANCELLED`, `PARTIALLY_REFUNDED`, and `REFUNDED`.

* **Payment–Order Mapping**
  Connects payments with their associated canonical orders, enabling revenue and payment-performance analysis.

* **Payment–Customer Mapping**
  Associates transactions with canonical customers when the customer is known.

* **Refund Management**
  Represents full and partial refunds together with refund amount, reason, status, external reference, and completion information.

* **External Payment References**
  Preserves payment-provider transaction identifiers for reconciliation and traceability.

---

### 5. Communication

Provides the canonical messaging layer between Business Brain and external communication platforms. Its responsibility is message connectivity and normalization rather than support workflow management.

**Features:**

* **Canonical Message Model**
  Represents incoming and outgoing messages using a common format independent of the originating communication platform.

* **Channel Abstraction**
  Provides a consistent communication contract across Messenger, WhatsApp, Instagram, Telegram, Website Chat, and future channels.

* **Incoming Message Processing**
  Accepts messages from connected platforms and transforms them into canonical messages.

* **Outgoing Message Processing**
  Converts canonical outgoing messages into the format required by the target communication provider.

* **Message Direction**
  Distinguishes incoming customer communication from outgoing business, agent, AI, or system communication.

* **Message Types**
  Supports text, image, video, audio, file, location, and other supported message formats.

* **Message Attachments**
  Stores structured references to files and media associated with communication messages.

* **Delivery Status**
  Tracks transport states such as pending, sent, delivered, and failed.

* **Read Status**
  Maintains message read information when supported by the connected communication provider.

* **External Message References**
  Preserves provider-specific message and conversation identifiers for synchronization and traceability.

* **Communication Connectors**
  Supports communication through providers such as Messenger, WhatsApp, Instagram, Telegram, and Website Chat through the Integration layer.

> Unified Inbox, support ownership, assignment, prioritization, and AI-to-human handover belong to **Customer Support**, not Communication.

---

### 6. Customer Support

Manages customer service conversations and operational support workflows on top of the canonical Communication layer.

**Features:**

* **Support Conversations**
  Groups related customer messages and interactions into persistent support conversations.

* **Unified Conversation History**
  Provides a channel-independent history of communication so support interactions can be viewed consistently regardless of their source.

* **Unified Inbox Foundation**
  Supplies the canonical conversation state required to present messages from multiple communication channels in one operational inbox.

* **Conversation Participants**
  Tracks customers, agents, AI assistants, and other participants associated with a conversation.

* **Support Queue**
  Organizes active conversations that require human or automated support attention.

* **Conversation Assignment**
  Assigns conversations to agents, teams, or AI systems and preserves assignment history.

* **Conversation Ownership**
  Identifies who currently has responsibility for handling a customer conversation.

* **AI-to-Human Handover**
  Allows AI-managed conversations to be transferred to a human agent when escalation or human judgment is required.

* **Human-to-AI Handover**
  Allows suitable conversations to return to AI handling when automated support can continue safely.

* **Internal Notes**
  Allows agents or AI systems to attach internal context to conversations without sending that information to the customer.

* **Conversation Status**
  Tracks operational states such as `OPEN`, `PENDING`, `RESOLVED`, and `CLOSED`.

* **Conversation Priority**
  Supports prioritization such as `LOW`, `NORMAL`, `HIGH`, and `URGENT`.

* **Resolution Tracking**
  Records when and how conversations are resolved for support-performance analysis.

* **Support Timeline**
  Preserves important conversation, assignment, handover, and resolution events chronologically.

* **Suggested Reply Context**
  Provides structured conversation, customer, order, and business context that downstream AI systems can use to generate grounded response suggestions.

---

### 7. Marketing

Provides a canonical representation of marketing campaigns and their performance across different advertising and marketing platforms.

**Features:**

* **Canonical Campaign Model**
  Standardizes campaign information such as name, platform, objective, status, budget, currency, and active period.

* **Campaign Normalization**
  Converts platform-specific campaign structures into a consistent model that Business Intelligence can analyze uniformly.

* **Campaign Validation**
  Ensures required campaign attributes, identifiers, status, budget, and related information are structurally valid.

* **Ad Account Mapping**
  Associates campaign data with the corresponding connected advertising account or integration.

* **Campaign Hierarchy Support**
  Provides the domain foundation for campaign, ad set, ad, and creative relationships where supported by external platforms.

* **Audience Information**
  Preserves targeting and audience-related information required for campaign analysis and optimization.

* **Campaign Metrics**
  Normalizes impressions, reach, clicks, spend, conversions, conversion value, CTR, CPC, CPM, ROAS, and related performance indicators.

* **Campaign Conversions**
  Connects marketing activity with conversions such as purchases, leads, signups, checkout events, and other business outcomes.

* **Attribution Inputs**
  Captures the campaign, customer, order, and website-session information required by Business Intelligence to perform deterministic attribution.

* **Retargeting Context**
  Maintains customer and behavioral signals that can later be used to identify retargeting opportunities.

* **Source Metadata**
  Preserves provider-specific campaign information that cannot be represented directly in the canonical model.

* **Marketing Platform Support**
  Supports normalized data from platforms such as Meta Ads, Google Ads, TikTok Ads, and future marketing providers.

---

### 8. Website Behavior

Captures and normalizes how visitors interact with a business website, providing behavioral data for journey analysis, conversion analysis, attribution, and business diagnosis.

**Features:**

* **Website Visitors**
  Represents persistent website visitors independently of individual browsing sessions.

* **Anonymous Visitors**
  Supports visitors who have not yet been associated with a known canonical customer.

* **Known Customer Linking**
  Allows website visitors and sessions to later reference a customer after deterministic identity resolution.

* **Website Sessions**
  Groups visitor activity into browsing sessions containing source, device, location, landing page, exit page, and timing information.

* **Page Views**
  Captures which pages visitors view and when those interactions occur.

* **Product Views**
  Connects website browsing behavior with canonical products.

* **Behavior Events**
  Supports events such as search, add-to-cart, remove-from-cart, checkout start, purchase, form submission, and other business-relevant interactions.

* **Conversion Events**
  Captures important outcomes such as checkout completion, purchase, signup, or lead submission.

* **Traffic Source & UTM Tracking**
  Preserves campaign and acquisition parameters including source, medium, campaign, term, and content.

* **Visitor Journey**
  Provides ordered behavioral events that can later be transformed into customer and conversion journeys.

* **Device & Browser Context**
  Captures device type, operating system, browser, and related technical context.

* **Performance Signals**
  Supports website latency, loading, error, and other performance-related behavioral signals.

* **Experience Signals**
  Supports behavioral indicators such as rage clicks, dead clicks, quick backs, and other signs of user friction.

* **Analytics Integration**
  Accepts normalized behavioral data originating from sources such as GA4, Microsoft Clarity, custom website tracking, or other analytics systems.

---

### 9. Courier

Manages the canonical shipment and delivery lifecycle while abstracting differences between external courier providers.

**Features:**

* **Canonical Shipment Model**
  Provides a unified shipment representation containing order, customer, courier provider, tracking information, delivery status, charges, and COD amount.

* **Shipment Submission**
  Represents the creation and submission of a delivery request to an external courier provider.

* **Shipment Status Management**
  Tracks states such as `PENDING`, `SUBMITTED`, `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `FAILED`, `RETURNING`, `RETURNED`, and `CANCELLED`.

* **Shipment Tracking**
  Preserves courier tracking codes and provider references required to follow a shipment throughout its lifecycle.

* **Shipment Events**
  Records detailed delivery events such as pickup, transit, delivery attempts, failures, successful delivery, and returns.

* **Delivery Failure Tracking**
  Captures failed delivery attempts and related metadata for later delivery-performance and customer-risk analysis.

* **Return Management**
  Tracks return initiation, return transit, and completed return states.

* **Shipment Cancellation**
  Represents cancellation of courier requests where supported by the provider.

* **Delivery Charge Tracking**
  Stores normalized courier charges associated with shipments.

* **COD Tracking**
  Preserves cash-on-delivery amounts associated with a shipment for downstream payment and delivery analysis.

* **Order & Customer Mapping**
  Connects shipment activity with canonical orders and customers.

* **Courier Provider Support**
  Provides a common model for integrations such as Steadfast, RedX, Pathao, CarryBee, and future courier providers.

---

### 10. Calling

Provides a canonical representation of business phone calls and connects voice interactions with customers, conversations, orders, and other business context.

**Features:**

* **Canonical Call Model**
  Standardizes incoming and outgoing calls with caller, receiver, direction, status, timestamps, duration, recording, and source information.

* **Incoming Calls**
  Captures customer-initiated calls received through connected calling platforms.

* **Outgoing Calls**
  Represents calls initiated by the business, agent, automation, or calling platform.

* **Callback Support**
  Provides the data foundation for requested or scheduled callbacks associated with customer interactions.

* **Call Status Management**
  Tracks lifecycle states such as initiated, ringing, answered, completed, missed, busy, failed, and cancelled.

* **Call Events**
  Records detailed lifecycle events including ringing, answering, holding, transfer, completion, and failure.

* **Call Recording**
  Stores references to call recordings when recordings are available and permitted.

* **Call Transcription**
  Stores speech-to-text transcripts generated from recorded or live calls.

* **Call Summary**
  Maintains generated summaries of calls for faster support review and downstream AI context.

* **Customer Mapping**
  Associates calls with canonical customers when caller or receiver identity can be resolved.

* **Conversation Mapping**
  Connects calls with related support conversations to provide a unified communication history.

* **Order Mapping**
  Associates calls with relevant orders when a call concerns an order, confirmation, delivery, cancellation, or support issue.

* **Calling Platform Integration**
  Provides the canonical data layer for calling systems such as Dialyra while keeping downstream Business Brain components provider-independent.

---

## Domain Boundary

The **Business Data** domain owns canonical business entities and their domain-specific lifecycle. It does not own cross-source identity resolution, analytical conclusions, graph projections, long-term business knowledge, or AI reasoning.

The downstream flow is:

**External Platforms → Integrations → Business Data → Identity & Resolution → Business Intelligence → Business Graph / Business Memory → AI Intelligence → Business Operations**

This separation ensures that Business Brain can ingest information from many external platforms while maintaining one consistent and reliable representation of the business.
