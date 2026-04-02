#!/usr/bin/env bash

codex_loop_root() {
  local script_path="$1"
  local script_dir
  script_dir="$(cd -- "$(dirname "$script_path")" && pwd)"
  if [ -n "${ROOT:-}" ]; then
    printf '%s\n' "$ROOT"
  else
    (cd -- "$script_dir/../.." && pwd)
  fi
}

codex_loop_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    printf '%s\n' "$PYTHON_BIN"
    return
  fi
  if [ -n "${PYTHON:-}" ]; then
    printf '%s\n' "$PYTHON"
    return
  fi
  if [ -x "/Users/lichenyu/miniconda3/envs/compliance-os/bin/python" ]; then
    printf '%s\n' "/Users/lichenyu/miniconda3/envs/compliance-os/bin/python"
    return
  fi
  command -v python3 || command -v python
}

codex_loop_config_path() {
  local root="$1"
  if [ -n "${CODEX_LOOP_CONFIG:-}" ]; then
    printf '%s\n' "$CODEX_LOOP_CONFIG"
  else
    printf '%s\n' "$root/config/codex_loop.yaml"
  fi
}

codex_loop_config_get() {
  local config_path="$1"
  local key="$2"
  local fallback="${3:-}"
  if [ ! -f "$config_path" ]; then
    printf '%s\n' "$fallback"
    return
  fi
  awk -v key="$key" -v fallback="$fallback" '
    BEGIN { found = 0 }
    /^[[:space:]]*#/ { next }
    {
      line = $0
      sub(/\r$/, "", line)
    }
    $0 ~ "^[[:space:]]*" key "[[:space:]]*:" {
      line = $0
      sub("^[[:space:]]*" key "[[:space:]]*:[[:space:]]*", "", line)
      gsub(/^["'"'"']|["'"'"']$/, "", line)
      print line
      found = 1
      exit
    }
    END {
      if (!found) {
        print fallback
      }
    }
  ' "$config_path"
}
