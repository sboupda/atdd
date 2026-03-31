"""
Test frontend code for known-bad security patterns.

Validates:
- No innerHTML or dangerouslySetInnerHTML usage in TypeScript/JSX files

Conventions from:
- atdd/coder/conventions/security.convention.yaml

Rationale: Direct DOM manipulation via innerHTML is the most common
XSS vector in frontend code.  Safe alternatives exist (textContent,
React's JSX escaping, DOMPurify).
"""

import fnmatch
import os
import re
import yaml
import pytest
from pathlib import Path
from typing import Dict, List, Optional

import atdd
from atdd.coach.utils.repo import find_repo_root


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
REPO_ROOT = find_repo_root()
WEB_DIR = REPO_ROOT / "web"
FRONTEND_DIRS = [
    REPO_ROOT / "web",
    REPO_ROOT / "frontend",
]

ATDD_PKG_DIR = Path(atdd.__file__).resolve().parent
SECURITY_CONVENTION = ATDD_PKG_DIR / "coder" / "conventions" / "security.convention.yaml"

_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".dart_tool",
    "build", ".pub-cache", "dist", ".next", ".nuxt", "coverage",
    ".venv", "venv", "env", ".tox", ".mypy_cache", ".pytest_cache",
}


# ---------------------------------------------------------------------------
# Convention loader
# ---------------------------------------------------------------------------
def load_security_convention() -> Dict:
    """Load security convention YAML.  Returns empty dict when missing."""
    if not SECURITY_CONVENTION.exists():
        return {}
    with open(SECURITY_CONVENTION, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
        return data.get("security", {})


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------
def matches_exclusion(
    file_path: Path,
    exclusions: List[str],
    base_dir: Path,
) -> bool:
    """Return True if *file_path* matches any exclusion glob relative to *base_dir*."""
    try:
        rel = str(file_path.relative_to(base_dir))
    except ValueError:
        rel = str(file_path)
    return any(fnmatch.fnmatch(rel, pat) for pat in exclusions)


def find_frontend_files(
    dirs: List[Path],
    extensions: List[str],
    exclude_patterns: Optional[List[str]] = None,
) -> List[Path]:
    """Walk directories for files matching *extensions*, honouring exclusions."""
    exclude_patterns = exclude_patterns or []
    files: List[Path] = []
    for base_dir in dirs:
        if not base_dir.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for fname in filenames:
                if not any(fname.endswith(ext) for ext in extensions):
                    continue
                full = Path(dirpath) / fname
                if matches_exclusion(full, exclude_patterns, base_dir):
                    continue
                files.append(full)
    return files


# ---------------------------------------------------------------------------
# XSS pattern detector  (regex)
# ---------------------------------------------------------------------------
def check_xss_patterns(
    file_path: Path,
    patterns: List[str],
) -> List[Dict]:
    """Line-by-line regex scan for XSS-prone DOM patterns."""
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    compiled = [(p, re.compile(p)) for p in patterns]
    violations: List[Dict] = []
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue
        for pattern_str, regex in compiled:
            if regex.search(line):
                snippet = stripped[:80] + ("..." if len(stripped) > 80 else "")
                violations.append({
                    "file": file_path,
                    "line": lineno,
                    "detail": f"XSS pattern '{pattern_str}' found: {snippet}",
                })
    return violations


# ---------------------------------------------------------------------------
# Violation formatter
# ---------------------------------------------------------------------------
def _format_violations(violations: List[Dict], base_dir: Path) -> str:
    """Format violations for pytest.fail() output."""
    lines = []
    for v in violations[:10]:
        try:
            rel = v["file"].relative_to(base_dir)
        except ValueError:
            rel = v["file"]
        lines.append(f"{rel}:{v['line']}\n  {v['detail']}")
    header = f"\n\nFound {len(violations)} security violation(s):\n\n"
    body = "\n\n".join(lines)
    tail = ""
    if len(violations) > 10:
        tail = f"\n\n... and {len(violations) - 10} more"
    return header + body + tail


# ===========================================================================
# Tests
# ===========================================================================

@pytest.mark.coder
def test_no_xss_prone_patterns():
    """
    SPEC-CODER-SEC-0004: No innerHTML or dangerouslySetInnerHTML in frontend code.

    Direct DOM manipulation via innerHTML is the most common XSS vector.
    Use textContent, framework-safe APIs, or DOMPurify instead.

    Given: TypeScript/JSX files in web/ or frontend/
    When:  Scanning for innerHTML and dangerouslySetInnerHTML patterns
    Then:  No XSS-prone DOM manipulation found
    """
    convention = load_security_convention()
    rule = convention.get("rules", {}).get("xss_patterns", {})
    patterns = rule.get("patterns", ["innerHTML", "dangerouslySetInnerHTML", r"outerHTML\s*="])
    extensions = rule.get("file_extensions", [".ts", ".tsx", ".jsx"])
    exclusions = rule.get("exclusions", [])

    files = find_frontend_files(FRONTEND_DIRS, extensions, exclusions)
    if not files:
        pytest.skip("No frontend files found in web/ or frontend/")

    violations: List[Dict] = []
    for f in files:
        violations.extend(check_xss_patterns(f, patterns))

    if violations:
        pytest.fail(_format_violations(violations, REPO_ROOT))
