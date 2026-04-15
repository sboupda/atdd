# ATDD Quick-Start Guide — Risk-Tiered Development

Three workflows for three risk levels. Pick the one that matches your work.

---

## Scenario 1: Tier 1 — Standard

**When:** docs, refactors, internal tooling, UI — anything that doesn't touch money or customer data.

1. Open Claude Code in your repo
2. Describe what you want to build
3. Claude classifies as tier 1 (or you confirm)
4. Claude implements, tests, commits
5. You review and merge

No ATDD commands required. Framework gates are optional.

**Optional ATDD tracking:**
```
atdd issue <slug>   # creates GitHub Issue + branch
```
Claude will use the branch and update the issue status automatically.

---

## Scenario 2: Tier 2 — Elevated

**When:** auth, KYC, contracts, pricing calculations — customer data but not money directly.

1. Open Claude Code in your repo
2. Describe what you want to build
3. Claude announces tier 2 classification at the start of the session
4. Claude plans → commits `[tier2] plan: ...`
5. Claude implements → commits `[tier2] implement: ...`
6. Claude tests → commits `[tier2] test: ...`
7. You review the commit trail and merge

The commits are the audit. Each phase boundary is a checkpoint you can inspect later.

**Optional ATDD tracking:**
```
atdd issue <slug>           # create issue + branch
atdd validate coder         # run before merge
```

---

## Scenario 3: Tier 3 — Critical / Money Paths

**When:** payments, settlement, FX execution, credit origination/scoring, portfolio management, reconciliation, regulatory reporting.

```
atdd issue <slug>           # 1. Create GitHub Issue + branch
```

**PLAN** — Codex (or a separate Claude session):
```
"Plan feature <slug>. Write plan.yaml and contracts.yaml to docs/handoffs/<slug>/"
```
- Codex writes handoff artifacts → commits `[tier3][plan]`
- **You review `plan.yaml`** — acceptance criteria complete? Scope correct?

**RED** — Claude Code:
```
"Implement feature <slug> from the handoff spec"
```
- Claude reads `docs/handoffs/<slug>/handoff-spec.yaml`
- Claude writes failing tests → commits `[tier3][red]`

**GREEN** — Claude Code (same session):
- Claude implements until tests pass → commits `[tier3][green]`

**REFACTOR** — Claude Code (same session):
- Claude cleans up → commits `[tier3][refactor]`

**VALIDATE** — Codex (or separate session):
```
"Coach-validate feature <slug>"
```
- Codex reads all artifacts + diffs → writes `docs/handoffs/<slug>/validation.yaml`
- Commits `[tier3][validate]`
- **You review `validation.yaml` + full diff** → merge or request changes

---

## Handoff Artifacts Reference

| File | Written by | Contains |
|---|---|---|
| `plan.yaml` | Planner (Codex) | Acceptance criteria, scope in/out, tier classification |
| `contracts.yaml` | Planner (Codex) | Interfaces, invariants, event schemas |
| `handoff-spec.yaml` | Planner/Tester | Files to change, test strategy, edge cases |
| `validation.yaml` | Coach (Codex) | Architecture compliance, cross-module impact, risk flags, recommendation |

---

## Acceptance Criteria Format

Structured YAML — not Gherkin:

```yaml
acceptance_criteria:
  - id: AC-01
    description: Settlement executes in correct priority order
    test_strategy: unit test with 5 waterfall scenarios
  - id: AC-02
    description: Failed settlement triggers automatic retry with backoff
    test_strategy: integration test with mock payment provider
```

---

## Tier Classification

1. Check `.atdd/tier_tags.yaml` in your repo (if it exists) — path-based override
2. If no file, apply the blast-radius rule:
   - Touches money or balances → **tier 3**
   - Touches customer data or compliance → **tier 2**
   - Everything else → **tier 1**
3. When in doubt, escalate

---

## Future: Automated Handoff Triggers

Not yet implemented. When the manual workflow is stable, a scheduled task can watch for new handoff artifacts on feature branches and notify via Dispatch. For now, handoffs are human-triggered: you review the plan, you say "go," you review the validation, you merge.

---

## Quick Reference

```
Tier 1: Claude Code → build → review → merge
Tier 2: Claude Code → [tier2] commits → review → merge
Tier 3: Codex plans → you review → Claude implements → Codex validates → you merge
```
