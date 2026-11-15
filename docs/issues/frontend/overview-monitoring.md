# Overview and Monitoring: frontend issues

Backend counterpart: [`../backend/overview-monitoring.md`](../backend/overview-monitoring.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| BIA-02 | high | Also: Overview windows are in `business.timezone` (Asia/Dhaka: 2026-09-30T18:00Z to 10-31T18:00Z) matched by exact equality vs UTC months in BI; `period_end <= now` hides the current month; only `%`, `PERCENT`, `PERCENTAGE` are treated as percentage points while BI uses `RATIO`/`CURRENCY` units. | Keep Overview KPI cards in the UNAVAILABLE state with the backend's reason; do not map BI keys client-side. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
