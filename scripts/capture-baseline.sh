#!/usr/bin/env bash
# capture-baseline.sh — snapshot framework state into baselines/ so future syncs
# can diff against a known-good reference point.
#
# Usage:
#   scripts/capture-baseline.sh          # writes baselines/current.txt
#   scripts/capture-baseline.sh v1.53.0  # writes baselines/v1.53.0.txt
#
# Captures:
#   - atdd --version
#   - atdd gate output
#   - atdd validate --quick output
#   - atdd inventory output
#   - atdd status output
#
# Commit the baseline on `diool` so a future sync can run:
#   diff baselines/v1.53.0.txt <(scripts/capture-baseline.sh -)
# and surface behavioral drift that pure code diffs would miss.

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

LABEL="${1:-current}"

if ! command -v atdd >/dev/null 2>&1; then
  echo "error: atdd CLI not on PATH" >&2
  exit 1
fi

if [[ "$LABEL" == "-" ]]; then
  OUT=/dev/stdout
else
  mkdir -p baselines
  OUT="baselines/$LABEL.txt"
fi

{
  echo "# atdd baseline: $LABEL"
  echo "# captured: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# git HEAD: $(git rev-parse HEAD)"
  echo "# branch:   $(git rev-parse --abbrev-ref HEAD)"
  echo ""
  echo "=== atdd --version ==="
  atdd --version 2>&1 || echo "(failed)"
  echo ""
  echo "=== atdd gate ==="
  atdd gate 2>&1 || echo "(failed)"
  echo ""
  echo "=== atdd validate --quick ==="
  atdd validate --quick 2>&1 || echo "(failed)"
  echo ""
  echo "=== atdd inventory ==="
  atdd inventory 2>&1 || echo "(failed)"
  echo ""
  echo "=== atdd status ==="
  atdd status 2>&1 || echo "(failed)"
} | sed 's/[[:space:]]*$//' > "$OUT"
# strip trailing whitespace so captured pytest output doesn't trip
# hooks or diff tooling later

if [[ "$OUT" != "/dev/stdout" ]]; then
  echo "baseline written: $OUT"
  echo ""
  echo "next steps:"
  echo "  git add $OUT"
  echo "  git commit -m \"chore: baseline snapshot for $LABEL\""
fi
