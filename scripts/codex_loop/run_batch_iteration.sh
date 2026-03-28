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
ROOT="${ROOT:-$(cd -- "$SCRIPT_DIR/../.." && pwd)}"
OBJECTIVE_FILE="${OBJECTIVE_FILE:-$SCRIPT_DIR/codex_objective.txt}"
RESUME_FILE="${RESUME_FILE:-$SCRIPT_DIR/codex_resume.md}"
MANIFEST_PATH="${MANIFEST_PATH:-$ROOT/config/data_room_batches.yaml}"
PROVIDER="${PROVIDER:-codex}"
SANDBOX_MODE="${SANDBOX_MODE:-danger-full-access}"
MODEL="${MODEL:-gpt-5.3-codex}"
if [ -n "${PYTHON_BIN:-}" ]; then
  PYTHON="$PYTHON_BIN"
elif [ -n "${PYTHON:-}" ]; then
  PYTHON="$PYTHON"
elif [ -x "/Users/lichenyu/miniconda3/envs/compliance-os/bin/python" ]; then
  PYTHON="/Users/lichenyu/miniconda3/envs/compliance-os/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

objective="$(cat "$OBJECTIVE_FILE" 2>/dev/null || true)"
resume_context="$(cat "$RESUME_FILE" 2>/dev/null || echo 'No previous resume context.')"
record_context="$(sed -n '1,220p' "$ROOT/$BATCH_RECORD" 2>/dev/null || echo 'Batch record file missing.')"

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

BATCH RECORD SNAPSHOT:
$record_context

MANDATORY WORKFLOW:
1. Start by running this exact assessment command:
   $ASSESS_COMMAND
2. Work only on Batch $BATCH_NUMBER. Do not manually advance to the next batch.
3. Make the smallest coherent code and documentation changes needed to reduce or clear the unresolved issues recorded for this batch.
4. Re-run validation with this exact command:
   $VALIDATE_COMMAND
5. Update $RESUME_FILE with:
   - current batch
   - changes made
   - validation results
   - remaining blockers
   - next step
6. Update $BATCH_RECORD if the real remaining gaps changed.

RULES:
- Treat scripts/data_room_batch_loop.py as the source of truth for whether the batch is resolved.
- Do not weaken or delete validation hooks just to make the batch look green.
- Preserve earlier passing behavior while fixing the current batch.
- If blocked, make the blocker explicit in the resume and batch record.
- Do not push changes from inside this iteration unless explicitly instructed."

cd "$ROOT"
case "$PROVIDER" in
  codex)
    codex exec -s "$SANDBOX_MODE" -m "$MODEL" "$PROMPT_TEXT"
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
