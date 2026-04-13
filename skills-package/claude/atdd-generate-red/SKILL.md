---
name: atdd-generate-red
description: Bridge between ATDD's RED phase and the TDD implement-story workflow. Reads ATDD wagon artifacts (WMBT, contracts, features) and produces a handoff spec that implement-story can consume. Use after atdd-plan-wagon has produced wagon + WMBT artifacts and before invoking implement-story.
argument-hint: [wagon-urn]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(atdd:*), Write
---

Generate a RED-phase handoff spec for wagon **$ARGUMENTS**.

This skill bridges the ATDD Tester phase output into the format that `implement-story` expects. It reads ATDD planning artifacts and produces both failing tests and a handoff spec document.

## 0. Verify Preconditions

- Read `.atdd/config.yaml` — confirm project is initialized.
- Run `atdd --version` — confirm CLI is installed. If not found, stop and instruct:
  ```
  ATDD CLI not installed. Run: pip install -e ".[dev]" from the ATDD repo root.
  ```
- Run `atdd status` — confirm the wagon is in `PLANNED` state (ready for RED).
- If not PLANNED, stop and report the current state.

## 1. Load ATDD Artifacts

Read the following for wagon **$ARGUMENTS**:

1. **Wagon definition** — `plan/{train}/{wagon}.yaml`
   - Extract: wagon URN, bounded context, dependencies, features list
2. **WMBT criteria** — `plan/{train}/{wagon}_wmbt.yaml`
   - Extract: all "What Must Be True" acceptance criteria with IDs
3. **Features** — `plan/{train}/_features.yaml`
   - Extract: feature definitions linked to this wagon
4. **Contracts** — `contracts/` directory
   - Extract: all JSON Schema contracts referenced by this wagon
5. **Event taxonomy** — `contracts/_artifacts.yaml` or coach convention
   - Extract: events this wagon emits or consumes

## 2. Generate JSON Schema Contracts

For each API endpoint or inter-wagon boundary in the WMBT:

- Create a JSON Schema file in `contracts/{wagon}/`
- Schema must validate request and response shapes
- Reference the WMBT ID that drives each schema field
- Run `atdd validate tester` to confirm schema validity

If contracts already exist (from a prior run), validate them against WMBT for completeness.

## 3. Generate RED Tests

For each WMBT criterion, generate one or more test functions:

**Naming convention** (per ATDD filename convention):
```
tests/{wagon}/test_{feature}_{wmbt_id}.py
```

**Test structure:**
- Each test maps to exactly one WMBT ID (referenced in docstring)
- Tests validate contract shapes (using JSON Schema)
- Tests validate business rules (from WMBT acceptance criteria)
- Tests validate error cases (from PRD error codes)
- Tests MUST fail — they test behavior that doesn't exist yet

**Priority order** (hardest contract boundaries first):
1. Financial accuracy (amounts, rounding, invariants)
2. Idempotency and atomicity
3. State machine transitions
4. API contract shapes
5. Error handling
6. Auth and permissions
7. SLA / performance (mark as `@pytest.mark.smoke` — deferred to SMOKE phase)

Run tests to confirm they fail for the right reason (not ImportError).

## 4. Generate Handoff Spec

Write `docs/handoffs/ATDD-{wagon}-{feature}_HANDOFF.md` with this structure:

```markdown
# ATDD-{wagon}: {Feature Title} — Handoff Spec

**Source:** ATDD RED phase for wagon `{wagon_urn}`
**ATDD Phase:** PLANNED → RED
**Generated:** {date}

## 1. Acceptance Criteria (from WMBT)

| WMBT ID | Criterion | Test File |
|---------|-----------|-----------|
| WMBT-01 | {criterion text} | tests/{wagon}/test_{feature}_01.py |
| ... | ... | ... |

## 2. Contracts

| Contract | Path | Validates |
|----------|------|-----------|
| {endpoint} request | contracts/{wagon}/{name}_request.json | WMBT-{ids} |
| {endpoint} response | contracts/{wagon}/{name}_response.json | WMBT-{ids} |
| ... | ... | ... |

## 3. TDD Plan

### Red tests (all must fail before GREEN):
{list of test files with test count per file}

### Priority order:
{numbered priority list from section 3 above}

## 4. Files Allowed to Change

### Create (new files):
- `src/{wagon}/domain/...`
- `src/{wagon}/application/...`
- `src/{wagon}/presentation/...`
- `src/{wagon}/integration/...`

### Do NOT modify:
- Any file outside `src/{wagon}/`
- Any contract schema (contracts are locked at RED)
- Any other wagon's code

## 5. Validation Commands

- `{test_runner.suite}` — all tests pass
- `{test_runner.check}` — project checks pass
- `atdd validate coder` — architecture compliance
- `atdd validate tester` — contract schemas valid

## 6. Events (from taxonomy)

| Event | Direction | Schema |
|-------|-----------|--------|
| {EVENT_NAME} | emits / consumes | contracts/{wagon}/{event}.json |
```

## 5. Transition State

- Run `atdd validate tester` — all test artifacts pass validation
- Run `atdd issue {wagon-slug} --status RED` (use the wagon slug, e.g. `payout-api`, not the full URN)
- Confirm: all tests fail (RED state is correct)

## 6. Handoff

The handoff spec is now ready for `implement-story` to pick up.

Announce:
```
RED phase complete for {wagon_urn}.
- {n} WMBT criteria → {m} tests across {k} files
- {j} JSON Schema contracts generated
- Handoff spec: docs/handoffs/ATDD-{wagon}-{feature}_HANDOFF.md
- Next: invoke implement-story with this spec to begin GREEN phase.
```
