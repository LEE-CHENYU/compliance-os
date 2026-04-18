"""Build the Guardian DXT (Desktop Extension) package.

DXT is Anthropic's one-click install format for Claude Desktop — a
zip archive with a manifest.json that Claude Desktop parses to pip-
install the server, prompt for auth, and wire the MCP client config.

Output: frontend/public/guardian.dxt
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


MANIFEST = {
    "dxt_version": "0.1",
    "name": "guardian",
    "display_name": "Guardian Compliance",
    "version": "1.0.0",
    "description": (
        "Compliance copilot for nonresidents, STEM OPT / H-1B workers, "
        "international students, and foreign-owned US entities. Exposes "
        "23 MCP tools for immigration/tax document cross-checks, case "
        "template matching (H-1B, CPA), form filing (Form 8843, 1040-NR, "
        "FBAR, Form 5472), and Gmail integration."
    ),
    "long_description": (
        "Guardian scans a local folder against reusable case templates "
        "(H-1B petition package, CPA tax engagement) and emits a gap "
        "report — coverage by section, missing required slots, lineage "
        "issues. Also handles Form 8843 generation, FBAR aggregation, "
        "I-983 STEM OPT training plan review, and tokenized data-room "
        "share links for external collaborators like attorneys and CPAs."
    ),
    "author": {
        "name": "Guardian",
        "email": "fretin13@gmail.com",
        "url": "https://guardiancompliance.app",
    },
    "homepage": "https://guardiancompliance.app",
    "documentation": "https://guardiancompliance.app/docs/install",
    "support": "mailto:fretin13@gmail.com",
    "icon": "icon.png",
    "keywords": [
        "compliance", "immigration", "tax", "h1b", "stem-opt",
        "form-8843", "form-1040-nr", "fbar", "form-5472",
        "mcp", "nonresident",
    ],
    "license": "MIT",
    "server": {
        "type": "python",
        "entry_point": "compliance_os.mcp_server",
        "mcp_config": {
            "command": "${USER_CONFIG.python}",
            "args": ["-m", "compliance_os.mcp_server"],
            "env": {
                "GUARDIAN_API_URL": "${USER_CONFIG.api_url}",
                "GUARDIAN_TOKEN": "${USER_CONFIG.token}",
            },
        },
        "pip_install": ["compliance-os[agent]>=1.0.0"],
    },
    "user_config": {
        "token": {
            "type": "string",
            "title": "Guardian API token",
            "description": (
                "Get yours at https://guardiancompliance.app/connect "
                "(sign in, click Generate token). Starts with gdn_oc_."
            ),
            "required": True,
            "sensitive": True,
        },
        "api_url": {
            "type": "string",
            "title": "Guardian API URL",
            "description": "Production: https://guardiancompliance.app — or your local dev server.",
            "default": "https://guardiancompliance.app",
            "required": False,
        },
        "python": {
            "type": "string",
            "title": "Python interpreter path",
            "description": (
                "Absolute path to a Python 3.11+ interpreter that will "
                "host the MCP server. Use `which python3` on Unix or "
                "`where python` on Windows."
            ),
            "default": "python3",
            "required": False,
        },
    },
    "tools": [
        {"name": "guardian_status",      "description": "Compliance findings, deadlines, key facts"},
        {"name": "guardian_deadlines",   "description": "Upcoming deadlines sorted by urgency"},
        {"name": "guardian_risks",       "description": "Active compliance findings by severity"},
        {"name": "guardian_documents",   "description": "Your data-room document inventory"},
        {"name": "guardian_ask",         "description": "Ask Guardian AI a compliance question"},
        {"name": "case_active_search",   "description": "Scan a folder against any case template"},
        {"name": "h1b_active_search",    "description": "H-1B petition gap report"},
        {"name": "cpa_active_search",    "description": "CPA tax engagement gap report"},
        {"name": "parse_document",       "description": "Extract text from PDF/DOCX"},
        {"name": "classify_document",    "description": "Identify doc type (W-2, I-20, ...)"},
        {"name": "upload_document",      "description": "Send to your Guardian data room"},
        {"name": "batch_upload",         "description": "Batch upload a folder"},
        {"name": "query_documents",      "description": "RAG search over indexed docs"},
        {"name": "index_documents",      "description": "Build/update ChromaDB vector index"},
        {"name": "generate_form_8843",   "description": "Fill Form 8843 with filing guidance"},
        {"name": "run_compliance_check", "description": "H-1B doc check, FBAR, 83(b), ..."},
        {"name": "get_filing_guidance",  "description": "Deadlines, mailing addresses, steps"},
        {"name": "gmail_search",         "description": "Find compliance-related emails"},
        {"name": "gmail_read",           "description": "Read a Gmail message"},
        {"name": "gmail_draft",          "description": "Draft with optional PDF attachment"},
        {"name": "gmail_send",           "description": "Send a draft"},
        {"name": "gmail_reply",          "description": "Reply in-thread"},
        {"name": "gmail_download_attachment", "description": "Save an attachment locally"},
    ],
    "compatibility": {
        "claude_desktop": ">=0.9.0",
        "platforms": ["darwin", "linux", "win32"],
        "python": ">=3.11",
    },
}


def build(output: Path) -> Path:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(MANIFEST, indent=2))
    return output


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "frontend/public/guardian.dxt"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    built = build(out)
    size = built.stat().st_size
    print(f"Built {built} ({size} bytes)")
