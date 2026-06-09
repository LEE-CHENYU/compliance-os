"""The deterministic /guardian onboarding prompt (vs probabilistic topic detection)."""

import asyncio

from compliance_os import mcp_server
from compliance_os.mcp_server import guardian


def _prompt_names():
    prompts = asyncio.get_event_loop().run_until_complete(mcp_server.mcp.list_prompts())
    return {p.name for p in prompts}


def test_guardian_prompt_is_registered():
    assert "guardian" in _prompt_names()


def test_guardian_prompt_no_situation_runs_cold_start_onboarding():
    text = guardian().lower()
    assert "out of scope" in text          # scope gate
    assert "5472" in text                  # states coverage
    assert "don't open with a form" in text
    assert "read-state" in text            # don't probe empty state


def test_guardian_prompt_with_situation_routes_immediately():
    text = guardian("F-1 student, paid internship in 2 weeks")
    assert "F-1 student, paid internship in 2 weeks" in text
    assert "single question that decides the path" in text.lower()


def test_guardian_prompt_renders_as_user_message():
    res = asyncio.get_event_loop().run_until_complete(
        mcp_server.mcp.get_prompt("guardian", {"situation": "foreign-owned LLC 5472 question"})
    )
    assert res.messages[0].role == "user"
    assert "foreign-owned LLC 5472 question" in res.messages[0].content.text
