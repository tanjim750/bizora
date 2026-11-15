# Prototype Simulation: frontend issues

Backend counterpart: [`../backend/prototype-simulation.md`](../backend/prototype-simulation.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| PS-01 | medium | Simulation is CLI only (`simulate_configuration`, `simulate_observability`, `simulate_overview`); no HTTP surface. Not run by this audit. | No UI for simulations; keep it CLI-only. |
| OVERVIEW-DEMO | low | `app/overview/demo.py` seeds short-key `BusinessMetric` rows (`total_revenue`...), which hides the BI-key mismatch (DOM-01) and makes Overview look healthy only in the demo. | Do not treat demo-populated KPIs as proof that BI feeds Overview. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
