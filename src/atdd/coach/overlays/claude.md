# Claude-specific additions
# This content is appended to the base ATDD.md when syncing to CLAUDE.md

# Risk-Tiered Development Policy — Claude Role: IMPLEMENTER

In the dual-model Tier 3 workflow, Claude is the **implementer**.
Codex (or another planning agent) writes `plan.yaml`, `contracts.yaml`, and `handoff-spec.yaml`.
Claude reads those artifacts and executes RED → GREEN → SMOKE → REFACTOR.

**Before writing any Tier 3 code:**
1. Read `docs/handoffs/<feature-slug>/handoff-spec.yaml` — this is your spec.
2. Read `docs/handoffs/<feature-slug>/contracts.yaml` — these are the interfaces you must satisfy.
3. Read `docs/handoffs/<feature-slug>/plan.yaml` — confirm scope (what is IN, what is OUT).
4. If any of these files are missing, STOP and ask the planner (Codex) to complete the PLAN phase.

**Tier 3 commit discipline:**

| Phase    | Commit prefix           |
|----------|-------------------------|
| RED      | `[tier3][red]`          |
| GREEN    | `[tier3][green]`        |
| REFACTOR | `[tier3][refactor]`     |

Never skip directly to GREEN. Always commit failing tests first (`[tier3][red]`).

**After implementation:**
Request `atdd-coach-validate` to run cross-wagon validation and write `validation.yaml`.
Do not merge until coach validation passes.

**Tier 2:** Use `[tier2]` prefix on all phase commits. Flag PR for human review.
