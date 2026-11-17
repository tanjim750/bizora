# Testing, release and database

Domain issue list for the domain owner. Written 2026-11-13 from the read-only audit (details and evidence in `../cross-cutting/audit-*.md`, cross-cutting priorities in `../cross-cutting/AUDIT.md`). **Nothing here has been fixed.** Fix only what the project docs specify; items tagged SPEC-GAP need the lead developer's decision first; no schema change, new endpoint, role or response field without approval. Every fix ships with a regression test; never push.

Tags: **SPEC-DEFECT** contradicts the docs; **SPEC-GAP** docs silent, decision needed; **INTEGRATION** frontend/backend mismatch. `INFERRED` = read from code, not run.

Code areas: `bizora/settings.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `scripts/`, `tests/`, `app/tests/`

| ID | Sev | Tag | Problem | How to fix | Test |
|---|---|---|---|---|---|
| PLA-06 | medium | SPEC-GAP | Insecure runtime defaults: `DEBUG` defaults True when unset (`settings.py:40`); cookie Secure, HSTS and the Browsable API follow DEBUG; Dockerfile and compose run `migrate && runserver 0.0.0.0:8000`, as root, no HEALTHCHECK, source bind-mounted, port 8000 published. | Default DEBUG False with an explicit local switch; gunicorn; `USER app`; healthcheck on `/api/`; migrate as a separate release step; no source bind mount in production. | Build with no `.env`: DEBUG false, non-root |
| PLA-07 | low | SPEC-GAP | `check --deploy`: security.W004 (HSTS) and W008 (SSL redirect); `SECURE_PROXY_SSL_HEADER` unset. | Set `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` and the proxy header once HTTPS terminates at a trusted proxy. | `check --deploy` returns 0 issues |
| PLA-08 | low | SPEC-GAP | No CI, no pip-audit, no hash-pinned lockfile; DRF 3.15.2 is behind later releases (advisories not looked up). | CI: `check --deploy`, `makemigrations --check`, `pip-audit`, tests, ruff. | CI fails on a deliberately outdated pin |
| ENV-01 | medium | INTEGRATION | Dev environment trap: `~/.cache/bizora-venv` was built with Python 3.15 (packages in `lib/python3.15`), the system `python3` is 3.12.3, so Django cannot be imported from a 3.12 shell. Dev data lives in `/tmp/bizora-dev-data` and disappears on reboot. | Rebuild the venv with `python3.12`; keep dev data out of `/tmp` or document `dev-setup.sh` (see `../cross-cutting/ENVIRONMENT.md`). | `manage.py check` runs from a fresh 3.12 venv |
| TEST-01 | low | SPEC-GAP | Tests that build rows with explicit `created_at` are silently overridden by `auto_now_add` fields (Order/Payment/Shipment/Conversation); fixtures must use business-time columns. Full suite takes ~8 min on SQLite; PostgreSQL run (`scripts/verify_domains_postgres.py`, needs Docker) was not executed by this audit. | Add a fixture helper; run the PostgreSQL gate in CI. | - |

## Baseline
Full suite on Python 3.12.3 / Django 4.2.27 / SQLite: 1389 tests OK (18 skipped), `manage.py check` clean, `makemigrations --check --dry-run` no changes (see `../cross-cutting/SUITE-RESULT.md`). Static scan (pyflakes) of `app/`, `bizora/`: only intentional model re-exports. Prior list `docs/backend-issues/testing-release.md`: TS-01..TS-06 were outside this audit's scope and not verified.
