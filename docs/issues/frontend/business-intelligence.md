# Business Intelligence: frontend issues

Backend counterpart: [`../backend/business-intelligence.md`](../backend/business-intelligence.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Always apply
- Always show 'Not computed' when `metrics/` is empty: `pipeline/run/` does not compute metric snapshots (BIA-03); they come from `manage.py run_intelligence`.
- Manager-only buttons (pipeline run, fact/issue create/patch): hide for VIEWER/OPERATOR (403 otherwise).

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| BIA-01 | high | Snapshots unreadable from Next.js: `metrics/<key>/snapshots/` keys contain dots (`bi.metric.sales_total_orders.v1`); the proxy (`frontend/src/app/api/backend/[...path]/route.js:9`) only passes `[a-zA-Z0-9_-]+`. | Until the owner picks a fix, show metric snapshots as 'Not available'. Do not build URLs with dotted metric keys. If the owner chooses to relax the proxy, allow `.` in segments of `metrics/*/snapshots/` only. |
| BIA-02 | high | Overview KPIs can never be fed by BI (see overview-monitoring.md DOM-01): key vocabulary, business-timezone windows vs UTC months, RATIO/CURRENCY units. | Keep Overview KPI cards in the UNAVAILABLE state with the backend's reason; do not map BI keys client-side. |
| BIA-08 | medium | (BI-06, intent to be confirmed) Default fact list = VERIFIED and valid now (history hidden); rows omit `valid_from/valid_to/subject_*`; `?status=bogus` 200 empty; reactivation keeps past `valid_to`. | Request `?status=VERIFIED` when history is needed; the default list shows only currently valid facts. |
| BIA-14 | low | Pagination `{total_count,limit,offset,results}` differs from Overview/Obs `count/next/previous`. | Handle `{total_count, limit, offset, results}` for BI and `count/next/previous` for Overview/Obs in the list adapter. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
