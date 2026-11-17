# Backend issues: Business Intelligence

Domain status: **unmounted and blocked**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| BI-01 | blocker | Not mounted: no `business_intelligence` include in `app/urls.py` or `bizora/urls.py` | Part E section 1; grep on main 8010daa | no BI screens | pick a URL prefix and mount | design-only pages and "Not connected" |
| BI-02 | blocker | Views read `request.business`/`auth_business`, which nothing sets; `HasAuthorizedBusiness` replaces `IsAuthenticated`; no role check | Part E section 2a | every call would return 403 | business id in the URL plus domain `authorize()` | - |
| BI-03 | blocker | Nothing runs the metric calculators; `pipeline/run/` only reconciles relationships, syncs the 42-row registry and counts | Part E gap 4; frontend.md P4 | metrics, facts, issues are empty; Overview KPIs are UNAVAILABLE | a scheduled job or command | empty states |
| BI-04 | high | `pipeline/run/` returns a constant "COMPLETED" with 200 even after a full rollback (`quarantined_records: 1`); conflict errors return 500 | Part E gap 6, 10 | false success | return failure and the reason | treat `quarantined_records > 0` as failure |
| BI-05 | high | `GET metrics/` writes 42 rows; snapshots return 404 until the first sync; legacy keys are listed | Part E section 2b, gap 13 | caching and 404 surprises | make GET read-only; seed the registry | treat GET as a mutation |
| BI-06 | partly FIXED | Non-VERIFIED facts are hidden: detail, PATCH and upsert now use `all_objects` (commit f933ad8); the list shows them only with `?status=` | diff `api.py:258`, `facts_issues.py`; not run | history is readable via the `status` filter | confirm the default-list intent | pass `status` |
| BI-07 | high | Inferred 500s: non-numeric `value`/`confidence`, non-object `evidence`, missing `issue_type`, array body | Part E gap 8; UNVERIFIED | crashes | validate to 400 | client-side validation |
| BI-08 | medium | One generic 400 text; PATCH of an unknown id gives 400 but of a foreign id gives 403; `fact_ids` accept foreign ids | Part E gap 7 | causes cannot be told apart | `{code, detail}`; verify ownership | log only |
| BI-09 | medium | Upsert on (type, `rule_key`) so POSTs without a key overwrite each other; no subject fields; evidence tables are never written | Part E section 2b, 4 | lost records | accept subject fields; write evidence | always send a unique `rule_key` |
| BI-10 | medium | Bad `limit`/`offset` are silently reset; no tie-break ordering; no unit or currency; no endpoints for relationships, attribution, anomalies or calculations | Part E section 2b, 4 | page drift; blocked screens | validate; decide scope | design-only pages |
