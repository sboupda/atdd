"""
Unit tests for the branch protection contract module.

SPEC: wmbt:branch-protection-drift-detection:GT-010
ID: SPEC-COACH-BP-UNIT

Acceptance URNs covered by this test file:
  acc:branch-protection-drift-detection:GT010-UNIT-001-contract-is-single-source
  acc:branch-protection-drift-detection:GT010-UNIT-002-compare-detects-enforced
  acc:branch-protection-drift-detection:GT010-UNIT-003-compare-detects-drift
  acc:branch-protection-drift-detection:GT010-UNIT-004-compare-detects-missing-checks
  acc:branch-protection-drift-detection:GT010-UNIT-005-compare-detects-admin-drift
  acc:branch-protection-drift-detection:GT010-UNIT-006-compare-detects-pr-review-drift
  acc:branch-protection-drift-detection:GT010-UNIT-007-extract-contexts-legacy
  acc:branch-protection-drift-detection:GT010-UNIT-008-extract-contexts-checks-array
  acc:branch-protection-drift-detection:GT010-UNIT-009-verify-handles-timeout
  acc:branch-protection-drift-detection:GT010-UNIT-010-verify-handles-not-found
  acc:branch-protection-drift-detection:GT010-UNIT-011-verify-handles-403

Purpose:
  Validate the branch protection contract and comparison logic without
  requiring GitHub API access. Tests exercise _compare_policy,
  _extract_contexts, and the subprocess error handling paths of
  verify_branch_protection.

Architecture:
  - Pure-logic tests exercise _compare_policy directly (no subprocess)
  - Subprocess paths are tested via unittest.mock.patch
  - No ad-hoc assertions — each test maps to a specific acceptance URN
"""
import subprocess
from unittest.mock import patch

import pytest

from atdd.coach.commands.branch_protection import (
    BRANCH,
    EXPECTED_POLICY,
    ProtectionStatus,
    _compare_policy,
    _extract_contexts,
    verify_branch_protection,
)


# ============================================================================
# Contract structure tests
# ============================================================================


class TestExpectedPolicyContract:
    """Verify the expected policy dict is well-formed and complete."""

    def test_policy_has_required_status_checks(self):
        """
        SPEC-COACH-BP-UNIT-001: Contract includes required_status_checks.

        Given: EXPECTED_POLICY
        When: Inspecting keys
        Then: required_status_checks is present with strict and contexts
        """
        checks = EXPECTED_POLICY["required_status_checks"]
        assert checks["strict"] is True
        assert "validate-gate" in checks["contexts"]

    def test_policy_has_enforce_admins(self):
        """
        SPEC-COACH-BP-UNIT-002: Contract enforces admins.

        Given: EXPECTED_POLICY
        When: Inspecting enforce_admins
        Then: enforce_admins is True
        """
        assert EXPECTED_POLICY["enforce_admins"] is True

    def test_policy_has_pr_reviews(self):
        """
        SPEC-COACH-BP-UNIT-003: Contract includes PR review requirements.

        Given: EXPECTED_POLICY
        When: Inspecting required_pull_request_reviews
        Then: required_approving_review_count is 0
        """
        pr = EXPECTED_POLICY["required_pull_request_reviews"]
        assert pr["required_approving_review_count"] == 0

    def test_branch_target(self):
        """
        SPEC-COACH-BP-UNIT-004: Contract targets main branch.

        Given: BRANCH constant
        When: Inspecting value
        Then: Branch is 'main'
        """
        assert BRANCH == "main"


# ============================================================================
# _compare_policy tests
# ============================================================================


class TestComparePolicy:
    """Test drift detection against various GitHub API response shapes."""

    def _build_actual(self, **overrides):
        """Build a GitHub-shaped protection response matching the contract."""
        base = {
            "required_status_checks": {
                "strict": True,
                "contexts": ["validate-gate"],
                "checks": [{"context": "validate-gate", "app_id": None}],
            },
            "enforce_admins": {"enabled": True},
            "required_pull_request_reviews": {
                "required_approving_review_count": 0,
            },
            "restrictions": None,
        }
        base.update(overrides)
        return base

    def test_enforced_when_matching(self):
        """
        SPEC-COACH-BP-UNIT-010: Matching policy yields ENFORCED.

        Given: Actual protection that matches expected contract
        When: Comparing with _compare_policy
        Then: Status is ENFORCED with no drift details
        """
        actual = self._build_actual()
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.ENFORCED
        assert details == []

    def test_drift_strict_mode_disabled(self):
        """
        SPEC-COACH-BP-UNIT-011: Strict mode mismatch is detected.

        Given: Actual protection with strict=False
        When: Comparing with _compare_policy
        Then: Status is DRIFTED with strict mode detail
        """
        actual = self._build_actual()
        actual["required_status_checks"]["strict"] = False
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.DRIFTED
        assert any("strict" in d for d in details)

    def test_drift_missing_context(self):
        """
        SPEC-COACH-BP-UNIT-012: Missing validate-gate context is detected.

        Given: Actual protection without validate-gate context
        When: Comparing with _compare_policy
        Then: Status is DRIFTED with missing context detail
        """
        actual = self._build_actual()
        actual["required_status_checks"]["contexts"] = []
        actual["required_status_checks"]["checks"] = []
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.DRIFTED
        assert any("validate-gate" in d for d in details)

    def test_drift_enforce_admins_disabled(self):
        """
        SPEC-COACH-BP-UNIT-013: Disabled enforce_admins is detected.

        Given: Actual protection with enforce_admins.enabled=False
        When: Comparing with _compare_policy
        Then: Status is DRIFTED with enforce_admins detail
        """
        actual = self._build_actual()
        actual["enforce_admins"]["enabled"] = False
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.DRIFTED
        assert any("enforce_admins" in d for d in details)

    def test_drift_pr_reviews_missing(self):
        """
        SPEC-COACH-BP-UNIT-014: Missing PR reviews config is detected.

        Given: Actual protection without required_pull_request_reviews
        When: Comparing with _compare_policy
        Then: Status is DRIFTED with PR review detail
        """
        actual = self._build_actual()
        actual["required_pull_request_reviews"] = None
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.DRIFTED
        assert any("required_pull_request_reviews" in d for d in details)

    def test_drift_pr_review_count_changed(self):
        """
        SPEC-COACH-BP-UNIT-015: Changed review count is detected.

        Given: Actual protection with review count = 2
        When: Comparing with _compare_policy
        Then: Status is DRIFTED with review count detail
        """
        actual = self._build_actual()
        actual["required_pull_request_reviews"]["required_approving_review_count"] = 2
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.DRIFTED
        assert any("required_approving_review_count" in d for d in details)

    def test_no_status_checks_at_all(self):
        """
        SPEC-COACH-BP-UNIT-016: Missing status checks entirely is detected.

        Given: Actual protection with no required_status_checks
        When: Comparing with _compare_policy
        Then: Status is DRIFTED (strict=False and missing contexts)
        """
        actual = self._build_actual()
        actual["required_status_checks"] = None
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.DRIFTED
        assert len(details) >= 1

    def test_multiple_drifts_reported(self):
        """
        SPEC-COACH-BP-UNIT-017: Multiple simultaneous drifts all reported.

        Given: Actual protection with strict=False AND enforce_admins=False
        When: Comparing with _compare_policy
        Then: Both drift details are present
        """
        actual = self._build_actual()
        actual["required_status_checks"]["strict"] = False
        actual["enforce_admins"]["enabled"] = False
        status, details = _compare_policy(actual)
        assert status == ProtectionStatus.DRIFTED
        assert any("strict" in d for d in details)
        assert any("enforce_admins" in d for d in details)


# ============================================================================
# _extract_contexts tests
# ============================================================================


class TestExtractContexts:
    """Test context name extraction from various API response shapes."""

    def test_checks_array_format(self):
        """
        SPEC-COACH-BP-UNIT-020: Extracts contexts from checks array.

        Given: Status checks with checks array (new format)
        When: Extracting contexts
        Then: Context names are returned
        """
        checks = {
            "checks": [
                {"context": "validate-gate", "app_id": None},
                {"context": "ci/build", "app_id": 123},
            ],
        }
        result = _extract_contexts(checks)
        assert result == {"validate-gate", "ci/build"}

    def test_contexts_flat_array_format(self):
        """
        SPEC-COACH-BP-UNIT-021: Extracts contexts from flat contexts array.

        Given: Status checks with contexts array (legacy format)
        When: Extracting contexts
        Then: Context names are returned
        """
        checks = {"contexts": ["validate-gate", "ci/lint"]}
        result = _extract_contexts(checks)
        assert result == {"validate-gate", "ci/lint"}

    def test_both_formats_merged(self):
        """
        SPEC-COACH-BP-UNIT-022: Both formats are merged correctly.

        Given: Status checks with both checks and contexts arrays
        When: Extracting contexts
        Then: Union of both sets is returned
        """
        checks = {
            "checks": [{"context": "validate-gate", "app_id": None}],
            "contexts": ["ci/lint"],
        }
        result = _extract_contexts(checks)
        assert result == {"validate-gate", "ci/lint"}

    def test_empty_checks(self):
        """
        SPEC-COACH-BP-UNIT-023: Empty checks returns empty set.

        Given: Empty checks dict
        When: Extracting contexts
        Then: Empty set returned
        """
        assert _extract_contexts({}) == set()


# ============================================================================
# verify_branch_protection subprocess tests
# ============================================================================


class TestVerifyBranchProtection:
    """Test verify_branch_protection error handling via mocked subprocess."""

    @patch("atdd.coach.commands.branch_protection.subprocess.run")
    def test_timeout_returns_degraded(self, mock_run):
        """
        SPEC-COACH-BP-UNIT-030: Timeout yields DEGRADED status.

        Given: gh CLI times out
        When: Verifying branch protection
        Then: Status is DEGRADED with timeout detail
        """
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=15)
        status, details = verify_branch_protection("owner/repo")
        assert status == ProtectionStatus.DEGRADED
        assert any("timed out" in d for d in details)

    @patch("atdd.coach.commands.branch_protection.subprocess.run")
    def test_gh_not_found_returns_degraded(self, mock_run):
        """
        SPEC-COACH-BP-UNIT-031: Missing gh CLI yields DEGRADED status.

        Given: gh CLI not installed
        When: Verifying branch protection
        Then: Status is DEGRADED
        """
        mock_run.side_effect = FileNotFoundError("gh not found")
        status, details = verify_branch_protection("owner/repo")
        assert status == ProtectionStatus.DEGRADED

    @patch("atdd.coach.commands.branch_protection.subprocess.run")
    def test_not_found_returns_missing(self, mock_run):
        """
        SPEC-COACH-BP-UNIT-032: 404 response yields MISSING status.

        Given: No branch protection rule on main
        When: Verifying branch protection
        Then: Status is MISSING
        """
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Not Found"
        )
        status, details = verify_branch_protection("owner/repo")
        assert status == ProtectionStatus.MISSING

    @patch("atdd.coach.commands.branch_protection.subprocess.run")
    def test_403_returns_degraded(self, mock_run):
        """
        SPEC-COACH-BP-UNIT-033: 403 response yields DEGRADED status.

        Given: Token lacks admin scope
        When: Verifying branch protection
        Then: Status is DEGRADED with permission detail
        """
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="",
            stderr="403 Must have admin access to repository"
        )
        status, details = verify_branch_protection("owner/repo")
        assert status == ProtectionStatus.DEGRADED
        assert any("permissions" in d.lower() or "admin" in d.lower() for d in details)

    @patch("atdd.coach.commands.branch_protection.subprocess.run")
    def test_malformed_json_returns_degraded(self, mock_run):
        """
        SPEC-COACH-BP-UNIT-034: Malformed JSON yields DEGRADED status.

        Given: GitHub API returns non-JSON
        When: Verifying branch protection
        Then: Status is DEGRADED
        """
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json", stderr=""
        )
        status, details = verify_branch_protection("owner/repo")
        assert status == ProtectionStatus.DEGRADED
        assert any("parse" in d.lower() for d in details)

    @patch("atdd.coach.commands.branch_protection.subprocess.run")
    def test_valid_enforced_response(self, mock_run):
        """
        SPEC-COACH-BP-UNIT-035: Valid matching response yields ENFORCED.

        Given: GitHub API returns protection matching expected contract
        When: Verifying branch protection
        Then: Status is ENFORCED
        """
        import json

        payload = json.dumps({
            "required_status_checks": {
                "strict": True,
                "contexts": ["validate-gate"],
                "checks": [{"context": "validate-gate", "app_id": None}],
            },
            "enforce_admins": {"enabled": True},
            "required_pull_request_reviews": {
                "required_approving_review_count": 0,
            },
            "restrictions": None,
        })
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr=""
        )
        status, details = verify_branch_protection("owner/repo")
        assert status == ProtectionStatus.ENFORCED
        assert details == []
