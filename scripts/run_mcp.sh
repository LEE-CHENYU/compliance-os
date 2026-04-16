#!/bin/bash
# Guardian MCP Server launcher
# Used by Claude Code and Codex MCP configs
set -euo pipefail

CONDA_ENV="${GUARDIAN_CONDA_ENV:-compliance-os}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"
exec conda run -n "$CONDA_ENV" python -m compliance_os.mcp_server "$@"
