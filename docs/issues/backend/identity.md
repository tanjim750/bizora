# Identity Resolution

Domain issue list for the domain owner. Written 2026-11-13 from the read-only audit (details and evidence in `../cross-cutting/audit-*.md`, cross-cutting priorities in `../cross-cutting/AUDIT.md`). **Nothing here has been fixed.** Fix only what the project docs specify; items tagged SPEC-GAP need the lead developer's decision first; no schema change, new endpoint, role or response field without approval. Every fix ships with a regression test; never push.

Tags: **SPEC-DEFECT** contradicts the docs; **SPEC-GAP** docs silent, decision needed; **INTEGRATION** frontend/backend mismatch. `INFERRED` = read from code, not run.

Code areas: `app/domains/identity.py`, `app/domains/merge.py`

| ID | Sev | Tag | Problem | How to fix | Test |
|---|---|---|---|---|---|
| DOM-13 | medium | SPEC-GAP (INFERRED) | `merge.plan()` uses the filtered default manager `BusinessFact.objects` (VERIFIED and currently valid only), so draft/expired facts referencing the merged entity are not inventoried or fingerprinted; `plan()` scans every model unbounded and `dry_run` runs it twice (manager POST amplifies load); `execute_merge` returns 200 `{status:'BLOCKED'}` and writes a `MERGE_EXECUTION_BLOCKED` history row on every call. | Use `BusinessFact.all_objects`; cap/limit the scan; return 409 and de-duplicate the history row. | Blocked execute -> 409, one history row |

## Prior list (`docs/backend-issues/identity.md`)
IR-01 (blocked execute returns 200, = DOM-13), IR-02 open; IR-03 open but intended (identity is manager-only per SRS line 116).
