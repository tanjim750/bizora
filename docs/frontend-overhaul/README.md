# Frontend overhaul: start here

Prepared on 2026-11-09 by Claude (acting as the planning "brain") for an unattended overnight run by another AI agent (written for Google Antigravity; plain files, so any agent tool can use them). Nothing here has been pushed; all work is local.

## What this is
The teammate's first Next.js frontend (`frontend/`) works and shows real backend data, but it is a generic record browser with a teal hard-coded look and several bugs. This folder holds everything an agent needs to turn it into a professional, hackathon-ready product UI in 7 to 8 hours,
without touching the backend, and to write down every backend problem it finds, per domain.

| File | Purpose |
|---|---|
| `MASTER_PROMPT.md` | The full brief for the agent (read first) |
| `PLAN.md` | Phases and tasks with acceptance criteria and time boxes |
| `PROGRESS.md` | The agent's live log (empty checklist now) |
| `AUDIT_REPORT.md` | What is wrong: colours, contrast, bugs with file and line, structure, route mapping, test breakage, risks |
| `DESIGN_SPEC.md` | What to build: foundations, nine workspaces, tabs, page content, endpoints, states |
| `assets/tokens.css` | Design tokens (neutral slate plus one cobalt primary, light and dark, contrast-verified; spacing, radius, shadow, type, motion) |
| `scripts/` | `dev-setup.sh`, `dev-backend.sh`, `dev-frontend.sh`, `dev-status.sh` to run the app locally |
| `../backend-issues/` | Per-domain backend problem lists (13 domains, plus a summary and the decisions the backend owner must make) |
| `../frontend.md`, `../frontend-api-reference.md` | Design system, modules and verified API contracts (stack sections of `frontend.md` describing Vite are superseded, see decisions) |

Private agent configuration (not in git): `.agents/rules/` (always-on rules), `.agents/workflows/` (slash commands: `/system-architect`, `/start-servers`, `/page-overhaul`, `/verify`, `/checkpoint`, `/design-review`, `/code-review`, `/security-review`, `/architect-review`, `/backend-issue`),
`.agents/skills/` (ECC accessibility, design-system and React skills copied from the local plugin, plus `bizora-*` skills), `.agent` (a link to `.agents`, because sources disagree on the spelling), and a root `GEMINI.md` pointer.

## How to start the night (5 minutes)
1. Open the repository folder `/home/hamza/Documents/UniverSity/bizora` in Antigravity. Check the bottom-left branch is `frontend-overhaul` (otherwise `git switch frontend-overhaul`).
2. Check that the rules were picked up: Antigravity's rules list should show `00-project-law`, `10-frontend-engineering`, `20-design-system`, `30-reports-and-progress` as always on. If it does not, open each file and set it to Always On in the UI (the location of these settings was not verified).
3. Start the servers in two terminals (or let the agent run `/start-servers`): `bash docs/frontend-overhaul/scripts/dev-backend.sh` and `bash docs/frontend-overhaul/scripts/dev-frontend.sh`. First time on a new machine run `bash docs/frontend-overhaul/scripts/dev-setup.sh` once.
   Open http://localhost:3000/login and use **Continue as demo owner** to check it works.
4. Choose the strongest model available and an agent mode that lets it run terminal commands and the browser on localhost without asking each time. Commits are safe: a local hook blocks every push and any commit outside `frontend/` and `docs/` on this branch.
5. In the agent panel type **`/system-architect start`**. If workflows are not listed, paste this instead:

```text
You are the system architect for the Bizora frontend overhaul. Read, in this order: .agents/rules/* (always on), docs/frontend-overhaul/MASTER_PROMPT.md, PLAN.md, PROGRESS.md, AUDIT_REPORT.md, DESIGN_SPEC.md.
Then work through PLAN.md phase by phase for about 7 to 8 hours: build each task properly, verify it in the browser (desktop and 390 px, light and dark) and with npm test, npm run format:check and npm run build, update PROGRESS.md, and make one local commit per task on branch frontend-overhaul.
Frontend only (frontend/**, docs/frontend-overhaul/**, docs/backend-issues/**). Never touch the backend: write backend problems into docs/backend-issues/<domain>.md. NEVER git push. Never open .env files or print secrets. Do not stop after one or two hours; when finished write docs/frontend-overhaul/FINAL_REPORT.md.
```

To resume after an interruption: **`/system-architect continue`** (it reads `PROGRESS.md` and carries on).

## In the morning
Read `PROGRESS.md` and `FINAL_REPORT.md`; `git log --oneline main..frontend-overhaul`; run the app and click through; skim `docs/backend-issues/README.md` for the new counts. If you are happy and want to publish the branch yourself:
`ALLOW_PUSH=1 git push origin frontend-overhaul` (the local guard blocks pushes unless you set that variable for one command). Nothing has been pushed by the agents or by Claude.

## Decisions already made (do not re-open them overnight)
- **D-F20** Adopt the teammate's Next.js 16 (JavaScript) app; the earlier Vite plan in `docs/frontend.md` section 1 is retired (keep the proxy, session and CSRF design).
- **D-F21** Nine workspace pages with tabs as path segments, drawers and dialogs, grouped navigation; old routes redirect.
- **D-F22** Neutral slate plus one cobalt primary, light and dark themes, tokens only; non-colour tokens added after the audit.
- **D-F23** A development-only demo sign-in exists (`/api/demo-login`); it is off in production builds and off unless the server environment enables it.
- **D-F24** The backend is frozen for this effort; problems are documented in `docs/backend-issues/`. Local hooks block pushes and out-of-scope commits.
- **D-F25** A sample-data (SIMULATED) mode for the Intelligence page is optional, off by default, never mixed with real rows.

## What was verified and what was not
Verified: all contrast numbers in `AUDIT_REPORT.md` (computed), the token file (31 pairs per theme, chart palette colour-blind checked), both servers running with the demo login, the 18 unit tests, the local guards (push blocked, backend commit blocked), the file locations used by the agent
(rules and workflows were written to `.agents/`). Not verified: how Antigravity discovers `.agents/` versus `.agent/` (sources disagree; both exist), the exact Antigravity settings names, that any workflow runs as written, the Playwright suite (it skips without credentials and needs Chrome), PostgreSQL behaviour, and any visual check of sections I did not open (the code audit covers them).
