---
name: implement-story
description: Implement a backlog story as the Coder role using strict Red -> Green -> Refactor TDD. Use when a story is in_progress and has a handoff spec. Supports both standalone TDD and ATDD-governed workflows.
argument-hint: [story-id]
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(pytest:*), Bash(conda:*), Bash(python*:*), Bash(bash scripts/*:*), Bash(atdd:*)
---

Implement story **$ARGUMENTS** as the Coder in the TDD agent workflow.

## 0. Resolve Project Config

Check for test runner configuration in this order:
1. `.atdd/config.yaml` → read `test_runner` section
2. `tdd.config.yaml` → fallback for non-ATDD projects
3. Hardcoded defaults (below) if neither file exists

**Defaults (used only when no config file found):**
```yaml
test_runner:
  single: "conda run -n quant pytest -v {test_files} --no-header"
  suite: "conda run -n quant pytest -q"
  check: "bash scripts/check.sh"
  env: null
```

**ATDD detection:** If `.atdd/config.yaml` exists, this is an ATDD-governed project. Set `atdd_mode = true`. Additional gates apply at completion (see section 6).

**ATDD dependency check (when `atdd_mode = true`):** Run `atdd --version`. If not found, stop and instruct:
```
ATDD CLI not installed. Run: pip install -e ".[dev]" from the ATDD repo root.
```

## 1. Orient

- Read `PLAN_Backlog.md` — confirm $ARGUMENTS is `in_progress`.
- Look for the handoff spec in this order:
  1. `docs/handoffs/` matching $ARGUMENTS (standard TDD)
  2. `docs/handoffs/ATDD-{wagon}-{feature}_HANDOFF.md` (ATDD-generated spec from `atdd-generate-red`)
- Read the files listed in the spec's "Files allowed to change" and related test files.
- If the spec has a "Contracts" section (ATDD), read the referenced JSON Schema files.

## 2. Red Phase

Write ALL tests from the spec's TDD plan **before any implementation code**.

- Tests must fail for the right reason (`KeyError`, `AssertionError` on missing behavior — not `ImportError`).
- Run new tests: `{test_runner.single}` (from config)
- Run existing suite excluding new tests to confirm no breakage.
- Record failure output as evidence.

## 3. Green Phase

Implement the **minimum code** to make all tests pass.

- Only modify files listed in the spec's "Files allowed to change".
- Run targeted tests, then full suite: `{test_runner.suite}` (from config)
- Run validation commands from spec section 5.

## 4. Refactor Phase

Only refactors explicitly allowed by the spec. Keep tests green.

## 5. Docs + Evidence

- Update `README.md` and any policy docs mentioned in the spec.
- Write `docs/handoffs/STORY-{id}_HANDOFF_EVIDENCE.md` using the template at [handoff-evidence-template.md](handoff-evidence-template.md).
- For a real example of a completed handoff, see [example-d4-handoff.md](example-d4-handoff.md).

## 6. Completion Gate

ALL must pass before declaring done:

- `{test_runner.suite}` green (from config)
- `{test_runner.check}` green (from config)
- No stale generated files in repo root
- Handoff evidence written
- Docs updated

**ATDD additional gates (only when `atdd_mode = true`):**
- `atdd validate coder` green — architecture layers, boundary compliance, contract consistency
- Phase transition recorded: note the current ATDD phase (GREEN or REFACTOR) in handoff evidence
- Contracts validated: all JSON Schema contracts referenced in the spec pass `atdd validate tester`

## Rules

- Never modify engine economics unless spec explicitly allows it.
- Never remove or rename legacy fields/columns unless spec explicitly allows it.
- Safe division for rate calculations (check denominator > 0).
- `float()` to convert numpy scalars before putting in dicts/CSV.
