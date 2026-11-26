# Start with Antigravity (copy-paste sheet)

## Once: create the separate work folder (local only, nothing pushed)
Run in a terminal from `/home/hamza/Documents/UniverSity/bizora`:
```bash
bash ecommerce/plan/tools/step-start.sh --dry-run
```
```bash
bash ecommerce/plan/tools/step-start.sh
```
Then open Antigravity on this folder (NOT the bizora folder):
`/home/hamza/Documents/UniverSity/bizora-storefront/ecommerce`

## Every card: a NEW conversation, paste this one line
```
Open plan/RUN-NEXT.md, read it completely, and do exactly what it says.
```
It does exactly one card (tests first, gates, one local commit, a ledger row) and stops with `NEXT CARD: SF-xx`. Then open a new conversation and paste the same line again.

## To redo or force one specific card
```
Open plan/RUN-NEXT.md, read it completely, and do exactly what it says, for card SF-07 only.
```
(For a BLOCKED card, first delete its row in `plan/LEDGER.md`.)

## If Antigravity asks you something
- Asks to run `npm install`, `npx playwright install chromium`, `npm run build`, `npx vitest`: allow.
- Asks to `git push`, `git merge`, `git rebase`, `git reset`, switch branch, or open a pull request: refuse.
- Says BLOCKED: do not argue with it. Send the report to Claude.

## Check after each card (or tell Claude "check SF-xx")
From `bizora-storefront/ecommerce`:
```bash
bash plan/tools/verify-card.sh SF-01 <commit-hash> --no-tests
```
From SF-02 on, drop `--no-tests`.
