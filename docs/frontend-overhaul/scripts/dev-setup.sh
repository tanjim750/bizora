#!/usr/bin/env bash
# One-time (idempotent) local setup: venv outside the repo, throwaway SQLite database outside the repo, demo owner, demo data.
# The tracked db.sqlite3 is never used. The generated login is written to a git-ignored file; this script prints no secret.
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VENV="${BIZORA_VENV:-$HOME/.cache/bizora-venv}"
D="${BIZORA_DEV_DATA:-/tmp/bizora-dev-data}"
LOGIN="${BIZORA_DEV_LOGIN_FILE:-$R/.claude/memory/frontend-work/dev_login.txt}"
export PYTHONDONTWRITEBYTECODE=1
if [ ! -x "$VENV/bin/python" ]; then python3.12 -m venv "$VENV" 2>/dev/null || python3 -m venv "$VENV"; "$VENV/bin/pip" install -q -r "$R/requirements.txt"; fi
mkdir -p "$D" "$(dirname "$LOGIN")"; chmod 700 "$D"
[ -f "$D/secret_key" ] || python3 -c 'import secrets;print(secrets.token_urlsafe(48))' > "$D/secret_key"; chmod 600 "$D/secret_key"
export DJANGO_SETTINGS_MODULE=bizora.local_settings BIZORA_DATA_DIR="$D" BIZORA_DATABASE=sqlite DEBUG=True DJANGO_SECRET_KEY="$(cat "$D/secret_key")"
cd "$R"
"$VENV/bin/python" manage.py migrate --noinput | tail -1
if [ ! -f "$D/.seeded" ]; then
  PW="$(python3 -c 'import secrets;print(secrets.token_urlsafe(18))')"
  DJANGO_SUPERUSER_PASSWORD="$PW" "$VENV/bin/python" manage.py createsuperuser --noinput --username demo-owner --email demo-owner@example.test >/dev/null
  ( umask 077; printf 'LOCAL DEV LOGIN (throwaway database in %s, git-ignored)\nusername: demo-owner\npassword: %s\n' "$D" "$PW" > "$LOGIN" )
  "$VENV/bin/python" manage.py demo_completion --username demo-owner | tail -3
  touch "$D/.seeded"
fi
echo "setup OK (login file: $LOGIN)"
