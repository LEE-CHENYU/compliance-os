#!/bin/bash
# Fetch full compliance status from Guardian API
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

stats=$(curl -sf -H "Authorization: Bearer $TOKEN" "$API_URL/api/dashboard/stats" 2>/dev/null) || stats='{}'
chains=$(curl -sf -H "Authorization: Bearer $TOKEN" "$API_URL/api/dashboard/chains" 2>/dev/null) || chains='[]'
integrity=$(curl -sf -H "Authorization: Bearer $TOKEN" "$API_URL/api/dashboard/integrity" 2>/dev/null) || integrity='[]'

echo "# Guardian Compliance Status"
echo ""

# Stats
docs=$(echo "$stats" | jq -r '.documents // 0')
risks=$(echo "$stats" | jq -r '.risks // 0')
echo "Documents: $docs | Active risks: $risks"
echo ""

# Critical findings
critical=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "critical")')
if [ -n "$critical" ]; then
  echo "## Critical Issues"
  echo ""
  echo "$timeline" | jq -r '.findings[] | select(.severity == "critical") | "- **\(.title)**\n  Action: \(.action)\n"'
fi

# Warnings
warnings=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "warning")')
if [ -n "$warnings" ]; then
  echo "## Warnings"
  echo ""
  echo "$timeline" | jq -r '.findings[] | select(.severity == "warning") | "- **\(.title)**\n  Action: \(.action)\n"'
fi

if [ -z "$critical" ] && [ -z "$warnings" ]; then
  echo "No active compliance findings. Looking good."
  echo ""
fi

chain_count=$(echo "$chains" | jq 'length')
if [ "$chain_count" -gt 0 ]; then
  echo "## Active Chains"
  echo ""
  echo "$chains" | jq -r '.[] | "- [\(.chain_type)] **\(.display_name)**\(
    if .start_date or .end_date then
      " (" + ([.start_date, .end_date] | map(select(. != null and . != "")) | join(" to ")) + ")"
    else
      ""
    end
  )"'
  echo ""
fi

integrity_count=$(echo "$integrity" | jq 'length')
if [ "$integrity_count" -gt 0 ]; then
  echo "## Data Integrity Issues"
  echo ""
  echo "$integrity" | jq -r '.[] | "- [\(.severity | ascii_upcase)] **\(.title)** — \(.message)"'
  echo ""
fi

# Deadlines
deadlines=$(echo "$timeline" | jq -r '.deadlines[]?')
if [ -n "$deadlines" ]; then
  echo "## Upcoming Deadlines"
  echo ""
  echo "$timeline" | jq -r '.deadlines[] | if .days < 0 then "- OVERDUE (\(-.days)d ago): \(.title) — \(.date)" elif .days <= 30 then "- **\(.days) days:** \(.title) — \(.date)" else "- \(.days) days: \(.title) — \(.date)" end'
  echo ""
fi

# Key facts
facts=$(echo "$timeline" | jq -r '.key_facts[]?')
if [ -n "$facts" ]; then
  echo "## Key Facts"
  echo ""
  echo "$timeline" | jq -r '.key_facts[] | "- **\(.label):** \(.value)"'
fi
