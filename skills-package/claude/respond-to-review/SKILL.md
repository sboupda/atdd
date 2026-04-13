---
name: respond-to-review
description: Respond to a reviewer's findings on a story using the formal ACCEPT/PUSH_BACK protocol. Use when told a review is ready. Supports both standalone TDD and ATDD-governed workflows.
argument-hint: [story-id]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(pytest:*), Bash(conda:*), Bash(python*:*), Bash(bash scripts/*:*), Bash(atdd:*)
---

Respond to the latest review for **$ARGUMENTS** as the Coder.

## 0. Resolve Project Config

Check for test runner configuration in this order:
1. `.atdd/config.yaml` → read `test_runner` section
2. `tdd.config.yaml` → fallback for non-ATDD projects
3. Hardcoded defaults if neither file exists

**Defaults:**
```yaml
test_runner:
  single: "conda run -n quant pytest -v {test_files} --no-header"
  suite: "conda run -n quant pytest -q"
  check: "bash scripts/check.sh"
  env: null
```

**ATDD detection:** If `.atdd/config.yaml` exists, set `atdd_mode = true`.

**ATDD dependency check (when `atdd_mode = true`):** Run `atdd --version`. If not found, stop and instruct:
```
ATDD CLI not installed. Run: pip install -e ".[dev]" from the ATDD repo root.
```

## 1. Find and Read the Review

- Look in `docs/reviews/` for `REVIEW_STORY-{id}_ROUND*.md` — pick the latest round.
- Read each finding: severity (P0-P3), evidence, required change.

## 2. Address Each Finding

### ACCEPT
- Implement the fix.
- Add or update tests — every fix needs test evidence. Validation fixes need negative tests.
- Run targeted tests to confirm.

### PUSH_BACK
- Write technical justification for why the finding is incorrect or harmful.
- Propose an alternative with tradeoffs.
- Reserve for cases with strong technical reasoning; prefer ACCEPT when finding is valid.

## 3. Validate

- Run full suite: `{test_runner.suite}` (from config)
- Run check: `{test_runner.check}` (from config)
- Confirm test count increased from new fix tests.

**ATDD additional validation (only when `atdd_mode = true`):**
- Run `atdd validate coder` — confirm architecture and contract compliance still holds after fixes.
- If a fix changes a contract schema or crosses a wagon boundary, flag it explicitly in the response — the reviewer (coach) needs to re-validate cross-wagon consistency.

## 4. Write the Response

Create `docs/reviews/RESPONSE_STORY-{id}_ROUND{n}.md` using the template at [response-template.md](response-template.md).

For a real example of a completed response (P1 validation fix + P2 test rename), see [example-d4-round1-response.md](example-d4-round1-response.md).

## Severity Guide

- **P0/P1**: Must fix. Story cannot close with open P0/P1.
- **P2**: Fix or defer with rationale. Reviewer adjudicates.
- **P3**: Optional.

## Rules

- Every ACCEPT includes a code patch AND test evidence.
- Never declare ready if tests are failing.
- Update handoff evidence if fix changes output or behavior.
