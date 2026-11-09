#!/usr/bin/env bash
# Runs Django for local development on 127.0.0.1:8000 (foreground). Run dev-setup.sh once first.
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VENV="${BIZORA_VENV:-$HOME/.cache/bizora-venv}"
D="${BIZORA_DEV_DATA:-/tmp/bizora-dev-data}"
[ -f "$D/secret_key" ] || { echo "Run docs/frontend-overhaul/scripts/dev-setup.sh first." >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1 DJANGO_SETTINGS_MODULE=bizora.local_settings BIZORA_DATA_DIR="$D" BIZORA_DATABASE=sqlite DEBUG=True DJANGO_SECRET_KEY="$(cat "$D/secret_key")"
cd "$R"
exec "$VENV/bin/python" manage.py runserver 127.0.0.1:8000 --noreload
