# Business Operations

Domain issue list for the domain owner. Written 2026-11-13 from the read-only audit (details and evidence in `../cross-cutting/audit-*.md`, cross-cutting priorities in `../cross-cutting/AUDIT.md`). **Nothing here has been fixed.** Fix only what the project docs specify; items tagged SPEC-GAP need the lead developer's decision first; no schema change, new endpoint, role or response field without approval. Every fix ships with a regression test; never push.

Tags: **SPEC-DEFECT** contradicts the docs; **SPEC-GAP** docs silent, decision needed; **INTEGRATION** frontend/backend mismatch. `INFERRED` = read from code, not run.

Code areas: `app/domains/operations.py`, `app/domain_views.py` (assign/handover/priority/callbacks/outbound), `app/views.py` support routes

| ID | Sev | Tag | Problem | How to fix | Test |
|---|---|---|---|---|---|
| AIS-10 | medium | SPEC-DEFECT | Escalation logic (`ai_support`): substring trigger 'court' matches 'courteous' and sets URGENT; `priority==URGENT` then escalates every later call ('Urgent priority flagged') and overwrites the original priority with no history; `customer_message` comes from the caller instead of the conversation; AI states ESCALATION_RECOMMENDED / HANDOVER_TO_HUMAN / ACTIVE_AI conflict with the domain's AI/HUMAN vocabulary and break the domain `handover()` repeat check. | Word-boundary regex; return advice without mutating priority; map states to the domain vocabulary; read the message from the conversation. | 'courteous' -> `should_escalate: false` |
| AIS-01 (ops part) | high | SPEC-DEFECT | AI support routes (escalate/handover/resume) change conversation state without `ConversationEvent` / `DomainAudit` rows, unlike `domains/operations.py handover` and `set_priority`; VIEWER can call them (see ai-intelligence.md). | Route writes through the domain operations so events and audits are written. | Handover via AI route writes event + audit |

## Prior list (`docs/backend-issues/business-operations.md`)
BO-06 fixed. BO-01 (code-read only), BO-02 (handover HUMAN without `assignee_id` fails membership check with 400 `INVALID_ASSIGNEE`), BO-03 (prepare-only), BO-04, BO-05 still open. Healthy: role gate (viewer cannot write, operator cannot use identity) behaves as documented.
