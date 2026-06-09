"""Lock the cold-start guidance into the Guardian MCP server instructions."""

from compliance_os import mcp_server


def test_instructions_constant_is_wired_into_the_server():
    assert mcp_server.mcp.instructions == mcp_server.GUARDIAN_INSTRUCTIONS


def test_instructions_cover_tool_honesty_and_real_checks():
    instr = mcp_server.GUARDIAN_INSTRUCTIONS
    assert "save_artifact" in instr
    for check in ("h1b_doc_check", "fbar", "student_tax", "83b_election"):
        assert check in instr
    assert "form_8843" in instr
    low = instr.lower()
    assert "fabricate" in low or "never narrate a tool call" in low
    assert "not a number my tools compute" in low or "reasoned read" in low


def test_instructions_cover_cold_start_and_routing():
    low = mcp_server.GUARDIAN_INSTRUCTIONS.lower()
    assert "blank slate" in low
    assert "out of scope" in low
    assert "fail closed" in low
    assert "dependent" in low
    assert "scholarship" in low
    assert "advance parole" in low


def test_instructions_cover_human_referral_and_tracks():
    instr = mcp_server.GUARDIAN_INSTRUCTIONS
    low = instr.lower()
    assert "consult" in low and "attorney" in low
    assert "lawyer_search_plan" in instr
    assert "set_user_fact" in instr
    assert "foreign_owned_llc" in instr


def test_instructions_forbid_simulated_tool_returns():
    # The e2e re-test found the surviving failure mode: the model authoring a
    # fake tool return and narrating its invented contents as fact.
    instr = mcp_server.GUARDIAN_INSTRUCTIONS
    low = instr.lower()
    assert "author a tool return" in low
    assert "sevis id" in low  # the specific-identifier prohibition
    # Real return shapes are pinned so the model stops inventing schemas.
    assert "file scanner" in low
    assert "no firm names" in low
    # case_active_search advertises the new generic templates (not just h1b/cpa).
    for tpl in ("founder_h1b", "form_5472", "eb1a", "dependent_status"):
        assert tpl in instr


def test_instructions_forbid_pre_running_a_real_check():
    # The targeted re-confirm found Leo still narrating "I ran the 83(b) check, it
    # confirms" with no actual call — because run_compliance_check is a REAL tool the
    # model rationalizes "pre-running from memory." The real-check clause closes it.
    low = mcp_server.GUARDIAN_INSTRUCTIONS.lower()
    assert "only if a real call to that exact check appears in this turn" in low
    assert "do not narrate a completed result" in low


def test_instructions_close_the_loop_and_persist_facts():
    # The e2e flagged two follow-ups: document-first loop set up but never closed,
    # and set_user_fact persistence treated as optional.
    low = mcp_server.GUARDIAN_INSTRUCTIONS.lower()
    assert "close the loop" in low
    assert "make getting one file your single next ask" in low
    assert "persist as you go" in low
    assert "in the same turn -- do not defer it" in low
