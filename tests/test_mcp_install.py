"""Regression tests for the guardian-mcp installer.

Covers the two ways the documented zero-fetch agent path broke
(2026-06-11): the installer prompting interactively despite
GUARDIAN_TOKEN being set (EOFError in agent shells), and the Claude
Code config landing in ~/.claude/settings.json, which Claude Code
never reads for server registration (user scope is ~/.claude.json).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from compliance_os import mcp_install


def test_license_key_read_from_guardian_token_env(monkeypatch):
    monkeypatch.delenv("GUARDIAN_LICENSE_KEY", raising=False)
    monkeypatch.setenv("GUARDIAN_TOKEN", " gdn_oc_abc_def ")
    # Must not reach input() at all — make it explode if touched.
    monkeypatch.setattr(
        "builtins.input", lambda *_: pytest.fail("prompted despite env key")
    )
    assert mcp_install._prompt_license_key() == "gdn_oc_abc_def"


def test_license_key_prefers_guardian_license_key_env(monkeypatch):
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_primary_key")
    monkeypatch.setenv("GUARDIAN_TOKEN", "gdn_oc_secondary_key")
    assert mcp_install._prompt_license_key() == "gdn_oc_primary_key"


def test_license_key_no_env_no_tty_exits_cleanly(monkeypatch):
    monkeypatch.delenv("GUARDIAN_LICENSE_KEY", raising=False)
    monkeypatch.delenv("GUARDIAN_TOKEN", raising=False)

    def _raise_eof(*_):
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise_eof)
    with pytest.raises(SystemExit) as exc:
        mcp_install._prompt_license_key()
    assert exc.value.code == 1


def test_claude_code_config_is_user_scope_claude_json():
    # ~/.claude/settings.json does NOT register MCP servers; user scope
    # lives in ~/.claude.json under the top-level mcpServers key.
    assert mcp_install._claude_code_config_path() == Path.home() / ".claude.json"


def test_claude_code_not_detected_on_machine_without_claude(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Path.home() honors HOME on POSIX.
    apps = [a["name"] for a in mcp_install._detect_apps()]
    assert "Claude Code" not in apps


def test_claude_code_detected_via_dot_claude_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    apps = [a["name"] for a in mcp_install._detect_apps()]
    assert "Claude Code" in apps
