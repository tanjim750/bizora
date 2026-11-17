# Backend issues: Business Configuration

Domain status: **partial (mounted; the UI is read-only)**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| BC-01 | FIXED | Configuration module was not mounted | `app/urls.py:25` | - | - | - |
| BC-02 | high | No consumer applies the settings (BI, Graph, AI and Memory never call `app.configuration.selectors`) | Part D section 4A | saved but inert | wire the `effective/` view into consumers | label "saved, not applied" |
| BC-03 | high | POST to a detail URL or PATCH to a collection URL returns 500 | Part D section 2; `views.py:86,95,160,165,182,187`; UNVERIFIED | crashes | return 405 | avoid those calls |
| BC-04 | medium | PUT deep-merges: keys cannot be deleted, credential slots and scope keys behave oddly, GET is not round-trippable | Part D section 5.5 | editing traps | a true PATCH with deletes | send diffs only |
| BC-05 | medium | No option lists; `BIZORA_AI_PROVIDERS`, `BIZORA_EMBEDDING_MODELS`, `BIZORA_AI_MIN_CONFIDENCE` are undefined (mock only) | Part D section 5.18 | hard-coded dropdowns | an options endpoint | Part D section 3 |
| BC-06 | medium | Credentials only as `env:BIZORA_BUSINESS_{id}_NAME` references; reprocessing stays REQUESTED (`worker_available: false`) | Part D section 5.11, B-REPROC | no secrets, no effect | a secret store; a worker | label the state |
| BC-07 | low | Redaction rewrites ordinary words ("Basic delivery applies"); history is 404 until the first write | Part D section 5.12, 5.9 | altered text | redact secrets only | hint in the UI |
