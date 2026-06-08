"""MCP output-schema + local-mode contract regression tests (2.0.3).

WHY THIS FILE EXISTS
--------------------
2.0.2 shipped a bug that made EVERY tool fail in Claude Desktop with:

    "Output validation error: outputSchema defined but no structured output returned"

Root cause (two parts):
1. The extension installs against mcp>=1.0, which resolves to the newer
   FastMCP (1.27.x). That version AUTO-GENERATES an outputSchema
   ({"result": str, "required": ["result"]}) for every `-> str` tool.
2. `GatedMCP.call_tool` returns a BARE list[TextContent] on the license-block
   path — no structured content. The lowlevel MCP CallToolRequest handler then
   sees `outputSchema is not None and structuredContent is None` and rejects
   the response. Because the gate fires on EVERY tool when the license can't
   validate, the user saw this on every tool.

The pre-existing gate tests (tests/test_license.py) did NOT catch this: they
call `mcp.call_tool(...)` and assert on the extracted TEXT only — never the
LOWLEVEL CallToolRequest handler (the layer the desktop client drives) where
the outputSchema check runs.

These tests drive the exact lowlevel handler and assert the contract for both
blocked and unblocked states, that the local dashboard tools actually return
local data (the in-process ASGI fix), and that the gate fails open on a
transient validation outage rather than bricking the extension.
"""
from __future__ import annotations

import asyncio
import importlib
import json

import pytest
from mcp import types


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())


async def _call_via_lowlevel(mcp, name: str, arguments: dict):
    """Drive the *exact* lowlevel CallToolRequest handler the desktop client
    hits — the only layer where outputSchema validation runs."""
    low = mcp._mcp_server
    await low.request_handlers[types.ListToolsRequest](None)  # warm the tool cache
    handler = low.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name=name, arguments=arguments),
    )
    return (await handler(req)).root  # CallToolResult


def _assert_sdk_valid(result) -> str:
    assert result.content, "expected at least one content block"
    text = result.content[0].text
    assert "Output validation error" not in text, (
        f"lowlevel handler rejected the tool response: {text!r}"
    )
    assert result.isError is False, f"unexpected isError=True: {text!r}"
    return text


@pytest.fixture
def fresh_mcp(monkeypatch, tmp_path):
    """Import the MCP server in LOCAL-extension mode with an isolated home/DB,
    so we exercise exactly what ships and license/token state can't leak across
    tests. Yields (mcp_server, licensing)."""
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GUARDIAN_DISABLE_PREWARM", "1")
    monkeypatch.delenv("GUARDIAN_TOKEN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database

    database._engine = None
    database._SessionLocal = None
    import compliance_os.licensing as licensing
    import compliance_os.mcp_server as mcp_server

    importlib.reload(licensing)
    importlib.reload(mcp_server)
    assert mcp_server._is_hosted() is False
    yield mcp_server, licensing
    database._engine = None
    database._SessionLocal = None


def _make_active(licensing, monkeypatch):
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_test_key")
    monkeypatch.setattr(
        licensing,
        "validate_online",
        lambda key: {
            "valid": True, "status": "active", "tier": "free",
            "features": ["extraction", "chat", "facts", "documents"],
            "grace_until": None,
        },
    )
    assert licensing.activation_state() == "active"


# ── (a) invariant: no tool carries an outputSchema ───────────────────────────

def test_no_tool_has_output_schema(fresh_mcp):
    mcp_server, _ = fresh_mcp
    tools = _run(mcp_server.mcp.list_tools())
    assert tools, "expected the server to register tools"
    offenders = [t.name for t in tools if getattr(t, "outputSchema", None) is not None]
    assert offenders == [], (
        f"these tools still auto-generate an outputSchema (re-breaks the "
        f"license-block path under FastMCP >=1.10): {offenders}"
    )


# ── (b) blocked state is SDK-valid (the exact 2.0.2 crash) ───────────────────

def test_blocked_call_is_sdk_valid(fresh_mcp, monkeypatch):
    mcp_server, _ = fresh_mcp
    monkeypatch.delenv("GUARDIAN_LICENSE_KEY", raising=False)
    result = _run(_call_via_lowlevel(mcp_server.mcp, "guardian_documents", {}))
    text = _assert_sdk_valid(result)
    assert json.loads(text).get("error") == "activation_required"


# ── (c) unblocked dashboard tool returns REAL local data (in-process ASGI) ───

def test_unblocked_dashboard_tool_returns_local_data(fresh_mcp, monkeypatch):
    mcp_server, licensing = fresh_mcp
    _make_active(licensing, monkeypatch)
    result = _run(_call_via_lowlevel(mcp_server.mcp, "guardian_status", {}))
    text = _assert_sdk_valid(result)
    assert "Cannot reach Guardian API" not in text, text
    assert "Guardian Compliance Status" in text, text  # served from local DB


# ── (d) a pure-local tool round-trips while unblocked ────────────────────────

def test_unblocked_local_tool_round_trips(fresh_mcp, monkeypatch):
    mcp_server, licensing = fresh_mcp
    _make_active(licensing, monkeypatch)
    result = _run(
        _call_via_lowlevel(mcp_server.mcp, "get_extraction_schema", {"doc_type": "i20"})
    )
    text = _assert_sdk_valid(result)
    assert "sevis_id" in text  # the real local tool ran


# ── (e) gate fails OPEN on transient validation outage, but not on a bad key ─

def test_fail_open_when_key_set_and_validation_unreachable(fresh_mcp, monkeypatch):
    _, licensing = fresh_mcp
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_test_key")
    monkeypatch.setattr(licensing, "validate_online", lambda key: None)  # unreachable
    assert licensing.activation_state() == "active"


def test_server_says_invalid_still_blocks(fresh_mcp, monkeypatch):
    _, licensing = fresh_mcp
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_bad")
    monkeypatch.setattr(licensing, "validate_online", lambda key: {"valid": False})
    assert licensing.activation_state() == "inactive"
