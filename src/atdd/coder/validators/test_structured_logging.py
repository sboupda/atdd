"""
Test structured logging conventions are followed.

Validates:
- No print() calls in non-test production Python code (LOG-001)
- Logger calls include extra= keyword for structured context (LOG-002)

Conventions from:
- atdd/coder/conventions/logging.convention.yaml

Scan scope: REPO_ROOT/python/ (consumer product code only)
"""

import pytest
import ast
from pathlib import Path
from typing import List, Tuple

import atdd
from atdd.coach.utils.repo import find_repo_root


# Path constants
# Consumer repo artifacts
REPO_ROOT = find_repo_root()
PYTHON_DIR = REPO_ROOT / "python"

# Package resources (conventions, schemas)
ATDD_PKG_DIR = Path(atdd.__file__).resolve().parent
LOGGING_CONVENTION = ATDD_PKG_DIR / "coder" / "conventions" / "logging.convention.yaml"

# Logger method names that require extra= for structured context
LOG_METHODS = {"debug", "info", "warning", "error", "critical", "exception", "log"}


def find_python_files() -> List[Path]:
    """
    Find non-test Python files in python/ directory.

    Excludes:
    - Test directories (tests/, test/)
    - Test files (test_*.py)
    - __pycache__ directories
    - __init__.py files

    Returns:
        List of Path objects for production Python files.
    """
    if not PYTHON_DIR.exists():
        return []

    python_files = []
    for py_file in PYTHON_DIR.rglob("*.py"):
        path_str = str(py_file)
        if "/tests/" in path_str or "/test/" in path_str:
            continue
        if py_file.name.startswith("test_"):
            continue
        if "__pycache__" in path_str:
            continue
        if py_file.name == "__init__.py":
            continue
        python_files.append(py_file)
    return python_files


def detect_print_calls(file_path: Path) -> List[Tuple[int, int]]:
    """
    Use AST to detect print() calls in a file.

    Args:
        file_path: Path to Python file to analyze.

    Returns:
        List of (line_number, column_offset) tuples for each print() call.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                violations.append((node.lineno, node.col_offset))
    return violations


def detect_bare_log_calls(file_path: Path) -> List[Tuple[int, int, str]]:
    """
    Use AST to detect logger.X() calls without extra= keyword argument.

    Matches any attribute call where the method name is a standard logging
    method (info, debug, warning, error, critical, exception, log).

    Args:
        file_path: Path to Python file to analyze.

    Returns:
        List of (line_number, column_offset, method_name) tuples.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in LOG_METHODS:
                has_extra = any(kw.arg == "extra" for kw in node.keywords)
                if not has_extra:
                    violations.append((node.lineno, node.col_offset, node.func.attr))
    return violations


@pytest.mark.coder
def test_no_print_in_production_code():
    """
    SPEC-CODER-LOG-0001: No print() in non-test production Python code.

    Production code should use the logging module, not print().
    Print statements are acceptable in:
    - Test files (test_*.py, */tests/*, */test/*)
    - CLI tools (src/atdd/) — exempt, uses print for user-facing output

    Given: Python files in python/ (excluding tests)
    When: Checking for print() calls via AST analysis
    Then: No print() calls found

    Convention: atdd/coder/conventions/logging.convention.yaml (LOG-001)
    """
    python_files = find_python_files()

    if not python_files:
        pytest.skip("No Python files found in python/ to validate")

    violations = []
    for py_file in python_files:
        prints = detect_print_calls(py_file)
        for lineno, col in prints:
            rel_path = py_file.relative_to(REPO_ROOT)
            violations.append(f"{rel_path}:{lineno}:{col} — print() call")

    if violations:
        pytest.fail(
            f"\n\nFound {len(violations)} print() violations in production code:\n\n"
            + "\n".join(violations[:20])
            + (
                f"\n\n... and {len(violations) - 20} more"
                if len(violations) > 20
                else ""
            )
            + "\n\nUse logging module instead of print()."
            + "\nSee: atdd/coder/conventions/logging.convention.yaml (LOG-001)"
        )


@pytest.mark.coder
def test_structured_logging_format():
    """
    SPEC-CODER-LOG-0002: Logger calls must include extra= context dict.

    Stdlib logging with extra={} provides structured context for observability.
    Bare-string log calls (logger.info("msg")) are unstructured.

    Valid:   logger.info("User created", extra={"user_id": uid})
    Invalid: logger.info("User created")
    Invalid: logger.info("User %s", username)

    Given: Python files in python/ (excluding tests)
    When: Checking logger calls via AST analysis
    Then: All logger calls include extra= keyword argument

    Convention: atdd/coder/conventions/logging.convention.yaml (LOG-002)
    """
    python_files = find_python_files()

    if not python_files:
        pytest.skip("No Python files found in python/ to validate")

    violations = []
    for py_file in python_files:
        bare_logs = detect_bare_log_calls(py_file)
        for lineno, col, method in bare_logs:
            rel_path = py_file.relative_to(REPO_ROOT)
            violations.append(
                f"{rel_path}:{lineno}:{col} — logger.{method}() without extra="
            )

    if violations:
        pytest.fail(
            f"\n\nFound {len(violations)} unstructured log call violations:\n\n"
            + "\n".join(violations[:20])
            + (
                f"\n\n... and {len(violations) - 20} more"
                if len(violations) > 20
                else ""
            )
            + "\n\nUse: logger.info('message', extra={'key': 'value'})"
            + "\nSee: atdd/coder/conventions/logging.convention.yaml (LOG-002)"
        )
