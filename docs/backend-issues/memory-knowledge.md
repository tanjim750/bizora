# Backend issues: Business Memory and Knowledge

Domain status: **blocked (service-only)**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| BM-01 | blocker | No HTTP endpoint for any of the 19 features (profile, policies, brand tone, goals, decisions, sources, ingestion, search, versioning) | Part B section 2E, 4B | the domain is absent | decide the API | design-only; show `applied_policies` and `active_goals` where they appear |
| BM-02 | high | No upload route, embedding provider or search caller; the lifecycle is unreachable (see AI-08) | Part B GAP-4, 14 | no search | build the pipeline | - |
| BM-03 | FIXED | `BusinessMemory`, `HistoricalDecision`, `ApprovedSuggestion`, `re`, `ValidationError` were missing | `app/models.py:1-4`; checkpoint | - | - | - |
