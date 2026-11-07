# Overview & Monitoring delivery traceability

Source: [Overview & Monitoring specification](features/overview-monitoring.md).

Branch: `codex/overview-monitoring`, based on integration commit `0a6d904`.
Scope: authenticated Django backend projections and monitoring configuration. No frontend exists in this repository.

All 75 named subfeatures have an implementation path below. Implemented means the monitoring projection is present; upstream BI, graph, AI and operational owners still supply their authoritative records. Missing data remains explicit.

## Requirement matrix

| # | Group / feature | API | Implementation under app/overview | Regression coverage under app/tests | Behavior / boundary |
| --- | --- | --- | --- | --- | --- |
| 1 | Business Overview: **Executive Business Summary** | `summary/` | views.py, health.py, metrics.py | test_overview_api.py, test_overview_metrics.py, test_overview_demo.py | Deterministic summary and evaluation timestamp; no generated narrative. |
| 2 | Business Overview: **Cross-Domain KPI Summary** | `summary/` | views.py, health.py, metrics.py | test_overview_api.py, test_overview_metrics.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 3 | Business Overview: **Current Business Status** | `summary/` | views.py, health.py, metrics.py | test_overview_api.py, test_overview_metrics.py, test_overview_demo.py | Explainable health and configured period movement; unknown when evidence is insufficient. |
| 4 | Business Overview: **Issue Summary** | `summary/` | views.py, health.py, metrics.py | test_overview_api.py, test_overview_metrics.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 5 | Business Overview: **Recommendation Summary** | `summary/` | views.py, health.py, metrics.py | test_overview_api.py, test_overview_metrics.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 6 | Business Overview: **Recent Performance Context** | `summary/` | views.py, health.py, metrics.py | test_overview_api.py, test_overview_metrics.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 7 | Business Overview: **Operational Drill-Down** | `summary/` | views.py, health.py, metrics.py | test_overview_api.py, test_overview_metrics.py, test_overview_demo.py | Working typed entity and source-evidence routes; scoped graph context. |
| 8 | KPI Overview: **Revenue KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 9 | KPI Overview: **Order KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 10 | KPI Overview: **Customer KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 11 | KPI Overview: **Marketing KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 12 | KPI Overview: **Website KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 13 | KPI Overview: **Support KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 14 | KPI Overview: **Delivery KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 15 | KPI Overview: **Configurable KPI Selection** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Validated business policy, actor-attributed revisions, optimistic version conflicts. |
| 16 | KPI Overview: **Dimension-Aware KPIs** | `kpis/, catalog/, configuration/` | metrics.py, catalog.py, configuration.py | test_overview_metrics.py, test_overview_api.py, test_overview_edges.py | Exact dimension pair; dimensional snapshots never inflate totals. |
| 17 | Performance Trends: **Time-Series Performance** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 18 | Performance Trends: **Period Comparison** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Calendar previous periods or explicit equal-duration windows; decimal and zero-baseline handling. |
| 19 | Performance Trends: **Growth & Decline Indicators** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Numeric direction distinct from higher/lower-is-better assessment. |
| 20 | Performance Trends: **Revenue Trends** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 21 | Performance Trends: **Order Trends** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 22 | Performance Trends: **Marketing Trends** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 23 | Performance Trends: **Website Trends** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 24 | Performance Trends: **Support Trends** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 25 | Performance Trends: **Delivery Trends** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 26 | Performance Trends: **Dimension Comparison** | `trends/` | metrics.py, windows.py | test_overview_metrics.py, test_overview_windows.py, test_overview_edges.py | Request matching series for each dimension value; no blended totals. |
| 27 | Active Issues: **Open Issue List** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 28 | Active Issues: **Severity-Based Prioritization** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 29 | Active Issues: **Confidence Display** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 30 | Active Issues: **Affected Entity Context** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 31 | Active Issues: **Issue Evidence Summary** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 32 | Active Issues: **Issue Trend Context** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Stored BI trend metadata only; UNKNOWN when absent or malformed. |
| 33 | Active Issues: **Issue Drill-Down** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 34 | Active Issues: **Issue Lifecycle Visibility** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Current status, detected/updated/resolved times; explicit historical status filters. |
| 35 | Active Issues: **Recommendation Association** | `issues/, issues/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 36 | Business Health: **Business Health Summary** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 37 | Business Health: **Domain-Level Health** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 38 | Business Health: **Health Indicator Rules** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 39 | Business Health: **Healthy State Detection** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 40 | Business Health: **Warning State Detection** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 41 | Business Health: **Critical State Detection** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 42 | Business Health: **Health Evidence** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 43 | Business Health: **Health Trend** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Existing BI issue trend and comparable KPI movement; explicit MIXED/UNKNOWN. |
| 44 | Business Health: **Goal-Aware Health Context** | `health/` | health.py, configuration.py | test_overview_api.py, test_overview_edges.py, test_overview_demo.py | Configured target ranges, direction and goal label with evidence. |
| 45 | Recent Activity: **Order Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 46 | Recent Activity: **Payment Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 47 | Recent Activity: **Customer Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 48 | Recent Activity: **Support Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 49 | Recent Activity: **Delivery Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 50 | Recent Activity: **Marketing Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 51 | Recent Activity: **Website Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 52 | Recent Activity: **Calling Activity** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 53 | Recent Activity: **Issue Activity** | `activity/` | activity.py | test_overview_activity.py | Recorded detection plus labelled latest state observation; no invented transition log. |
| 54 | Recent Activity: **AI Activity** | `activity/` | activity.py | test_overview_activity.py | Recorded generation, approval, execution and labelled latest state observations. |
| 55 | Recent Activity: **Activity Filtering** | `activity/` | activity.py | test_overview_activity.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 56 | Recommendations: **Recommendation Feed** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 57 | Recommendations: **Priority Ranking** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 58 | Recommendations: **Issue-Linked Recommendations** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 59 | Recommendations: **Evidence Summary** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 60 | Recommendations: **Recommendation Confidence** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 61 | Recommendations: **Suggested Action Preview** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 62 | Recommendations: **Approval Status** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Stored action and recommendation status; no monitoring approval/execution endpoint. |
| 63 | Recommendations: **Historical Recommendations** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reviewed/completed status filters and effective expiry visibility. |
| 64 | Recommendations: **Goal Alignment** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Explicit stored upstream goal labels; no invented goal association. |
| 65 | Recommendations: **Recommendation Drill-Down** | `recommendations/, recommendations/<id>/` | findings.py, evidence.py | test_overview_api.py, test_overview_edges.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 66 | Cross-Domain Monitoring: **Marketing-to-Revenue Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 67 | Cross-Domain Monitoring: **Marketing-to-Delivery Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 68 | Cross-Domain Monitoring: **Website-to-Sales Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 69 | Cross-Domain Monitoring: **Product-to-Support Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 70 | Cross-Domain Monitoring: **Product-to-Delivery Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 71 | Cross-Domain Monitoring: **Customer-to-Retention Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 72 | Cross-Domain Monitoring: **Support-to-Customer Outcome Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 73 | Cross-Domain Monitoring: **Courier-to-Revenue Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 74 | Cross-Domain Monitoring: **Campaign-to-Customer Quality Monitoring** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Reads existing authoritative outputs with business scope and explicit unavailable states. |
| 75 | Cross-Domain Monitoring: **Cross-Domain Issue Surfacing** | `cross-domain/` | cross_domain.py, evidence.py | test_overview_cross_domain.py, test_overview_demo.py | Existing BI scenario tags plus deterministic relationships and required-domain evidence. |

## Test-first iteration evidence

1. Added metric/API acceptance tests before the module. The first run failed on missing MonitoringConfiguration and module imports.
2. Implemented the first slices: 24 new tests passed; the pre-existing 93-test non-migration regression batch also passed with four PostgreSQL-only skips.
3. Added a ten-test edge batch. Four failures exposed incomplete-source health, row-by-row entity lookups, incompatible trend comparisons, and evidence owner self-references. Fixed the implementation and reran those tests.
4. Added command acceptance tests before simulate_overview existed; two tests failed on the missing command. Implemented isolated declared inputs and real-view validation; demo and edge tests passed.
5. Added and fixed completed-period snapshot and effective-expiry regressions, then expanded calendar, all-nine-scenario, precision, malformed metadata and concurrency coverage.
6. Final verification results are recorded below after running the final working tree.

The process uses bounded test-first iterations: write focused acceptance/regression tests, observe failure, implement or repair, rerun, then run the complete regression suite. A failing check is not treated as completion.

## Verification

Final verification (Python 3.12.14, pinned project dependencies):

| Check | Result |
| --- | --- |
| Complete PostgreSQL suite, pgvector/pgvector:pg16 | 147 passed, no skips |
| Complete SQLite suite | 140 passed; 7 PostgreSQL-specific skips; 147 discovered |
| Fresh SQLite migration through 0003 | Passed, disposable /tmp database |
| Fresh PostgreSQL migration through 0003 | Passed, disposable local container/database |
| simulate_overview on SQLite | 16 / 16 acceptance outcomes passed |
| simulate_overview on PostgreSQL | 16 / 16 acceptance outcomes passed |
| SQLite demo rerun | Identical report; current state revalidated |
| Django system check | No issues |
| makemigrations --check --dry-run | No changes detected |
| Python compile check | Passed |
| git diff --check | Passed |

The developer's tracked db.sqlite3 was unchanged. The disposable PostgreSQL container was stopped after verification.

Migration coverage verifies 0002 → 0003 preserves BI snapshots and does not create default configuration rows. The pre-existing 0001 → 0002 migration test now restores all latest migration leaves so later module tests run with the full schema.

PostgreSQL-specific coverage verifies serialized first writes, version conflicts, full 24-digit decimal storage and extreme comparisons, plus the earlier integration concurrency tests. SQLite skips these checks explicitly.

The deterministic command validates 16 independent acceptance outcomes through real views. Repeated runs revalidate current state, and corrupted upstream metric inputs cause a nonzero exit.

Known architecture limits and upstream data contracts: [implementation guide](overview-monitoring.md).
