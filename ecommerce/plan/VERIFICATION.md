# VERIFICATION — how we know it is done (and not just "the agent said so")

Status: plan, written 2026-11-26. Four layers. A layer only counts with pasted output or a screenshot.

## 1. Every card (after each Antigravity conversation; 1–3 minutes)
Run from `ecommerce/` (independent of what the agent wrote):
```bash
bash plan/tools/verify-card.sh SF-07 <commit-hash>
```
It checks, trusting nothing in the ledger: the commit exists and its message ends with `(SF-07)`; no `Co-Authored-By` or AI wording in the message; every changed file is under `frontend/` (except the ledger, which is never committed by the agent); `package.json`/`package-lock.json` changed only in SF-01; the card's new test file is in the commit; that test FAILS on the parent commit (red) and PASSES on the card's commit (green); with `--full` also `npm test`, `npm run typecheck`, `npm run lint` on the card's commit. Exit code 0 = OK.
Then glance at the diff: `git show --stat <hash>` (the files must match the card's "Files you may change").

## 2. Automated suites (after SF-32 / SF-33 / SF-34)
| Check | Command (in `frontend/`) | Pass |
|---|---|---|
| Unit + component tests | `npm test` | 0 failed |
| Types / lint / format | `npm run typecheck && npm run lint && npm run format:check` | clean |
| Production build | `npm run build` | succeeds |
| E2E + axe (light, dark, mobile 360 px, reduced motion) | `npm run test:e2e` | 0 failed, 0 axe violations |
| Journeys (guest checkout, sign-in merge, account) | `npx playwright test tests/e2e/journeys.spec.ts` | 0 failed |
| Contract vs mock | `npm run contract:check` | 0 failed |
| Token guard + contrast | part of `npm test` (SF-02) | 0 failed |

## 3. Human browser pass (the owner or Claude; nothing is "done" visually before this)
Start: `cd frontend && npm run dev`, open http://localhost:3000. Do each row in light mode, dark mode, at 360 px width (DevTools device toolbar), and once with reduced motion on (DevTools → Rendering → "Emulate CSS prefers-reduced-motion: reduce").
| Page | Look for |
|---|---|
| Home | Hero lines rise from a mask, image settles (W1); tiles reveal; featured rail pins and scrolls sideways on desktop, swipes on phone (W3); editorial image unmasks on scroll; nothing jumps (no layout shift when fonts load); dark mode looks intentional, not inverted |
| Shop | Filters change the grid smoothly (W5) and the URL; back button restores filters; empty state copy; mobile filter sheet; pagination with `?page=2` |
| Product | Gallery thumbnails, arrow keys, zoom; variant change updates price and `?variant=`; sold-out combination (Still Bed Linen, Ash / King); add to cart: image flies to the bag, count rolls, drawer slides in (W6, W7); sticky bar on phone |
| Cart drawer / cart page | Quantity +/−, max hint, remove animation, free-delivery meter, empty state |
| Search | ⌘K / Ctrl K and `/` open it; typing "lamp"; arrows + Enter; Esc closes; focus returns to the button |
| Checkout | Empty submit → error summary with links that focus fields; live total changes with Express; "Card payment" disabled; place order → confirmation with the drawn check (W9) |
| Sign in / Register | Wrong password message; `demo@aurelo.test` / `demo-pass-123` works; guest cart merges after sign-in |
| Account | Three demo orders, statuses, order detail, sign out |
| Keyboard only | Tab through every page: visible focus everywhere, skip link first, dialogs trap focus and return it |
| Reduced motion | No movement anywhere; everything still visible and usable; fly-to-cart becomes a short fade of the bag icon |

Performance (Chrome DevTools → Lighthouse, mobile, on `npm run build && npm run start`): Home, Shop and one product page: Performance ≥ 85, Accessibility 100, Best Practices ≥ 95, SEO ≥ 95; LCP < 2.5 s, CLS < 0.1. Record the numbers in `plan/LOG.md` (create it then).

## 4. Hand-over to the backend developer
1. Send `plan/03-API-CONTRACT.md` (the contract) and the folder `frontend/src/lib/api/schemas.ts` (the same contract as code).
2. They implement it and run `CONTRACT_BASE_URL=<their base> npm run contract:check` until green (§9 checklist inside the contract).
3. Switch: in `frontend/.env.local` set `API_BASE_URL=<their base>` (and `IMAGE_REMOTE_HOST=<image host>` if their image URLs are on another host), restart. Nothing else changes.
4. Re-run `npm run test:e2e` against a build with that env var (journeys create a real test user and order: use a staging backend, never production).
