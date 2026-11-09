# Backend issues: Identity Resolution

Domain status: **live (MANAGER/OWNER only; merge blocked by design)**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| IR-01 | medium | `execute-merge` is always BLOCKED; dry-run readiness stays WAITING_FOR_OWNERS (no adapters) | Part A D14, D24 | no consolidation | decide the executor and adapters | read-only plan with "Blocked by design" |
| IR-02 | medium | Commands need raw ids; no lookup by value; only 25 evidence rows; few filters; no match-rejection route | handoff F03; Part A section 2.4, 4 | clumsy review | lookup, pagination, filters | id entry; page through |
| IR-03 | medium | All identity GET and POST need MANAGER; there is no read-only role | Part A D13 | operators are locked out | confirm the intent | hide for non-managers |
