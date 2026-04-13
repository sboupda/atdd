#!/usr/bin/env bash
# install-hooks.sh — point this repo's git hooks at .git-hooks/
#
# Run once per clone. Safe to re-run (idempotent).
#
#   scripts/install-hooks.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if [[ ! -d .git-hooks ]]; then
  echo "error: .git-hooks/ directory not found" >&2
  exit 1
fi

chmod +x .git-hooks/*
git config core.hooksPath .git-hooks

echo "hooks installed from .git-hooks/:"
ls -1 .git-hooks/ | sed 's/^/  - /'
echo ""
echo "current core.hooksPath: $(git config core.hooksPath)"
