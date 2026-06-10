"""The reactive cascade: a SoT write re-runs cross_check and reports only what's
NEW, plus rule checks the new facts make runnable."""

import pytest

from compliance_os import cascade as C
from compliance_os import presenters as P


@pytest.fixture
def local_db(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield database
    database._engine = None
    database._SessionLocal = None


# ── cascade unit logic (no DB) ─────────────────────────────────────

def test_suggested_checks_from_trigger_facts():
    out = C.suggested_checks(["foreign_account_aggregate_high", "h1b_receipt_number"])
    checks = {s["check"] for s in out}
    assert checks == {"fbar", "h1b_doc_check"}


def test_suggested_checks_dedup_and_ignores_unmapped():
    out = C.suggested_checks(["h1b_receipt_number", "lca_case_number", "date_of_birth"])
    # both H-1B triggers collapse to a single h1b_doc_check suggestion
    assert [s["check"] for s in out] == ["h1b_doc_check"]


def test_finding_key_is_stable_per_category():
    assert C._finding_key({"category": "mismatch", "fact": "employer"}) == "mismatch:employer"
    assert C._finding_key({"category": "missing", "chain": "h1b", "doc_type": "ead"}) == "missing:h1b:ead"
    assert C._finding_key({"category": "deadline", "fact": "x", "date": "2026-07-01"}) == "deadline:x:2026-07-01"


# ── format_cascade presenter ───────────────────────────────────────

def test_format_cascade_renders_new_findings_and_suggestions():
    out = P.format_cascade({
        "new_findings": [
            {"category": "mismatch", "fact": "current_employer_legal_name"},
            {"category": "missing", "chain": "stem_opt", "doc_type": "ead", "label": "EAD / I-766"},
            {"category": "deadline", "message": "stem_opt_end_date is 22 days away"},
        ],
        "suggested_checks": [{"check": "fbar", "reason": "you now have your foreign-account aggregate balance"}],
    })
    assert "This triggered" in out                 # real findings section
    assert "current_employer_legal_name" in out
    assert "EAD / I-766" in out
    assert "22 days away" in out
    assert "Now available to run" in out            # offers are a separate section
    assert "fbar" in out and "want me to run" in out


def test_format_cascade_empty_when_nothing_new():
    assert P.format_cascade({"new_findings": [], "suggested_checks": []}) == ""
    assert P.format_cascade(None) == ""


def test_wedge_appends_cascade():
    wedge = P.format_fact_wedge({
        "fact": {"label": "Foreign account high", "value": {"v": "63500"}, "detected_conflicts": []},
        "superseded": None,
        "cascade": {"new_findings": [], "suggested_checks": [
            {"check": "fbar", "reason": "you now have your foreign-account aggregate balance"}]},
    })
    assert "Locked into your source of truth" in wedge
    assert "Now available to run" in wedge   # offer-only (no real finding here)
    assert "fbar" in wedge


def test_record_wedge_appends_cascade():
    wedge = P.format_record_wedge({
        "recorded_fields": ["petitioner_name"],
        "changes": [{"label": "Employer", "old": {"v": "Acme Inc"}, "new": {"v": "Acme LLC"}}],
        "conflicts": [],
        "cascade": {"new_findings": [{"category": "mismatch", "fact": "current_employer_legal_name"}],
                    "suggested_checks": []},
    })
    assert "Read 1 field" in wedge
    assert "This triggered" in wedge
    assert "current_employer_legal_name" in wedge


def test_cascade_value_is_sanitized():
    # a poisoned reason/finding can't break the card
    out = P.format_cascade({
        "new_findings": [{"category": "mismatch", "fact": "a\r| evil"}],
        "suggested_checks": [],
    })
    assert "\r" not in out


# ── end-to-end through the real write path ─────────────────────────

def test_set_fact_cascade_integration(local_db):
    from compliance_os import local_engine
    res = local_engine.local_set_fact("foreign_account_aggregate_high", "63500")
    assert "cascade" in res
    assert any(s["check"] == "fbar" for s in res["cascade"]["suggested_checks"])
    # and it renders in the wedge card the tool returns
    card = P.format_fact_wedge(res)
    assert "Now available to run" in card and "fbar" in card


def test_set_fact_no_trigger_no_cascade(local_db):
    from compliance_os import local_engine
    res = local_engine.local_set_fact("date_of_birth", "1995-01-01")
    # an unmapped fact suggests nothing and (on an empty room) finds nothing new
    assert res["cascade"]["suggested_checks"] == []
    assert "This triggered" not in P.format_fact_wedge(res)
    assert "Now available to run" not in P.format_fact_wedge(res)


def test_set_fact_idempotent_reset_does_not_reoffer(local_db):
    from compliance_os import local_engine
    local_engine.local_set_fact("foreign_account_aggregate_high", "63500")
    # re-locking the SAME value must not re-fire the offer
    res2 = local_engine.local_set_fact("foreign_account_aggregate_high", "63500")
    assert res2["cascade"]["suggested_checks"] == []
    assert "Now available to run" not in P.format_fact_wedge(res2)
