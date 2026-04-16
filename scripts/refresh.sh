#!/usr/bin/env bash
# refresh.sh — bring this checkout up to date after working in a worktree
# or merging a PR on GitHub.
#
# What it does:
#   1. Fetches origin
#   2. Pulls (rebase) the current branch
#   3. Restores core.hooksPath if atdd init clobbered it
#   4. Reinstalls editable package (only if pyproject.toml changed)
#   5. Runs verify-after-sync.sh
#
# Usage:
#   scripts/refresh.sh              # from repo root
#   scripts/refresh.sh --skip-verify  # skip the verify step (quick mode)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
BRANCH="$(git branch --show-current)"
SKIP_VERIFY=false

for arg in "$@"; do
  case "$arg" in
    --skip-verify) SKIP_VERIFY=true ;;
    *) echo "unknown flag: $arg" >&2; exit 1 ;;
  esac
done

# --- preflight ---
if [[ -n "$(git status --porcelain)" ]]; then
  echo "warning: working tree is dirty — pull may conflict." >&2
  git status --short >&2
  echo ""
  read -rp "continue anyway? [y/N] " confirm
  [[ "$confirm" == "y" || "$confirm" == "Y" ]] || exit 1
fi

# --- 1. fetch ---
echo "==> fetching origin"
git fetch origin

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")"

if [[ -z "$REMOTE" ]]; then
  echo "==> no remote tracking branch origin/$BRANCH — skipping pull"
elif [[ "$LOCAL" == "$REMOTE" ]]; then
  echo "==> already up to date ($BRANCH @ $(git rev-parse --short HEAD))"
else
  BEHIND=$(git rev-list --count "HEAD..origin/$BRANCH")
  echo "==> pulling $BEHIND commit(s) from origin/$BRANCH"
  git pull --rebase origin "$BRANCH"
fi

# --- 2. restore hooksPath ---
EXPECTED_HOOKS_PATH=".git-hooks"
if [[ -d "$EXPECTED_HOOKS_PATH" ]]; then
  CURRENT="$(git config --get core.hooksPath || echo "")"
  if [[ "$CURRENT" != "$EXPECTED_HOOKS_PATH" ]]; then
    echo "==> restoring core.hooksPath: ${CURRENT:-<unset>} → $EXPECTED_HOOKS_PATH"
    git config core.hooksPath "$EXPECTED_HOOKS_PATH"
  fi
fi

# --- 3. reinstall if pyproject.toml changed ---
# Compare the installed version metadata against pyproject.toml's version.
PYPROJECT_VER=$(python3 -c "
try:
    import tomllib
except ImportError:
    import tomli as tomllib
print(tomllib.loads(open('pyproject.toml').read())['project']['version'])
" 2>/dev/null || echo "")
INSTALLED_VER=$(python3 -c "
from importlib.metadata import version
print(version('atdd'))
" 2>/dev/null || echo "")

if [[ -n "$PYPROJECT_VER" && "$PYPROJECT_VER" != "$INSTALLED_VER" ]]; then
  echo "==> version mismatch (pyproject: $PYPROJECT_VER, installed: $INSTALLED_VER)"
  echo "    reinstalling editable package..."
  pip install -e ".[dev]" --quiet
  echo "    atdd $(atdd --version 2>/dev/null || echo '???')"
else
  echo "==> editable install current ($INSTALLED_VER)"
fi

# --- 4. verify ---
if [[ "$SKIP_VERIFY" == "true" ]]; then
  echo "==> verify skipped (--skip-verify)"
else
  echo ""
  echo "==> running verify-after-sync.sh"
  echo ""
  bash scripts/verify-after-sync.sh
fi

echo ""
echo "==> refresh complete ($BRANCH @ $(git rev-parse --short HEAD))"
