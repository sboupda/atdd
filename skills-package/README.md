# ATDD Skills Package

Skills for Claude and Codex that integrate with the ATDD framework.

## Installation

### Prerequisites
```bash
cd /path/to/atdd-fork
pip install -e ".[dev]"
atdd --version  # should show 1.16.2
```

### Claude Skills (copy to ~/.claude/skills/)
```bash
# Updated existing skills
cp -r skills-package/claude/implement-story/ ~/.claude/skills/implement-story/
cp -r skills-package/claude/respond-to-review/ ~/.claude/skills/respond-to-review/

# New skill
cp -r skills-package/claude/atdd-generate-red/ ~/.claude/skills/atdd-generate-red/
```

### Codex Skills (copy to ~/.codex/skills/)
```bash
cp -r skills-package/codex/atdd-plan-wagon/ ~/.codex/skills/atdd-plan-wagon/
cp -r skills-package/codex/atdd-coach-validate/ ~/.codex/skills/atdd-coach-validate/
```

## Workflow

```
Codex: atdd-plan-wagon      → wagon + WMBT from PRD
Claude: atdd-generate-red   → failing tests + handoff spec
Claude: implement-story     → Red → Green → Refactor
Codex:  tdd-agent-review-loop → code review
Claude: respond-to-review   → ACCEPT/PUSH_BACK
Codex:  atdd-coach-validate → cross-wagon validation + phase gate
```

## Backward Compatibility

The updated `implement-story` and `respond-to-review` skills are backward-compatible. Without `.atdd/config.yaml`, they fall back to `conda run -n quant pytest` defaults. No disruption to non-ATDD projects.
