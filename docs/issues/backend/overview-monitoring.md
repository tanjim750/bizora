# Overview and Monitoring

Domain issue list for the domain owner. Written 2026-11-13 from the read-only audit (details and evidence in `../cross-cutting/audit-*.md`, cross-cutting priorities in `../cross-cutting/AUDIT.md`). **Nothing here has been fixed.** Fix only what the project docs specify; items tagged SPEC-GAP need the lead developer's decision first; no schema change, new endpoint, role or response field without approval. Every fix ships with a regression test; never push.

Tags: **SPEC-DEFECT** contradicts the docs; **SPEC-GAP** docs silent, decision needed; **INTEGRATION** frontend/backend mismatch. `INFERRED` = read from code, not run.

Code areas: `app/overview/**`

| ID | Sev | Tag | Problem | How to fix | Test |
|---|---|---|---|---|---|
| DOM-01 | blocker | SPEC-DEFECT | Overview KPIs are permanently UNAVAILABLE: `app/overview/catalog.py:16-29` keys (`total_revenue`, `order_count`, ...) never match BI registry keys `bi.metric.<name>.v1` (0 of 42 overlap); `overview/metrics.py:116` filters `metric__key__in=self.keys()` from `DEFAULT_KPIS`; only the demo seeder (`overview/demo.py:79`) creates short-key rows; window periods `ROLLING_7D/30D` are not BI period types (HOUR/DAY/WEEK/MONTH/CUSTOM). Probe: `GET /overview/kpis/?period=MONTH` -> 0 of 9 cards AVAILABLE (`NO_EXACT_BI_SNAPSHOT`). | Lead decides (docs silent on the mapping); recommended: adapter `KPI_TO_BI = {'total_revenue': 'bi.metric.revenue_gross.v1', 'order_count': 'bi.metric.sales_total_orders.v1', ...}` in `catalog.py`, resolved in `MetricProjection.keys()`/`query()` and the known-key sets; let `KpiRuleSerializer.key` accept `.`; map ROLLING_* to CUSTOM; return the BI key in the card. | After `run_intelligence` for the last closed month an Overview KPI is AVAILABLE |
| BIA-02 | high | INTEGRATION | Also: Overview windows are in `business.timezone` (Asia/Dhaka: 2026-09-30T18:00Z to 10-31T18:00Z) matched by exact equality vs UTC months in BI; `period_end <= now` hides the current month; only `%`, `PERCENT`, `PERCENTAGE` are treated as percentage points while BI uses `RATIO`/`CURRENCY` units. | Compute BI periods in the business timezone (stored aware UTC); map RATIO to percent display. | Matching window found without manual alignment |
| DOM-06 | high | SPEC-DEFECT | Overview, customer360 and detail do O(tenant) work per request: `contracts.safe_records()` (`contracts.py:20`) iterates every row with `.iterator()` and runs `ensure_owned` (a query per FK) for facts, issues, relationships, nodes, both evidence tables; `recommendation_supported()` (`contracts.py:32`) calls it once per recommendation (quadratic); builds `pk__in=[...]` beyond the SQLite variable limit; each `section()` runs a count plus a slice. | Enforce tenancy in SQL (`filter(business=...)`); validate cross-tenant references at write time, not on every read; cache current-facts ids per request; cap work; fail closed with a count-only query. | `assertNumQueries` bound with 500 nodes |

## Prior list (`docs/backend-issues/overview-monitoring.md`)
OM-01 fixed. OM-02 (root overview URL falls through to the domain view), OM-03 (root cause = DOM-01, not only BI-03), OM-04 still open.
