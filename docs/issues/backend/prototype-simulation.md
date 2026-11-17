# Prototype Simulation

Domain issue list for the domain owner. Written 2026-11-13 from the read-only audit (details and evidence in `../cross-cutting/audit-*.md`, cross-cutting priorities in `../cross-cutting/AUDIT.md`). **Nothing here has been fixed.** Fix only what the project docs specify; items tagged SPEC-GAP need the lead developer's decision first; no schema change, new endpoint, role or response field without approval. Every fix ships with a regression test; never push.

Tags: **SPEC-DEFECT** contradicts the docs; **SPEC-GAP** docs silent, decision needed; **INTEGRATION** frontend/backend mismatch. `INFERRED` = read from code, not run.

Code areas: `app/management/commands/simulate_*.py`, mock scenario models

| ID | Sev | Tag | Problem | How to fix | Test |
|---|---|---|---|---|---|
| PS-01 | medium | INTEGRATION | Simulation is CLI only (`simulate_configuration`, `simulate_observability`, `simulate_overview`); no HTTP surface. Not run by this audit. | Lead decides whether an HTTP API is in scope (docs). | - |
| PS-02 | low | SPEC-GAP | CLI-only with hard-coded fixtures (not re-probed). | Lead decides. | - |
| OVERVIEW-DEMO | low | INTEGRATION | `app/overview/demo.py` seeds short-key `BusinessMetric` rows (`total_revenue`...), which hides the BI-key mismatch (DOM-01) and makes Overview look healthy only in the demo. | Keep the demo, but also exercise a BI-fed path in the demo after the key decision. | - |

## Prior list
PS-01 and PS-02 still open as of the audit; nothing else new.
