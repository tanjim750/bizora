# Business Intelligence

## Description

The **Business Intelligence** domain is the deterministic analytical layer of Business Brain. It transforms normalized and identity-resolved business data into measurable relationships, metrics, trends, verified facts, anomalies, and actionable business issues.

This domain is responsible for establishing **what is actually happening in the business based on available data and explicit analytical rules**. AI can later explain these findings and recommend actions, but AI does not create authoritative relationships, metrics, facts, or issues.

---

## Features

### 1. Business Relationships

Identifies and stores meaningful relationships between canonical business entities. These relationships connect otherwise isolated data and form the analytical foundation for cross-domain reasoning and Business Graph construction.

**Features:**

* **Cross-Domain Relationship Detection**
  Establishes relationships between customers, orders, products, payments, campaigns, website sessions, conversations, calls, and shipments.

* **Deterministic Relationship Rules**
  Uses explicit rules and known references rather than LLM inference to determine authoritative entity relationships.

* **Customer–Order Relationships**
  Identifies which canonical customer placed or is associated with a particular order.

* **Order–Product Relationships**
  Connects orders with the canonical products and variants contained within them.

* **Order–Payment Relationships**
  Associates financial transactions with the orders they paid for.

* **Order–Shipment Relationships**
  Connects order fulfillment with corresponding courier shipments.

* **Customer–Communication Relationships**
  Associates customers with their conversations, messages, and calls.

* **Marketing Relationships**
  Connects campaigns, website sessions, customers, and resulting business outcomes where sufficient evidence exists.

* **Relationship Confidence**
  Maintains confidence information where a relationship rule supports different certainty levels.

* **Relationship Traceability**
  Stores the rule and metadata responsible for creating a relationship so downstream analysis remains explainable.

---

### 2. Business Metrics

Defines the measurable indicators Business Brain uses to evaluate business performance consistently across domains.

**Features:**

* **Metric Registry**
  Maintains standardized definitions for supported business metrics and prevents different modules from calculating the same concept inconsistently.

* **Sales Metrics**
  Defines indicators such as total orders, units sold, average order value, cancellation rate, and sales growth.

* **Revenue Metrics**
  Defines revenue, refunded revenue, revenue growth, revenue per customer, and related financial performance measures.

* **Customer Metrics**
  Defines customer acquisition, repeat customer rate, customer purchase frequency, and other customer-performance indicators.

* **Marketing Metrics**
  Supports spend, impressions, clicks, CTR, CPC, CPM, conversion rate, ROAS, and related advertising indicators.

* **Support Metrics**
  Defines response time, resolution time, conversation volume, unresolved cases, escalation rate, and other support indicators.

* **Website Metrics**
  Defines conversion rate, checkout completion, cart abandonment, product-view conversion, and behavioral indicators.

* **Delivery Metrics**
  Defines successful delivery rate, failure rate, return rate, delivery time, and courier-related performance measures.

* **Metric Dimensions**
  Allows metrics to be calculated for dimensions such as product, campaign, region, courier, channel, customer segment, or other analytical scopes.

---

### 3. Metric Snapshots

Stores calculated metric values for specific periods and dimensions so Business Brain can analyze performance over time rather than only displaying current totals.

**Features:**

* **Time-Based Metric Storage**
  Stores metric values for hourly, daily, weekly, monthly, or custom periods.

* **Historical Comparison**
  Enables comparison between current and previous periods to identify improvement, decline, or stability.

* **Dimension-Based Snapshots**
  Stores metric values for specific products, campaigns, regions, couriers, channels, or other dimensions.

* **Trend Foundation**
  Provides historical observations required for trend analysis and anomaly detection.

* **Calculation Traceability**
  Records the rule or calculation method responsible for producing a metric snapshot.

* **Reproducible Analysis**
  Allows Business Brain to reference the exact metric observation used to produce a fact or issue.

---

### 4. Attribution

Determines which identifiable business interactions contributed to a conversion or business outcome using explicit attribution rules and available evidence.

**Features:**

* **Campaign Attribution**
  Connects marketing campaigns with resulting conversions when deterministic evidence supports the relationship.

* **Session Attribution**
  Associates website sessions with purchases, leads, signups, or other conversion events.

* **Customer Attribution**
  Connects known customer journeys with acquisition and marketing touchpoints after identity resolution.

* **Order Attribution**
  Associates resulting orders with supported campaign or website interactions.

* **First-Touch Attribution**
  Identifies the earliest qualifying marketing touchpoint in a customer journey.

* **Last-Touch Attribution**
  Identifies the final qualifying marketing touchpoint before conversion.

* **Direct Attribution**
  Supports explicit relationships where the source system directly provides reliable campaign or conversion references.

* **Platform-Reported Attribution**
  Preserves attribution information reported by advertising platforms while distinguishing it from Business Brain's own deterministic attribution.

* **Attribution Evidence**
  Preserves sessions, campaign references, timestamps, identifiers, and rules supporting an attribution result.

---

### 5. Conversion Analysis

Analyzes how visitors, customers, campaigns, products, and website interactions progress toward meaningful business outcomes.

**Features:**

* **Conversion Rate Analysis**
  Measures the percentage of eligible visitors, sessions, or interactions that result in defined conversions.

* **Funnel Analysis**
  Evaluates progression through stages such as product view → add to cart → checkout → purchase.

* **Funnel Drop-Off Detection**
  Identifies stages where a significant number of users leave the conversion journey.

* **Campaign Conversion Analysis**
  Measures conversions and conversion value associated with marketing campaigns.

* **Product Conversion Analysis**
  Evaluates how frequently product views or interactions result in purchases.

* **Conversion Trend Analysis**
  Compares conversion performance across periods to detect improvement or deterioration.

* **Conversion Segmentation**
  Allows conversion performance to be analyzed by source, campaign, product, device, region, customer segment, or other supported dimensions.

---

### 6. Revenue Analysis

Analyzes how revenue is generated, distributed, and changing across the business.

**Features:**

* **Total Revenue Analysis**
  Calculates business revenue over defined analytical periods.

* **Revenue Trend Analysis**
  Measures how revenue changes across days, weeks, months, or other periods.

* **Product Revenue Analysis**
  Determines how much revenue individual products or product categories generate.

* **Campaign Revenue Analysis**
  Measures revenue associated with attributable marketing activity.

* **Customer Revenue Analysis**
  Evaluates revenue generated by individual customers or customer segments.

* **Channel Revenue Analysis**
  Compares revenue originating from different commerce, acquisition, or marketing channels.

* **Refund Impact Analysis**
  Accounts for refunds when evaluating realized business revenue.

* **Revenue Change Detection**
  Identifies significant increases or decreases relative to historical baselines or comparison periods.

---

### 7. Product Analysis

Evaluates how products perform across sales, revenue, marketing, website behavior, customer activity, and fulfillment.

**Features:**

* **Product Sales Performance**
  Measures units sold, order frequency, and sales trends for individual products.

* **Product Revenue Performance**
  Calculates revenue contribution by product or category.

* **Product Conversion Performance**
  Compares product views and engagement with resulting purchases.

* **Product Trend Analysis**
  Identifies improving, stable, or declining product performance.

* **High-Performing Product Detection**
  Identifies products contributing disproportionately to sales, revenue, or conversions.

* **Underperforming Product Detection**
  Detects products experiencing weak conversion, declining sales, or other measurable performance problems.

* **Product–Campaign Analysis**
  Connects product outcomes with relevant marketing campaigns where attribution evidence exists.

* **Product–Delivery Analysis**
  Evaluates whether specific products are disproportionately associated with delivery failures or returns.

---

### 8. Campaign Analysis

Evaluates advertising campaign efficiency and business impact using normalized marketing metrics and attributed outcomes.

**Features:**

* **Campaign Performance Analysis**
  Evaluates impressions, reach, clicks, spend, conversions, and revenue together.

* **ROAS Analysis**
  Measures attributable revenue relative to campaign advertising spend.

* **CTR Analysis**
  Evaluates how effectively campaign impressions generate clicks.

* **CPC & CPM Analysis**
  Measures advertising cost efficiency using normalized cost metrics.

* **Campaign Conversion Analysis**
  Evaluates how effectively campaign traffic produces meaningful business outcomes.

* **Campaign Comparison**
  Compares campaigns using standardized metrics regardless of the original advertising platform.

* **Campaign Trend Analysis**
  Detects improving or declining campaign performance over time.

* **Low-Performance Detection**
  Identifies campaigns whose measurable performance falls below configured or historical expectations.

---

### 9. Customer Analysis

Analyzes customer behavior and commercial activity using unified canonical and identity-resolved customer data.

**Features:**

* **Customer Purchase Analysis**
  Measures order frequency, purchase value, product preferences, and purchasing history.

* **Customer Value Analysis**
  Evaluates customers based on measurable revenue and transaction behavior.

* **Customer Activity Analysis**
  Combines orders, website behavior, conversations, calls, payments, and delivery activity into analytical customer context.

* **Customer Segment Analysis**
  Evaluates groups such as new customers, repeat buyers, high-value customers, or other deterministic segments.

* **Customer Channel Analysis**
  Determines which channels customers use for acquisition, communication, purchase, and support.

* **Customer Journey Analysis**
  Examines the sequence of measurable customer interactions across connected domains.

* **Customer Risk Signals**
  Identifies measurable signals such as repeated delivery failures, frequent cancellations, unresolved support cases, or declining engagement.

---

### 10. Retention & Repeat Purchase Analysis

Measures whether customers continue purchasing from the business after their initial transaction.

**Features:**

* **New vs Repeat Customer Analysis**
  Separates first-time customers from customers who have completed previous purchases.

* **Repeat Purchase Rate**
  Calculates the percentage of customers who return and purchase again.

* **Purchase Frequency**
  Measures how frequently customers place orders over a defined period.

* **Time Between Purchases**
  Measures the interval between consecutive customer purchases.

* **Retention Trend Analysis**
  Evaluates whether repeat purchasing behavior is improving or declining.

* **Product-Level Repeat Analysis**
  Determines which products are commonly associated with repeat purchases.

* **Campaign Retention Analysis**
  Evaluates whether customers acquired through particular campaigns later become repeat buyers.

* **Customer Retention Segmentation**
  Compares retention across channels, products, regions, campaigns, or customer groups.

---

### 11. Support Analysis

Evaluates customer support performance using canonical conversations, messages, assignments, handovers, and resolutions.

**Features:**

* **Conversation Volume Analysis**
  Measures incoming support demand over time.

* **Response Time Analysis**
  Measures how quickly customer conversations receive an initial or subsequent response.

* **Resolution Time Analysis**
  Calculates how long support conversations remain active before resolution.

* **Unresolved Conversation Analysis**
  Identifies conversations that remain open or pending beyond expected periods.

* **Priority Analysis**
  Measures the distribution and performance of high-priority and urgent conversations.

* **AI/Human Handover Analysis**
  Evaluates how frequently conversations move between automated and human support.

* **Support Issue Trend Analysis**
  Identifies measurable increases in support activity associated with products, orders, delivery, or other business areas.

* **Customer Support History Analysis**
  Connects repeated support interactions with customer and order activity for broader business analysis.

---

### 12. Website Analysis

Evaluates website traffic, visitor journeys, behavior, conversion performance, and measurable user-experience signals.

**Features:**

* **Traffic Analysis**
  Measures visitors, sessions, page views, acquisition sources, and traffic trends.

* **Traffic Source Analysis**
  Compares direct, organic, paid, referral, social, and other acquisition channels.

* **Landing Page Analysis**
  Evaluates how different entry pages perform in engagement and conversion.

* **Product Behavior Analysis**
  Measures product views, add-to-cart activity, checkout activity, and purchases.

* **Cart Abandonment Analysis**
  Identifies sessions where customers add products to their cart but fail to complete purchase.

* **Checkout Drop-Off Analysis**
  Measures users who begin checkout but do not reach purchase completion.

* **Device & Browser Analysis**
  Compares behavior and conversion performance across devices, browsers, and operating systems.

* **Experience Signal Analysis**
  Analyzes signals such as rage clicks, dead clicks, quick backs, errors, and latency when available.

* **Website Journey Analysis**
  Reconstructs sequences of website interactions to understand how users progress toward or away from conversion.

---

### 13. Delivery Analysis

Evaluates courier and fulfillment performance using canonical shipments, shipment events, orders, customers, and delivery costs.

**Features:**

* **Delivery Success Rate**
  Measures the percentage of shipments successfully delivered.

* **Delivery Failure Rate**
  Measures failed delivery attempts and unsuccessful shipments.

* **Return Rate Analysis**
  Evaluates how frequently shipments are returned after submission or delivery attempts.

* **Courier Performance Comparison**
  Compares delivery success, failure, return, timing, and cost across courier providers.

* **Delivery Time Analysis**
  Measures the time between shipment submission, pickup, and successful delivery.

* **Regional Delivery Analysis**
  Identifies geographic areas with unusually high delivery failures, returns, or delays.

* **Customer Delivery Analysis**
  Detects customers associated with repeated failed or returned shipments.

* **Product Delivery Analysis**
  Identifies products disproportionately associated with delivery failures or returns.

* **Delivery Cost Analysis**
  Measures courier charges and their impact on order economics.

---

### 14. Anomaly Detection

Detects unusual changes or deviations in business metrics using deterministic analytical rules and historical observations.

**Features:**

* **Threshold-Based Detection**
  Detects when a metric exceeds or falls below a configured acceptable threshold.

* **Period-over-Period Detection**
  Identifies significant differences between current and previous analytical periods.

* **Baseline Deviation Detection**
  Compares current performance with historical baselines to identify unusual behavior.

* **Trend Break Detection**
  Detects significant changes from an established performance direction.

* **Cross-Domain Anomalies**
  Identifies anomalies involving multiple domains, such as rising campaign spend combined with falling conversions.

* **Dimension-Level Detection**
  Detects anomalies for individual products, campaigns, regions, couriers, customer segments, or other dimensions.

* **Anomaly Evidence**
  Preserves the metric observations and comparisons responsible for identifying an anomaly.

> For the prototype, anomaly detection should remain primarily rule-based and deterministic. More advanced statistical or ML-based detection can be introduced later without changing the surrounding intelligence architecture.

---

### 15. Business Facts

Converts validated analytical results into structured, evidence-backed statements that downstream systems can safely consume.

**Features:**

* **Verified Fact Creation**
  Creates structured facts only when deterministic analysis and available evidence satisfy the required rule.

* **Fact Classification**
  Classifies findings such as revenue change, delivery failure, campaign performance, conversion decline, or support delay.

* **Entity-Specific Facts**
  Associates facts with a specific product, customer, campaign, courier, region, or other entity when appropriate.

* **Quantified Facts**
  Stores measurable values and units alongside textual representations of analytical findings.

* **Fact Confidence**
  Records confidence when the analytical mechanism supports different certainty levels.

* **Fact Lifecycle**
  Supports states such as `CANDIDATE`, `VERIFIED`, `INVALIDATED`, and `EXPIRED`.

* **Fact Validity Period**
  Records the period for which an analytical fact applies.

* **Rule Traceability**
  Identifies which deterministic analytical rule generated the fact.

Example:

> **Delivery failure rate in Gazipur increased from 9% to 17% during the current comparison period.**

This is a **fact** because it describes an observed and measurable condition.

---

### 16. Fact Evidence

Maintains the evidence that proves or supports each Business Fact.

**Features:**

* **Metric Evidence**
  Links facts to the metric snapshots used to calculate or verify them.

* **Relationship Evidence**
  References deterministic business relationships involved in producing a fact.

* **Entity Evidence**
  Associates supporting orders, shipments, campaigns, customers, products, or other domain entities.

* **Event Evidence**
  References relevant lifecycle or behavioral events where they contribute to the analytical result.

* **Comparison Evidence**
  Stores previous and current observations used for period or baseline comparisons.

* **Evidence Weighting**
  Allows supporting evidence to carry different analytical importance where appropriate.

* **Evidence Metadata**
  Preserves calculations, dimensions, filters, thresholds, and other information needed to understand how the fact was produced.

* **Fact Explainability**
  Enables Business Brain and AI to answer not only **what happened**, but also **which data proves it**.

---

### 17. Business Issue Detection

Transforms significant verified findings into structured business problems that may require attention or action.

**Features:**

* **Rule-Based Issue Detection**
  Uses deterministic rules to decide when a metric, anomaly, or combination of facts represents an actionable business problem.

* **Cross-Domain Issue Detection**
  Combines evidence across domains when a business problem cannot be understood from one metric alone.

* **Issue Classification**
  Supports problems such as `HIGH_DELIVERY_FAILURE`, `LOW_CAMPAIGN_ROAS`, `HIGH_CART_ABANDONMENT`, `SUPPORT_RESPONSE_DELAY`, and `REVENUE_DECLINE`.

* **Issue Severity**
  Classifies detected problems as `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.

* **Issue Confidence**
  Represents analytical confidence in the detected issue separately from severity.

* **Entity-Specific Issues**
  Associates an issue with the affected campaign, product, courier, region, customer segment, or other business entity.

* **Issue Lifecycle**
  Supports operational states such as `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, and `DISMISSED`.

* **Issue Resolution Tracking**
  Records when an identified problem is resolved so Business Brain can distinguish historical problems from active ones.

Example:

```text
Fact:
Delivery failure rate increased from 9% → 17%.

Additional Facts:
Most failures are in Gazipur.
Courier X accounts for 74% of those failures.

        ↓

Business Issue:
HIGH_DELIVERY_FAILURE

Severity:
HIGH
```

The issue is therefore an interpretation produced by deterministic business rules from verified observations—not an unsupported AI conclusion.

---

### 18. Issue Evidence

Maintains the evidence explaining why Business Intelligence classified a condition as a business issue.

**Features:**

* **Fact Evidence Linking**
  Connects an issue with one or more verified Business Facts.

* **Metric Evidence Linking**
  References the metric snapshots directly supporting the issue.

* **Relationship Evidence Linking**
  Connects issues with deterministic relationships relevant to the detected problem.

* **Entity Evidence**
  References affected customers, orders, products, campaigns, shipments, conversations, or other business entities.

* **Trend Evidence**
  Preserves historical trends showing how the problem developed.

* **Comparison Evidence**
  Stores comparisons against previous periods, baselines, thresholds, or other dimensions.

* **Evidence Weighting**
  Indicates the relative importance of individual evidence items when multiple signals contribute to an issue.

* **Issue Explainability**
  Allows downstream AI and user interfaces to explain exactly why Business Brain considers something a problem.

---

## Intelligence Processing Flow

Business Intelligence follows a deterministic evidence chain:

```text
Canonical Business Data
        +
Resolved Identities
        ↓
Business Relationships
        ↓
Business Metrics
        ↓
Metric Snapshots
        ↓
Analysis
├── Attribution
├── Conversion
├── Revenue
├── Product
├── Campaign
├── Customer
├── Retention
├── Support
├── Website
└── Delivery
        ↓
Anomaly Detection
        ↓
Business Facts
        ↓
Fact Evidence
        ↓
Business Issue Detection
        ↓
Business Issues
        ↓
Issue Evidence
```

A cross-domain example:

```text
Meta Campaign
      ↓
Website Sessions
      ↓
Product Views
      ↓
Checkout
      ↓
Orders
      ↓
Shipments
      ↓
Delivery Failures

Business Intelligence calculates:

Campaign Spend ↑
Conversion Rate stable
Orders ↑
Delivery Failure ↑
Returned Orders ↑
Realized Revenue ↓

        ↓

Verified Facts

        ↓

Business Issue:
Campaign is generating orders,
but fulfillment failures are reducing
the actual business value.
```

This is one of the important distinctions of Business Brain: the system should not evaluate each platform independently when the relevant business outcome spans multiple domains.

---

## Facts vs Issues vs AI Recommendations

These concepts should remain separate:

```text
METRIC
"Delivery failure rate = 17%"
        ↓
FACT
"Delivery failure increased from 9% to 17%."
        ↓
ISSUE
"Delivery failure is abnormally high in Gazipur
and is affecting completed-order revenue."
        ↓
AI RECOMMENDATION
"Consider shifting Gazipur deliveries away from
Courier X and compare performance for seven days."
```

**Metrics** are measurements.

**Facts** are verified statements derived from measurements and relationships.

**Issues** are business problems identified from verified facts according to explicit rules.

**AI Recommendations** are proposed responses to those problems and belong to the **AI Intelligence** domain.

---

## Domain Boundary

The **Business Intelligence** domain answers:

**“What is happening in the business, how are different business activities related, and which verified conditions require attention?”**

It consumes canonical information from **Business Data** and resolved entities from **Identity & Resolution**.

It does not own raw provider connectivity, canonical business entities, graph visualization, long-term business knowledge, or generative recommendations.

The architectural flow is:

**Business Data → Identity & Resolution → Business Intelligence → Business Graph → AI Intelligence**

The core trust principle is:

**Data → Relationship → Metric → Evidence → Fact → Issue → AI Explanation/Recommendation**

Business Intelligence establishes the evidence-backed reality of the business. AI operates on top of that reality rather than inventing it.
