# Bizora frontend

Next.js 16 operations client for the mounted Django APIs. The visual system follows [`docs/requirements/DESIGN.md`](../docs/requirements/DESIGN.md).

## Local setup

1. Start PostgreSQL 16 for authoritative development, or use the isolated SQLite fallback with `BIZORA_DATA_DIR` and `bizora.local_settings`.
2. Run Django migrations and start Django on `127.0.0.1:8000`.
3. From `frontend/`, run `npm ci` and `npm run dev`. Open `http://localhost:3000`.

The server-side `DJANGO_API_ORIGIN` defaults to `http://127.0.0.1:8000`. Set it to the internal Django origin in deployment. Browser requests go through `/api/backend/...` on the Next.js origin. The proxy forwards Django session and CSRF cookies; it checks the browser origin for writes. Keep frontend traffic on HTTPS in production.

The frontend does not keep credentials or access tokens in local storage. Login and logout use `/api/frontend/` session endpoints; all business authorization remains in Django.

## Checks

```sh
npm test
npm run build
```

For the live browser flow, run Django and Next.js against a **local test business**, then:

```sh
BIZORA_E2E_USERNAME=... BIZORA_E2E_PASSWORD=... npm run test:e2e
```

Use a manager membership in an isolated business. Seed one connected integration source and one product with SKU `TEA`, then set `BIZORA_E2E_CONNECTION_ID` and `BIZORA_E2E_PRODUCT_ID` to their IDs. The operation tests create unique records through the API. Playwright uses one worker because the local SQLite fixture is shared across tests. Do not point these tests at production data.

Playwright uses `/usr/bin/google-chrome` by default. Set `PLAYWRIGHT_CHROME_EXECUTABLE` if Chrome is elsewhere. Set `BIZORA_E2E_URL` when Next.js is not on `http://127.0.0.1:3000`.

The current endpoint coverage and remaining work are recorded in [`frontend-progress.md`](../docs/implementations/frontend-progress.md).
