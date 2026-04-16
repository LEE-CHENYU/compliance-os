# Guardian MCP Server

Connect your Claude Code or Codex to Guardian for compliance status, document processing, form filing, and Gmail integration — directly in your terminal.

## What You Get

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

## Setup

### 1. Install dependencies

```bash
pip install compliance-os[agent]
```

Or if you have the repo cloned:

```bash
pip install -e ".[agent]"
```

### 2. Get your Guardian token

1. Log in at [guardiancompliance.app](https://guardiancompliance.app)
2. Go to Dashboard → Connect to OpenClaw
3. Generate a token and copy it

### 3. Gmail (optional)

To enable Gmail tools:

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create an OAuth 2.0 Client ID (Desktop application)
3. Enable the Gmail API
4. Download credentials JSON
5. Save as `~/.config/guardian/gmail_credentials.json`
6. Run: `python scripts/guardian_mcp_setup.py`

### 4. Add to Claude Code

Add to your project's `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "guardian": {
      "command": "python",
      "args": ["-m", "compliance_os.mcp_server"],
      "env": {
        "GUARDIAN_API_URL": "https://guardiancompliance.app",
        "GUARDIAN_TOKEN": "gdn_oc_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

Or to your global `~/.claude/settings.json` under `mcpServers`.

### 5. Add to Codex

Copy `codex_mcp_config.json` to your Codex MCP config, or add the `guardian` server entry to your existing config.

## Usage Examples

Once connected, just talk naturally:

- "What's my compliance status?"
- "Process these tax documents" (with file paths)
- "Generate my Form 8843 — I'm an F-1 student from China, arrived 2022-08-15"
- "Search my Gmail for IRS notices"
- "Draft an email to my attorney with the H-1B doc check results"
- "When is my FBAR due?"

## Architecture

```
Your Machine                          Guardian API
┌─────────────────────┐               ┌──────────────┐
│ Claude Code / Codex │               │  Guardian     │
│                     │               │  Backend      │
│  ┌───────────────┐  │   REST API    │              │
│  │ Guardian MCP   │──│──────────────│► Status      │
│  │ Server         │  │  (token)     │► Deadlines   │
│  │                │  │              │► Risks       │
│  │ Local tools:   │  │              │► Documents   │
│  │ • PDF extract  │  │              │► Chat        │
│  │ • Classify     │  │              │► Upload      │
│  │ • Form fill    │  │              └──────────────┘
│  │ • Gmail OAuth  │  │
│  │ • RAG query    │  │         Google API
│  │                │──│─────────────► Gmail
│  └───────────────┘  │  (OAuth2)
└─────────────────────┘
```

Document parsing runs locally — your Claude Code/Codex handles the LLM extraction work, saving Guardian API token costs.
