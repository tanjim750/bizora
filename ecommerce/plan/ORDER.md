# ORDER — the cards in the only order they may run

One card per Antigravity conversation, top to bottom. A card runs only when every card in its "Depends on" column has a `DONE` row in `LEDGER.md`. The run prompt (`RUN-NEXT.md`) picks the first card below that has no ledger row. Sizes are rough estimates of non-test lines.

| # | Card | What it builds | Depends on | Size |
|---|---|---|---|---|
| 1 | SF-01 | Next.js project by hand, exact versions, Vitest/ESLint/Prettier | — | config |
| 2 | SF-02 | Design tokens, Tailwind theme, fonts, light/dark, token guard + contrast test | SF-01 | ~200 |
| 3 | SF-03 | Motion tokens, reduced-motion hook, GSAP setup, Reveal | SF-02 | ~100 |
| 4 | SF-04 | UI primitives (Button, Field, Input, Select, Checkbox, RadioCard, Badge, Skeleton, Price, Container) | SF-03 | ~300 |
| 5 | SF-05 | API contract in code: zod schemas, types, errors, money/date formatting | SF-01 | ~300 |
| 6 | SF-06 | Mock JSON fixtures + placeholder images | SF-05 | data |
| 7 | SF-07 | Mock backend: router, in-memory DB, catalog endpoints | SF-05, SF-06 | ~350 |
| 8 | SF-08 | Mock backend: cart, auth, checkout, orders + `/api/store` route | SF-07 | ~400 |
| 9 | SF-09 | Data-access layer + the one-env-var mock/real switch | SF-08 | ~200 |
| 10 | SF-10 | Cart, session, announcer, UI stores + hydrators | SF-09 | ~250 |
| 11 | SF-11 | Store shell: header, footer, mobile nav, skip link | SF-04, SF-10 | ~350 |
| 12 | SF-12 | Page-enter transition, 404, error boundaries, loading | SF-11 | ~120 |
| 13 | SF-13 | Cart drawer, stepper, free-delivery meter, rolling count, fly-to-cart | SF-11 | ~380 |
| 14 | SF-14 | Search dialog (⌘K, live suggestions, combobox) | SF-11 | ~250 |
| 15 | SF-15 | Product card, grid, skeleton | SF-04, SF-06, SF-07 | ~150 |
| 16 | SF-16 | Home: hero intro + category tiles | SF-12, SF-15 | ~180 |
| 17 | SF-17 | Home: featured rail, editorial band, new in, values, newsletter | SF-16 | ~300 |
| 18 | SF-18 | Catalog URL state helpers (pure) | SF-05 | ~180 |
| 19 | SF-19 | Catalog page: filters, sort, search, pagination | SF-09, SF-15, SF-18 | ~400 |
| 20 | SF-20 | Variant logic + VariantPicker | SF-04, SF-05, SF-06 | ~180 |
| 21 | SF-21 | Product page: layout, gallery, details, stock, 404 | SF-12, SF-20 | ~330 |
| 22 | SF-22 | Product page: add to cart + fly, sticky bar, related, JSON-LD | SF-13, SF-21 | ~250 |
| 23 | SF-23 | Cart page | SF-13, SF-15 | ~150 |
| 24 | SF-24 | Auth validation, safe redirect, sign-in page | SF-10, SF-11 | ~280 |
| 25 | SF-25 | Registration page | SF-24 | ~30 |
| 26 | SF-26 | Checkout validation + idempotency helpers (pure) | SF-05 | ~180 |
| 27 | SF-27 | Checkout page (form, live quote, place order, all errors) | SF-23, SF-24, SF-26 | ~400 |
| 28 | SF-28 | Order confirmation + check-mark animation | SF-27 | ~220 |
| 29 | SF-29 | Account page: guard, profile, order history, sign out | SF-24, SF-28 | ~250 |
| 30 | SF-30 | Order detail page | SF-29 | ~150 |
| 31 | SF-31 | Sitemap, robots, icon, Open Graph | SF-22 | ~80 |
| 32 | SF-32 | E2E smoke + axe (light, dark, mobile 360 px, reduced motion) | SF-30, SF-31 | e2e |
| 33 | SF-33 | E2E journeys (guest checkout, sign-in merge, account) | SF-32 | e2e |
| 34 | SF-34 | Contract check against mock or real backend | SF-09 | ~200 |
| — | IMG-01 | OPTIONAL: real-looking product photos at the same paths (only when the owner asks) | SF-06 | assets |

Milestones you can look at in the browser (`cd frontend && npm run dev`, open http://localhost:3000):
- after SF-11: the shell with header, footer, dark mode;
- after SF-17: the full home page with its motion;
- after SF-22: browse → product → add to cart (the "wow" path);
- after SF-28: a full guest order;
- after SF-30: everything.
