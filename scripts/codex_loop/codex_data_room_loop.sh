#!/usr/bin/env bash
# Codex CLI loop for Compliance OS data-room batch remediation.
#
# Usage:
#   ./codex_data_room_loop.sh
#   ./codex_data_room_loop.sh --once
#   PROVIDER=echo ./codex_data_room_loop.sh --once

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd -- "$SCRIPT_DIR/../.." && pwd)}"
LOG_DIR="$ROOT/logs/codex_loop"
LOG="$LOG_DIR/codex_data_room_loop.log"
PIDFILE="$LOG_DIR/codex_data_room_loop.pid"
STOPFILE="$LOG_DIR/codex_data_room_loop.stop"
SESSION_ROOT="${SESSION_ROOT:-$ROOT/logs/data-room-batch-loop-codex}"

OBJECTIVE_FILE="$SCRIPT_DIR/codex_objective.txt"
RESUME_FILE="$SCRIPT_DIR/codex_resume.md"
RUN_BATCH_SCRIPT="$SCRIPT_DIR/run_batch_iteration.sh"
BATCH_LOOP_SCRIPT="$ROOT/scripts/data_room_batch_loop.py"
MANIFEST_PATH="${MANIFEST_PATH:-$ROOT/config/data_room_batches.yaml}"

ROUND_SIZE="${ROUND_SIZE:-5}"
MAX_PASSES="${MAX_PASSES:-1}"
SLEEP_SECONDS="${SLEEP_SECONDS:-300}"
DURATION_HOURS="${DURATION_HOURS:-8}"
DURATION_SECONDS=$((DURATION_HOURS * 3600))
BATCH_SELECTION="${BATCH_SELECTION:-}"

PROVIDER="${PROVIDER:-codex}"
SANDBOX_MODE="${SANDBOX_MODE:-danger-full-access}"
MODEL="${MODEL:-gpt-5.3-codex}"
if [ -n "${PYTHON_BIN:-}" ]; then
  PYTHON="$PYTHON_BIN"
elif [ -x "/Users/lichenyu/miniconda3/envs/compliance-os/bin/python" ]; then
  PYTHON="/Users/lichenyu/miniconda3/envs/compliance-os/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

OBJECTIVE_DEFAULT="Compliance OS data-room batch loop:
1. Keep the loop on the current unresolved batch until validation says it is resolved.
2. Use scripts/data_room_batch_loop.py as the source of truth for batch state.
3. Improve parsing, storage, schema coverage, retrieval, and review logic only as needed to clear the current batch.
4. Update the batch record and codex resume after each iteration.
5. Do not weaken validation hooks to get a green result.

Priority:
- Fix the first unresolved issue on the current batch.
- Preserve prior passing batches.
- Only move to the next batch when the current batch validates as resolved."

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

cleanup() {
  rm -f "$PIDFILE"
}
trap cleanup EXIT

ensure_files() {
  mkdir -p "$LOG_DIR" "$SESSION_ROOT"
  if [ ! -f "$OBJECTIVE_FILE" ]; then
    printf '%s\n' "$OBJECTIVE_DEFAULT" > "$OBJECTIVE_FILE"
    log "Created default objective file"
  fi
  if [ ! -f "$RESUME_FILE" ]; then
    cat > "$RESUME_FILE" <<'EOF'
# Compliance OS Codex Loop Resume

**Last Updated:** pending first iteration
**Status:** initialized

## Current Focus

- Batch 01 is the first blocking batch in the first five-batch round.

## Previous Changes

- Added auditable batch-loop orchestration with validation hooks and session logs.

## Validation Snapshot

- Batch 02 currently resolves cleanly.
- Batches 01 and 03 still have unresolved recorded gaps.
- Batches 04 and 05 are still planned and need concrete manifests plus hooks.

## Next Steps

1. Run the current batch through `scripts/data_room_batch_loop.py`.
2. Work only on the blocked batch selected by the loop.
3. Re-run validation and update the batch record plus this resume.

## Risks / Blockers

- The loop controller exists, but the actual code changes still depend on the Codex batch processor prompt clearing real gaps.
EOF
    log "Created initial resume file"
  fi
}

run_single_iteration() {
  local iter="$1"
  local run_command
  local -a cmd

  export ROOT PROVIDER SANDBOX_MODE MODEL PYTHON OBJECTIVE_FILE RESUME_FILE MANIFEST_PATH

  run_command="bash $RUN_BATCH_SCRIPT {batch_number_quoted} {batch_id_quoted} {focus_quoted} {record_quoted}"

  cmd=(
    "$PYTHON"
    "$BATCH_LOOP_SCRIPT"
    --manifest "$MANIFEST_PATH"
    --round-size "$ROUND_SIZE"
    --max-passes "$MAX_PASSES"
    --run-command "$run_command"
    --run-validation-hooks
    --log-root "$SESSION_ROOT"
  )

  if [ -n "$BATCH_SELECTION" ]; then
    # shellcheck disable=SC2206
    local selection_args=( $BATCH_SELECTION )
    cmd+=("${selection_args[@]}")
  fi

  log "=== Iteration $iter started ==="
  log "Provider=$PROVIDER Model=$MODEL RoundSize=$ROUND_SIZE MaxPasses=$MAX_PASSES"
  log "Running batch loop with validation-gated Codex batch processor"
  (
    cd "$ROOT"
    "${cmd[@]}"
  ) >> "$LOG" 2>&1 || log "Batch loop returned non-zero exit during iteration $iter"

  log "Git status after iteration $iter:"
  git -C "$ROOT" status -sb >> "$LOG" 2>&1 || true
  log "=== Iteration $iter completed ==="
}

if [ "${1:-}" = "--once" ]; then
  ensure_files
  run_single_iteration 1
  exit 0
fi

ensure_files
echo "$$" > "$PIDFILE"

start_ts=$(date +%s)
end_ts=$((start_ts + DURATION_SECONDS))

log "=== Compliance OS Codex batch loop started ==="
log "Root: $ROOT"
log "Manifest: $MANIFEST_PATH"
log "Duration: ${DURATION_HOURS}h (${DURATION_SECONDS}s)"
log "Sleep: ${SLEEP_SECONDS}s"
log "Provider: $PROVIDER"
log "Model: $MODEL"
log "PID: $$"

iter=0
while [ "$(date +%s)" -lt "$end_ts" ]; do
  iter=$((iter + 1))

  if [ -f "$STOPFILE" ]; then
    log "Stop file detected, exiting gracefully"
    rm -f "$STOPFILE"
    break
  fi

  run_single_iteration "$iter"

  if [ "$(date +%s)" -lt "$end_ts" ]; then
    log "Sleeping ${SLEEP_SECONDS}s before next iteration..."
    sleep "$SLEEP_SECONDS"
  fi
done

log "=== Compliance OS Codex batch loop ended ==="
log "Total iterations: $iter"
