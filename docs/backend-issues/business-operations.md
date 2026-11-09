# Backend issues: Business Operations

Domain status: **live, partial**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| BO-01 | high | Two handover paths write one column with different values: AI `support/handover`, `resume`, `escalate` (HANDOVER_TO_HUMAN, ACTIVE_AI, ESCALATION_RECOMMENDED; escalate also sets priority URGENT, no event) vs the domain route (AI/HUMAN) | Part B GAP-10, E3-E5 | inconsistent badges | make the AI routes call the domain service | use the domain `conversations/{pk}/handover/`; treat AI flags as advisory |
| BO-02 | medium | HUMAN handover needs an agent `assignee_id` although the serializer says optional | Part A G16 | form error | align the contract | require an agent |
| BO-03 | high | Outbound is prepare-only (`NOT_EXECUTED`); reply and media reply only save PENDING messages | Part A D21, section 5.8 | nothing is sent | an execution contract with confirmed states | label "recorded" or "saved", never "sent" |
| BO-04 | medium | Always UNAVAILABLE: `business_health`, website-performance (7 keys), queue `capabilities`, `policy_context`, `suggested_reply`, retargeting audience, `recording_access`, graph `generation` | Part A D7, D10, D18, D20 | empty panels | owners ship adapters (see IO-03) | UnavailableState naming the owner |
| BO-05 | medium | Detail, 360 and context sections cap at 50 rows; no list endpoints for order items, customer timeline or conversation events; `assigned=team` needs a SupportTeam but there is no team CRUD | Part A section 5.3, 5.19, G5 | truncated history | add list routes | child lists; show the `truncated` flag |
| BO-06 | FIXED | Campaign `provider` filter was rejected; `platform` is now allowed | diff 5f176a2..8010daa, `domain_views.py` | - | - | use `platform` |
