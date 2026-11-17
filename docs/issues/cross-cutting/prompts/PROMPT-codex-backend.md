# Prompt for Codex (backend fixer). Copy everything below the line.

---

You are fixing backend defects in the Bizora Django project. Work in a NEW git worktree of the repository, not in the main checkout, and never push.

## Read first, in this order
1. `AGENTS.md` (repo rules: Conventional Commits, Python 3.12, Django 4.2, DRF 3.15, PostgreSQL 16 authoritative).
2. `docs/issues/cross-cutting/ENVIRONMENT.md` (venv trap, test environment, branches).
3. `docs/issues/cross-cutting/AUDIT.md`, then the per-domain file in `docs/issues/backend/` (evidence in `docs/issues/cross-cutting/audit-*.md`).
4. The specs: `docs/implementations/features/business-intelligence.md`, `business-graph.md`, `business-data.md`, `ai-intelligence.md`, `business-memory-knowledge.md`, `overview-monitoring.md`, and `docs/requirements/SRS.md`.
5. Branch `bi-graph-integration` already contains related work; its current state and what it changed are listed in `AUDIT.md`. Start your branch from it.

## Hard rules (owner's instructions)
- Do ONLY what the project docs specify. Fix items tagged SPEC-DEFECT in the audit. Do NOT implement SPEC-GAP items (docs silent): collect them in a file `docs/issues/QUESTIONS.md` for the owner and stop on them. INTEGRATION items: do not change the frontend; only change the backend when the item says it is a backend defect.
- No new endpoints, models, migrations, response fields, roles or features. A schema change (including indexes and constraints) needs the owner's approval first: ask, do not do.
- Do not touch `frontend/**`. Do not touch API keys, provider setup or `.env*` (a senior provides those).
- Never push; commit locally in small Conventional Commits; one concern per commit; every fix ships with a regression test that fails before and passes after.
- Gates before each commit: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, the tests of the touched apps. Run the full suite before you finish.
- Never invent data or numbers; where a calculation has no documented rule, say so in QUESTIONS.md.

## Work order
P0 list in `AUDIT.md` (items that are SPEC-DEFECT only), then P1. For each item: reproduce first with a failing test, fix the root cause minimally, rerun the gates, commit with the audit id in the message (for example `fix(graph): keep website-event nodes stable on rebuild (BGA-01)`).

Start with: BGA-01, BGA-02, BGA-03, BGA-04, BIA-04, then AIS-01 and AIS-02 (confirm the role decision for approvals first), then the global exception handler for oversized integers (DOM-03, BIA-12, BGA-15).

## Final report
A table: change, audit id and doc section that requires it, test that proves it; a list of items you skipped as SPEC-GAP with the question for the owner; the commit list.
