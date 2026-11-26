# 05 — Sitemap and page specifications

Status: plan, written 2026-11-26. Copy in quotes is exact (cards and tests use it). Data names refer to 03-API-CONTRACT. Motion ids W1–W10 refer to 01-VISION-DESIGN §5.

## 0. Sitemap
```
/                                   Home
/shop                               Catalog (all products; ?q ?category ?collection ?color ?size ?minPrice ?maxPrice ?inStock ?sort ?page)
/products/[slug]                    Product detail
/cart                               Cart page (the drawer is available everywhere)
/checkout                           Checkout (guest or signed-in)
/order-confirmation/[orderNumber]   Confirmation (?token=…)
/account                            Account: profile + order history (signed-in only)
/account/orders/[orderNumber]       Order detail (signed-in only)
/account/sign-in                    Sign in (?next=/path)
/account/register                   Create account (?next=/path)
(not-found)                         404
(error)                             500 boundary
/sitemap.xml  /robots.txt           SEO (SF-31)
```
Every page except checkout uses the store shell (Header + Footer). `/checkout` uses a reduced header: logo (link home) + "Secure checkout" label + link "Back to cart"; no nav, no footer links except the support email.

Page titles (`metadata.title`): template `"%s — Aurelo"` where "Aurelo" is `StoreConfig.name` (read via `serverApi.store.get()` in `generateMetadata` of the root layout). Home title: `"Aurelo — Objects for slow living"` (name — tagline).

## 1. Shell (SF-11, SF-12, SF-13, SF-14)
### Header (sticky, `z-header`, height 64 px mobile / 72 px desktop)
- Left: logo = store name in `font-display text-title`, link `/`, `aria-label="<name> home"`.
- Center (≥ 1024 px): nav links "Shop all" (`/shop`) and one link per category from `GET /categories` (`/shop?category=<slug>`). Active link has an accent underline (2 px, drawn with `scaleX` 0 → 1, `duration.fast`).
- Right: search button (lucide `Search`, `aria-label="Search"`, shortcut hint `⌘K`/`Ctrl K` shown ≥ 1024 px), theme toggle (`aria-label="Switch to dark theme"` / `"Switch to light theme"`), account link (`User` icon, `aria-label="Account"` → `/account` when signed in, else `/account/sign-in`), cart button (`ShoppingBag` icon, `aria-label="Cart, 2 items"`, count badge with RollingNumber, opens the drawer; `id="header-cart-button"` is the fly-to-cart target).
- < 1024 px: a menu button (`Menu` icon, `aria-label="Open menu"`) opens `MobileNav` (Radix Dialog from the left, full height, same links + "Account" + "Theme").
- Background is always solid `bg-bg` (no transparency, no blur). After 24 px of scroll a bottom hairline `border-border` appears (class toggle `data-scrolled="true"`, transition `border-color duration.fast`).
### Footer
Four columns (stack on mobile): brand (name + tagline), "Shop" (categories), "Help" ("Delivery", "Returns", "Contact" → `mailto:<supportEmail>`; Delivery/Returns link to `/shop` for now with a `title` "Policy pages are coming soon" — NOT a fake page), newsletter form (SF-17). Bottom row: "© 2026 Aurelo" (name from StoreConfig) and the theme toggle.
### Skip link, announcer, page transition
- "Skip to content" link, visually hidden until focused, target `#main`.
- `Announcer`: one visually hidden `<div aria-live="polite" aria-atomic="true">`; `announce(message)` from `stores` or a tiny context.
- `app/(store)/template.tsx`: wraps children in `motion.div` initial `{opacity:0, y:12}` → animate `{opacity:1, y:0}`, `duration.base`, `ease.out` (W8). Reduced motion: no transform, opacity only from 0.98 (effectively instant).
### Cart drawer (SF-13)
- Radix Dialog, right side, classes `w-full sm:max-w-md` (full width on phones, 28 rem from 640 px), `bg-surface`, `shadow-float`, `rounded-l-lg` (none on mobile). Title "Your cart (2)". Close button `aria-label="Close cart"`.
- Body: `FreeShippingMeter` ("You're ৳2,100 away from free delivery." with a progress bar `role="progressbar"` `aria-valuenow`; when reached: "You've unlocked free standard delivery."; hidden when `freeShippingRemaining` is null), then `CartLine` list.
- `CartLine`: image 80 × 100, name (link to PDP), variant title, unit price (with struck compare-at), `QuantityStepper` (− / number / +, `aria-label="Decrease quantity"`, `"Increase quantity"`, input `aria-label="Quantity for <name>"`; + disabled at `maxQuantity` with the hint "Max <n>"), remove button (`aria-label="Remove <name>"`), line total. Low stock line: Badge "Only <available> left" — the API gives `stockStatus` only, so the copy is "Low stock" (no number). Pending line: opacity 60 % + `aria-busy`.
- Footer: subtotal (RollingNumber tween), note "Delivery and VAT are calculated at checkout.", primary button "Checkout" → `/checkout`, secondary link "View cart" → `/cart`.
- Empty: illustration-free; text "Your cart is empty." + button "Start shopping" → `/shop`.
- Error (hydrate failed): "We couldn't load your cart." + button "Try again".
- Motion W7: open spring.snappy x 100 % → 0; scrim opacity 0 → 1 `duration.base`; line remove `AnimatePresence` + `layout` (height collapse via layout, not height animation); subtotal tween with RollingNumber.
### Search dialog (SF-14)
- Opens from the header button or ⌘K / Ctrl+K anywhere, `/` when focus is not in an input. Radix Dialog near the top of the screen (`pt-24` on the overlay container; no arbitrary values), classes `w-full max-w-2xl`.
- Input with label "Search products" (visually hidden), placeholder "Search mugs, linen, lamps…". Debounce 200 ms; min 2 characters; calls `browserApi.catalog.suggest(q)`.
- Results: ARIA combobox pattern (`role="combobox"` on the input, `role="listbox"` results, `aria-activedescendant`); arrow keys move, Enter opens the product, Esc closes. Sections "Products" (image 40 × 50, name, price) and "Categories". Footer row: "See all results for “<q>”" → `/shop?q=<q>`.
- States: idle (q < 2) → "Popular: Mugs · Linen · Lamps" chips (links to `/shop?q=mug` etc.); loading → 3 skeleton rows; no results → "Nothing found for “<q>”. Try a shorter word."; error → "Search is unavailable right now."

## 2. Home `/` (SF-16, SF-17)
| # | Section | Content | States | Motion |
|---|---|---|---|---|
| 1 | Hero | `HomeContent.hero`: full-width image (next/image `priority`, `sizes="100vw"`, classes `w-full aspect-4/5 md:aspect-video max-h-224 object-cover`, rounded-lg inset by the container on ≥ 768 px, full-bleed on mobile); text block bottom-left on a `bg-bg` panel (no gradient overlay): eyebrow (`text-label text-fg-muted`), headline `h1 text-display-xl font-display`, subheadline `text-body-lg`, CTA Button (primary, size lg) | Server-rendered; if the content call fails the page error boundary shows | W1 (SplitText lines, mask reveal, image scale) |
| 2 | Shop by category | Heading "Shop by category"; 4 tiles from `featuredCategorySlugs` matched to `/categories` (unknown slugs skipped); tile = category image (aspect 4/5), name, "<productCount> pieces"; link `/shop?category=<slug>`; grid 2 cols mobile, 4 cols ≥ 1024 | — | W2; tiles reveal with stagger on scroll (ScrollTrigger `start: "top 80%"`, once) |
| 3 | Featured | Heading "Most loved" + link "Shop all" → `/shop?collection=featured`; `ProductCard`s from `listProducts({collection:'featured', pageSize: 8})` | 0 items → section not rendered | W3 pinned horizontal rail ≥ 1024 px; native scroll-snap below; reduced motion → native scroll everywhere |
| 4 | Editorial band | `HomeContent.editorial`: image left (aspect 4/5), text right on ≥ 1024 px, stacked on mobile; eyebrow, `h2 text-display-lg`, paragraphs, CTA link with arrow | — | Image clip-path reveal `inset(10% 10% 10% 10%)` → `inset(0)` scrubbed with scroll; text Reveal |
| 5 | New in | Heading "New in"; 4 `ProductCard`s from `listProducts({collection:'new', pageSize: 4})`, grid | 0 → not rendered | Reveal stagger |
| 6 | Values strip | `HomeContent.values`: 4 items, icon + title + body, 2×2 mobile, 4 cols desktop, top and bottom hairlines | — | none (calm) |
| 7 | Newsletter | Heading "Letters from the workshop", body "One email a month. New pieces and the stories behind them.", email input (label "Email address"), button "Subscribe"; `POST /newsletter`; success: "Thanks — you're on the list." (`role="status"`); error: field message or the §3 user message | idle / submitting (button spinner, disabled) / success / error | success text fades in |

## 3. Catalog `/shop` (SF-18, SF-19; cards SF-15)
- Header row: `h1` = category name when `category` is set, "Search results" when `q` is set (plus line `“<q>” — <totalItems> results`), "Sale" / "New in" / "Most loved" for collections, else "Shop all". Below: category description (when a category), result count "<n> products" (`aria-live="polite"` only on change).
- Layout ≥ 1024 px: filter sidebar (16 rem) left, grid right (3 cols ≥ 1024, 4 cols ≥ 1536 via `2xl:`). < 1024 px: "Filters (<active count>)" button opens `FilterSheet` (Radix Dialog from the bottom, from 4 rem below the top of the screen, "Show <n> results" button at the bottom which simply closes; filters apply live), grid 2 cols (1 col below 400 px is NOT used: 2 cols down to 360 px with compact cards).
- Filters (from `facets`): Category (radio list, includes "All"), Price (Radix Slider with two thumbs, step ৳100, min/max from `facets.price`, commits on `onValueCommit`; labels show formatted money; inputs `aria-label="Minimum price"`, `"Maximum price"`), Color (swatch checkboxes; each `aria-label="<label> (<count>)"`; zero-count values disabled), Size (checkbox chips; section hidden when `facets.sizes` empty), "In stock only" (Checkbox). "Clear all" button when any filter is active.
- `ActiveFilters`: chips under the header for each active filter ("Sand ×", "৳1,000–৳5,000 ×", "In stock ×", "“mug” ×"), each removable, `aria-label="Remove filter Sand"`.
- Sort `SortSelect` (native `<select>` styled, label "Sort by"): "Featured", "Newest", "Price: low to high", "Price: high to low", "Name: A to Z" ↔ `featured|newest|price-asc|price-desc|name-asc`.
- Grid: `ProductGrid` of `ProductCard`. Pagination below: "Previous", page numbers (max 7 with ellipsis), "Next"; links (crawlable `<a href>`), `aria-current="page"`; hidden when `totalPages ≤ 1`. Changing a filter resets `page` to 1. Scroll to the grid top after a page change.
- URL is the state: every control writes the URL through `lib/catalog/query.ts` (`parseCatalogQuery(searchParams)` → `CatalogQuery`; `serializeCatalogQuery(query)` → string, omitting defaults, sorted keys for stable URLs).
- States: loading (route `loading.tsx` on first load: header skeleton + 8 `ProductCardSkeleton`); pending (while a transition runs: grid `opacity-60`, `aria-busy="true"`, controls stay usable); empty ("No products match these filters." + button "Clear all filters"; with `q`: "No results for “<q>”." + "Check the spelling or try a broader word." + link "Browse all products"); error (`error.tsx`).
- Motion W5: grid items `motion.li` with `layout` + `spring.soft`; `AnimatePresence mode="popLayout"`; initial `{opacity:0, y:distance.reveal}` with `stagger.list` only on first mount.
### ProductCard (SF-15)
- `<article>` with a full-card link to `/products/<slug>` (the name is the link; the card uses the "stretched link" pattern with `after:absolute after:inset-0` so the swatches stay readable).
- Image well aspect 4/5, `bg-surface-2`, `rounded-md`; first image; on `(hover:hover)` hover the second image cross-fades in (`opacity`, `duration.fast`) (W4; Tailwind v4 `hover:` and `group-hover:` already apply only on devices that can hover). `next/image` with `sizes="(min-width:1440px) 25vw, (min-width:1024px) 33vw, 50vw"`.
- Badges top-left (each with `bg-surface` behind it so it stays readable on any photo): "New", "Sale", "Bestseller" (`Badge` variants), "Sold out" when `stockStatus = out_of_stock` (image at 70 % opacity).
- Below: name (`text-body font-medium`), subtitle (`text-small text-fg-muted`), price (`Price` component: sale price in `text-accent` + struck compare-at `text-fg-muted line-through` with `aria-label`: "Sale price ৳5,400, was ৳6,200"), swatches (max 4 dots 12 px + "+n").
- No "Quick add" button: a summary has no variant ids, so adding from the card would need a variant chooser. Left out on purpose (DECISIONS D-07); the card links to the product page.

## 4. Product detail `/products/[slug]` (SF-20, SF-21, SF-22)
- Breadcrumb: "Shop / <Category> / <Name>" (`nav aria-label="Breadcrumb"`).
- Two columns ≥ 1024 px: gallery left (7/12), info right (5/12, `lg:sticky lg:top-24`). Stacked on mobile.
- `ProductGallery`: main image (aspect 4/5) + thumbnails row (buttons `aria-label="Show image 2 of 3"`, `aria-pressed`); mobile: horizontal scroll-snap strip with dots (`aria-hidden` dots + visually hidden "Image 1 of 3" live text); keyboard ←/→ on the focused gallery changes image; click on main image opens a zoom dialog (Radix Dialog, image at full resolution, `Esc` closes). Image change = cross-fade `duration.fast`.
- Info: badges, `h1 font-display text-display-md`, subtitle, `Price` (from the selected variant), `VariantPicker`, `StockBadge` (in stock: "In stock" success; low: "Low stock — order soon" warning; out: "Sold out" danger), quantity stepper (1 … `min(availableQuantity, maxQuantityPerLine)`), `AddToCart` button, delivery note "Free standard delivery over ৳5,000." (formatted from `StoreConfig.freeShippingThreshold`; omitted when null), `ProductDetails` accordion (Radix Accordion: "Description" (open by default, the paragraphs), "Details" (the `details` list as `<dl>`), "Delivery & returns" (text: "Standard delivery: 3–5 working days. Express delivery: 1–2 working days. Unused items can be returned within 14 days." built from `StoreConfig.shippingMethods[]` as `"{label}: {description}."` + the fixed returns sentence)).
- `VariantPicker` (logic in `lib/product/variants.ts`, SF-20): one group per option (`role="radiogroup"`, `aria-label="<Option name>"`); Color as swatch radios (label visible next to the group: "Color: Sand"), other options as text chips. Selection starts from `defaultVariantId`. A value that has no variant in stock in combination with the other selected values is shown crossed-out (`line-through`, still selectable, then the button says "Sold out"). URL keeps the selection: `?variant=<variantId>` (replace, no scroll). Image does NOT change with colour (fixtures have one image set per product).
- `AddToCart`: label "Add to cart — ৳1,450" (price × quantity); disabled with visible reason when sold out ("Sold out") ; while pending a spinner + "Adding…"; on success: W6 fly-to-cart from the main gallery image to `#header-cart-button`, then the drawer opens after the flight (0.7 s) — under reduced motion the drawer opens at once; announcer "Added Ondo Stoneware Mug (Sand) to cart". Errors shown under the button (`role="alert"`) using `toUserMessage`; on `INSUFFICIENT_STOCK` the quantity stepper is set to `details.available`.
- Mobile sticky bar (< 1024 px): when the main AddToCart button scrolls out of view (IntersectionObserver), a bottom bar slides up (y 100 % → 0, spring.snappy) with name, price, and an "Add to cart" button that triggers the same action. Bottom padding uses the utility `pb-safe` (defined in globals.css by SF-02 as `padding-bottom: max(1rem, env(safe-area-inset-bottom))`).
- Related: "You may also like" + 4 `ProductCard`s from `/related`; hidden when empty.
- SEO: `generateMetadata` (title = product name, description = first description paragraph, Open Graph image = first image); JSON-LD `Product` with an `AggregateOffer` (`lowPrice`/`highPrice` as decimal strings, `priceCurrency`, `availability` `https://schema.org/InStock|OutOfStock`), exact shape in card SF-22.
- States: loading (`loading.tsx`: gallery block + text lines skeleton); 404 (`products/[slug]/not-found.tsx`: "We couldn't find that product." + "Browse the shop" button); error boundary.

## 5. Cart page `/cart` (SF-23)
- `h1` "Your cart". Two columns ≥ 1024 px: lines (8/12) + summary (4/12, sticky). Lines use the same `CartLine` (size `lg`: image 120 × 150).
- Summary card: "Subtotal", `FreeShippingMeter`, "Delivery and VAT are calculated at checkout.", button "Checkout", accepted payment line "Cash on delivery available" (only if a `cod` payment method is enabled in `StoreConfig`).
- Empty: "Your cart is empty." + "Start shopping" + "Most loved" row of 4 featured products (fetched client-side via `browserApi.catalog.listProducts({collection:'featured', pageSize:4})`).
- Loading: skeleton for 2 lines + summary. Error: "We couldn't load your cart." + "Try again".

## 6. Checkout `/checkout` (SF-26, SF-27)
- Guard: if cart hydrated and empty → `router.replace('/cart')`.
- Layout: form left (7/12), `OrderSummary` right (5/12, sticky); on mobile the summary is a collapsible panel at the top ("Show order summary ৳3,129" toggle, `aria-expanded`).
- Form sections (one page, all visible, numbered headings `h2`): "1. Contact" (Email, Phone; if signed in, email prefilled from the session and a line "Signed in as <email>"; if guest: "Have an account? Sign in" → `/account/sign-in?next=/checkout`), "2. Delivery address" (First name, Last name, Address, Apartment, suite, etc. (optional), City, Postal code, Country (select from `StoreConfig.countries`; one option → still a select)), "3. Delivery method" (`ShippingMethodPicker`: RadioCards with label, description, price or "Free"), "4. Payment" (`PaymentMethodPicker`: RadioCards; disabled methods shown with their description "Coming soon." and `aria-disabled`), "Order note (optional)" textarea (max 500, counter "<n>/500").
- Inputs use `autocomplete` tokens: `email`, `tel`, `given-name`, `family-name`, `address-line1`, `address-line2`, `address-level2`, `postal-code`, `country`.
- Validation (`lib/checkout/validation.ts`, zod, mirrors 03-API-CONTRACT §4.13 and §5.5): on blur per field and on submit; messages: "Enter your email address." / "Enter a valid email address.", "Enter a phone number we can call.", "Enter your first name.", "Enter your last name.", "Enter your street address.", "Enter your city.", "Enter a valid postal code.", "Choose a delivery method.", "Choose a payment method.", "Keep the note under 500 characters.". On submit with errors: an error summary box at the top (`role="alert"`, focused, `tabIndex=-1`) titled "Please fix these fields:" with links to each field; the first invalid field gets `aria-invalid`.
- `OrderSummary`: lines (image, name, variant, qty, line total), then from `Quote`: "Subtotal", "Delivery" ("Free" when `freeShippingApplied`), "VAT (5%)" (label = `StoreConfig.taxLabel` + rate from `taxRateBps`), "Total" (`text-title`). Quote loading: the numbers show skeleton bars; quote error: "We couldn't calculate the total." + "Try again".
- Submit button "Place order — ৳3,129" (total from the quote); disabled while the quote loads (reason shown: "Calculating total…"); on submit: spinner + "Placing your order…", all inputs `disabled` via `<fieldset disabled>`.
- Errors after submit: field errors from `VALIDATION_FAILED.fields` mapped to inputs (path `shippingAddress.postalCode` → postal code); `PRICE_CHANGED` → banner (warning) "Prices changed since you started checkout. Please review the new total." and the summary shows `details.quote`; `OUT_OF_STOCK` → banner "Some items are no longer available." + list of names + link "Edit cart" (cart re-hydrated); `CART_EMPTY` → redirect `/cart`; network → banner "You seem to be offline. Your order was not placed. Try again." with retry that reuses the same idempotency key.
- Success → `cart.reset()` and `router.push('/order-confirmation/<number>?token=<token>')`.

## 7. Order confirmation `/order-confirmation/[orderNumber]` (SF-28)
- Loads `browserApi.orders.get(number, token)`. Missing token and not signed in → same as 404.
- Top: `ConfirmationCheck` (SVG circle + check, W9), `h1` "Thank you, <firstName>!", line "Order <number> is confirmed." (number in `font-mono`), line "A confirmation will be sent to <email>." (exact: the mock sends no email, so never "has been sent").
- Blocks: "What happens next" (3 steps: "We prepare your order", "It ships with <shipping method label>", "You pay <total> in cash on delivery" (only for cod; for other methods omit the step)); delivery address; `OrderLines`; totals (subtotal, delivery, VAT, total). Buttons "Continue shopping" → `/shop`; if signed in "View your orders" → `/account`; if guest "Create an account" → `/account/register` (note: past guest orders are not linked automatically — no copy promising that).
- States: loading (check placeholder + skeleton lines); 404 ("We couldn't find this order." + "Go to the shop"); error.

## 8. Sign in `/account/sign-in` and Register `/account/register` (SF-24, SF-25)
- Centered card `max-w-md`, `h1` "Sign in" / "Create your account", short line under it ("Welcome back." / "Track orders and check out faster.").
- Sign-in fields: Email (`autocomplete="email"`), Password (`autocomplete="current-password"`, show/hide toggle button `aria-label="Show password"`/"Hide password", `aria-pressed`). Button "Sign in". Link "New here? Create an account" (keeps `next`).
- Register fields: First name, Last name, Email, Password (`autocomplete="new-password"`, hint "At least 8 characters."). Button "Create account". Link "Already have an account? Sign in".
- Errors: `INVALID_CREDENTIALS` → form-level `role="alert"` "That email and password don't match."; `RATE_LIMITED` → "Too many attempts. Try again in <n> seconds."; `EMAIL_TAKEN` → email field error + link "Sign in instead"; validation messages as in checkout plus "Enter your password." / "Use at least 8 characters.".
- Success: session store updated, cart re-hydrated (merged), announcer "Signed in", `router.replace(safeNext ?? '/account')` (`lib/auth/redirect.ts`: only paths starting with a single `/`).
- Already signed in when opening these pages → `router.replace('/account')`.
- No "Forgot password" link (not in the contract; D-07).

## 9. Account `/account` (SF-29) and order detail `/account/orders/[orderNumber]` (SF-30)
- `AccountGuard`: while session status is `unknown` → skeleton; `guest` → `router.replace('/account/sign-in?next=<current path>')`.
- `/account`: `h1` "Hello, <firstName>"; profile block (name, email, "Member since <Month YYYY>"); button "Sign out" (secondary) → `auth.signOut()` → session + cart reset → `router.push('/')` + announcer "Signed out".
- "Your orders" (`OrderHistory`): list of `OrderSummary` rows: number (mono), date ("26 Nov 2026"), status badge (placed/processing = neutral "Placed"/"Processing", shipped = accent "Shipped", delivered = success "Delivered", cancelled = danger "Cancelled"), item count ("3 items"), total, up to 3 preview thumbnails; each row links to `/account/orders/<number>`. Pagination "Load more" button (appends next page) when `page < totalPages`. Empty: "No orders yet." + "Start shopping". Loading: 3 skeleton rows. Error: "We couldn't load your orders." + "Try again".
- Order detail: back link "All orders"; `h1` "Order <number>"; placed date; status badge + payment status ("Payment pending"/"Paid"/"Refunded"); a simple status track (Placed → Processing → Shipped → Delivered; cancelled shows only "Cancelled"); address; method lines; `OrderLines`; totals. 404 → "We couldn't find this order." + link "All orders".

## 10. 404 and error pages (SF-12)
- These two pages sit outside the `(store)` layout (no header/footer); their content is wrapped in `<main id="main" tabIndex={-1}>` and always offers "Go home".
- `not-found.tsx`: `h1 text-display-lg` "Page not found", text "The page you're looking for has moved or never existed.", buttons "Go home" and "Browse the shop".
- `error.tsx` (client): `h1` "Something went wrong", text "Something went wrong on our side. Please try again.", buttons "Try again" (`reset()`) and "Go home"; logs `error.digest` with `console.error` only in development.
- `global-error.tsx`: same text, plain HTML with tokens.
