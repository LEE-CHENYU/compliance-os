"""One-time setup for the Guardian MCP server.

Handles Gmail OAuth2 consent and verifies Guardian API connectivity.

Usage:
    python scripts/guardian_mcp_setup.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib import error, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compliance_os.gmail_client import CONFIG_DIR, CREDENTIALS_PATH, TOKEN_PATH


def _check_guardian_api():
    api_url = os.environ.get("GUARDIAN_API_URL", "http://localhost:8000")
    token = os.environ.get("GUARDIAN_TOKEN", "")
    print(f"Guardian API: {api_url}")

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(f"{api_url}/api/dashboard/stats", headers=headers)
    try:
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"  Connected — {data.get('documents', '?')} documents in data room")
            return True
    except error.HTTPError as exc:
        if exc.code == 401:
            print("  Auth failed — set GUARDIAN_TOKEN to a valid OpenClaw-scoped token")
        else:
            print(f"  HTTP {exc.code}")
        return False
    except Exception as exc:
        print(f"  Not reachable: {exc}")
        print("  Start the Guardian server (uvicorn compliance_os.web.app:app)")
        print("  or set GUARDIAN_API_URL to point to the deployed instance")
        return False


def _setup_gmail():
    print(f"\nGmail credentials directory: {CONFIG_DIR}")

    if not CREDENTIALS_PATH.exists():
        print(f"\n  Credentials not found at: {CREDENTIALS_PATH}")
        print()
        print("  To enable Gmail tools:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create an OAuth 2.0 Client ID (Desktop application)")
        print("  3. Enable the Gmail API in your Google Cloud project")
        print("  4. Download the JSON credentials")
        print(f"  5. Save as: {CREDENTIALS_PATH}")
        print("  6. Run this script again")
        return False

    if TOKEN_PATH.exists():
        print("  Token already exists — checking validity...")
        try:
            from compliance_os.gmail_client import get_service

            service = get_service()
            profile = service.users().getProfile(userId="me").execute()
            print(f"  Connected as: {profile.get('emailAddress', 'unknown')}")
            return True
        except Exception as exc:
            print(f"  Token invalid, re-authenticating: {exc}")
            TOKEN_PATH.unlink(missing_ok=True)

    print("  Starting OAuth flow (a browser window will open)...")
    try:
        from compliance_os.gmail_client import get_service

        service = get_service()
        profile = service.users().getProfile(userId="me").execute()
        print(f"  Connected as: {profile.get('emailAddress', 'unknown')}")
        print(f"  Token saved to: {TOKEN_PATH}")
        return True
    except Exception as exc:
        print(f"  Setup failed: {exc}")
        return False


def main():
    print("=" * 50)
    print("  Guardian MCP Server Setup")
    print("=" * 50)
    print()

    print("1. Checking Guardian API connectivity...")
    api_ok = _check_guardian_api()

    print("\n2. Setting up Gmail OAuth2...")
    gmail_ok = _setup_gmail()

    print("\n" + "=" * 50)
    print("  Summary")
    print("=" * 50)
    print(f"  Guardian API: {'OK' if api_ok else 'Not connected (context tools unavailable)'}")
    print(f"  Gmail:        {'OK' if gmail_ok else 'Not configured (Gmail tools unavailable)'}")
    print()

    if api_ok or gmail_ok:
        print("  MCP server is ready. Add to Claude Code:")
        print()
        print('  In .claude/mcp.json:')
        print('  {')
        print('    "mcpServers": {')
        print('      "guardian": {')
        print('        "command": "conda",')
        print('        "args": ["run", "-n", "compliance-os", "--no-banner",')
        print('                 "python", "-m", "compliance_os.mcp_server"]')
        print("      }")
        print("    }")
        print("  }")
    else:
        print("  Neither Guardian API nor Gmail are configured.")
        print("  Configure at least one to use the MCP server.")

    sys.exit(0 if (api_ok or gmail_ok) else 1)


if __name__ == "__main__":
    main()
