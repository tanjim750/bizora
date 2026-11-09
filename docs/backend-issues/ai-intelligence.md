# Backend issues: AI Intelligence

Domain status: **partial (routes live; data mostly empty or canned)**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| AI-01 | high | No route or job creates recommendations or actions | Part B GAP-3; frontend.md P5 | lists are empty | a generation job | empty state |
| AI-02 | high | The LLM fallback is invisible: with `BIZORA_LLM_URL` unset the routes return canned text, `tokens_used: 180` and a hard-coded `model_name` | Part B GAP-8 | cannot tell AI from canned text | return `provider_status` and the real model | make no "AI" claim |
| AI-03 | high | Two approval routes: A (`actions/{pk}/approve`, `reject`, `execute`; OWNER/ADMIN/OPERATOR; no evidence check) vs B (`actions/{pk}/review`; OWNER/MANAGER; evidence required; no `approved_by`; no execute) | Part B section 2C, GAP-5 | divergent behaviour | one canonical route | key the UI off `status` |
| AI-04 | high | Execution is always simulated; `EXECUTING` has no recovery route; `target_entity_id` is fabricated as 1 | Part B GAP-9, GAP-16; handoff F05 | no real execution | an executor contract and recovery | SimulatedBadge; no execute UI |
| AI-05 | high | State-changing AI POSTs (E3-E5, E8, E9) and LLM routes accept any role including VIEWER; a foreign action id returns 403; no idempotency | Part B GAP-7, section 5.9 | duplicates | role gates; idempotency key | disable the control while pending |
| AI-06 | medium | Recommendations, actions and issues are unpaginated bare arrays | Part B section 5.5; handoff F06 | client-side paging | pagination and filters | client paging |
| AI-07 | medium | No read route for AI history or audit; an unknown `conversation_id` is silently replaced; conversations do not record the user | Part B GAP-12, 18 | no history or audit view | list and detail routes | client-side transcript |
| AI-08 | medium | Recommendations omit `expires_at`, action ids and evidence weight; status never leaves SUGGESTED; memory promotion is unreachable | Part B GAP-4, 11 | thin lifecycle | add fields; sync status | show the action status |
| AI-09 | medium | Brand tone is never applied; hybrid retrieval is unused; product-aware AI is unwired | Part B GAP-13 to 15 | weaker answers | wire them in | - |
