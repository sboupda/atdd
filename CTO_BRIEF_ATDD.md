# ATDD for Diool — Technical Brief for CTO Review

**From:** Serge Boupda
**Date:** March 31, 2026
**Framework:** Fork of [afokapu/atdd](https://github.com/afokapu/atdd)

---

## What ATDD Is

Acceptance Test Driven Development. A lifecycle framework that wraps around TDD to govern multi-system builds. Where TDD validates "does my code work?", ATDD validates "are my systems building the right thing, and do they agree across boundaries?"

The framework enforces a state machine: **INIT → PLANNED → RED → GREEN → SMOKE → REFACTOR**. Each phase has validators that must pass before transitioning to the next. Four agent roles (planner, tester, coder, coach) own different phases. No code is written until acceptance criteria are defined and contracts are validated.

## Why It Matters for Diool — Specifically

We are rebooting legacy payment infrastructure into multiple new systems: Payout API, trade lifecycle, event management, booking, valuation, reporting. Each new system consumes events from the legacy OMS. **The core risk isn't "does my code work?" — it's "do my systems agree on what happened?"**

The recent audit of `m3-core` found 101 issues (28 critical). The most damaging category wasn't security — it was the complete absence of systematic testing and contract enforcement. Every system talks to the OMS through ad-hoc integrations with no validated contracts. When we build 5+ new systems on top of this, contract drift becomes the primary failure mode.

ATDD prevents this by enforcing:

**Contract-driven communication.** Every wagon (bounded context) communicates exclusively through JSON Schema contracts validated by the coach layer. No ad-hoc integration. If the Payout API emits `PAYOUT_CONFIRMED` and the booking system consumes it, both reference the same schema — and validators catch drift before code ships.

**Tests before code, always.** The RED phase generates failing tests from acceptance criteria before any implementation. We currently have zero automated tests in the core. ATDD makes it structurally impossible to write code without tests.

**Architecture enforcement.** Validators check 4-layer compliance (presentation → application → domain → integration), dependency direction (inward only), and wagon isolation. The audit found god classes (6,841 LOC), entities leaking to REST responses, and no layer boundaries. ATDD validators catch these structurally, not through code review.

**Cross-system coherence.** The coach layer validates that all wagons reference a shared event taxonomy, that URNs are unique, and that contracts are consistent across the system. No single-service TDD framework does this.

## What We Already Have That Fits Inside

Our existing Claude/Codex TDD workflow — `implement-story`, `tdd-agent-review-loop`, `respond-to-review` — operates as a proven inner loop for coding: Codex architects and reviews, Claude codes and responds. ATDD doesn't replace this. It wraps around it:

- ATDD's **planner** produces wagons with acceptance criteria → these feed into story specs
- ATDD's **tester** generates RED tests and contracts → these become the handoff specs for `implement-story`
- The **Claude/Codex review loop** executes the GREEN and REFACTOR phases
- ATDD's **coach validators** run as a higher-order gate that checks cross-system concerns the inner loop can't see

The inner loop handles "is this story implemented correctly?" ATDD handles "is this story the right thing to build, and does it fit the system?"

## What the Audit Would Have Looked Like Under ATDD

| Audit Finding | ATDD Phase That Catches It |
|---|---|
| Zero automated tests (AUD-015) | RED phase: structurally impossible to skip — tests generated before code |
| SQL injection in financial queries (AUD-007) | RED phase: contract tests validate parameterized queries; SMOKE tests against real DB catch injection patterns |
| Entities serialized directly to REST (architectural) | REFACTOR validators: domain layer cannot import from presentation; response schemas enforced via contracts |
| God classes (6,841 LOC UserAccountController) | REFACTOR validators: architecture compliance checks, bounded wagon contexts prevent unbounded growth |
| No input validation (AUD-010) | RED phase: contract schemas define valid inputs; tests generated from schemas enforce validation |
| Fragmented Auth0 RBAC (AUD-018) | Coach validators: cross-wagon contract check catches inconsistent permission models |
| Hardcoded secrets (AUD-001) | Not directly caught by ATDD — this is a DevSecOps concern. ATDD handles system correctness, not ops hygiene. (Honest answer.) |

## Proof of Concept: Reasy Payout Wagon

The Payout API PRD v0.2 defines 19 requirements with detailed acceptance criteria. The first wagon through the ATDD cycle would be the partner-facing REST API for the Reasy integration. This validates the framework end-to-end on a real, high-stakes deliverable (25K payouts/day, 99.99% reliability target).

The PRD's acceptance criteria map directly to ATDD "What Must Be True" (WMBT) criteria — 34 concrete, testable statements extracted from REQ-01 through REQ-19. These drive contract generation, test generation, and architecture validation through the full cycle.

Timeline estimate: 5–6 weeks for one wagon through all phases, including convention rewiring.

## What ATDD Costs

**Setup time:** ~1 week to rewire conventions from the framework's default stack to ours. The framework is stack-agnostic — conventions are YAML, validators are Python, contracts are JSON Schema. Language/framework choice is a configuration, not a constraint.

**Per-wagon overhead:** Each wagon goes through the full lifecycle instead of jumping straight to code. This adds ~2–3 days of planning and contract work upfront. The tradeoff is catching integration failures before they reach production instead of after.

**Learning curve:** The framework has its own vocabulary (trains, wagons, WMBT, coach) and a CLI (`atdd`) for validation. The concepts map cleanly to our domain (trains = end-to-end flows, wagons = bounded contexts, WMBT = acceptance criteria from PRDs). The distributed team (Paris, Nairobi, São Paulo, Yaoundé) benefits from the shared structure — everyone works against the same contracts and validators regardless of timezone.

## Recommendation

Adopt ATDD as the governance layer for the multi-system reboot. Keep the existing Claude/Codex TDD workflow as the execution engine for GREEN and REFACTOR phases. Run the Reasy payout wagon as the proof-of-concept to validate the framework before applying it to remaining systems.

The framework was built by a colleague in Nairobi who is available to support adoption. The fork is already in our repo.

## Open Decisions for CTO

1. **Stack for Payout API service** — language/framework for the new service (doesn't affect ATDD adoption, but affects convention configuration)
2. **Database topology** — shared RDS vs dedicated instance for new services
3. **Integration pattern with legacy OMS** — internal REST API vs event queue (determines contract shape between wagons)
