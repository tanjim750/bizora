# Integrations and Data Observability: frontend issues

Backend counterpart: [`../backend/integrations-observability.md`](../backend/integrations-observability.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| PLA-02 (webhook note) | low | Proxy forwards no client IP (`route.js:34`), so IP-based observability/rate checks see the Next server for every request. | Same as PLA-02. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
