"""Gmail API client with OAuth2 for the Guardian MCP server.

Token storage: ~/.config/guardian/gmail_token.json
Credentials:   ~/.config/guardian/gmail_credentials.json

Setup: Run `python scripts/guardian_mcp_setup.py` to complete the
one-time OAuth2 consent flow.
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR = Path(
    os.environ.get("GUARDIAN_CONFIG_DIR", "~/.config/guardian")
).expanduser()
TOKEN_PATH = CONFIG_DIR / "gmail_token.json"
CREDENTIALS_PATH = CONFIG_DIR / "gmail_credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

_service = None


def get_service():
    """Get an authenticated Gmail API service object (cached per process)."""
    global _service
    if _service is not None:
        return _service

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "Gmail dependencies not installed. Run: "
            "pip install 'compliance-os[agent]'"
        ) from exc

    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail OAuth credentials not found at {CREDENTIALS_PATH}.\n\n"
                    "Setup instructions:\n"
                    "1. Go to https://console.cloud.google.com/apis/credentials\n"
                    "2. Create an OAuth 2.0 Client ID (type: Desktop application)\n"
                    "3. Enable the Gmail API in your project\n"
                    "4. Download the credentials JSON\n"
                    f"5. Save it as: {CREDENTIALS_PATH}\n"
                    "6. Run: python scripts/guardian_mcp_setup.py"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())

    _service = build("gmail", "v1", credentials=creds)
    return _service
