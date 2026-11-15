# Business Configuration

Domain issue list for the domain owner. Written 2026-11-13 from the read-only audit (details and evidence in `../cross-cutting/audit-*.md`, cross-cutting priorities in `../cross-cutting/AUDIT.md`). **Nothing here has been fixed.** Fix only what the project docs specify; items tagged SPEC-GAP need the lead developer's decision first; no schema change, new endpoint, role or response field without approval. Every fix ships with a regression test; never push.

Tags: **SPEC-DEFECT** contradicts the docs; **SPEC-GAP** docs silent, decision needed; **INTEGRATION** frontend/backend mismatch. `INFERRED` = read from code, not run.

Code areas: `app/configuration/**`

| ID | Sev | Tag | Problem | How to fix | Test |
|---|---|---|---|---|---|
| DOM-10 | medium | SPEC-DEFECT | A configuration PROFILE/GENERAL write changes `Business.currency` / `timezone` with no guard (`app/configuration/services.py:463`): later orders and BI single-currency scopes use the new currency while history keeps the old one. | Reject a currency change when orders exist or require an explicit migration flag; 409 `{code:CURRENCY_LOCKED}`. | Currency change with existing orders -> 409 |
| AIS-08 (config part) | medium | SPEC-DEFECT | Configured AI/Knowledge settings are decorative: no AI service reads `ai_configuration`, `action_policy`, `approved_sources` (see ai-intelligence.md). | Enforce in the AI views. | `ai.enabled=false` blocks AI |
| DOM-17 (config part) | low | SPEC-GAP | 3-letter currency check applies only to ingest, not to `Business.currency` set here. | Validate on write. | Invalid currency -> 400 |

## Prior list (`docs/backend-issues/business-configuration.md`)
BC-01 fixed. BC-02, BC-03 (mechanism = DOM-17 connections 500), BC-04 (merge semantics), BC-05, BC-06, BC-07 (SECRET_TEXT rewrites 'Basic <word>') open; BC-05/06 not re-probed. Healthy: `ConfigurationConflict` version check works; credentials stored only as env references and never returned.
