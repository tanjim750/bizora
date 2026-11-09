# Production-focused test report

Date: 9 November 2026. Scope: Django API, Next.js client, their session proxy, and the requirements in `docs/requirements/SRS.md` and `USE_CASES.md`. This report supplements the earlier `frontend_backend_integration_report.md`.

## Reproducible run

From the repository root, after installing `requirements.txt` into `.venv` and running `npm ci` in `frontend/`:

```sh
DJANGO_SETTINGS_MODULE=bizora.local_settings BIZORA_DATA_DIR=/tmp/bizora-test-audit .venv/bin/python manage.py test app --noinput
cd frontend && npm test && npm run format:check && cd ..
.venv/bin/python tests/run_full_stack.py
```

`run_full_stack.py` creates a disposable SQLite database, manager and viewer accounts, two tenants, a source connection, and a product. It builds and starts the production Next.js server plus Django on free loopback ports, runs Playwright, then stops both servers and removes the fixture. It cannot point at production data.

## Results

| Area | Evidence and result |
| --- | --- |
| Django automated suite | 1,341 run in 83.0 s: 1,323 passed, 18 skipped on isolated SQLite. Includes domain unit, API, integration, security, concurrency simulation, and adversarial input tests. Some skips are PostgreSQL-only row-lock/pgvector tests. |
| Frontend unit and proxy tests | `npm test`: 7 passed. Covers path validation, display behavior, product review validation, proxy route/origin rules, and cookie/CSRF forwarding. |
| Full-stack system and regression | Disposable runner: 8 Playwright tests passed in 24.0 s against a Next.js production build and a real Django process. No browser tests were skipped. |
| Business acceptance evidence | Browser tests exercise business selection, canonical lists, identity linking, product review, refund, callback, outbound preparation, and seven owner contract probes. Django tests cover role checks and the rule that proposal review does not execute a provider action. These are automated acceptance checks against selected SRS use cases, not stakeholder UAT. |
| Security | Browser tests passed for viewer read/write separation, manager screen denial, foreign-tenant denial, missing CSRF, cross-origin writes, and logout. Existing backend suite includes adversarial payload and tenant tests. `npm audit` reported zero vulnerabilities. |
| Local performance/load | A bounded burst of 50 authenticated product/customer reads, five concurrent per batch, returned 50 HTTP 200 responses. Observed p50 69 ms and p95 77 ms on this machine. This is a reliability smoke check; the SRS defines no latency or throughput objective. |
| Stress | Existing `app/test_critical_security_and_stress_testing.py` ran within the passing Django suite, including concurrent document versioning, adversarial nested input, and large document chunking. No production-scale traffic or breaking-point test was run. |
| Usability/accessibility and compatibility | Playwright verified mobile navigation at 320 px, no horizontal overflow in the workspace test, keyboard Escape behavior, accessible labels and headings used by locators. The live browser run used local Chrome/Chromium only. |
| Build, migration, dependency checks | `npm run build`, `npm run format:check`, SQLite migrations, `makemigrations --check --dry-run`, targeted Ruff for the new runner, and `pip check` passed. |
| Deployment/static checks | `manage.py check --deploy` returned HSTS and HTTPS redirect warnings. Whole-repository Ruff returned 639 existing findings; these are recorded in `issues.md`. |

## Test level and technique mapping

| Requested type | What was done | Status |
| --- | --- | --- |
| Unit | Node unit tests and Django method/service tests within the app suite | Executed |
| Integration | Django API tests plus browser requests through the Next.js proxy to Django | Executed |
| System / end-to-end | Eight Playwright flows with both services running | Executed on local fixture |
| Acceptance / UAT | Automated checks against selected SRS use cases; no business stakeholder signed off | Partial |
| Manual / exploratory / ad-hoc | No human tester or unscripted session was available; automated route sweep covered mounted sections and lists | Not executed as manual tests |
| Automated / functional / regression | Unit, backend, browser, build, migration, and security checks | Executed |
| Smoke / sanity | Production build, login, workspace, main routes, and focused proxy regression | Executed |
| API / UI / black-box | Browser workflows and HTTP assertions through public routes | Executed |
| White-box / gray-box | Backend service tests, proxy unit tests, and seeded full-stack fixtures | Executed |
| Performance / load | Bounded 50-read local burst with latency observation | Limited local check |
| Stress | Backend adversarial and concurrency tests; no breaking-point environment | Limited |
| Security | Browser auth/tenant/CSRF checks, backend suite, dependency audit | Executed locally |
| Usability / compatibility | Mobile and keyboard checks in Chrome; no formal accessibility or cross-browser matrix | Partial |
| Alpha / beta | Internal pre-release automated tests ran; no external beta users | Alpha evidence only |

## Release interpretation

These passing checks provide strong local regression evidence for the tested paths. They do not establish PostgreSQL 16 behavior, deployment TLS settings, real traffic capacity, external provider execution, cross-browser compatibility, or stakeholder acceptance. Use `manual_acceptance_plan.md` for the human checks, and treat the unresolved items in `issues.md` as release gates where they apply to the deployment.
