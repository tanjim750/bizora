# Bizora backend

Django/DRF backend for canonical business data, deterministic identity resolution and
business operations. See the [implementation report](docs/implementations/my-domains-implementation-report.md)
for the complete 31-group / 298-subfeature checklist, limitations, APIs and test evidence.
The as-built [Software Requirements Specification](docs/requirements/SRS.md) and
[Use Case Specification](docs/requirements/USE_CASES.md) describe the current product scope,
reachable interfaces, actor permissions, workflows, and known integration gaps.
This increment includes a replaceable Django operational UI at `/ops/` for all thirteen
operations groups. Provider transport requires owner adapters; the BI, Graph, Configuration,
Observability, and expanded Overview URL modules are present but are not mounted in the root URL map.
The dedicated [Next.js frontend](frontend/README.md) uses the mounted Django APIs and the
[Clean Teal design system](docs/requirements/DESIGN.md). Its [progress ledger](docs/implementations/frontend-progress.md)
records endpoint coverage and unfinished screens.
For a fresh Linux server, see the [VPS installation review](docs/setup/vps.md).
See the [team-lead handoff](docs/implementations/TEAM_LEAD_HANDOFF.md) and
[versioned contracts](docs/implementations/contracts/README.md) before integration.

## Isolated local setup

The checked-in `db.sqlite3` has an incompatible legacy schema. Do not migrate or replace it.
The local settings below use a separate database outside the repository.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=bizora.local_settings
export BIZORA_DATA_DIR="$(mktemp -d /tmp/bizora-demo-XXXXXX)"
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python manage.py migrate --noinput
python manage.py createsuperuser --username demo-owner
python manage.py demo_completion --username demo-owner
python manage.py runserver 127.0.0.1:8000
```

The demo prints the business/customer IDs for authenticated API requests. The public status
endpoint remains `/api/`; business endpoints require explicit membership. Use the same
`BIZORA_DATA_DIR` and secret when restarting the local server.
Open `http://127.0.0.1:8000/ops/`, sign in with the demo user and select the business.

## Demo login for every teammate (frontend)

There is no shared username or password: the users live in each person's own local database, which is not in git.
One command prepares everything and starts both servers (Python 3.12 and Node.js 20 or newer must be installed):

```bash
bash scripts/demo-login.sh start
```

The first run creates the Python virtualenv `.venv`, installs the requirements and the frontend packages, creates the
local user `demo-owner` with a random password, loads the demo business and writes the demo settings into
`frontend/.env.local` (git-ignored, never commit it). Then it runs the backend and the frontend. When it says the backend
is up, open `http://localhost:3000/login` and click "Continue as demo owner". Ctrl+C stops both servers.

Other forms: `bash scripts/demo-login.sh setup` (only the one-time setup) and `bash scripts/demo-login.sh run` (only the
backend). The user is created by the new management command, which you can also run yourself in an isolated local
database (it refuses the tracked `db.sqlite3` and any non-SQLite database):

```bash
python manage.py create_demo_user --username demo-owner --with-demo-data
```

The button exists only in a development build, with the backend on your own machine. Running the script again is safe
(same password, nothing duplicated). The data lives in `~/.bizora-dev-data` (change it with `BIZORA_DATA_DIR`; ports with
`BIZORA_BACKEND_PORT` and `BIZORA_FRONTEND_PORT`).

## Verification

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
python scripts/verify_domains_postgres.py
```

The PostgreSQL verifier requires Docker. It uses a newly created local PostgreSQL 16/pgvector
container, tmpfs data, random credentials and a random localhost port, then removes only
its own temporary container. It includes real concurrent replay/refund, product/variant deduplication
and identity lifecycle tests. The regular Compose setup uses a persistent volume and installs
the vector extension through Django's initial migration.

Domain requirements are in [docs/implementations/domain.md](docs/implementations/domain.md)
and [docs/implementations/features/](docs/implementations/features/).
The [298-requirement audit](docs/implementations/my-domains-requirements-audit.md) distinguishes
full documented behavior from backend contracts and remaining external dependencies. Rebuild
the reviewed inventory with `python scripts/audit_domain_requirements.py`; this validates
evidence symbols and does not infer completion from passing tests.
