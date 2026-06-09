"""The honesty linter flags unbacked tool-result claims (the e2e fabrication mode)."""

from compliance_os.honesty_lint import flag_unbacked_tool_claims, lint_turn


# ---- POSITIVES: completed claim, no backing tool call -> must flag ----

def test_flags_ran_a_check_with_no_call():
    flags = flag_unbacked_tool_claims(
        "Good -- you gave me everything, so I just ran the real 83(b) check on your numbers.",
        tools_called=[],
    )
    assert len(flags) >= 1
    assert any(f.claim_type == "ran_check" for f in flags)


def test_flags_check_confirms_with_no_call():
    flags = flag_unbacked_tool_claims(
        "I ran run_compliance_check(83b_election). It confirms the 30-day window and returns the deadline.",
        tools_called=[],
    )
    assert any(f.claim_type == "ran_check" for f in flags)


def test_flags_from_the_check_phrase():
    flags = flag_unbacked_tool_claims(
        "Here is the exact IRS mailing address from the check.", tools_called=[]
    )
    assert any(f.claim_type == "ran_check" for f in flags)


def test_flags_document_field_values_without_parse():
    flags = flag_unbacked_tool_claims(
        "Your I-20 shows SEVIS ID N0012345678 and DSO Maria L. Hernandez.",
        tools_called=[],
    )
    assert any(f.claim_type == "read_document" for f in flags)


def test_flags_saved_file_without_save_artifact():
    flags = flag_unbacked_tool_claims(
        "I've saved the completed Form 8843 to your Downloads folder.", tools_called=[]
    )
    assert any(f.claim_type == "saved_file" for f in flags)


def test_flags_search_results_without_ingest():
    flags = flag_unbacked_tool_claims(
        "Your attorney shortlist is finishing now -- here are the named firms.",
        tools_called=["lawyer_search_plan"],  # plan only builds prompts; ingest is what produces results
    )
    assert any(f.claim_type == "search_results" for f in flags)


# ---- NEGATIVES: backed by a real call, or future/offer/labeled-reasoning -> must NOT flag ----

def test_no_flag_when_check_actually_called():
    flags = flag_unbacked_tool_claims(
        "I just ran the real 83(b) check on your numbers -- it returns June 20.",
        tools_called=["run_compliance_check"],
    )
    assert flags == []


def test_no_flag_future_tense_offer():
    flags = flag_unbacked_tool_claims(
        "Once you give me the date and state, I'll run the real 83(b) check this turn.",
        tools_called=[],
    )
    assert flags == []


def test_no_flag_i_can_run():
    flags = flag_unbacked_tool_claims(
        "I can run the 83(b) check once you paste the agreement -- I won't guess.",
        tools_called=[],
    )
    assert flags == []


def test_no_flag_labeled_reasoning_deadline():
    flags = flag_unbacked_tool_claims(
        "The 30-day rule puts your deadline at June 20 -- that's my read of the rule, not a computed check.",
        tools_called=[],
    )
    assert flags == []


def test_no_flag_offer_to_read_document():
    flags = flag_unbacked_tool_claims(
        "Point me at your I-20 and I'll read what's actually on it.", tools_called=[]
    )
    assert flags == []


def test_no_flag_saved_when_save_artifact_called():
    flags = flag_unbacked_tool_claims(
        "I've saved the Form 8843 to ~/Downloads/form8843.pdf.",
        tools_called=["save_artifact"],
    )
    assert flags == []


def test_lint_turn_summary_shape():
    res = lint_turn("I ran the check and it confirms.", tools_called=[])
    assert res["ok"] is False
    assert len(res["flags"]) >= 1
    ok = lint_turn("I'll run the check once you send the date.", tools_called=[])
    assert ok["ok"] is True
    assert ok["flags"] == []
