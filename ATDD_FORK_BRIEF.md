# ATDD Fork — Adaptation Brief for Diool

## Context

Diool is rebooting legacy payment infrastructure assets into a full front-to-back technology spine. Legacy Diool functions as an **OMS** (Order Management System) — handling order routing (MoMo rails: MTN MoMo, Orange Money), execution (payout settlement), and position tracking (float/balance management). New systems being built on top: trade lifecycle, event management, booking, valuation, reporting.

This fork of [afokapu/atdd](https://github.com/afokapu/atdd) adapts the ATDD framework to govern the multi-system reboot.

## Why ATDD on top of existing TDD

- **TDD validates components work correctly.** ATDD validates the right thing is being built and that systems agree across boundaries.
- The core risk in a multi-system reboot on legacy OMS isn't "does my code work?" — it's "do my systems agree on what happened?"
- Every new system (booking, valuation, reporting) consumes OMS events. Contract drift between them is the failure mode ATDD prevents.

## Framework → Diool Domain Mapping

| ATDD Concept | Diool Equivalent |
|---|---|
| **Train** | End-to-end flow (payout lifecycle, trade lifecycle, booking flow) |
| **Wagon** | Bounded context / new system (event management, valuation, reporting, each partner integration) |
| **WMBT ("What Must Be True")** | Acceptance criteria from PRDs (e.g., Payout API PRD v0.1) |
| **Contracts (JSON Schema)** | Event taxonomy + API contracts between systems (PAYOUT_INITIATED, PAYOUT_SETTLED, PAYOUT_FAILED, etc.) |
| **Session** | Working session on a specific system or integration |
| **Coach validators** | Cross-system coherence checks (shared event schemas, URN uniqueness, contract consistency) |
| **SMOKE phase** | Testing against real MoMo sandbox endpoints, not mocks |

## What to Adapt

### Keep (stack-agnostic, high value)
- State machine: INIT → PLANNED → RED → GREEN → SMOKE → REFACTOR
- Phase transition quality gates with validator enforcement
- Agent separation: planner / tester / coder / coach
- Convention + schema enforcement per phase
- Cross-phase registry checks (coach layer)
- Train/wagon/WMBT planning structure
- Contract-driven inter-wagon communication rule
- Git workflow: conventional commits, phase-aligned commits
- Release gate with semver + tagging

### Rewire (stack-specific)
- **Default stack** (Supabase/FastAPI/Preact/Railway/Vercel) → replace with Diool's actual stack in convention YAML files
- **4-layer architecture conventions** → adapt layer names/boundaries to Diool's architecture
- **Test paths and co-location rules** → align to Diool repo structure
- **Dev server configs** → point to Diool services
- **Archetypes** (db, be, fe, contracts, etc.) → add Diool-specific archetypes (momo_rail, fx_partner, float_management, etc.)

### Add (Diool-specific)
- **Event taxonomy convention** — shared YAML defining all system events, validated by coach across all wagons
- **Partner integration wagon template** — Reasy, Odum Pay, Hub2 each as a wagon with standardized contract schemas
- **SLA acceptance criteria** — 99.99% reliability target as a WMBT enforced at SMOKE phase
- **OpenAPI spec generation** — contracts layer should produce OpenAPI 3.0 specs (open item from Payout API PRD)
- **Partner integration guide template** — generated from wagon contracts + WMBT (open item from PRD)

## Suggested First Move

Prototype one wagon through the full ATDD cycle: **Reasy payout integration**.

1. **INIT** → Define Reasy wagon with acceptance criteria from Payout API PRD
2. **PLANNED** → Generate RED tests from WMBT (FX quote, payout initiation, callback handling, failure modes)
3. **RED** → Write failing tests
4. **GREEN** → Implement against mocked MoMo endpoints
5. **SMOKE** → Test against real Reasy/MoMo sandbox
6. **REFACTOR** → Clean architecture pass

This validates the framework before applying it to the remaining five systems.

## Three Open Items from PRD That Connect Here

1. **OpenAPI 3.0 spec** → generate from ATDD contract schemas, not manually
2. **Partner integration guide** → generate from wagon WMBT + contracts + SMOKE test results
3. **Failure budget / escalation protocol** → encode as WMBT acceptance criteria, validate at SMOKE phase

## Key Architectural Principle

> "Wagons communicate via contracts only."

This is the OMS discipline. Every new system talks to legacy Diool and to each other exclusively through validated JSON Schema contracts. The coach layer enforces this. No ad-hoc integration.
