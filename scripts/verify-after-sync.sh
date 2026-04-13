#!/usr/bin/env bash
# verify-after-sync.sh — smoke-check the fork after pulling an upstream release.
# Run this from the diool branch after sync-upstream.sh completes.
#
# Usage:
#   scripts/verify-after-sync.sh
#
# Checks:
#   1. atdd CLI is installed and reports a version
#   2. `atdd gate` passes (core framework self-check)
#   3. `atdd validate` passes on the current repo
#   4. All convention files referenced by skills-package/ still exist upstream
#   5. .atdd/config.yaml is valid YAML
#   6. Report any skills-package/ references to renamed/removed convention files

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
  # Extract all convention paths mentioned in skills
  MISSING=0
  CONV_REFS=$(grep -roh "src/atdd/[a-z]*/conventions/[a-z_.-]*\.yaml" skills-package/ 2>/dev/null | sort -u || true)
  if [[ -z "$CONV_REFS" ]]; then
    info "no convention references found in skills-package/"
  else
    while IFS= read -r ref; do
      if [[ -f "$ref" ]]; then
        pass "$ref exists"
      else
        fail "$ref missing (likely renamed upstream)"
        MISSING=$((MISSING+1))
      fi
    done <<< "$CONV_REFS"
  fi
else
  info "no skills-package/ directory — skipped"
fi

echo ""
echo "=== 5. .atdd/config.yaml validity ==="
if [[ -f .atdd/config.yaml ]]; then
  if python3 -c "import yaml; yaml.safe_load(open('.atdd/config.yaml'))" 2>/dev/null; then
    pass ".atdd/config.yaml is valid YAML"
    # check test_runner block survived
    if grep -q "^test_runner:" .atdd/config.yaml; then
      pass "test_runner block present"
    else
      warn "test_runner block not found — may have been dropped in merge"
    fi
  else
    fail ".atdd/config.yaml is invalid YAML"
  fi
else
  warn ".atdd/config.yaml not found"
fi

echo ""
echo "=== 6. CLI command surface (skills reference these) ==="
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
  echo "  - invalid config: reconcile .atdd/config.yaml against upstream's new shape"
  echo "  - CLI missing: cd to repo root and run 'pip install -e .[dev]'"
  exit 1
fi

exit 0
