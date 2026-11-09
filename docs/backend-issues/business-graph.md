# Backend issues: Business Graph

Domain status: **unmounted and blocked**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| BG-01 | blocker | `app.business_graph` cannot be imported on Python 3.12: `projection.py:53` annotates `type[models.Model]` where `models` is `app.models` | line read directly; full test run on 3.12: 1,297 tests, 1 error (this import) | cannot be mounted on the declared runtime; no Graph test runs | import Django's `Model` for the annotation | - |
| BG-02 | blocker | Not mounted; same `request.business` seam as BI-02 | Part E section 1, 2a | every call would return 403 | mount with a membership check | the live `graph-context/{kind}/{pk}/` one-hop route |
| BG-03 | blocker | BI writes `bi.relationship.<name>.v1` while Graph accepts bare `<name>`: nodes appear, zero edges (still open on main) | Part E gap 1; `relationships.py:70` vs `projection.py:72-96` | no connections | align the keys; add a BI-to-Graph test | - |
| BG-04 | high | Journeys return 400 until `rebuild/` has run; one bad relationship rolls back all; synchronous; `clean` must be a JSON boolean | Part E section 2e | fragile | async rebuild; per-row quarantine | send JSON booleans |
| BG-05 | high | No caps on `max_depth`, `max_nodes` or `limit`; snapshots are unbounded | Part E gap 9 | huge payloads | enforce caps | client-side small caps (depth 2, nodes 200) |
| BG-06 | high | Inferred 500s: non-integer params, bad or naive datetimes, negative `limit` | Part E gap 8; UNVERIFIED | crashes | return 400 | validate on the client |
| BG-07 | medium | Errors leak the owning business id; "not found" is 400; product and campaign journeys are summaries only; malformed filters are ignored | Part E section 2a, 2d | information leak; thin data | generic errors; full shapes | never show raw error text |
