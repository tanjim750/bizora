# Backend issues by domain

Written so that another engineer can pick up any domain from these files alone, without the frontend team. One file per domain; each row has an id, severity, evidence, the impact on the UI,
a suggested action for the backend owner and the workaround the frontend uses meanwhile. Last updated: 2026-11-09, `main` at 8010daa. The frontend overhaul agent appends rows as it finds problems.

## Summary

| Domain | Status | blocker | high | medium | low | fixed | File |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| Platform, auth, routing and runtime | partial (boots; session API exists; auth, error and runtime gaps) | 0 | 4 | 3 | 0 | 2 | [platform.md](platform.md) |
| Business Data (canonical domain API) | live | 0 | 2 | 5 | 1 | 0 | [business-data.md](business-data.md) |
| Business Operations | live, partial | 0 | 2 | 3 | 0 | 1 | [business-operations.md](business-operations.md) |
| Identity Resolution | live (MANAGER/OWNER only; merge blocked by design) | 0 | 0 | 3 | 0 | 0 | [identity.md](identity.md) |
| Business Intelligence | unmounted and blocked | 3 | 3 | 3 | 0 | 1 | [business-intelligence.md](business-intelligence.md) |
| Business Graph | unmounted and blocked | 3 | 3 | 1 | 0 | 0 | [business-graph.md](business-graph.md) |
| AI Intelligence | partial (routes live; data mostly empty or canned) | 0 | 5 | 4 | 0 | 0 | [ai-intelligence.md](ai-intelligence.md) |
| Overview and Monitoring | partial (mounted; data mostly UNAVAILABLE) | 0 | 1 | 2 | 0 | 1 | [overview-monitoring.md](overview-monitoring.md) |
| Integrations and Data Observability | partial (mounted; no live adapters or data producers) | 0 | 2 | 2 | 1 | 1 | [integrations-observability.md](integrations-observability.md) |
| Business Configuration | partial (mounted; the UI is read-only) | 0 | 2 | 3 | 1 | 1 | [business-configuration.md](business-configuration.md) |
| Business Memory and Knowledge | blocked (service-only) | 1 | 1 | 0 | 0 | 1 | [memory-knowledge.md](memory-knowledge.md) |
| Prototype Simulation | blocked (CLI only) | 1 | 0 | 1 | 0 | 0 | [prototype-simulation.md](prototype-simulation.md) |
| Testing, release and database | partial | 0 | 3 | 2 | 0 | 1 | [testing-release.md](testing-release.md) |
| **Total** | | **8** | **28** | **32** | **3** | **9** | |

Counts are generated from the files; "fixed" rows are already resolved on main.

## Cross-cutting decisions the backend owner must make
1. One authorization table and role enum (replace the free `MEMBER` default; fold `BusinessAccess` into membership; settle OWNER/ADMIN vs MANAGER); the role per business is already in the session payload.
2. One error shape `{code, detail, fields}`; 401 for unauthenticated requests; JSON for 500 errors.
3. One pagination style on every list endpoint.
4. An OpenAPI schema with per-resource writable-field metadata.
5. Agent and team list endpoints, and a formal "my businesses" endpoint beyond `/api/frontend/session`.
6. Business Intelligence and Graph tenant seam under `businesses/<id>/...` with the domain `authorize()`; fix the Graph Python 3.12 import and the relationship rule keys.
7. Who runs the BI calculators and syncs (job runner, scheduler); move off `runserver`.
8. One AI approval route, one handover vocabulary, and honest LLM provider status.
9. Provision `BIZORA_DOMAIN_ADAPTERS` and the AI provider settings, or declare the contracts out of scope.
10. Scope the Memory and Simulation HTTP APIs, or declare them CLI/service-only.
11. Gates: Python 3.12 plus PostgreSQL 16 CI, HTTPS settings, hermetic tests.

## Row template
`| XX-NN | blocker, high, medium or low | One sentence | Request and short response excerpt, or file:line, or screenshot name (UNVERIFIED if inferred) | Effect on the UI | Suggested action for the backend owner | Workaround in the UI |`
Use the next free id of the domain. Never paste secrets or personal data.
