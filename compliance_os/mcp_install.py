"""Guardian MCP installer — one command to configure Claude Desktop, Claude Code, and Codex.

Usage:
    python -m compliance_os.mcp_install          # interactive
    python -m compliance_os.mcp_install --all     # configure all detected apps
    guardian-mcp install                          # via entry point
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path


# ─── App detection ───────────────────────────────────────────────

def _claude_desktop_config_path() -> Path | None:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Linux":
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    return None


def _claude_code_config_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def _detect_apps() -> list[dict[str, str | Path | bool]]:
    apps = []

    desktop_path = _claude_desktop_config_path()
    if desktop_path and desktop_path.parent.exists():
        apps.append({
            "name": "Claude Desktop",
            "path": desktop_path,
            "format": "json",
            "key": "mcpServers",
            "installed": True,
        })

    code_path = _claude_code_config_path()
    if code_path.parent.exists():
        apps.append({
            "name": "Claude Code",
            "path": code_path,
            "format": "json",
            "key": "mcpServers",
            "installed": True,
        })

    codex_path = _codex_config_path()
    if codex_path.exists():
        apps.append({
            "name": "Codex",
            "path": codex_path,
            "format": "toml",
            "key": "mcp_servers",
            "installed": True,
        })

    return apps


# ─── Config writers ──────────────────────────────────────────────

def _python_path() -> str:
    return sys.executable


def _mcp_server_config(api_url: str, token: str) -> dict:
    return {
        "command": _python_path(),
        "args": ["-m", "compliance_os.mcp_server"],
        "env": {
            "GUARDIAN_API_URL": api_url,
            "GUARDIAN_TOKEN": token,
        },
    }


def _write_json_config(path: Path, server_config: dict) -> bool:
    config = {}
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["guardian"] = server_config

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return True


def _write_toml_config(path: Path, api_url: str, token: str) -> bool:
    content = ""
    if path.exists():
        content = path.read_text(encoding="utf-8")

    # Remove existing guardian MCP config if present
    lines = content.split("\n")
    cleaned = []
    skip_until_next_section = False
    for line in lines:
        if line.strip().startswith("[mcp_servers.guardian"):
            skip_until_next_section = True
            continue
        if skip_until_next_section and line.strip().startswith("["):
            skip_until_next_section = False
        if skip_until_next_section and (line.strip().startswith(("command", "args", "type", "env", "GUARDIAN"))):
            continue
        if skip_until_next_section and line.strip() == "":
            continue
        cleaned.append(line)

    content = "\n".join(cleaned).rstrip()

    python = _python_path()
    toml_block = f'''

[mcp_servers.guardian]
type = "stdio"
command = "{python}"
args = ["-m", "compliance_os.mcp_server"]

[mcp_servers.guardian.env]
GUARDIAN_API_URL = "{api_url}"
GUARDIAN_TOKEN = "{token}"
'''

    content += toml_block
    path.write_text(content, encoding="utf-8")
    return True


# ─── Token setup ─────────────────────────────────────────────────

def _prompt_token() -> tuple[str, str]:
    print()
    print("  Guardian API connection")
    print("  -----------------------")
    print()
    print("  Where is your Guardian server?")
    print()
    print("  1. Local development  (http://localhost:8000 — auto-auth)")
    print("  2. Production         (https://guardiancompliance.app)")
    print("  3. Custom URL")
    print()

    choice = input("  Choose [1]: ").strip() or "1"

    if choice == "1":
        return "http://localhost:8000", ""
    elif choice == "2":
        print()
        print("  Get your token: guardiancompliance.app → Dashboard → Connect to OpenClaw")
        token = input("  Paste Guardian token: ").strip()
        return "https://guardiancompliance.app", token
    else:
        url = input("  Guardian API URL: ").strip()
        token = input("  Guardian token (blank for none): ").strip()
        return url, token


# ─── Main installer ──────────────────────────────────────────────

def install(auto_all: bool = False, local: bool = False):
    print()
    print("  ================================================")
    print("   Guardian MCP Installer")
    print("  ================================================")
    print()
    print(f"  Python: {_python_path()}")
    print()

    # Detect apps
    apps = _detect_apps()
    if not apps:
        print("  No supported apps detected.")
        print("  Supported: Claude Desktop, Claude Code, Codex CLI")
        print()
        print("  You can manually add to your MCP config:")
        print(f'    "command": "{_python_path()}"')
        print('    "args": ["-m", "compliance_os.mcp_server"]')
        return

    print(f"  Detected {len(apps)} app(s):")
    for i, app in enumerate(apps, 1):
        print(f"    {i}. {app['name']}  ({app['path']})")
    print()

    # Select apps
    if auto_all or local:
        selected = apps
    else:
        print("  Which apps to configure?")
        print()
        print(f"  a. All ({len(apps)} apps)")
        for i, app in enumerate(apps, 1):
            print(f"  {i}. {app['name']} only")
        print()

        choice = input("  Choose [a]: ").strip().lower() or "a"

        if choice == "a":
            selected = apps
        else:
            try:
                idx = int(choice) - 1
                selected = [apps[idx]]
            except (ValueError, IndexError):
                selected = apps

    # Get token
    if local:
        api_url, token = "http://localhost:8000", ""
    else:
        api_url, token = _prompt_token()

    # Write configs
    print()
    server_config = _mcp_server_config(api_url, token)

    for app in selected:
        path = app["path"]
        try:
            if app["format"] == "json":
                _write_json_config(path, server_config)
            elif app["format"] == "toml":
                _write_toml_config(path, api_url, token)

            print(f"  [ok] {app['name']}  →  {path}")
        except Exception as exc:
            print(f"  [!!] {app['name']}  →  {exc}")

    # Summary
    print()
    print("  ------------------------------------------------")
    print("  Done! Restart your app(s) to load Guardian tools.")
    print()
    print("  You'll have access to 18 tools:")
    print("    - guardian_status, guardian_deadlines, guardian_risks")
    print("    - parse_document, classify_document, upload_document")
    print("    - generate_form_8843, run_compliance_check")
    print("    - gmail_search, gmail_draft, gmail_send, ...")
    print()
    if api_url == "http://localhost:8000":
        print("  For context tools, start the Guardian server:")
        print("    uvicorn compliance_os.web.app:app")
        print()
    print("  Gmail setup (optional):")
    print("    python scripts/guardian_mcp_setup.py")
    print()


def uninstall():
    print()
    print("  Removing Guardian MCP from all apps...")
    print()

    apps = _detect_apps()
    for app in apps:
        path = app["path"]
        try:
            if app["format"] == "json" and path.exists():
                config = json.loads(path.read_text(encoding="utf-8"))
                servers = config.get("mcpServers", {})
                if "guardian" in servers:
                    del servers["guardian"]
                    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
                    print(f"  [ok] Removed from {app['name']}")
                else:
                    print(f"  [--] {app['name']} — not configured")

            elif app["format"] == "toml" and path.exists():
                content = path.read_text(encoding="utf-8")
                if "[mcp_servers.guardian]" in content:
                    lines = content.split("\n")
                    cleaned = []
                    skip = False
                    for line in lines:
                        if line.strip().startswith("[mcp_servers.guardian"):
                            skip = True
                            continue
                        if skip and line.strip().startswith("[") and not line.strip().startswith("[mcp_servers.guardian"):
                            skip = False
                        if skip:
                            continue
                        cleaned.append(line)
                    path.write_text("\n".join(cleaned), encoding="utf-8")
                    print(f"  [ok] Removed from {app['name']}")
                else:
                    print(f"  [--] {app['name']} — not configured")
        except Exception as exc:
            print(f"  [!!] {app['name']} — {exc}")

    print()
    print("  Done. Restart your apps to apply changes.")
    print()


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    if "uninstall" in args or "--uninstall" in args:
        uninstall()
        return

    auto_all = "--all" in args or "--auto" in args
    local = "--local" in args
    install(auto_all=auto_all, local=local)


if __name__ == "__main__":
    main()
