# Codex-specific additions
# This content is appended to the base ATDD.md when syncing to AGENTS.md

# Risk-Tiered Development Policy — Codex Role: PLANNER

## Tier Definitions

Tier is determined by the blast radius of a bug, not the apparent complexity of the task.

**Tier 1 — Standard (default)**
Docs, internal tooling, refactors, UI, tests, admin scripts, data pipelines that don't affect
money. No special protocol — single model, framework gates only.

**Tier 2 — Elevated**
Customer data, contracts, calculations that feed Tier 3, external compliance — but not money
directly. Examples: KYC data handling, contract generation, pricing calculations, authentication.
Protocol: commit at each phase with `[tier2]` prefix; flag PR for human review before merge.

**Tier 3 — Critical (Money Paths)**
Any code path that initiates, modifies, or validates financial transactions.
Triggers: transfer, pay, disburse, settle, trade, reconcile, balance writes, FX rate application,
credit scoring that determines limits, regulatory reporting, anything irreversible within 24h.
Protocol: **dual-model workflow — Codex is the PLANNER, Claude is the implementer.**

### Per-Repo Override

If `.atdd/tier_tags.yaml` exists in the repo, use its `tier_3_paths` and `tier_2_paths` glob
lists to classify files. When the file is absent, apply the definitions above.

### Uncertainty Rule

If unsure between Tier 2 and Tier 3, treat as Tier 3. The cost of unnecessary rigor is low;
the cost of a money-path bug is high.

---

## Tier 3 Escalation Protocol — Codex as PLANNER

When any changed file matches a `tier_3_path`:

1. **Declare the tier** at the start of your response:
   `"This feature touches a Tier 3 path ({path}). Applying dual-model protocol."`

2. **Do NOT produce implementation code.** Your role is planning only.

3. **Write handoff artifacts** to `docs/handoffs/<feature-slug>/`:

   ```
   docs/handoffs/<feature-slug>/
     plan.yaml          ← your output: acceptance criteria, scope boundaries
     contracts.yaml     ← your output: interfaces, invariants, event schemas
     handoff-spec.yaml  ← your output: files to change, test strategy, edge cases
   ```

   Minimum `plan.yaml` structure:
   ```yaml
   feature: <feature-slug>
   tier: 3
   acceptance_criteria:
     - id: AC-01
       description: <what must be true>
       test_strategy: <how to verify>
   scope:
     in:
       - <explicit inclusions>
     out:
       - <explicit exclusions>
   ```

   Minimum `contracts.yaml` structure:
   ```yaml
   feature: <feature-slug>
   interfaces:
     - name: <InterfaceName>
       description: <what it does>
       schema: <inline JSON Schema or $ref>
   invariants:
     - <property that must always hold>
   ```

4. **Commit** the handoff artifacts:
   ```
   [tier3][plan] plan: <feature-slug>
   ```

5. **Hand off to Claude** (implementer) with:
   > "Tier 3 plan complete. Read `docs/handoffs/<feature-slug>/handoff-spec.yaml` before
   > writing any code. Implement RED tests first, then GREEN, then SMOKE, then REFACTOR.
   > Prefix every phase commit with `[tier3][red]`, `[tier3][green]`, etc."

6. **After implementation**, request `atdd-coach-validate` review before merge.
   Do not approve the merge yourself — coach validation is mandatory.

---

## Tier 2 Escalation Protocol

When any changed file matches a `tier_2_path` (and none match `tier_3_path`):

1. Declare the tier at the start of your response.
2. Include `[tier2]` prefix in every phase commit:
   `[tier2] plan: ...`, `[tier2] implement: ...`, `[tier2] test: ...`
3. Flag the PR for human review — do not approve it yourself.

---

## Handoff Artifact Store

```
docs/handoffs/<feature-slug>/
  plan.yaml           # planner output (Codex writes)
  contracts.yaml      # interface contracts (Codex writes)
  handoff-spec.yaml   # coder input: files, tests, edge cases (Codex writes)
  validation.yaml     # coach output (atdd-coach-validate writes)
```

Artifacts are written by agents and committed — they form the audit trail alongside git history.

---

## Phase Commit Prefixes (Tier 3)

| Phase | Agent  | Commit prefix          |
|-------|--------|------------------------|
| PLAN  | Codex  | `[tier3][plan]`        |
| RED   | Claude | `[tier3][red]`         |
| GREEN | Claude | `[tier3][green]`       |
| REFACTOR | Claude | `[tier3][refactor]` |
| VALIDATE | Coach | `[tier3][validate]`  |
