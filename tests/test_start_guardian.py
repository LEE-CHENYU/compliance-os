"""The deterministic /guardian trigger — a start_guardian TOOL (not just the
prompt), so it fires in tool-only surfaces like Cowork where prompts aren't
typeable."""

import asyncio

from compliance_os import mcp_server
from compliance_os.mcp_server import guardian, start_guardian, _guardian_kickoff


def _tool_names():
    tools = asyncio.get_event_loop().run_until_complete(mcp_server.mcp.list_tools())
    return {t.name for t in tools}


def test_start_guardian_tool_is_registered():
    assert "start_guardian" in _tool_names()


def test_start_guardian_matches_prompt_byte_for_byte():
    # The tool and the prompt must behave identically (shared kickoff).
    assert start_guardian("") == guardian("") == _guardian_kickoff("")
    sit = "F-1 internship in 2 weeks"
    assert start_guardian(sit) == guardian(sit) == _guardian_kickoff(sit)


def test_start_guardian_no_situation_runs_cold_start():
    text = start_guardian().lower()
    assert "cold-start onboarding" in text
    assert "out of scope" in text  # states scope honestly
    assert "don't open with a form" in text


def test_start_guardian_with_situation_routes_immediately():
    text = start_guardian("foreign-owned US LLC, 5472 penalty")
    assert "foreign-owned US LLC, 5472 penalty" in text
    assert "single question that decides the path" in text.lower()


def test_start_guardian_description_steers_the_trigger():
    tools = asyncio.get_event_loop().run_until_complete(mcp_server.mcp.list_tools())
    desc = next(t.description for t in tools if t.name == "start_guardian").lower()
    assert "/guardian" in desc
    assert "immediately" in desc


def test_instructions_have_deterministic_trigger_and_show_card_rules():
    instr = mcp_server.GUARDIAN_INSTRUCTIONS
    assert "DETERMINISTIC START" in instr
    assert "start_guardian" in instr
    assert "SHOW WHAT YOU DID" in instr
