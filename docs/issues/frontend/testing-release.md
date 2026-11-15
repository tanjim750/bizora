# Testing, release and database: frontend issues

Backend counterpart: [`../backend/testing-release.md`](../backend/testing-release.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| ENV-01 | medium | Dev environment trap: `~/.cache/bizora-venv` was built with Python 3.15 (packages in `lib/python3.15`), the system `python3` is 3.12.3, so Django cannot be imported from a 3.12 shell. Dev data lives in `/tmp/bizora-dev-data` and disappears on reboot. | Document the Python 3.12 venv in the frontend dev-setup notes. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
