"""Contract tests for the Markdown card presenters.

These pin the visible-result contract: when a Guardian tool fires, the user
sees a consistent card (old→new wedge, verdict + findings table, severity
markers, mismatch diff) — not raw JSON. Pure functions, no DB.
"""

from compliance_os import presenters as P


# ── ① set_user_fact wedge ──────────────────────────────────────────

def test_fact_wedge_shows_old_to_new():
    out = P.format_fact_wedge({
        "fact": {"label": "Current employer", "value": {"v": "Acme Robotics LLC"},
                 "source_type": "decision_lock", "detected_conflicts": []},
        "superseded": {"value": {"v": "Acme Robotics Inc"}},
    })
    assert "Locked into your source of truth" in out
    assert "Current employer" in out
    assert "Acme Robotics LLC" in out
    assert "was: Acme Robotics Inc" in out


def test_fact_wedge_first_time_has_no_was():
    out = P.format_fact_wedge({
        "fact": {"label": "EIN", "value": {"v": "99-1234567"}, "detected_conflicts": []},
        "superseded": None,
    })
    assert "EIN" in out and "99-1234567" in out
    assert "was:" not in out


def test_fact_wedge_surfaces_conflict():
    out = P.format_fact_wedge({
        "fact": {"label": "Job title", "value": {"v": "Software Engineer"},
                 "detected_conflicts": [{"claimed_value": "SW Engineer II"}]},
        "superseded": None,
    })
    assert "SW Engineer II" in out
    assert "reconcile" in out.lower()


# ── record_extracted_facts wedge ───────────────────────────────────

def test_record_wedge_lists_new_and_changed():
    out = P.format_record_wedge({
        "recorded_fields": ["petitioner_name", "receipt_number"],
        "changes": [
            {"label": "Receipt number", "old": None, "new": {"v": "EAC2690000001"}},
            {"label": "Current employer", "old": {"v": "Acme Inc"}, "new": {"v": "Acme LLC"}},
        ],
        "conflicts": [],
    })
    assert "Read 2 fields" in out
    assert "Receipt number" in out and "EAC2690000001" in out
    assert "Current employer" in out and "was: Acme Inc" in out


def test_record_wedge_conflict_block():
    out = P.format_record_wedge({
        "recorded_fields": ["job_title"],
        "changes": [],
        "conflicts": [{
            "label": "Job title", "value": {"v": "Software Engineer"},
            "detected_conflicts": [{"claimed_value": "SW Engineer II"}],
        }],
    })
    assert "need a decision" in out.lower()
    assert "Software Engineer" in out and "SW Engineer II" in out


def test_record_wedge_singular_field():
    out = P.format_record_wedge({"recorded_fields": ["sevis_number"], "changes": [], "conflicts": []})
    assert "Read 1 field " in out  # singular, no trailing 's'


# ── ② run_compliance_check card ────────────────────────────────────

def test_compliance_card_student_tax_table_and_verdict():
    out = P.format_compliance_result("student_tax", {
        "summary": "1 blocking issue.",
        "findings": [
            {"severity": "critical", "title": "Resident software can't file 1040-NR",
             "consequence": "filing the wrong return risks a residency-status error"},
            {"severity": "info", "title": "China treaty Art. 20(c)", "consequence": "saves $5,000"},
        ],
        "filing_deadline": "2026-04-15",
        "next_steps": ["Switch to Sprintax", "File 1040-NR"],
        "artifacts": [{"label": "Download package", "path": "/tmp/p.pdf"}],
    })
    assert "Student tax check" in out
    assert "| Finding |" in out                 # a table rendered
    assert "🔴" in out and "🔵" in out           # severity glyphs
    assert "Resident software" in out
    assert "2026-04-15" in out
    assert "/tmp/p.pdf" in out


def test_compliance_card_fbar_verdict_from_bool():
    out = P.format_compliance_result("fbar", {
        "summary": "Filing required.", "requires_fbar": True, "filing_deadline": "2026-10-15",
    })
    assert "FBAR check" in out
    assert "required" in out


def test_compliance_card_handles_missing_keys():
    # must not raise on a sparse result
    out = P.format_compliance_result("83b_election", {"verdict": "pass"})
    assert "83(b)" in out


# ── ③ risks & deadlines ────────────────────────────────────────────

def test_risks_sorted_and_tabled():
    out = P.format_risks([
        {"severity": "info", "title": "Form 8843 still required", "action": "file it"},
        {"severity": "critical", "title": "Unauthorized employment risk", "action": "stop work"},
    ])
    # critical sorts above info
    assert out.index("Unauthorized employment") < out.index("Form 8843")
    assert "| Finding | Do |" in out


def test_risks_empty():
    assert "No active compliance findings" in P.format_risks([])


def test_deadlines_overdue_and_soon():
    out = P.format_deadlines([
        {"title": "Tax return", "days": -55, "action": "file now", "date": "2026-04-15"},
        {"title": "OPT ends", "days": 22, "action": "plan", "date": "2026-07-01"},
        {"title": "FBAR", "days": 120, "action": "file", "date": "2026-10-15"},
    ])
    assert "55d overdue" in out
    assert "22d" in out
    # overdue sorts first
    assert out.index("Tax return") < out.index("OPT ends") < out.index("FBAR")


def test_deadlines_empty():
    assert "No upcoming deadlines" in P.format_deadlines([])


# ── ④ cross_check / doc mismatch card ──────────────────────────────

def test_cross_check_mismatch_side_by_side():
    out = P.format_cross_check({
        "chains_detected": ["stem_opt", "h1b"],
        "summary": {"mismatches": 1, "missing": 1, "deadlines": 0, "high_severity": 2},
        "findings": [
            {"category": "mismatch", "severity": "high", "fact": "current_employer_legal_name",
             "values": ["Acme Robotics Inc", "Acme Robotics LLC"],
             "sources": [
                 {"value": "Acme Robotics Inc", "docs": ["i983", "offer_letter"]},
                 {"value": "Acme Robotics LLC", "docs": ["i797"]},
             ],
             "recommended_action": "Confirm the correct entity."},
            {"category": "missing", "severity": "high", "doc_type": "ead",
             "label": "EAD / I-766", "recommended_action": "Upload your EAD."},
        ],
    })
    assert "current_employer_legal_name" in out
    assert "| Value | Appears in |" in out      # the diff table
    assert "Acme Robotics Inc" in out and "Acme Robotics LLC" in out
    assert "`i983`" in out and "`i797`" in out
    assert "Missing" in out and "EAD / I-766" in out


def test_cross_check_clean():
    out = P.format_cross_check({"chains_detected": ["tax"], "summary": {}, "findings": []})
    assert "No conflicts" in out


def test_cross_check_pipe_in_value_is_escaped():
    # a value containing a pipe must not break the table
    out = P.format_cross_check({
        "chains_detected": [], "summary": {"mismatches": 1},
        "findings": [{"category": "mismatch", "fact": "x", "severity": "high",
                      "sources": [{"value": "A|B", "docs": ["d1"]}]}],
    })
    assert "A\\|B" in out
