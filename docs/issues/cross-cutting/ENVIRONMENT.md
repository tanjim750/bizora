# Environment notes for the next agent (Codex or Antigravity)

## Where things are

| What | Where |
|---|---|
| Main checkout (Antigravity frontend overhaul runs here, branch `frontend-overhaul`) | `/home/hamza/Documents/UniverSity/bizora` |
| Backend work worktree, branch `bi-graph-integration` (cut from `main` 8010daa) | `/home/hamza/Documents/UniverSity/bizora/.claude/worktrees/nervous-napier-7881a5` |
| This folder (git-ignored, never pushed) | `agent-handoff/` in that worktree, copy in `/home/hamza/.config/Claude/side-session-notes/local_4b8f41c6-801e-44f7-a2d2-1b87434481c3/agent-handoff/` |
| Dev SQLite database used by the dev server on :8000 | `/tmp/bizora-dev-data/development.sqlite3` (lives in `/tmp`; gone after a reboot, recreate with `docs/frontend-overhaul/scripts/dev-setup.sh` then `python manage.py demo_completion --username demo-owner`) |
| Backup of that database taken before BI/Graph data was added | `/home/hamza/.config/Claude/side-session-notes/local_4b8f41c6-801e-44f7-a2d2-1b87434481c3/dev-db-backup-before-bi-seed-2026-11-10.sqlite3` |
| Issue reports written by the frontend agent (live only on `frontend-overhaul`, not on `main`) | `docs/backend-issues/*.md`, `docs/frontend-api-reference.md` (read with `git show frontend-overhaul:docs/backend-issues/business-intelligence.md`) |

Rules that apply to every agent: never push (a pre-push hook blocks it), never switch branches in the main checkout, never commit `.env*`, `*.sqlite3`, logs or this folder, Conventional Commits, Python 3.12, Django 4.2, DRF 3.15, PostgreSQL 16 is authoritative (SQLite is a local fallback only), AI never creates authoritative records without approval. Ask before any migration or change to the authorization model or URL prefixes.

## Python environment (known trap)

`~/.cache/bizora-venv` was created with Python 3.15 (`pyvenv.cfg`), its packages sit in `lib/python3.15/site-packages`. The system `python3` here is 3.12.3, so that venv cannot import Django from a 3.12 shell. The running dev server works because the host sees a 3.15 interpreter. Make a real 3.12 venv:

```bash
python3.12 -m venv ~/.cache/bizora-venv312
~/.cache/bizora-venv312/bin/pip install -r requirements.txt
```

Test and run environment (never the tracked `db.sqlite3`):

```bash
export DJANGO_SETTINGS_MODULE=bizora.local_settings BIZORA_DATABASE=sqlite
export BIZORA_DATA_DIR=$(mktemp -d) DJANGO_SECRET_KEY=local-test-key-not-secret PYTHONDONTWRITEBYTECODE=1
~/.cache/bizora-venv312/bin/python manage.py check
~/.cache/bizora-venv312/bin/python manage.py makemigrations --check --dry-run
~/.cache/bizora-venv312/bin/python manage.py test --noinput          # about 8 minutes, 1377 tests
~/.cache/bizora-venv312/bin/python manage.py test app.business_intelligence app.business_graph app.tests --noinput
```

## Seeding and running the intelligence pipeline

```bash
python manage.py run_intelligence --slug bizora-domains-demo            # every UTC month that holds records, then graph rebuild
python manage.py run_intelligence --business-id 1 --current-month --no-graph
python manage.py run_intelligence --slug bizora-domains-demo --from 2026-10-01 --to 2026-11-01
```

`demo_domains` and `demo_completion` now call it at the end. It is idempotent. After the run on 2026-11-10 the dev database holds 42 metric registry rows, 27 snapshots and facts (with 27 fact evidence rows), 1 issue (2 evidence rows), 13 business relationships, 11 graph nodes and 13 graph edges for business 1.

The dev server on `:8000` runs the main checkout, which has no BI/Graph routes until `bi-graph-integration` is merged and the server restarted. To try the branch now, run its own server (`python manage.py runserver 127.0.0.1:8001 --noreload` with the same environment variables and `BIZORA_DATA_DIR=/tmp/bizora-dev-data`) and log in as `demo-owner` (password is in `.claude/memory/frontend-work/dev_login.txt` of the main checkout, git-ignored).
