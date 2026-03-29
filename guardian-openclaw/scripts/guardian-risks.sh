#!/bin/bash
# Fetch compliance findings grouped by severity from Guardian API
set -euo pipefail

API_URL="${GUARDIAN_API_URL:-https://guardiancompliance.app}"
TOKEN="${GUARDIAN_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "Error: GUARDIAN_TOKEN not set. Please configure your Guardian token."
  exit 1
fi

timeline=$(curl -sf -H "Authorization: Bearer $TOKEN" "$API_URL/api/dashboard/timeline" 2>/dev/null) || {
  echo "Error: Could not reach Guardian API. Check your token and network connection."
  exit 1
}
integrity=$(curl -sf -H "Authorization: Bearer $TOKEN" "$API_URL/api/dashboard/integrity" 2>/dev/null) || integrity='[]'

findings=$(echo "$timeline" | jq -r '.findings[]?')
advisories=$(echo "$timeline" | jq -r '.advisories[]?')
integrity_count=$(echo "$integrity" | jq 'length')

if [ -z "$findings" ] && [ -z "$advisories" ] && [ "$integrity_count" = "0" ]; then
  echo "No compliance risks detected. Your documents look consistent."
  exit 0
fi

echo "# Compliance Findings"
echo ""

# Critical
critical=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "critical")')
if [ -n "$critical" ]; then
  echo "## CRITICAL"
  echo ""
  echo "$timeline" | jq -r '.findings[] | select(.severity == "critical") | "**\(.title)**\n- Action: \(.action)\n- Consequence: \(.consequence // "N/A")\n- Immigration impact: \(if .immigration_impact then "Yes" else "No" end)\n"'
fi

# Warning
warning=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "warning")')
if [ -n "$warning" ]; then
  echo "## WARNING"
  echo ""
  echo "$timeline" | jq -r '.findings[] | select(.severity == "warning") | "**\(.title)**\n- Action: \(.action)\n- Consequence: \(.consequence // "N/A")\n- Immigration impact: \(if .immigration_impact then "Yes" else "No" end)\n"'
fi

# Advisories
if [ -n "$advisories" ]; then
  echo "## Worth Looking Into"
  echo ""
  echo "$timeline" | jq -r '.advisories[] | "- **\(.title)** — \(.action // "")"'
fi

if [ "$integrity_count" -gt 0 ]; then
  echo ""
  echo "## Data Integrity / Mapping Issues"
  echo ""
  echo "$integrity" | jq -r '.[] | "- [\(.severity | ascii_upcase)] **\(.title)** — \(.message)"'
fi
