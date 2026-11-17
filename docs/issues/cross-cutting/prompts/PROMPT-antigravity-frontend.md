# Prompt for Antigravity (frontend agent). Copy everything below the line.

---

Continue the Bizora frontend overhaul (branch `frontend-overhaul`). Frontend only: `frontend/**`, `docs/frontend-overhaul/**`, `docs/backend-issues/**`. Never touch the backend, never push, never open `.env*`.

The backend branch `bi-graph-integration` (merged later by the owner) mounts the Business Intelligence and Business Graph APIs. Read `docs/issues/cross-cutting/API-CONTRACT.md` (exact paths, shapes, roles, errors) and `docs/issues/cross-cutting/AUDIT.md` (section "Integration problems for the frontend team"). Then:

1. Keep the BI/Graph adapters "Not connected" until the owner confirms the branch is merged and the dev server restarted. When it is, switch them on against the contract, tolerating extra fields.
2. Honest states, per the audit: no value for BI metric snapshots yet (the proxy rejects dotted metric keys, BIA-01; ask the owner which fix they choose); `pipeline/run/` does not compute metrics (BIA-03), show "Not computed" not success; Overview KPIs stay UNAVAILABLE (DOM-01); Graph edges may reference nodes missing from `nodes` when `truncated` is true (BGA-03), so draw only edges whose endpoints are present; journeys for product/campaign are summaries only.
3. Error handling: BI/Graph errors are `{code, detail[, fields]}`; other endpoints may return `{detail}` or HTML 500; keep the normalizer defensive.
4. Do not change the proxy semantics yourself except what the owner approves: client-IP forwarding (PLA-02) and wrapping non-JSON upstream errors (PLA-10) are recommendations to the owner.
5. Record every new backend problem you find as a row in the matching `docs/backend-issues/<domain>.md` using the template in `docs/backend-issues/README.md`; do not fix backend code. Statuses for BI-01..BI-05, BI-07, BG-01..BG-03, BG-05, BG-06 are in `AUDIT.md`; update those rows when the owner confirms the merge.
