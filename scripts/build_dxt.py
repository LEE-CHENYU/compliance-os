"""Build the Guardian DXT (Desktop Extension) package.

DXT is Anthropic's one-click install format for Claude Desktop. We use
the `uv` runtime so Claude Desktop downloads Python and resolves
`compliance-os[agent]` from PyPI on first launch — no user Python
install, no manual pip, no conda env required.

Bundle contents:
  manifest.json   — DXT manifest, manifest_version 0.4, server.type uv
  pyproject.toml  — declares the compliance-os runtime dependency
  src/server.py   — entry-point wrapper that runs compliance_os.mcp_server
  icon.png        — Guardian wordmark (512x512)

Output: frontend/public/guardian.dxt
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


COMPLIANCE_OS_VERSION = "==2.0.8"


MANIFEST = {
    "manifest_version": "0.4",
    "name": "guardian",
    "display_name": "Guardian Compliance",
    "version": "2.0.8",
    "description": (
        "Local-first compliance copilot for nonresidents, STEM OPT / H-1B "
        "workers, international students, and foreign-owned US entities. Runs "
        "entirely on your machine — document extraction, a personal facts "
        "source-of-truth, deadlines/risk checks, and form filing (Form 8843, "
        "1040-NR, FBAR, Form 5472). Your documents never leave your computer."
    ),
    "long_description": (
        "Guardian scans a local folder against reusable case templates "
        "(H-1B petition package, CPA tax engagement) and emits a gap "
        "report — coverage by section, missing required slots, lineage "
        "issues. Also handles Form 8843 generation, FBAR aggregation, "
        "I-983 STEM OPT training plan review, and tokenized data-room "
        "share links for external collaborators like attorneys and CPAs. "
        "Run the /guardian command to start it deterministically — or "
        "/guardian <your situation> (e.g. 'F-1 student, paid internship in "
        "2 weeks') to route straight to your case."
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
        "compliance", "corporate-compliance", "immigration", "tax",
        "h1b", "stem-opt", "opt", "cpt", "i-20",
        "form-8843", "form-1040-nr", "1040-nr", "fbar", "form-5472",
        "ein", "entity", "boi", "mcp", "nonresident",
    ],
    "license": "MIT",
    "server": {
        "type": "uv",
        "entry_point": "src/server.py",
        "mcp_config": {
            "command": "uv",
            "args": ["run", "--directory", "${__dirname}", "src/server.py"],
            "env": {
                "GUARDIAN_LICENSE_KEY": "${user_config.license_key}",
                "GUARDIAN_MODE": "local",
            },
        },
    },
    "user_config": {
        "license_key": {
            "type": "string",
            "title": "Guardian license key",
            "description": (
                "Get yours at https://guardiancompliance.app/connect "
                "(sign in, click Generate). Starts with gdn_oc_. Required to "
                "activate the extension; nothing else to configure — everything "
                "runs locally."
            ),
            "required": True,
            "sensitive": True,
        },
    },
    "tools": [
        {"name": "start_guardian",       "description": "Deterministically begin Guardian onboarding (type /guardian)"},
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
        {"name": "save_artifact",        "description": "Save a generated artifact into the Guardian artifacts directory"},
        {"name": "run_compliance_check", "description": "H-1B doc check, FBAR, 83(b), ..."},
        {"name": "cross_check_filings",  "description": "Cross-check your filings for mismatches, missing forms, deadlines"},
        {"name": "get_extraction_schema", "description": "Fields to extract for a given document type"},
        {"name": "record_extracted_facts", "description": "Record extracted fields into your facts source-of-truth"},
        {"name": "get_user_facts",       "description": "Read your facts source-of-truth"},
        {"name": "set_user_fact",        "description": "Lock a decided value into your facts source-of-truth"},
        {"name": "resolve_fact_conflict", "description": "Resolve a conflicting fact"},
        {"name": "share_data_room",      "description": "Upload your data room to Guardian cloud (with your approval)"},
        {"name": "list_egress_consents", "description": "List approved data-room sharing consents"},
        {"name": "revoke_egress_consent", "description": "Revoke a data-room sharing consent"},
        {"name": "lawyer_search_plan",   "description": "Plan a parallel lawyer / professional search"},
        {"name": "lawyer_search_ingest", "description": "Ingest professional-search results into the diligence DB"},
        {"name": "lawyer_tier_report",   "description": "Tiered report of discovered professionals"},
        {"name": "vendor_directory",     "description": "Browse the discovered professionals directory"},
        {"name": "vendor_detail",        "description": "Details on a discovered professional"},
        {"name": "get_filing_guidance",  "description": "Deadlines, mailing addresses, steps"},
        {"name": "gmail_search",         "description": "Find compliance-related emails"},
        {"name": "gmail_read",           "description": "Read a Gmail message"},
        {"name": "gmail_draft",          "description": "Draft with optional PDF attachment"},
        {"name": "gmail_send",           "description": "Send a draft"},
        {"name": "gmail_reply",          "description": "Reply in-thread"},
        {"name": "gmail_download_attachment", "description": "Save an attachment locally"},
    ],
    "compatibility": {
        "claude_desktop": ">=0.10.0",
        "platforms": ["darwin", "linux", "win32"],
        "runtimes": {
            "python": ">=3.11",
        },
    },
}


PYPROJECT_TOML = f"""[project]
name = "guardian-dxt"
version = "1.0.8"
description = "Guardian Compliance DXT runtime — pulls compliance-os from PyPI"
requires-python = ">=3.11"
dependencies = [
    "compliance-os[agent]{COMPLIANCE_OS_VERSION}",
]
"""


SERVER_PY = '''"""Guardian DXT entry point.

Imported and run by Claude Desktop via uv. Delegates to the
compliance_os.mcp_server module (installed from PyPI by uv on first
run, per pyproject.toml).
"""

from compliance_os.mcp_server import mcp


if __name__ == "__main__":
    mcp.run()
'''


REPO_ROOT = Path(__file__).resolve().parent.parent
ICON_SOURCE = REPO_ROOT / "frontend" / "public" / "assets" / "guardian-icon-white-512.png"


def build(output: Path) -> Path:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(MANIFEST, indent=2))
        zf.writestr("pyproject.toml", PYPROJECT_TOML)
        zf.writestr("src/server.py", SERVER_PY)
        if ICON_SOURCE.exists():
            zf.write(ICON_SOURCE, "icon.png")
        else:
            print(f"WARNING: icon not found at {ICON_SOURCE} — bundle has no icon")
    return output


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "frontend/public/guardian.dxt"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    built = build(out)
    size = built.stat().st_size
    print(f"Built {built} ({size} bytes)")
