# 03 — Storefront API contract v1

Status: v1, written 2026-11-26. **This file is the single source of truth for the JSON the storefront sends and receives.** The frontend's zod schemas (`frontend/src/lib/api/schemas.ts`), the mock backend (`frontend/src/mocks/server/`) and the real backend (built later by the backend developer) all implement exactly this. A change to a shape is a contract change: bump the version line above, add a row to §10 (changelog), update the schemas and the mock in the same commit.

For the backend developer: implement these endpoints with these exact JSON shapes and status codes, then run `CONTRACT_BASE_URL=<your base URL> npm run contract:check` in `frontend/` (card SF-34). When it is green, the storefront switches to your API by setting one env var (`API_BASE_URL`).

## 1. Conventions
| Topic | Rule |
|---|---|
| Base URL | `{BASE}`, for example `https://api.example.com/v1`. All paths below are relative to it. |
| Format | JSON, UTF-8. Request bodies only on POST/PATCH, with `Content-Type: application/json`. Responses always `Content-Type: application/json` except `204`. |
| Keys | `camelCase`. No `null` for arrays (use `[]`). Optional values are present with `null`, never omitted, unless marked "optional (may be omitted)". |
| IDs | Opaque strings. The mock uses prefixes (`prod_`, `var_`, `cat_`, `cart_`, `line_`, `cus_`, `ord_`) but the frontend must not parse them. |
| Slugs | `^[a-z0-9]+(?:-[a-z0-9]+)*$`, unique per type, used in URLs. |
| Dates | ISO 8601 strings in UTC with `Z`, e.g. `"2026-11-26T08:15:00Z"`. |
| Money | Always the object `Money` (§4.1): integer `amount` in **minor units** (paisa for BDT; ৳1,450 is `145000`) and ISO 4217 `currency`. Never floats, never formatted strings. |
| Request ID | Every response carries header `X-Request-Id`; error bodies repeat it as `requestId`. |
| Auth | Session cookie, see §2. |
| Pagination | Page-based, see §6. |
| Versioning | Breaking changes go to `/v2`. Adding a new optional response field is not breaking; the frontend ignores unknown fields (zod `.passthrough()` is NOT used; unknown keys are stripped). |

## 2. Session, cart identity and security
- **The browser never talks to the backend directly.** It calls the storefront's own origin `/api/store/*`, which Next.js proxies to `{BASE}/*` (02-ARCHITECTURE §4.1). Cookies are therefore first-party for the storefront domain and no CORS setup is needed.
- **Session cookie:** set by `POST /auth/sign-in` and `POST /auth/register`, cleared by `POST /auth/sign-out`. Name is the backend's choice (the frontend never reads it). Attributes: `HttpOnly; Path=/; SameSite=Lax; Secure` (Secure in production), lifetime 30 days sliding. **No `Domain` attribute** (it must stay host-only on the storefront domain behind the proxy).
- **Cart cookie:** set by the first `POST /cart/items` for a visitor without a cart. Same attributes, lifetime 30 days. A signed-in customer's cart is tied to the customer; the cart cookie may still exist.
- **Cart merge on sign-in/register:** if the visitor had a guest cart, its lines are merged into the customer's cart (same variant → quantities added, capped at `maxQuantity`); the guest cart is then discarded.
- **Sign-out:** clears the session cookie AND the cart cookie (the next visitor on that device starts with an empty guest cart).
- **CSRF:** a request that carries a body is accepted only with `Content-Type: application/json` (others → `415 UNSUPPORTED_MEDIA_TYPE`); body-less mutations (`POST /auth/sign-out`, `DELETE …`) need no content type. Protection relies on `SameSite=Lax` and the same-origin proxy.
- **Rate limits (production backend):** `POST /auth/sign-in`: after 5 failed attempts for one email within 60 s, every further attempt for that email in that window gets `429 RATE_LIMITED` with header `Retry-After: <seconds>` (attempts 1–5 get 401, the 6th gets 429). The mock implements this exact rule.
- **Never trust client prices:** the server computes every total. The client sends `expectedTotal` at checkout only to detect a price change (§5.5).
- The client IP arrives in `X-Forwarded-For` (set by the proxy).

## 3. Errors
Every non-2xx response (except `204`) has this body:
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Some fields are not valid.",
    "fields": { "email": ["Enter a valid email address."] },
    "details": null,
    "requestId": "req_7f3a2c"
  }
}
```
`fields` is `null` or an object of field path → list of human messages (field paths use dots: `shippingAddress.postalCode`). `details` is `null` or an object whose shape is fixed per code (below). `message` is safe to show but the frontend prefers its own text per code (column "Frontend shows").

| HTTP | `code` | When | `details` | Frontend shows (from `toUserMessage`) |
|---|---|---|---|---|
| 400 | `VALIDATION_FAILED` | Body or query invalid | `null` | Field messages next to fields; summary "Please check the highlighted fields." |
| 400 | `IDEMPOTENCY_KEY_REQUIRED` | `POST /checkout` without header | `null` | "Something went wrong. Please try again." |
| 401 | `UNAUTHENTICATED` | Endpoint needs a session | `null` | Redirect to sign-in (account pages); "Please sign in." elsewhere |
| 401 | `INVALID_CREDENTIALS` | Wrong email or password | `null` | "That email and password don't match." |
| 404 | `NOT_FOUND` | Unknown resource or route | `null` | Page 404 or "This item is no longer available." |
| 404 | `VARIANT_NOT_FOUND` | `variantId` unknown | `null` | "This option is no longer available." |
| 404 | `LINE_NOT_FOUND` | Cart line id not in this cart | `null` | Re-hydrate cart silently; "Your cart was updated." |
| 409 | `EMAIL_TAKEN` | Register with existing email | `null` | Field error on email: "An account with this email already exists." + link "Sign in instead" |
| 409 | `OUT_OF_STOCK` | Variant has 0 available (cart add) or a checkout line is no longer available | `{ "lines": [{ "lineId": "line_…", "variantId": "var_…", "available": 0 }] }` (for cart add: one entry with `lineId: null`) | "Sorry, this is sold out." / at checkout the line is marked and the cart refreshed |
| 409 | `INSUFFICIENT_STOCK` | Requested quantity > available | `{ "variantId": "var_…", "available": 3 }` | "Only 3 left — we've updated the quantity." (then the UI sets quantity to `available`) |
| 409 | `CART_EMPTY` | Checkout or quote with an empty cart | `null` | Redirect to `/cart` |
| 409 | `PRICE_CHANGED` | `expectedTotal` ≠ server total at checkout | `{ "quote": Quote }` | "Prices changed since you started checkout. Please review the new total." (summary re-renders with `details.quote`) |
| 409 | `IDEMPOTENCY_CONFLICT` | Same `Idempotency-Key`, different body | `null` | "Something went wrong. Please try again." (client makes a new key) |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Request with a body but without JSON content type | `null` | "Something went wrong. Please try again." |
| 422 | `SHIPPING_METHOD_UNAVAILABLE` | Unknown or disabled shipping method | `null` | "Please choose another delivery option." |
| 422 | `PAYMENT_METHOD_UNAVAILABLE` | Unknown or disabled payment method | `null` | "Please choose another payment method." |
| 429 | `RATE_LIMITED` | Too many attempts | `{ "retryAfterSeconds": 60 }` | "Too many attempts. Try again in 60 seconds." |
| 500 | `INTERNAL` | Anything unexpected | `null` | "Something went wrong on our side. Please try again." |
| 503 | `UNAVAILABLE` | Maintenance | `null` | "The shop is taking a short break. Please try again soon." |
| — | `NETWORK_ERROR` | Client-only: fetch failed (status 0) | `null` | "You seem to be offline. Check your connection and try again." |
| — | `CONTRACT_MISMATCH` | Client-only: a 2xx body did not match the schema (status 502) | `null` | "Something went wrong on our side. Please try again." |
| — | `UNKNOWN` | Client-only: error body not in this format | `null` | "Something went wrong. Please try again." |

## 4. Objects (field: type — rules). Every object below has a zod schema of the same name + `Schema` in `schemas.ts`.

### 4.1 `Money`
`amount`: integer ≥ 0 (minor units) · `currency`: string, 3 upper-case letters. Example `{ "amount": 145000, "currency": "BDT" }`.

### 4.2 `Image`
`url`: string (absolute URL or a path starting with `/`) · `alt`: string (may be `""` for decorative) · `width`: integer > 0 · `height`: integer > 0.

### 4.3 `StoreConfig` (`GET /store`)
```json
{
  "name": "Aurelo",
  "tagline": "Objects for slow living",
  "currency": "BDT",
  "locale": "en-BD",
  "supportEmail": "help@aurelo.test",
  "taxRateBps": 500,
  "taxLabel": "VAT",
  "maxQuantityPerLine": 10,
  "freeShippingThreshold": { "amount": 500000, "currency": "BDT" },
  "shippingMethods": [
    { "id": "standard", "label": "Standard delivery", "description": "3–5 working days", "price": { "amount": 8000, "currency": "BDT" }, "freeOverThreshold": true, "estimatedDays": { "min": 3, "max": 5 } },
    { "id": "express", "label": "Express delivery", "description": "1–2 working days", "price": { "amount": 15000, "currency": "BDT" }, "freeOverThreshold": false, "estimatedDays": { "min": 1, "max": 2 } }
  ],
  "paymentMethods": [
    { "id": "cod", "label": "Cash on delivery", "description": "Pay when your order arrives.", "enabled": true },
    { "id": "card", "label": "Card payment", "description": "Coming soon.", "enabled": false }
  ],
  "countries": [{ "code": "BD", "name": "Bangladesh" }]
}
```
Rules: `taxRateBps` integer 0–10000 (500 = 5 %), tax is added on top of subtotal + shipping; `freeShippingThreshold` is `null` when there is none; a method with `freeOverThreshold: true` costs 0 when the cart subtotal ≥ threshold.

### 4.4 `Category`
`id` · `slug` · `name` · `description`: string · `image`: `Image | null` · `productCount`: integer ≥ 0.

### 4.5 `OptionValue`, `ProductOption`
`OptionValue`: `label`: string · `swatch`: string `#RRGGBB` or `null` (only colours have swatches).
`ProductOption`: `name`: string (e.g. `"Color"`, `"Size"`, `"Scent"`) · `values`: `OptionValue[]` (≥ 1).

### 4.6 `StockStatus`
`"in_stock" | "low_stock" | "out_of_stock"`. Rule (server side): available 0 → `out_of_stock`; 1–5 → `low_stock`; > 5 → `in_stock`. A product's aggregate status: `in_stock` if any variant is `in_stock`, else `low_stock` if any is `low_stock`, else `out_of_stock`.

### 4.7 `Variant`
`id` · `sku` · `title`: string (option values joined by `" / "`, e.g. `"Oat / Double"`) · `options`: object option name → value label (e.g. `{ "Color": "Oat", "Size": "Double" }`, one key per product option) · `price`: Money · `compareAtPrice`: `Money | null` (set ⇒ shown struck through; must be > price) · `stockStatus`: StockStatus · `availableQuantity`: integer ≥ 0 (the backend may cap it at 99).

### 4.8 `ProductSummary` (cards, lists)
```json
{
  "id": "prod_001",
  "slug": "ondo-stoneware-mug",
  "name": "Ondo Stoneware Mug",
  "subtitle": "Hand-thrown, 350 ml",
  "category": { "slug": "ceramics", "name": "Ceramics" },
  "price": { "amount": 145000, "currency": "BDT" },
  "compareAtPrice": null,
  "images": [
    { "url": "/mock/products/ondo-stoneware-mug-1.jpg", "alt": "Ondo Stoneware Mug in Sand, front view", "width": 1600, "height": 2000 },
    { "url": "/mock/products/ondo-stoneware-mug-2.jpg", "alt": "Ondo Stoneware Mug, close-up detail", "width": 1600, "height": 2000 }
  ],
  "badges": ["bestseller"],
  "stockStatus": "in_stock",
  "swatches": [ { "label": "Sand", "swatch": "#D8C8B0" }, { "label": "Ink", "swatch": "#2B2F36" }, { "label": "Moss", "swatch": "#6B7A55" } ]
}
```
Rules: `price` = lowest variant price; `compareAtPrice` = that variant's compare-at price or `null`; `images` = the first two product images (one is allowed); `badges` ⊆ `["new","sale","bestseller"]`, in that order; `swatches` = values of the `Color` option or `[]`.

### 4.9 `Product` (`GET /products/{slug}`) = all `ProductSummary` fields, with `images` holding ALL images, plus:
`description`: `string[]` (plain-text paragraphs, no HTML) · `details`: `{ "label": string, "value": string }[]` (e.g. Material, Dimensions, Care) · `options`: `ProductOption[]` (may be `[]` for a single-variant product) · `variants`: `Variant[]` (≥ 1) · `defaultVariantId`: string (first available variant, else the first variant) · `createdAt`: date string.

### 4.10 `Facets`
```json
{
  "categories": [{ "slug": "ceramics", "name": "Ceramics", "count": 5 }],
  "colors": [{ "label": "Sand", "swatch": "#D8C8B0", "count": 3 }],
  "sizes": [{ "label": "Double", "count": 1 }],
  "price": { "min": { "amount": 95000, "currency": "BDT" }, "max": { "amount": 2190000, "currency": "BDT" } }
}
```
Counts are computed over the result set with all filters EXCEPT the facet's own (so a user can widen a choice). `price.min/max` cover the result set ignoring the price filter. Empty result → arrays `[]`, `price` = `null`.

### 4.11 `Cart`
```json
{
  "id": "cart_9d2e",
  "lines": [
    {
      "id": "line_01",
      "variantId": "var_ondo-stoneware-mug_sand",
      "productSlug": "ondo-stoneware-mug",
      "productName": "Ondo Stoneware Mug",
      "variantTitle": "Sand",
      "image": { "url": "/mock/products/ondo-stoneware-mug-1.jpg", "alt": "Ondo Stoneware Mug in Sand, front view", "width": 1600, "height": 2000 },
      "unitPrice": { "amount": 145000, "currency": "BDT" },
      "compareAtUnitPrice": null,
      "quantity": 2,
      "lineTotal": { "amount": 290000, "currency": "BDT" },
      "maxQuantity": 10,
      "stockStatus": "in_stock"
    }
  ],
  "itemCount": 2,
  "subtotal": { "amount": 290000, "currency": "BDT" },
  "freeShippingRemaining": { "amount": 210000, "currency": "BDT" },
  "updatedAt": "2026-11-26T08:15:00Z"
}
```
Rules: no cart yet ⇒ `id: null, lines: [], itemCount: 0, subtotal: { "amount": 0, "currency": <StoreConfig.currency> }`, `freeShippingRemaining` = the full threshold, `updatedAt: null`. `itemCount` = sum of quantities. `maxQuantity` = min(`availableQuantity`, `maxQuantityPerLine`). `freeShippingRemaining` = `null` if the store has no threshold, else max(0, threshold − subtotal). Lines keep insertion order.

### 4.12 `Customer`
`id` · `email` · `firstName` · `lastName` · `createdAt`. (Never a password hash, never internal flags.)

### 4.13 `Address`
`firstName`: 1–60 chars · `lastName`: 1–60 · `line1`: 3–120 · `line2`: string ≤ 120 or `null` · `city`: 2–60 · `postalCode`: `^[A-Za-z0-9 -]{3,10}$` · `countryCode`: one of `StoreConfig.countries[].code`.

### 4.14 `Quote`
`subtotal`, `shipping`, `tax`, `total`: Money · `shippingMethodId`: string · `freeShippingApplied`: boolean · `taxRateBps`: integer · `itemCount`: integer.
Computation (server): `shipping` = method price, or 0 when `freeOverThreshold` and subtotal ≥ threshold; `tax` = round_half_up((subtotal + shipping) × taxRateBps / 10000); `total` = subtotal + shipping + tax.

### 4.15 `OrderLine`, `Order`, `OrderSummary`
`OrderLine`: `id` · `productSlug` · `productName` · `variantTitle` · `sku` · `image`: `Image | null` · `unitPrice`: Money · `quantity`: integer ≥ 1 · `lineTotal`: Money.
`Order`:
```json
{
  "id": "ord_0200",
  "number": "AUR-100200",
  "status": "placed",
  "paymentStatus": "pending",
  "placedAt": "2026-11-26T08:20:00Z",
  "email": "nadia@example.com",
  "phone": "+8801712345678",
  "shippingAddress": { "firstName": "Nadia", "lastName": "Rahman", "line1": "House 12, Road 5", "line2": null, "city": "Dhaka", "postalCode": "1209", "countryCode": "BD" },
  "shippingMethod": { "id": "standard", "label": "Standard delivery", "price": { "amount": 8000, "currency": "BDT" } },
  "paymentMethod": { "id": "cod", "label": "Cash on delivery" },
  "lines": [ { "id": "oline_1", "productSlug": "ondo-stoneware-mug", "productName": "Ondo Stoneware Mug", "variantTitle": "Sand", "sku": "AUR-001-SAN", "image": null, "unitPrice": { "amount": 145000, "currency": "BDT" }, "quantity": 2, "lineTotal": { "amount": 290000, "currency": "BDT" } } ],
  "subtotal": { "amount": 290000, "currency": "BDT" },
  "shipping": { "amount": 8000, "currency": "BDT" },
  "tax": { "amount": 14900, "currency": "BDT" },
  "total": { "amount": 312900, "currency": "BDT" },
  "note": null
}
```
`status`: `"placed" | "processing" | "shipped" | "delivered" | "cancelled"`. `paymentStatus`: `"pending" | "paid" | "refunded"`. `shippingMethod.price` is what was charged (0 when free).
`OrderSummary`: `number` · `status` · `placedAt` · `itemCount` · `total`: Money · `previewImages`: `Image[]` (≤ 3, first lines' images).

### 4.16 `HomeContent` (`GET /content/home`)
```json
{
  "hero": { "eyebrow": "Autumn edit 2026", "headline": "Made slowly. Kept for years.", "subheadline": "Ceramics, linen and light from small workshops, chosen to be used every day.", "image": { "url": "/mock/editorial/hero.jpg", "alt": "Stoneware mugs and a linen throw on an oak table in morning light", "width": 2400, "height": 1600 }, "cta": { "label": "Shop the collection", "href": "/shop" } },
  "featuredCategorySlugs": ["ceramics", "linen", "lighting", "bags"],
  "editorial": { "eyebrow": "From the workshop", "headline": "Every Ondo mug starts as 400 grams of clay", "body": ["Each piece is thrown, trimmed and glazed by hand, so no two are quite the same.", "Small differences in colour and form are part of the object, not a flaw."], "image": { "url": "/mock/editorial/workshop.jpg", "alt": "Hands shaping a mug on a potter's wheel", "width": 1600, "height": 2000 }, "cta": { "label": "Shop ceramics", "href": "/shop?category=ceramics" } },
  "values": [
    { "icon": "truck", "title": "Delivery across Bangladesh", "body": "Standard in 3–5 days, express in 1–2." },
    { "icon": "leaf", "title": "Made by small workshops", "body": "Natural materials, made in small batches." },
    { "icon": "refresh", "title": "Easy returns", "body": "Changed your mind? Return unused items within 14 days." },
    { "icon": "shield", "title": "Cash on delivery", "body": "Pay when your order arrives." }
  ]
}
```
`icon` ∈ `"truck" | "leaf" | "refresh" | "shield"` (the frontend maps them to lucide icons `Truck`, `Leaf`, `RefreshCw`, `ShieldCheck`). `cta.href` is a site-relative path.

### 4.17 `Paginated<T>`
`items`: `T[]` · `page`: integer ≥ 1 · `pageSize`: integer · `totalItems`: integer ≥ 0 · `totalPages`: integer ≥ 0 (= ceil(totalItems / pageSize)).

## 5. Endpoints
Legend: 🔓 public · 🍪 uses cart cookie · 🔐 needs session.

### 5.1 Store and content
| Method & path | Auth | Request | 200 response | Errors |
|---|---|---|---|---|
| `GET /store` | 🔓 | — | `StoreConfig` | 500 |
| `GET /content/home` | 🔓 | — | `HomeContent` | 500 |
| `POST /newsletter` | 🔓 | `{ "email": "a@b.co" }` | **202** `{ "status": "subscribed" }` (idempotent: same email again → same 202) | 400 `VALIDATION_FAILED` |

### 5.2 Catalog
| Method & path | Auth | Request | 200 response | Errors |
|---|---|---|---|---|
| `GET /categories` | 🔓 | — | `{ "items": Category[] }` (fixed order) | 500 |
| `GET /products` | 🔓 | query, see below | `Paginated<ProductSummary> & { "facets": Facets }` | 400 `VALIDATION_FAILED` |
| `GET /products/{slug}` | 🔓 | — | `Product` | 404 `NOT_FOUND` |
| `GET /products/{slug}/related?limit=4` | 🔓 | `limit` 1–12, default 4 | `{ "items": ProductSummary[] }` (same category first, then others; never the product itself; out-of-stock last) | 404 `NOT_FOUND` |
| `GET /search/suggest?q=` | 🔓 | `q` string | `{ "query": "mu", "products": [{ "slug", "name", "image": Image|null, "price": Money }], "categories": [{ "slug", "name" }] }` — max 5 products, 3 categories; `q` trimmed shorter than 2 chars → both arrays `[]` | — |

`GET /products` query parameters (all optional; unknown params ignored; invalid values → 400 with `fields`):
| Param | Type | Meaning |
|---|---|---|
| `q` | string ≤ 100 | Case-insensitive match on name, subtitle, category name, description, option values |
| `category` | slug | Only this category |
| `collection` | `featured` \| `new` \| `sale` | featured = badge `bestseller` or `new`; new = badge `new`; sale = `compareAtPrice` not null |
| `color` | repeatable string | Product has a `Color` option value with this label (OR between values) |
| `size` | repeatable string | Product has a `Size` option value with this label (OR) |
| `minPrice`, `maxPrice` | integer minor units | Filter on `ProductSummary.price.amount` (inclusive) |
| `inStock` | `true` | Only products whose aggregate status is not `out_of_stock` |
| `sort` | `featured` (default) \| `newest` \| `price-asc` \| `price-desc` \| `name-asc` | featured = the store's curated order (the fixture file order); ties by name |
| `page` | integer ≥ 1, default 1 | Page beyond the last → 200 with `items: []` |
| `pageSize` | integer 1–48, default 24 | |
Repeatable params are sent as repeated keys: `?color=Sand&color=Ink`.

### 5.3 Cart (🍪)
| Method & path | Request body | 200 response | Errors |
|---|---|---|---|
| `GET /cart` | — | `Cart` (empty cart object when there is none; never 404) | — |
| `POST /cart/items` | `{ "variantId": "var_…", "quantity": 1 }` (quantity integer 1–`maxQuantityPerLine`) | `Cart` (creates the cart and sets the cart cookie if needed; same variant already in cart ⇒ quantities add) | 400 `VALIDATION_FAILED`; 404 `VARIANT_NOT_FOUND`; 409 `OUT_OF_STOCK`; 409 `INSUFFICIENT_STOCK` (resulting line quantity would exceed available; nothing is changed) |
| `PATCH /cart/items/{lineId}` | `{ "quantity": 3 }` (integer ≥ 1; to remove use DELETE) | `Cart` | 400; 404 `LINE_NOT_FOUND`; 409 `INSUFFICIENT_STOCK` (nothing changed) |
| `DELETE /cart/items/{lineId}` | — | `Cart` | 404 `LINE_NOT_FOUND` |
Stock is NOT reserved by the cart; it is checked again at checkout.

### 5.4 Auth
| Method & path | Auth | Request body | Success | Errors |
|---|---|---|---|---|
| `POST /auth/register` | 🔓 | `{ "firstName": "Nadia", "lastName": "Rahman", "email": "nadia@example.com", "password": "at-least-8-chars" }` | **201** `{ "customer": Customer }` + session cookie; guest cart merged | 400 (`firstName`/`lastName` 1–60, `email` valid ≤ 254, lower-cased by server, `password` 8–128); 409 `EMAIL_TAKEN` |
| `POST /auth/sign-in` | 🔓 | `{ "email": "…", "password": "…" }` | 200 `{ "customer": Customer }` + session cookie; guest cart merged | 400; 401 `INVALID_CREDENTIALS`; 429 `RATE_LIMITED` |
| `POST /auth/sign-out` | 🔐 (no session → still 204) | — | **204**, clears session + cart cookies | — |
| `GET /auth/me` | 🔐 | — | 200 `{ "customer": Customer }` | 401 `UNAUTHENTICATED` |

### 5.5 Checkout (🍪, works for guests and signed-in customers)
| Method & path | Request | Success | Errors |
|---|---|---|---|
| `GET /checkout/quote?shippingMethodId=standard` | query `shippingMethodId` | 200 `Quote` for the current cart | 409 `CART_EMPTY`; 422 `SHIPPING_METHOD_UNAVAILABLE` |
| `POST /checkout` | header `Idempotency-Key: <uuid v4>` (required); body below | **201** `{ "order": Order, "confirmationToken": "tok_…" }`; stock decremented; cart emptied (cart cookie cleared) | 400 `VALIDATION_FAILED` / `IDEMPOTENCY_KEY_REQUIRED`; 409 `CART_EMPTY`, `OUT_OF_STOCK`, `PRICE_CHANGED`, `IDEMPOTENCY_CONFLICT`; 422 `SHIPPING_METHOD_UNAVAILABLE`, `PAYMENT_METHOD_UNAVAILABLE` |

`POST /checkout` body:
```json
{
  "email": "nadia@example.com",
  "phone": "+8801712345678",
  "shippingAddress": { "firstName": "Nadia", "lastName": "Rahman", "line1": "House 12, Road 5", "line2": null, "city": "Dhaka", "postalCode": "1209", "countryCode": "BD" },
  "shippingMethodId": "standard",
  "paymentMethodId": "cod",
  "note": null,
  "expectedTotal": { "amount": 312900, "currency": "BDT" }
}
```
Rules: `email` valid (for a signed-in customer it may differ from the account email; the order is still linked to the customer); `phone` matches `^\+?[0-9 ()-]{7,20}$`; `note` `null` or ≤ 500 chars; `expectedTotal` must equal the server's `Quote.total` for this cart and method, else 409 `PRICE_CHANGED` with `details.quote`. Idempotency: the same key with the same body within 24 h returns the SAME 201 response again (no second order); the same key with a different body → 409 `IDEMPOTENCY_CONFLICT`. The client generates one key per checkout attempt (a new one only after a 4xx that it fixes, or after `IDEMPOTENCY_CONFLICT`).

### 5.6 Orders
| Method & path | Auth | Request | 200 response | Errors |
|---|---|---|---|---|
| `GET /orders?page=1&pageSize=10` | 🔐 | `pageSize` 1–50, default 10 | `Paginated<OrderSummary>`, newest first | 401 `UNAUTHENTICATED` |
| `GET /orders/{number}` | 🔐 owner, or 🔓 with `?token=<confirmationToken>` | — | `Order` | 404 `NOT_FOUND` (also when the order exists but belongs to someone else or the token is wrong: never reveal existence) |

## 6. Pagination
Page-based (`page`, `pageSize`) because the catalog shows numbered pages and the result counts. Responses are `Paginated<T>` (§4.17). The frontend never assumes a page size; it reads `pageSize` from the response.

## 7. Flows
### 7.1 Browse → cart
1. Server renders `/shop` with `GET /products?...` (no cookies needed).
2. Visitor picks a variant on `/products/{slug}`, presses "Add to cart" → browser `POST /cart/items` → cart cookie set on first add → response `Cart` replaces the client cart; the drawer opens.
3. Quantity change → `PATCH /cart/items/{lineId}`; remove → `DELETE …`. On `409 INSUFFICIENT_STOCK` the client sets the quantity to `details.available` with one more PATCH (or DELETE when 0) and says so.

### 7.2 Sign-in with a guest cart
`POST /auth/sign-in` → server merges carts → client calls `GET /cart` and `GET /auth/me` again (the session store does this) → header count updates.

### 7.3 Checkout
1. `/checkout` loads `GET /store` (methods) and `GET /cart`; empty cart → redirect `/cart`.
2. On load and on every shipping-method change: `GET /checkout/quote?shippingMethodId=…` → the summary shows `Quote` (never a client-computed total).
3. Submit → client validates → `POST /checkout` with a new `Idempotency-Key` and `expectedTotal = quote.total`.
4. 201 → client clears its cart state, stores nothing sensitive, navigates to `/order-confirmation/{order.number}?token={confirmationToken}` → that page calls `GET /orders/{number}?token=…`.
5. 409 `PRICE_CHANGED` → show `details.quote`, user confirms again (same key is NOT reused: body changed → new key). 409 `OUT_OF_STOCK` → refresh cart, mark lines, user adjusts. Network error → retry with the SAME key (safe thanks to idempotency).

### 7.4 Account
`/account` → `GET /auth/me` (401 → redirect `/account/sign-in?next=/account`) → `GET /orders?page=1` → `/account/orders/{number}` → `GET /orders/{number}`.

## 8. Mock behaviour that is NOT part of the contract (frontend-only conveniences)
- The mock keeps state in memory; restarting `npm run dev` resets carts, sessions, new orders and stock.
- Demo account in the mock: `demo@aurelo.test` / `demo-pass-123` (a test credential, not a real account) with three past orders.
- `MOCK_LATENCY_MS` delays mock responses for the browser.

## 9. Checklist for the backend developer
- [ ] All endpoints of §5 with exact paths, methods and status codes.
- [ ] Every 2xx body validates against `frontend/src/lib/api/schemas.ts` (run `CONTRACT_BASE_URL=… npm run contract:check`).
- [ ] Every error uses the §3 envelope and codes.
- [ ] Cookies: HttpOnly, SameSite=Lax, Secure, no Domain attribute.
- [ ] Money in minor units; totals computed server-side as in §4.14.
- [ ] Idempotency on `POST /checkout` as in §5.5.
- [ ] Rate limit on sign-in as in §2.
- [ ] `X-Request-Id` on every response.

## 10. Changelog
| Version | Date | Change |
|---|---|---|
| v1 | 2026-11-26 | First version |
