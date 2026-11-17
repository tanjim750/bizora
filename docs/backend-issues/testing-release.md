# Backend issues: Testing, release and database

Domain status: **partial**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| TS-01 | high | Python 3.12 run: 1,297 tests, 1 error (BG-01), 1 failure (TS-02), 18 skipped; the team reports 1,341 run on Python 3.14 (the gap is unexplained) | checkpoint; tests/testing_report.md | Graph is untested | fix BG-01; run CI on 3.12 | - |
| TS-02 | medium | `test_dat_003_sqlite_schema_drift_missing_slug_column` fails on a clean checkout (it reads the physical `db.sqlite3`) | `app/test_p0_regressions.py:51`; checkpoint | red suite | make the test hermetic | - |
| TS-03 | high | PostgreSQL 16, row locks and pgvector are unverified (18 skipped); SQLite ignores `select_for_update` | tests/issues.md; Part B GAP-16 | concurrency is unproven | run `scripts/verify_domains_postgres.py` in CI | - |
| TS-04 | high | `check --deploy` reports `security.W004` (HSTS) and `security.W008` (SSL redirect) | tests/issues.md | insecure defaults | set after the HTTPS decision | - |
| TS-05 | medium | No CI (`.github` absent); Ruff reports 639 findings; no `pip-audit`; no load, accessibility, cross-browser or acceptance data | tests/issues.md; tests/testing_report.md | regressions slip through | add jobs and targets | - |
| TS-06 | FIXED | `IntegrationSyncLog.created_at` drift; Compose now selects PostgreSQL | migration `0010`; `docker-compose.yml` | - | - | - |
