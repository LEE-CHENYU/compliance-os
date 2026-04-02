#!/usr/bin/env bash
# Control script for the Compliance OS Codex batch loop.
#
# Usage:
#   ./control.sh start
#   ./control.sh stop
#   ./control.sh restart
#   ./control.sh status
#   ./control.sh once
#   ./control.sh tail
#   ./control.sh log

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
ROOT="$(codex_loop_root "${BASH_SOURCE[0]}")"
CONFIG_PATH="$(codex_loop_config_path "$ROOT")"
LOOP_SCRIPT="$ROOT/scripts/codex_loop/codex_data_room_loop.sh"
LOG_DIR="$ROOT/logs/codex_loop"
PIDFILE="$LOG_DIR/codex_data_room_loop.pid"
STOPFILE="$LOG_DIR/codex_data_room_loop.stop"
LOG="$LOG_DIR/codex_data_room_loop.log"

mkdir -p "$LOG_DIR"

current_pid() {
  tr -d '[:space:]' < "$PIDFILE"
}

is_running() {
  [ -f "$PIDFILE" ] || return 1
  local pid
  pid="$(current_pid 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null
}

clear_stale_state() {
  if [ -f "$PIDFILE" ] && ! is_running; then
    rm -f "$PIDFILE"
  fi
}

wait_for_process_start() {
  local pid="$1"
  local deadline="${2:-10}"
  local second
  for second in $(seq 1 "$deadline"); do
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_process_exit() {
  local pid="$1"
  local deadline="${2:-10}"
  local second
  for second in $(seq 1 "$deadline"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  ! kill -0 "$pid" 2>/dev/null
}

launch_loop() {
  local launcher_pid
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid "$LOOP_SCRIPT" </dev/null >> "$LOG" 2>&1 &
  else
    nohup "$LOOP_SCRIPT" </dev/null >> "$LOG" 2>&1 &
  fi
  launcher_pid="$!"
  disown "$launcher_pid" 2>/dev/null || true
  printf '%s\n' "$launcher_pid" > "$PIDFILE"
  if ! wait_for_process_start "$launcher_pid" 10; then
    echo "Loop exited during startup. Recent log:"
    tail -40 "$LOG" 2>/dev/null || true
    rm -f "$PIDFILE"
    return 1
  fi
  printf '%s\n' "$launcher_pid"
}

case "${1:-help}" in
  start)
    clear_stale_state
    if is_running; then
      echo "Loop already running (PID: $(current_pid))"
      exit 1
    fi
    rm -f "$STOPFILE"
    export PROVIDER="${PROVIDER:-codex}"
    echo "Starting Compliance OS Codex batch loop (provider: $PROVIDER)..."
    if ! launch_loop >/tmp/compliance_os_codex_loop_pid.$$; then
      exit 1
    fi
    started_pid="$(cat /tmp/compliance_os_codex_loop_pid.$$)"
    rm -f /tmp/compliance_os_codex_loop_pid.$$
    echo "Started with PID: $started_pid"
    echo "Log: $LOG"
    ;;

  stop)
    clear_stale_state
    if is_running; then
      pid="$(current_pid)"
      echo "Sending stop signal..."
      touch "$STOPFILE"
      if wait_for_process_exit "$pid" "${STOP_WAIT_SECONDS:-10}"; then
        rm -f "$PIDFILE" "$STOPFILE"
        echo "Stopped"
      else
        echo "Loop will stop after the current iteration."
        echo "To force stop: kill $pid"
      fi
    else
      echo "Not running"
      rm -f "$PIDFILE" "$STOPFILE" 2>/dev/null || true
    fi
    ;;

  restart)
    clear_stale_state
    if is_running; then
      pid="$(current_pid)"
      echo "Restarting existing loop..."
      touch "$STOPFILE"
      if ! wait_for_process_exit "$pid" "${STOP_WAIT_SECONDS:-10}"; then
        echo "Graceful stop timed out, sending TERM to $pid"
        kill "$pid" 2>/dev/null || true
        if ! wait_for_process_exit "$pid" 5; then
          echo "Loop did not stop cleanly"
          exit 1
        fi
      fi
    fi
    rm -f "$PIDFILE" "$STOPFILE"
    export PROVIDER="${PROVIDER:-codex}"
    if ! launch_loop >/tmp/compliance_os_codex_loop_pid.$$; then
      exit 1
    fi
    restarted_pid="$(cat /tmp/compliance_os_codex_loop_pid.$$)"
    rm -f /tmp/compliance_os_codex_loop_pid.$$
    echo "Restarted with PID: $restarted_pid"
    echo "Log: $LOG"
    ;;

  status)
    clear_stale_state
    if is_running; then
      echo "Running (PID: $(current_pid))"
      if [ -f "$STOPFILE" ]; then
        echo "Stop requested: yes"
      fi
      echo "Log tail:"
      tail -20 "$LOG" 2>/dev/null || echo "(no log yet)"
    else
      echo "Not running"
      rm -f "$PIDFILE" 2>/dev/null || true
    fi
    ;;

  once)
    echo "Running single iteration..."
    "$LOOP_SCRIPT" --once
    ;;

  tail)
    echo "Following log (Ctrl+C to stop)..."
    tail -f "$LOG"
    ;;

  log)
    echo "=== Recent log (last 80 lines) ==="
    tail -80 "$LOG" 2>/dev/null || echo "(no log yet)"
    ;;

  *)
    echo "Compliance OS Codex Batch Loop Control"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|once|tail|log}"
    echo ""
    echo "Config file: $CONFIG_PATH"
    echo "Environment:"
    echo "  PROVIDER=$(codex_loop_config_get "$CONFIG_PATH" provider codex)"
    echo "  MODEL=$(codex_loop_config_get "$CONFIG_PATH" model gpt-5.3-codex)"
    echo "  REASONING_EFFORT=$(codex_loop_config_get "$CONFIG_PATH" reasoning_effort xhigh)"
    echo "  DURATION_HOURS=$(codex_loop_config_get "$CONFIG_PATH" duration_hours 8)"
    echo "  SUCCESS_SLEEP_SECONDS=$(codex_loop_config_get "$CONFIG_PATH" success_sleep_seconds 0)"
    echo "  FAILURE_SLEEP_SECONDS=$(codex_loop_config_get "$CONFIG_PATH" failure_sleep_seconds 60)"
    echo "  STOP_WHEN_ALL_RESOLVED=$(codex_loop_config_get "$CONFIG_PATH" stop_when_all_resolved true)"
    echo "  ROUND_SIZE=$(codex_loop_config_get "$CONFIG_PATH" round_size 5)"
    echo "  MAX_PASSES=$(codex_loop_config_get "$CONFIG_PATH" max_passes 1)"
    echo "  BATCH_SELECTION='--batch-number 1'  Optional selection override"
    ;;
esac
