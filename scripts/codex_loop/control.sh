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

is_running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

case "${1:-help}" in
  start)
    if is_running; then
      echo "Loop already running (PID: $(cat "$PIDFILE"))"
      exit 1
    fi
    rm -f "$STOPFILE"
    export PROVIDER="${PROVIDER:-codex}"
    echo "Starting Compliance OS Codex batch loop (provider: $PROVIDER)..."
    nohup "$LOOP_SCRIPT" >> "$LOG" 2>&1 &
    echo "$!" > "$PIDFILE"
    echo "Started with PID: $!"
    echo "Log: $LOG"
    ;;

  stop)
    if is_running; then
      echo "Sending stop signal..."
      touch "$STOPFILE"
      echo "Loop will stop after the current iteration."
      echo "To force stop: kill $(cat "$PIDFILE")"
    else
      echo "Not running"
      rm -f "$PIDFILE" "$STOPFILE" 2>/dev/null || true
    fi
    ;;

  restart)
    if is_running; then
      echo "Restarting existing loop..."
      touch "$STOPFILE"
      sleep 1
      if is_running; then
        echo "Waiting for loop to stop gracefully..."
      fi
    fi
    rm -f "$PIDFILE" "$STOPFILE"
    export PROVIDER="${PROVIDER:-codex}"
    nohup "$LOOP_SCRIPT" >> "$LOG" 2>&1 &
    echo "$!" > "$PIDFILE"
    echo "Restarted with PID: $!"
    echo "Log: $LOG"
    ;;

  status)
    if is_running; then
      echo "Running (PID: $(cat "$PIDFILE"))"
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
    echo "  MODEL=$(codex_loop_config_get "$CONFIG_PATH" model gpt-5.4-codex)"
    echo "  REASONING_EFFORT=$(codex_loop_config_get "$CONFIG_PATH" reasoning_effort xhigh)"
    echo "  DURATION_HOURS=$(codex_loop_config_get "$CONFIG_PATH" duration_hours 8)"
    echo "  SLEEP_SECONDS=$(codex_loop_config_get "$CONFIG_PATH" sleep_seconds 300)"
    echo "  ROUND_SIZE=$(codex_loop_config_get "$CONFIG_PATH" round_size 5)"
    echo "  MAX_PASSES=$(codex_loop_config_get "$CONFIG_PATH" max_passes 1)"
    echo "  BATCH_SELECTION='--batch-number 1'  Optional selection override"
    ;;
esac
