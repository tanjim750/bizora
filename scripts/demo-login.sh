#!/usr/bin/env bash
# Local demo for every teammate: one command, nothing secret stored in git.
#
#   bash scripts/demo-login.sh start    does everything below, then runs backend and frontend (Ctrl+C stops both)
#   bash scripts/demo-login.sh setup    only the one-time setup (no servers)
#   bash scripts/demo-login.sh run      only the Django backend
#
# After "start", open http://localhost:3000/login and click "Continue as demo owner".
# That button exists only on your own machine, in development, with the backend on this machine.
#
# What it does (idempotent, safe to run again):
#   1. makes a Python virtualenv in .venv and installs requirements.txt (only if Django is missing)
#   2. uses an isolated SQLite database outside the repository (default folder ~/.bizora-dev-data), applies migrations
#   3. creates or updates the local user "demo-owner" with a RANDOM password and loads the demo business
#      (python manage.py create_demo_user --with-demo-data)
#   4. writes the demo settings into frontend/.env.local (git-ignored; the password lives only there)
#   5. runs npm install in frontend/ if node_modules is missing
# Overrides: BIZORA_PY, BIZORA_DATA_DIR, BIZORA_DEMO_USERNAME, BIZORA_BACKEND_PORT (8000), BIZORA_FRONTEND_PORT (3000),
# BIZORA_FRONTEND_ENV_FILE (the file to write).
set -eu

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
[ -f manage.py ] || { echo "STOP: run this from the repository (manage.py not found in $ROOT)"; exit 1; }

ACTION=${1:-}
case "$ACTION" in start | setup | run) ;; *) sed -n 2,6p "$0"; exit 2 ;; esac

BACKEND_PORT=${BIZORA_BACKEND_PORT:-8000}
FRONTEND_PORT=${BIZORA_FRONTEND_PORT:-3000}
USERNAME=${BIZORA_DEMO_USERNAME:-demo-owner}
ENV_FILE=${BIZORA_FRONTEND_ENV_FILE:-$ROOT/frontend/.env.local}
export DJANGO_SETTINGS_MODULE=bizora.local_settings
export BIZORA_DATA_DIR=${BIZORA_DATA_DIR:-$HOME/.bizora-dev-data}
mkdir -p "$BIZORA_DATA_DIR"

port_busy() { (echo > "/dev/tcp/127.0.0.1/$1") > /dev/null 2>&1; }

# ---------- Python ----------
if [ -n "${BIZORA_PY:-}" ]; then
  PY=$BIZORA_PY
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY=$ROOT/.venv/bin/python
else
  BASE_PY=""
  for candidate in python3.12 python3 python; do
    if command -v "$candidate" > /dev/null 2>&1; then BASE_PY=$candidate; break; fi
  done
  [ -n "$BASE_PY" ] || { echo "STOP: Python is not installed. Install Python 3.12 and run this again."; exit 1; }
  echo "== creating the virtualenv .venv with $($BASE_PY --version 2>&1)"
  "$BASE_PY" -m venv "$ROOT/.venv" || { echo "STOP: could not create .venv. Install the python3-venv package and run this again."; exit 1; }
  PY=$ROOT/.venv/bin/python
fi
if ! "$PY" -c 'import django, rest_framework' > /dev/null 2>&1; then
  echo "== installing the Python requirements (first time only, a few minutes)"
  "$PY" -m pip install --quiet -r requirements.txt || {
    echo "STOP: pip install failed. The project is developed with Python 3.12: install it and run this again."
    exit 1
  }
fi

if [ "$ACTION" = run ]; then
  port_busy "$BACKEND_PORT" && { echo "STOP: port $BACKEND_PORT is busy. Set BIZORA_BACKEND_PORT to another port."; exit 1; }
  echo "Backend on http://127.0.0.1:$BACKEND_PORT using the data folder $BIZORA_DATA_DIR"
  exec "$PY" manage.py runserver "127.0.0.1:$BACKEND_PORT"
fi

# ---------- setup ----------
echo "== 1/3 database in $BIZORA_DATA_DIR"
"$PY" manage.py migrate --noinput > /dev/null
echo "done"

# Reuse the password of an earlier run so that nothing changes when you run this again.
PASSWORD=""
if [ -f "$ENV_FILE" ]; then
  PASSWORD=$(sed -n 's/^BIZORA_DEMO_PASSWORD=//p' "$ENV_FILE" | head -n 1)
fi
if [ -z "$PASSWORD" ]; then
  PASSWORD=$("$PY" -c 'import secrets; print(secrets.token_urlsafe(18))')
fi

echo "== 2/3 local user $USERNAME and the demo business"
BIZORA_DEMO_PASSWORD="$PASSWORD" "$PY" manage.py create_demo_user --username "$USERNAME" --with-demo-data > /dev/null
echo "done"

echo "== 3/3 frontend login settings in $ENV_FILE"
mkdir -p "$(dirname "$ENV_FILE")"
[ -f "$ENV_FILE" ] || : > "$ENV_FILE"
for pair in "BIZORA_DEMO_LOGIN=1" "BIZORA_DEMO_USERNAME=$USERNAME" "BIZORA_DEMO_PASSWORD=$PASSWORD" "DJANGO_API_ORIGIN=http://127.0.0.1:$BACKEND_PORT"; do
  key=${pair%%=*}
  grep -v "^${key}=" "$ENV_FILE" > "$ENV_FILE.tmp" || true
  printf '%s\n' "$pair" >> "$ENV_FILE.tmp"
  mv "$ENV_FILE.tmp" "$ENV_FILE"
done
chmod 600 "$ENV_FILE" 2> /dev/null || true
echo "done (the password is only in that file; never commit it)"

if [ "$ACTION" = setup ]; then
  echo
  echo "Ready. Start everything with:  bash scripts/demo-login.sh start"
  exit 0
fi

# ---------- start: frontend dependencies, backend in the background, frontend in the foreground ----------
command -v npm > /dev/null 2>&1 || { echo "STOP: Node.js is not installed. Install Node.js 20 or newer (https://nodejs.org) and run this again."; exit 1; }
if [ ! -d frontend/node_modules ]; then
  echo "== installing the frontend packages (first time only, a few minutes)"
  (cd frontend && npm install --no-audit --no-fund) || { echo "STOP: npm install failed."; exit 1; }
fi
port_busy "$BACKEND_PORT" && { echo "STOP: port $BACKEND_PORT is busy. Set BIZORA_BACKEND_PORT to another port."; exit 1; }
port_busy "$FRONTEND_PORT" && { echo "STOP: port $FRONTEND_PORT is busy. Set BIZORA_FRONTEND_PORT to another port."; exit 1; }

LOG="$BIZORA_DATA_DIR/backend.log"
"$PY" manage.py runserver "127.0.0.1:$BACKEND_PORT" --noreload > "$LOG" 2>&1 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2> /dev/null || true' EXIT
trap 'exit 130' INT TERM
echo "== waiting for the backend on port $BACKEND_PORT (log: $LOG)"
READY=0
for _ in $(seq 1 60); do
  kill -0 "$BACKEND_PID" 2> /dev/null || { echo "STOP: the backend stopped. Last lines of $LOG:"; tail -n 15 "$LOG"; exit 1; }
  if port_busy "$BACKEND_PORT"; then READY=1; break; fi
  sleep 1
done
[ "$READY" = 1 ] || { echo "STOP: the backend did not start within 60 seconds. See $LOG"; exit 1; }
echo
echo "Backend is up. Open  http://localhost:$FRONTEND_PORT/login  and click \"Continue as demo owner\"."
echo "Press Ctrl+C to stop both servers."
echo
cd frontend
npm run dev -- -p "$FRONTEND_PORT"
