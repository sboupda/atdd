"""
Error Response Compliance Validator.

Validates conventions from:
- atdd/coder/conventions/error-response.convention.yaml

Enforces:
- Error responses MUST use structured format: {status_code, error_code, message, details?}
- Error codes MUST be enum-based (UPPER_SNAKE_CASE), not freeform strings
- Bare string error details are forbidden in HTTP exception handlers
- Error response convention YAML must exist and define rules

Convention: atdd/coder/conventions/error-response.convention.yaml
Contract: contracts/commons/error/response.schema.json

URN: test:verify-contracts:error-response-contract
WMBT: wmbt:verify-contracts:C001, D001, E001, K001
Phase: RED
"""

import json
import re
from pathlib import Path

import jsonschema
import pytest
import yaml

import atdd
from atdd.coach.utils.repo import find_repo_root

# Consumer repo artifacts
REPO_ROOT = find_repo_root()
PYTHON_DIR = REPO_ROOT / "python"

# Package resources (conventions, schemas, contracts)
ATDD_PKG_DIR = Path(atdd.__file__).resolve().parent
ERROR_RESPONSE_CONVENTION = (
    ATDD_PKG_DIR / "coder" / "conventions" / "error-response.convention.yaml"
)
ERROR_RESPONSE_CONTRACT = (
    REPO_ROOT / "contracts" / "commons" / "error" / "response.schema.json"
)

# Regex: matches detail='...' or detail="..." (bare string) in HTTPException calls
BARE_STRING_DETAIL_RE = re.compile(
    r"""HTTPException\s*\([^)]*detail\s*=\s*(?:f?['"][^'"]*['"])""",
    re.DOTALL,
)

# Regex: matches error_code assignments/values that are NOT UPPER_SNAKE_CASE
ERROR_CODE_VALUE_RE = re.compile(
    r"""['\"]error_code['\"]\s*:\s*['\"]([^'"]+)['\"]""",
)

UPPER_SNAKE_CASE_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")


# ============================================================================
# CONTRACT VALIDATION (WMBT C001)
# ============================================================================


@pytest.mark.coder
def test_error_response_contract_exists():
    """
    SPEC-CODER-ERRORRESPONSE-0001: Error response contract schema exists.

    GIVEN: contracts/commons/error/response.schema.json expected path
    WHEN: Checking for contract file
    THEN: File exists, is valid JSON Schema draft-07, has correct $id and required fields

    Validates: acc:verify-contracts:C001-UNIT-001
    """
    if not ERROR_RESPONSE_CONTRACT.exists():
        pytest.fail(
            f"\n\nError response contract not found.\n"
            f"  Expected: {ERROR_RESPONSE_CONTRACT.relative_to(REPO_ROOT)}\n"
            f"  Action: Create the contract per commons:error:response spec.\n"
            f"  Convention: error-response.convention.yaml (ERR-01)"
        )

    schema = json.loads(ERROR_RESPONSE_CONTRACT.read_text(encoding="utf-8"))

    violations = []

    if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
        violations.append("$schema must be http://json-schema.org/draft-07/schema#")

    if schema.get("$id") != "commons:error:response":
        violations.append("$id must be 'commons:error:response'")

    if schema.get("title") != "CommonsErrorResponse":
        violations.append("title must be 'CommonsErrorResponse'")

    required = schema.get("required", [])
    for field in ("status_code", "error_code", "message"):
        if field not in required:
            violations.append(f"'{field}' must be in required array")

    if "details" in required:
        violations.append("'details' must NOT be in required array (it is optional)")

    if violations:
        pytest.fail(
            f"\n\nError response contract schema violations:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


@pytest.mark.coder
def test_error_response_contract_validates_canonical_payloads():
    """
    SPEC-CODER-ERRORRESPONSE-0002: Contract validates canonical error payloads.

    GIVEN: Error response contract schema
    WHEN: Validating canonical payloads (valid and invalid)
    THEN: Valid payloads pass, invalid payloads fail

    Validates: acc:verify-contracts:C001-UNIT-001, C001-UNIT-002, C001-UNIT-003
    """
    if not ERROR_RESPONSE_CONTRACT.exists():
        pytest.fail(
            f"\n\nCannot validate payloads: contract not found at "
            f"{ERROR_RESPONSE_CONTRACT.relative_to(REPO_ROOT)}"
        )

    schema = json.loads(ERROR_RESPONSE_CONTRACT.read_text(encoding="utf-8"))

    # --- Valid payloads must pass ---
    valid_minimal = {
        "status_code": 400,
        "error_code": "INVALID_INPUT",
        "message": "Missing required field: name",
    }
    valid_with_details = {
        "status_code": 500,
        "error_code": "INTERNAL_ERROR",
        "message": "Unexpected failure",
        "details": {"trace_id": "abc-123", "service": "auth"},
    }

    violations = []

    for label, payload in [
        ("valid_minimal", valid_minimal),
        ("valid_with_details", valid_with_details),
    ]:
        try:
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.ValidationError as e:
            violations.append(f"{label}: should pass but failed — {e.message}")

    # --- Invalid payloads must fail ---
    invalid_missing_error_code = {
        "status_code": 400,
        "message": "Bad request",
    }
    invalid_lowercase_error_code = {
        "status_code": 400,
        "error_code": "bad_input",
        "message": "Bad input",
    }
    invalid_extra_field = {
        "status_code": 400,
        "error_code": "BAD_REQUEST",
        "message": "Bad",
        "unexpected_field": True,
    }

    for label, payload in [
        ("missing_error_code", invalid_missing_error_code),
        ("lowercase_error_code", invalid_lowercase_error_code),
        ("extra_field", invalid_extra_field),
    ]:
        try:
            jsonschema.validate(instance=payload, schema=schema)
            violations.append(f"{label}: should fail but passed validation")
        except jsonschema.ValidationError:
            pass  # Expected

    if violations:
        pytest.fail(
            f"\n\nContract payload validation failures:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ============================================================================
# CONVENTION VALIDATION (WMBT D001)
# ============================================================================


@pytest.mark.coder
def test_error_response_convention_exists():
    """
    SPEC-CODER-ERRORRESPONSE-0003: Error response convention YAML exists.

    GIVEN: src/atdd/coder/conventions/error-response.convention.yaml expected path
    WHEN: Checking for convention file
    THEN: File exists and contains required sections

    Validates: acc:verify-contracts:D001-UNIT-001
    """
    if not ERROR_RESPONSE_CONVENTION.exists():
        pytest.fail(
            f"\n\nError response convention not found.\n"
            f"  Expected: {ERROR_RESPONSE_CONVENTION}\n"
            f"  Action: Create error-response.convention.yaml with rules, "
            f"error_code_format, and phase_guidance sections."
        )

    content = yaml.safe_load(
        ERROR_RESPONSE_CONVENTION.read_text(encoding="utf-8")
    )

    violations = []
    required_keys = ["rules", "error_code_format", "phase_guidance"]
    for key in required_keys:
        if key not in content:
            violations.append(f"Missing required section: '{key}'")

    if content.get("convention_id") != "error-response":
        violations.append("convention_id must be 'error-response'")

    if violations:
        pytest.fail(
            f"\n\nError response convention structure violations:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ============================================================================
# ENDPOINT COMPLIANCE (WMBT E001)
# ============================================================================


@pytest.mark.coder
def test_python_endpoints_use_structured_error_responses():
    """
    SPEC-CODER-ERRORRESPONSE-0004: Python endpoints use structured error responses.

    GIVEN: Python source files in the consumer repo
    WHEN: Scanning for HTTPException usage
    THEN: No bare string detail= arguments found

    Validates: acc:verify-contracts:E001-UNIT-001, E001-UNIT-002
    """
    if not PYTHON_DIR.exists():
        pytest.skip("python/ directory not found — no endpoints to validate")

    py_files = list(PYTHON_DIR.rglob("*.py"))
    if not py_files:
        pytest.skip("No Python files found in python/")

    violations = []
    files_with_httpexception = 0

    for py_file in py_files:
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8", errors="replace")
        if "HTTPException" not in content:
            continue

        files_with_httpexception += 1

        for match in BARE_STRING_DETAIL_RE.finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            violations.append(
                f"{py_file.relative_to(REPO_ROOT)}:{line_num}: "
                f"bare string detail in HTTPException — use structured "
                f"error response {{status_code, error_code, message}}"
            )

    if files_with_httpexception == 0:
        pytest.skip("No files with HTTPException found in python/")

    if violations:
        pytest.fail(
            f"\n\nBare string error responses detected "
            f"(convention ERR-03):\n"
            + "\n".join(f"  - {v}" for v in violations)
            + f"\n\n  Contract: contracts/commons/error/response.schema.json"
            + f"\n  Convention: error-response.convention.yaml"
        )


# ============================================================================
# ERROR CODE FORMAT (WMBT E001 continued)
# ============================================================================


@pytest.mark.coder
def test_error_codes_follow_enum_convention():
    """
    SPEC-CODER-ERRORRESPONSE-0005: Error codes follow UPPER_SNAKE_CASE convention.

    GIVEN: Python source files in the consumer repo
    WHEN: Scanning for error_code values
    THEN: All error codes match ^[A-Z][A-Z0-9_]+$ pattern

    Validates: acc:verify-contracts:E001-UNIT-001 (error code format)
    """
    if not PYTHON_DIR.exists():
        pytest.skip("python/ directory not found — no error codes to validate")

    py_files = list(PYTHON_DIR.rglob("*.py"))
    if not py_files:
        pytest.skip("No Python files found in python/")

    violations = []
    error_codes_found = 0

    for py_file in py_files:
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8", errors="replace")

        for match in ERROR_CODE_VALUE_RE.finditer(content):
            error_code = match.group(1)
            error_codes_found += 1

            if not UPPER_SNAKE_CASE_RE.match(error_code):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(
                    f"{py_file.relative_to(REPO_ROOT)}:{line_num}: "
                    f"error_code '{error_code}' is not UPPER_SNAKE_CASE "
                    f"(expected pattern: ^[A-Z][A-Z0-9_]+$)"
                )

    if error_codes_found == 0:
        pytest.skip("No error_code values found in python/")

    if violations:
        pytest.fail(
            f"\n\nError code format violations (convention ERR-02):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
