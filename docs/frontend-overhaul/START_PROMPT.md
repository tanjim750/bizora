# Start prompts (copy and paste)

The agent team is the owner's A-Team (see `AGENT_TEAM.md`). Its session hook injects `docs/CHECKPOINT.md` into the first turn of a session, and its `system-architect` skill has a "Programme mode" that runs `PLAN.md` task by task without asking questions.

Pick **one**. Type `/` in the Antigravity agent panel first and look at the list.
- `/goal` is listed: use **A** (keeps the agent working until the goal is met; the docs describe it as built for long overnight work, no iteration cap, approvals still apply).
- Only `/system-architect` is listed: use **B**.
- Neither is listed, or slash commands do nothing: use **D** (plain text, tells the agent to read the team files directly; recommended). **C** is the shorter plain version.

Before sleeping, finish the checklist in `README.md` section "Before you sleep"; an approval prompt nobody answers stops the whole night.

## 0. Two-minute smoke test (do this first, awake)
Paste this and read the answer; it costs almost nothing and tells you whether the team loaded:
```text
Do not change anything. In one short list tell me: (1) which rules, skills and subagents you can see, (2) whether you were given docs/CHECKPOINT.md at the start of this session, (3) the current git branch, (4) the first not-done task in docs/frontend-overhaul/PLAN.md.
```
Expected: the A-Team rules and skills (`system-architect`, `design-review`, `verify`, ...), the four reviewer agents (if the IDE supports them), branch `frontend-overhaul`, task `T0-1` (Preflight) or the first task not marked done in `PROGRESS.md`. If the hook did not run, it should still find the branch and task by reading the files; that is fine.

## A. With `/goal` (preferred when available)
```text
/goal Complete the Bizora frontend overhaul described in docs/frontend-overhaul/ using the A-Team in .agents/ (run /system-architect in Programme mode). First read docs/CHECKPOINT.md, then the always-on rules in .agents/rules/, then docs/frontend-overhaul/MASTER_PROMPT.md, PLAN.md, PROGRESS.md, AUDIT_REPORT.md and DESIGN_SPEC.md. Work on the local branch frontend-overhaul. Frontend only: you may change frontend/**, docs/frontend-overhaul/** and docs/backend-issues/**; never touch the backend, never git push, never open .env files, never print secrets, never ask me questions (I am asleep: record blockers in PROGRESS.md and continue with the next independent task). Done means ALL of the following: (1) every task in docs/frontend-overhaul/PLAN.md is marked done in PROGRESS.md with its commit hash and verification evidence, or marked blocked with the reason after three honest attempts; (2) in frontend/, npm test, npm run format:check and npm run build all exit 0; (3) node docs/frontend-overhaul/scripts/verify-pages.mjs --strict --label final --theme light,dark over every page and tab of the nine workspaces at 1440x900 and 390x844 reports 0 issues, or each remaining issue is explained in PROGRESS.md; (4) docs/frontend-overhaul/FINAL_REPORT.md exists and every backend problem you found is recorded in docs/backend-issues/; (5) git status shows only the expected untracked .agents/, GEMINI.md and docs/CHECKPOINT.md, with one local commit per task on branch frontend-overhaul and nothing pushed. Follow the phases and time boxes in PLAN.md (about 7 to 8 hours); do not stop after one or two hours; update docs/CHECKPOINT.md after every task; at the end of every phase run the four reviewer agents (design-reviewer, code-reviewer, security-reviewer, architect-reviewer) in parallel with invoke_subagent or, if they are unavailable, run /design-review, /code-review, /security-review and /architect-review yourself, and fix every critical, high and medium finding.
```

## B. With the system architect skill
```text
/system-architect start the Bizora frontend overhaul in Programme mode: tasks are the entries of docs/frontend-overhaul/PLAN.md, one branch (frontend-overhaul), no questions to me, record blockers in PROGRESS.md, never push, frontend only.
```
(To resume after an interruption: `/system-architect continue`.)

## C. Plain prompt (works anywhere, even if skills and hooks do not load)
```text
You are the system architect for the Bizora frontend overhaul. Read, in this order: docs/CHECKPOINT.md, the always-on rules in .agents/rules/, then docs/frontend-overhaul/MASTER_PROMPT.md, PLAN.md, PROGRESS.md, AUDIT_REPORT.md, DESIGN_SPEC.md.
Then work through PLAN.md phase by phase for about 7 to 8 hours: build each task properly, verify it with npm test, npm run format:check, npm run build and the page-check script docs/frontend-overhaul/scripts/verify-pages.mjs (desktop and 390 px, light and dark), update PROGRESS.md and docs/CHECKPOINT.md, and make one local commit per task on branch frontend-overhaul.
Frontend only (frontend/**, docs/frontend-overhaul/**, docs/backend-issues/**). Never touch the backend: write backend problems into docs/backend-issues/<domain>.md. NEVER git push. Never open .env files or print secrets. Never ask me questions; I am asleep: record blockers in PROGRESS.md and continue. At the end of each phase run the reviewer agents (or the review skills /design-review, /code-review, /security-review, /architect-review) and fix every critical, high and medium finding. Do not stop after one or two hours; when finished write docs/frontend-overhaul/FINAL_REPORT.md.
```

## D. No slash commands available (recommended when `/` shows nothing useful)
Works with plain text only: it tells the agent to read the team's files directly instead of calling commands. Paste the whole block as one message.
```text
You are the autonomous lead of the Bizora frontend overhaul. I am asleep until the morning (about 7 to 8 hours) and will NOT answer anything. Never ask me a question, never wait for my approval, never stop to check in. When unsure, take the default written in the docs, record the decision in docs/frontend-overhaul/PROGRESS.md and keep going. If you are truly blocked, write it under "Blocked / questions for the owner" in PROGRESS.md and continue with the next independent task. If a command needs an approval that is not given, find another way and note it; do not wait.

Slash commands may not exist here, so use the team by reading its files directly:
1. Read, in this order: docs/CHECKPOINT.md, every file in .agents/rules/ (always on), then docs/frontend-overhaul/MASTER_PROMPT.md, PLAN.md, PROGRESS.md, AUDIT_REPORT.md, DESIGN_SPEC.md and assets/tokens.css.
2. Read .agents/skills/system-architect/SKILL.md, above all its last section "Programme mode", and follow it. You are the orchestrator: you build alone, one task at a time, on one branch.
3. Skills are the files .agents/skills/<name>/SKILL.md. Whenever the plan or a rule mentions /verify, /checkpoint, /page-overhaul, /design-review, /code-review, /security-review, /architect-review, /qa, /backend-issue or /start-servers, open that file and follow it step by step. Also use the accessibility, design-system, frontend-patterns, react-patterns and react-performance skills when they apply.
4. Reviewers: at the end of EVERY phase run the four reviewers design-reviewer, code-reviewer, security-reviewer and architect-reviewer (definitions in .agents/agents/). If you can start subagents (invoke_subagent), start them in parallel, read-only, each with a self-contained brief. If you cannot, read each definition and do that review yourself as a separate pass. Write each verdict into PROGRESS.md and fix every critical, high and medium finding before the next phase.

Work plan: check `git branch --show-current`; it must be frontend-overhaul (else `git switch frontend-overhaul`). Check the servers with `bash docs/frontend-overhaul/scripts/dev-status.sh`; if one is DOWN follow .agents/skills/start-servers/SKILL.md. Note the start time (`date`) in PROGRESS.md. Then work through PLAN.md phase by phase (T0-1 to T7-1), starting at the first task not marked done in PROGRESS.md. For each task: build it properly, verify it (in frontend/: npm test, npm run format:check, npm run build; and node docs/frontend-overhaul/scripts/verify-pages.mjs for the pages you touched at 1440x900 and 390x844, light and dark), fix what fails, update PROGRESS.md and docs/CHECKPOINT.md, then make ONE local commit with a conventional message (stage only files under frontend/ and docs/; never stage .agents/, GEMINI.md or docs/CHECKPOINT.md). Quality over speed: do not stop after one or two hours. If everything is done before 7 hours, do a second full review pass over all nine workspaces and fix what it finds.

Hard rules (never break): frontend only, so change only frontend/**, docs/frontend-overhaul/** and docs/backend-issues/**. Never edit the backend; write backend problems into docs/backend-issues/<domain>.md and give the UI an honest workaround. NEVER git push, no force push, no tags, no remote changes, never use --no-verify or the ALLOW_* variables. Never open .env files, never print or commit secrets. Adding a heavy dependency or changing the stack is the owner's decision: record it as blocked. Follow the honesty wording and design rules in .agents/rules/ exactly.

Finish: when every task is done or blocked, run a last full check, write docs/frontend-overhaul/FINAL_REPORT.md (what was done per task with commit hashes, verification numbers before and after, backend issues found, blocked items, and what I must check in the morning), update docs/CHECKPOINT.md and stop. Done means: every task in PLAN.md is done with a commit and evidence, or blocked with a reason; npm test, format:check and build exit 0; the page check over all nine workspaces reports 0 issues or each remaining one is explained; nothing is pushed.
```

## If it stops
Say: `/system-architect continue` (or paste prompt C again). A new session gets `docs/CHECKPOINT.md` from the hook (or reads it, as prompt C says) and carries on after the last finished task. Check `git log --oneline -5` and `PROGRESS.md` to see how far it got.
