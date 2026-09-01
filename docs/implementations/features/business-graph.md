# Business Graph

## Description

The **Business Graph** domain provides a connected graph representation of Business Brain's canonical entities and verified relationships. It transforms already-resolved business data into nodes and edges so customer journeys, product flows, campaign outcomes, orders, payments, conversations, calls, and deliveries can be explored as connected business activity rather than isolated records.

The graph is a **projection layer, not a source of truth**. Authoritative entities remain in Business Data, identity decisions remain in Identity & Resolution, and verified relationships remain in Business Intelligence. Business Graph exposes those verified structures for traversal, visualization, investigation, and AI context.

---

## Features

### 1. Graph Nodes

Represents canonical business entities as nodes that can participate in graph relationships and journey views.

**Features:**

* **Canonical Entity Nodes**
  Creates graph representations for customers, products, orders, payments, campaigns, sessions, conversations, messages, calls, shipments, and other supported entities.

* **Canonical Identity Association**
  Links graph nodes with canonical identities where identity resolution is applicable, preserving the connection between graph data and the Identity & Resolution layer.

* **Node Classification**
  Classifies each graph node by entity and node type so graph queries can distinguish customers, products, orders, campaigns, and other business objects.

* **Node Labels**
  Provides human-readable labels that make graph visualizations easier to understand without replacing canonical entity data.

* **Node Properties**
  Stores graph-oriented metadata useful for visualization, traversal, filtering, or context without copying the complete canonical entity into the graph.

* **Entity Traceability**
  Preserves the original canonical entity type and identifier so every graph node can be traced back to its source-of-truth record.

* **Node Activity Tracking**
  Supports first-seen and last-seen information for entities whose graph relevance changes over time.

---

### 2. Graph Edges

Represents verified relationships between graph nodes and provides the structural connections required for graph traversal.

**Features:**

* **Relationship-Based Edges**
  Creates graph edges from established business relationships such as customer-to-order, order-to-product, campaign-to-conversion, and order-to-shipment.

* **Directional Relationships**
  Preserves the logical direction of relationships, for example `CUSTOMER → PLACED_ORDER → ORDER`.

* **Relationship Types**
  Supports semantic edge types such as `PLACED_ORDER`, `CONTAINS_PRODUCT`, `PAID_FOR`, `ATTRIBUTED_TO`, `PARTICIPATED_IN`, `CONTACTED`, and `SHIPPED_AS`.

* **Business Relationship References**
  Links graph edges back to authoritative records in Business Intelligence whenever a verified `business_relationship` exists.

* **Relationship Confidence**
  Preserves confidence information from the underlying verified relationship.

* **Temporal Relationships**
  Supports validity periods so graph connections can represent relationships that are active only during a particular timeframe.

* **Edge Properties**
  Stores graph-specific metadata that helps visualization and traversal without changing the underlying authoritative relationship.

* **Edge Traceability**
  Ensures users and AI systems can determine why a graph connection exists and which relationship produced it.

---

### 3. Graph Building

Constructs or updates graph structures from canonical entities and verified Business Intelligence relationships.

**Features:**

* **Node Builder**
  Creates graph nodes for eligible canonical entities and keeps them synchronized with the graph representation.

* **Edge Builder**
  Converts verified business relationships into corresponding graph edges.

* **Incremental Graph Updates**
  Updates only affected sections of the graph when new customers, orders, conversations, payments, sessions, or relationships arrive.

* **Full Graph Rebuild**
  Supports rebuilding a business graph from canonical and verified data when required.

* **Identity-Aware Building**
  Uses resolved canonical identities to avoid creating fragmented graph representations for the same real-world entity.

* **Relationship Validation**
  Ensures only valid and supported relationships become authoritative graph edges.

* **Duplicate Prevention**
  Prevents repeated processing from generating duplicate nodes or equivalent edges.

* **Projection Synchronization**
  Keeps the graph aligned with changes in canonical entities and Business Intelligence relationships.

---

### 4. Graph Projection

Transforms canonical data and relationships into graph-optimized structures designed for traversal and visualization.

**Features:**

* **Projection from Source-of-Truth Data**
  Builds graph structures from existing canonical entities instead of creating a competing business data model.

* **Selective Properties**
  Includes only properties needed for graph operations, reducing unnecessary duplication of domain data.

* **Relationship Projection**
  Represents verified Business Intelligence relationships as navigable graph connections.

* **Identity Projection**
  Projects resolved entities so multiple external identities appear as one connected canonical entity where appropriate.

* **Domain-Aware Projection**
  Supports different graph representations depending on entity type and analytical use case.

* **Journey Projection**
  Produces focused subgraphs for customer, order, product, and campaign journeys.

* **Projection Refresh**
  Allows graph projections to be regenerated when the underlying canonical or relationship data changes.

---

### 5. Customer Journey Graph

Builds a connected view of a customer's interactions across commerce, marketing, website behavior, communication, support, calling, payment, and delivery.

**Features:**

* **Cross-Channel Customer Journey**
  Connects activity from multiple platforms after identities have been resolved into the same canonical customer.

* **Website Journey**
  Shows sessions, product views, cart activity, checkout behavior, and conversions associated with the customer.

* **Campaign Touchpoints**
  Includes verified campaign and acquisition relationships connected to the customer's journey.

* **Order Journey**
  Connects customer interactions with resulting orders and order contents.

* **Payment Journey**
  Shows payment and refund activity associated with customer orders.

* **Support Journey**
  Connects conversations, messages, assignments, and support events with the customer.

* **Call Journey**
  Adds incoming and outgoing calls to the broader customer relationship history.

* **Delivery Journey**
  Connects shipments, delivery failures, successful deliveries, and returns.

* **Chronological Exploration**
  Allows journey information to be explored according to when connected events occurred.

Example:

```text
Meta Campaign
      ↓
Website Session
      ↓
Product View
      ↓
Add to Cart
      ↓
Checkout
      ↓
Customer
      ↓
Order
      ↓
Payment
      ↓
Shipment
      ↓
Delivery Failure
      ↓
WhatsApp Conversation
      ↓
Support Call
```

This gives Business Brain a connected representation of the customer's complete observable journey.

---

### 6. Product Journey Graph

Shows how a product participates across website activity, marketing, orders, customers, payments, support, and delivery outcomes.

**Features:**

* **Product–Order Graph**
  Shows which orders contain a particular product.

* **Product–Customer Graph**
  Identifies customers associated with the product through purchases and supported deterministic relationships.

* **Product–Campaign Graph**
  Shows campaigns and marketing interactions connected with product outcomes.

* **Product–Website Graph**
  Connects product views, add-to-cart events, checkout events, and resulting purchases.

* **Product–Revenue Context**
  Connects products to orders and payments that contribute to measurable revenue.

* **Product–Support Context**
  Identifies conversations or calls associated with orders containing a product where the relationship can be established.

* **Product–Delivery Context**
  Shows shipments, failures, and returns associated with orders containing the product.

* **Performance Investigation**
  Enables analysts or AI systems to navigate from an underperforming product to the customer, campaign, website, support, or delivery evidence surrounding that performance.

---

### 7. Order Journey Graph

Represents the complete lifecycle and surrounding context of an individual order.

**Features:**

* **Customer Connection**
  Connects an order with the canonical customer who placed or owns it.

* **Product Connections**
  Shows all canonical products and variants contained within the order.

* **Payment Connection**
  Connects payment and refund activity with the order.

* **Marketing Context**
  Shows campaigns and website sessions attributed to the order when verified relationships exist.

* **Conversation Context**
  Connects support conversations and relevant messages associated with the order.

* **Calling Context**
  Shows calls related to order confirmation, cancellation, delivery, or support.

* **Shipment Connection**
  Connects courier shipments and shipment lifecycle events with the order.

* **Lifecycle Exploration**
  Allows the entire order path from acquisition through fulfillment, support, refund, or return to be investigated from one graph.

---

### 8. Campaign Journey Graph

Represents how marketing activity connects with sessions, customers, products, conversions, orders, revenue, and downstream business outcomes.

**Features:**

* **Campaign–Session Connections**
  Shows website sessions attributed to or associated with a campaign.

* **Campaign–Customer Connections**
  Identifies resolved customers associated with attributable campaign journeys.

* **Campaign–Conversion Connections**
  Links campaign activity with verified leads, purchases, signups, or other conversion events.

* **Campaign–Order Connections**
  Shows orders attributed to campaign interactions when deterministic attribution supports the relationship.

* **Campaign–Product Connections**
  Identifies products involved in campaign-generated browsing or purchasing activity.

* **Campaign–Revenue Connections**
  Connects attributed orders and payments with measurable campaign revenue.

* **Post-Conversion Outcomes**
  Extends the campaign journey into delivery failures, returns, refunds, or support issues rather than stopping at the initial conversion.

* **Campaign Quality Investigation**
  Helps distinguish campaigns that produce healthy business outcomes from campaigns that generate orders but later result in failures, returns, or low realized revenue.

---

### 9. Graph Traversal

Allows connected business entities to be explored by following relationships across the graph.

**Features:**

* **Neighbor Traversal**
  Retrieves directly connected entities around a selected customer, product, order, campaign, or other node.

* **Multi-Hop Traversal**
  Follows several relationships to discover indirect connections between business entities.

* **Relationship-Constrained Traversal**
  Restricts traversal to selected relationship types such as purchases, campaign attribution, support interactions, or shipments.

* **Direction-Aware Traversal**
  Supports inbound, outbound, or bidirectional exploration where relationship direction matters.

* **Depth Control**
  Limits traversal depth so queries return relevant business context without unnecessarily expanding the entire graph.

* **Journey Traversal**
  Follows logical sequences such as `CAMPAIGN → SESSION → CUSTOMER → ORDER → SHIPMENT`.

* **Context Expansion**
  Allows AI or user interfaces to progressively expand nearby business context from an initial entity.

---

### 10. Graph Query

Provides structured mechanisms for retrieving graph information based on entities, relationships, paths, and business context.

**Features:**

* **Entity-Centered Queries**
  Retrieves a graph beginning from a specific customer, order, product, campaign, or other entity.

* **Relationship Queries**
  Finds entities connected through a specified relationship type.

* **Path Queries**
  Searches for valid paths between two business entities.

* **Journey Queries**
  Retrieves predefined journey structures such as customer or campaign journeys.

* **Cross-Domain Queries**
  Supports questions that cross multiple business domains rather than requiring separate queries for each database table.

* **Temporal Queries**
  Restricts graph results to relationships or events relevant to a specific timeframe.

* **Evidence Queries**
  Allows graph relationships to be retrieved together with their underlying Business Intelligence evidence.

Example graph query:

> Which campaigns generated customers who later placed orders that resulted in failed deliveries?

Conceptually:

```text
Campaign
   ↓
Website Session
   ↓
Customer
   ↓
Order
   ↓
Shipment
   ↓
FAILED
```

---

### 11. Graph Filtering

Controls which nodes and relationships appear in graph results based on business and analytical criteria.

**Features:**

* **Entity Type Filtering**
  Includes or excludes specific entity types such as calls, messages, payments, or website sessions.

* **Relationship Type Filtering**
  Restricts graphs to selected relationships such as purchase, attribution, communication, or delivery.

* **Time Filtering**
  Limits graph activity to a specified date or analytical period.

* **Confidence Filtering**
  Allows low-confidence relationships to be excluded from critical analytical views.

* **Status Filtering**
  Filters entities or relationships according to relevant operational states.

* **Journey Filtering**
  Produces focused graph views for marketing, support, delivery, or commerce journeys.

* **Business Dimension Filtering**
  Supports filtering by campaign, product, region, courier, channel, customer segment, or other available dimensions.

* **Graph Complexity Control**
  Reduces graph size so large connected datasets remain understandable and usable.

---

### 12. Graph Snapshots

Stores selected graph states or serialized subgraphs for repeatable analysis, visualization, and prototype demonstrations.

**Features:**

* **Business Graph Snapshot**
  Captures a selected representation of the overall business graph at a particular time.

* **Customer Journey Snapshot**
  Stores a customer's connected journey for later inspection or comparison.

* **Product Journey Snapshot**
  Captures the relationships surrounding a product and its outcomes.

* **Order Journey Snapshot**
  Preserves the connected state of an order and related entities.

* **Campaign Journey Snapshot**
  Stores campaign-related paths from marketing interaction to downstream business outcomes.

* **Snapshot Filters**
  Records the filters and criteria used when the graph snapshot was generated.

* **Node & Edge Counts**
  Maintains structural summary information about the captured graph.

* **Serialized Graph Data**
  Allows a prototype to persist graph structures for deterministic demonstrations without rebuilding every visualization dynamically.

* **Historical Comparison**
  Enables selected graph states to be compared across different periods when snapshots are intentionally retained.

> For production-scale use, large graph structures may be generated dynamically instead of storing every complete graph inside a serialized snapshot.

---

### 13. Evidence-Aware Graph

Ensures graph relationships remain connected to the deterministic evidence and verified relationships that justify them.

**Features:**

* **Relationship Evidence Traceability**
  Allows graph edges to point back to the authoritative Business Intelligence relationship responsible for their existence.

* **Fact Context**
  Associates relevant verified facts with nodes or connected journey segments when presenting analytical context.

* **Issue Context**
  Allows detected business issues to be explored alongside the entities and relationships involved in those issues.

* **Metric Context**
  Makes relevant metric observations accessible from graph-based investigations.

* **Attribution Evidence**
  Preserves the evidence behind campaign-to-session, campaign-to-order, or other attribution-related graph connections.

* **Identity Evidence Context**
  Allows graph users to understand which resolved identities caused cross-platform activity to appear under one canonical entity.

* **AI Grounding**
  Provides AI Intelligence with graph context that is linked back to deterministic business evidence rather than supplying disconnected graph paths alone.

* **Explainable Paths**
  Enables Business Brain to explain not merely that two entities are connected, but why each important edge in the path exists.

Example:

```text
Campaign A
    │
    │ ATTRIBUTED_TO
    │
    ▼
Order #1024
    │
    │ SHIPPED_AS
    │
    ▼
Shipment #S81
    │
    ▼
FAILED
```

For the `ATTRIBUTED_TO` edge, Business Brain can additionally expose:

```text
Relationship Rule:
LAST_TOUCH_ATTRIBUTION

Evidence:
- Website Session S94
- utm_campaign = campaign_a
- Customer resolved as C18
- Order created 23 minutes after session
- Deterministic attribution rule satisfied
```

The graph therefore remains **evidence-aware rather than merely visually connected**.

---

## Graph Architecture

The Business Graph should not independently infer business relationships. Its authoritative input comes from previously validated layers:

```text
Business Data
      ↓
Identity & Resolution
      ↓
Business Intelligence
      │
      └── business_relationships
              ↓
         Business Graph
        ┌─────┴─────┐
        ↓           ↓
   Graph Nodes   Graph Edges
        └─────┬─────┘
              ↓
       Journey Graphs
              ↓
   Traversal / Query / Filter
              ↓
       Graph Snapshots
              ↓
     AI / UI Exploration
```

This distinction prevents an important architectural problem:

```text
WRONG

Graph detects relationship
        ↓
Business assumes relationship is true
```

Instead:

```text
CORRECT

Canonical Data
      ↓
Deterministic Relationship Detection
      ↓
Verified Business Relationship
      ↓
Graph Projection
```

---

## Example Cross-Domain Graph

A connected customer journey could appear as:

```text
                         ┌───────────────┐
                         │  Campaign A   │
                         └───────┬───────┘
                                 │ ATTRIBUTED_TO
                                 ▼
                         ┌───────────────┐
                         │ Web Session 1 │
                         └───────┬───────┘
                                 │
                       VIEWED_PRODUCT
                                 │
                                 ▼
                         ┌───────────────┐
                         │   Product X   │
                         └───────────────┘

                                 │
                                 ▼
                         ┌───────────────┐
                         │ Customer C1   │
                         └───────┬───────┘
                                 │ PLACED_ORDER
                                 ▼
                         ┌───────────────┐
                         │  Order O100   │
                         └───┬─────┬─────┘
                             │     │
                      PAID_FOR     │ SHIPPED_AS
                             │     │
                             ▼     ▼
                       ┌────────┐ ┌────────────┐
                       │Payment │ │ Shipment S1│
                       └────────┘ └─────┬──────┘
                                       │ FAILED
                                       ▼
                                Delivery Failure
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ WhatsApp Support│
                              └────────┬────────┘
                                       │
                                       ▼
                                ┌────────────┐
                                │ Call C102  │
                                └────────────┘
```

A traditional dashboard might show these as separate statistics. Business Graph preserves the relationships between them so Business Brain can investigate the **complete causal and operational context** around an outcome.

---

## Domain Boundary

The **Business Graph** domain answers:

**“How are verified business entities connected, and what paths or journeys exist between them?”**

It does not decide whether two external identities represent the same entity; that belongs to **Identity & Resolution**.

It does not determine whether a campaign caused an order or whether delivery performance is problematic; those decisions belong to **Business Intelligence**.

It does not create AI recommendations; that belongs to **AI Intelligence**.

The architecture is therefore:

**Business Data → Identity & Resolution → Business Intelligence → Business Graph → AI Intelligence**

The core principle is:

**Business Graph projects verified business reality into a connected structure—it does not invent that reality.**

This allows graph traversal, customer journeys, cross-domain investigation, visual exploration, and graph-aware AI reasoning while preserving traceability back to canonical entities and deterministic evidence.
