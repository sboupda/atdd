---
name: atdd-plan-wagon
description: ATDD Planner agent. Reads a PRD from Notion (or local file), extracts WMBT acceptance criteria, and produces wagon + train + feature artifacts that pass atdd validate planner. Use at the start of a new wagon lifecycle, before any tests or code exist. Codex acts as the architect — defining what must be true before Claude codes.
---

# ATDD Plan Wagon

Architect a new wagon through the ATDD INIT → PLANNED phases.

## Trigger Cues
- "plan wagon {name}"
- "extract WMBT from PRD"
- "define acceptance criteria for {feature}"
- "start ATDD cycle for {wagon}"
- "what must be true for {feature}?"

## Prerequisites

Run `atdd --version` to confirm CLI is installed. If not found:
```
ATDD CLI not installed. Run: pip install -e ".[dev]" from the ATDD repo root.
```

## Operating Sequence

### 1. Load Context

**If PRD is in Notion:**
- Search Notion for the PRD by name or URL
- Fetch the full page content
- Extract: requirements (REQ-xx), acceptance criteria (AC-xx), personas, success metrics, API surface, error codes, non-functional requirements

**If PRD is a local file:**
- Read the file from the specified path
- Same extraction as above

**Also read:**
- `.atdd/config.yaml` — project configuration
- `plan/_trains.yaml` — existing trains (avoid duplicates)
- `plan/_wagons.yaml` — existing wagons
- ATDD planner conventions: `src/atdd/planner/conventions/*.yaml`
- ATDD planner schemas: `src/atdd/planner/schemas/*.json`

### 2. Define the Train (if new)

If the wagon belongs to a new end-to-end flow, define the train:

```yaml
# plan/_trains.yaml (append)
- urn: "train:{train-name}"
  description: "{end-to-end flow description}"
  wagons:
    - "wagon:{wagon-1}"
    - "wagon:{wagon-2}"
    # ... in execution order
```

If the train already exists, skip this step and reference the existing train.

### 3. Define the Wagon

Create wagon artifact per planner conventions:

```yaml
# plan/{train}/{wagon}.yaml
urn: "wagon:{wagon-name}"
train: "train:{train-name}"
description: "{bounded context description}"
features:
  - "{feature-1}"
  - "{feature-2}"
dependencies:
  consumes_from: []  # other wagons this wagon reads contracts from
  produces_for: []   # other wagons that read this wagon's contracts
```

### 4. Extract WMBT Criteria

For each requirement in the PRD, produce one or more WMBT (What Must Be True) criteria:

**Rules:**
- Each WMBT maps to exactly one PRD acceptance criterion (AC-xx)
- WMBT IDs are sequential: WMBT-01, WMBT-02, ...
- Each WMBT must be testable — it can be verified by a test or validator
- Include the PRD requirement ID as provenance (REQ-xx → WMBT-yy)
- Group WMBTs by feature

**Output:**
```yaml
# plan/{train}/{wagon}_wmbt.yaml
wagon: "wagon:{wagon-name}"
features:
  - name: "{feature-name}"
    source: "REQ-{xx}"
    wmbt:
      - id: "WMBT-01"
        criterion: "{testable statement}"
        source_ac: "AC-{xxa}"
        harness: "unit | contract | integration | smoke"
      - id: "WMBT-02"
        criterion: "{testable statement}"
        source_ac: "AC-{xxb}"
        harness: "unit | contract | integration | smoke"
```

**Harness types:**
- `unit` — pure logic, no I/O (fee calculation, validation rules, state transitions)
- `contract` — JSON Schema validation (request/response shapes, event schemas)
- `integration` — requires mocked external service (MoMo adapter, webhook delivery)
- `smoke` — requires real infrastructure (live API, real DB, real network)

### 5. Define Features

```yaml
# plan/{train}/_features.yaml (append)
- name: "{feature-name}"
  wagon: "wagon:{wagon-name}"
  wmbt_count: {n}
  description: "{what this feature does}"
```

### 6. Identify Events (if applicable)

If the wagon emits or consumes events, list them:

```yaml
# In wagon definition or separate events section
events:
  emits:
    - name: "{EVENT_NAME}"
      description: "{when this event fires}"
      schema: "contracts/{wagon}/{event_name}.json"
  consumes:
    - name: "{EVENT_NAME}"
      source_wagon: "wagon:{other-wagon}"
```

### 7. Validate

Run: `atdd validate planner`

All artifacts must pass:
- Wagon URN is unique
- Train references are valid
- WMBT criteria are well-formed
- Features are linked to wagon
- Cross-references are consistent

### 8. Transition

Run: `atdd issue {wagon-slug} --status PLANNED` (use the wagon slug, e.g. `payout-api`, not the full URN)

### 9. Handoff to Tester

Announce:
```
PLANNED phase complete for wagon:{wagon-name}.
- {n} features defined
- {m} WMBT criteria extracted from PRD
- {k} events identified
- Next: atdd-generate-red to produce RED tests and contracts.
```

## Review Standards

When reviewing the planning output (self-review or peer review):
- Every WMBT must trace back to a PRD acceptance criterion
- No criterion invented beyond what the PRD states
- Wagon boundaries must be clean — no overlapping bounded contexts
- Dependencies between wagons must be explicit
- Events must reference the shared taxonomy

## Completion Gate
- `atdd validate planner` passes
- All WMBT criteria have provenance (source_ac field)
- Wagon status is PLANNED
- No orphaned features or unreferenced WMBT

## Local Policy Precedence
- If an `AGENTS.md` or `CLAUDE.md` exists in the repo, treat it as authoritative for paths, commands, environment, and naming conventions.
- Do not override local policy with generic defaults.
