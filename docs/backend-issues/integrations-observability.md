# Backend issues: Integrations and Data Observability

Domain status: **partial (mounted; no live adapters or data producers)**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| IO-01 | FIXED | Observability module was not mounted | `app/urls.py:26` | - | - | - |
| IO-02 | high | No live provider: `register_adapter` is never called; only `is_mock` connections run operations (PRODUCT only), others return 409; Marketing, Analytics, Courier and Calling providers are absent | Part C G5; Part A section 4 | nothing is ever real | ship adapters and a webhook receiver | label mock connections |
| IO-03 | high | No data producer, ingestion endpoint, scheduler or sync trigger; `BIZORA_DOMAIN_ADAPTERS` is defined nowhere so all 7 contract owners stay UNAVAILABLE | Part C G4; Part A G6 | empty screens | build ingestion; provision adapters | empty states |
| IO-04 | medium | `freshness/` filters after pagination (wrong `count`, empty pages that still have `next`) | Part C F-1 | broken paging | filter before paginating | follow `next` |
| IO-05 | medium | Operations: unknown target is 400; FAILED is 200, UNSUPPORTED is 409; first backoff 60 s; the retry cap counts successes; sync-retry eligibility is hidden | Part C section 2.3, D3, D4, F-5 | buttons cannot be gated | a `retryable` flag; clear codes | gate on the documented states |
| IO-06 | low | Providers are empty on a fresh database; no attempt list or audit; `RETRYING` is never set | Part D gaps; Part C F-3, F-14 | connections cannot be added | seed providers | hide the control |
