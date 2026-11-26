#!/usr/bin/env bash
# One-time setup (owner runs it once). Local only: no push, no merge.
#   bash ecommerce/plan/tools/step-start.sh [--dry-run]
# Creates a git worktree ../bizora-storefront on a NEW local branch `storefront` (from `main`),
# copies this kit (ecommerce/plan) into it and commits the kit there as the branch's first commit.
# Antigravity is then opened on ../bizora-storefront/ecommerce . Your current folder is not touched.
set -eu
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PLAN=$(cd "$HERE/.." && pwd)
ROOT=$(git -C "$PLAN" rev-parse --show-toplevel)
REL=$(realpath --relative-to="$ROOT" "$PLAN")          # ecommerce/plan
WT="$(dirname "$ROOT")/$(basename "$ROOT")-storefront"
run() { echo "+ $*"; [ "$DRY" = 1 ] || "$@"; }

git -C "$ROOT" rev-parse --verify -q refs/heads/storefront >/dev/null && { echo "Branch 'storefront' already exists. Nothing done."; exit 1; }
[ -e "$WT" ] && { echo "$WT already exists. Nothing done."; exit 1; }
git -C "$ROOT" rev-parse --verify -q refs/heads/main >/dev/null || { echo "No local branch 'main'. Nothing done."; exit 1; }

run git -C "$ROOT" worktree add -b storefront "$WT" main
run mkdir -p "$WT/$(dirname "$REL")"
run cp -r "$PLAN" "$WT/$REL"
run git -C "$WT" add -- "$REL"
run git -C "$WT" commit -q -m "docs(storefront): add storefront planning kit"
echo
echo "Done. Open Antigravity on: $WT/$(dirname "$REL")"
echo "Then, in a NEW conversation for every card, paste:"
echo "  Open plan/RUN-NEXT.md, read it completely, and do exactly what it says."
