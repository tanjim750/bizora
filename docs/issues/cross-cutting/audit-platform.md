# Audit: platform, security, release (subagent report 2026-11-11; some late probes INFERRED)

363 routes (api/ mounted twice). Persona sweep (anonymous, non-member, other-tenant owner, VIEWER, MEMBER, OPERATOR, MANAGER, ADMIN): no tenant leak or anonymous 2xx on business routes; only intended anonymous 200s (`GET /api/`, `/api/frontend/session/`, `/ops/login/`). No state-changing GET; business id only from URL.

| ID | Sev | Tag | Problem | Fix |
|---|---|---|---|---|
| PLA-01 | high | SPEC-GAP | No `DEFAULT_AUTHENTICATION_CLASSES` (Session + Basic active on every route) and no throttling anywhere (`settings.py:206-219`). | Session auth only; DRF throttles anon 30/min, user 300/min, scoped `ai` 20/min; shared cache. Test: 12th wrong Basic request -> 429. |
| PLA-02 | high | SPEC-GAP, INTEGRATION | `frontend_login` (`frontend_auth.py:35-48`) and `/ops/login/` have no brute-force protection; proxy forwards no client IP (`route.js:34`). | Rate-limit by username+IP (cache counter/django-axes); proxy forwards `x-forwarded-for`, Django trusts proxy. |
| PLA-03 | medium | SPEC-DEFECT | AI POST endpoints (`app/views.py:50-57`, `roles=None`) open to VIEWER/MEMBER, write AiConversation/AiMessage, up to 15 s blocking LLM call each. | OWNER/MANAGER/OPERATOR for POST routes; role `choices` on BusinessMembership (needs migration, ask). |
| PLA-04 | medium | SPEC-DEFECT | Role vocab inconsistent: AI actions allow {OWNER, ADMIN, OPERATOR}, exclude MANAGER (`views.py:75,102,120`); non-member gets 403 for existing vs 404 for missing business/action on legacy AI routes (enumeration). | One helper (`require_access`, manage=True for approve/reject/execute); membership check before `get_object_or_404`. |
| PLA-05 | medium | SPEC-GAP | No `LOGGING` config: 500s not logged with DEBUG off; sweep saw 5-8 HTTP 500s per user on `{}` bodies (endpoint list lost). | LOGGING dict (django.request, django.security, app -> console INFO); re-run sweep, 500 -> 400. |
| PLA-06 | medium | SPEC-GAP | `DEBUG` defaults True if unset (`settings.py:40`); Dockerfile/compose run `migrate && runserver`, root user, no healthcheck, source bind mount. | Default DEBUG False; gunicorn; non-root; healthcheck `/api/`; separate migrate step. |
| PLA-07 | low | SPEC-GAP | `check --deploy`: W004 HSTS, W008 SSL redirect; no `SECURE_PROXY_SSL_HEADER`. | Set when HTTPS proxy exists. |
| PLA-08 | low | SPEC-GAP | No CI, no pip-audit; DRF 3.15.2 behind later releases. | CI: check --deploy, makemigrations --check, pip-audit, tests. |
| PLA-09 | low | SPEC-GAP | `/admin/` default path; git history has an old hard-coded production SECRET_KEY (commit 2732e07), now rejected when DEBUG off. | Restrict admin; never reuse that key. |
| PLA-10 | low | INTEGRATION | Proxy passes upstream bodies through unchanged (DEBUG HTML page possible); Origin check allows missing Origin; bodies read via `.text()` (no multipart). | Wrap non-JSON errors as `{detail}`. |

Healthy: CSRF on login/logout, session rotation, password validators, cookie Secure follows DEBUG, tracked-file secret scan clean, credentials via env refs, proxy path regex blocks traversal/SSRF, ops UI POST-only with CSRF + role re-check.
