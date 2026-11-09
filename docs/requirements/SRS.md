# Bizora Software Requirements Specification

**Document type:** As-built Software Requirements Specification
**Revision:** 1.0
**Reviewed:** 7 November 2026
**System:** Bizora Django backend and operational UI

## 1. Purpose and reading guide

This document describes the behavior evidenced by the current repository. It is intended for product owners, implementers, testers, and teams integrating domain services. It is an as-built specification, not a promise that every feature in the original domain briefs is complete.

Requirement status has these meanings:

| Status | Meaning |
| --- | --- |
| Implemented | The repository has an executable path for the behavior. Reachability is stated separately when relevant. |
| Partial | Some behavior exists, while a documented dependency, decision, or lifecycle step remains. |
| Unavailable | The API or projection deliberately reports that an owner service is absent. |
| Not mounted | Code and a URL module exist, but the root URL configuration does not expose that module. |
| Blocked | The implementation report explicitly says the behavior must not proceed without an external preservation or policy decision. |

The canonical domain audit reports **229 COMPLETE, 66 PARTIAL, and 3 BLOCKED of 298 requirements** across Business Data, Identity & Resolution, and Business Operations. That count is limited to those three source specifications; it does not represent all code in the repository. Configuration, Integration & Data Observability, and Overview & Monitoring have separate implementation traceability documents. Their existence does not make their URL modules reachable.

## 2. Product scope

Bizora is a multi-business backend for maintaining canonical business records, resolving provider identities, supporting operational workflows, and exposing evidence and advisory context. It includes a server-rendered operations UI at `/ops/` and JSON APIs mounted at `/api/` and `/api/v1/`.

The system’s core responsibilities are:

1. Keep canonical business records in one tenant-scoped data model.
2. Validate source data, maintain source references, enforce lifecycle transitions, and record replay receipts.
3. Support human operational review and updates through bounded APIs and the operations UI.
4. Preserve evidence and source provenance for deterministic analytical facts, identity links, graph projections, and AI suggestions.
5. Require explicit human review for proposed AI actions and keep provider execution behind an owner adapter.

### 2.1 Included domains

| Domain | Current repository behavior | Reachability |
| --- | --- | --- |
| Business Data | Products/variants/images, customers/contacts/tags, orders/items, payments/refunds, conversations/messages/attachments/notes, campaigns/ads/conversions, website visitors/sessions/events, shipments/events, calls/transcripts/callbacks. | Canonical CRUD-like intake/list/detail/transition APIs and UI are mounted. |
| Identity & Resolution | Canonical and external identities, source-scoped links, verification, conflicts, history, anonymous visitor linkage, candidate detection/review, merge planning. | Manager identity endpoints and UI review are mounted. Destructive merge completion remains blocked. |
| Business Operations | Overview, customer context, support queue, assignment, handover, priority, callbacks, financial timeline, product assessment, action review, outbound request preparation. | Core operational endpoints and `/ops/` UI are mounted. |
| AI assistance | Assistant query, support draft/escalation/handover/resume, marketing explanation, issue diagnosis, conversation/call summaries, recommendation/action lifecycle. | AI endpoints are mounted. The LLM is an HTTP gateway configured by `BIZORA_LLM_URL`; without it, a fallback response is returned. Provider integrations may be absent. |
| Business Intelligence | Deterministic metric, revenue, product, customer, campaign, support, website, delivery, anomaly, relationship, fact, issue, and evidence services plus API views. | `app.business_intelligence.urls` exists but is not included by `bizora/urls.py` or `app/urls.py`. Treat the REST endpoints as unavailable in the deployed URL surface until mounted. In-process services exist. |
| Business Graph | Graph projection, traversal, path search, journey builders, snapshots, and rebuild API views. | `app.business_graph.urls` exists but is not mounted. A narrower graph-context projection is exposed through the core API. |
| Business Memory & Knowledge | Versioned source/document/chunk/embedding pipeline, hybrid retrieval, business policy/profile/goal memory, decision history, and approved suggestion promotion. | Services and models exist. They are consumed by some AI paths; there is no complete public CRUD API for the whole domain in the root URL map. |
| Business Configuration | Versioned profile/general/AI/knowledge/rule/policy/integration/source/freshness settings, effective configuration, history, and reprocessing requests. | `app.configuration.urls` exists but is not mounted. Configuration services are not reachable through a root HTTP route. |
| Integration & Data Observability | Immutable payload capture, observation receipts, connection/provider health, sync and webhook observations, failures, freshness, retry/replay operations, and audit. A deterministic mock product processor exists. | `app.observability.urls` exists but is not mounted. Live adapters beyond registered owner implementations are not supplied. |
| Overview & Monitoring | KPI cards/trends, configured windows, health, activity, findings, evidence drill-down, and overview configuration. | `app.overview.urls` exists but is not mounted. A smaller canonical `/overview/` operational projection is available. |
| Domain-owner contracts | Versioned request/response envelope for Integrations, BI, Graph, AI, Memory, Configuration, and Monitoring; response provenance and business scope checks. | Contract endpoint is mounted. Missing owner adapters return `UNAVAILABLE`; fixture responses are explicitly simulated. |

### 2.2 Out of scope or not claimed

- Live provider webhooks, synchronization schedules, provider credentials, and send/ship/call execution are not implied by canonical record storage or an outbound preparation response.
- AI output does not establish canonical facts, metrics, identity links, or issues. AI recommendations and actions do not silently change the underlying business state.
- Business Intelligence and Graph service code is not equivalent to an enabled public endpoint because the URL modules are not mounted.
- A merge dry-run is a plan and impact inventory. It does not consolidate customer identities or guarantee downstream preservation.
- The operational UI saves internal/pending records. It explicitly does not execute provider operations.
- The checked-in `db.sqlite3` is documented as a legacy, incompatible database and is not a supported migration target. PostgreSQL 16 is the authoritative target; SQLite is a local fallback.

## 3. System context and interfaces

### 3.1 Runtime and components

- Python/Django application with Django REST Framework, server-rendered Django templates, and ORM persistence.
- Runtime settings are in `bizora/settings.py`; local and PostgreSQL test settings are separate modules.
- Root URL configuration mounts `app.urls` twice (`/api/` and `/api/v1/`), the operations UI (`/ops/`), and Django admin (`/admin/`).
- The ORM in `app/models.py`, additive migrations, and the domain services are the canonical persistence and behavior definitions. `db_diagram.sql` is descriptive and is not the migration source of truth.
- PostgreSQL and SQLite are supported backends, with PostgreSQL providing locking and concurrency guarantees that SQLite cannot establish.

### 3.2 External interfaces

| Interface | Purpose | Current boundary |
| --- | --- | --- |
| JSON HTTP API | Canonical resource intake, reads, transitions, support and identity commands, AI requests, and domain-owner contracts. | JSON renderer; JSON/form/multipart parsers; authentication and tenant checks vary by view family. |
| Operations web UI | Authenticated browser access to thirteen operations areas, lists, details, and bounded commands. | Session authentication; write forms use POST and CSRF. No provider transport is called by UI commands. |
| LLM gateway | Optional AI generation through `BIZORA_LLM_URL`. | Bounded request timeout and fallback result; the gateway owns model choice, availability, and actual generation. |
| Domain adapters | Optional owner implementation configured server-side as `BIZORA_DOMAIN_ADAPTERS`. | Contract version `bizora.domain.v1`, finite JSON, request correlation, business/entity scope validation, and explicit simulation flag. |
| Integration processing | Provider-specific ingestion or outbound operations. | Trusted adapter protocol. Only mock product processing is provided in the integration prototype; other live provider behavior requires an owner adapter. |
| Database | Tenant-scoped canonical and supporting records. | PostgreSQL 16 is authoritative; local SQLite is a fallback. Existing legacy SQLite file must not be migrated. |

### 3.3 Mounted API families

The following route shapes are registered by the root URL map. `{id}` values are business-scoped except the status route and the action lifecycle URLs, which load their business from the action record and then authorize membership.

| Family | Route shape |
| --- | --- |
| Status | `GET /api/` and `GET /api/v1/` |
| Canonical resources | `/api/businesses/{business_id}/{resource}/`, `/api/businesses/{business_id}/{resource}/{id}/`, and `/api/businesses/{business_id}/{resource}/{id}/transition/` |
| Overview/support | `overview/`, `customers/{id}/360/`, `support-queue/`, conversation `assign/`, `handover/`, `priority/`, and `context/`, plus message `read/` |
| Identity | `identity/{command}/`, `identity/merge-candidates/{id}/dry-run/`, and product assessment |
| Other projections | `financial-timeline/`, `website-performance/`, visitor journey, customer retargeting context, graph context, callbacks, variant update |
| AI | `ai/assistant/query/`, support suggest/escalate/handover/resume, marketing explain-campaign, diagnosis, conversation/call summarization, recommendations, and actions |
| AI action lifecycle | `POST /api/actions/{id}/approve/`, `reject/`, and `execute/` |
| Owner seam | `POST /api/businesses/{business_id}/contracts/{owner}/{capability}/` |

Exact registered names and methods are maintained in `app/urls.py`, `bizora/urls.py`, and the individual view classes. The separate URL modules `app/business_intelligence/urls.py`, `app/business_graph/urls.py`, `app/configuration/urls.py`, `app/observability/urls.py`, and `app/overview/urls.py` are not mounted today.

## 4. Users and actors

| Actor | Capabilities evidenced in code |
| --- | --- |
| Anonymous visitor | Read the status endpoint only. Business APIs and the operations UI require authentication. |
| Business Viewer | Read tenant-scoped records and operational views. Cannot issue canonical writes. |
| Business Operator | Read and perform ordinary operational writes such as intake, status transitions, assignment, priority, handover, and callbacks. |
| Business Manager | Operator capabilities plus identity/conflict/merge-candidate review and action proposal review. |
| Business Owner | Manager capabilities and business administration. |
| Django superuser | Core domain authorization still generally requires an active business membership; some auxiliary subsystems grant superusers bypass access. Do not assume this exception is consistent across modules. |
| Integration owner/adapter | Supplies validated provider transport, source translation, processing confirmation, and execution behavior. Client requests cannot select an adapter class. |
| AI gateway | Produces optional language output from supplied prompt/context. The gateway is not authoritative for stored metrics or canonical state. |
| BI, Graph, Memory, Configuration, Monitoring owners | May provide domain capabilities through the versioned adapter seam. Missing adapters report unavailable. |
| System operator | Runs migrations, demo commands, preflight, and deployment configuration using trusted server access. |

### 4.1 Authorization rules and known inconsistency

The core domain service authorizer allows `OWNER`, `MANAGER`, and `OPERATOR` to write and permits `VIEWER` to read. Identity review requires manager-level access (`OWNER` or `MANAGER`). UI writes enforce membership, role, POST, and CSRF.

The configuration and observability packages use a separate `BusinessAccess` grant (`READER`/`MANAGER`), while observability also uses a distinct `BusinessAccess` model. Their URL trees are currently unmounted. If they are mounted, access grants and role mapping must be reconciled before treating authorization as uniform. Some legacy AI endpoints use `require_business_access` with a different role vocabulary (`OWNER`, `ADMIN`, `OPERATOR`) and do not match the documented `MANAGER` role exactly. This is a codebase integration concern, not a new permission promise.

## 5. Functional requirements

IDs below provide stable references for requirements and use cases. Status describes current code, and “reachable” distinguishes HTTP availability from an unmounted service/API module.

### 5.1 Tenant, identity, and data requirements

| ID | Requirement | Status / reachability |
| --- | --- | --- |
| FR-01 | The system shall authenticate business users and require an active business membership before exposing tenant data. | Implemented in core domain/UI; exceptions and role mapping differ in legacy AI and auxiliary packages. |
| FR-02 | The system shall scope reads, writes, and related-entity references to the active business and reject cross-business references. | Implemented in core domain services and serializers; tested according to implementation reports. |
| FR-03 | The system shall accept provider-independent canonical records for the supported resource families and expose paginated tenant-scoped lists and details. | Implemented and mounted for resources in `app/domains/registry.py`. Resource allowlist prevents arbitrary model CRUD. |
| FR-04 | The system shall validate canonical fields, nested relationships, finite JSON, contacts, monetary amounts, attachments, and state transitions before persistence. | Implemented; domain constraints supplement application checks. |
| FR-05 | The system shall preserve source identifiers and reject changed replays or stale/conflicting updates where an idempotency/source receipt applies. | Implemented for domain intake and selected integration observability services. Provider adapters remain separate. |
| FR-06 | The system shall preserve monetary and order invariants, including positive item/refund quantities, nonnegative money, refund capacity, and immutable order item snapshots. | Implemented in domain services/models per audit; external payment settlement is not claimed. |
| FR-07 | The system shall maintain explicit allowed transitions and history for supported lifecycle-managed records. | Implemented for registered resource/state combinations; unsupported transition is rejected. |
| FR-08 | The system shall maintain products, variants, images/references, customer contacts/tags/timeline, orders/payments/refunds, conversations/messages/attachments/notes, campaigns, web events, shipments, calls, and callbacks. | Implemented to varying audit status; see the 298-row domain audit for subfeature completion. |

### 5.2 Identity and operational requirements

| ID | Requirement | Status / reachability |
| --- | --- | --- |
| FR-09 | The system shall register canonical and source identities, record verified evidence, resolve deterministic matches, and preserve links, conflicts, and history. | Implemented and reachable through manager identity commands; exact match policy is conservative. |
| FR-10 | The system shall create, review, and reject merge candidates and expose a fingerprinted dry-run impact plan. | Candidate review and dry-run are implemented and reachable. Physical consolidation, full downstream guarantees, and final merge history are blocked/partial. |
| FR-11 | The system shall expose operational overview, Customer 360, financial timeline, support context/queue, website observations, retargeting context, and graph context from canonical records. | Core subset implemented and reachable; analytical add-ons may report unavailable. |
| FR-12 | The system shall allow authorized operators to assign conversations, hand over AI/human ownership, set priority, mark messages read, record private notes, prepare replies, and schedule callbacks. | Implemented and reachable. UI-saved replies/media are pending records and are not sent. |
| FR-13 | The system shall provide the operations UI with business selection, thirteen navigation sections, search/filter/paginated lists, record detail, and state-appropriate commands. | Implemented at `/ops/`; command set varies by resource and role. |
| FR-14 | The system shall allow a manager to review identity conflicts, merge candidates, and AI action proposals with a recorded decision/reason. | Implemented and reachable. Action approval authorizes proposal execution eligibility, not a real external operation. |
| FR-15 | The system shall prepare canonical outbound requests and return owner adapter availability/status without claiming delivery when no executor is present. | Implemented through operations preparation and versioned contracts. Live send/call/shipment provider actions are unavailable absent an adapter. |

### 5.3 Intelligence, knowledge, and integration requirements

| ID | Requirement | Status / reachability |
| --- | --- | --- |
| FR-16 | AI workflows shall receive tenant-scoped business context and return assistant answers, support/marketing/diagnostic suggestions, or summaries where a provider is available. | AI endpoints are mounted; provider uses `BIZORA_LLM_URL`, with fallback behavior when missing/failing. Generated content quality/availability depends on that gateway. |
| FR-17 | AI recommendations/actions shall preserve evidence/audit context and must not create authoritative business facts or execute an external action without explicit approval and an executor. | Human review and simulated lifecycle exist. External execution requires a trusted executor; UI does not execute providers. |
| FR-18 | Knowledge services shall ingest and version business documents, chunk/embed content, enforce tenant/domain boundaries, and provide keyword/vector/hybrid retrieval. | Service implementation exists and is consumed by AI; full public management API is not mounted. Embedding/provider availability is configuration-dependent. |
| FR-19 | BI shall calculate and record deterministic metrics, relationships, revenue and domain analysis, anomalies, evidence-backed facts, and issues. | In-process BI services and API views exist. BI URL module is not mounted, and live public access is unavailable. |
| FR-20 | Graph shall project canonical entities and relationships, support tenant-scoped traversal/path queries and journey/snapshot access. | Graph implementation and URL module exist, but URL module is not mounted. Narrower graph context is reachable. |
| FR-21 | Configuration shall persist versioned business settings, rules, policies, approved sources, effective values, and history with role checks. | Configuration services and URL module exist but are not mounted. |
| FR-22 | Observability shall record source receipts, connection/provider checks, sync/webhook events, failures, freshness, attempts, and audited recovery actions. | Services and URL module exist but are not mounted. Live adapters are limited to explicit implementations. |
| FR-23 | Overview shall present configured KPI windows, trends, health, activity, issue/recommendation evidence, and entity drill-downs. | Module and API implementation exist but are not mounted; basic operations overview is a separate reachable projection. |
| FR-24 | Domain-owner adapters shall exchange versioned, correlated, finite JSON envelopes with tenant/entity scope checks and explicit simulation provenance. | Implemented and reachable through the core contract endpoint; owner-specific semantics are not supplied by the envelope. |

## 6. Data requirements and invariants

1. Every canonical record and supporting evidence must be associated with a business, directly or through an explicitly validated parent relationship.
2. Parent-child entity links must resolve to the same business. Cross-tenant references are invalid.
3. Event and source keys are scoped by business and/or connection as defined by the owning service. Reusing a key with materially different content must fail rather than silently overwrite.
4. Money is represented as finite decimal amounts. Domain intake requires nonnegative values with at most two decimal places; refund amounts must be positive and within remaining refundable capacity.
5. Status changes are constrained by explicit transition maps. A caller may not set an arbitrary status through generic CRUD.
6. Identity confidence may be unknown. A manual link or shared SKU must not be presented as a calibrated probability without an approved scoring definition.
7. Facts, metrics, issues, AI recommendations, and canonical business records are separate concepts. An AI output is not an authoritative fact.
8. Captured integration payloads are immutable source evidence and must not be serialized through public diagnostics. Sensitive payload access needs explicit authorization and redaction.
9. Merge planning must report scope, inventory, and fingerprint; changing relationships invalidate a stale plan. No merge may be described as complete until downstream owners guarantee preservation.
10. Configuration revisions, domain audits, identity history, action audit events, and operational state histories provide provenance for selected changes.

## 7. Nonfunctional requirements

The repository defines safety controls but does not define general availability, throughput, recovery point, or response-time service levels. Numerical service objectives must be agreed separately; none are invented here.

| ID | Requirement | Evidence / boundary |
| --- | --- | --- |
| NFR-01 Tenant confidentiality | A user must not read or mutate another business’s records by substituting IDs or relationship references. | Business-scoped query helpers, related-object ownership checks, authorization tests, and anti-oracle behavior in BI/Graph packages. Verify each route family before deployment. |
| NFR-02 Authentication and write protection | Business APIs require authentication; browser writes require authenticated session, POST, and CSRF protection. | DRF default permission settings, explicit view permissions, and UI decorators/POST handlers. Public status endpoint is intentionally exempt. |
| NFR-03 Input safety | Reject malformed, oversized, non-finite, unsupported, or cross-scope values. | Strict serializers, finite JSON validation, bounded pagination, attachment validation, and contract depth/list bounds. |
| NFR-04 Replay safety | Repeated source events must not duplicate canonical records; changed content under the same idempotency key must conflict. | `ProcessingReceipt`, source reference constraints, and observability receipts. Exact scope differs by operation. |
| NFR-05 Concurrency safety | Concurrent mutations affecting shared business state must serialize or be protected by database constraints. | PostgreSQL row locks/transactions and constraints. SQLite tests do not establish production multi-writer safety. |
| NFR-06 Auditability | Sensitive decisions and lifecycle actions should record actor, reason, timestamps, and evidence where supported. | DomainAudit, IdentityHistory, action audit conversations, configuration revisions, observability audit. Coverage varies by domain. |
| NFR-07 AI fault containment | LLM calls have a bounded timeout and return a fallback on missing provider or failure. | `Business.execute_llm_with_timeout`; default service call timeout is 15 seconds. Gateway is external. |
| NFR-08 Human control | Recommendations do not silently become authoritative records or provider actions. | Suggested action lifecycle; approval identity/note; executor required for non-simulated action. Some older endpoints have role-model inconsistency. |
| NFR-09 Data integrity | Database constraints and domain validation must preserve key uniqueness, positive quantities, valid ranges, and parent relationships. | ORM model constraints and service validation; PostgreSQL is authoritative. |
| NFR-10 Maintainability and integration | Domain responsibilities use explicit services, allowlisted resources, typed adapters, and versioned contracts. | `app/domains/`, owner contract boundary, additive migration policy, and separate domain packages. |
| NFR-11 Accessibility/usability | UI must make current record state and available commands understandable. | Server-rendered templates and state-dependent forms exist. No conformance level or formal accessibility audit is recorded. |
| NFR-12 Operations and deployment | Production requires a private secret, correct database, migrations, trusted adapter configuration, and appropriate provider owner implementations. | Settings guard for `DEBUG=False`; README/setup guidance. The checked-in SQLite database is explicitly excluded. |

## 8. Error handling and state outcomes

- Core domain API returns structured codes for domain errors. Invalid input is generally HTTP 400; inaccessible resources are denied or hidden as not found according to the view; stale/idempotency/state conflicts use conflict responses where mapped.
- AI and domain-owner adapters can return fallback/unavailable outcomes. Callers must preserve status/provenance rather than treating an empty or fixture result as a real finding.
- Integration observability defines explicit receipt, validation, sync, webhook, failure, and operation-attempt states, but its HTTP API currently is not mounted.
- Action execution may end `EXECUTED` or `FAILED`; an interrupted provider attempt can remain `EXECUTING` for manual reconciliation. Automatic retry is unsafe without provider idempotency.
- Unsupported domain capability, state transition, filter, or resource name fails closed.

## 9. Acceptance and traceability

This specification is grounded in repository files and the existing requirement/test traceability documents. It does not claim a new test run or independent verification for every sentence.

| Requirement area | Primary implementation evidence | Existing traceability/evidence |
| --- | --- | --- |
| Canonical data and lifecycle | `app/models.py`, `app/domains/data.py`, `app/domains/registry.py`, `app/domain_views.py` | [298-requirement audit](../implementations/my-domains-requirements-audit.md), `app/test_domains.py`, `app/test_domain_completion.py`, `app/test_integration_readiness.py` |
| Identity and merge | `app/domains/identity.py`, `app/domains/merge.py`, `app/domain_views.py` | Same audit, `app/test_domains.py`, `app/test_integration_readiness.py` |
| Operations and UI | `app/domains/operations.py`, `app/domains/projections.py`, `app/operations_ui.py`, `app/operations_urls.py` | Implementation report, `app/test_integration_readiness.py` |
| AI, memory, knowledge | `app/views.py`, `app/services/ai*.py`, `app/services/domain_memory.py`, `app/services/knowledge_pipeline.py`, `app/services/hybrid_retrieval.py` | Feature specs and `app/test_*knowledge*`, `app/test_*ai*`, `app/test_batch*` |
| BI and Graph | `app/business_intelligence/`, `app/business_graph/` | `docs/implementations/features/business-intelligence.md`, `business-graph.md`, package tests; route modules not mounted |
| Configuration | `app/configuration/`, `app/configuration/urls.py` | [configuration progress traceability](../implementations/business-configuration-progress.md), `app/tests/test_configuration_*.py`; route module not mounted |
| Integration and observability | `app/integrations/`, `app/observability/` | [observability progress traceability](../implementations/integration-data-observability-progress.md), `app/tests/test_observability_*.py`; route module not mounted |
| Overview | `app/overview/` | [overview progress traceability](../implementations/overview-monitoring-progress.md), `app/tests/test_overview_*.py`; route module not mounted |
| Build/setup and deployment | `bizora/settings.py`, `bizora/urls.py`, migrations, `Dockerfile`, compose, setup docs | [README](../../README.md), [Docker setup](../setup/docker.md), verification artifacts under `docs/implementations/verification/` |

The original feature requirements remain in `docs/implementations/features/`. The domain audit JSON/Markdown is the authoritative subfeature status inventory for its 298 entries. Configuration progress documents 90 named requirements; observability progress documents 81; overview progress contains its own matrix. Those inventories should be reconciled into a single future acceptance backlog after the unmounted route trees and authorization grants are integrated.

## 10. Known limitations and decisions

1. Public route mounting is incomplete for BI, Graph, Configuration, Observability, and Overview APIs despite code and URL modules being present.
2. Configuration/observability access grants differ from core BusinessMembership roles. Mounting them without a role/grant integration decision creates uneven access semantics.
3. Legacy AI access uses `ADMIN` in one permission path while current membership roles use `MANAGER`; verify and reconcile before relying on manager-only access through those endpoints.
4. No live provider adapters are included for general source sync, outbound messaging, calls, or shipments. Product mock transport is simulation only.
5. Shipment raw provider diagnostics remain private. Public diagnostic fields require an approved allowlist and redaction policy.
6. Identity confidence is not generally a calibrated probability. Physical merge lifecycle and downstream preservation are blocked pending owner guarantees.
7. Deterministic BI/Graph code and tests do not imply active analytics APIs or a fully populated graph in a running deployment.
8. The existing reports record historical test totals. This documentation task did not rerun tests or verify a target deployment.

## 11. Source review inventory

The repository inventory contained 339 project files and approximately 97,000 lines across application source, tests, docs, migrations, templates, configuration, and supporting artifacts (excluding Git metadata, virtual environments, and the tracked SQLite database from the line count). Review coverage included:

- Django project settings, root URL mounting, API views, serializers, models, migrations, admin, and management commands.
- Domain services for canonical data, identity, operations, projections, product assessment, merge planning, contracts, and mock transport.
- AI, knowledge, retrieval, memory, action, and authorization services.
- Business Intelligence, Business Graph, Configuration, Observability, Overview, Integration, and Business Data packages and their route modules.
- Operational templates and template tags, tests and test helpers, setup files, and repository rule files.
- Existing feature briefs, implementation reports, requirement audits, progress/traceability documents, contracts, and verification reports.

Generated or third-party content is not part of product requirements. The repository’s prior reports are treated as evidence with their stated dates and limitations, not as proof that a current deployment has the same configuration.
