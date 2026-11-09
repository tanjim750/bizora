# Start prompts (copy and paste)

Pick **one**. Type `/` in the Antigravity agent panel first and look at the list: if `/goal` is there, use A (it keeps the agent working until the goal is met and blocks early stopping; the docs describe it as built for long overnight work with no iteration cap). Otherwise use B. If skills or workflows do not show up at all, use C.
Before sleeping, finish the checklist in `README.md` section "Before you sleep"; an approval prompt nobody answers stops the whole night.

## A. With `/goal` (preferred when available)
```text
/goal Complete the Bizora frontend overhaul described in docs/frontend-overhaul/. First read .agents/rules/* (always on), then docs/frontend-overhaul/MASTER_PROMPT.md, PLAN.md, PROGRESS.md, AUDIT_REPORT.md and DESIGN_SPEC.md. Work on the local branch frontend-overhaul. Frontend only: you may change frontend/**, docs/frontend-overhaul/** and docs/backend-issues/**; never touch the backend, never git push, never open .env files, never print secrets. Done means ALL of the following: (1) every task in docs/frontend-overhaul/PLAN.md is marked done in PROGRESS.md with its commit hash and verification evidence, or marked blocked with the reason after three honest attempts; (2) in frontend/, npm test, npm run format:check and npm run build all exit 0; (3) node docs/frontend-overhaul/scripts/verify-pages.mjs --strict --label final --theme light,dark over every page and tab of the nine workspaces at 1440x900 and 390x844 reports 0 issues, or each remaining issue is explained in PROGRESS.md; (4) docs/frontend-overhaul/FINAL_REPORT.md exists and every backend problem you found is recorded in docs/backend-issues/; (5) git status is clean on branch frontend-overhaul with one local commit per task and nothing pushed. Follow the phases and time boxes in PLAN.md (about 7 to 8 hours); do not stop after one or two hours; at the end of every phase run the four reviewer agents (design-reviewer, code-reviewer, security-reviewer, architect-reviewer) or, if they are unavailable, the matching review skills, and fix every high and medium finding.
```

## B. With the system architect skill
```text
/system-architect start
```
(To resume after an interruption: `/system-architect continue`.)

## C. Plain prompt (works anywhere)
```text
You are the system architect for the Bizora frontend overhaul. Read, in this order: .agents/rules/* (always on), docs/frontend-overhaul/MASTER_PROMPT.md, PLAN.md, PROGRESS.md, AUDIT_REPORT.md, DESIGN_SPEC.md.
Then work through PLAN.md phase by phase for about 7 to 8 hours: build each task properly, verify it with npm test, npm run format:check, npm run build and the page-check script docs/frontend-overhaul/scripts/verify-pages.mjs (desktop and 390 px, light and dark), update PROGRESS.md, and make one local commit per task on branch frontend-overhaul.
Frontend only (frontend/**, docs/frontend-overhaul/**, docs/backend-issues/**). Never touch the backend: write backend problems into docs/backend-issues/<domain>.md. NEVER git push. Never open .env files or print secrets. At the end of each phase run the reviewer agents (or the review skills). Do not stop after one or two hours; when finished write docs/frontend-overhaul/FINAL_REPORT.md.
```

## If it stops
Say: `/system-architect continue` (or paste prompt C again). The agent reads `PROGRESS.md` and carries on after the last finished task. Check `git log --oneline -5` and `PROGRESS.md` to see how far it got.
