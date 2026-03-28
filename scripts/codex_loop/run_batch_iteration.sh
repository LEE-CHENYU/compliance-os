#!/usr/bin/env bash
# Concrete batch processor used by scripts/data_room_batch_loop.py --run-command.

set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <batch-number> <batch-id> <focus> <record>"
  exit 1
fi

BATCH_NUMBER="$1"
BATCH_ID="$2"
BATCH_FOCUS="$3"
BATCH_RECORD="$4"

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
ROOT="$(codex_loop_root "${BASH_SOURCE[0]}")"
PYTHON="$(codex_loop_python)"
CONFIG_PATH="$(codex_loop_config_path "$ROOT")"
OBJECTIVE_FILE="${OBJECTIVE_FILE:-$SCRIPT_DIR/codex_objective.txt}"
RESUME_FILE="${RESUME_FILE:-$SCRIPT_DIR/codex_resume.md}"
MANIFEST_PATH="${MANIFEST_PATH:-$(codex_loop_config_get "$CONFIG_PATH" manifest_path "$ROOT/config/data_room_batches.yaml")}"
PROVIDER="${PROVIDER:-$(codex_loop_config_get "$CONFIG_PATH" provider codex)}"
SANDBOX_MODE="${SANDBOX_MODE:-$(codex_loop_config_get "$CONFIG_PATH" sandbox_mode danger-full-access)}"
MODEL="${MODEL:-$(codex_loop_config_get "$CONFIG_PATH" model gpt-5.3-codex)}"
FALLBACK_MODEL="${FALLBACK_MODEL:-$(codex_loop_config_get "$CONFIG_PATH" fallback_model gpt-5.3-codex)}"
REASONING_EFFORT="${REASONING_EFFORT:-$(codex_loop_config_get "$CONFIG_PATH" reasoning_effort xhigh)}"

objective="$(cat "$OBJECTIVE_FILE" 2>/dev/null || true)"
resume_context="$(cat "$RESUME_FILE" 2>/dev/null || echo 'No previous resume context.')"
remaining_gaps="$(
  python - "$ROOT/$BATCH_RECORD" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
if not path.exists():
    print("Batch record file missing.")
    raise SystemExit(0)

lines = path.read_text().splitlines()
in_section = False
items: list[str] = []
for line in lines:
    stripped = line.strip()
    if stripped.lower() == "## remaining gaps":
        in_section = True
        continue
    if in_section and stripped.startswith("## "):
        break
    if not in_section:
        continue
    if stripped.startswith(("- ", "* ")):
        items.append(stripped[2:].strip())
        continue
    if stripped and stripped[0].isdigit() and ". " in stripped:
        items.append(stripped.split(". ", 1)[1].strip())

if not items:
    print("- No remaining gaps recorded.")
else:
    for item in items:
        print(f"- {item}")
PY
)"

ASSESS_COMMAND="$PYTHON scripts/data_room_batch_loop.py --manifest $MANIFEST_PATH --batch-number $BATCH_NUMBER --run-validation-hooks --json --log-root logs/data-room-batch-loop-agent-assess"
VALIDATE_COMMAND="$PYTHON scripts/data_room_batch_loop.py --manifest $MANIFEST_PATH --batch-number $BATCH_NUMBER --run-validation-hooks --json --log-root logs/data-room-batch-loop-agent-validate"

PROMPT_TEXT="You are improving the Compliance OS repository at $ROOT.

CURRENT BATCH:
- batch_number: $BATCH_NUMBER
- batch_id: $BATCH_ID
- focus: $BATCH_FOCUS
- record: $BATCH_RECORD

GLOBAL OBJECTIVE:
$objective

RESUME CONTEXT:
$resume_context

RECORDED REMAINING GAPS:
$remaining_gaps

MANDATORY WORKFLOW:
1. Start by running this exact assessment command:
   $ASSESS_COMMAND
2. Work only on Batch $BATCH_NUMBER. Do not manually advance to the next batch.
3. Make the smallest coherent code and documentation changes needed to reduce or clear the unresolved issues recorded for this batch.
4. Re-run validation with this exact command:
   $VALIDATE_COMMAND
5. If you changed classifier or intake logic, retro-validate completed batches with:
   $PYTHON scripts/validate_completed_batches.py --manifest $MANIFEST_PATH --max-batch-number $BATCH_NUMBER
6. Update $RESUME_FILE with:
   - current batch
   - changes made
   - validation results
   - remaining blockers
   - next step
7. Update $BATCH_RECORD if the real remaining gaps changed.

RULES:
- Treat scripts/data_room_batch_loop.py as the source of truth for whether the batch is resolved.
- Only put true current-batch blockers under \`## Current batch blockers\` or \`## Remaining gaps\`.
- Move cross-batch work, future-family expansion, and platform backlog into a non-blocking section such as \`## Deferred backlog\` or \`## Next queue\`.
- Do not weaken or delete validation hooks just to make the batch look green.
- Preserve earlier passing behavior while fixing the current batch.
- Maintain or improve classifier generality. Prefer family-level filename, path-context, or text rules over exact corpus filenames.
- If an exact path exception is unavoidable for a legacy archive file, isolate it clearly as an exception and keep it out of the general path-context rules.
- If blocked, make the blocker explicit in the resume and batch record.
- Do not push changes from inside this iteration unless explicitly instructed."

cd "$ROOT"
case "$PROVIDER" in
  codex)
    output_file="$(mktemp)"
    cleanup_output_file() {
      rm -f "$output_file"
    }
    trap cleanup_output_file EXIT

    run_codex_exec() {
      local model_name="$1"
      codex exec \
        -c "model_reasoning_effort=\"$REASONING_EFFORT\"" \
        -s "$SANDBOX_MODE" \
        -m "$model_name" \
        "$PROMPT_TEXT"
    }

    if run_codex_exec "$MODEL" >"$output_file" 2>&1; then
      cat "$output_file"
      exit 0
    fi

    status=$?
    cat "$output_file"
    if [ "$MODEL" != "$FALLBACK_MODEL" ] && rg -q "model is not supported" "$output_file"; then
      printf 'Retrying with fallback model: %s\n' "$FALLBACK_MODEL" >&2
      run_codex_exec "$FALLBACK_MODEL"
      exit 0
    fi
    exit "$status"
    ;;
  claude)
    claude -p "$PROMPT_TEXT" \
      --allowedTools "Bash(git:*),Bash(python:*),Read,Write,Edit,Glob,Grep"
    ;;
  echo)
    printf '%s\n' "$PROMPT_TEXT"
    ;;
  *)
    echo "Unsupported PROVIDER: $PROVIDER"
    exit 1
    ;;
esac
