# Guardian MCP Server

Connect Claude Desktop, Claude Code, or Codex to Guardian for compliance status, document processing, form filing, and Gmail integration.

## Quick Start (one command)

```bash
pip install compliance-os[agent] && guardian-mcp install
```

The installer auto-detects your apps (Claude Desktop, Claude Code, Codex) and writes the config for you. No JSON editing needed.

### Flags

```bash
guardian-mcp install              # interactive — choose apps and API
guardian-mcp install --all        # configure all detected apps (interactive API setup)
guardian-mcp install --all --local   # all apps, local dev (no token needed)
guardian-mcp uninstall            # remove Guardian from all apps
```

## What You Get

18 tools across 5 groups:

**Compliance Context** — same intelligence as the Guardian dashboard:
- `guardian_status` — findings, deadlines, key facts
- `guardian_deadlines` — upcoming deadlines sorted by urgency
- `guardian_risks` — compliance findings by severity
- `guardian_documents` — your data room inventory
- `guardian_ask` — ask Guardian's AI assistant any compliance question

**Document Processing** — runs locally on your machine (no API cost):
- `parse_document` — extract text from PDF/DOCX
- `classify_document` — identify document type (W-2, I-20, passport, etc.)
- `upload_document` — send documents to your Guardian data room
- `query_documents` — RAG search across your indexed documents

**Form Filing** — generate IRS forms locally:
- `generate_form_8843` — fill Form 8843 with filing guidance
- `run_compliance_check` — H-1B doc check, FBAR, student tax, 83(b) election
- `get_filing_guidance` — deadlines, mailing addresses, next steps

**Gmail** — compliance correspondence:
- `gmail_search` / `gmail_read` — find and read compliance-related emails
- `gmail_draft` / `gmail_send` — draft and send with PDF attachments
- `gmail_reply` — respond in-thread
- `gmail_download_attachment` — save attachments for processing

## Manual Setup (if you prefer)

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "guardian": {
      "command": "/path/to/python",
      "args": ["-m", "compliance_os.mcp_server"],
      "env": {
        "GUARDIAN_API_URL": "https://guardiancompliance.app",
        "GUARDIAN_TOKEN": "gdn_oc_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Claude Code

Add to `~/.claude/settings.json` (global) or `.claude/mcp.json` (project):

Same JSON format as Claude Desktop.

### Codex

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.guardian]
type = "stdio"
command = "/path/to/python"
args = ["-m", "compliance_os.mcp_server"]

[mcp_servers.guardian.env]
GUARDIAN_API_URL = "https://guardiancompliance.app"
GUARDIAN_TOKEN = "gdn_oc_YOUR_TOKEN_HERE"
```

## Auth

| Mode | Token needed? | How |
|------|--------------|-----|
| **Local dev** | No | Auto-generates JWT from local SQLite DB |
| **Production** | Yes | Get from Dashboard > Connect to OpenClaw |

## Gmail (optional)

```bash
python scripts/guardian_mcp_setup.py
```

Requires a one-time Google Cloud OAuth setup. See the setup script for instructions.

## Usage Examples

Once connected, just talk naturally:

- "What's my compliance status?"
- "Process these tax documents" (with file paths)
- "Generate my Form 8843 -- I'm an F-1 student from China, arrived 2022-08-15"
- "Search my Gmail for IRS notices"
- "Draft an email to my attorney with the H-1B doc check results"
- "When is my FBAR due?"

## Architecture

```
Your Machine                          Guardian API
+---------------------+               +--------------+
| Claude / Codex      |               |  Guardian     |
|                     |               |  Backend      |
|  +---------------+  |   REST API    |              |
|  | Guardian MCP   |--+--------------+> Status      |
|  | Server         |  |  (token)     |> Deadlines   |
|  |                |  |              |> Risks       |
|  | Local tools:   |  |              |> Documents   |
|  | - PDF extract  |  |              |> Chat        |
|  | - Classify     |  |              |> Upload      |
|  | - Form fill    |  |              +--------------+
|  | - Gmail OAuth  |  |
|  | - RAG query    |  |         Google API
|  |                |--+--------------> Gmail
|  +---------------+  |  (OAuth2)
+---------------------+
```

Document parsing runs locally -- your Claude/Codex handles the LLM extraction work, saving Guardian API token costs.
