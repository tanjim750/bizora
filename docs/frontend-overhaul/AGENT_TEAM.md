# The A-Team in Antigravity: what is installed and how it works here

Checked on 2026-11-09. The owner's own framework, **The A-Team v7, Antigravity edition** (`~/Documents/Antigravity/a-team-antigravity`, identical to `a-team-antigravity.zip`; read-only source, never modified), is installed in this repository in **workspace mode** and adapted to the Bizora frontend overhaul.
The owner's machine has the Antigravity IDE. Everything below was checked against the official Antigravity documentation (`antigravity.google/docs`), the kit's own scripts (read in full), and tests with synthetic hook events. Nothing could be run inside Antigravity itself from here.

## Can the team simply be copied in? Mostly yes, but not blindly
The kit uses documented extension points (rules, skills, subagents, `hooks.json`, `stack.json`), so a workspace install works and its own `install.sh` is safe (it never overwrites). These things had to be handled, and were:
| Problem found | What was done |
|---|---|
| Needs `/adapt` first; with `adapted: false` the SessionStart hook tells the agent "the only valid action is /adapt. Say so and stop." That would end the night at minute one | `.agents/stack.json` written by hand with `adapted: true`, Bizora's real gates (frontend `npm test`, `format:check`, `build`) and a `programme` entry pointing at the overhaul |
| Template secret pattern `sk-` matches `task-`, `desk-`, `ask-`, so the write guard would block normal CSS and JSX | Replaced by `sk-[A-Za-z0-9]{20,}`; client-reachable paths limited to `/frontend/src/`; tested (class names pass, real secrets are denied) |
| The Stop hook (checkpoint gate) returns `decision: "continue"` on every normal stop; the official Hooks page says that **prevents stopping**, while the Build-plugins page says it lets it stop; the pages disagree | Gate **disabled** (`enabled: false` in `.agents/hooks.json`, reason written there). The other three hooks follow the documented schema and stay on |
| Skill and agent names collide with ours (`system-architect`, `design-review`, `security-review`, four reviewers) | The kit's versions are the canonical ones, each with a short, clearly marked addendum (programme mode, Chrome-less screenshots, no `ask_question`). Our old files are backed up in `.claude/memory/frontend-work/agents_before_ateam/` |
| Kit assumes tickets in `docs/ROADMAP.md`, a branch per ticket, worktree subagents, `AskUserQuestion` | The `system-architect` skill has a final section "Programme mode": tasks are the entries of `PLAN.md`, one branch, no builder subagents, autonomous (never asks), records in `PROGRESS.md` plus `docs/CHECKPOINT.md` |
| Reviewer agents ask the owner questions and refuse to score without a browser | Addenda: never call `ask_question`; use `verify-pages.mjs` (Chrome is not installed) |
| `/ship`, `/migrate`, `/db`, `/notify`, `/kickoff`, `/stack-change`, `/sprint`, `/ticket`, `/debate`, `/onboard` are not applicable tonight (some could push or touch the schema) | Moved to `.agents/skills-disabled/` (not deleted; move a folder back to re-enable) |
| The kit warns not to put `.agents/` in `.gitignore`; this repository's own `.gitignore` ignores `.agent`/`.agents` | A negation rule `!/.agents/` was added locally (uncommitted `.gitignore` change). A local pre-commit hook refuses to stage `.agents/`, `GEMINI.md`, `docs/CHECKPOINT.md`; pushes are blocked anyway |
| Codex second reviewer is not installed | `.agents/codex-off` created; the in-model `code-reviewer` holds the second seat |

## What is active
- **Rules (always on):** the kit's law `a-team-law.md` plus our four (`00-project-law`, `10-frontend-engineering`, `20-design-system`, `30-reports-and-progress`); 25.7 KB in total, about 6,400 tokens (limit 20,000). Glob rules `design-law` (UI files) and `schema-law`, and `context-protocol` (model decision).
- **Subagents:** `design-reviewer`, `code-reviewer`, `security-reviewer`, `architect-reviewer` (kit versions, model tier `pro`, tool names all from the official list), each with a Bizora addendum.
- **Skills (24 active):** the kit's `system-architect`, `team`, `design-review`, `security-review`, `qa`, `build`, `adapt`, `codex`; our programme skills `verify`, `checkpoint`, `page-overhaul`, `code-review`, `architect-review`, `backend-issue`, `start-servers`; ECC skills (accessibility, design-system, React); `bizora-frontend-context`, `bizora-ui-qa`. The same commands also exist as legacy workflows (tiny pointers or copies) because the IDE documents slash commands for workflows.
- **Hooks (`.agents/hooks.json`):** write guard (blocks secret-looking writes into `frontend/src`, supports an armed wave boundary in `.agents/guard.json`; it is not armed), post-edit (format and lint feedback; harmless here), session start (injects `docs/CHECKPOINT.md` and the stack summary into the first turn of every session). Checkpoint gate: disabled.
- **Resume file:** `docs/CHECKPOINT.md` (private). It says the programme is active, where the files are, and the exact next step, so any new or restarted session knows what to do.

## How the team runs the night
1. A session starts: the hook injects `docs/CHECKPOINT.md`. The agent reads the programme files and begins at the first task of `PLAN.md` not done in `PROGRESS.md`.
2. The main agent is the orchestrator (`/system-architect`, Programme mode). It builds alone, one task at a time, verifies with `/verify`, commits locally, updates `PROGRESS.md` and `docs/CHECKPOINT.md`.
3. At the end of every phase it calls the four reviewers in parallel with `invoke_subagent` (`Workspace: "inherit"`, read-only, clean context, self-contained brief). It fixes every critical, high and medium finding and records the verdicts.
4. If subagents cannot be invoked, it runs `/design-review`, `/code-review`, `/security-review`, `/architect-review` itself in turn.

## What each surface supports (from the docs)
| Feature | IDE | App | CLI |
|---|---|---|---|
| Rules, skills, legacy workflows, parallel conversations | yes | yes | yes |
| Hooks (`.agents/hooks.json`) and plugins (`.agents/plugins/`) | **yes (documented for the IDE)** | yes | yes |
| Custom subagents (`.agents/agents/*.md`, `invoke_subagent`) | not stated on the docs page; the installed IDE bundle contains the strings `invoke_subagent`, `PreToolUse`, `SessionStart`, `injectSteps` and `.agents/hooks.json` | yes | yes |
| `/goal`, `/boost`, `/teamwork` | not stated | yes | yes |
| `/browser` (needs Google Chrome 144+ with remote debugging) | yes, but Chrome is not installed | yes | |
No minimum Antigravity version is stated in the docs. The kit's own README says "App v2.5+ or CLI v1.2+"; that claim could not be verified. The IDE here already has plugins installed from the official marketplace, which suggests plugin support.

## Not verified
That this IDE build lists the reviewer subagents and runs the hooks; that `/<skill-name>` works as a slash command in the IDE (documented for the App and CLI; the legacy workflow stubs cover the IDE); whether the terminal sandbox allows localhost; the kit's Codex integration (off).
If a hook or the subagents do not load, the programme still works: rules and skills carry the instructions, and the reviews run as skills.
