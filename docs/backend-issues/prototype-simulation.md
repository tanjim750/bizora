# Backend issues: Prototype Simulation

Domain status: **blocked (CLI only)**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| PS-01 | blocker | No HTTP endpoint for any of the 11 headings (registry, scenarios, seeds, events, flaws, validation) | Part D section 4B | the domain is absent | an API, or keep it CLI | design-only |
| PS-02 | medium | Only `simulate_*` and `demo_*` management commands exist; hard-coded fixtures, no RNG, no persisted report | Part D section 4B | no report data | persist reports | - |
