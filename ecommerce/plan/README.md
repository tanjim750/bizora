# Aurelo storefront — planning kit (START HERE)

Written 2026-11-26. **Plan only: no app code exists yet.** You (the owner) run it card by card with Google Antigravity, one card per new conversation. Claude (or you) checks every card's commit with one script.

## What gets built
A new e-commerce storefront frontend (Next.js 16 App Router, React 19, TypeScript, Tailwind 4, Motion + GSAP), separate from Bizora:
Home · Shop (filters, search, sort, pagination) · Product page (gallery, variants, add to cart) · Cart drawer and cart page · Checkout + order confirmation · Sign in · Register · Account with order history and order detail. Light and dark mode, 360 px phones up to wide desktops, WCAG AA, reduced-motion fallback, and a set of signature animations (hero reveal, pinned product rail, fly-to-cart, drawn check mark).

There is **no backend**. Every screen reads data through a typed layer (`frontend/src/lib/api`) that talks to a built-in **mock backend** which follows the written **API contract** exactly. When your friend's backend is ready, you set ONE env var (`API_BASE_URL`) and restart. A contract-check command tells him first whether his API matches.

## Files
| File | What it is |
|---|---|
| `01-VISION-DESIGN.md` | Style, colour/type/motion tokens (with measured contrast), signature animations W1–W10, banned defaults, accessibility floor |
| `02-ARCHITECTURE.md` | Exact package versions, folder layout, rendering model, data layer, the mock→real switch, state, env vars, quality gates |
| `03-API-CONTRACT.md` | **For the backend developer:** every endpoint, request/response JSON, errors, pagination, cookies/session, cart and checkout flows, checklist |
| `04-FIXTURES.md` | The mock data: 5 categories, 24 products (60 variants), demo user, 3 demo orders, derivation rules, expected counts |
| `05-PAGES.md` | Sitemap and every page: sections, exact copy, loading/empty/error states, animations |
| `PROTOCOL.md` | The law for Antigravity: one card, tests first (red), gates, one local commit, ledger row, report |
| `ORDER.md` | The 34 cards in dependency order (+ optional IMG-01) and when you can look at the site |
| `cards/SF-01.md` … `SF-34.md`, `IMG-01.md` | The cards: context, required behaviour, tests to write first, allowed files, done means, commit message |
| `RUN-NEXT.md` | What the one-line prompt makes Antigravity do |
| `LEDGER.md` | One row per finished or blocked card (Antigravity appends) |
| `VERIFICATION.md` | Per-card check, automated suites, the browser checklist, Lighthouse targets, backend hand-over |
| `DECISIONS.md` | 12 choices I made that you may veto |
| `tools/step-start.sh` | One-time setup: separate worktree + local branch `storefront` |
| `tools/verify-card.sh` | Independent check of one card commit (red on parent, green on commit, files, message) |

## How to run it
1. Read `DECISIONS.md`; tell me any veto before step 2.
2. One-time setup (local only; your Bizora folder is not touched). Check first with `--dry-run`:
```bash
bash ecommerce/plan/tools/step-start.sh --dry-run
```
```bash
bash ecommerce/plan/tools/step-start.sh
```
   It creates `../bizora-storefront` on a new local branch `storefront` and commits this kit there.
3. Open Antigravity on the folder `/home/hamza/Documents/UniverSity/bizora-storefront/ecommerce`.
4. For EVERY card start a NEW conversation and paste this one line:
   `Open plan/RUN-NEXT.md, read it completely, and do exactly what it says.`
   It does the next card only, commits locally, writes the ledger row and stops.
5. After each card (or a few), check it from `bizora-storefront/ecommerce`:
```bash
bash plan/tools/verify-card.sh SF-01 <commit-hash> --no-tests
```
   (From SF-02 on drop `--no-tests`; add `--full` now and then.) Or just tell Claude "check SF-xx".
6. Look at the site at the milestones in `ORDER.md` (`cd frontend && npm run dev`).

Nothing is pushed or merged by anyone without your words.

## Honest limits
- Planned, not executed: no card has run yet. Versions were checked on npm today and the full dependency set resolved in a dry run, but `next build` with these exact versions has not run.
- `tools/verify-card.sh` was tested on a scratch repository for the git checks only; its red/green test runs need the real `node_modules` and are untested until SF-02 exists.
- Unit tests read the DOM in jsdom; they cannot see layout, colour or motion. Every UI card reports `NOT VISUALLY VERIFIED` until the browser pass in `VERIFICATION.md` §3 (SF-32 adds screenshots and axe scans in a real browser).
- 34 cards at roughly 10–20 minutes each is about 8–10 hours of Antigravity time. SF-19 and SF-27 are the largest; if one exceeds 400 lines the agent stops and the card gets split.
- The mock keeps carts, sessions and new orders in memory: restarting `npm run dev` resets them (fine for a demo; the real backend stores them).
