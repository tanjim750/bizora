# Frontend–backend integration test report

Date: 9 November 2026

## Scope and finding

The Next.js client uses `/api/backend/...` as a same-origin proxy to Django `/api/...`. The proxy already forwarded session cookies, CSRF tokens, request bodies, and query strings. It checked the browser origin for writes, but omitted an upstream `Origin` header. With Django served over HTTPS, a write without `Origin` or `Referer` fails Django's CSRF check even when the token is valid. This breaks production sign-in and other writes.

The proxy now sends the configured Django origin on writes after checking the browser origin. Django remains responsible for CSRF validation and business authorization. No authoritative records are created by the proxy or AI advisory code.

## Automated verification

| Check | Result |
| --- | --- |
| Frontend unit tests: `npm test` | 7 passed. The new proxy assertion failed before the fix and passed after it. |
| Django focused tests: `DEBUG=True .venv/bin/python manage.py test app.tests.test_frontend_auth app.tests.test_frontend_integration app.tests.test_module_route_mounts --noinput` | 6 passed. The new secure-request test confirms Django rejects a missing origin and accepts the upstream origin with a valid CSRF token. |
| Django app suite: `DJANGO_SETTINGS_MODULE=bizora.local_settings BIZORA_DATA_DIR=/tmp/bizora-connection-check .venv/bin/python manage.py test app --noinput` | 1,341 run: 1,323 passed, 18 skipped. |
| Frontend production build: `npm run build` | Passed. |
| Frontend format check: `npm run format:check` | Passed. |
| Isolated SQLite migrations: `DJANGO_SETTINGS_MODULE=bizora.local_settings BIZORA_DATA_DIR=/tmp/bizora-connection-check .venv/bin/python manage.py migrate --noinput` | Passed. |
| Live browser integration: `npm run test:e2e` with `BIZORA_E2E_URL=http://127.0.0.1:13000` and isolated manager, connection, and product fixture | 5 passed. Covered session login, mounted sections and canonical lists, identity linking, product source review, refund, callback, outbound preparation, contract probes, and mobile navigation. |

The browser run used Next.js production mode on port 13000 and Django on port 18000, both pointed at `/tmp/bizora-connection-check/development.sqlite3`. The test data is outside the repository. The full Django suite used Django's separate test database. The event-dispatcher exception traces in the suite are expected output from tests that intentionally exercise failing subscribers; the suite finished successfully.

## Limits

PostgreSQL 16 integration was not run: no usable PostgreSQL connection credentials or local `pg_isready` binary were available. The browser check used the documented SQLite development fallback, so it does not establish PostgreSQL behavior. The local virtual environment runs Python 3.14; Python 3.12 compatibility was not separately executed. The live browser check used HTTP; the HTTPS CSRF case was verified with Django's secure-request regression test and the proxy unit test.
