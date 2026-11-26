# 04 — Mock data (JSON fixtures) specification

Status: plan, written 2026-11-26. Card SF-06 creates these files exactly from this spec. Every fixture value must validate against the zod schemas of 03-API-CONTRACT (a test checks it). Folder: `frontend/src/mocks/fixtures/`.

## 1. Files
| File | Top-level JSON | Content |
|---|---|---|
| `store.json` | `StoreConfig` | Exactly the example in 03-API-CONTRACT §4.3 |
| `home.json` | `HomeContent` | Exactly the example in 03-API-CONTRACT §4.16 |
| `categories.json` | `{ "items": Category[] }` | The 5 categories of §2, in that order; `productCount` = number of products in §3 with that category; `image` = the first image of the first product of that category |
| `products.json` | `{ "items": Product[] }` | The 24 products of §3 in that order (this order IS the "featured" sort order) |
| `users.json` | `{ "items": MockUser[] }` | §5 (mock-only shape: `Customer` + `"password"`) |
| `orders.json` | `{ "items": MockOrder[] }` | §6 (mock-only shape: `Order` + `"customerId"` + `"confirmationToken"`) |

Images: `frontend/public/mock/products/<slug>-1.jpg`, `-2.jpg`, `-3.jpg` (1600 × 2000) and `frontend/public/mock/editorial/hero.jpg` (2400 × 1600), `workshop.jpg` (1600 × 2000). SF-06 generates calm placeholder JPGs with `scripts/make-placeholder-images.mjs` (uses `sharp`, which Next already installs: a soft two-tone vertical gradient from the product's first swatch colour to `#ECE6DC`, plus the product name in small uppercase text, at the exact sizes). Optional card IMG-01 replaces them with real photographs at the same paths.

## 2. Categories
| id | slug | name | description |
|---|---|---|---|
| `cat_ceramics` | `ceramics` | Ceramics | Hand-thrown stoneware for the table. |
| `cat_linen` | `linen` | Linen & Textiles | Stonewashed linen that softens with every wash. |
| `cat_lighting` | `lighting` | Lighting | Warm light for slow evenings. |
| `cat_stationery` | `stationery` | Paper & Desk | Notebooks and tools for the desk. |
| `cat_bags` | `bags` | Bags & Carry | Canvas and leather made to be used daily. |

## 3. Products (price in taka; store ×100 as minor units; "—" = none)
| # | slug | name | subtitle | category | price ৳ | compare-at ৳ | options (values) | badges | stock rule |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ondo-stoneware-mug | Ondo Stoneware Mug | Hand-thrown, 350 ml | ceramics | 1450 | — | Color: Sand, Ink, Moss | bestseller | all 25 |
| 2 | kiln-serving-bowl | Kiln Serving Bowl | Speckled glaze, 24 cm | ceramics | 3200 | — | Color: Sand, Ash | new | all 25 |
| 3 | tide-dinner-plates | Tide Dinner Plates | Set of four, 27 cm | ceramics | 5400 | 6200 | Color: Ash, Ink | sale | all 25 |
| 4 | hollow-bud-vase | Hollow Bud Vase | Matte, 18 cm | ceramics | 1850 | — | Color: Sand, Clay, Ink | — | all 3 |
| 5 | ember-teapot | Ember Teapot | Cast iron lid, 900 ml | ceramics | 4600 | — | Color: Ink | — | all 0 |
| 6 | drift-linen-throw | Drift Linen Throw | Stonewashed, 130 × 180 cm | linen | 6800 | — | Color: Oat, Moss, Clay | bestseller | all 25 |
| 7 | meadow-napkins | Meadow Napkins | Set of four | linen | 1900 | 2400 | Color: Oat, Sky | sale | all 25 |
| 8 | still-bed-linen | Still Bed Linen | Duvet cover | linen | 9800 | — | Color: Oat, Ash; Size: Single, Double, King | new | all 25, except Ash / King = 0 |
| 9 | harbor-apron | Harbor Apron | Heavy linen, adjustable | linen | 2600 | — | Color: Ink, Clay | — | all 25 |
| 10 | loom-cushion-cover | Loom Cushion Cover | 50 × 50 cm | linen | 1650 | — | Color: Oat, Moss, Clay, Ink | — | all 25 |
| 11 | arc-table-lamp | Arc Table Lamp | Brass and linen shade | lighting | 12500 | — | Color: Brass, Black | bestseller | all 25 |
| 12 | halo-pendant | Halo Pendant | Hand-blown glass, 30 cm | lighting | 15800 | 18500 | Color: Smoke, Clear | sale | all 25 |
| 13 | wick-candle-trio | Wick Candle Trio | Soy wax, 40 hours each | lighting | 2200 | — | Scent: Cedar, Fig, Rain | new | all 25 |
| 14 | dusk-floor-lamp | Dusk Floor Lamp | Oak stem, 150 cm | lighting | 21900 | — | Color: Oak | — | all 2 |
| 15 | glow-tealight-holders | Glow Tealight Holders | Set of three | lighting | 1350 | — | Color: Amber, Smoke | — | all 25 |
| 16 | field-notebook | Field Notebook | A5, dot grid, 192 pages | stationery | 950 | — | Color: Moss, Ink, Clay | bestseller | all 25 |
| 17 | ledger-desk-pad | Ledger Desk Pad | Recycled leather, 60 × 30 cm | stationery | 3400 | — | Color: Tan, Black | — | all 25 |
| 18 | quill-pen-set | Quill Pen Set | Brass, refillable | stationery | 2800 | — | Color: Brass, Black | new | all 25 |
| 19 | archive-box | Archive Box | Linen-bound, A4 | stationery | 2100 | 2600 | Color: Oat, Ink | sale | all 25 |
| 20 | market-tote | Market Tote | Waxed canvas | bags | 3900 | — | Color: Oat, Moss, Ink | bestseller | all 25 |
| 21 | commute-backpack | Commute Backpack | Water-resistant, 20 L | bags | 8900 | — | Color: Ink, Clay | new | all 25 |
| 22 | weekend-duffle | Weekend Duffle | Canvas and leather, 40 L | bags | 13500 | 15900 | Color: Tan, Ink | sale | all 25 |
| 23 | pocket-pouch | Pocket Pouch | Zip pouch, 22 cm | bags | 1250 | — | Color: Oat, Moss, Clay, Ink | — | all 25, except Clay = 4 |
| 24 | sling-bag | Sling Bag | Crossbody, 4 litres | bags | 4200 | — | Color: Ink, Moss | — | all 25 |

Size prices for #8 Still Bed Linen: Single 9800, Double 11800, King 13800 (both colours). Every other variant costs the product's price. Sale products: every variant has the compare-at price (for #8 not applicable).

### 3.1 Derivation rules (apply mechanically; a test checks each)
- `id`: `prod_` + the row number padded to 3 digits (`prod_001` … `prod_024`).
- Variants: the cartesian product of the option values, first option outer. `id`: `var_<slug>_<values lower-cased, spaces→hyphens, joined by "_">` (e.g. `var_still-bed-linen_oat_double`). `title`: values joined by `" / "`. `options`: `{ "<option name>": "<value>" }`. `sku`: `AUR-<row padded to 3>-<first 3 letters of each value upper-cased, joined by "-">` (e.g. `AUR-008-OAT-DOU`).
- `availableQuantity` from the "stock rule" column; `stockStatus` by 03-API-CONTRACT §4.6.
- `defaultVariantId`: the first variant with `availableQuantity > 0`, else the first variant.
- Product `price` / `compareAtPrice` / `stockStatus` / `swatches`: by 03-API-CONTRACT §4.8 rules.
- `images`: three images `/mock/products/<slug>-1.jpg`, `-2.jpg`, `-3.jpg`, 1600 × 2000, `alt` = `"<name> in <first value of the first option>, front view"`, `"<name>, close-up detail"`, `"<name> in use at home"`. For #13 (Scent) the first alt is `"Wick Candle Trio, front view"`.
- `description`: two paragraphs: `"<subtitle>. Made in small batches by independent workshops, finished by hand."` and `"Designed to be used every day and to look better with age."`
- `details`: `[{ "label": "Category", "value": "<category name>" }, { "label": "Care", "value": "<care text by category>" }, { "label": "Ships in", "value": "1–2 working days" }]`. Care text: ceramics "Dishwasher safe. Avoid sudden temperature changes."; linen "Machine wash at 40 °C. Tumble dry low."; lighting "Dust with a dry cloth. Use bulbs up to 40 W."; stationery "Keep dry. Wipe leather with a soft cloth."; bags "Spot clean only. Re-wax canvas once a year."
- `createdAt`: products with badge `new`: `2026-11-0<k>T09:00:00Z` where k = 1…5 in table order (#2 → 01, #8 → 02, #13 → 03, #18 → 04, #21 → 05). All others: `2026-06-<row padded to 2>T09:00:00Z`.

### 3.2 Swatches (`OptionValue.swatch` for `Color`; `Scent` and `Size` values have `null`)
| Value | Hex | Value | Hex | Value | Hex |
|---|---|---|---|---|---|
| Sand | `#D8C8B0` | Ink | `#2B2F36` | Moss | `#6B7A55` |
| Ash | `#B9B4AC` | Clay | `#B5694A` | Oat | `#E3D9C6` |
| Sky | `#A9BFCB` | Brass | `#B08D57` | Black | `#1F1F1F` |
| Smoke | `#6E6A66` | Clear | `#E8ECEC` | Oak | `#A27B52` |
| Amber | `#C98B3A` | Tan | `#A9784F` | | |
(These hex values are DATA inside JSON, rendered with an inline `style={{ backgroundColor: value.swatch }}`; the token guard test only scans `.ts`, `.tsx` and `.css` files, never `.json`.)

## 4. Expected derived counts (the SF-06 test asserts these)
- 24 products, 5 categories; productCount: ceramics 5, linen 5, lighting 5, stationery 4, bags 5.
- Total variants: 60 (1:3, 2:2, 3:2, 4:3, 5:1, 6:3, 7:2, 8:6, 9:2, 10:4, 11:2, 12:2, 13:3, 14:1, 15:2, 16:3, 17:2, 18:2, 19:2, 20:3, 21:2, 22:2, 23:4, 24:2).
- `collection=sale`: 5 products (#3, #7, #12, #19, #22). `collection=new`: 5. `collection=featured`: 10.
- Aggregate `out_of_stock`: 1 product (#5). `low_stock`: #4, #14 (2 products). #8 and #23 are `in_stock` overall.
- Cheapest product price 95000 (#16), most expensive 2190000 (#14).

## 5. Users (`users.json`)
```json
{ "items": [ { "id": "cus_001", "email": "demo@aurelo.test", "firstName": "Nadia", "lastName": "Rahman", "createdAt": "2026-03-14T10:00:00Z", "password": "demo-pass-123" } ] }
```
Mock-only: passwords are plain text because this is fake data for a fake server. The real backend hashes passwords; the `password` field never appears in any API response (the mock strips it; a test checks it).

## 6. Orders (`orders.json`) for `cus_001`, all `paymentMethod` cod, address = the §4.15 example address, email `demo@aurelo.test`, phone `+8801712345678`, `note: null`, tax by §4.14
| number | id | status | paymentStatus | placedAt | lines (slug, variant, qty) | shipping method | confirmationToken |
|---|---|---|---|---|---|---|---|
| AUR-100101 | ord_0101 | delivered | paid | 2026-08-02T11:20:00Z | ondo-stoneware-mug Sand ×2; field-notebook Moss ×1 | standard (৳80) | tok_demo_0101 |
| AUR-100117 | ord_0117 | shipped | pending | 2026-10-21T15:05:00Z | drift-linen-throw Oat ×1 | standard (free: subtotal 6800 ≥ 5000) | tok_demo_0117 |
| AUR-100142 | ord_0142 | processing | pending | 2026-11-20T09:40:00Z | arc-table-lamp Brass ×1; wick-candle-trio Fig ×2 | express (৳150) | tok_demo_0142 |
All money fields computed with the §4.14 rules from these lines (SF-06 test recomputes them). `OrderLine.id` = `oline_<order id suffix>_<n>`, `sku`/`image`/`unitPrice` copied from the product variant and its first image. New mock orders get numbers `AUR-100200`, `AUR-100201`, … and ids `ord_0200`, … and token `tok_` + 24 random hex chars.
