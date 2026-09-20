# AI Intelligence module audit

Audit date: 2026-09-20

Scope: `docs/implementations/features/ai-intelligence.md`, `app/services/ai*.py`, `app/services/actions.py`, `app/models.py`, `app/views.py`, serializers, URLs, migrations, and the AI test suites. The module has code and tests for all 18 named feature groups, but the implementation is a prototype with major correctness, security, and completeness gaps. A feature being represented by a service function or happy-path test is not treated as complete.

## Coverage assessment

| Feature | Current implementation | Status |
|---|---|---|
| 1. Business Assistant | Authenticated endpoint, conversation/message persistence, keyword intent classification, context assembly, fallback response | Partial: no real model integration; unsafe tenant/session handling; unsupported claims possible |
| 2. Customer Support AI | Suggested reply, policy lookup, escalation keywords, handover and resume services/endpoints | Partial: policy search is incomplete; order/customer mismatch accepted; no model-backed or complete message context |
| 3. Marketing Assistant | Campaign metrics, UTM/conversion attribution, ROAS and heuristic suggestions | Partial: no AI generation, no goals, wrong fallback attribution, SQLite incompatibility |
| 4. Business Diagnosis | Issue, evidence, graph and historical lookup plus generated summary | Partial: hard-coded causal/impact language and factors are not evidence-bound |
| 5. Fact-Aware Retrieval | Verified/expiry-aware manager and evidence serialization | Partial: invalidated and future facts leak through several paths; entity filter uses PostgreSQL-only JSON lookup and does not use fact subject columns |
| 6. Graph-Aware Retrieval | Bounded graph query and cycle-safe traversal | Partial: expired edges, cross-tenant node inconsistencies, arbitrary fallback graph, DFS depth behavior, and direction semantics are wrong |
| 7. Memory Retrieval | READY/PUBLISHED documents and approved recommendation/action history | Partial: no keyword/vector/hybrid chunk retrieval, no source references, PUBLISHED policy intent lookup is excluded |
| 8. Customer-Aware AI | Profile, contacts, orders, aggregate spend, support summaries | Partial: accepts a customer from another tenant; omits payments, calls, delivery history, tags, and verified customer metrics |
| 9. Product-Aware AI | Product/variants, sales and return aggregates, title-based guides | Partial: accepts another tenant’s product; no campaign/customer/support evidence and title matching is not reliable knowledge retrieval |
| 10. Order-Aware AI | Items, payments, shipments, subject-matched conversations, UTM fields | Partial: accepts another tenant’s order; calls, refunds, order journey graph and verified attribution are missing |
| 11. Conversation Summarization | Heuristic intent/status, truncated message prompt, metadata persistence | Partial: no AI audit/model metadata; only first 800 chars; internal notes/customer-visible separation is absent |
| 12. Call Summarization | Transcript read/create/update and heuristic purpose/outcome | Partial: ignores real call/order/conversation context; reports completed outbound calls as confirmed even when transcript says cancel; concerns are duration-only |
| 13. Recommendation Generation | Creates recommendation and suggested action from an issue/context | Partial: deterministic hard-coded recommendation, fake default targets/payloads, no goals/policies/history in prompt, no model-generated structured output |
| 14. Recommendation Evidence | Evidence model with FK validation and auto-grounding fallback | Incomplete/unsafe: missing evidence silently creates a new VERIFIED `GROUNDING` fact, violating the authoritative-data boundary; references are not comprehensive |
| 15. Suggested Actions | Structured `AiAction` rows with target/payload and SUGGESTED state | Partial: no action proposal endpoint/listing, no validation of target/payload, simulation flag is not enforced during execution |
| 16. Approval & Execution | Approval service, approval endpoint, simulated executor, failure status | Incomplete: no execution endpoint/routing, duplicate approvals can 500, stale instances can execute twice, and `{"status":"failed"}` is treated as success |
| 17. AI Audit | AiConversation/AiMessage and service audit events | Partial: only assistant output is stored by generic audit helper; prompt is discarded; model/token values are fabricated defaults; actions/execution/approval history and evidence claims are not fully linked |
| 18. AI Guardrails | Some approval checks, tenant filters in views, XML delimiters, timeout-shaped fallback | Incomplete/unsafe: tenant authority is optional, prompt delimiters are unescaped, model gateway never calls a model, cross-tenant service calls are accepted, and unsupported fallback claims are emitted |

## Confirmed bugs and issues

### Critical

- **AI-001 — Tenant isolation can be bypassed for normal authenticated users.** `app/views.py` only rejects a request when `request.user.business_id` happens to exist. Django’s built-in `User` has no such field or persisted membership. A normal session-authenticated user can call any business endpoint and approve any business action. Reproduced with two businesses and a real session login: assistant data and approval both returned HTTP 200. Fix with a real membership/role relation and mandatory object-level permission checks.

- **AI-002 — Service-layer tenant isolation is absent.** `assemble_customer_context`, `assemble_product_context`, and `assemble_order_context` accept an entity from another business without checking `entity.business_id`. `generate_grounded_recommendation` accepts an issue belonging to another business. Any caller bypassing the views can mix tenants. Add invariant checks at service boundaries and ensure all evidence FKs belong to the recommendation business.

- **AI-003 — Missing recommendation evidence manufactures authoritative truth.** `AiRecommendationEvidence.save()` creates a `BusinessFact` with `status="VERIFIED"` and a fabricated statement when no evidence exists. This directly violates the documented AI boundary. Missing evidence must fail closed and leave the recommendation ungrounded/rejected.

- **AI-004 — LLM integration is not implemented.** `Business.execute_llm_with_timeout()` always returns `fallback_response`; it never invokes a provider, applies a real timeout, validates a response, or records provider errors. The module is heuristic/fallback simulation, not an AI intelligence implementation.

- **AI-005 — Fallback assistant makes unsupported business claims.** With no facts or orders, `ask_business_assistant()` says “revenue and order volumes are steady.” Fallback outputs must state that evidence is unavailable, not invent stability.

- **AI-006 — Approval and execution lifecycle is incomplete and unsafe.** There is an approval endpoint but no execution endpoint or integration routing. `execute_action()` permits a simulated action to invoke an arbitrary executor and permits a non-simulated action with no executor to report success. A stale approved object can execute again after another request has already executed it. Use a locked state transition/idempotency key and enforce simulation/provider routing.

### High

- **AI-007 — Invalidated/future facts leak into AI context.** `assemble_ai_context()` filters only by business, not `status` or `valid_from`; the context can include invalidated and not-yet-valid facts. `assemble_fact_context()` filters `status="VERIFIED"` but still includes future facts when `as_of` is absent. Use one active-for-context query everywhere, including `valid_from <= now` and invalidation status.

- **AI-008 — Entity fact filtering is wrong and database-specific.** `metadata__contains={entity_type: entity_id}` does not use `subject_entity_type/subject_entity_id`, can miss correctly modeled facts, and raises `NotSupportedError` under SQLite. Use normal columns and a JSON metadata fallback only where supported.

- **AI-009 — Graph retrieval ignores edge validity and has incorrect traversal semantics.** Expired edges are included. Reverse relationships are queried but only directed successors are traversed, so an order-origin journey omits its incoming customer. The fallback loads unrelated edges when the start node is absent. Apply validity/tenant checks and define whether traversal is directed or undirected per task.

- **AI-010 — Graph depth is path-order dependent.** `safe_traverse()` uses DFS with one global visited set. A node reached through a longer branch can be marked visited before a shorter path is explored, causing reachable nodes within the requested hop depth to be omitted. Use breadth-first traversal with explicit depth tracking.

- **AI-011 — Memory retrieval does not implement the documented retrieval model.** It reads whole documents only; no `KnowledgeChunk`/embedding/vector search, keyword search, metadata ranking, source traceability, brand tone, goals, or historical decision records exist. `get_active_policies_for_intent()` only accepts `status="READY"`, so published policies are silently unavailable.

- **AI-012 — Customer/order/product context accepts mismatched entities.** The support endpoint scopes `order_id` to the business but never checks that the order belongs to the conversation’s customer. A customer-A conversation can receive customer-B’s order. The same missing relation check exists in service context functions.

- **AI-013 — Recommendation generation uses fabricated operational defaults.** Courier IDs `1`/`2`, 50% allocation, campaign adjustment payloads, reorder quantity, and generic rationale are hard-coded rather than selected from retrieved graph/facts/operations. This can propose actions against nonexistent or unrelated entities.

- **AI-014 — Diagnosis invents causal context.** Every diagnosis says the issue impacts fulfillment/revenue and emits “regional failures” and courier bottlenecks, including an inventory issue with no evidence. Contributing factors and impact must be derived from attached evidence or explicitly marked unknown.

- **AI-015 — Call summarization misclassifies outcomes.** A completed outbound call whose transcript says “cancel”/“refund” is reported as `CONFIRMED` because direction/status is checked before transcript meaning. It also emits “No customer complaints” for a complaint transcript. Parse transcript intent/outcome first and preserve evidence.

- **AI-016 — Conversation summary and handover context are lossy.** Summaries pass only the first 800 characters of the whole thread, omit structured message details, internal notes, order references and actions, and do not store an AI summary audit record. Human notes saved by `resume_ai_handling()` are not included by suggested-reply context, so continuation does not retain the promised context.

- **AI-017 — Prompt-injection boundary is not a boundary.** User/retrieved text is inserted between literal XML-like tags without escaping or structured message separation. A query containing `</untrusted_user_input>` can close the delimiter and add apparent trusted instructions. Use provider message roles, structured JSON, and escaping; treat retrieved documents as untrusted data too.

- **AI-018 — Audit records are incomplete and misleading.** `record_ai_audit_event()` discards the prompt, always creates a single assistant message, defaults to `gemini-1.5-pro`, and splits a default token count instead of recording provider usage. Approval/execution events are not persisted as AI audit records; recommendation evidence is not attached to assistant claims.

- **AI-019 — Error handling returns HTTP 500 for a normal state conflict.** Re-approving an already approved action raises `ValidationError` from the service and is not translated by the view to a 4xx response. Return a deterministic 409/400 response and make approval idempotent where appropriate.

- **AI-020 — Execution result parsing misses provider failure shapes.** `execute_action()` only checks `error`/`errors`; a provider response such as `{"status": "failed"}` is marked `EXECUTED`. Require an explicit success signal and persist the raw provider result.

- **AI-021 — Recommendation creation is not atomic.** Recommendation and evidence are saved before action creation. If action persistence fails, orphaned recommendation/evidence rows remain. Wrap the complete generation lifecycle in `transaction.atomic()`.

### Medium

- **AI-022 — Marketing analysis falls back to every business order.** When a business has one campaign and no conversion/UTM links, all orders are attributed to that campaign. This is not evidence-backed attribution; return “unattributed” instead.

- **AI-023 — Marketing “goal alignment” is not implemented.** Suggestions use fixed ROAS thresholds and never retrieve active business goals, target metrics, approved suggestions, or policies.

- **AI-024 — Order context is not a complete journey.** It omits refunds, calls, status history, conversation relation (it searches subject text), graph journey and verified campaign/session relationships. Subject substring matching can associate unrelated conversations.

- **AI-025 — Customer context is incomplete.** It omits calls, payments/refunds, shipment history, tags, timeline events and verified value facts despite the feature contract.

- **AI-026 — Product knowledge retrieval is title substring matching.** Product guides are selected by `title__icontains=product.name`; variants, knowledge chunks, approved documents, support issues and campaign relationships are not retrieved.

- **AI-027 — No public endpoints expose recommendations/actions/evidence or execution.** The URL surface exposes assistant/support/marketing/diagnosis/summaries and action approval only. Users cannot inspect recommendation evidence, list proposed actions, reject actions, execute approved actions, or view lifecycle history through the API.

- **AI-028 — No explicit rejection workflow.** The model/service allows approval from `REJECTED` but has no rejection endpoint, rejection note operation, or rejected-by audit field.

- **AI-029 — Conversation type/status is not validated.** `ask_business_assistant()` can append to a completed support audit conversation because lookup filters only by ID/business. Enforce `conversation_type="BUSINESS_ASSISTANT"`, active status, and customer ownership.

- **AI-030 — Audit helper does not record user messages for non-assistant services.** Support, marketing and diagnosis audit calls create only an assistant message, so the actual input/prompt and user/task actor are absent.

- **AI-031 — Feature tests overstate coverage.** `app/test_ai_intelligence_features.py` mainly asserts response keys and fallback behavior; it does not assert real provider calls, evidence sufficiency, API authorization for users without a dynamic `business_id`, action idempotency, published policy retrieval, graph validity, or unsupported claims. Existing regression tests document several old defects but are not a substitute for production behavior.

## Validation evidence

- Static inspection covered all AI services, models, views, serializers, URLs, migrations, documentation, and tests.
- A temporary Python 3.12 environment with the pinned requirements was created outside the repository because the checked-in `.venv` has Python 3.13 and no Django installation.
- Twenty isolated probes ran against an in-memory SQLite test database and all reproduced probes passed. The probes intentionally demonstrate the defects listed above (tenant bypass, fabricated facts, policy omission, false call outcomes, duplicate execution, cross-tenant context, diagnosis invention, lossy context, graph validity/direction, SQLite failures, fake model audit, mismatched order, failure parsing, non-atomic writes, session confusion, DFS depth, and delimiter breakout).
- Docker/PostgreSQL was unavailable in the environment, so PostgreSQL-only behavior and migration execution were not live-verified. The SQLite failures are themselves a portability issue because the project’s local fallback is SQLite while AI context uses PostgreSQL-only JSON lookups.

## Recommended fix order

1. Establish persisted business membership/roles and enforce tenant checks in every view and AI service.
2. Remove fabricated facts and unsupported fallbacks; make evidence and uncertainty fail closed.
3. Implement a real provider adapter with timeout, structured output validation, prompt/data isolation, and honest usage/model audit fields.
4. Repair fact/graph/memory retrieval validity, published policy handling, vector/chunk search, and cross-domain entity relations.
5. Complete the action state machine with atomic/idempotent transitions, rejection/execution APIs, provider result handling, and audit events.
6. Replace hard-coded diagnosis/recommendation/call logic with evidence-derived outputs and expand regression tests around the confirmed probes.
