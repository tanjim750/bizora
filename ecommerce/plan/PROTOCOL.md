# PROTOCOL — build ONE storefront card, with proof

Read this completely at the start of every conversation. It is short on purpose. AI agents invent names, claim things work without running them, and quietly widen the task. Every rule below makes one of those impossible to do unnoticed.

## What you are
You build **one card per conversation** of the Aurelo storefront (Next.js 16 App Router, React 19, TypeScript, Tailwind 4, Motion, GSAP) in `frontend/`. Your workspace root is the folder `ecommerce/` (it contains `plan/` and `frontend/`). All paths below are relative to it. The plan documents are the law, in this order: the card → `plan/02-ARCHITECTURE.md` → `plan/03-API-CONTRACT.md` → `plan/01-VISION-DESIGN.md` → `plan/05-PAGES.md` → `plan/04-FIXTURES.md`. If they disagree, the earlier document in this order wins (the card beats everything); write the difference under ASSUMPTIONS in your report. STOP with BLOCKED only when the card contradicts itself or is silent on something you need. You never redesign, never "improve" the plan, never do the next card.

## Hard rules (break one = stop and report)
1. **One card per conversation.** Then stop.
2. **Only touch the files the card lists** under "Files you may change", plus your ledger row in `plan/LEDGER.md`. Nothing else in `plan/` may change.
3. **No new dependencies.** Only card SF-01 installs packages, and only the exact versions it lists. Never `npm install <anything>` in another card. Never `--force` or `--legacy-peer-deps`.
4. **Design law:** colours only through the token utilities from `frontend/src/styles/tokens.css` (`bg-bg`, `text-fg`, `text-fg-muted`, `border-border`, `bg-accent`, …). No hex, `rgb(`, `hsl(`, `oklch(` outside `tokens.css`. No arbitrary Tailwind values with units (`p-[13px]`, `mt-[10vh]`); use the scale. Durations and easings only from `src/lib/motion/tokens.ts`, or literal values written in the card itself. Banned defaults: `plan/01-VISION-DESIGN.md` §6.
5. **Data law:** no component, page or store calls `fetch` or imports a fixture. Server code uses `serverApi` from `@/lib/api/server`; client code uses `browserApi` from `@/lib/api/browser`. Prices and totals are displayed as the API returns them; never computed for payment in the client.
6. **Copy law:** user-visible text is exactly the text in the card or in `plan/05-PAGES.md`. Never invent numbers, reviews, stock counts, or promises (no "email sent" — the mock sends none).
7. **Accessibility floor:** `plan/01-VISION-DESIGN.md` §7 for everything you build.
8. **Never invent.** Before you use any existing file, export, prop or type, print it with `grep -n` or `sed -n`. If a card names something from an earlier card and it is not there, write `NOT FOUND`, and the card is BLOCKED ("depends on <card>").
9. **Every claim needs a command.** "Tests pass", "build passes" count only with the command and the real last lines of its output pasted.
10. **Uncertain = write `UNKNOWN`** and stop with BLOCKED. Do not fill the gap with a likely answer.
11. **Tests first.** Write the card's test file first, run it, paste the failing (red) output. Then build until it is green. Never delete, skip (`.skip`, `.todo`) or weaken an existing test.
12. **Size:** if your change exceeds about 400 non-test lines, stop and report BLOCKED ("card too big").
13. **Git (the owner's rules, binding):** stay on branch `storefront`. Allowed git commands: `status`, `log`, `diff`, `show`, `add <paths>`, `commit -m`, `restore` (only to undo your own uncommitted work of this card, see BLOCKED). Forbidden: `merge`, `pull`, `push`, `rebase`, `cherry-pick`, `reset`, `stash`, `checkout`/`switch` of a branch, `branch -f/-D`, `add -A`, `add .`, creating or merging pull requests. **No `Co-Authored-By` line and no AI attribution of any kind in any commit message, ever** (this is a graded project; such a line costs the owner marks).
14. **Test hygiene.** Load fixtures in tests through their schema (`ProductSchema.parse(json)`, `HomeContentSchema.parse(…)`, `OrderSchema.parse(…)`, `StoreConfigSchema.parse(…)`), never with `as` casts. Any test that touches a zustand store resets it in `beforeEach` (`useCartStore.setState(initialCartState)`, `useSessionStore.setState(initialSessionState)`, `useUiStore.setState({ searchOpen: false, mobileNavOpen: false })`). When the same text appears twice on screen, scope the query with `within(...)` instead of loosening the assertion.
15. **No network calls in unit tests.** Tests call pure functions, the mock router, or render components with stubbed modules. The internet is allowed only for `npm install` in SF-01, `next/font` downloads during `npm run build`, and `npx playwright install chromium` in SF-31.
16. **No secrets.** The only credentials anywhere are the mock demo user in `04-FIXTURES` §5.

## Steps (paste the evidence of each step in your reply)

**S0 Orient.** Run from `ecommerce/`:
```bash
git branch --show-current          # must print: storefront   (otherwise STOP; never switch)
git status --short -- frontend     # must print nothing         (otherwise STOP and list it)
git log --oneline -3
```
Then print `plan/LEDGER.md`. Find the card you are asked to do; if it already has a ledger row, STOP ("already done"). Check every card named in the card's "Depends on" line has a `DONE` row; if not, BLOCKED ("depends on <ID>"). From SF-02 on also run the baseline: `cd frontend && npm test 2>&1 | tail -6` (must be green; if red STOP and report, do not repair).

**S1 Read.** Read the card completely, then the plan sections it names. Print (with `sed -n` or `grep -n`) every existing file and export the card tells you to use. Write one sentence: "This card adds <X> in <files>; done means <Y>."

**S2 Red.** Create the card's test file exactly at the path the card gives, with at least the assertions the card lists (you may add more). Run only that file: `cd frontend && npx vitest run <test path>` and paste the failing tail. A test that passes before you wrote the feature is wrong: fix the test, not the feature.

**S3 Build.** Write the code. Only the allowed files. Print `git diff --stat -- frontend` and `git status --short -- frontend`.

**S4 Gates.** Run each and paste the last lines:
```bash
cd frontend && npx vitest run <test path>   # the card's test: green
cd frontend && npm test                     # all unit tests: green
cd frontend && npm run typecheck            # 0 errors
cd frontend && npm run lint                 # 0 errors
cd frontend && npm run format:check         # clean (run `npx prettier --write <your files>` first, then check)
cd frontend && npm run build                # succeeds
```
If an existing test fails and the cause is not obvious after one honest attempt, BLOCKED. Never edit another card's test file unless your card names it.

**S5 Self-audit.** Answer yes/no with evidence: only allowed files? no dependency or lockfile change (except SF-01)? no hex/arbitrary values (`grep -rnE "#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(|oklch\(" frontend/src --include=*.ts --include=*.tsx --include=*.css | grep -v tokens.css` prints nothing)? no `fetch(` outside `src/lib/api/transport-http.ts` and tests (`grep -rn "fetch(" frontend/src | grep -v transport-http`)? copy exactly from the card/05-PAGES? test was red before the build? every name you used was grepped? still on `storefront`?

**S6 Commit locally.** Stage by path (`git add frontend/<file> …`), then one commit with exactly the message the card gives. Print `git log --oneline -1` and `git show --stat --format=%B HEAD | head -40`.

**S7 Ledger.** Append ONE row to `plan/LEDGER.md` (never edit other rows): `| <ID> | DONE | <short hash> | <test path> | <red tail, one line> | <green tail, one line> | <gate summary> |`. The ledger is not committed by you (leave it modified; the owner commits it).

**S8 Report and stop.** Reply in exactly this format:
```
CARD: <ID>
STATUS: DONE | BLOCKED
COMMIT: <hash>   BRANCH: storefront
FILES CHANGED: <list>
TEST: <path>   RED (tail): <pasted>   GREEN (tail): <pasted>
GATES: test=<…> typecheck=<…> lint=<…> format=<…> build=<…>
VISUAL: NOT VISUALLY VERIFIED (no human browser check yet)
ASSUMPTIONS: <list or none>
UNKNOWN: <list or none>
QUESTIONS FOR OWNER: <list or none>
NEXT CARD: <ID from plan/ORDER.md>
```

## BLOCKED procedure
When the card cannot be done honestly (missing dependency card, contradiction in the plan, a needed file outside the list, a needed new package, a gate red after one honest attempt, the card is too big, you notice you are about to guess):
1. Undo only your own uncommitted work: `git restore --source=HEAD --staged --worktree -- <every tracked file you changed>` and `rm <every new file you created>`.
2. `git status --short -- frontend` must print nothing (if it does not, STOP and say so).
3. Append the ledger row with status `BLOCKED` and the exact reason and question.
4. Report in the S8 format and stop.
