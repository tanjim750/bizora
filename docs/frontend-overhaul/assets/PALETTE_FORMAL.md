# Formal theme (v2): palette and typography

Chosen 2026-11-10 after the owner saw the first overnight result: the layout was good, but the text and colours looked heavy, blue-on-blue and slightly cramped. The file `tokens.formal.css` is the finished replacement for `frontend/src/styles/tokens.css` (same token names, nothing removed, six type tokens added).

## What was wrong (measured on the running app)
- Headings used Plus Jakarta Sans 700 with **negative letter-spacing** (-0.025em to -0.04em): words run together ("Opencases", "requireshuman review").
- Three typefaces (Jakarta, Inter, JetBrains Mono); monospace was used for ordinary dates in tables, which looks technical and harsh.
- Weight 700 in 13 places; card titles 18 px and page title 28 px looked shouty next to 14 px body text.
- Palette: a default-looking vivid blue (#1d4ed8) used for every outline button, link and badge; navy-blue canvas and cards in dark mode; saturated orange badge; slate tones with a strong blue cast.

## The choice
**Typeface:** IBM Plex Sans for everything (400, 500, 600), IBM Plex Mono only for identifiers, keys and code (400, 500), Noto Sans Bengali as the Bengali fallback. It is a corporate, neutral, highly legible face with tabular figures for numbers. Loaded with `next/font/google` (self-hosted at build time, no runtime CDN request), like the fonts before it.
**Type scale:** page title 26/600, section 18/600, card title 16/600, body 14/400 with line-height 1.5, table 13, caption 12, overline 11 uppercase with +0.06em tracking, KPI 26/600 (hero 32). Letter-spacing 0 on headings. Only weights 400, 500, 600.
**Colour:** calm neutral greys with a faint cool tint, one deep steel-blue primary, muted semantic colours, a deep ink-navy rail. No gradients, no second accent.

| Role | Light | Dark |
|---|---|---|
| Canvas / surface / subtle | #f5f6f8 / #ffffff / #edf0f4 | #0f141a / #151b23 / #1c242e |
| Border / input border | #d8dee6 / #7a8696 | #2b3542 / #7b8798 |
| Text / secondary / muted | #121c2b / #364252 / #556173 | #e6ebf1 / #bfc8d4 / #98a3b1 |
| Primary / hover / subtle / text | #1b4b8f / #143a72 / #eaf0f8 / #17407d | #7faee8 / #a3c4ef / #16263a / #b7d0f2 |
| Success / warning / danger / info | #1e6b45 / #8a5300 / #a12b2b / #1d5f8e | #5cc38a / #e0a93a / #ee7b7b / #5fb0e4 |
| Rail background / text / active / indicator | #101c2c / #c9d2de / #1b2a3f / #7fb0e8 | #0a0f15 / #c9d2de / #17202b / #7fb0e8 |

## Verified
48 contrast pairs per theme, 0 failures (computed with the WCAG formula): text on canvas, surface and subtle (17.1:1 on white), secondary 10.2:1, muted at least 5.5:1 on every surface, primary text on white 8.6:1, white on primary 8.6:1, white on warning 6.3:1, semantic text on its tint at least 8:1, input border at least 3.4:1, focus ring at least 3:1, rail text and muted text at least 6.5:1. Chart colours are unchanged (already colour-blind checked).
Not verified: how it looks. The page-check script checks contrast, overflow and focus but cannot judge taste; the screenshots must be looked at.
