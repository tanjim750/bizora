#!/usr/bin/env bash
# Runs the Next.js dev server on 127.0.0.1:3000 (foreground) with the development-only demo sign-in enabled.
# The demo password is read from the git-ignored login file and handed to the server process only.
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGIN="${BIZORA_DEV_LOGIN_FILE:-$R/.claude/memory/frontend-work/dev_login.txt}"
[ -f "$LOGIN" ] || { echo "Run docs/frontend-overhaul/scripts/dev-setup.sh first." >&2; exit 1; }
cd "$R/frontend"
[ -d node_modules ] || npm ci --no-audit --no-fund
export DJANGO_API_ORIGIN=http://127.0.0.1:8000 BIZORA_DEMO_LOGIN=1 BIZORA_DEMO_USERNAME=demo-owner
BIZORA_DEMO_PASSWORD="$(sed -n 's/^password: //p' "$LOGIN")"; export BIZORA_DEMO_PASSWORD
exec npm run dev -- -p 3000 -H 127.0.0.1
