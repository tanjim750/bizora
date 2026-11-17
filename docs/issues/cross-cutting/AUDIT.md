# Bizora backend audit (2026-11-11), index and priorities

Detail lives in the per-area files next to this one: `audit-bi.md` (BIA), `audit-graph.md` (BGA), `audit-domains.md` (DOM), `audit-platform.md` (PLA), `audit-ai.md` (AIS). Every finding is tagged:

- **SPEC-DEFECT**: contradicts the project docs (`docs/implementations/features/*.md`, `docs/requirements/*`). Fixing it is in scope.
- **SPEC-GAP**: docs are silent. Do NOT implement; the owner decides first.
- **INTEGRATION**: frontend/backend mismatch. Document or coordinate; backend change only if the owner agrees.
- Not reported on purpose: API keys, LLM provider setup, credentials (a senior provides them).

Owner rule in force: only what the docs specify; no new endpoints, models, migrations, response fields, roles or features without asking. Method: five read-only auditors, live probes on a disposable SQLite DB, plus the full test suite. About 40% of the domain/graph items are code-read (marked INFERRED).

## What this branch (`bi-graph-integration`, uncommitted tail) already fixed

| Change | Doc id | Proof |
|---|---|---|
| `projection.py` imports Django `Model` (3.12 import) | BG-01 | `app/business_graph/tests/test_imports.py` |
| URLs mounted at `businesses/<id>/intelligence/` and `/graph/`; tenant from URL + `require_access` (read any member, write OWNER/MANAGER); anonymous/foreign 403 | BI-01, BI-02, BG-02 | `app/tests/test_bi_graph_access.py` |
| Graph missing and foreign entities answer the same generic 404; errors `{code, detail}` | BG-07, BI-08 (shape) | `test_bi_graph_access.py`, `test_api_and_scenarios.py` |
| BI rule keys `bi.relationship.<name>.v1` project into edges | BG-03 | `app/business_graph/tests/test_bi_graph_integration.py` |
| `run_intelligence` command runs registry sync + existing calculators | BI-03 | `app/business_intelligence/tests/test_pipeline.py` |
| Pipeline failure reported (500 `PIPELINE_FAILED`), conflicts 409 | BI-04 | `test_api_hardening.py` |
| `GET metrics/` read-only | BI-05 | `test_api_hardening.py` |
| Fact/issue bodies validated to 400 | BI-07 | `test_api_hardening.py` |
| Graph ints/datetimes/bodies validated; caps depth 5, nodes 1000, limit 1000 | BG-06, BG-05 | `test_api_input_validation.py` |

Commits exist for the first three rows only (b8e76c5, d95f7a2, 1fc5c38); the rest is uncommitted by instruction until the owner settles the branch policy.

## Deviations from "docs only" the owner must confirm (each is reversible)

1. URL prefixes `intelligence/` and `graph/` (BI-01 says "pick").
2. Role rule: reads any member, writes OWNER/MANAGER via `require_access` (docs silent; domain `authorize()` has write=OPERATOR+).
3. Error body `{code, detail}` for BI/Graph (BI-08/BG-07 ask for it; revert in `app/business_scope.py handle_exception`).
4. New shared module `app/business_scope.py`.
5. BG-05 cap values 5/1000/1000 (docs give none). Constants at top of `app/business_graph/api.py`.
6. BI-04 failure status 500 (docs: "return failure and the reason").
7. `GraphNotFoundError` subclass in `projection.py` (service-level change behind BG-07).
8. `run_intelligence` management command (BI-03 says "scheduled job or command").
9. Not touched on purpose: BG-04 (async/quarantine), BI-06, BI-09, BI-10 and every SPEC-GAP below.

## Priority list for the fixer (Codex or Antigravity)

**P0 (correctness/security, SPEC-DEFECT):**
1. BGA-01 non-clean rebuild deletes/recreates website-event nodes (id churn). 2. BGA-02 `clean:"false"` wipes graph. 3. BGA-03 truncated traversal returns dangling edges. 4. BGA-04 `min_confidence` NaN -> 500. 5. BIA-04 different issues overwrite each other (`BusinessIssue.save`). 6. AIS-01/AIS-02 VIEWER can mutate via AI routes; two approval routes, execution without approver. 7. AIS-05 prompt-injection wrapper bypass; AIS-07 unapproved knowledge in prompts. 8. DOM-02 / PLA-04 role models diverge (needs the owner's role decision first). 9. DOM-03 / BIA-12 / BGA-15 huge integers give HTML 500 (global exception handler + bounded path converter). 10. PLA-01/PLA-02 Basic auth enabled, no throttling or login lockout.

**P1:** BIA-06/07 foreign ids accepted/oracle (BI-08); BGA-05/07/08/09/10/11; DOM-01/BIA-02 Overview KPIs cannot read BI keys (design decision); AIS-03/04/08/09/10/11/12; DOM-04..DOM-13; PLA-03/05/06.

**P2:** the rest.

## Integration problems for the frontend team (no backend change implied)

- Metric snapshot route uses dotted keys; the Next proxy rejects dots (BIA-01). Until decided, the frontend cannot show a BI value.
- Overview KPIs stay UNAVAILABLE (DOM-01/BIA-02): key vocabulary, timezone windows and units differ.
- `pipeline/run/` computes no metrics; metrics need the command (BIA-03). Show "Not computed" rather than success.
- Error bodies: BI/Graph `{code, detail[, fields]}`; DRF-native and older endpoints differ (DOM-11); some paths return HTML 500/404 (DOM-03).
- Graph responses lack node_type/timestamps/direction and journeys have no nodes/edges (BGA-10); `traversal`/`query` can return dangling edges (BGA-03). Draw only edges whose endpoints are present.
- Pagination styles differ across modules (BIA-14, DOM-16).
- Proxy: no client IP forwarding (PLA-02), upstream errors passed through unchanged (PLA-10).

## Test-suite baseline

See `SUITE-RESULT.md` in this folder when present (full run of 1377+ tests on Python 3.12).
