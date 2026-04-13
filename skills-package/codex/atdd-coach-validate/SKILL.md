---
name: atdd-coach-validate
description: ATDD Coach agent. Runs cross-wagon validation — contract consistency, event taxonomy compliance, architecture checks, and phase gate enforcement. Use after a wagon completes a phase (GREEN, SMOKE, REFACTOR) to validate system-level coherence before allowing the next phase. Also use as a reviewer in the TDD review loop to add ATDD-level findings alongside code-level review.
---

# ATDD Coach Validate

Validate cross-wagon coherence and enforce ATDD quality gates.

## Trigger Cues
- "validate wagon {name}"
- "check cross-wagon contracts"
- "coach review"
- "can we transition to {phase}?"
- "run ATDD validation"
- "check system coherence"
- After any phase completion in the TDD review loop

## Prerequisites

Run `atdd --version` to confirm CLI is installed. If not found:
```
ATDD CLI not installed. Run: pip install -e ".[dev]" from the ATDD repo root.
```

## Operating Sequence

### 1. Load State

- Read `.atdd/config.yaml` — project configuration
- Run `atdd status` — get current phase of all wagons
- Read `plan/_trains.yaml` and `plan/_wagons.yaml` — understand the system map
- Read `contracts/_contracts.yaml` and `contracts/_artifacts.yaml` — contract registry

### 2. Run Validators

Execute the full ATDD validation suite:

```bash
atdd validate              # All phases
atdd validate --coverage   # With coverage metrics
```

If validating a specific phase transition:
```bash
atdd validate planner   # Before PLANNED → RED
atdd validate tester    # Before RED → GREEN, or GREEN → SMOKE
atdd validate coder     # Before GREEN → SMOKE, or SMOKE → REFACTOR
atdd validate coach     # Cross-wagon coherence (always run)
```

### 3. Cross-Wagon Checks

Beyond what `atdd validate` catches, perform these manual checks:

**Contract consistency:**
- For each wagon that `produces_for` another wagon: does the producer's output schema match what the consumer expects?
- Are there contracts referenced by multiple wagons that have diverged?
- Do all API response schemas include the error codes from the shared error schema?

**Event taxonomy compliance:**
- Every event emitted by a wagon must be defined in the shared event taxonomy
- Every event consumed by a wagon must be emitted by exactly one producer wagon
- No orphaned events (defined but never emitted or consumed)

**Architecture compliance:**
- Domain layer has zero imports from application, integration, or presentation
- Dependencies point inward only (integration → application → domain)
- No wagon imports code from another wagon (contract-only communication)
- Composition roots (`composition.py`, `wagon.py`, or equivalent) exist and wire layers

**State machine integrity:**
- Current phase transition is valid per ATDD state machine
- All prerequisite phases completed
- No wagon stuck in an invalid state

### 4. Publish Findings

If running as part of the TDD review loop, publish findings in the same review format:

Create `docs/reviews/REVIEW_STORY-{id}_ROUND{n}_COACH.md`:

```markdown
# COACH REVIEW — {wagon_urn} — {phase} Phase

## Validator Results
- `atdd validate`: {PASS | FAIL with details}
- `atdd validate coach`: {PASS | FAIL with details}

## Cross-Wagon Findings

### Finding {n}: [{severity}] {title}
- **Scope:** Cross-wagon / architecture / contract / taxonomy
- **Evidence:** {what was checked and what failed}
- **Affected wagons:** {list}
- **Required change:** {specific action}
- **Acceptance proof expected:** {what the coder must show}

## Phase Gate Decision
- **Transition allowed:** `yes` | `no` | `conditional`
- **Conditions (if conditional):** {what must be fixed first}
- **Open P0/P1 findings:** {count}
```

### 5. Adjudicate Coder Responses

When the coder (Claude) responds to coach findings via `respond-to-review`:

- Verify ACCEPT responses include both code patch AND validator evidence (`atdd validate` output)
- For PUSH_BACK responses, evaluate whether the justification is valid at the system level (not just the wagon level)
- A fix that passes wagon-level tests but breaks cross-wagon contracts is still a P0
- Log final decision for each finding

### 6. Gate Decision

After all findings are resolved:

**Allow transition if:**
- `atdd validate` passes (all phases)
- No open P0 or P1 findings
- Cross-wagon contract checks pass
- Event taxonomy is consistent

**Block transition if:**
- Any P0/P1 finding remains open
- `atdd validate` fails
- Contract drift detected between wagons
- Architecture boundary violations exist

### 7. Record Transition

If gate passes:
```bash
atdd issue {wagon-slug} --status {next_phase}
```

Announce:
```
Coach validation complete for {wagon_urn}.
- Phase: {current} → {next}
- Validators: {pass_count}/{total_count} passed
- Cross-wagon checks: {status}
- Open findings: {count} (P0: {n}, P1: {n}, P2: {n})
```

## Integration with TDD Review Loop

This skill extends the `tdd-agent-review-loop` by adding a coach review layer:

1. **Standard review** (Codex as reviewer) — code quality, bugs, regressions
2. **Coach review** (this skill) — system coherence, contracts, architecture, phase gates

The coach review runs AFTER the standard review is complete and all P0/P1 code findings are resolved. This ensures we don't waste time on system-level checks while code-level bugs remain.

**Sequencing in the review loop:**
```
Coder submits handoff evidence
  → Reviewer runs standard review (code level)
    → Coder responds (ACCEPT/PUSH_BACK)
      → Loop until standard review passes
        → Coach runs cross-wagon validation (system level)
          → Coder responds to coach findings
            → Coach adjudicates and gates phase transition
```

## Completion Gate
- `atdd validate` passes
- No open P0 or P1 findings at coach level
- Phase transition recorded
- All cross-wagon contracts verified

## Local Policy Precedence
- If an `AGENTS.md` or `CLAUDE.md` exists in the repo, treat it as authoritative for paths, commands, environment, and naming conventions.
- Do not override local policy with generic defaults.
