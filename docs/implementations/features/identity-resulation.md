# Identity & Resolution

## Description

The **Identity & Resolution** domain is responsible for determining when records originating from different platforms represent the same real-world business entity. It creates a stable identity layer above provider-specific identifiers so Business Brain can connect fragmented customer, product, order, session, conversation, payment, shipment, campaign, and call data.

The domain uses deterministic matching and explicit evidence to create and maintain identity links. It is a critical foundation for cross-source relationships, Customer 360, attribution, Business Graph construction, analytics, and AI context.

---

## Features

### 1. Canonical Identity

Provides the stable internal identity that Business Brain uses to represent an entity independently of any external platform.

**Features:**

* **Canonical Identity Registry**
  Maintains a centralized registry of canonical identities belonging to a business, allowing different domain entities to participate in the same identity-resolution framework.

* **Canonical Entity Mapping**
  Associates each canonical identity with its corresponding domain entity, such as a customer, product, order, payment, campaign, session, conversation, call, or shipment.

* **Canonical Identity Keys**
  Assigns stable internal identifiers such as `CUST-000001`, `PROD-000045`, or `ORD-000928` that remain independent of provider identifiers.

* **Entity Type Classification**
  Identifies what type of business entity an identity represents so resolution rules can be applied within appropriate entity boundaries.

* **Identity Status Management**
  Tracks whether a canonical identity is active, merged, superseded, or otherwise unavailable for normal resolution.

* **Canonical Identity Assignment**
  Creates or selects the appropriate canonical identity after external records have been evaluated by deterministic resolution rules.

---

### 2. External Identity

Represents identities and identifiers observed in external platforms before or during their association with canonical Business Brain entities.

**Features:**

* **External Identity Registry**
  Maintains provider-specific identities received from commerce, communication, analytics, marketing, courier, calling, and other connected systems.

* **Provider Identity Preservation**
  Preserves identifiers such as WooCommerce customer IDs, Messenger PSIDs, Telegram user IDs, GA4 client IDs, phone numbers, and other provider-specific references.

* **Identity Type Classification**
  Distinguishes identifiers such as `EMAIL`, `PHONE`, `WHATSAPP_PHONE`, `PSID`, `CLIENT_ID`, `EXTERNAL_CUSTOMER_ID`, and other supported identity types.

* **Identity Value Normalization**
  Standardizes comparable values such as email addresses and phone numbers before they participate in deterministic matching.

* **Source Association**
  Records which integration connection or external provider produced an identity.

* **Identity Metadata**
  Preserves provider-specific attributes, source context, timestamps, and additional information that may help resolution or auditing.

* **First/Last Seen Tracking**
  Records when an external identity first appeared and when it was most recently observed.

---

### 3. Identity Linking

Creates explicit, traceable mappings between external identities and canonical Business Brain identities.

**Features:**

* **External-to-Canonical Linking**
  Associates an external identity with the canonical identity that represents the same entity inside Business Brain.

* **Match Type Tracking**
  Records how a link was established, such as `EXACT`, `DETERMINISTIC`, `MANUAL`, `MERGED`, or `ANONYMOUS_TO_KNOWN`.

* **Resolution Rule Tracking**
  Stores the deterministic rule responsible for producing an identity link so the result remains explainable.

* **Confidence Tracking**
  Stores a confidence value where the resolution mechanism produces different levels of certainty.

* **Link Status Management**
  Allows identity links to be activated, invalidated, superseded, or removed without losing historical resolution context.

* **Manual Resolution Support**
  Allows ambiguous identities to be explicitly linked by an authorized user when deterministic rules cannot safely resolve them.

* **Link Traceability**
  Maintains when, why, and by which mechanism an identity relationship was established.

> AI may assist with explaining ambiguous identity information, but authoritative identity links should not be created solely from an LLM inference.

---

### 4. Cross-Source Matching

Determines whether identities observed across independent platforms belong to the same canonical business entity.

**Features:**

* **Exact Identifier Matching**
  Matches identities when reliable normalized identifiers are identical, such as the same verified email address or normalized phone number.

* **Deterministic Multi-Field Matching**
  Combines multiple available attributes according to explicit rules when a single identifier is insufficient.

* **Cross-Platform Customer Matching**
  Connects customer identities originating from commerce, communication, website analytics, calling, and other systems.

* **Cross-Platform Product Matching**
  Resolves provider-specific product records against canonical products using identifiers such as SKU, external references, and configured deterministic rules.

* **Order Reference Matching**
  Connects order references observed in payments, courier systems, communication events, or other sources with their canonical orders.

* **Context-Aware Matching**
  Uses appropriate identifiers based on entity type and source instead of applying one universal matching rule to every entity.

* **Match Evidence Collection**
  Preserves the attributes and rules that caused two records to be considered equivalent.

* **Match Rejection**
  Prevents a canonical link when available identifiers contradict each other or deterministic confidence requirements are not satisfied.

A typical customer resolution may look like:

`WooCommerce Customer 52 + Messenger PSID + WhatsApp Phone + GA4 Client ID → Canonical Customer C1`

---

### 5. Anonymous Identity Linking

Connects previously anonymous activity with a known canonical entity when reliable identifying information becomes available later.

**Features:**

* **Anonymous Visitor Identity**
  Allows website visitors and sessions to exist without requiring an immediately known customer.

* **Anonymous Activity Preservation**
  Retains browsing sessions, product views, cart events, campaign interactions, and other activity while the visitor remains unidentified.

* **Identity Transition Detection**
  Detects when an anonymous identity later provides a reliable identifier through events such as login, checkout, purchase, form submission, or communication.

* **Anonymous-to-Known Linking**
  Links an existing anonymous identity to the appropriate canonical customer when deterministic evidence supports the association.

* **Historical Journey Recovery**
  Allows earlier anonymous activity to become part of the resolved customer's journey after identity resolution.

* **Cross-Session Continuity**
  Preserves relationships between multiple sessions where stable visitor identifiers make deterministic continuity possible.

* **Attribution Continuity**
  Enables marketing and conversion analysis to connect pre-identification campaign interactions with later known customer outcomes when evidence supports the link.

---

### 6. Merge Detection

Detects cases where multiple canonical identities may actually represent the same real-world entity.

**Features:**

* **Duplicate Identity Detection**
  Identifies potentially duplicated canonical identities using deterministic matching rules and normalized identifiers.

* **Merge Candidate Generation**
  Creates reviewable merge candidates rather than immediately combining uncertain canonical identities.

* **Match Reason Recording**
  Records why two identities were considered potential duplicates, such as matching phone numbers, emails, external references, or combinations of identifiers.

* **Merge Confidence**
  Assigns confidence information to help distinguish strong duplicate candidates from ambiguous cases.

* **Merge Candidate Review**
  Supports states such as pending, approved, rejected, and merged so potentially destructive identity operations can be controlled.

* **Canonical Identity Consolidation**
  Allows approved duplicate identities to be consolidated under a selected canonical identity.

* **Relationship Preservation**
  Ensures existing orders, conversations, sessions, calls, payments, shipments, and other relationships remain associated with the resulting canonical identity.

* **Duplicate Prevention**
  Uses existing identity mappings before creating new canonical identities to reduce unnecessary duplicate entities.

---

### 7. Identity Conflict Resolution

Detects and manages situations where identity evidence is contradictory, ambiguous, or unsafe to resolve automatically.

**Features:**

* **Multiple Match Detection**
  Detects when one external identity appears to match multiple canonical identities.

* **Conflicting Identifier Detection**
  Identifies situations where attributes such as phone numbers, emails, or external identifiers produce contradictory resolution results.

* **External ID Collision Detection**
  Detects cases where the same provider identifier is unexpectedly associated with multiple entities.

* **Cross-Source Conflict Detection**
  Identifies contradictions between identities coming from independent platforms.

* **Invalid Link Detection**
  Detects identity links that violate deterministic identity rules or known entity constraints.

* **Conflict Severity**
  Classifies conflicts using levels such as `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.

* **Conflict Lifecycle**
  Supports states such as `OPEN`, `REVIEWING`, `RESOLVED`, and `IGNORED`.

* **Manual Conflict Resolution**
  Allows ambiguous cases to be reviewed and explicitly resolved instead of forcing unsafe automatic matches.

* **Resolution Documentation**
  Stores resolution notes and relevant evidence so future systems can understand why a particular identity decision was made.

---

### 8. Identity History

Preserves the evolution of identity-resolution decisions so changes remain explainable and auditable over time.

**Features:**

* **Link History**
  Preserves when external identities were linked, unlinked, reassigned, or otherwise changed.

* **Merge History**
  Maintains information about canonical identities that were merged and which identity became authoritative.

* **Conflict History**
  Preserves detected conflicts and their eventual resolutions rather than discarding them after resolution.

* **Resolution Method History**
  Records whether an identity decision originated from an exact rule, deterministic matching rule, manual review, merge, or anonymous-to-known transition.

* **Rule Traceability**
  Preserves the rule or resolution mechanism associated with historical identity decisions.

* **Identity Evolution**
  Allows Business Brain to reconstruct how a fragmented set of external identities gradually became associated with a canonical entity.

* **Audit Support**
  Provides historical evidence needed to investigate incorrect matches, graph relationships, attribution results, or downstream analytical conclusions.

---

## Example Identity Resolution Flow

A customer may interact with a business through several unrelated platforms:

```text
WooCommerce
Customer ID: 52
Email: rahim@example.com
        │
        │
Messenger
PSID: 92837462
        │
        │
WhatsApp
Phone: +8801712345678
        │
        │
Website / GA4
Client ID: 12345.67890
        │
        ▼
External Identities
        │
        ▼
Normalization
        │
        ▼
Deterministic Matching
        │
        ├── Confident match ──→ Identity Link
        │
        ├── Possible duplicate → Merge Candidate
        │
        └── Contradiction ────→ Identity Conflict
        │
        ▼
Canonical Identity
CUST-000001
        │
        ▼
Canonical Customer C1
```

Once resolved, Business Brain can understand that the customer's website visit, Messenger conversation, WhatsApp interaction, WooCommerce order, payment, shipment, and call belong to the same customer journey.

---

## Domain Boundary

The **Identity & Resolution** domain answers:

**“Which internal business entity does this external identity represent?”**

It does not own the underlying customer, product, order, payment, conversation, or other business records. Those remain owned by **Business Data**.

It also does not determine business conclusions such as whether a customer is high-value, whether a campaign caused a purchase, or whether delivery performance is deteriorating. Those responsibilities belong to **Business Intelligence**.

The architectural flow is:

**Integrations → Business Data → Identity & Resolution → Business Intelligence → Business Graph → AI Intelligence**

For customer identity specifically:

**External Customer/Visitor/Participant → External Identity → Normalize → Match → Resolve → Canonical Identity → Canonical Customer**

This separation allows Business Brain to connect fragmented cross-platform data without allowing individual provider identifiers to become the system-wide source of truth.
