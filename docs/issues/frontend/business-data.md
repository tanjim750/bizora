# Business Data (canonical domain API): frontend issues

Backend counterpart: [`../backend/business-data.md`](../backend/business-data.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| DOM-08 | medium | Money serialised as float (1234567890123456.78 returned as ...8); BI returns strings; `money()` allows < 1e16. | Treat money as strings/decimals; do not parse backend floats for totals; BI returns strings. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
