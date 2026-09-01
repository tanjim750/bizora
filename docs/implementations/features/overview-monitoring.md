# Overview & Monitoring

## Description

The **Overview & Monitoring** domain provides a continuously understandable view of the current state of the business. It consolidates important KPIs, trends, active issues, recent activity, recommendations, and cross-domain signals into monitoring-oriented views that help users quickly understand what requires attention.

Unlike Business Operations, which focuses on performing day-to-day workflows, Overview & Monitoring is primarily concerned with **visibility, awareness, prioritization, and business health**. It consumes data and findings from Business Intelligence, Business Graph, AI Intelligence, and operational domains without becoming a separate analytical source of truth.

---

## Features

### 1. Business Overview

Provides a high-level summary of the current business state across the most important operational and analytical domains.

**Features:**

* **Executive Business Summary**
  Presents a concise view of overall business performance without requiring users to navigate through individual modules.

* **Cross-Domain KPI Summary**
  Combines key indicators from sales, customers, marketing, website activity, support, delivery, and payments.

* **Current Business Status**
  Highlights whether important areas of the business appear healthy, declining, improving, or require attention.

* **Issue Summary**
  Surfaces high-priority active issues detected by Business Intelligence.

* **Recommendation Summary**
  Displays the most relevant AI recommendations associated with current business conditions.

* **Recent Performance Context**
  Shows short-term changes relative to previous periods so current values are not viewed in isolation.

* **Operational Drill-Down**
  Allows users to move from overview cards into detailed operational, analytical, graph, or evidence views.

---

### 2. KPI Overview

Provides a centralized view of important measurable business indicators.

**Features:**

* **Revenue KPIs**
  Displays metrics such as total revenue, realized revenue, refunded revenue, and revenue growth.

* **Order KPIs**
  Shows order volume, average order value, completed orders, cancellations, and related order performance indicators.

* **Customer KPIs**
  Displays new customers, repeat customers, repeat purchase rate, purchase frequency, and other customer metrics.

* **Marketing KPIs**
  Shows spend, conversions, CTR, CPC, ROAS, and attributable revenue.

* **Website KPIs**
  Displays sessions, visitors, conversion rate, cart abandonment, and checkout completion.

* **Support KPIs**
  Shows conversation volume, unresolved conversations, response time, resolution time, and escalation indicators.

* **Delivery KPIs**
  Displays delivery success rate, failure rate, return rate, average delivery time, and related courier performance metrics.

* **Configurable KPI Selection**
  Allows the business to determine which metrics should appear prominently in monitoring views.

* **Dimension-Aware KPIs**
  Supports KPI views by campaign, product, courier, region, channel, or other analytical dimensions.

---

### 3. Performance Trends

Shows how important business metrics change over time so users can identify direction, acceleration, decline, or instability.

**Features:**

* **Time-Series Performance**
  Displays historical metric snapshots across daily, weekly, monthly, or other analytical periods.

* **Period Comparison**
  Compares current performance with previous periods.

* **Growth & Decline Indicators**
  Highlights positive and negative movement in important metrics.

* **Revenue Trends**
  Tracks changes in revenue and realized business value.

* **Order Trends**
  Shows changes in order volume, completed orders, cancellations, and average order value.

* **Marketing Trends**
  Displays changes in campaign spend, conversion, ROAS, and other marketing metrics.

* **Website Trends**
  Tracks conversion, traffic, abandonment, and user-behavior changes.

* **Support Trends**
  Shows changes in support demand, response time, unresolved conversations, and escalation.

* **Delivery Trends**
  Displays changes in delivery success, failure, returns, and courier performance.

* **Dimension Comparison**
  Allows trends to be compared across products, campaigns, regions, couriers, or customer groups.

---

### 4. Active Issues

Provides a prioritized view of currently unresolved business problems detected by Business Intelligence.

**Features:**

* **Open Issue List**
  Displays Business Issues that are currently active and unresolved.

* **Severity-Based Prioritization**
  Organizes issues according to severity such as low, medium, high, and critical.

* **Confidence Display**
  Shows the analytical confidence associated with each detected issue.

* **Affected Entity Context**
  Identifies the product, campaign, courier, region, customer segment, or other entity associated with the issue.

* **Issue Evidence Summary**
  Presents the main facts and metrics explaining why the issue was detected.

* **Issue Trend Context**
  Shows whether the underlying condition is improving, worsening, or remaining stable.

* **Issue Drill-Down**
  Allows users to inspect detailed evidence, graph relationships, related entities, and AI diagnosis.

* **Issue Lifecycle Visibility**
  Distinguishes newly detected, acknowledged, ongoing, resolved, and dismissed issues.

* **Recommendation Association**
  Shows AI recommendations generated specifically to address an active issue.

---

### 5. Business Health

Summarizes the overall condition of the business using deterministic performance and issue signals.

**Features:**

* **Business Health Summary**
  Provides a concise overall status derived from measurable business conditions.

* **Domain-Level Health**
  Evaluates areas such as sales, marketing, website, support, delivery, and customer performance separately.

* **Health Indicator Rules**
  Uses explicit thresholds, active issues, metric trends, and business goals rather than arbitrary AI judgment.

* **Healthy State Detection**
  Identifies areas operating within expected or acceptable ranges.

* **Warning State Detection**
  Highlights areas showing early deterioration or moderate issues.

* **Critical State Detection**
  Surfaces areas affected by severe or high-impact problems.

* **Health Evidence**
  Allows users to inspect which metrics, facts, or issues contributed to the displayed health state.

* **Health Trend**
  Shows whether overall or domain-level health is improving or declining over time.

* **Goal-Aware Health Context**
  Can evaluate business performance relative to configured business goals where appropriate.

> Business Health should summarize existing deterministic intelligence. It should not create a separate opaque score that users cannot explain.

---

### 6. Recent Activity

Provides a chronological stream of important business events and changes across connected domains.

**Features:**

* **Order Activity**
  Displays newly created, completed, cancelled, or otherwise significant order events.

* **Payment Activity**
  Shows successful payments, failures, refunds, and other relevant financial events.

* **Customer Activity**
  Highlights important customer events such as new customers, repeat purchases, or significant customer interactions.

* **Support Activity**
  Shows newly opened conversations, escalations, assignments, resolutions, and handovers.

* **Delivery Activity**
  Displays shipment submission, failed deliveries, returns, successful deliveries, and other fulfillment events.

* **Marketing Activity**
  Shows meaningful campaign changes, conversion events, or detected performance changes.

* **Website Activity**
  Highlights significant website events or detected conversion behavior changes.

* **Calling Activity**
  Displays important incoming and outgoing call events.

* **Issue Activity**
  Shows newly detected, updated, acknowledged, or resolved business issues.

* **AI Activity**
  Surfaces newly generated recommendations, approvals, rejections, and executed suggested actions.

* **Activity Filtering**
  Allows users to filter recent activity by domain, entity type, severity, or timeframe.

---

### 7. Recommendations

Provides a monitoring-oriented view of current AI-generated business recommendations.

**Features:**

* **Recommendation Feed**
  Displays active recommendations generated by AI Intelligence.

* **Priority Ranking**
  Organizes recommendations according to urgency and business importance.

* **Issue-Linked Recommendations**
  Shows which Business Issue triggered or motivated a recommendation.

* **Evidence Summary**
  Displays the main facts, metrics, graph relationships, and memory context supporting the recommendation.

* **Recommendation Confidence**
  Shows confidence information where available.

* **Suggested Action Preview**
  Displays the operation associated with a recommendation before approval.

* **Approval Status**
  Shows whether the recommendation or associated action is suggested, under review, approved, rejected, or already actioned.

* **Historical Recommendations**
  Allows previously reviewed or completed recommendations to be inspected.

* **Goal Alignment**
  Indicates when a recommendation directly supports an active business goal.

* **Recommendation Drill-Down**
  Allows users to inspect the full AI explanation, evidence, graph context, and suggested action.

---

### 8. Cross-Domain Monitoring

Monitors relationships between different business areas so problems that span multiple systems can be detected and understood together.

**Features:**

* **Marketing-to-Revenue Monitoring**
  Tracks whether increased marketing activity is producing actual revenue rather than only clicks or conversions.

* **Marketing-to-Delivery Monitoring**
  Detects cases where campaigns generate orders but those orders later experience high delivery failure or return rates.

* **Website-to-Sales Monitoring**
  Connects website behavior and conversion performance with resulting order and revenue outcomes.

* **Product-to-Support Monitoring**
  Identifies products associated with increased customer-support activity or recurring issues.

* **Product-to-Delivery Monitoring**
  Monitors whether particular products are disproportionately associated with failed or returned shipments.

* **Customer-to-Retention Monitoring**
  Tracks whether acquired customers return and make additional purchases.

* **Support-to-Customer Outcome Monitoring**
  Evaluates whether support demand is associated with customer churn, cancellations, refunds, or repeat purchases.

* **Courier-to-Revenue Monitoring**
  Connects fulfillment quality with realized revenue and refund impact.

* **Campaign-to-Customer Quality Monitoring**
  Evaluates whether campaigns acquire customers who produce healthy long-term business outcomes.

* **Cross-Domain Issue Surfacing**
  Highlights problems that would be difficult to detect by observing individual systems independently.

Example:

```text id="7lqm2k"
Marketing
Orders from Campaign A ↑ 26%

        ↓

Delivery
Failure rate ↑ 9% → 18%

        ↓

Payments
Refunded revenue ↑ 24%

        ↓

Revenue
Realized revenue ↓

        ↓

Cross-Domain Monitoring

Campaign A generates additional demand,
but downstream fulfillment problems are
reducing actual business value.
```

---

## Monitoring Information Flow

Overview & Monitoring does not independently calculate most business intelligence.

It consumes already-processed outputs:

```text id="d0w3nm"
Business Data
      ↓
Identity & Resolution
      ↓
Business Intelligence
      │
      ├── Metrics
      ├── Metric Snapshots
      ├── Facts
      ├── Issues
      └── Relationships
      │
      ├───────────────┐
      ▼               ▼
Business Graph    AI Intelligence
      │               │
      └───────┬───────┘
              ↓
      Overview & Monitoring
              │
       ┌──────┼────────┐
       ↓      ↓        ↓
      KPIs  Issues  Recommendations
       │      │        │
       └──────┼────────┘
              ↓
        User Awareness
```

This keeps monitoring views lightweight and consistent with authoritative analytical systems.

---

## Business Overview vs Business Operations

The name **Business Overview** appears in both Business Operations and Overview & Monitoring, but the responsibilities are slightly different.

```text id="vpgrnj"
Overview & Monitoring
---------------------
"What needs my attention?"

Focus:
- KPIs
- Trends
- Health
- Issues
- Recommendations
- Cross-domain signals


Business Operations
-------------------
"What do I need to work on?"

Focus:
- Customers
- Orders
- Conversations
- Shipments
- Calls
- Payments
- Operational actions
```

A practical UI can expose one **Business Overview page** that combines both responsibilities, while the architecture still distinguishes monitoring concerns from operational workflow concerns.

---

## Example Monitoring Flow

Consider a business where orders appear healthy at first:

```text id="g4uzy7"
Orders
+21%

Revenue
+5%
```

A traditional dashboard may show this as positive growth.

Cross-domain monitoring can provide deeper context:

```text id="x21zvo"
Campaign Spend
+18%

        ↓

Orders
+21%

        ↓

Gazipur Orders
+39%

        ↓

Courier X Failures
9% → 20%

        ↓

Returns
+28%

        ↓

Refunded Revenue
+24%

        ↓

Realized Revenue
Only +5%
```

Overview & Monitoring can then surface:

```text id="jpo1yi"
BUSINESS HEALTH
WARNING

Active Issue:
HIGH_DELIVERY_FAILURE

Affected Area:
Gazipur / Courier X

Impact:
Incremental sales are being partially
lost through failed deliveries and refunds.

Recommendation:
Test alternative courier allocation
for high-risk Gazipur orders.
```

The monitoring layer therefore turns complex intelligence into an immediately understandable business state.

---

## Monitoring Priority Model

Information shown to users should not be treated equally.

A useful hierarchy is:

```text id="thklco"
1. Critical Active Issues
        ↓
2. Significant Business Health Changes
        ↓
3. Important KPI Deviations
        ↓
4. High-Priority Recommendations
        ↓
5. Major Recent Activity
        ↓
6. Normal Performance Information
```

This helps prevent dashboards from becoming collections of unrelated cards where genuinely important signals are visually indistinguishable from routine business activity.

---

## Domain Boundary

The **Overview & Monitoring** domain answers:

**“What is happening across the business right now, what has changed, and what requires attention?”**

It does not own canonical business entities; those belong to **Business Data**.

It does not calculate authoritative metrics, facts, anomalies, or business issues; those belong to **Business Intelligence**.

It does not establish graph relationships; those belong to **Business Graph** and its authoritative upstream relationship sources.

It does not generate recommendations; those belong to **AI Intelligence**.

It primarily acts as a consolidated presentation and monitoring layer over those systems.

The architecture is:

**Business Data → Identity → Business Intelligence → Graph / AI → Overview & Monitoring → User Awareness → Business Operations**

The core principle is:

**Overview & Monitoring should reduce a complex multi-platform business into a clear answer to three questions: What is happening? What changed? What needs attention?**
