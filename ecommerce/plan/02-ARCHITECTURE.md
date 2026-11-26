# 02 — Architecture

Status: plan, written 2026-11-26. Binding for every card. Paths in this kit are relative to the folder `ecommerce/` (the Antigravity workspace root). App code lives in `ecommerce/frontend/`; this plan lives in `ecommerce/plan/`.

## 1. Stack and exact versions (checked on npm 2026-11-26; install EXACTLY these, no `^`)
| Package | Version | Why |
|---|---|---|
| Node.js | 22.x (host has 22.23.2) | Next 16 needs ≥ 20.9 |
| `next` | 16.4.6 | App Router, Server Components, `next/font`, `next/image` |
| `react`, `react-dom` | 19.3.1 | |
| `typescript` | 5.9.3 | Strict mode. TypeScript 6/7 are newer but not chosen: Next's type-check integration is proven on 5.9 (veto-able, see README) |
| `@types/react`, `@types/react-dom`, `@types/node` | 19.3.3, 19.3.0, 22.20.7 | |
| `tailwindcss`, `@tailwindcss/postcss` | 4.3.5 | CSS-first config (`@theme`) mapped to our tokens |
| `motion` | 14.14.0 | Framer Motion's new name; import from `motion/react` |
| `gsap` | 3.15.1 | Includes ScrollTrigger, Flip, SplitText (free) |
| `@gsap/react` | 2.1.2 | `useGSAP` hook (cleanup + scope) |
| `zustand` | 5.1.0 | Cart and session client state |
| `zod` | 4.6.7 | The API contract in code; validates every response |
| `radix-ui` | 1.8.1 | Accessible Dialog (drawers, search), Slider (price), Accordion, Checkbox, RadioGroup, Toast-free (we use our own announcer) |
| `next-themes` | 0.4.6 | Light/dark/system without flash |
| `lucide-react` | 1.80.0 | Icons |
| `clsx` 2.1.1, `tailwind-merge` 3.7.1 | | `cn()` helper |
| `server-only` | 0.0.1 | Build error if a server file is imported by client code |
| Dev: `vitest` 5.1.2, `@vitejs/plugin-react` 6.3.0, `jsdom` 31.0.1, `@testing-library/react` 16.3.3, `@testing-library/user-event` 14.6.13, `@testing-library/jest-dom` 8.0.0 | | Unit + component tests |
| Dev: `@playwright/test` 1.65.1, `@axe-core/playwright` 4.14.1 | | End-to-end + accessibility scans |
| Dev: `eslint` 10.15.0, `eslint-config-next` 16.4.6, `prettier` 3.10.1 | | Lint and format |

The whole set was resolved with `npm install --dry-run` on 2026-11-26 without peer conflicts (606 packages). Rule: a card never adds a dependency. Only SF-01 installs packages. If `npm install` reports a peer-dependency conflict, the card is BLOCKED (never `--force`, never `--legacy-peer-deps`).

## 2. Folder layout (overview; each card's "Files you may change" list is the authority for what that card creates)
```
ecommerce/
  plan/                         ← this kit (cards, ledger, protocol)
  frontend/
    package.json  package-lock.json  tsconfig.json  next.config.ts  postcss.config.mjs
    eslint.config.mjs  .prettierrc.json  .prettierignore  vitest.config.ts  vitest.setup.ts
    vitest.contract.config.ts  playwright.config.ts  .env.example  .gitignore  README.md
    public/
      mock/products/<product-slug>-<n>.jpg     ← product images (SF-06 placeholder script, IMG-01 real photos)
      mock/editorial/<name>.jpg                ← home page imagery
    scripts/
      make-placeholder-images.mjs              ← SF-06
    src/
      app/
        layout.tsx  fonts.ts  globals.css  not-found.tsx  error.tsx  global-error.tsx  sitemap.ts  robots.ts  icon.svg
        (store)/
          layout.tsx                             ← Header + Footer + CartDrawer + SearchDialog (SF-11)
          template.tsx                           ← page-enter transition (SF-12)
          page.tsx  loading.tsx                  ← Home + generic loading skeleton
          shop/page.tsx  shop/loading.tsx
          products/[slug]/page.tsx  products/[slug]/loading.tsx  products/[slug]/not-found.tsx
          cart/page.tsx
          order-confirmation/[orderNumber]/page.tsx
          account/page.tsx
          account/sign-in/page.tsx
          account/register/page.tsx
          account/orders/[orderNumber]/page.tsx
        (checkout)/
          layout.tsx                             ← reduced checkout header, no footer nav (SF-27)
          checkout/page.tsx
        api/store/[...path]/route.ts             ← the MOCK backend (only used when API_BASE_URL is empty)
      components/
        ui/          Button.tsx IconButton.tsx Input.tsx Field.tsx Select.tsx Checkbox.tsx RadioCard.tsx
                     Badge.tsx Skeleton.tsx Price.tsx Spinner.tsx VisuallyHidden.tsx Container.tsx index.ts
        layout/      Header.tsx Footer.tsx MobileNav.tsx SkipLink.tsx ThemeToggle.tsx CartButton.tsx AccountLink.tsx SearchButton.tsx CheckoutHeader.tsx
        providers/   Providers.tsx Announcer.tsx CartHydrator.tsx SessionHydrator.tsx
        motion/      Reveal.tsx RollingNumber.tsx
        cart/        CartDrawer.tsx CartLine.tsx QuantityStepper.tsx FreeShippingMeter.tsx CartPageView.tsx
        search/      SearchDialog.tsx
        product/     ProductCard.tsx ProductGrid.tsx ProductCardSkeleton.tsx ProductGallery.tsx ProductView.tsx
                     VariantPicker.tsx AddToCart.tsx StickyAddToCart.tsx StockBadge.tsx ProductDetails.tsx RelatedProducts.tsx
        catalog/     FilterPanel.tsx FilterSheet.tsx SortSelect.tsx ActiveFilters.tsx Pagination.tsx CatalogView.tsx
        home/        Hero.tsx CategoryTiles.tsx pick-categories.ts FeaturedRail.tsx EditorialBand.tsx Newsletter.tsx ValueStrip.tsx
        checkout/    CheckoutForm.tsx ShippingMethodPicker.tsx PaymentMethodPicker.tsx OrderSummary.tsx
        account/     AuthForm.tsx AccountGuard.tsx AccountView.tsx OrderHistory.tsx OrderDetail.tsx StatusBadge.tsx
        order/       ConfirmationView.tsx ConfirmationCheck.tsx OrderLines.tsx
      lib/
        cn.ts
        api/         types.ts schemas.ts errors.ts create-api.ts browser.ts server.ts transport-http.ts transport-mock.ts
        format/      money.ts date.ts
        motion/      tokens.ts gsap.ts use-reduced-motion.ts fly-to-cart.ts
        catalog/     query.ts
        product/     variants.ts json-ld.ts
        checkout/    validation.ts idempotency.ts
        auth/        validation.ts redirect.ts
      stores/        cart-store.ts session-store.ts announce-store.ts ui-store.ts
      mocks/
        fixtures/    store.json categories.json products.json home.json users.json orders.json
        server/      router.ts db.ts http.ts catalog.ts cart.ts auth.ts checkout.ts orders.ts
    tests/
      stubs/         server-only.ts                  ← empty module so Vitest can import server files
      unit/          <card-id>-<slug>.test.ts(x)     ← one file per card (Vitest)
      contract/      live-contract.test.ts           ← SF-34, run only by `npm run contract:check`
      e2e/           *.spec.ts                       ← Playwright (SF-32, SF-33)
```

## 3. Rendering model
| Route | Rendering | Data |
|---|---|---|
| `/` Home | Server Component page; animated sections are client components that receive data as props | `content.getHome()`, `catalog.listProducts({collection:'featured', pageSize: 8})`, `catalog.listCategories()` via `serverApi` |
| `/shop` | Server Component reading `searchParams` (dynamic). Filter/sort controls are client components that update the URL with `router.replace(url, { scroll: false })` inside `startTransition`; the grid dims (`opacity-60`, `aria-busy="true"`) while pending | `serverApi.catalog.listProducts(query)` + `listCategories()` |
| `/products/[slug]` | Server Component; `notFound()` on API 404; `generateMetadata` from the product | `serverApi.catalog.getProduct(slug)`, `getRelated(slug)` |
| `/cart`, `/checkout`, `/order-confirmation/[n]`, `/account/**` | Server page shell + client component doing all data work through `browserApi` (cookies travel automatically, same origin) | cart, session, orders |

Public GETs on the server use `next: { revalidate: 60 }` in HTTP mode. Everything with cookies (cart, auth, checkout, orders) is only ever called from the browser.

## 4. Data-access layer (the seam the backend plugs into)
**Rule: no component, page or store calls `fetch` directly or imports a fixture.** Everything goes through `lib/api`.

- `lib/api/types.ts` — TypeScript types inferred from the zod schemas (`export type Product = z.infer<typeof ProductSchema>` …). Names are exactly the schema names of 03-API-CONTRACT.
- `lib/api/schemas.ts` — one zod schema per JSON object in 03-API-CONTRACT (the contract in code).
- `lib/api/errors.ts` — `class ApiError extends Error { status; code; fields; requestId }`, `isApiError()`, the `ErrorCode` union, `toUserMessage(error)` (friendly text per code, table in 03-API-CONTRACT §3).
- `lib/api/create-api.ts` — `createApi(transport)` returns `{ store, catalog, content, cart, auth, checkout, orders, newsletter }`; every method builds the request, calls the transport, throws `ApiError` on non-2xx (body parsed with `ErrorEnvelopeSchema`, falling back to code `UNKNOWN`), and parses success bodies with the matching schema (`schema.parse`; a parse failure throws `ApiError` with code `CONTRACT_MISMATCH`, status 502, so a backend drifting from the contract is caught loudly).
- Transport type: `type Transport = (req: ApiRequest) => Promise<ApiResponse>`; `ApiRequest = { method: 'GET'|'POST'|'PATCH'|'DELETE'; path: string; query?: Record<string, string | string[] | undefined>; body?: unknown; headers?: Record<string,string> }`; `ApiResponse = { status: number; body: unknown; headers: Record<string,string> }`.
- `lib/api/transport-http.ts` — `createHttpTransport(baseUrl, init?)`: `fetch(baseUrl + path + query, { method, headers: {'Accept':'application/json', 'Content-Type':'application/json' when body}, body: JSON.stringify(body), credentials: 'include', ...init })`; network failure → `ApiError` code `NETWORK_ERROR`, status 0.
- `lib/api/transport-mock.ts` — `import 'server-only'`; calls `handleMockRequest` from `src/mocks/server/router.ts` in-process (no network, works during `next build`).
- `lib/api/server.ts` — `import 'server-only'`; `export const serverApi = createApi(process.env.API_BASE_URL ? createHttpTransport(process.env.API_BASE_URL, { revalidate: 60 }) : mockTransport)`.
- `lib/api/browser.ts` — `'use client'`-safe; `export const browserApi = createApi(createHttpTransport('/api/store'))`. The browser ALWAYS talks to its own origin `/api/store/...`.

### 4.1 The mock-to-real switch (one env var)
| `API_BASE_URL` | Browser `/api/store/*` is answered by | Server components read from |
|---|---|---|
| empty / unset (default) | `src/app/api/store/[...path]/route.ts` → the mock router (fixtures + in-memory state) | the mock router, in-process |
| `https://api.example.com/v1` | `next.config.ts` **beforeFiles** rewrite `/api/store/:path*` → `${API_BASE_URL}/:path*` (proxied by Next, so cookies are first-party and no CORS is needed) | the real API over HTTP |

`next.config.ts` (SF-09) contains exactly this logic (plus `images.remotePatterns` built from `IMAGE_REMOTE_HOST`, §7):
```ts
async rewrites() {
  const base = process.env.API_BASE_URL;
  return base ? { beforeFiles: [{ source: '/api/store/:path*', destination: `${base.replace(/\/$/, '')}/:path*` }], afterFiles: [], fallback: [] } : [];
}
```
To switch: set `API_BASE_URL` in `frontend/.env.local` and restart `npm run dev` (or rebuild for production; rewrites are fixed at build time). Nothing else changes. `CONTRACT_BASE_URL=https://api.example.com/v1 npm run contract:check` (SF-34) proves the backend matches the contract before switching; without the variable the same command checks the mock.

Backend requirements that follow from the proxy (also written in 03-API-CONTRACT §2): set cookies WITHOUT a `Domain` attribute, `Path=/`, `HttpOnly`, `SameSite=Lax`, `Secure` in production; read the client IP from `X-Forwarded-For`.

### 4.2 The mock backend (`src/mocks/server/`)
- `router.ts` — `handleMockRequest(req: MockRequest): Promise<MockResponse>` where `MockRequest = ApiRequest & { cookies: Record<string,string> }` and `MockResponse = ApiResponse & { setCookies: string[] }`. Matches method + path patterns from 03-API-CONTRACT §5 and dispatches to the handler files. Unknown path → 404 `NOT_FOUND`.
- `db.ts` — in-memory state seeded from fixtures, stored on `globalThis.__aureloMockDb` so it survives hot reload: `products` (with live stock), `carts: Map<cartId, Cart>`, `sessions: Map<token, userId>`, `users`, `orders`, `idempotency: Map<key, response>`. `resetMockDb()` for tests. State is lost on server restart (documented, fine for a mock).
- The route handler converts a `Request` into `MockRequest` (cookies from `request.cookies`), waits `MOCK_LATENCY_MS` (default 250, only in the route handler, never in-process), and returns `Response.json(body, { status, headers })` with every `Set-Cookie`.
- The mock implements the contract EXACTLY, including errors, so the frontend handles every error state before the real backend exists. Responses are validated against the zod schemas in the mock's own tests.

## 5. State
| State | Where | Notes |
|---|---|---|
| Server data (catalog, content) | Server Components (props) | No client cache library |
| URL state (filters, sort, page, q) | URL search params, parsed/serialized by `lib/catalog/query.ts` (pure, tested) | Shareable, back button works |
| Cart | `stores/cart-store.ts` (zustand) | Holds `cart: Cart | null`, `status: 'idle'|'loading'|'ready'|'error'`, `pendingLineIds: string[]`, `drawerOpen`. Actions `hydrate()`, `addItem({ variantId, quantity, name })`, `updateQuantity(lineId, qty)`, `removeLine(lineId)`, `openDrawer()`, `closeDrawer()`, `reset()`. The server cart is the truth: optimistic update for quantity and removal, then replace with the server response; on error roll back to the previous cart and announce the friendly message. `addItem` is NOT optimistic (price/stock come from the server) but the fly-to-cart animation starts immediately. |
| Session | `stores/session-store.ts` (zustand) | `user: Customer | null`, `status: 'unknown'|'guest'|'signed-in'`; `hydrate()` calls `auth.me()` (401 → guest); `signIn`, `register`, `signOut` (sign-out and sign-in both re-hydrate the cart because the server merges/clears it). |
| Theme | next-themes | `class` on `<html>` |
| Checkout form | Local React state in `CheckoutForm` | Validated with `lib/checkout/validation.ts` (zod) on blur and on submit |

Hydration: `CartHydrator` and `SessionHydrator` (client components inside `Providers`) call `hydrate()` once on mount. UI state shared across the shell (search dialog open, mobile nav open) lives in `stores/ui-store.ts`; the announcer message in `stores/announce-store.ts`.

## 6. Errors, loading, empty (applies to every page)
- Every page section that loads has a **skeleton** shaped like the content (`components/ui/Skeleton.tsx`, `bg-surface-2` with Tailwind's `animate-pulse`, only under `motion-safe`).
- Server errors in a route segment are caught by `error.tsx` ("Something went wrong on our side." + "Try again" button calling `reset()` + link home). 404 → `not-found.tsx`.
- Client calls: catch `ApiError`, show `toUserMessage(error)` inline next to the control that failed AND through the announcer; never swallow; in development also `console.error` the `requestId` (no `console.log` in shipped code).
- Empty states are designed (copy in 05-PAGES), never blank.

## 7. Environment variables (`frontend/.env.example`, SF-01)
| Name | Side | Default | Meaning |
|---|---|---|---|
| `API_BASE_URL` | server only | empty | Empty = mock backend. Set to the real API base (e.g. `https://api.example.com/v1`) to switch. |
| `NEXT_PUBLIC_SITE_URL` | both | `http://localhost:3000` | Absolute URL for metadata, Open Graph, sitemap |
| `MOCK_LATENCY_MS` | server only | `250` | Artificial delay of the mock route handler so loading states are visible |
| `IMAGE_REMOTE_HOST` | build | empty | Only needed if the real API returns image URLs on another host (e.g. `cdn.example.com`); `next.config.ts` adds it to `images.remotePatterns` (https only). Mock images are local paths and need nothing. |

The store name, currency, locale, tax rate, shipping methods and free-shipping threshold are NOT env vars: they come from `GET /store` (in mock mode: `src/mocks/fixtures/store.json`). The placeholder brand "Aurelo" is changed there (and later by the backend).

## 8. Quality gates (every card runs all of them, in `ecommerce/frontend/`)
| Gate | Command | Must |
|---|---|---|
| Unit tests | `npm test` (= `vitest run`) | all pass |
| Types | `npm run typecheck` (= `tsc --noEmit`) | 0 errors |
| Lint | `npm run lint` (= `eslint .`) | 0 errors |
| Format | `npm run format:check` (= `prettier --check .`) | clean |
| Build | `npm run build` | succeeds (cards SF-01 onward) |
| Token guard | part of `npm test` (test from SF-02) | no raw colour outside `tokens.css` |
| E2E | `npm run test:e2e` (= `playwright test`) | only from SF-32 on |

## 9. Security and privacy (frontend side)
- Never store tokens in `localStorage`; auth is an HttpOnly cookie the frontend cannot read.
- Never trust client prices: the order total is computed by the server; the client only displays what the API returns.
- Product descriptions are plain-text paragraphs (no HTML from the API, no `dangerouslySetInnerHTML` except the JSON-LD script built with `JSON.stringify`).
- The `next` redirect parameter after sign-in only accepts same-site paths starting with `/` and not `//` (`lib/auth/redirect.ts`, tested).
- No analytics, no third-party scripts.
