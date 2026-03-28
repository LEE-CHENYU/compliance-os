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
ROOT="${ROOT:-$(cd -- "$SCRIPT_DIR/../.." && pwd)}"
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
    echo "Environment:"
    echo "  PROVIDER=codex|claude|echo  Provider for batch iterations"
    echo "  MODEL=gpt-5.3-codex         Model used with Codex CLI"
    echo "  DURATION_HOURS=8            Loop duration"
    echo "  SLEEP_SECONDS=300           Sleep between iterations"
    echo "  ROUND_SIZE=5                First-round batch cap"
    echo "  MAX_PASSES=1                Batch-loop passes per outer iteration"
    echo "  BATCH_SELECTION='--batch-number 1'  Optional selection override"
    ;;
esac
