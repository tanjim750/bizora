# Frontend overhaul: start here

Prepared on 2026-11-09 by Claude (the planning "brain") for an unattended overnight run by another AI agent, written for **Google Antigravity** (the owner's machine has the Antigravity IDE). Everything is plain files, so another agent tool can use them too. Nothing here has been pushed; all work is local.

## What this is
The teammate's first Next.js frontend (`frontend/`) works and shows real backend data, but it is a generic record browser with a teal hard-coded look and several bugs. This folder holds everything an agent needs to turn it into a professional, hackathon-ready product UI in 7 to 8 hours, without touching the backend, and to write down every backend problem it finds, per domain.

| File | Purpose |
|---|---|
| `START_PROMPT.md` | **The prompts to paste** (with `/goal`, with the skill, or plain) |
| `MASTER_PROMPT.md` | The full brief for the agent |
| `PLAN.md` | Phases and tasks with acceptance criteria and time boxes |
| `PROGRESS.md` | The agent's live log (empty checklist now) |
| `AUDIT_REPORT.md` | What is wrong: colours, contrast, bugs with file and line, structure, route mapping, test breakage, risks |
| `DESIGN_SPEC.md` | What to build: foundations, nine workspaces, tabs, page content, endpoints, states |
| `AGENT_TEAM.md` | What Antigravity supports (checked against its docs) and how the reviewer team is used |
| `assets/tokens.css` | Design tokens (neutral slate plus one cobalt primary, light and dark, contrast-verified; spacing, radius, shadow, type, motion) |
| `scripts/` | `dev-setup.sh`, `dev-backend.sh`, `dev-frontend.sh`, `dev-status.sh` (run the app) and `verify-pages.mjs` (screenshots plus automatic checks, no Chrome needed) |
| `../backend-issues/` | Per-domain backend problem lists (13 domains, summary and owner decisions) |
| `../frontend.md`, `../frontend-api-reference.md` | Design system, modules and verified API contracts (the Vite stack sections of `frontend.md` are superseded, see decisions) |

The agent team is the owner's **A-Team (Antigravity edition)**, installed in `.agents/` (workspace mode) and adapted: always-on rules, 24 skills (`/system-architect`, `/team`, `/design-review`, `/security-review`, `/qa`, `/build`, plus our `/verify`, `/checkpoint`, `/page-overhaul`, `/code-review`, `/architect-review`, `/backend-issue`, `/start-servers` and ECC skills), four reviewer subagents, three active hooks, and the resume file `docs/CHECKPOINT.md`. Details, what was changed and why: `AGENT_TEAM.md`. `.agents/` and `GEMINI.md` show up as untracked in `git status` (Antigravity must be able to read them); a local hook refuses to commit them. Before the overhaul starts, the **baseline** screenshots and automatic-check report of the old UI are in `~/bizora-shots/baseline/` (do not delete).

## Before you sleep (10 minutes; this decides whether the night works)
1. **Branch and servers.** Open `/home/hamza/Documents/UniverSity/bizora` in Antigravity. Bottom-left must say `frontend-overhaul` (else `git switch frontend-overhaul`). Servers: `bash docs/frontend-overhaul/scripts/dev-status.sh` should show both OK; if not, start them in two Antigravity terminals: `bash docs/frontend-overhaul/scripts/dev-backend.sh` and `bash docs/frontend-overhaul/scripts/dev-frontend.sh` (first time on a new machine: `bash docs/frontend-overhaul/scripts/dev-setup.sh`). The servers Claude started die when this Claude session closes.
2. **Team loaded?** In the agent side panel open Customizations: you should see the rules (`00-project-law`, `10-frontend-engineering`, `20-design-system`, `30-reports-and-progress`, `a-team-law`), the skills, the four reviewer agents, and under Hooks the write guard, post-edit and session start (the checkpoint gate is intentionally off). If hooks or agents are missing, the IDE build may not support them: the night still works with rules and skills. If a rule is missing, check its first line is `trigger: always_on`.
3. **No approval prompts.** An approval nobody answers stops the whole night, and `/goal` does not remove approvals. In Antigravity's settings set terminal command execution to a mode that does not ask (the docs name the presets Auto, which needs a personal account and a recent version, and Turbo, which has no restrictions; the IDE's exact setting names were not verifiable), and add **deny** rules for `command(git push)` and `command(rm -rf)` (rule format `action(target)`, deny beats allow).
   The local git hooks block every push and any commit outside `frontend/` and `docs/` anyway. Test it: ask the agent "run `bash docs/frontend-overhaul/scripts/dev-status.sh` and `cd frontend && npm test`" and confirm it runs without asking. If the status script says DOWN while the servers are up, the terminal sandbox is blocking localhost: allow `command(curl)`, `command(node)`, `command(npm)`, `command(bash)` or switch the mode.
   **Permission list for tonight** (paste into Antigravity's permission rules; format `action(target)`, deny beats allow; adjust if a pattern does not match). The kit's own list asks before `git push` and does not allow `git commit`, which would stall an unattended run, so tonight's list differs:
   ```
   Allow: command(git status), command(git diff), command(git log), command(git show), command(git branch), command(git add), command(git commit), command(git switch), command(git restore --staged),
          command(npm test), command(npm run), command(npm ci), command(npx prettier), command(node), command(bash docs/frontend-overhaul/scripts), command(curl http://127.0.0.1), command(curl http://localhost)
   Deny:  command(git push), command(git push --force), command(git push -f), command(git reset --hard), command(sudo), command(rm -rf), read_file(.env), write_file(.git/)
   ```
4. **Page-check script works from the agent's terminal:** ask it to run `node docs/frontend-overhaul/scripts/verify-pages.mjs --label preflight /login` and check it prints a table. (The `/browser` subagent needs Google Chrome; only Brave is installed here, so this script is the main verification tool.)
5. **Browser rule (only if you want `/browser` anyway):** Settings, Browser, Browser Actuation Rules: add an Allow rule for `localhost`.
6. **Keep the computer awake for 10 hours** (the agent stops when the machine sleeps): run in a terminal and leave it open: `systemd-inhibit --what=idle:sleep:handle-lid-switch --who=bizora --why="overnight agent" sleep 36000`. Plug in the charger, keep Antigravity open, and check your plan's credit or usage limits cover a long run (not verifiable from here).
7. **Paste a prompt from `START_PROMPT.md`** (type `/` first: `/goal` if listed, else `/system-architect start`, else the plain prompt).
8. After 30 to 60 minutes glance at `docs/frontend-overhaul/PROGRESS.md` and `git log --oneline -5`: tasks should be getting checked off with commits. If nothing moves, it is probably waiting for an approval; answer it and re-check the settings in step 3.

## Which Antigravity features are confirmed (details in `AGENT_TEAM.md`)
Confirmed in the docs for the IDE: rules (`.agents/rules`, `AGENTS.md`, `GEMINI.md`), skills (`.agents/skills`), legacy workflows (`.agents/workflows`), parallel conversations. Documented only for the App and CLI, not stated for the IDE: custom subagents, `/goal`, `/boost`, `/teamwork`. Everything was written so the night works without them (the same review passes exist as skills).

## In the morning
Read `PROGRESS.md` and `FINAL_REPORT.md`; `git log --oneline main..frontend-overhaul`; compare `~/bizora-shots/baseline/` with the final screenshots; run the app and click through; skim `docs/backend-issues/README.md` for the new counts. To publish the branch yourself:
`ALLOW_PUSH=1 git push origin frontend-overhaul` (a local guard blocks pushes unless you set that variable for one command). Nothing has been pushed by Claude or the agents.

## Decisions already made (do not re-open them overnight)
- **D-F20** Adopt the teammate's Next.js 16 (JavaScript) app; the Vite plan in `docs/frontend.md` section 1 is retired (keep the proxy, session and CSRF design).
- **D-F21** Nine workspace pages with tabs as path segments, drawers and dialogs, grouped navigation; old routes redirect.
- **D-F22** Neutral slate plus one cobalt primary, light and dark themes, tokens only; non-colour tokens added after the audit.
- **D-F23** A development-only demo sign-in exists (`/api/demo-login`); off in production builds and unless the server environment enables it.
- **D-F24** The backend is frozen for this effort; problems go to `docs/backend-issues/`. Local hooks block pushes and out-of-scope commits.
- **D-F25** A sample-data (SIMULATED) mode for the Intelligence page is optional, off by default, never mixed with real rows.
- **D-F26** The page-check script (`verify-pages.mjs`) is the primary verification tool because Chrome is not installed; reviewers are read-only subagents with skill fallbacks.

## What was verified and what was not
Verified: all contrast numbers (computed), the token file (31 pairs per theme, chart palette colour-blind checked), both servers with the demo login, 18 unit tests, the local guards (push blocked, backend commit blocked), the page-check script (ran on real pages and found a real issue, the login brand dot at 1.42:1), the rule file sizes against the documented limits, and the folder names and formats against the official docs.
Not verified: that the Antigravity IDE lists the reviewer subagents or `/goal`; the IDE's exact permission setting names; that any skill runs exactly as written; whether the terminal sandbox allows localhost; the Playwright e2e suite (skips without credentials; no Chrome); PostgreSQL behaviour; your plan's usage limits.
