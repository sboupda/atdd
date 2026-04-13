# ATDD Implementation Plan — Diool Payout API

**Date:** 2026-03-31
**First Wagon:** Reasy Payout Integration
**Framework:** Fork of afokapu/atdd

---

## 1. Situation Assessment

### What the ATDD fork contains
A pure framework: YAML conventions, JSON schemas, Python validators, and the `atdd` CLI. No application code. Currently configured for Supabase Edge Functions + Flutter + Gun.js mesh — none of which Diool uses.

### What Diool has today
A legacy Java 8 monolith (`m3-core`) running Spring MVC 5.3.18, Hibernate 5.1.10, PostgreSQL on AWS RDS, deployed as a WAR to Tomcat. Two Angular frontends (customer portal v13, ops portal v10). A Python Flask middleware layer.

The codebase audit found **101 issues (28 critical)**: SQL injection in financial queries, plaintext production secrets in git, zero automated tests, EOL security frameworks, and god classes exceeding 6,800 LOC.

### What the Payout API PRD v0.2 defines
A B2B REST API for mobile money payouts (MTN MoMo, Orange Money) across CEMAC. 12 endpoints, 19 requirements, detailed acceptance criteria, 99.99% reliability target, 25K–125K payouts/day throughput. Launch partner: Reasy.

---

## 2. Key Architectural Decision

**The Payout API must be a new service, not an extension of the legacy monolith.**

Reasons:
- The legacy core has zero automated tests and 28 critical security findings — building on it violates the ATDD premise ("do my systems agree on what happened?")
- The PRD describes a stateless, horizontally scalable API with async queue-based payout execution — architecturally incompatible with the monolithic WAR
- The ATDD contract-driven approach requires clean wagon boundaries — impossible inside a 415-file monolith with no layer separation
- The legacy OMS remains the system of record for float, user accounts, and settlement — the Payout API talks to it via contracts, exactly as ATDD intends

**Stack decision needed:** The Payout API service needs its own stack. ATDD is stack-agnostic — conventions are YAML, validators are Python, contracts are JSON Schema. The runtime language is a configuration choice, not a framework constraint. The CTO decides this based on team strengths and hiring strategy.

The workload is I/O-bound (MoMo API calls, DB queries, webhook delivery). At 125K payouts/day peak, runtime performance is not the differentiator — network latency to MoMo operators is the bottleneck. Any modern language with good async support (Go, Java 17+, Python, Kotlin, Rust) works.

**What matters for ATDD:** The chosen stack must support the 4-layer architecture (presentation → application → domain → integration) with clean import boundaries that validators can check. Most languages support this via module/package conventions.

---

## 3. Implementation Phases

### Phase 0 — Rewire ATDD Conventions (before any wagon work)

**Goal:** Make the framework reflect Diool's actual stack so validators enforce the right rules.

#### 0.1 Update `technology.convention.yaml`
Replace:
- Supabase Edge Functions → [CTO stack decision: backend framework]
- Flutter → Angular (existing frontends; Payout API is API-only Phase 1)
- Gun.js mesh → PostgreSQL (via legacy OMS contracts)
- Sentry → TBD (or keep Sentry — it works)
- PostHog → Segment (already in ops-portal)

#### 0.2 Update `backend.convention.yaml`
Keep the 4-layer architecture (presentation → application → domain → integration). Update implementation examples to match chosen stack:
- Deno imports → [stack-specific import conventions]
- Supabase client → [stack-specific DB client / OMS HTTP client]
- Edge Function handlers → [stack-specific route handlers]

#### 0.3 Update `CLAUDE.md`
- `dev_servers.backend` → [stack-specific run command + URL]
- `dev_servers.frontend` → remove (API-only Phase 1)
- `dev_servers.supabase` → remove
- `code` paths → `payout-api/src/`, `payout-api/tests/`
- `tests` paths → `payout-api/tests/`

#### 0.4 Add Diool-specific archetypes
In coach conventions, add:
- `momo_rail` — MoMo network integration wagon (MTN, Orange)
- `fx_partner` — Partner integration wagon (Reasy, Odum Pay, Hub2)
- `float_management` — Pre-funded balance management
- `event_taxonomy` — Shared event definitions across wagons

#### 0.5 Add event taxonomy convention (new file)
`src/atdd/coach/conventions/event_taxonomy.convention.yaml`

Define shared events with JSON Schema:
- `PAYOUT_INITIATED` — order created, float debited
- `PAYOUT_PROCESSING` — sent to MoMo network
- `PAYOUT_CONFIRMED` — wallet credited
- `PAYOUT_FAILED` — terminal failure, float refunded
- `FLOAT_DEBITED` / `FLOAT_CREDITED` — balance movements
- `WEBHOOK_DELIVERED` / `WEBHOOK_FAILED` — callback lifecycle

Coach validator enforces: every wagon that emits or consumes an event must reference the taxonomy. No ad-hoc event names.

#### 0.6 Validate
```bash
atdd validate coach
```

---

### Phase 1 — INIT: Define the Reasy Wagon

**Agent:** Planner
**Deliverables:** Train path, wagon path, WMBT path, feature path

#### 1.1 Define the Train
**Train:** `payout-lifecycle`
**Description:** End-to-end payout flow from partner API call to wallet credit confirmation.
**Wagons in order:**
1. `payout-api` — REST API layer (partner-facing)
2. `payout-engine` — Async execution, retry logic, status tracking
3. `momo-adapter` — MTN/Orange network integration (Station Master pattern)
4. `float-ledger` — Pre-funded balance management (talks to legacy OMS)

#### 1.2 Define the Reasy Wagon (first wagon through the cycle)
The Reasy wagon is actually `payout-api` — the REST surface that Reasy integrates against. All partners use the same API; "Reasy" is the launch partner that validates it.

**Wagon URN:** `wagon:payout-api`
**Bounded context:** Partner-facing REST API for payout submission, status query, float visibility

#### 1.3 Extract WMBT from PRD v0.2

**Feature: Beneficiary Validation (REQ-01)**
- WMBT-01: `POST /beneficiaries/validate` returns account status within p95 <2s
- WMBT-02: Returns 400 if operator field missing or unsupported
- WMBT-03: Rate-limited to ≤100 req/min per partner

**Feature: Single Payout (REQ-02)**
- WMBT-04: `POST /orders` requires operator, recipient_name, idempotency_key
- WMBT-05: Amount must be positive integer (XAF); rejects non-integer, zero, negative
- WMBT-06: Float debited atomically before network send
- WMBT-07: Returns order ID + status `pending` within p95 <500ms
- WMBT-08: Duplicate idempotency key within 24h returns original order (HTTP 200, not 201)
- WMBT-09: Rejects if float insufficient with `insufficient_balance` error + current balance
- WMBT-10: `transaction_type` defaults to `C2C`; rejects unsupported values

**Feature: Batch Payout (REQ-03)**
- WMBT-11: All-or-nothing validation; per-order execution
- WMBT-12: Pre-checks total batch amount against float
- WMBT-13: p95 <5s for 500-order batch acknowledgment

**Feature: Transaction Status (REQ-04)**
- WMBT-14: `GET /orders/{id}` returns real-time status (not cached >30s)
- WMBT-15: Response includes full state transition timestamps + fee breakdown
- WMBT-16: p95 <300ms

**Feature: Webhooks (REQ-05)**
- WMBT-17: Webhook delivered within 30s of status change
- WMBT-18: Payload signed HMAC-SHA256 with partner-specific secret
- WMBT-19: 3 retries with exponential backoff (30s, 2min, 10min)

**Feature: Float Management (REQ-07, REQ-08)**
- WMBT-20: `GET /balance` returns available + pending within p95 <200ms
- WMBT-21: Balance reflects debits/credits within 5s
- WMBT-22: Low-balance alert within 60s of threshold breach

**Feature: Permissioning (REQ-10)**
- WMBT-23: Three roles: read, execute, admin
- WMBT-24: API keys 256-bit, stored as bcrypt hash, shown once on creation
- WMBT-25: Revoked key returns 401 within 5s

**Feature: Retry & Idempotency (REQ-11, REQ-12)**
- WMBT-26: Up to 3 retries with exponential backoff (5s, 30s, 2min)
- WMBT-27: No retry on non-transient errors (invalid number, wallet limit)
- WMBT-28: Failed payout refunds float within 60s

**Feature: Audit Trail (REQ-16)**
- WMBT-29: Append-only audit log, no UPDATE/DELETE
- WMBT-30: SHA-256 hash chain integrity
- WMBT-31: Entry created <1s of event

**Feature: Financial Accuracy (REQ-17)**
- WMBT-32: All amounts BIGINT, no FLOAT/DECIMAL
- WMBT-33: `gross_amount = net_amount + fee_amount` enforced at DB level
- WMBT-34: Banker's rounding for fee calculation

#### 1.4 Validate and transition
```bash
atdd validate planner   # All WMBT, wagon, train artifacts pass
atdd issue payout-api --status PLANNED
```

---

### Phase 2 — RED: Write Failing Tests

**Agent:** Tester
**Deliverables:** Test paths, contract paths, telemetry paths

#### 2.1 Generate contracts from WMBT
JSON Schema contracts for every API endpoint:
- `POST /orders` request/response schema
- `POST /orders/batch` request/response schema
- `POST /beneficiaries/validate` request/response schema
- `GET /orders/{id}` response schema
- `GET /orders` response schema (paginated)
- `GET /balance` response schema
- `GET /health` response schema
- `GET /operators` response schema
- Error response schema (standardized error codes from PRD Appendix C)
- Webhook payload schema

#### 2.2 Write RED tests
Tests derived directly from WMBT. Each test file named per URN convention.

Priority order (tests that validate the hardest contract boundaries first):
1. **Financial accuracy tests** (WMBT-32, 33, 34) — integer amounts, fee invariant, rounding
2. **Idempotency tests** (WMBT-08, 28) — duplicate detection, float refund
3. **Float atomicity tests** (WMBT-06, 09, 21) — debit-before-send, insufficient balance
4. **Payout lifecycle tests** (WMBT-04, 05, 07, 14, 15) — order creation, status flow
5. **Webhook tests** (WMBT-17, 18, 19) — signing, delivery, retry
6. **Permissioning tests** (WMBT-23, 24, 25) — role enforcement, key lifecycle
7. **Batch tests** (WMBT-11, 12, 13) — all-or-nothing, batch float check
8. **Validation tests** (WMBT-01, 02, 03) — beneficiary check, rate limiting
9. **Audit trail tests** (WMBT-29, 30, 31) — immutability, hash chain
10. **SLA tests** (latency, throughput) — deferred to SMOKE

#### 2.3 Validate and transition
```bash
atdd validate tester    # All tests exist, follow naming convention, reference contracts
atdd issue payout-api --status RED
```

All tests fail (RED). This is correct.

---

### Phase 3 — GREEN: Make Tests Pass

**Agent:** Coder
**Deliverables:** Code paths, all tests passing

#### 3.1 Scaffold the Payout API service
Regardless of stack choice, the 4-layer structure is mandatory:
```
payout-api/
├── src/
│   ├── domain/           # Pure business logic, no imports from other layers
│   │   ├── models         # Order, Balance, Partner, AuditEntry
│   │   ├── events         # Event types from taxonomy
│   │   └── rules          # Fee calculation, idempotency, validation
│   ├── application/      # Use cases, orchestration
│   │   ├── create_order
│   │   ├── create_batch
│   │   ├── validate_beneficiary
│   │   ├── query_orders
│   │   └── manage_webhooks
│   ├── integration/      # External adapters
│   │   ├── momo_adapter          # MTN/Orange API client
│   │   ├── float_adapter         # Legacy OMS float queries
│   │   ├── webhook_dispatcher    # Outbound webhook delivery
│   │   └── audit_store           # Append-only audit persistence
│   └── presentation/     # Routes, request/response models
│       ├── routes/
│       │   ├── orders
│       │   ├── beneficiaries
│       │   ├── balance
│       │   ├── health
│       │   ├── operators
│       │   ├── settings
│       │   └── keys
│       └── middleware/    # Auth, rate limiting, CORS
├── tests/                # Co-located per ATDD convention
├── contracts/            # JSON Schema files
└── [stack-specific build config]
```

File extensions and module conventions depend on stack choice. The layer structure does not.

#### 3.2 Implementation order
Follow test priority from Phase 2:
1. Domain layer first (models, rules, fee calculation) — passes financial accuracy tests
2. Application layer (create_order use case) — passes idempotency + float tests
3. Presentation layer (routes) — passes lifecycle + API contract tests
4. Integration layer (mocked adapters) — passes webhook + validation tests

#### 3.3 Agent workflow for GREEN phase
This is where the existing Claude/Codex TDD skills plug in:
1. `atdd-generate-red` (new skill) outputs a handoff spec from ATDD's RED artifacts
2. `implement-story` (Claude) picks up the handoff spec, codes Red→Green→Refactor
3. `tdd-agent-review-loop` (Codex) reviews, publishes findings
4. `respond-to-review` (Claude) addresses findings with ACCEPT/PUSH_BACK
5. Loop until completion gate passes (including `atdd validate coder`)

#### 3.3 Validate and transition
```bash
atdd validate coder     # All tests pass, architecture layers correct
atdd issue payout-api --status GREEN
```

---

### Phase 4 — SMOKE: Test Against Real Infrastructure

**Agent:** Tester
**Deliverables:** Smoke test paths

#### 4.1 Smoke test targets
- **MoMo Sandbox:** Real HTTP calls to MTN MoMo / Orange Money sandbox APIs
- **PostgreSQL:** Real database writes/reads (not in-memory)
- **Webhook delivery:** Real HTTP POST to a test endpoint
- **Auth:** Real API key validation flow
- **Float:** Real balance debit/credit against test ledger

#### 4.2 SLA smoke tests
- Single payout p95 <500ms (acknowledgment)
- Balance query p95 <200ms
- Webhook delivery <30s
- Batch 500 orders p95 <5s

#### 4.3 Validate and transition
```bash
atdd validate tester    # Smoke tests pass against real infrastructure
atdd issue payout-api --status SMOKE
```

---

### Phase 5 — REFACTOR: Clean Architecture

**Agent:** Coder
**Deliverables:** Refactored code, all tests still pass

#### 5.1 Architecture compliance
- Domain layer has zero imports from application/integration/presentation
- Dependencies point inward only
- Station Master pattern for MoMo adapters (Direct/HTTP/Fake)
- Composition root (`composition.py`) wires all layers — survives refactoring
- All ATDD URN headers in file docstrings

#### 5.2 Validate and transition
```bash
atdd validate coder     # Architecture validators pass, all tests still green
atdd issue payout-api --status REFACTOR
```

---

## 4. What This Plan Does NOT Cover (Yet)

- **Remaining wagons:** `payout-engine`, `momo-adapter`, `float-ledger` — each goes through the same ATDD cycle after `payout-api` validates the framework
- **Legacy remediation:** The 101 audit findings in `m3-core` are a separate workstream; ATDD governs new systems, not legacy cleanup
- **Partner dashboard:** Out of scope per PRD (Phase 2+)
- **XOF corridors:** Same architecture, different network integrations (Phase 2)
- **OpenAPI spec generation:** Wire after contracts are stable post-GREEN
- **Partner integration guide:** Generate from wagon WMBT + contracts post-REFACTOR

---

## 5. Open Decisions

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| D1 | Payout API stack | Python/FastAPI (recommended) vs Java/Spring Boot 3 | Determines convention rewiring in Phase 0 |
| D2 | Database for Payout API | Shared PostgreSQL RDS vs dedicated instance | Affects float-ledger wagon boundary |
| D3 | How Payout API talks to legacy OMS | Direct DB read vs internal REST API vs event queue | Defines the contract between payout-api and float-ledger wagons |
| D4 | CI/CD for new service | GitHub Actions + Docker (likely) vs existing manual deploy | Affects SMOKE phase infrastructure |
| D5 | Hosting | Same AWS region (eu-central-1) vs different | Latency to MoMo APIs in Cameroon |

---

## 6. Suggested Sequence

```
Week 1:  Phase 0 — Rewire conventions + decide D1-D5
Week 2:  Phase 1 — INIT (wagon + WMBT from PRD)
Week 2:  Phase 2 — RED (contracts + failing tests)
Week 3-4: Phase 3 — GREEN (implement, make tests pass)
Week 5:  Phase 4 — SMOKE (real MoMo sandbox, real DB)
Week 5:  Phase 5 — REFACTOR (clean architecture)
Week 6:  Second wagon (payout-engine) enters INIT
```

This is aggressive but realistic if D1-D5 are resolved in Week 1.
