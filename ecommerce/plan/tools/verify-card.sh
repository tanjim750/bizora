#!/usr/bin/env bash
# Independent check of ONE storefront card commit. Trusts nothing the agent wrote.
#   bash plan/tools/verify-card.sh <CARD-ID> <commit> [--full] [--no-tests]
# Run from anywhere inside the repository. Exit 0 = OK, 1 = a check failed, 2 = usage error.
#   --full      also run npm test, npm run typecheck and npm run lint on the card's commit
#   --no-tests  only the git checks (message, files, test file present)
set -u
ID=${1:-}; COMMIT=${2:-}; shift 2 2>/dev/null || true
FULL=0; NOTESTS=0
for a in "$@"; do case "$a" in --full) FULL=1;; --no-tests) NOTESTS=1;; *) echo "unknown option $a"; exit 2;; esac; done
[ -n "$ID" ] && [ -n "$COMMIT" ] || { sed -n 2,7p "$0"; exit 2; }

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ECOM=$(cd "$HERE/../.." && pwd)                       # the ecommerce/ folder
ROOT=$(git -C "$ECOM" rev-parse --show-toplevel) || exit 2
REL=$(realpath --relative-to="$ROOT" "$ECOM")          # e.g. "ecommerce" or "." if moved to its own repo
[ "$REL" = "." ] && PFX="" || PFX="$REL/"
FE="${PFX}frontend/"
FAIL=0
ok()  { echo "OK    $*"; }
bad() { echo "FAIL  $*"; FAIL=1; }

git -C "$ROOT" rev-parse --verify -q "$COMMIT^{commit}" >/dev/null || { echo "FAIL  commit $COMMIT not found"; exit 1; }
SHORT=$(git -C "$ROOT" rev-parse --short "$COMMIT")
MSG=$(git -C "$ROOT" log -1 --format=%B "$COMMIT")
echo "== $ID @ $SHORT: $(echo "$MSG" | head -1)"

# 1. Message
echo "$MSG" | head -1 | grep -q "($ID)\$" && ok "subject ends with ($ID)" || bad "subject does not end with ($ID)"
echo "$MSG" | grep -qiE 'co-authored-by|generated (with|by)|claude|gemini|antigravity|chatgpt|copilot|\bAI\b' \
  && bad "commit message has co-author or AI wording" || ok "no co-author / AI wording"

# 2. Files
FILES=$(git -C "$ROOT" diff-tree --no-commit-id --name-only -r "$COMMIT")
[ -n "$FILES" ] || bad "commit changes no files"
OUTSIDE=$(echo "$FILES" | grep -v "^${FE}" || true)
[ -z "$OUTSIDE" ] && ok "all files under ${FE}" || bad "files outside ${FE}: $(echo $OUTSIDE)"
if [ "$ID" != "SF-01" ]; then
  echo "$FILES" | grep -qE "^${FE}(package\.json|package-lock\.json)$" && bad "package.json or lockfile changed (only SF-01 may)" || ok "no dependency change"
fi
LOWER=$(echo "$ID" | tr 'A-Z' 'a-z')
TESTS=$(echo "$FILES" | grep -E "^${FE}tests/(unit|e2e|contract)/" | grep -E "(${LOWER}-|/e2e/|/contract/)" || true)
UNIT_TESTS=$(echo "$TESTS" | grep -E "^${FE}tests/unit/${LOWER}-.*\.test\.tsx?$" || true)
case "$ID" in
  IMG-01) ok "asset card: no test file expected";;
  SF-32|SF-33|SF-34) [ -n "$TESTS" ] && ok "test files: $(echo $TESTS)" || bad "no e2e/contract test file in commit";;
  *) [ -n "$UNIT_TESTS" ] && ok "unit test files: $(echo $UNIT_TESTS)" || bad "no tests/unit/${LOWER}-*.test.ts(x) in commit";;
esac
# token guard on the files of this commit (source only)
SRC=$(echo "$FILES" | grep -E "^${FE}src/.*\.(ts|tsx|css)$" | grep -v "src/styles/tokens.css" || true)
HEXHITS=""
for f in $SRC; do
  if git -C "$ROOT" cat-file -e "$COMMIT:$f" 2>/dev/null; then
    h=$(git -C "$ROOT" show "$COMMIT:$f" | grep -nE '#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(' || true)
    [ -n "$h" ] && HEXHITS="$HEXHITS $f"
  fi
done
[ -z "$HEXHITS" ] && ok "no raw colours in changed source" || bad "raw colour values in:$HEXHITS"

[ "$NOTESTS" = 1 ] && { echo "== git checks only"; [ $FAIL = 0 ] && echo "RESULT: OK" || echo "RESULT: FAIL"; exit $FAIL; }

# 3. Red on parent, green on commit (unit test cards only)
NM="$ECOM/frontend/node_modules"
[ -d "$NM" ] || { bad "no node_modules in $ECOM/frontend (run npm install there first)"; echo "RESULT: FAIL"; exit 1; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/sf-verify-XXXXXX")
cleanup() { git -C "$ROOT" worktree remove --force "$TMP/green" >/dev/null 2>&1; git -C "$ROOT" worktree remove --force "$TMP/red" >/dev/null 2>&1; rm -rf "$TMP"; }
trap cleanup EXIT
git -C "$ROOT" worktree add --detach -q "$TMP/green" "$COMMIT" || { bad "cannot create worktree"; exit 1; }
ln -s "$NM" "$TMP/green/${FE}node_modules"
if [ -n "$UNIT_TESTS" ] && [ "$ID" != "SF-01" ]; then
  REL_TESTS=$(echo "$UNIT_TESTS" | sed "s#^${FE}##")
  git -C "$ROOT" worktree add --detach -q "$TMP/red" "$COMMIT^" || { bad "cannot create parent worktree"; exit 1; }
  if [ -d "$TMP/red/${FE}" ]; then
    ln -s "$NM" "$TMP/red/${FE}node_modules"
    for t in $REL_TESTS; do mkdir -p "$TMP/red/${FE}$(dirname "$t")"; cp "$TMP/green/${FE}$t" "$TMP/red/${FE}$t"; done
    if (cd "$TMP/red/${FE}" && npx vitest run $REL_TESTS >"$TMP/red.log" 2>&1); then
      bad "RED: the card's test PASSES on the parent commit (it does not prove the feature)"; tail -5 "$TMP/red.log"
    else ok "RED on parent: $(grep -E 'Tests|FAIL|Error' "$TMP/red.log" | tail -1)"; fi
  else bad "parent commit has no ${FE} (cannot do the red check)"; fi
  if (cd "$TMP/green/${FE}" && npx vitest run $REL_TESTS >"$TMP/green.log" 2>&1); then
    ok "GREEN on commit: $(grep -E 'Tests' "$TMP/green.log" | tail -1)"
  else bad "the card's test FAILS on its own commit"; tail -15 "$TMP/green.log"; fi
fi
if [ "$FULL" = 1 ]; then
  for cmd in "npm test" "npm run typecheck" "npm run lint"; do
    if (cd "$TMP/green/${FE}" && $cmd >"$TMP/full.log" 2>&1); then ok "$cmd"; else bad "$cmd"; tail -15 "$TMP/full.log"; fi
  done
fi
echo "== done"; [ $FAIL = 0 ] && echo "RESULT: OK" || echo "RESULT: FAIL"
exit $FAIL
