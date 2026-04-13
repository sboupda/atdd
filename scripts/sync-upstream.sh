#!/usr/bin/env bash
# sync-upstream.sh — pull upstream (afokapu/atdd) releases into this fork
# and rebase the diool customizations on top.
#
# Layout this script assumes:
#   main   → clean mirror of an upstream tag (no local changes)
#   diool  → your customizations, rebased on top of main
#
# Usage:
#   scripts/sync-upstream.sh v1.53.0          # pin to a tag
#   scripts/sync-upstream.sh upstream/main    # track head (risky)
#
# What it does:
#   1. Confirms upstream remote is configured
#   2. Fetches upstream with tags
#   3. Creates a timestamped safety branch
#   4. Fast-forwards main to the target ref
#   5. Rebases diool onto the new main
#   6. Prints next-step push commands (never auto-pushes)

set -euo pipefail

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  echo "usage: $0 <tag-or-ref>   e.g. $0 v1.53.0" >&2
  exit 1
fi

# --- preflight ---
if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "error: upstream remote not configured." >&2
  echo "  git remote add upstream https://github.com/afokapu/atdd.git" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "error: working tree is dirty. commit or stash first." >&2
  git status --short >&2
  exit 1
fi

# --- fetch ---
echo "==> fetching upstream with tags"
git fetch upstream --tags

# verify target exists
if ! git rev-parse --verify "$TARGET" >/dev/null 2>&1; then
  echo "error: $TARGET does not exist after fetch" >&2
  exit 1
fi

TARGET_SHA="$(git rev-parse "$TARGET")"
echo "==> target: $TARGET ($TARGET_SHA)"

# --- safety branch ---
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAFETY="pre-sync-$STAMP"
echo "==> creating safety branch: $SAFETY"
git branch "$SAFETY"

# --- main: fast-forward or reset to target ---
echo "==> checking out main"
git checkout main

CURRENT_MAIN="$(git rev-parse HEAD)"
if git merge-base --is-ancestor "$CURRENT_MAIN" "$TARGET_SHA"; then
  echo "==> fast-forwarding main to $TARGET"
  git merge --ff-only "$TARGET_SHA"
else
  echo "warning: main has commits not in $TARGET — using hard reset"
  echo "         (safety branch $SAFETY preserves the old state)"
  read -rp "proceed with 'git reset --hard $TARGET'? [y/N] " confirm
  [[ "$confirm" == "y" || "$confirm" == "Y" ]] || exit 1
  git reset --hard "$TARGET"
fi

# --- diool: rebase onto new main ---
if git show-ref --verify --quiet refs/heads/diool; then
  echo "==> rebasing diool onto updated main"
  git checkout diool
  if ! git rebase main; then
    echo ""
    echo "rebase hit conflicts. resolve them, then:"
    echo "  git rebase --continue"
    echo "or abort with:"
    echo "  git rebase --abort"
    echo "safety branch: $SAFETY"
    exit 1
  fi
else
  echo "note: no 'diool' branch found — skipping rebase"
fi

# --- done ---
echo ""
echo "==> sync complete"
echo "safety branch preserved: $SAFETY"
echo ""
echo "next steps (review before running):"
echo "  git log --oneline main -5"
echo "  git log --oneline diool -5"
echo ""
echo "to push:"
echo "  git push origin main --force-with-lease"
echo "  git push origin diool --force-with-lease"
echo ""
echo "to clean up safety branch after verifying everything works:"
echo "  git branch -D $SAFETY"
