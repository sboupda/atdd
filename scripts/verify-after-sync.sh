#!/usr/bin/env bash
# verify-after-sync.sh — smoke-check the fork after pulling an upstream release.
# Run this from the diool branch after sync-upstream.sh completes.
#
# Usage:
#   scripts/verify-after-sync.sh
#
# Behavior:
#   - Hard-fails immediately on YAML errors or unresolved conflict markers
#     (these mask all downstream checks, so fix them first).
#   - Continues through soft checks (CLI, conventions) reporting pass/fail/warn.
#
# Exit codes:
#   0  all checks passed
#   1  soft-check failures
#   2  hard-fail: config invalid or conflict markers present

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
WARN=0

pass()  { echo "  [PASS] $1";   PASS=$((PASS+1)); }
fail()  { echo "  [FAIL] $1";   FAIL=$((FAIL+1)); }
warn()  { echo "  [WARN] $1";   WARN=$((WARN+1)); }
info()  { echo "  [INFO] $1"; }
die()   { echo "  [HARD-FAIL] $1" >&2; exit 2; }

# ============================================================================
# HARD CHECKS — bail immediately, nothing else matters until these pass
# ============================================================================

echo "=== 0a. conflict markers (repo-wide) ==="
# Look for unresolved merge conflict markers in tracked files.
# Using git grep so we respect .gitignore and skip binary/vendored content.
if git grep -nE '^(<{7}|={7}|>{7})( |$)' -- ':!scripts/verify-after-sync.sh' ':!.git-hooks/' 2>/dev/null; then
  die "unresolved conflict markers found above. resolve them before continuing."
else
  pass "no conflict markers in tracked files"
fi

echo ""
echo "=== 0b. .atdd/config.yaml validity (hard) ==="
if [[ ! -f .atdd/config.yaml ]]; then
  die ".atdd/config.yaml is missing"
fi
if ! python3 -c "import yaml, sys; yaml.safe_load(open('.atdd/config.yaml'))" 2>/tmp/yaml_err; then
  cat /tmp/yaml_err >&2
  die ".atdd/config.yaml is invalid YAML — see error above"
fi
pass ".atdd/config.yaml parses cleanly"
if grep -q "^test_runner:" .atdd/config.yaml; then
  pass "test_runner block present"
else
  warn "test_runner block not found — may have been dropped in merge"
fi

# ============================================================================
# SOFT CHECKS — report and keep going
# ============================================================================

echo ""
echo "=== 1. atdd CLI availability ==="
if command -v atdd >/dev/null 2>&1; then
  VERSION=$(atdd --version 2>/dev/null || echo "unknown")
  pass "atdd found: $VERSION"
else
  fail "atdd CLI not on PATH — run 'pip install -e .[dev]' inside the fork"
fi

echo ""
echo "=== 2. atdd gate ==="
if command -v atdd >/dev/null 2>&1; then
  if atdd gate 2>&1 | tail -20; then
    pass "atdd gate reported output"
  else
    fail "atdd gate failed"
  fi
else
  warn "skipped (CLI missing)"
fi

echo ""
echo "=== 3. atdd validate ==="
if command -v atdd >/dev/null 2>&1; then
  if atdd validate --quick 2>&1 | tail -30; then
    pass "atdd validate completed"
  else
    fail "atdd validate failed"
  fi
else
  warn "skipped (CLI missing)"
fi

echo ""
echo "=== 4. convention files referenced by skills-package/ ==="
if [[ -d skills-package ]]; then
  # Loosened regex: match any path containing 'conventions/' or 'convention.yaml'
  CONV_REFS=$(grep -rEoh "[a-zA-Z0-9_/.-]*convention[a-zA-Z0-9_./-]*\.yaml" skills-package/ 2>/dev/null \
              | grep -v "^$" | sort -u || true)
  if [[ -z "$CONV_REFS" ]]; then
    info "no convention references found in skills-package/"
  else
    while IFS= read -r ref; do
      # Strip leading slashes so we can resolve relative to repo root
      clean="${ref#/}"
      if [[ -f "$clean" ]]; then
        pass "$ref exists"
      else
        # Try a search in case the path is relative to src/atdd/
        if find src -path "*/$clean" -print -quit 2>/dev/null | grep -q .; then
          pass "$ref resolves under src/"
        else
          fail "$ref not found (likely renamed upstream)"
        fi
      fi
    done <<< "$CONV_REFS"
  fi
else
  info "no skills-package/ directory — skipped"
fi

echo ""
echo "=== 5. CLI command surface (skills reference these) ==="
if command -v atdd >/dev/null 2>&1; then
  for cmd in "validate" "gate" "issue" "inventory" "status"; do
    if atdd "$cmd" --help >/dev/null 2>&1; then
      pass "atdd $cmd is available"
    else
      warn "atdd $cmd not available — skills may reference a renamed command"
    fi
  done
else
  warn "skipped (CLI missing)"
fi

echo ""
echo "================================"
echo "  verify summary: $PASS pass, $FAIL fail, $WARN warn"
echo "================================"

if [[ $FAIL -gt 0 ]]; then
  echo ""
  echo "action required. common fixes:"
  echo "  - missing conventions: update skills-package/ references to new paths"
  echo "  - CLI missing: cd to repo root and run 'pip install -e .[dev]'"
  exit 1
fi

exit 0
