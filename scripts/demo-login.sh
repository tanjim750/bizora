#!/usr/bin/env bash
# One-command local demo login for every teammate. Nothing secret is stored in git.
#
#   bash scripts/demo-login.sh setup    creates YOUR local demo user and demo data, writes frontend/.env.local
#   bash scripts/demo-login.sh run      starts the Django backend with the same local settings
#
# Then, in a second terminal:  cd frontend && npm install && npm run dev
# Open http://localhost:3000/login and click "Continue as demo owner" (it only exists on your own machine,
# in development, with a backend on this machine).
#
# What setup does (idempotent, safe to run again):
#   1. uses an isolated SQLite database outside the repository (default folder ~/.bizora-dev-data)
#   2. applies the migrations
#   3. creates or updates the local user "demo-owner" with a RANDOM password (kept only in your frontend/.env.local)
#   4. runs the existing demo_completion command so that user owns a demo business with data
#   5. writes the four BIZORA_DEMO_* / DJANGO_API_ORIGIN lines into frontend/.env.local (a git-ignored file)
# Needs: the Python virtualenv of the project active (pip install -r requirements.txt), or set BIZORA_PY=/path/to/python.
# Overrides: BIZORA_DATA_DIR, BIZORA_DEMO_USERNAME, BIZORA_FRONTEND_ENV_FILE (the file to write).
set -eu

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
[ -f manage.py ] || { echo "STOP: run this from the repository (manage.py not found in $ROOT)"; exit 1; }

PY=${BIZORA_PY:-python}
command -v "$PY" > /dev/null 2>&1 || PY=python3
"$PY" -c 'import django, rest_framework' 2> /dev/null || {
  echo "STOP: Django is not installed for $PY. Activate the project virtualenv and run: pip install -r requirements.txt"
  exit 1
}

export DJANGO_SETTINGS_MODULE=bizora.local_settings
export BIZORA_DATA_DIR=${BIZORA_DATA_DIR:-$HOME/.bizora-dev-data}
mkdir -p "$BIZORA_DATA_DIR"
USERNAME=${BIZORA_DEMO_USERNAME:-demo-owner}
ENV_FILE=${BIZORA_FRONTEND_ENV_FILE:-$ROOT/frontend/.env.local}

case "${1:-}" in
  run)
    echo "Backend on http://127.0.0.1:8000 using the data folder $BIZORA_DATA_DIR"
    exec "$PY" manage.py runserver 127.0.0.1:8000
    ;;
  setup)
    ;;
  *)
    sed -n 2,6p "$0"
    exit 2
    ;;
esac

echo "== 1/4 database in $BIZORA_DATA_DIR"
"$PY" manage.py migrate --noinput > /dev/null
echo "done"

# Reuse the password from an earlier run so that nothing changes when you run setup again.
PASSWORD=""
if [ -f "$ENV_FILE" ]; then
  PASSWORD=$(sed -n 's/^BIZORA_DEMO_PASSWORD=//p' "$ENV_FILE" | head -n 1)
fi
if [ -z "$PASSWORD" ]; then
  PASSWORD=$("$PY" -c 'import secrets; print(secrets.token_urlsafe(18))')
fi

echo "== 2/4 local user $USERNAME"
DEMO_USER="$USERNAME" DEMO_PASS="$PASSWORD" "$PY" manage.py shell -c "
import os
from django.contrib.auth import get_user_model
U = get_user_model()
u, created = U.objects.get_or_create(username=os.environ['DEMO_USER'])
u.set_password(os.environ['DEMO_PASS'])
u.is_active = True
u.is_staff = True
u.is_superuser = True
u.save()
print('created' if created else 'updated')
"

echo "== 3/4 demo business and data (the existing demo_completion command)"
"$PY" manage.py demo_completion --username "$USERNAME" > /dev/null
echo "done"

echo "== 4/4 frontend login settings in $ENV_FILE"
mkdir -p "$(dirname "$ENV_FILE")"
[ -f "$ENV_FILE" ] || : > "$ENV_FILE"
for pair in "BIZORA_DEMO_LOGIN=1" "BIZORA_DEMO_USERNAME=$USERNAME" "BIZORA_DEMO_PASSWORD=$PASSWORD" "DJANGO_API_ORIGIN=http://127.0.0.1:8000"; do
  key=${pair%%=*}
  grep -v "^${key}=" "$ENV_FILE" > "$ENV_FILE.tmp" || true
  printf '%s\n' "$pair" >> "$ENV_FILE.tmp"
  mv "$ENV_FILE.tmp" "$ENV_FILE"
done
chmod 600 "$ENV_FILE" 2> /dev/null || true
echo "done (the password is only in that file; never commit it)"

echo
echo "Ready. Next:"
echo "  1) terminal 1:  bash scripts/demo-login.sh run"
echo "  2) terminal 2:  cd frontend && npm install && npm run dev"
echo "  3) open http://localhost:3000/login and click \"Continue as demo owner\""
