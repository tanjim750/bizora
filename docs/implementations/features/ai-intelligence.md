# AI Intelligence

## Description

The **AI Intelligence** domain is the reasoning and assistance layer of Business Brain. It consumes verified business facts, relationships, graph context, business memory, and canonical operational data to explain situations, answer questions, summarize interactions, generate recommendations, and suggest actions.

AI Intelligence does **not** independently establish authoritative business relationships, identity links, metrics, facts, or issues. Instead, it operates on evidence produced by deterministic domains and must preserve traceability between its outputs and the business data, facts, graph paths, and knowledge used to generate them.

---

## Features

### 1. Business Assistant

Provides a conversational interface for users to ask business questions and receive context-aware answers grounded in Business Brain data.

**Features:**

* **Natural Language Business Queries**
  Allows users to ask questions such as revenue performance, campaign effectiveness, customer behavior, delivery problems, or recent business changes in normal language.

* **Cross-Domain Answers**
  Combines information from orders, customers, campaigns, website behavior, support, calling, delivery, and other connected business areas when answering a question.

* **Business Context Awareness**
  Uses the current business profile, goals, policies, recent facts, active issues, and relevant graph context when constructing answers.

* **Evidence-Backed Responses**
  Grounds important claims in verified Business Intelligence outputs rather than relying only on language-model inference.

* **Follow-Up Context**
  Maintains conversational context so users can ask follow-up questions about previously discussed entities, issues, or recommendations.

* **Business-Specific Terminology**
  Uses product names, campaign names, customer context, business policies, and other business-specific information when relevant.

---

### 2. Customer Support AI

Assists customer support workflows by generating grounded responses, summaries, context, and escalation suggestions.

**Features:**

* **Suggested Customer Replies**
  Generates draft responses based on the current conversation, customer information, relevant order state, business policies, and support knowledge.

* **Policy-Aware Responses**
  Retrieves delivery, refund, cancellation, product, and support policies before generating answers that depend on business rules.

* **Customer Context Awareness**
  Uses available customer history such as previous orders, support conversations, delivery failures, calls, and other relevant activity.

* **Order-Aware Support**
  Retrieves the specific order and fulfillment context when a customer asks about delivery, cancellation, payment, refund, or order status.

* **Escalation Suggestions**
  Identifies situations that may require a human agent based on business rules, uncertainty, policy restrictions, or conversation context.

* **AI-to-Human Handover Support**
  Produces concise handover summaries so human agents can understand the conversation without rereading the complete history.

* **Human-to-AI Continuation**
  Allows AI to resume handling where appropriate while retaining previous human notes and conversation context.

* **Support Knowledge Retrieval**
  Retrieves relevant FAQs, troubleshooting guides, policies, and approved support procedures before generating a response.

---

### 3. Marketing Assistant

Helps users understand marketing performance and generate grounded optimization ideas using verified campaign and business outcomes.

**Features:**

* **Campaign Performance Explanation**
  Explains campaign metrics such as spend, clicks, conversions, ROAS, conversion rate, and attributable revenue in accessible language.

* **Cross-Domain Campaign Analysis**
  Considers downstream outcomes such as order quality, delivery failures, refunds, repeat purchases, and customer support activity rather than evaluating campaigns only by ad-platform metrics.

* **Optimization Suggestions**
  Suggests actions such as budget adjustments, audience review, product focus changes, or campaign investigation based on verified findings.

* **Low-Performance Explanation**
  Explains why Business Intelligence classified a campaign as underperforming using the associated metrics and evidence.

* **Product-Campaign Context**
  Uses product sales and conversion performance when evaluating marketing campaigns.

* **Customer Quality Context**
  Considers whether campaign-acquired customers become repeat buyers, produce high-value orders, or experience poor fulfillment outcomes.

* **Marketing Goal Alignment**
  Prioritizes suggestions based on active business goals such as improving ROAS, increasing conversion, or growing repeat purchases.

---

### 4. Business Diagnosis

Explains business problems by combining verified issues with cross-domain context and evidence.

**Features:**

* **Issue Explanation**
  Converts structured Business Issues into clear descriptions of what is wrong and why the problem matters.

* **Root-Context Exploration**
  Traverses related facts, metrics, relationships, graph paths, and business entities to provide broader context around an issue.

* **Cross-Domain Diagnosis**
  Examines multiple business areas when the visible symptom and underlying problem belong to different domains.

* **Impact Explanation**
  Describes how an issue may affect revenue, customer experience, fulfillment, marketing efficiency, or other measurable outcomes.

* **Contributing Factor Identification**
  Surfaces evidence-backed factors associated with an issue without presenting unsupported correlation as causation.

* **Historical Context**
  Retrieves similar previous issues, decisions, or approved recommendations when available.

* **Diagnostic Summary**
  Produces a concise explanation suitable for overview dashboards, management reviews, or operational investigation.

Example:

```text id="4op8kw"
Observed:
Campaign orders increased by 22%.

But:
Delivery failure increased from 9% to 18%.

Graph Context:
Most failed orders came from Gazipur
and were handled by Courier X.

Diagnosis:
The campaign is generating demand,
but fulfillment performance is reducing
the realized value of those orders.
```

---

### 5. Fact-Aware Context Retrieval

Retrieves verified facts and their evidence before AI generates business explanations or recommendations.

**Features:**

* **Relevant Fact Selection**
  Identifies Business Facts relevant to the current question, issue, customer, campaign, product, or other context.

* **Fact Status Filtering**
  Prioritizes verified and currently valid facts while excluding invalidated or expired findings unless historical context is explicitly needed.

* **Fact Evidence Retrieval**
  Retrieves the metrics, relationships, comparisons, or entities that support each selected fact.

* **Entity-Scoped Retrieval**
  Restricts fact context to relevant customers, products, campaigns, orders, regions, couriers, or other business dimensions.

* **Time-Aware Fact Selection**
  Ensures current questions use facts from the appropriate analytical period.

* **Fact-to-Prompt Context**
  Converts structured facts into compact AI context without losing their provenance.

* **Unsupported Claim Reduction**
  Helps prevent AI from generating business claims that are inconsistent with verified Business Intelligence output.

---

### 6. Graph-Aware Context Retrieval

Uses Business Graph traversal to retrieve connected context around an entity, issue, or business question.

**Features:**

* **Entity-Centered Graph Retrieval**
  Starts from a customer, order, product, campaign, conversation, or other graph node and retrieves relevant connected entities.

* **Relationship-Constrained Retrieval**
  Selects only graph paths relevant to the current task instead of expanding the entire graph.

* **Multi-Hop Context**
  Supports questions where useful context requires traversing several relationships.

* **Journey Context Retrieval**
  Retrieves customer, product, order, or campaign journey subgraphs when those views are useful to the AI task.

* **Evidence-Aware Paths**
  Preserves references to the authoritative relationships supporting graph edges.

* **Graph Context Compression**
  Converts potentially large graph structures into concise context that fits the AI request.

* **Cross-Domain Reasoning Context**
  Allows AI to reason over connected business activity without directly joining every canonical data table itself.

---

### 7. Memory Retrieval

Retrieves relevant business knowledge, policies, goals, historical decisions, and approved suggestions from Business Memory.

**Features:**

* **Knowledge Retrieval**
  Searches business documents and knowledge chunks for information relevant to the current AI task.

* **Policy Retrieval**
  Retrieves delivery, refund, support, or other policies when a response or suggested action depends on business rules.

* **Historical Decision Retrieval**
  Finds previous decisions related to similar business issues or contexts.

* **Approved Suggestion Retrieval**
  Retrieves previously accepted recommendations so AI can avoid repeatedly proposing the same strategy.

* **Business Goal Retrieval**
  Includes active goals when recommendations need to be prioritized or evaluated.

* **Brand Tone Retrieval**
  Retrieves communication guidelines for customer-facing responses or marketing assistance.

* **Hybrid Retrieval**
  Uses keyword, vector, metadata, and contextual search together to select relevant business memory.

* **Source Traceability**
  Preserves the original knowledge source and document references used to ground the AI output.

---

### 8. Customer-Aware AI

Provides AI capabilities that understand the current customer using unified identity-resolved business context.

**Features:**

* **Customer Profile Context**
  Retrieves canonical customer information and relevant tags.

* **Customer Journey Context**
  Uses website activity, campaigns, orders, payments, shipments, conversations, and calls associated with the customer.

* **Purchase History Awareness**
  Understands previous orders, products purchased, order values, cancellations, and refunds.

* **Support History Awareness**
  Includes prior conversations, escalations, resolutions, and support notes where appropriate.

* **Delivery Context**
  Considers previous delivery successes, failures, returns, and courier interactions.

* **Customer Value Context**
  Uses verified customer metrics or facts when available instead of asking AI to independently calculate customer value.

* **Personalized Assistance**
  Produces more relevant customer-support or business insights using the customer's established context.

---

### 9. Product-Aware AI

Provides AI reasoning and assistance grounded in canonical product information, product knowledge, and verified product performance.

**Features:**

* **Product Context Retrieval**
  Retrieves canonical product attributes and related product variants.

* **Product Knowledge Retrieval**
  Uses product guides, FAQs, troubleshooting content, and approved product documentation.

* **Product Performance Context**
  Includes verified sales, conversion, revenue, return, or delivery-related findings.

* **Campaign Context**
  Retrieves campaigns and marketing outcomes associated with the product where supported by verified relationships.

* **Customer Context**
  Uses aggregated customer or purchase patterns produced by Business Intelligence when relevant.

* **Support Context**
  Connects recurring support problems or customer complaints with specific products where deterministic evidence supports the connection.

* **Product Recommendation Explanation**
  Allows AI to explain why a product may require attention or investment using existing metrics and facts.

---

### 10. Order-Aware AI

Provides AI capabilities grounded in the complete context of a canonical order.

**Features:**

* **Order Detail Context**
  Retrieves order status, items, totals, timestamps, and customer references.

* **Payment Awareness**
  Includes associated payments and refunds when answering order-related questions.

* **Shipment Awareness**
  Retrieves courier, tracking, delivery status, delivery failures, and returns.

* **Conversation Awareness**
  Includes support conversations associated with the order.

* **Call Awareness**
  Retrieves relevant order-related calls where available.

* **Marketing Context**
  Includes campaign and session attribution when verified relationships exist.

* **Order Journey Retrieval**
  Uses the Business Graph order journey to provide a connected representation of the complete order lifecycle.

* **Order Issue Explanation**
  Explains order-related problems using verified operational data instead of assumptions.

---

### 11. Conversation Summarization

Produces concise summaries of customer support conversations for agents, managers, and AI workflows.

**Features:**

* **Conversation Summary**
  Condenses long message histories into the major customer request, responses, actions, and current state.

* **Customer Intent Summary**
  Identifies the main purpose of the conversation, such as delivery inquiry, cancellation, refund request, or product question.

* **Important Detail Extraction**
  Surfaces relevant order references, product names, dates, requested actions, and other important context.

* **Resolution Summary**
  Describes whether the problem was resolved, remains pending, or requires follow-up.

* **Handover Summary**
  Generates concise context when transferring a conversation between AI and human agents.

* **Internal Context Summary**
  Can include relevant internal notes and operational context while keeping customer-visible and internal information separated.

* **Summary Metadata**
  Preserves when and by which AI model the summary was generated.

---

### 12. Call Summarization

Converts call transcripts and metadata into concise business-useful summaries.

**Features:**

* **Transcript Summarization**
  Produces a concise overview of the important content discussed during a call.

* **Call Purpose Identification**
  Identifies whether the call relates to order confirmation, support, delivery, sales, cancellation, or another business purpose.

* **Important Detail Extraction**
  Extracts relevant products, orders, customer concerns, requested actions, or promised follow-ups.

* **Outcome Summary**
  Summarizes whether the call resulted in confirmation, cancellation, escalation, follow-up, or another outcome.

* **Customer Concern Summary**
  Captures major complaints, objections, or questions raised by the customer.

* **Conversation Context Integration**
  Allows call summaries to contribute to the broader customer and support context.

* **AI Retrieval Context**
  Makes call information usable without repeatedly injecting full call transcripts into future AI requests.

---

### 13. Recommendation Generation

Generates actionable business suggestions using verified issues, facts, graph context, business goals, and organizational memory.

**Features:**

* **Issue-Based Recommendations**
  Generates suggestions in response to structured Business Issues rather than attempting to independently discover authoritative problems.

* **Fact-Grounded Recommendations**
  Uses verified facts and associated metrics as supporting context.

* **Cross-Domain Recommendations**
  Can suggest actions based on evidence spanning marketing, customer, website, support, delivery, or other business domains.

* **Goal-Aware Recommendations**
  Prioritizes suggestions that support active business goals.

* **Historical Awareness**
  Considers previous decisions and approved suggestions before recommending a similar action.

* **Policy Awareness**
  Avoids recommendations that conflict with explicit business rules or policies.

* **Confidence Indication**
  Provides a confidence or certainty signal where appropriate.

* **Recommendation Classification**
  Supports categories such as marketing optimization, courier change, support improvement, product strategy, customer retention, and website optimization.

Example:

```text id="eh4f3o"
Issue:
HIGH_DELIVERY_FAILURE

Evidence:
- Gazipur failure rate: 18%
- Business average: 7%
- Courier X handles 76% of Gazipur failures

Memory:
Courier Y is approved for Gazipur deliveries.

Goal:
Reduce delivery failure below 10%.

AI Recommendation:
Route a controlled portion of Gazipur orders
through Courier Y and compare delivery success
against Courier X.
```

---

### 14. Recommendation Evidence

Maintains explicit references between AI recommendations and the evidence used to produce them.

**Features:**

* **Fact References**
  Connects recommendations with supporting Business Facts.

* **Issue References**
  Links recommendations to the Business Issues they are intended to address.

* **Metric References**
  Includes relevant metric snapshots when quantitative evidence is important.

* **Relationship References**
  References deterministic business relationships used during reasoning.

* **Graph References**
  Preserves graph nodes and edges that contributed contextual information.

* **Knowledge References**
  Links recommendations to relevant business-memory chunks, policies, or historical decisions.

* **Evidence Weighting**
  Supports relevance or importance values when multiple evidence sources contribute differently.

* **Recommendation Explainability**
  Allows users to inspect why a recommendation was generated rather than treating it as an opaque model response.

---

### 15. Suggested Actions

Converts recommendations into structured proposed operations that can be reviewed before execution.

**Features:**

* **Action Proposal Generation**
  Creates structured actions such as pausing a campaign, changing a courier, contacting a customer, or creating a support task.

* **Target Entity Selection**
  Identifies the customer, campaign, product, order, courier, or other entity affected by the proposed action.

* **Action Payload Generation**
  Produces the parameters required if the action is later executed through an external integration.

* **Simulated Actions**
  Allows the prototype to demonstrate execution flows without modifying real external business systems.

* **Action Status**
  Tracks states such as suggested, approved, rejected, executing, executed, and failed.

* **Recommendation Linking**
  Preserves the connection between an action and the recommendation that produced it.

* **Action Explanation**
  Provides the rationale and evidence needed for a user to understand the proposed operation.

---

### 16. Approval & Execution

Controls the transition from an AI-suggested operation to an authorized business action.

**Features:**

* **Explicit Approval Workflow**
  Requires user or system approval before configured actions can modify business systems.

* **Approval Status Tracking**
  Records whether an action was approved, rejected, or remains pending.

* **Approval Notes**
  Allows decision-makers to record why an action was accepted or rejected.

* **Execution Routing**
  Sends approved operations to the appropriate Business Operations or Integration workflow.

* **Simulated Execution**
  Supports prototype execution without sending real requests to providers.

* **Execution Result Tracking**
  Records provider responses, resulting state, or errors when an approved action is executed.

* **Failed Action Handling**
  Captures failures and prevents AI from incorrectly assuming that an operation succeeded.

* **Post-Execution Context**
  Makes action results available for future analysis and historical decision memory.

---

### 17. AI Audit

Maintains traceability of AI interactions, outputs, evidence, recommendations, and actions.

**Features:**

* **AI Conversation History**
  Stores user and assistant messages associated with Business Brain AI sessions.

* **Model Tracking**
  Records which AI model generated a response, summary, recommendation, or other output.

* **Context Tracking**
  Preserves references to relevant facts, graph context, knowledge, or business entities supplied during generation.

* **Recommendation History**
  Maintains previously generated recommendations and their lifecycle.

* **Approval History**
  Tracks whether recommendations and actions were accepted or rejected.

* **Execution History**
  Records which AI-generated actions were eventually executed.

* **Evidence Traceability**
  Allows important AI claims and recommendations to be traced back to their evidence.

* **Audit Metadata**
  Stores timestamps and generation metadata useful for debugging, evaluation, and governance.

---

### 18. AI Guardrails

Defines constraints that prevent AI from overstepping authoritative business systems or performing unsafe or unsupported actions.

**Features:**

* **Authoritative Data Boundary**
  Prevents AI-generated claims from automatically becoming canonical business data.

* **Identity Guardrail**
  Prevents LLM inference alone from creating authoritative cross-source identity links.

* **Relationship Guardrail**
  Prevents AI from directly creating verified Business Relationships without deterministic validation.

* **Fact Guardrail**
  Prevents unsupported AI observations from being stored as verified Business Facts.

* **Issue Guardrail**
  Requires Business Issues to originate from the Business Intelligence rules rather than unverified model interpretation.

* **Action Approval Guardrail**
  Requires explicit approval for configured business-impacting operations.

* **Policy Compliance**
  Ensures customer-facing responses and proposed actions respect relevant business policies.

* **Evidence Requirement**
  Requires recommendations or important analytical explanations to reference sufficient supporting context.

* **Context Isolation**
  Ensures one business's data and memory are not retrieved into another business's AI context.

* **Prompt Injection Resistance**
  Treats retrieved documents and external content as data rather than automatically trusting embedded instructions.

* **Uncertainty Handling**
  Allows AI to communicate when available evidence is insufficient instead of inventing a definitive conclusion.

---

## AI Context Architecture

AI should not receive arbitrary raw business data and independently determine business reality.

The preferred context pipeline is:

```text id="c2m88n"
User / AI Task
      ↓
Task Classification
      ↓
Context Retrieval
      │
      ├── Canonical Business Data
      ├── Verified Business Facts
      ├── Business Issues
      ├── Metric Evidence
      ├── Business Relationships
      ├── Business Graph
      ├── Business Memory
      └── Historical AI / Decisions
      ↓
Context Selection & Compression
      ↓
AI Model
      ↓
Explanation / Summary / Recommendation
      ↓
Evidence Attachment
      ↓
Suggested Action
      ↓
Approval
      ↓
Execution
```

This gives the AI rich context while preserving a clear boundary between **reasoning** and **authoritative business state**.

---

## Business Assistant Example

A user may ask:

> Why did revenue decrease this month even though our Meta campaign generated more orders?

Business Brain can construct context such as:

```text id="fhz0wb"
Business Intelligence
---------------------
Meta orders: +24%
Campaign spend: +11%
Campaign ROAS: stable

Delivery failure: 8% → 19%
Returns: +31%
Refunded revenue: +27%

Business Graph
--------------
Meta Campaign
    ↓
Customers
    ↓
Orders
    ↓
Courier X
    ↓
Failed Deliveries / Returns

Business Memory
---------------
Goal:
Increase realized monthly revenue.

Historical Decision:
Courier X previously showed poor
performance in Gazipur.
```

AI can then explain:

```text id="ww2yxl"
The campaign is successfully generating additional
orders, but a large portion of the incremental orders
are not becoming realized revenue.

The strongest evidence is the increase in failed
deliveries, returns, and refunds. Most of those failures
are concentrated among orders fulfilled by Courier X.
```

The important distinction is that AI **explains the verified pattern**. It did not independently invent the revenue decline, delivery failure rate, or campaign relationship.

---

## AI Output Trust Model

Different AI outputs have different authority levels:

```text id="p54c8d"
AI Answer
   ↓
Informational

AI Summary
   ↓
Derived / Non-authoritative

AI Recommendation
   ↓
Advisory

Suggested Action
   ↓
Proposed

Approved Action
   ↓
Authorized

Executed Action
   ↓
Operational Result
```

AI output should therefore never silently transition from:

```text id="k1lkn6"
"AI thinks this should happen"
```

to:

```text id="zldgxe"
"The business has done this"
```

without the appropriate approval and execution lifecycle.

---

## Deterministic Intelligence vs AI Intelligence

The separation between these domains is fundamental.

```text id="wky00p"
Business Intelligence
---------------------
Calculates
Detects
Verifies
Establishes relationships
Produces facts
Produces issues


AI Intelligence
---------------
Explains
Summarizes
Answers questions
Generates recommendations
Suggests actions
Communicates findings
```

For example:

```text id="bws20u"
Business Intelligence:

Metric:
Delivery failure rate = 18%

Fact:
Delivery failure increased from 9% to 18%.

Issue:
HIGH_DELIVERY_FAILURE


AI Intelligence:

Explanation:
"The increase is concentrated in Gazipur
orders handled by Courier X."

Recommendation:
"Test Courier Y for a portion of Gazipur orders."

Suggested Action:
CHANGE_COURIER
```

This boundary is what prevents the AI layer from becoming the uncontrolled source of business truth.

---

## Domain Boundary

The **AI Intelligence** domain answers:

**“Given what Business Brain already knows and has verified, how can that information be explained, summarized, used to answer questions, or converted into useful recommendations and proposed actions?”**

It does not own canonical business records, external connectivity, cross-source identity resolution, deterministic metrics, authoritative relationships, verified business facts, or issue detection.

Its primary inputs are:

**Business Data + Identity + Business Intelligence + Business Graph + Business Memory**

Its outputs are:

**Answers + Summaries + Diagnoses + Recommendations + Suggested Actions**

The overall reasoning architecture is:

**Canonical Data → Resolved Identity → Deterministic Intelligence → Graph + Memory → AI Context → AI Reasoning → Evidence-Backed Recommendation → Approval → Action**

The core principle is:

**AI Intelligence can interpret and advise on business reality, but it should not be allowed to silently define that reality.**
