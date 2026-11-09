# Backend issues: Overview and Monitoring

Domain status: **partial (mounted; data mostly UNAVAILABLE)**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| OM-01 | FIXED | Overview module was not mounted | `app/urls.py:24` | - | - | - |
| OM-02 | medium | The root `overview/` route stays the domain placeholder (`business_health` UNAVAILABLE); the real module is `overview/summary`, `kpis`, `trends`, `health` and so on | `app/urls.py:24` vs `:98`; Part C section 2.7 | two sources for one idea | merge or rename | use `summary/` |
| OM-03 | high | KPIs, trends and health are UNAVAILABLE without BI snapshots (BI-03) | Part C section 5.4 | an empty dashboard | fix BI-03 | null means unavailable, not 0 |
| OM-04 | medium | Errors are bare lists, `{field: "text"}` or `{"unknown": [...]}` with no `code`; configuration PUT rejects echoed GET fields; `health/` scans all issues | Part C section 2.0, 5.15, F-10 | parser sprawl; performance | `{code, detail}`; accept echoed objects | error normaliser; send diffs |
