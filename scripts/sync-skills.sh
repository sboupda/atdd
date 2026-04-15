#!/usr/bin/env bash
# sync-skills.sh — copy agent skills from skills-package/ to agent skill directories
#
# Reads .atdd/config.yaml to determine which agents are enabled, then copies
# skills from skills-package/{agent}/ to each agent's configured skill directory.
#
# Usage:
#   scripts/sync-skills.sh            # sync all enabled agents
#   scripts/sync-skills.sh --dry-run  # show what would be copied, copy nothing
#   scripts/sync-skills.sh --agent claude  # sync a single agent only
#
# Target directory defaults (overridable in .atdd/config.yaml under sync.skill_dirs):
#   claude  →  ~/.claude/skills/
#   codex   →  ~/.codex/skills/
#   gemini  →  ~/.gemini/skills/
#   qwen    →  ~/.qwen/skills/

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILLS_PACKAGE="${REPO_ROOT}/skills-package"
CONFIG_FILE="${REPO_ROOT}/.atdd/config.yaml"

DRY_RUN=false
FILTER_AGENT=""

# Default skill directories per agent (bash 3 compatible — no associative arrays)
default_skill_dir_for() {
    case "$1" in
        claude) echo "${HOME}/.claude/skills" ;;
        codex)  echo "${HOME}/.codex/skills" ;;
        gemini) echo "${HOME}/.gemini/skills" ;;
        qwen)   echo "${HOME}/.qwen/skills" ;;
        *)      echo "" ;;
    esac
}

# Counters
SYNCED=0       # actually copied (live run)
WOULD_COPY=0   # would be copied (dry-run)
SKIPPED=0      # source missing or agent unknown
ERRORS=0

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --agent)
            FILTER_AGENT="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            echo "Run with --help for usage." >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# YAML helpers — pure bash, no external dependencies
#
# These handle the simple YAML patterns found in .atdd/config.yaml:
#   - Indented list items under a known key (yaml_list)
#   - Single scalar value under a dotted key path (yaml_scalar)
#
# Limitations (acceptable for this use case):
#   - Does not support flow-style YAML ({a: b})
#   - Does not handle multi-line strings
#   - Key matching is indent-aware but not full YAML-spec compliant
# ---------------------------------------------------------------------------

# yaml_list DOTTED_KEY FILE
# Extract a block-sequence list under a dotted key path.
# Example: yaml_list "sync.agents" .atdd/config.yaml
yaml_list() {
    local dotted_key="$1" file="$2"
    # Convert dotted path to array of keys
    IFS='.' read -ra KEY_PARTS <<< "${dotted_key}"
    local depth=0
    local max_depth=${#KEY_PARTS[@]}
    local in_list=false
    local current_indent=-1

    while IFS= read -r line; do
        # Skip blank lines and pure comments
        [[ "${line}" =~ ^[[:space:]]*$ ]] && continue
        [[ "${line}" =~ ^[[:space:]]*# ]] && continue

        # Measure indentation
        local stripped="${line#"${line%%[! ]*}"}"  # remove leading spaces
        local indent=$(( ${#line} - ${#stripped} ))

        if [[ "${in_list}" == true ]]; then
            # If we hit a line at or below the list's indent that isn't a list item, stop
            if [[ ${indent} -le ${current_indent} && ! "${stripped}" =~ ^-[[:space:]] ]]; then
                break
            fi
            # Emit list items
            if [[ "${stripped}" =~ ^-[[:space:]]+(.*) ]]; then
                echo "${BASH_REMATCH[1]}"
            fi
            continue
        fi

        # Try to match each key in the path
        if [[ ${depth} -lt ${max_depth} ]]; then
            local expected_key="${KEY_PARTS[${depth}]}"
            if [[ "${stripped}" =~ ^${expected_key}[[:space:]]*: ]]; then
                depth=$(( depth + 1 ))
                current_indent=${indent}
                if [[ ${depth} -eq ${max_depth} ]]; then
                    in_list=true
                fi
            fi
        fi
    done < "${file}"
}

# yaml_scalar DOTTED_KEY FILE
# Extract a scalar value for a dotted key path.
# Example: yaml_scalar "sync.skill_dirs.claude" .atdd/config.yaml
yaml_scalar() {
    local dotted_key="$1" file="$2"
    IFS='.' read -ra KEY_PARTS <<< "${dotted_key}"
    local depth=0
    local max_depth=${#KEY_PARTS[@]}

    while IFS= read -r line; do
        [[ "${line}" =~ ^[[:space:]]*$ ]] && continue
        [[ "${line}" =~ ^[[:space:]]*# ]] && continue

        local stripped="${line#"${line%%[! ]*}"}"

        if [[ ${depth} -lt ${max_depth} ]]; then
            local expected_key="${KEY_PARTS[${depth}]}"
            if [[ "${stripped}" =~ ^${expected_key}:[[:space:]]*(.*) ]]; then
                depth=$(( depth + 1 ))
                local value="${BASH_REMATCH[1]}"
                if [[ ${depth} -eq ${max_depth} && -n "${value}" ]]; then
                    # Strip inline comment and surrounding quotes
                    value="${value%%#*}"
                    value="${value%"${value##*[! ]}"}"  # rtrim
                    value="${value#\'}" ; value="${value%\'}"
                    value="${value#\"}" ; value="${value%\"}"
                    echo "${value}"
                    return
                fi
            fi
        fi
    done < "${file}"
}

# ---------------------------------------------------------------------------
# Load enabled agents from config
# ---------------------------------------------------------------------------

load_agents() {
    if [[ ! -f "${CONFIG_FILE}" ]]; then
        echo "warning: .atdd/config.yaml not found — no agents configured" >&2
        return
    fi

    if [[ -n "${FILTER_AGENT}" ]]; then
        echo "${FILTER_AGENT}"
        return
    fi

    yaml_list "sync.agents" "${CONFIG_FILE}" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Resolve target skill directory for an agent
# ---------------------------------------------------------------------------

target_dir_for() {
    local agent="$1"

    # Check for override in config: sync.skill_dirs.<agent>
    if [[ -f "${CONFIG_FILE}" ]]; then
        local override
        override="$(yaml_scalar "sync.skill_dirs.${agent}" "${CONFIG_FILE}" 2>/dev/null || true)"
        if [[ -n "${override}" ]]; then
            # Expand ~ manually since it won't expand inside double quotes
            echo "${override/#\~/${HOME}}"
            return
        fi
    fi

    # Fall back to built-in default
    default_skill_dir_for "${agent}"
}

# ---------------------------------------------------------------------------
# Sync one skill directory
# ---------------------------------------------------------------------------

sync_skill() {
    local skill_dir="$1"   # e.g. skills-package/codex/atdd-coach-validate
    local target_dir="$2"  # e.g. ~/.codex/skills
    local skill_name
    skill_name="$(basename "${skill_dir}")"
    local dest="${target_dir}/${skill_name}"

    if "${DRY_RUN}"; then
        echo "  [dry-run] would copy: ${skill_dir#"${REPO_ROOT}/"} → ${dest}"
        (( WOULD_COPY++ )) || true
        return
    fi

    # Create target directory if needed
    if [[ ! -d "${target_dir}" ]]; then
        mkdir -p "${target_dir}"
    fi

    # Copy (rsync-style semantics via cp -r; idempotent)
    if cp -r "${skill_dir}" "${target_dir}/"; then
        echo "  synced: ${skill_name} → ${dest}"
        (( SYNCED++ )) || true
    else
        echo "  error: failed to copy ${skill_name}" >&2
        (( ERRORS++ )) || true
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if "${DRY_RUN}"; then
    echo "=== sync-skills (dry run) ==="
else
    echo "=== sync-skills ==="
fi
echo ""

AGENTS_RAW="$(load_agents)"

if [[ -z "${AGENTS_RAW}" ]]; then
    echo "No agents found. Add agents to .atdd/config.yaml under sync.agents."
    exit 0
fi

while IFS= read -r agent; do
    agent="$(echo "${agent}" | tr -d '[:space:]')"   # strip whitespace
    [[ -z "${agent}" ]] && continue

    source_dir="${SKILLS_PACKAGE}/${agent}"
    target_dir="$(target_dir_for "${agent}")"

    echo "Agent: ${agent}"

    # Source dir must exist
    if [[ ! -d "${source_dir}" ]]; then
        echo "  skip: no skills directory at ${source_dir#"${REPO_ROOT}/"}"
        (( SKIPPED++ )) || true
        echo ""
        continue
    fi

    # Target dir must be resolvable
    if [[ -z "${target_dir}" ]]; then
        echo "  skip: unknown agent '${agent}' — no default skill dir and none in config" >&2
        (( SKIPPED++ )) || true
        echo ""
        continue
    fi

    # Enumerate skill subdirectories (each subdir = one skill)
    skill_count=0
    while IFS= read -r -d '' skill_dir; do
        sync_skill "${skill_dir}" "${target_dir}"
        (( skill_count++ )) || true
    done < <(find "${source_dir}" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

    if [[ "${skill_count}" -eq 0 ]]; then
        echo "  skip: no skill subdirectories found in ${source_dir#"${REPO_ROOT}/"}"
        (( SKIPPED++ )) || true
    fi

    echo ""
done <<< "${AGENTS_RAW}"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo "---"
if "${DRY_RUN}"; then
    echo "Dry run complete. ${WOULD_COPY} would be copied, ${SKIPPED} skipped. No files written."
else
    echo "Done. ${SYNCED} synced, ${SKIPPED} skipped, ${ERRORS} errors."
fi

[[ "${ERRORS}" -eq 0 ]] || exit 1
