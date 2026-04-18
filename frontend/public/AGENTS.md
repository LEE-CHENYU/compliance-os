# Guardian MCP — Install Instructions for AI Agents

You are an AI coding agent (Claude Code, Codex CLI, Cursor, Continue, …)
asked to connect **Guardian** to your user's environment. Follow these
steps deterministically. Do not ask the user for choices that are
already specified here.

Guardian is a compliance copilot that exposes 23 MCP tools covering
immigration, tax, and entity status — plus local document processing,
form filing, and Gmail integration.

## Zero-fetch fast path (copy-paste, no URL read required)

If your user's workspace blocks fetching `guardiancompliance.app`, skip
the rest of this doc and run this instead — it does everything below
in one shell pipe. Ask the user for their Guardian token (from
https://guardiancompliance.app/connect) and substitute it:

```bash
pip install "compliance-os[agent]" && \
GUARDIAN_TOKEN="gdn_oc_THE_USERS_TOKEN" \
GUARDIAN_API_URL="https://guardiancompliance.app" \
guardian-mcp install --auto
```

Then ask the user to restart their host (fully quit + reopen Claude
Desktop; Ctrl-C + rerun Claude Code / Codex) and call
`guardian_status` to verify.

Otherwise, follow the full flow below.

---

## 0. Detect the target app

Look at what host you are running in and pick ONE of:

| Host | Config file |
|---|---|
| Claude Code (CLI) | `~/.claude/settings.json` |
| Claude Desktop | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json` · Windows: `%APPDATA%\Claude\claude_desktop_config.json` · Linux: `~/.config/Claude/claude_desktop_config.json` |
| Codex CLI | `~/.codex/config.toml` |
| Cursor / Continue / other | Follow that tool's MCP config convention |

If you cannot determine the host, default to Claude Code.

---

## 1. Install the Python package

Run ONE of these. Prefer the user's existing Python/conda environment.

```bash
# If the user has conda:
conda run -n <env-name> pip install "compliance-os[agent]"

# Else, user's system Python:
pip install "compliance-os[agent]"

# Or pipx for isolated install:
pipx install "compliance-os[agent]"
```

The package exposes two commands: `guardian-mcp` (installer) and the
server at `python -m compliance_os.mcp_server`.

---

## 2. Acquire the auth token

Tell the user exactly this, then wait for their reply:

> Open **https://guardiancompliance.app/connect** in your browser,
> sign in, click **Generate token**, and paste the token back
> (it starts with `gdn_oc_`).

**Do not invent a token.** Do not proceed without one, unless the user
is running a local Guardian dev server on `localhost:8000` (in which
case an empty token is valid — Guardian auto-issues a dev JWT for
loopback).

---

## 3. Write the MCP config

Use the one-shot installer (preferred):

```bash
GUARDIAN_TOKEN="<token-from-step-2>" \
GUARDIAN_API_URL="https://guardiancompliance.app" \
guardian-mcp install --auto
```

`--auto` detects all installed apps and writes config without prompts.

**If the installer is unavailable**, write the config manually:

### Claude Desktop / Claude Code (JSON)

Merge this into the target config file's `mcpServers` map (preserve
anything already there):

```json
{
  "mcpServers": {
    "guardian": {
      "command": "/ABSOLUTE/PATH/TO/PYTHON",
      "args": ["-m", "compliance_os.mcp_server"],
      "env": {
        "GUARDIAN_API_URL": "https://guardiancompliance.app",
        "GUARDIAN_TOKEN": "gdn_oc_THE_TOKEN"
      }
    }
  }
}
```

The `command` must be an absolute path to a Python interpreter that has
`compliance-os[agent]` installed. Run `python -c "import sys; print(sys.executable)"`
from the user's active env to find it. Do not use `"python"` bare — GUI
apps (Claude Desktop) don't inherit shell PATH.

### Codex CLI (TOML)

Append (or replace if already present) in `~/.codex/config.toml`:

```toml
[mcp_servers.guardian]
type = "stdio"
command = "/ABSOLUTE/PATH/TO/PYTHON"
args = ["-m", "compliance_os.mcp_server"]

[mcp_servers.guardian.env]
GUARDIAN_API_URL = "https://guardiancompliance.app"
GUARDIAN_TOKEN = "gdn_oc_THE_TOKEN"
```

### Hosted SSE alternative (no Python install)

If the user has no Python or you want the lightest setup, use the
hosted MCP endpoint instead. Claude Desktop / Claude Code:

```json
{
  "mcpServers": {
    "guardian": {
      "url": "https://guardiancompliance.app/mcp/sse",
      "headers": { "Authorization": "Bearer gdn_oc_THE_TOKEN" }
    }
  }
}
```

Codex:

```toml
[mcp_servers.guardian]
type = "http"
url = "https://guardiancompliance.app/mcp/sse"

[mcp_servers.guardian.http_headers]
Authorization = "Bearer gdn_oc_THE_TOKEN"
```

---

## 4. Restart the host and verify

Tell the user to restart the app (fully quit and reopen for Claude
Desktop; `Ctrl-C` + re-run for CLIs). Then verify by calling Guardian
tools directly — do NOT assume a tool works just because it's listed:

```
guardian_status          # should return a formatted compliance summary
case_active_search(template="h1b", folder="/tmp")   # error ok, confirms plumbing
```

Common failures:

| Symptom | Cause | Fix |
|---|---|---|
| Tool not listed | Config not loaded | User didn't restart host, OR path/JSON error |
| "Cannot reach Guardian API" | Wrong URL | Re-check `GUARDIAN_API_URL` is `https://guardiancompliance.app` |
| "Token expired" / 401 | Stale token | Go back to step 2 and get a new one |
| SSE timeout | Firewall / proxy | Fall back to stdio (step 3 JSON block) |

---

## 5. Report back

When verification succeeds, tell the user:

> Guardian is connected. You now have 23 tools: compliance context
> (`guardian_status`, `guardian_deadlines`, `guardian_risks`,
> `guardian_documents`, `guardian_ask`), case templates
> (`case_active_search`, `h1b_active_search`, `cpa_active_search`),
> document processing (`parse_document`, `classify_document`,
> `upload_document`, `batch_upload`, `query_documents`), form filing
> (`generate_form_8843`, `run_compliance_check`, `get_filing_guidance`),
> indexing (`index_documents`), and Gmail
> (`gmail_search/read/draft/send/reply/download_attachment`).
>
> Try: "What's my compliance status?" or "Check this folder against the
> H-1B template: /path/to/my/docs".

---

## Notes for the agent

- **Idempotency**: `guardian-mcp install --auto` is idempotent — running
  twice is safe. Manual JSON merge must preserve other `mcpServers`
  entries.
- **Secrets**: never print the token back to the user; never paste it
  into chat history. Only write it to the config file.
- **Version**: if the user needs a specific version, use
  `pip install "compliance-os[agent]==X.Y.Z"`.
- **Local dev**: if the user says "I'm running Guardian locally", set
  `GUARDIAN_API_URL=http://localhost:8000` and `GUARDIAN_TOKEN=""`.
  Guardian auto-generates a dev JWT for loopback.
- **Self-check**: after install, the server's tool list must contain
  exactly one tool named `case_active_search`. If it doesn't, the
  `compliance-os` package version is too old — run
  `pip install -U "compliance-os[agent]"` and retry.

Questions or issues: fretin13@gmail.com.
