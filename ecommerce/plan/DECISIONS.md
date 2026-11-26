# DECISIONS — choices made in this plan (veto any before running SF-01)

Each line: the choice · why · how to veto. A vetoed decision is changed in the plan BEFORE the cards that use it run.

| # | Decision | Why | To veto |
|---|---|---|---|
| D-01 | Kit lives in `ecommerce/plan/`, code in `ecommerce/frontend/`, built on a local branch `storefront` in a separate worktree `../bizora-storefront` | The storefront is a separate product; the worktree keeps Antigravity away from the Bizora folder other sessions use; every path in the kit is relative to `ecommerce/`, so the folder can later move to its own repository unchanged | Say where it should live (e.g. its own repo); only `tools/step-start.sh` changes |
| D-02 | Placeholder brand "Aurelo", home & lifestyle goods (ceramics, linen, lighting, stationery, bags), 24 products | A calm product range suits the editorial "wow" style and needs no real photos to look coherent | Give the real product range; 04-FIXTURES and the home copy change |
| D-03 | Currency BDT in paisa, locale `en-BD`, 5 % VAT added on top, free standard delivery from ৳5,000, max 10 per line, Cash on delivery only (card shown as "Coming soon") | Owner is in Bangladesh; all of it is DATA from `GET /store`, never hard-coded | Change `store.json` values (or tell me the real policy) |
| D-04 | Browser always calls the storefront's own `/api/store/*`; Next proxies to the backend when `API_BASE_URL` is set, otherwise a built-in mock answers | One env var switches mock → real; cookies stay first-party; no CORS work for the backend developer | If the backend must be called directly from the browser, the contract §2 cookie rules and CORS need rewriting |
| D-05 | Session = HttpOnly cookie set by the backend (no JWT in localStorage); guest cart in a cookie, merged on sign-in | Safest default; nothing secret is readable by JavaScript | Say if the backend developer insists on bearer tokens |
| D-06 | Page transitions are enter-only (fade-up), no exit animations, no shared-element morph from card to product page | App Router cannot run exit animations reliably; a half-working morph looks worse than none | Ask for View Transitions as an experiment card later |
| D-07 | No "Quick add" on product cards, no wishlist, no reviews, no discount codes, no forgot-password, no policy pages | Not in the requested scope and not in the contract; adding them later is a contract change | Name the ones you want; each becomes contract + cards |
| D-08 | TypeScript 5.9.3 (not 6/7), exact pins for every package, Vitest + Testing Library + Playwright + axe | Proven with Next 16; exact pins stop Antigravity drifting; the whole set resolved cleanly on 2026-11-26 | Say "use TS 6"; only SF-01 changes |
| D-09 | No smooth-scroll library (Lenis), native scroll only; GSAP only for timelines/scroll, Motion for component state | Scroll hijacking hurts accessibility and feels janky on phones | Ask for Lenis; it would be one more card |
| D-10 | Product images: generated placeholder gradients committed to the repo (74 JPGs); real-looking photos only via optional card IMG-01 | No licensed photos exist; remote stock URLs break and need config | Provide photos, or run IMG-01 |
| D-11 | Order confirmation says "A confirmation will be sent to…" (never "has been sent") | The mock sends no email; the copy must stay true for mock and real backend | — |
| D-12 | Fonts Fraunces (display) + Instrument Sans (UI) + JetBrains Mono (numbers), via `next/font/google` | Distinctive editorial pairing, free (OFL), self-hosted by Next at build | Name other fonts |
