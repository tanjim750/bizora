# Unresolved testing and release issues

Updated: 9 November 2026. These items were not fixed or verified in this local test pass. They are not counted as passing tests.

| Priority | Issue | Evidence and next action |
| --- | --- | --- |
| High | PostgreSQL 16 integration and multi-writer behavior remain unverified. | Docker API access was denied in this workspace, and no usable PostgreSQL credentials were available. The SQLite run skipped 18 tests, including PostgreSQL row-lock and pgvector coverage. Run `scripts/verify_domains_postgres.py` in an environment with Docker access before release, or run the equivalent isolated PostgreSQL job in CI. |
| High | Production HTTPS policy needs deployment decisions. | `manage.py check --deploy` reports `security.W004` (HSTS unset) and `security.W008` (Django SSL redirect unset). Configure HTTPS redirection at the edge or Django as appropriate, then set HSTS only after confirming the entire public site is HTTPS. Re-run the deployment check and a real HTTPS login/write flow. |
| Medium | Whole-repository Python lint is not clean. | `ruff check app bizora tests` reports 639 findings in existing code. The new runner passes targeted Ruff. Triage and fix the baseline in separate code phases, then enforce a clean lint gate. |
| Medium | Production-scale performance, load, and breaking-point stress are unmeasured. | The SRS defines no throughput, latency, or recovery targets. The local 50-read burst is only a smoke check. Agree on service objectives, then test against production-like PostgreSQL, representative data, and deployment infrastructure. |
| Medium | Browser and accessibility coverage is incomplete. | Only local Chrome/Chromium was exercised. Firefox, WebKit/Safari, other operating systems, assistive technology, and a formal accessibility audit were unavailable. Run a cross-browser matrix and accessibility review before broad release. |
| Medium | Python 3.12 runtime was not executed locally. | The available `.venv` uses Python 3.14.4, while repository guardrails target 3.12. Run the full suite and migration checks on Python 3.12 in CI or a matching container. |
| Medium | Tests are not wired into a repository CI workflow. | No `.github/workflows` exists. The repeatable runner is local; add protected-branch jobs for Python 3.12/PostgreSQL 16, frontend unit/build, and full-stack browser tests, then verify the workflow on a remote runner. |
| Medium | Human acceptance and external beta testing were not performed. | A business owner must review the SRS flows, real data expectations, usability, and provider behavior. Beta testing requires opted-in users and a safe staging environment; neither was available here. |
| Low | Python dependency vulnerability audit was unavailable. | `pip check` passed, but `pip-audit` is not installed. Run a dependency vulnerability scan in CI and triage findings before release. |

Existing SRS limitations also remain: some owner services and provider actions are partial or unavailable by design. A passing local UI flow must not be interpreted as proof of live provider execution.
