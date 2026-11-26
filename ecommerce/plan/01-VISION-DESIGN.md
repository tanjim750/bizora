# 01 — Vision and design direction

Status: plan, written 2026-11-26. Binding for every card. A card may only use the tokens, fonts, durations and easings named here. If a card seems to need something new, it is BLOCKED, not improvised.

## 1. Vision in one paragraph
**Aurelo** (placeholder name; it comes from `GET /store`, in mock mode from `src/mocks/fixtures/store.json`, see 02-ARCHITECTURE §7) is a small online shop for calm, well-made objects for the home: ceramics, linen, lighting, stationery and bags. The site should feel like a printed design magazine that happens to sell things: big confident type, generous space, warm paper colours, real product photography, and motion that is smooth and purposeful, never decorative noise. The "wow" comes from three things done very well: (1) the home page opening sequence and scroll choreography, (2) how the cart reacts (the product flies into the cart, the count ticks, the drawer slides in with springy but calm physics), and (3) how fast and fluid filtering and page changes feel. Everything works with motion turned off, on a 360 px phone, in dark mode, and with a keyboard only.

## 2. Style: "editorial warm minimal"
- Warm off-white paper in light mode, deep warm charcoal (never pure black) in dark mode. One accent colour: burnt terracotta.
- Large serif display type for headlines and product names; a clean grotesque for everything functional (buttons, prices, forms).
- Layout on a 12-column grid with wide outer margins; asymmetric editorial compositions on the home page; strict, quiet grids on catalog and account pages.
- Product photos are the colour; the interface stays neutral. Photos sit on `surface-2` with no borders and a small radius.
- Lines (1 px `border`) instead of shadows to separate things. Shadows only on floating layers (drawer, popover, sticky add-to-cart bar).

### Reference sites (for mood only; do not copy layouts, logos, text or assets)
| Site | What to take from it |
|---|---|
| aesop.com | Warm palette, typographic calm, slow confident pacing |
| ssense.com | Strict product grid, minimal chrome, small uppercase labels |
| apple.com (product pages) | Scroll-driven storytelling, sticky media, restraint |
| kinfolk.com | Editorial serif headlines, whitespace |
| linear.app | Motion quality: short, eased, purposeful micro-interactions |
| rapha.cc | Bold full-bleed imagery with tight type overlays |

## 3. Design tokens (exact values; the only colours allowed in the codebase)
Tokens live in ONE file: `frontend/src/styles/tokens.css` (card SF-02). Components use only the Tailwind utilities generated from these tokens (`bg-bg`, `text-fg`, `text-fg-muted`, `border-border`, `bg-accent`, …). A raw hex, `rgb(`, `hsl(` or `oklch(` anywhere outside `tokens.css` is a bug (a test enforces it).

### 3.1 Colour (contrast measured 2026-11-26, WCAG 2.1 formula)
| Token | Light | Dark | Use | Contrast check |
|---|---|---|---|---|
| `--color-bg` | `#F6F2EC` | `#121110` | Page background | — |
| `--color-surface` | `#FFFFFF` | `#1B1A18` | Cards, drawer, inputs | — |
| `--color-surface-2` | `#ECE6DC` | `#262420` | Image wells, hover rows, skeletons | — |
| `--color-fg` | `#1C1A17` | `#F2EEE7` | Body text, headings | ≥ 12:1 on all three surfaces |
| `--color-fg-muted` | `#5C574E` | `#ABA59A` | Secondary text, labels | ≥ 5.6:1 on all surfaces (light), ≥ 6.4:1 (dark) |
| `--color-border` | `#D9D1C3` | `#36332E` | Hairlines, dividers (decorative) | not for meaning |
| `--color-border-strong` | `#8A8274` | `#77716A` | Input borders, focusable outlines | ≥ 3:1 (non-text, WCAG 1.4.11) |
| `--color-accent` | `#A3461F` | `#E58A5C` | Primary button, links, active states | ≥ 4.5:1 as text on all surfaces |
| `--color-accent-fg` | `#FFFFFF` | `#1A0E08` | Text on accent | 6.08:1 light, 7.32:1 dark |
| `--color-success` | `#2E6B3D` | `#79C48C` | In stock, order placed | ≥ 4.5:1 |
| `--color-danger` | `#B3261E` | `#F28B82` | Errors, out of stock | ≥ 4.5:1 |
| `--color-warning` | `#7A5200` | `#E6B95C` | Low stock | ≥ 4.5:1 |
| `--color-focus` | `#1D4FB8` | `#8AB4F8` | Focus ring only | ≥ 4.5:1 |
| `--color-overlay` | `#1C1A17` at 40 % | `#000000` at 60 % | Scrim behind drawers | written as `color-mix(in srgb, <fg or black> 40%, transparent)` inside tokens.css |

Dark mode is the `.dark` class on `<html>` (next-themes, `attribute="class"`), with `color-scheme: dark` set on it. Default theme = `system`.

### 3.2 Typography
| Role | Font (via `next/font/google`) | CSS var | Weights |
|---|---|---|---|
| Display (headlines, product names on PDP) | **Fraunces** (variable, `opsz` axis, OFL) | `--font-display` | 300–600 |
| UI and body | **Instrument Sans** (variable, OFL) | `--font-sans` | 400, 500, 600 |
| Numbers that must align (order numbers, SKUs) | **JetBrains Mono** | `--font-mono` | 400 |

Type scale (fluid, defined as tokens; components use `text-display-xl`, … utilities):
| Token | Value | Line height | Letter spacing |
|---|---|---|---|
| `--text-display-xl` | `clamp(3rem, 2rem + 6vw, 7.5rem)` | 0.95 | -0.03em |
| `--text-display-lg` | `clamp(2.25rem, 1.6rem + 3.4vw, 4.5rem)` | 1.0 | -0.02em |
| `--text-display-md` | `clamp(1.75rem, 1.4rem + 1.8vw, 3rem)` | 1.05 | -0.015em |
| `--text-title` | `1.375rem` | 1.25 | -0.01em |
| `--text-body-lg` | `1.125rem` | 1.6 | 0 |
| `--text-body` | `1rem` | 1.6 | 0 |
| `--text-small` | `0.875rem` | 1.5 | 0 |
| `--text-label` | `0.75rem`, uppercase | 1.4 | 0.08em |

Body text never smaller than 16 px on inputs (prevents iOS zoom). Max line length for paragraphs: `65ch`.

### 3.3 Space, radius, elevation, layout
- Spacing: Tailwind's default 4 px scale IS the spacing token set. Allowed section paddings: `py-16`, `py-24`, `py-32` (mobile uses one step smaller). No arbitrary values like `p-[13px]`.
- Radius tokens: `--radius-sm: 6px` (inputs, badges), `--radius-md: 12px` (cards, image wells), `--radius-lg: 20px` (drawer edge, hero media), `--radius-pill: 999px` (chips, quantity stepper).
- Shadow tokens: `--shadow-float: 0 12px 40px -12px color-mix(in srgb, var(--color-fg) 25%, transparent)` (drawer, popover, sticky bar). No other shadows.
- Container: `max-width: 90rem` (1440 px) with side padding `px-5` (mobile), `px-8` (≥ 768), `px-12` (≥ 1280).
- Breakpoints (Tailwind v4 defaults): `sm 40rem`, `md 48rem`, `lg 64rem`, `xl 80rem`, `2xl 96rem`. **Smallest supported width: 360 px.** Nothing scrolls horizontally at 360 px except intentional carousels.
- Z-index tokens: `--z-header: 40`, `--z-drawer: 50`, `--z-toast: 60`, `--z-skip: 70`.

## 4. Motion principles
Two libraries, each with a clear job. Never both on the same element.
| Library | Package | Used for |
|---|---|---|
| **Motion** (formerly Framer Motion) | `motion` (import from `motion/react`) | Component state changes: enter/exit of drawers, toasts, dialogs; layout animations (grid re-flow when filters change, cart line removal); page enter transition; micro-interactions (button press, quantity tick, heart toggle); shared-layout `layoutId` from product card image to PDP is **not** used (App Router does not keep both trees). |
| **GSAP** | `gsap` + `@gsap/react` (`useGSAP`), plugins `ScrollTrigger` and `SplitText` (free and bundled in `gsap` 3.15) | Timelines and scroll: home hero intro, scroll-linked reveals, the pinned horizontal "featured" rail, fly-to-cart, the order-confirmation check-mark draw. |

### 4.1 Motion tokens (in `frontend/src/lib/motion/tokens.ts`, card SF-03; mirrored as CSS vars in tokens.css)
| Token | Value | Use |
|---|---|---|
| `duration.instant` | 0.12 s | Press feedback, colour changes |
| `duration.fast` | 0.2 s | Hover, small fades, quantity tick |
| `duration.base` | 0.32 s | Drawers, dialogs, page enter |
| `duration.slow` | 0.56 s | Section reveals |
| `duration.hero` | 0.9 s | Hero headline lines |
| `ease.out` | `[0.16, 1, 0.3, 1]` (CSS `cubic-bezier(0.16,1,0.3,1)`, GSAP `"expo.out"`) | Everything entering |
| `ease.inOut` | `[0.65, 0, 0.35, 1]` (GSAP `"power3.inOut"`) | Things moving across the screen (fly-to-cart) |
| `ease.in` | `[0.7, 0, 0.84, 0]` | Things leaving |
| `spring.snappy` | `{ type: "spring", stiffness: 420, damping: 34, mass: 0.9 }` | Drawer, stepper digits |
| `spring.soft` | `{ type: "spring", stiffness: 220, damping: 28 }` | Layout re-flow of grids |
| `stagger.list` | 0.04 s | Grid items, list rows (max 12 items staggered; the rest appear with the 12th) |
| `distance.reveal` | 24 px | Y offset for reveals |

### 4.2 Rules
1. Animate only `transform` and `opacity` (and `clip-path` for the hero mask, `stroke-dashoffset` for the check mark). Never animate `width`, `height`, `top`, `left`, `margin`, `box-shadow`, `filter: blur` on large areas.
2. Every animation finishes in ≤ 0.9 s, except scroll-linked ones (they follow the scroll).
3. Nothing blocks input: content is clickable during and after animation; no "loading curtain" over the page.
4. Content is visible without JavaScript: elements are rendered visible in HTML and only hidden by the animation code when it starts (`gsap.from` / Motion `initial` inside client components that render after hydration; use `useGSAP` with `scope`).
5. **Reduced motion** (`prefers-reduced-motion: reduce`): Motion uses `<MotionConfig reducedMotion="user">`; GSAP code runs inside `gsap.matchMedia()` with the two conditions `(prefers-reduced-motion: no-preference)` → full animation and `(prefers-reduced-motion: reduce)` → no tweens, elements in their final state; the fly-to-cart becomes a 0.2 s opacity pulse on the cart icon; page transitions become instant; the horizontal pinned rail becomes a normal horizontal scroll list. A Playwright test (SF-32) checks it.
6. No autoplaying carousels, no parallax on text, no scroll hijacking (no Lenis or smooth-scroll library; native scroll only).
7. Hover effects exist only on `(hover: hover)` devices; touch devices get press feedback instead.

## 5. Signature moments (the "wow" list; each is owned by one card)
| # | Moment | Card | Spec |
|---|---|---|---|
| W1 | Hero intro: headline split into lines with SplitText, each line rises from a clip mask (y 100 % → 0, `duration.hero`, stagger 0.08 s); hero image scales 1.08 → 1 over 1.4 s; CTA fades in last | SF-16 | 05-PAGES Home §1 |
| W2 | Category tiles: image inside tile scales 1 → 1.04 on hover, label underline draws left → right | SF-16 | Home §2 |
| W3 | Featured rail: on ≥ 1024 px the section pins and the row of products moves horizontally with scroll (ScrollTrigger `scrub: 0.6`); below 1024 px native `scroll-snap-type: x mandatory` | SF-17 | Home §3 |
| W4 | Product card: second image cross-fades in on hover (only on `(hover: hover)` devices); the name underline draws in | SF-15 | Catalog §ProductCard |
| W5 | Filter change: grid items re-flow with Motion `layout` + `spring.soft`; removed items fade out, new ones fade in | SF-19 | Catalog |
| W6 | Fly-to-cart: a clone of the product image flies along a curve to the header cart icon (GSAP timeline: x with `power3.inOut`, y with `power2.in`, scale → 0.12, 0.7 s), icon bumps (scale 1 → 1.18 → 1), count digit rolls (Motion, old digit exits up, new enters from below) | SF-13 (util), SF-22 (use) | PDP §4 |
| W7 | Cart drawer: slides from the right with `spring.snappy`; scrim fades; line removal collapses with `layout`; subtotal number tweens | SF-13 | Cart drawer |
| W8 | Page transitions: new page fades up 12 px over `duration.base` with `ease.out` (enter only; App Router cannot run exit animations reliably) | SF-12 | Shell |
| W9 | Order confirmation: circle and check mark draw (stroke-dashoffset, 0.8 s), then the order summary staggers in | SF-28 | Confirmation |
| W10 | Theme toggle: sun/moon icon rotates and cross-fades; colours switch with a 0.2 s `background-color, color` CSS transition on `html` (disabled under reduced motion) | SF-02 | Shell |

## 6. Banned defaults (a reviewer rejects these on sight; "it looks fine" is not an argument)
1. Purple/blue gradients, gradient text, glowing blobs, glassmorphism (backdrop-blur cards).
2. Inter or system-ui as the only font; centered body paragraphs; all-caps headlines.
3. Pure black `#000` background or pure white text in dark mode.
4. Shadows on every card; borders AND shadows on the same element.
5. Emoji as icons (use `lucide-react` icons only, 1.5 px stroke, 20 px default).
6. Autoplaying carousels, popups on load, fake countdown timers, fake "12 people are looking at this".
7. Lorem ipsum or invented reviews in the UI. Copy comes from fixtures (04-FIXTURES) or 05-PAGES.
8. Spinners for page loads (use skeletons shaped like the content); spinners only inside buttons.
9. `alert()`, `confirm()`, `window.prompt()`.
10. Bouncy overshoot on everything; animations over 0.9 s; animation on scroll of every paragraph.
11. Disabled buttons without explanation (say why next to it, e.g. "Choose a size").
12. Placeholder text used as a label.

## 7. Accessibility floor (WCAG 2.1 AA)
- Contrast as in §3.1 (a unit test computes it from tokens.css, card SF-02).
- Visible focus on everything focusable: `outline: 2px solid var(--color-focus); outline-offset: 2px;` via `:focus-visible`. Never `outline: none` without this replacement.
- Semantic HTML: one `<h1>` per page, landmarks `header`, `nav`, `main#main`, `footer`; lists are `ul/ol`; buttons are `<button>`, links are `<a>`/`next/link`.
- Skip link "Skip to content" as the first focusable element.
- Every image has `alt` from fixtures (decorative images `alt=""`).
- Forms: `<label>` for every input, errors linked with `aria-describedby`, `aria-invalid`, error summary focused on submit failure.
- Dialogs and drawers (Radix): focus trapped, `Esc` closes, focus returns to the trigger.
- One app-wide `aria-live="polite"` announcer (SF-10) says: "Added <name> to cart", "Cart updated", "Removed <name>", filter result counts.
- Touch targets ≥ 44 × 44 px (`size-11`); colour swatches included.
- Works at 200 % zoom and at 360 px width.
