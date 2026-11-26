# CARD IMG-01 (OPTIONAL, ASSETS): Replace placeholder images with generated product photographs

Branch `storefront` | any time after SF-06 | Protocol `plan/PROTOCOL.md` (rules 2, 13 apply; there are no code tests) | Read: `plan/04-FIXTURES.md` §1, §3; `plan/01-VISION-DESIGN.md` §2

## 1. Context
The placeholder JPGs from SF-06 are calm gradients. This optional card replaces them with photographs made by your image-generation tool, at the SAME paths and sizes, so no code or fixture changes. Only do it when the owner asks for it.

## 2. Required behaviour
1. For each of the 24 products, generate three images (1600 × 2000, portrait 4:5, JPEG, ≤ 400 KB each): `-1` the product alone on a warm off-white seamless background (`#ECE6DC`-like), soft daylight from the left, front view, the first colour of its first option; `-2` a close-up detail of material/texture; `-3` the product in use in a calm, warm, minimal home interior (oak, linen, plaster walls), no people's faces, no text, no logos, no brand marks.
2. `hero.jpg` (2400 × 1600): stoneware mugs and a linen throw on an oak table in morning light (matches its alt text). `workshop.jpg` (1600 × 2000): hands shaping a mug on a potter's wheel, face not visible.
3. Write each file over the placeholder at the exact path from 04-FIXTURES §1. Verify sizes: `node -e "…sharp(file).metadata()…"` for every file must print the exact width and height; total `du -sh public/mock`.
4. Never include real brands, real people or text in images.

## 3. Tests
`npm test` stays green (SF-06's test checks the files exist). Paste a list of the 74 files with their sizes.

## 4. Files you may change
Only the 74 JPG files under `frontend/public/mock/`.

## 5. Done means
All 74 images replaced with correct dimensions, `npm test` green, ledger row (`IMG-01`), report with `VISUAL: owner must look at them`.

## 6. Commit
`chore(storefront): product photography for mock catalog (IMG-01)`
