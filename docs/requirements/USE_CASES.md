# Bizora Use Case Specification

**Companion to:** [Bizora SRS](SRS.md)
**Revision:** 1.0
**Reviewed:** 7 November 2026

## 1. Actors and conventions

The use cases below describe user-visible behavior that is reachable through the current root URL configuration unless a case is explicitly marked **service-only / not mounted**. The API is available below both `/api/` and `/api/v1/`; examples use `/api/`.

| Actor | Role |
| --- | --- |
| Viewer | Authenticated member with read access. |
| Operator | Authenticated member allowed to update ordinary business records and support operations. |
| Manager | Owner or manager authorized for identity review and proposal decisions. |
| Owner | Business administrator with the same manager review scope and ownership responsibility. |
| Integration adapter | Trusted server-side provider implementation. |
| AI gateway | Optional language generation service configured by `BIZORA_LLM_URL`. |

Preconditions common to business use cases: the user is active, authenticated, and has an active membership in the business. Resource IDs and related records must belong to that same business. Invalid or stale state is rejected; the API does not permit arbitrary model writes.

## 2. Use case index

| ID | Use case | Primary actor | Main requirements | Availability |
| --- | --- | --- | --- | --- |
| UC-01 | Select a business and inspect operations overview | Viewer | FR-01, FR-11, FR-13 | Available at `/ops/` and `/api/businesses/{business_id}/overview/` |
| UC-02 | Find and inspect a customer’s 360 record | Viewer | FR-02, FR-03, FR-11 | Available |
| UC-03 | Ingest or replay a canonical business event | Operator | FR-02–FR-08 | Available |
| UC-04 | Advance a record through its valid lifecycle | Operator | FR-04, FR-06–FR-07 | Available |
| UC-05 | Handle a support conversation | Operator | FR-11–FR-13 | Available |
| UC-06 | Generate a support reply suggestion | Operator | FR-16–FR-17 | Available; gateway optional |
| UC-07 | Resolve an external identity and review a conflict | Manager | FR-09–FR-10 | Available |
| UC-08 | Review a possible identity merge | Manager | FR-10 | Available; consolidation blocked |
| UC-09 | Review and execute an AI action proposal | Manager / Operator | FR-14, FR-17 | Proposal review available; execution simulated or adapter-dependent |
| UC-10 | Prepare an outbound operation | Operator | FR-15, FR-24 | Preparation available; provider execution unavailable without owner adapter |
| UC-11 | Query business information with the assistant | Viewer | FR-16–FR-18 | Available; answer may use fallback |
| UC-12 | Configure a business rule or policy | Manager | FR-21 | Service-only / route not mounted |
| UC-13 | Diagnose integration health and retry a failed record | Manager | FR-22 | Service-only / route not mounted |
| UC-14 | Review KPI trends and evidence drill-down | Viewer | FR-19, FR-23 | Service-only / route not mounted for BI/Overview APIs |
| UC-15 | Retrieve a business graph journey | Viewer | FR-20 | Graph API service-only / route not mounted; narrow graph context available |

## 3. Detailed use cases

### UC-01 Select a business and inspect the operations overview

**Primary actor:** Viewer
**Goal:** Select an authorized business and see a concise view of its operational records.
**Entry point:** `GET /ops/`, then `/ops/business/{business_id}/overview/` or `GET /api/businesses/{business_id}/overview/`.

**Preconditions:** The user has an active business membership.
**Trigger:** The user opens the operations UI or requests the overview API.

**Main flow:**

1. The user signs in and opens the business selector.
2. The system lists businesses for which the user has an active membership.
3. The user selects a business.
4. The system checks the membership and role, then returns scoped summary sections.
5. The user opens a section or record detail to continue work.

**Alternatives and errors:**

- If the user is unauthenticated, the UI redirects to login and the API denies access.
- If the business is not in the user’s active membership set, the system returns a denial or not-found response.
- If a BI or monitoring measure has no configured owner, the projection identifies it as unavailable or omits the unavailable analysis; it does not fabricate a metric.

**Postconditions:** No canonical data is changed.
**Notes:** This core operations overview is distinct from the richer `app.overview` KPI/health module, whose route module is not mounted.

### UC-02 Find and inspect a customer’s 360 record

**Primary actor:** Viewer
**Goal:** Find one customer and inspect related canonical records and context.
**Entry points:** `GET /api/businesses/{business_id}/customers/?q=...`, `GET /api/businesses/{business_id}/customers/{id}/`, `GET /api/businesses/{business_id}/customers/{id}/360/`, or the Customer 360 UI section.

**Preconditions:** Active membership and a customer belonging to the selected business.
**Trigger:** The actor searches for a customer or opens Customer 360.

**Main flow:**

1. The actor supplies a supported search term or filter.
2. The system validates filters and returns a bounded, paginated list in stable order.
3. The actor selects a customer.
4. The system returns the customer plus available contacts, tags, timeline, orders, support context, source identity, and evidence-backed graph/context projections.
5. The actor follows a related record into its detail view.

**Alternatives and errors:**

- Unsupported filters, bad date formats, and invalid page values are rejected.
- A customer or related entity owned by another business is not returned.
- Optional domain-owner context may be `UNAVAILABLE` if no adapter is configured.

**Postconditions:** No canonical data is changed.
**Related requirements:** FR-01–FR-03, FR-11, FR-13, FR-24.

### UC-03 Ingest or replay a canonical business event

**Primary actor:** Operator or trusted ingestion caller
**Goal:** Store a validated event as canonical business data while preserving source identity and replay safety.
**Entry point:** `POST /api/businesses/{business_id}/{resource}/`.

**Preconditions:** The caller has an active business membership with write access; any connection and parent records belong to that business.
**Trigger:** An operator or trusted adapter submits canonical input.

**Main flow:**

1. The caller submits an allowlisted resource name, canonical payload, optional source connection/event time, and optional `Idempotency-Key`.
2. The system validates the payload shape, required fields, related entity ownership, status, finite JSON, and domain invariants.
3. The system checks source reference and replay receipt rules.
4. In a transaction, the system creates or updates the canonical record and its supported nested children/history.
5. The system returns the serialized record; a new record returns HTTP 201, while an accepted replay/update can return HTTP 200.

**Alternatives and errors:**

- Same key and same content: the prior event result is reused according to the owning service’s idempotency rules.
- Same key with changed content: reject with an idempotency conflict.
- Stale source timestamps or contradictory mappings: reject without overwriting newer canonical state.
- Invalid money, attachment, nested reference, or cross-business relationship: reject atomically.
- Unknown resource or unsupported fields: reject; arbitrary Django model CRUD is not exposed.

**Postconditions:** A valid canonical record and associated source/history evidence exist.
**Related requirements:** FR-02–FR-08, NFR-03–NFR-05.

### UC-04 Advance a record through its valid lifecycle

**Primary actor:** Operator
**Goal:** Record a state change that is allowed for the resource’s current state.
**Entry points:** `POST /api/businesses/{business_id}/{resource}/{id}/transition/` or a state-aware UI command.

**Preconditions:** Operator has write access; record belongs to the business; requested transition is permitted by `app/domains/states.py`.
**Trigger:** The operator selects a next state and supplies a reason and, where supported, expected current state.

**Main flow:**

1. The system loads the scoped record and current lifecycle state.
2. The system validates requested transition against the explicit transition map.
3. If an expected state was supplied, the system confirms the record has not changed since it was read.
4. The system persists the new state and transition history atomically.
5. The system returns the updated record.

**Alternatives and errors:**

- Invalid or terminal transition: reject with validation/state conflict and make no change.
- A stale expected state: reject so the operator can refresh and review current state.
- Provider side effect: none is implied by a local state change. Integration execution requires a separate owner operation.

**Postconditions:** State and history are updated only if the transition is valid.
**Related requirements:** FR-04, FR-06–FR-07.

### UC-05 Handle a support conversation

**Primary actor:** Operator
**Goal:** Triage, assign, hand over, prioritize, and record conversation work.
**Entry points:** Support queue, conversation detail, or `/api/businesses/{business_id}/conversations/{id}/...` commands.

**Preconditions:** Operator has write access; conversation belongs to the business.
**Trigger:** A new or existing conversation requires attention.

**Main flow:**

1. The operator opens the queue and optionally filters by status, channel, priority, or assignment.
2. The system returns open/pending conversations in priority order and does not claim SLA/escalation calculations when the policy owner is unavailable.
3. The operator opens the conversation and reviews messages, customer context, and any associated order context.
4. The operator assigns the conversation to an agent/team, adjusts priority, marks a message read, records a private note, or changes AI/human handover state.
5. The system validates same-business ownership and assignment rules, records the change, and returns the updated state.

**Alternatives and errors:**

- Invalid assignee, team, or handover state: reject without changing the conversation.
- Another active assignment conflicts with the requested change: resolve through the assignment service’s explicit replacement/uniqueness rule or return conflict.
- Queue analytics or SLA thresholds unavailable: show capability as unavailable; do not invent an overdue status.
- A saved UI reply or media attachment is pending and remains unsent until an integration owner executes it.

**Postconditions:** The conversation state and operational history reflect the operator’s command.
**Related requirements:** FR-11–FR-13.

### UC-06 Generate a support reply suggestion

**Primary actor:** Operator
**Supporting actor:** Optional AI gateway
**Goal:** Receive a draft response grounded in recent messages and available business/customer/order policy context.
**Entry point:** `POST /api/businesses/{business_id}/ai/support/suggest-reply/`.

**Preconditions:** User is authenticated and has business access; conversation and optional order belong to the same business and customer.
**Trigger:** Operator submits conversation ID and optional order ID/intent.

**Main flow:**

1. The system validates the request and loads the scoped conversation and optional order.
2. The system assembles recent conversation messages, customer/order context, and active policy memory.
3. The system calls the configured LLM gateway with a bounded timeout.
4. The system stores an AI audit record and returns suggested text and the policies/context referenced.
5. The operator reviews and edits the suggestion before any separate send operation.

**Alternatives and errors:**

- No gateway or gateway failure: return the configured fallback text and provider status where exposed.
- Invalid or cross-customer order: reject; no cross-tenant or unrelated order context is accepted.
- Generation is not equivalent to sending. The use case does not change message delivery state or contact the customer.

**Postconditions:** AI audit data may be recorded; no canonical customer communication is sent.
**Related requirements:** FR-16–FR-18, NFR-07–NFR-08.

### UC-07 Resolve an external identity and review a conflict

**Primary actor:** Manager
**Goal:** Link a source identity to the appropriate canonical entity or disposition a conflict with rationale.
**Entry point:** `GET/POST /api/businesses/{business_id}/identity/{command}/` and identity UI section.

**Preconditions:** Manager membership; canonical and external identities are in the same business.
**Trigger:** A source identity is new, ambiguous, stale, or conflicts with an existing mapping.

**Main flow:**

1. The manager lists external identities, links, conflicts, or history with supported filters.
2. The manager reviews identity type, source, evidence, verification state, and current link.
3. The manager chooses a supported command such as register, resolve, link, unlink, verify-contact, enrich, or review-conflict.
4. The system validates scope, uniqueness, and the command’s required evidence/reason.
5. The system records the result and history, returning `RESOLVED`, `NO_MATCH`, or `CONFLICT` as appropriate.

**Alternatives and errors:**

- Ambiguous or contradictory evidence: record conflict; do not force an automatic link.
- Cross-business target or an already-active conflicting link: reject or return conflict.
- Missing confidence evidence: preserve confidence as unknown rather than inventing a probability.

**Postconditions:** Identity registry and audit/history show the reviewed action.
**Related requirements:** FR-09–FR-10.

### UC-08 Review a possible identity merge

**Primary actor:** Manager
**Goal:** Review a duplicate candidate and understand affected relationships before any possible consolidation.
**Entry point:** Identity review UI or `POST /api/businesses/{business_id}/identity/merge-candidates/{id}/dry-run/`.

**Preconditions:** Manager membership; candidate and both identities belong to the business.
**Trigger:** Candidate detection identifies a possible duplicate.

**Main flow:**

1. The manager reviews candidate evidence and decides whether the candidate itself is valid.
2. The manager may approve/reject the candidate with a reason.
3. The manager requests a dry-run plan, optionally supplying the expected fingerprint from a previously viewed plan.
4. The system inventories known local relationships and receipts and requests reconciliation from configured downstream owners.
5. The system returns a plan and owner statuses; it makes no physical identity consolidation.

**Alternatives and errors:**

- Fingerprint changed: reject stale plan and require a fresh review.
- Owner adapter missing, unavailable, or unsafe: report the owner result and do not claim preservation.
- Candidate rejected: retain the rejection rationale; do not merge.
- A request to execute physical merge is blocked pending guarantees for external stores, redirects/reprojection, retries, and durable downstream acknowledgements.

**Postconditions:** A reviewed candidate and/or non-destructive plan exists; canonical customer records remain separate.
**Related requirements:** FR-10.

### UC-09 Review and execute an AI action proposal

**Primary actor:** Manager for review; Operator for the legacy action execution endpoint
**Goal:** Decide whether a suggested action may proceed and retain the human decision.
**Entry points:** Action list, `POST /api/businesses/{business_id}/actions/{id}/review/`, or `POST /api/actions/{id}/approve|reject|execute/`.

**Preconditions:** Action, recommendation, and evidence belong to the same business. Required role depends on endpoint; current role models differ across legacy and domain endpoints.
**Trigger:** An AI or other trusted service has created a `SUGGESTED` action.

**Main flow:**

1. The reviewer inspects the recommendation, linked evidence, target, and proposed payload.
2. The reviewer approves or rejects with a reason/note.
3. The system verifies action state and records reviewer identity and time.
4. If an approved action is explicitly executed, the action service claims execution before invoking an external executor.
5. The system stores execution result and audit outcome.

**Alternatives and errors:**

- Missing approval or illegal lifecycle state: reject execution.
- Simulated action without executor: the service records a simulated success result.
- Non-simulated action without executor: reject; real provider behavior requires a trusted executor.
- Provider failure: record `FAILED`; interrupted actions may stay `EXECUTING` for manual reconciliation.
- External execution inside a surrounding transaction: reject to avoid unsafe external side effects within a database rollback boundary.

**Postconditions:** Human decision and action execution outcome are auditable. Approval alone does not change canonical business data.
**Related requirements:** FR-14, FR-17, NFR-06–NFR-08.

### UC-10 Prepare an outbound operation

**Primary actor:** Operator
**Supporting actor:** Integrations owner adapter, if configured
**Goal:** Build an outbound request from canonical state without allowing arbitrary client overrides.
**Entry point:** `POST /api/businesses/{business_id}/operations/{operation}/{id}/prepare/` or the owner contract capability.

**Preconditions:** Operator has write access; target record is in the selected business and eligible for the requested operation.
**Trigger:** Operator asks to prepare a message, call, or shipment operation.

**Main flow:**

1. The operator selects the operation and canonical target.
2. The system rejects a request body that attempts to override canonical values.
3. The system validates target state and builds a bounded owner request from stored data.
4. The configured owner adapter receives a versioned envelope, if present.
5. The system returns prepared request and availability/provenance, with execution explicitly not completed.

**Alternatives and errors:**

- Target not eligible or wrong operation/entity combination: reject.
- No adapter configured or owner timeout: return `UNAVAILABLE`.
- Fixture adapter: return `simulated: true`; result is not a real provider acknowledgement.

**Postconditions:** No delivery/call/shipment is claimed unless a distinct real executor performs it and records an outcome.
**Related requirements:** FR-15, FR-24.

### UC-11 Query business information with the assistant

**Primary actor:** Viewer
**Supporting actor:** Optional AI gateway
**Goal:** Ask a natural-language question and receive an answer with available business context.
**Entry point:** `POST /api/businesses/{business_id}/ai/assistant/query/`.

**Preconditions:** User is authenticated and has active business membership.
**Trigger:** User submits query text and optional AI conversation ID/intent.

**Main flow:**

1. The system validates the query and confirms any supplied conversation belongs to the business and assistant workflow.
2. The system classifies intent using deterministic rules where applicable.
3. The system assembles tenant-scoped fact, issue, customer/product/order, graph, and memory context available to that code path.
4. The system calls the LLM gateway or produces its configured fallback.
5. The system stores the AI conversation/messages and returns the answer and available evidence/context metadata.

**Alternatives and errors:**

- Provider absent/fails: return fallback/unavailable behavior; do not treat fallback prose as a verified metric.
- A requested analytical capability is not configured: report unavailable or lack of evidence.
- The answer does not itself create a fact, metric, issue, identity link, or action execution.

**Postconditions:** AI conversation audit may be stored; authoritative records remain unchanged.
**Related requirements:** FR-16–FR-18.

### UC-12 Configure a business rule or policy (service-only / not mounted)

**Primary actor:** Manager
**Goal:** Create or update a versioned rule/policy and inspect its effective value and history.
**Code entry points:** `app.configuration.views.ResourceView`, `EffectiveView`, and `HistoryView`; intended URL family is under a business configuration prefix, but `app.configuration.urls` is not included by root URL configuration.

**Preconditions:** If the route is mounted, a manager must have the separate `BusinessAccess` grant.
**Main flow:**

1. Manager reads the selected policy/rule and current revision.
2. Manager submits a strict bounded schema and stable lowercase key.
3. System validates scope, dates, version, rule DSL, platform guardrails, and permitted source references.
4. System writes a new revision and a durable configuration change event.
5. Consumers request effective configuration for a scope/workflow and receive revision provenance.

**Alternatives and errors:**

- Invalid DSL, unknown provider/model/source, cross-business reference, or policy outside platform guardrails: reject with no revision.
- Optimistic version conflict: require manager to reload and reconcile.
- The current repository has no root route for this use case; it is not callable as a product HTTP flow until URL mounting and grant mapping are completed.

**Postconditions:** A versioned configuration record exists if successful. Downstream processing is not claimed merely because a change event exists.
**Related requirements:** FR-21.

### UC-13 Diagnose integration health and retry a failed record (service-only / not mounted)

**Primary actor:** Manager
**Supporting actor:** Trusted integration adapter
**Goal:** Inspect connection/sync/webhook failures and retry an eligible operation with audit.
**Code entry points:** `app.observability.views`, `app.observability.services`, and `app.observability.operations`; `app.observability.urls` is not mounted.

**Preconditions:** Manager has a separate observability `BusinessAccess` grant; connection belongs to the business; retry is allowed by state and policy.
**Main flow:**

1. Manager reviews scoped summary, connection/provider status, freshness, failed-record groups, or a sanitized diagnostic.
2. Manager opens a failure and reviews category, stage, occurrence, and redacted evidence.
3. Manager requests an allowed retry/replay using an idempotency key.
4. System verifies eligibility, records an operation attempt, invokes the registered adapter, and records success/failure plus audit.
5. Freshness advances only after the owning processor confirms canonical persistence.

**Alternatives and errors:**

- Unsupported live adapter: mark operation unsupported; do not fabricate a successful retry.
- Duplicate request key: return the prior operation outcome or an idempotency conflict if the payload differs.
- Invalid signature or unsafe payload: reject/quarantine and preserve diagnostic state.
- The current repository has no root HTTP route for this flow.

**Postconditions:** Observation and attempt history show what was tried and whether canonical processing was confirmed.
**Related requirements:** FR-22, NFR-04, NFR-06.

### UC-14 Review KPI trends and evidence drill-down (service-only / not mounted)

**Primary actor:** Viewer
**Goal:** Inspect configured business metrics, trends, health, findings, and source evidence.
**Code entry points:** `app.overview.views`, `app.business_intelligence.api`, and their service modules; their URL modules are not mounted.

**Preconditions:** A business context is authorized by the respective API grant; metrics/facts and evidence are available for the selected window.
**Main flow:**

1. Viewer selects a configured reporting window and optional scope/filter.
2. System resolves effective overview configuration and metric catalog.
3. System returns KPI values/trends and freshness/health annotations from stored snapshots and evidence.
4. Viewer selects a finding or value and opens its evidence/entity detail.

**Alternatives and errors:**

- Missing metric source or stale/incomplete input: return unavailable/unknown freshness rather than zero or fabricated success.
- Missing evidence or wrong-business entity reference: omit or reject the drill-down.
- BI/Overview HTTP endpoints cannot currently be reached through root URLs; core `/overview/` is a separate simpler summary.

**Postconditions:** Read-only. No configuration, finding, or canonical record is changed.
**Related requirements:** FR-19, FR-23.

### UC-15 Retrieve a business graph journey

**Primary actor:** Viewer
**Goal:** Explore connected customer, order, product, or campaign relationships over a tenant-scoped graph.
**Code entry points:** `app.business_graph.api` and `app.business_graph.urls` define traversal, paths, query, journeys, snapshots, and rebuild; URL module not mounted. Core graph-context projection is available through `/api/businesses/{business_id}/graph-context/{kind}/{id}/`.

**Preconditions:** Viewer has access to the business; graph projection is current enough for the intended question.
**Main flow (reachable context projection):**

1. Viewer requests graph context for a supported entity kind and ID.
2. System validates the entity belongs to the business and returns bounded connected context.
3. Viewer uses the context as supporting evidence for operational review.

**Main flow (full graph API, once mounted):**

1. Caller requests traversal, path search, journey, snapshot, or rebuild with supported filters and bounds.
2. Graph service checks business scope and resolves projected graph nodes/edges.
3. System returns matching nodes/edges/path or a stored snapshot.

**Alternatives and errors:**

- Missing/stale projection: return empty/unknown context or a rebuild-required outcome; do not claim a complete journey.
- Cross-business node, unsupported filters, or invalid traversal bounds: reject.
- Full graph API is currently not mounted.

**Postconditions:** Read-only query, except an explicitly requested graph rebuild/snapshot through the currently unmounted graph API.
**Related requirements:** FR-20, FR-24.

## 4. Requirement-to-use-case mapping

| Requirement | Covered by |
| --- | --- |
| FR-01–FR-02 / tenant access | UC-01–UC-15 preconditions and scope checks |
| FR-03–FR-08 / canonical data | UC-02–UC-05 |
| FR-09–FR-10 / identity | UC-07–UC-08 |
| FR-11–FR-13 / operations UI | UC-01–UC-05 |
| FR-14, FR-17 / proposal review | UC-09 |
| FR-15, FR-24 / adapter boundary | UC-09–UC-10 |
| FR-16–FR-18 / AI and knowledge | UC-06, UC-11 |
| FR-19 / BI | UC-14 |
| FR-20 / Graph | UC-15 |
| FR-21 / Configuration | UC-12 |
| FR-22 / Observability | UC-13 |
| FR-23 / Overview | UC-14 |

## 5. Source references

- Root mounts: `bizora/urls.py`; API routes: `app/urls.py`; UI routes: `app/operations_urls.py`.
- Canonical views and scoped resource registry: `app/domain_views.py`, `app/domains/registry.py`.
- Domain policies: `app/domains/data.py`, `app/domains/identity.py`, `app/domains/operations.py`, `app/domains/merge.py`, `app/domains/states.py`.
- Operational UI and command forms: `app/operations_ui.py`, `app/templates/operations/`.
- AI endpoints and lifecycle: `app/views.py`, `app/services/ai*.py`, `app/services/actions.py`.
- Owner contract: `app/domains/boundaries.py`, `app/domains/contracts.py`.
- Unmounted API packages: `app/business_intelligence/urls.py`, `app/business_graph/urls.py`, `app/configuration/urls.py`, `app/observability/urls.py`, `app/overview/urls.py`.
- Prior subfeature inventories and evidence: `docs/implementations/my-domains-requirements-audit.md`, `docs/implementations/business-configuration-progress.md`, `docs/implementations/integration-data-observability-progress.md`, and `docs/implementations/overview-monitoring-progress.md`.
