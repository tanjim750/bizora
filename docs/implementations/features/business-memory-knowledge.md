# Business Memory & Knowledge

## Description

The **Business Memory & Knowledge** domain stores the durable business context that cannot be derived only from transactional data. It represents what the business knows about itself, including policies, product guidance, brand tone, goals, support instructions, historical decisions, and previously approved recommendations.

This domain also provides the retrieval infrastructure required to make that knowledge usable by AI Intelligence and other downstream systems. It supports document ingestion, chunking, embeddings, vector search, keyword search, hybrid retrieval, and versioning while preserving the original source and context of every knowledge item.

---

## Features

### 1. Business Profile

Stores foundational information describing the business, its operating model, identity, positioning, and general characteristics.

**Features:**

* **Business Identity Information**
  Stores structured information such as business name, description, industry, operating regions, target customers, and other relevant business context.

* **Business Description**
  Maintains a concise explanation of what the business does, what it sells, and how it operates.

* **Business Context for AI**
  Provides AI systems with stable background information so responses and recommendations are aligned with the actual business.

* **Operating Context**
  Stores information such as business model, sales channels, delivery model, support model, and other operational characteristics.

* **Profile Source Tracking**
  Preserves whether profile information came from manual entry, imported documents, websites, or another approved source.

---

### 2. Business Policies

Stores general rules and policies that guide how the business operates and makes decisions.

**Features:**

* **Policy Repository**
  Maintains business rules covering areas such as customer service, order handling, payment, delivery, refunds, discounts, and internal operations.

* **Policy Categorization**
  Classifies policies by area so they can be retrieved efficiently for relevant workflows.

* **Policy Applicability**
  Allows policies to specify the context or business process where they apply.

* **Policy Retrieval**
  Makes relevant policies available to AI systems and operational workflows when decisions or responses require policy awareness.

* **Policy Source Traceability**
  Preserves the original document or manually entered source from which a policy was derived.

* **Policy Lifecycle**
  Supports active, superseded, archived, or otherwise historical policy states.

---

### 3. Product Knowledge

Stores descriptive and operational knowledge about products beyond the canonical product fields maintained by Business Data.

**Features:**

* **Product Guides**
  Stores detailed information about product features, usage, benefits, limitations, compatibility, or recommended use.

* **Product FAQs**
  Maintains common questions and answers related to individual products or product categories.

* **Product Support Information**
  Stores troubleshooting guidance, usage instructions, and customer-support context related to products.

* **Product Positioning**
  Maintains information describing how products should be presented or differentiated to customers.

* **Product Knowledge Association**
  Connects knowledge content with relevant canonical products or product categories.

* **Product-Aware Retrieval**
  Allows AI systems to retrieve only the knowledge relevant to the product involved in a support, sales, or analytical context.

---

### 4. Delivery Policy

Stores business-specific rules and expectations related to shipping, courier handling, delivery times, charges, and fulfillment.

**Features:**

* **Delivery Coverage Rules**
  Stores where the business delivers and any geographic restrictions or special conditions.

* **Expected Delivery Times**
  Maintains expected delivery durations by region, courier, shipping type, or other business-defined conditions.

* **Delivery Charge Rules**
  Stores delivery fees and rules governing when different charges apply.

* **Courier Preferences**
  Maintains business guidance about preferred or restricted courier providers.

* **Failed Delivery Handling**
  Stores instructions for handling failed delivery attempts, customer contact, re-delivery, or return processes.

* **COD Rules**
  Preserves business-specific cash-on-delivery policies where relevant.

* **Delivery Support Context**
  Provides policy information to support agents and AI when customers ask about delivery conditions.

---

### 5. Return & Refund Policy

Maintains the business's approved rules for product returns, cancellations, replacements, refunds, and related customer requests.

**Features:**

* **Return Eligibility Rules**
  Defines which products or orders can be returned and under what conditions.

* **Return Window**
  Stores how long customers have to request a return.

* **Refund Eligibility**
  Defines circumstances under which full or partial refunds are allowed.

* **Refund Method Rules**
  Stores how approved refunds should be returned to the customer.

* **Replacement Rules**
  Defines when products should be replaced instead of refunded.

* **Non-Returnable Conditions**
  Maintains exclusions such as specific product categories, opened products, damaged goods, or other business rules.

* **Cancellation Policy**
  Stores conditions governing order cancellation before shipment or fulfillment.

* **Policy-Aware Support**
  Enables support AI and agents to provide answers grounded in the approved refund and return policy.

---

### 6. Brand Tone

Defines how the business should communicate with customers and external audiences.

**Features:**

* **Tone Definition**
  Stores preferred communication characteristics such as professional, friendly, concise, premium, casual, or empathetic.

* **Writing Style Guidelines**
  Defines sentence style, vocabulary preferences, level of formality, and other communication conventions.

* **Preferred Terminology**
  Stores business-specific words, product terminology, greetings, closings, and naming conventions.

* **Restricted Language**
  Defines words, promises, claims, or communication styles that should not be used.

* **Channel-Specific Tone**
  Allows communication style to vary between customer support, marketing, social media, email, or other channels.

* **AI Tone Grounding**
  Provides the context required for AI-generated replies and content to remain consistent with the business's communication identity.

---

### 7. Support Knowledge

Stores information used by customer support teams and AI systems to resolve customer questions consistently.

**Features:**

* **Support Guides**
  Maintains step-by-step instructions for handling common customer problems.

* **Support FAQs**
  Stores frequently asked questions and approved responses.

* **Troubleshooting Knowledge**
  Maintains known problems, causes, and recommended solutions.

* **Escalation Guidance**
  Defines cases that should be escalated to specific teams or human agents.

* **Order Support Knowledge**
  Stores guidance for cancellations, delayed orders, status questions, payment issues, and similar scenarios.

* **Delivery Support Knowledge**
  Maintains approved handling instructions for delayed, failed, damaged, or returned shipments.

* **Product Support Knowledge**
  Stores product-specific troubleshooting and customer guidance.

* **Support AI Retrieval**
  Provides context that Customer Support AI can retrieve before generating a suggested reply.

---

### 8. Business Goals

Stores explicit business objectives so analysis and AI recommendations can be evaluated against what the business is trying to achieve.

**Features:**

* **Goal Definition**
  Maintains objectives such as increasing revenue, reducing delivery failures, improving retention, or increasing campaign efficiency.

* **Goal Categorization**
  Organizes goals into areas such as sales, marketing, customer support, delivery, product, or operational efficiency.

* **Goal Priority**
  Allows the business to indicate which objectives are strategically more important.

* **Target Values**
  Supports measurable targets such as desired conversion rate, ROAS, revenue, or delivery success rate.

* **Goal Timeframe**
  Stores target dates or evaluation periods where goals are time-bound.

* **AI Recommendation Alignment**
  Allows AI Intelligence to prioritize suggestions that directly contribute to active business goals.

* **Goal History**
  Preserves completed or changed goals for historical decision context.

---

### 9. Historical Decisions

Stores important business decisions and their context so the system can remember previous choices.

**Features:**

* **Decision Records**
  Maintains decisions such as changing a courier, pausing a campaign, modifying a policy, or adjusting a business process.

* **Decision Rationale**
  Stores why a particular decision was made when the rationale is available.

* **Decision Context**
  Associates relevant issues, facts, metrics, recommendations, or business conditions with the decision.

* **Decision Outcome**
  Allows later results or observations to be connected with previous decisions.

* **Historical Retrieval**
  Enables AI to retrieve similar decisions when analyzing a new but related business problem.

* **Repeat Decision Prevention**
  Helps avoid repeatedly suggesting actions that were previously tried and rejected or found ineffective.

* **Organizational Memory**
  Preserves important operational knowledge even when individual employees or decision-makers change.

---

### 10. Approved Suggestions

Stores recommendations or suggestions that were explicitly accepted by the business and are considered useful historical knowledge.

**Features:**

* **Approved Recommendation Memory**
  Preserves AI or human recommendations that were reviewed and approved.

* **Recommendation Context**
  Maintains the business issue, facts, evidence, or circumstances that originally led to the recommendation.

* **Approval Information**
  Records that the recommendation passed an explicit approval process rather than being automatically treated as truth.

* **Action Outcome Context**
  Allows results from approved actions to be stored alongside the original suggestion.

* **Future Recommendation Context**
  Enables AI to consider previously accepted strategies when producing new recommendations.

* **Duplicate Suggestion Reduction**
  Helps prevent AI from repeatedly proposing the same already-addressed action.

> Raw AI output should not automatically become Business Memory. Only explicitly approved or intentionally retained suggestions should be promoted into durable knowledge.

---

### 11. Knowledge Sources

Represents the origin and classification of information stored inside the Business Memory system.

**Features:**

* **Source Registry**
  Maintains sources such as documents, manually entered information, websites, imports, system-generated knowledge, or prototype mock data.

* **Knowledge Type Classification**
  Categorizes sources as business profile, product knowledge, delivery policy, refund policy, brand tone, support knowledge, business goals, historical decisions, or approved suggestions.

* **Source Reference**
  Preserves information needed to trace knowledge back to its original source.

* **Source Metadata**
  Stores source-specific attributes such as URLs, upload information, labels, ownership, or ingestion details.

* **Source Status**
  Maintains whether a knowledge source is active, archived, or otherwise unavailable for normal retrieval.

* **Business Isolation**
  Ensures knowledge sources belong to the correct business and are not mixed across tenants.

---

### 12. Document Ingestion

Imports business documents and textual knowledge into the Business Memory processing pipeline.

**Features:**

* **Document Upload**
  Accepts supported documents containing business policies, product guides, FAQs, support information, or other business knowledge.

* **Manual Text Ingestion**
  Allows knowledge to be entered directly without requiring a file.

* **Website Content Ingestion**
  Supports importing business-owned website content where appropriate.

* **Imported Knowledge**
  Allows structured or unstructured content from other business systems to enter the knowledge pipeline.

* **Source Association**
  Connects every ingested document with its corresponding Knowledge Source.

* **File Metadata Preservation**
  Stores file name, MIME type, source location, or related document metadata.

* **Ingestion Status Tracking**
  Tracks documents through pending, processing, ready, failed, or archived states.

---

### 13. Document Processing

Transforms ingested content into clean, structured text that can be searched and retrieved reliably.

**Features:**

* **Text Extraction**
  Extracts textual content from supported source documents.

* **Content Cleaning**
  Removes unnecessary formatting, duplicated content, navigation elements, or other noise where appropriate.

* **Structure Preservation**
  Preserves useful document structure such as headings, sections, pages, and lists.

* **Content Normalization**
  Converts content into a consistent representation for downstream chunking and retrieval.

* **Processing Validation**
  Ensures required content was extracted successfully before marking the document as ready.

* **Content Hashing**
  Supports hashes or equivalent mechanisms to detect duplicate or unchanged document content.

* **Processing Metadata**
  Stores information about extraction and processing for debugging and traceability.

---

### 14. Knowledge Chunking

Splits large knowledge documents into smaller retrievable units while preserving their original context.

**Features:**

* **Chunk Generation**
  Divides documents into manageable text segments suitable for keyword and semantic retrieval.

* **Ordered Chunks**
  Maintains chunk sequence so the original document structure can be reconstructed when necessary.

* **Section-Aware Chunking**
  Uses headings and document structure where available to avoid unnecessarily mixing unrelated concepts.

* **Chunk Metadata**
  Stores information such as heading, page, policy type, product, category, or other useful retrieval attributes.

* **Token-Aware Chunking**
  Keeps chunks within practical token limits for embedding and AI context generation.

* **Source Traceability**
  Maintains a direct reference from every chunk back to its source document.

* **Context Preservation**
  Avoids creating fragments that lose the meaning required to answer business questions correctly.

---

### 15. Embeddings

Creates semantic vector representations of knowledge chunks for meaning-based retrieval.

**Features:**

* **Chunk Embeddings**
  Generates an embedding vector for each eligible knowledge chunk.

* **Embedding Model Tracking**
  Records which model produced each vector.

* **Embedding Dimensions**
  Preserves vector dimensionality so storage and retrieval remain compatible with the selected embedding model.

* **Embedding Regeneration**
  Allows vectors to be regenerated when the content or embedding model changes.

* **Multiple Model Support**
  Allows knowledge chunks to maintain embeddings from different models if required.

* **Vector Storage**
  Supports vector-capable storage such as PostgreSQL with `pgvector`.

* **Semantic Retrieval Foundation**
  Provides the representation required to search by conceptual similarity rather than exact words.

---

### 16. Vector Search

Retrieves knowledge based on semantic similarity between a query and stored knowledge embeddings.

**Features:**

* **Semantic Similarity Search**
  Finds chunks whose meaning is similar to the user's or system's query even when exact terminology differs.

* **Top-K Retrieval**
  Returns the most semantically relevant knowledge chunks according to similarity ranking.

* **Metadata Filtering**
  Restricts vector searches by knowledge type, product, policy, source, document, or other metadata.

* **Business Isolation**
  Ensures semantic search only retrieves knowledge belonging to the current business.

* **Similarity Scoring**
  Provides relevance scores that can later be used during ranking and context selection.

* **Context Retrieval**
  Supplies relevant business knowledge to AI Intelligence before generating an answer, explanation, or recommendation.

---

### 17. Keyword Search

Retrieves knowledge using exact terms, phrases, identifiers, and lexical matching.

**Features:**

* **Exact Term Matching**
  Finds knowledge containing specific words, phrases, SKU values, policy names, or other exact identifiers.

* **Full-Text Search**
  Supports efficient lexical search across document and chunk content.

* **Business Terminology Search**
  Performs well for business-specific terms that may not rely on semantic similarity.

* **Metadata Search**
  Searches by document title, source, product, policy category, or other stored metadata.

* **Filtered Keyword Retrieval**
  Combines keyword matching with knowledge type and business-specific filters.

* **Relevance Ranking**
  Ranks results according to lexical relevance rather than merely returning unordered matches.

---

### 18. Hybrid Retrieval

Combines semantic search, keyword search, metadata, and contextual filters to produce higher-quality knowledge retrieval.

**Features:**

* **Vector + Keyword Search**
  Combines semantic similarity with exact lexical matching.

* **Result Fusion**
  Merges candidate results from multiple retrieval methods into a single ranked result set.

* **Metadata-Aware Retrieval**
  Uses source, knowledge type, product, policy, or other metadata to improve result relevance.

* **Context-Aware Filtering**
  Uses the current task to restrict retrieval, such as retrieving only delivery policy when answering a delivery question.

* **Relevance Ranking**
  Scores and ranks retrieved knowledge according to combined signals.

* **Evidence Preservation**
  Returns source and document references alongside retrieved chunks so AI responses can remain grounded.

* **AI Context Optimization**
  Selects only the most relevant knowledge needed for a given AI task instead of injecting the entire business knowledge base.

A typical retrieval flow can look like:

```text id="xyj4pz"
User / AI Query
       ↓
Query Classification
       ↓
┌───────────────────┐
│   Keyword Search  │
└─────────┬─────────┘
          │
          ├──────────────┐
          │              │
┌─────────▼─────────┐    │
│   Vector Search   │    │
└─────────┬─────────┘    │
          │              │
          └──────┬───────┘
                 ↓
          Result Fusion
                 ↓
        Metadata Filtering
                 ↓
           Re-Ranking
                 ↓
     Relevant Knowledge Chunks
                 ↓
          AI Intelligence
```

---

### 19. Knowledge Versioning

Preserves changes in business knowledge so Business Brain can distinguish current guidance from historical information.

**Features:**

* **Document Versions**
  Maintains sequential versions when policies, guides, or other knowledge documents change.

* **Historical Knowledge Preservation**
  Keeps previous versions available for audit or historical analysis instead of overwriting them permanently.

* **Current Version Resolution**
  Identifies which version should be used for normal retrieval and AI context.

* **Version Metadata**
  Records version numbers, timestamps, source changes, and other relevant update information.

* **Policy Change Tracking**
  Preserves changes to important policies such as refund, delivery, or customer support rules.

* **Embedding Version Alignment**
  Ensures updated document chunks can receive new embeddings rather than silently reusing vectors from outdated content.

* **Historical Decision Context**
  Allows Business Brain to understand which policy or knowledge version was active when a previous decision was made.

* **Stale Knowledge Prevention**
  Prevents archived or superseded knowledge from being treated as current business guidance unless historical retrieval is explicitly requested.

---

## Knowledge Processing Flow

Business Memory separates knowledge acquisition from knowledge retrieval:

```text id="j74rpt"
Business Knowledge
      ↓
Knowledge Source
      ↓
Document Ingestion
      ↓
Document Processing
      ↓
Knowledge Document
      ↓
Knowledge Chunking
      ↓
Knowledge Chunks
      ↓
┌─────────────────────┐
│ Embedding Generation│
└──────────┬──────────┘
           ↓
       Embeddings

Knowledge Chunks
     │        │
     ▼        ▼
Keyword    Vector
 Search     Search
     │        │
     └────┬───┘
          ↓
    Hybrid Retrieval
          ↓
   Relevant Knowledge
          ↓
     AI Intelligence
```

---

## Business Memory vs Business Data

These two concepts should remain separate.

```text id="61322h"
Business Data
"What happened?"

Examples:
- Order #1024 was created.
- Payment of BDT 2,500 succeeded.
- Shipment failed.
- Customer sent a message.


Business Memory
"What does the business know, prefer, or require?"

Examples:
- Delivery inside Dhaka normally takes 1–2 days.
- Refunds are allowed within 7 days.
- The brand should communicate politely and concisely.
- Courier X was previously avoided in Gazipur.
- Increasing Campaign A's budget was previously rejected.
```

Business Data represents operational state and events.

Business Memory represents durable organizational knowledge and context.

---

## Business Memory vs Business Intelligence

Business Intelligence should not be used as long-term policy storage, and Business Memory should not independently invent analytical conclusions.

For example:

```text id="pyco04"
Business Intelligence:

Fact:
"Courier X has a 19% delivery failure rate
in Gazipur during the last 30 days."

Issue:
"Courier X performance in Gazipur is unusually poor."


Business Memory:

Policy:
"For high-risk Gazipur deliveries,
prefer Courier Y when available."

Historical Decision:
"Courier X was reduced in Gazipur
after delivery issues in May."


AI Intelligence:

Recommendation:
"Shift more Gazipur orders from Courier X
to Courier Y."
```

The recommendation becomes stronger because AI can combine **current verified reality** from Business Intelligence with **durable organizational context** from Business Memory.

---

## Approved Knowledge Lifecycle

Not every piece of generated information should automatically become durable business memory.

A safe lifecycle is:

```text id="i8t3lk"
AI Suggestion
      ↓
Human Review
      ↓
Approved
      ↓
Action / Decision
      ↓
Relevant Outcome
      ↓
Historical Decision
or
Approved Suggestion
      ↓
Business Memory
```

This avoids allowing unverified AI output to silently modify the business's long-term knowledge.

---

## Domain Boundary

The **Business Memory & Knowledge** domain answers:

**“What does this business know, believe, prefer, require, or remember from previous decisions?”**

It does not own transactional business entities; those belong to **Business Data**.

It does not determine cross-platform identity; that belongs to **Identity & Resolution**.

It does not calculate revenue trends, anomalies, or verified business problems; those belong to **Business Intelligence**.

It does not independently create relationships between business entities; those are established through Business Intelligence and projected by **Business Graph**.

It provides durable context to **AI Intelligence**, which can combine:

```text id="mta9v4"
Current Business State
        +
Verified Business Facts
        +
Business Issues
        +
Business Graph
        +
Business Memory
        ↓
Grounded AI Context
        ↓
Explanation
Recommendation
Suggested Action
Customer Support Response
Marketing Assistance
Business Diagnosis
```

The core principle is:

**Business Intelligence tells Business Brain what is happening now; Business Memory tells it what the business already knows and how the business wants to operate.**
