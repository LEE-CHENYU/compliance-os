#!/bin/bash
# Guardian Cowork skill — single entry point for read access to the
# Guardian API. Mirrors the endpoints and output format of the OpenClaw
# skill (guardian-openclaw/scripts/*) so the two surfaces stay in sync.
#
# Usage:
#   guardian.sh status
#   guardian.sh deadlines
#   guardian.sh risks
#   guardian.sh documents
#   guardian.sh ask "do I need to file FBAR?"
set -euo pipefail

CMD="${1:-}"
case "$CMD" in
  status|deadlines|risks|documents|ask) ;;
  *)
    echo "Usage: guardian.sh {status|deadlines|risks|documents|ask \"question\"}" >&2
    exit 1
    ;;
esac

API_URL="${GUARDIAN_API_URL:-https://guardiancompliance.app}"
TOKEN="${GUARDIAN_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.guardian-token" ]; then
  TOKEN=$(cat "$HOME/.guardian-token")
fi

if [ -z "$TOKEN" ]; then
  echo "No token configured. Ask the user for their Guardian key (starts with gdn_oc_,"
  echo "from guardiancompliance.app/connect) and save it to ~/.guardian-token."
  exit 1
fi

# api GET <path> — prints body; distinguishes auth failure from network failure.
api() {
  local path="$1" body code
  body=$(curl -s --max-time 30 -w '\n%{http_code}' -H "Authorization: Bearer $TOKEN" "$API_URL$path") || {
    echo "Error: Could not reach Guardian API at $API_URL. Check network connection." >&2
    exit 1
  }
  code=${body##*$'\n'}
  body=${body%$'\n'*}
  if [ "$code" = "401" ] || [ "$code" = "403" ]; then
    echo "Error: Guardian rejected the token (HTTP $code) — likely revoked by a newer key." >&2
    echo "Paste the CURRENT active key into ~/.guardian-token. Only regenerate at" >&2
    echo "guardiancompliance.app/connect if the key is lost — each Generate click" >&2
    echo "de-activates ALL previously issued keys, including the desktop extension's." >&2
    exit 1
  fi
  if [ "${code:0:1}" != "2" ]; then
    echo "Error: Guardian API returned HTTP $code for $path." >&2
    exit 1
  fi
  printf '%s' "$body"
}

cmd_status() {
  local timeline stats chains integrity
  timeline=$(api /api/dashboard/timeline)
  stats=$(api /api/dashboard/stats) || stats='{}'
  chains=$(api /api/dashboard/chains) || chains='[]'
  integrity=$(api /api/dashboard/integrity) || integrity='[]'

  echo "# Guardian Compliance Status"
  echo ""
  echo "Documents: $(echo "$stats" | jq -r '.documents // 0') | Active risks: $(echo "$stats" | jq -r '.risks // 0')"
  echo ""

  local critical warnings
  critical=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "critical")')
  warnings=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "warning")')
  if [ -n "$critical" ]; then
    echo "## Critical Issues"
    echo ""
    echo "$timeline" | jq -r '.findings[] | select(.severity == "critical") | "- **\(.title)**\n  Action: \(.action)\n"'
  fi
  if [ -n "$warnings" ]; then
    echo "## Warnings"
    echo ""
    echo "$timeline" | jq -r '.findings[] | select(.severity == "warning") | "- **\(.title)**\n  Action: \(.action)\n"'
  fi
  if [ -z "$critical" ] && [ -z "$warnings" ]; then
    echo "No active compliance findings. Looking good."
    echo ""
  fi

  if [ "$(echo "$chains" | jq 'length')" -gt 0 ]; then
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

  if [ "$(echo "$integrity" | jq 'length')" -gt 0 ]; then
    echo "## Data Integrity Issues"
    echo ""
    echo "$integrity" | jq -r '.[] | "- [\(.severity | ascii_upcase)] **\(.title)** — \(.message)"'
    echo ""
  fi

  if [ -n "$(echo "$timeline" | jq -r '.deadlines[]?')" ]; then
    echo "## Upcoming Deadlines"
    echo ""
    echo "$timeline" | jq -r '.deadlines[] | if .days < 0 then "- OVERDUE (\(-.days)d ago): \(.title) — \(.date)" elif .days <= 30 then "- **\(.days) days:** \(.title) — \(.date)" else "- \(.days) days: \(.title) — \(.date)" end'
    echo ""
  fi

  if [ -n "$(echo "$timeline" | jq -r '.key_facts[]?')" ]; then
    echo "## Key Facts"
    echo ""
    echo "$timeline" | jq -r '.key_facts[] | "- **\(.label):** \(.value)"'
  fi
}

cmd_deadlines() {
  local timeline
  timeline=$(api /api/dashboard/timeline)

  if [ -z "$(echo "$timeline" | jq -r '.deadlines[]?')" ]; then
    echo "No upcoming deadlines tracked. Upload documents to Guardian to generate deadline tracking."
    return
  fi

  echo "# Upcoming Deadlines"
  echo ""
  echo "$timeline" | jq -r '.deadlines[] | select(.days < 0) | "- OVERDUE (\(-.days) days ago): **\(.title)** — \(.date)"'
  echo "$timeline" | jq -r '.deadlines[] | select(.days >= 0 and .days <= 7) | "- **\(.days) days:** \(.title) — \(.date)"'
  echo "$timeline" | jq -r '.deadlines[] | select(.days > 7 and .days <= 30) | "- \(.days) days: \(.title) — \(.date)"'
  echo "$timeline" | jq -r '.deadlines[] | select(.days > 30) | "- \(.days) days: \(.title) — \(.date)"'
}

cmd_risks() {
  local timeline integrity findings advisories integrity_count
  timeline=$(api /api/dashboard/timeline)
  integrity=$(api /api/dashboard/integrity) || integrity='[]'

  findings=$(echo "$timeline" | jq -r '.findings[]?')
  advisories=$(echo "$timeline" | jq -r '.advisories[]?')
  integrity_count=$(echo "$integrity" | jq 'length')

  if [ -z "$findings" ] && [ -z "$advisories" ] && [ "$integrity_count" = "0" ]; then
    echo "No compliance risks detected. Your documents look consistent."
    return
  fi

  echo "# Compliance Findings"
  echo ""

  local critical warning
  critical=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "critical")')
  warning=$(echo "$timeline" | jq -r '.findings[]? | select(.severity == "warning")')
  if [ -n "$critical" ]; then
    echo "## CRITICAL"
    echo ""
    echo "$timeline" | jq -r '.findings[] | select(.severity == "critical") | "**\(.title)**\n- Action: \(.action)\n- Consequence: \(.consequence // "N/A")\n- Immigration impact: \(if .immigration_impact then "Yes" else "No" end)\n"'
  fi
  if [ -n "$warning" ]; then
    echo "## WARNING"
    echo ""
    echo "$timeline" | jq -r '.findings[] | select(.severity == "warning") | "**\(.title)**\n- Action: \(.action)\n- Consequence: \(.consequence // "N/A")\n- Immigration impact: \(if .immigration_impact then "Yes" else "No" end)\n"'
  fi
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
}

cmd_documents() {
  local docs chains count
  docs=$(api /api/dashboard/documents)
  chains=$(api /api/dashboard/chains) || chains='[]'

  count=$(echo "$docs" | jq 'length')
  if [ "$count" = "0" ] || [ -z "$count" ]; then
    echo "No documents uploaded yet. Visit guardiancompliance.app to upload your I-983, employment letter, tax returns, or I-20."
    return
  fi

  echo "# Documents in Data Room ($count files)"
  echo ""
  echo "$docs" | jq -r '.[] | "- **\(.filename)** (\(.doc_type | gsub("_"; " ") | ascii_upcase), \((.file_size / 1024 * 10 | floor) / 10) KB) — uploaded \(.uploaded_at[:10])"'

  if [ "$(echo "$chains" | jq 'length')" -gt 0 ]; then
    echo ""
    echo "## Chains"
    echo ""
    echo "$chains" | jq -r '.[] | "- [\(.chain_type)] **\(.display_name)** — \((.documents | length)) linked docs"'
  fi
}

cmd_ask() {
  local question="${1:-}"
  if [ -z "$question" ]; then
    echo "Error: No question provided. Usage: guardian.sh ask \"your question here\"" >&2
    exit 1
  fi
  local json_question body code
  json_question=$(printf '%s' "$question" | jq -Rs .)
  body=$(curl -s --max-time 60 -w '\n%{http_code}' -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\": $json_question, \"history\": []}" \
    "$API_URL/api/chat") || {
    echo "Error: Could not reach Guardian assistant at $API_URL. Check network connection." >&2
    exit 1
  }
  code=${body##*$'\n'}
  body=${body%$'\n'*}
  if [ "$code" = "401" ] || [ "$code" = "403" ]; then
    echo "Error: Guardian rejected the token (HTTP $code) — likely revoked by a newer key." >&2
    echo "Paste the CURRENT active key into ~/.guardian-token. Only regenerate at" >&2
    echo "guardiancompliance.app/connect if the key is lost — each Generate click" >&2
    echo "de-activates ALL previously issued keys, including the desktop extension's." >&2
    exit 1
  fi
  if [ "${code:0:1}" != "2" ]; then
    echo "Error: Guardian assistant returned HTTP $code: $(echo "$body" | jq -r '.detail // .' 2>/dev/null | head -c 300)" >&2
    exit 1
  fi
  echo "$body" | jq -r '.reply // "No response received."'
  local refs
  refs=$(echo "$body" | jq -r '[.references[]?.filename] | unique | join(", ")' 2>/dev/null || true)
  if [ -n "$refs" ]; then
    echo ""
    echo "_Grounded in: ${refs}_"
  fi
}

case "$CMD" in
  status)    cmd_status ;;
  deadlines) cmd_deadlines ;;
  risks)     cmd_risks ;;
  documents) cmd_documents ;;
  ask)       shift; cmd_ask "${1:-}" ;;
esac
