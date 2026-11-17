# Integrations and Data Observability

Domain issue list for the domain owner. Written 2026-11-13 from the read-only audit (details and evidence in `../cross-cutting/audit-*.md`, cross-cutting priorities in `../cross-cutting/AUDIT.md`). **Nothing here has been fixed.** Fix only what the project docs specify; items tagged SPEC-GAP need the lead developer's decision first; no schema change, new endpoint, role or response field without approval. Every fix ships with a regression test; never push.

Tags: **SPEC-DEFECT** contradicts the docs; **SPEC-GAP** docs silent, decision needed; **INTEGRATION** frontend/backend mismatch. `INFERRED` = read from code, not run.

Code areas: `app/observability/**`, `app/integrations/**`, `app/events/**`

| ID | Sev | Tag | Problem | How to fix | Test |
|---|---|---|---|---|---|
| DOM-07 (obs part) | medium | SPEC-GAP | `require_processing_scope` is enforced only on the observability path; domain ingest accepts any CONNECTED connection from an OPERATOR (see business-data.md). | Enforce on every path that attributes data to a connection. | - |
| DOM-02 (obs part) | high | SPEC-DEFECT | `observability/access.py require_access` (superuser bypass, `BusinessAccess` grants, 403) is one of three divergent role implementations (see platform.md). | Fold into the single authorization helper once the role matrix is decided. | Role matrix test |
| PLA-02 (webhook note) | low | INTEGRATION | Proxy forwards no client IP (`route.js:34`), so IP-based observability/rate checks see the Next server for every request. | Forward `x-forwarded-for`; Django trusted-proxy setting. | - |

## Prior list (`docs/backend-issues/integrations-observability.md`)
IO-01 fixed. Open: IO-02, IO-03, IO-04 (freshness filtered after pagination, `views.py:170-180`), IO-05 (retry cap counts successes; first backoff 60 s), IO-06. Not re-probed in depth by this audit.
