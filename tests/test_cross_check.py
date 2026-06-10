# tests/test_cross_check.py
import pytest


def test_load_chains_has_v1_chains():
    from compliance_os.compliance.cross_check import load_chains

    chains = load_chains()
    assert set(chains) == {"stem_opt", "h1b", "tax", "corporate"}
    stem = chains["stem_opt"]
    assert "i20" in stem["detect_when_any"]
    assert "sevis_id" in stem["must_agree"]
    assert any(d["doc_type"] == "i983" and d["required"] for d in stem["documents"])


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


def _seed(db, docs):
    """docs: list of (doc_type, {field_name: value}). Creates the local user,
    a check, and a DocumentRow + ExtractedFieldRows per entry. Returns user_id."""
    from compliance_os import local_engine
    from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, ExtractedFieldRow

    user_id = local_engine.get_local_user_id(db)
    check = CheckRow(track="stem_opt", status="saved", user_id=user_id, answers={})
    db.add(check); db.flush()
    for doc_type, fields in docs:
        doc = DocumentRow(check_id=check.id, doc_type=doc_type, filename=f"{doc_type}.txt",
                          file_path=f"/x/{doc_type}.txt", file_size=1, mime_type="text/plain",
                          is_active=True)
        db.add(doc); db.flush()
        for fname, fval in fields.items():
            db.add(ExtractedFieldRow(document_id=doc.id, field_name=fname, field_value=fval, confidence=0.95))
    db.commit()
    return user_id


def test_contributions_maps_fields_to_canonical_keys(local_db):
    from compliance_os.compliance import cross_check
    db = next(local_db.get_session())
    try:
        uid = _seed(db, [
            ("i20", {"student_name": "Jane Q", "sevis_number": "N0001234567"}),
            ("i983", {"sevis_number": "N0001234567", "employer_name": "Acme Inc"}),
        ])
        contrib = cross_check._contributions(db, uid)
        assert ("i20", "N0001234567") in [(d, v) for (d, _id, v) in contrib["sevis_id"]]
        assert "Acme Inc" in [v for (_d, _id, v) in contrib["current_employer_legal_name"]]
    finally:
        db.close()


def test_mismatch_flags_employer_name_not_salary_format(local_db):
    from compliance_os.compliance import cross_check
    db = next(local_db.get_session())
    try:
        uid = _seed(db, [
            ("i983", {"employer_name": "Acme Inc", "compensation": "$135,000"}),
            ("employment_letter", {"employer_name": "Acme Incorporated", "compensation": "135000"}),
        ])
        contrib = cross_check._contributions(db, uid)
        # employer name differs after normalization -> mismatch
        keys = ["current_employer_legal_name", "current_annual_salary"]
        findings = cross_check._mismatches(keys, contrib)
        facts = {f["fact"] for f in findings}
        assert "current_employer_legal_name" in facts       # "Acme Inc" != "Acme Incorporated"
        assert "current_annual_salary" not in facts          # 135000 == 135000 after normalize
        emp = next(f for f in findings if f["fact"] == "current_employer_legal_name")
        assert all(isinstance(v, str) for v in emp["values"])
        assert set(emp["values"]) == {"Acme Inc", "Acme Incorporated"}
        assert isinstance(emp["sources"], list) and emp["sources"]
    finally:
        db.close()


def test_normalize_examples():
    from compliance_os.compliance.cross_check import _normalize
    assert _normalize("current_annual_salary", "$135,000") == _normalize("current_annual_salary", "135000")
    assert _normalize("current_employer_ein", "37-2222933") == _normalize("current_employer_ein", "372222933")
    assert _normalize("legal_name", "Jane Q ") == _normalize("legal_name", "jane q")


def test_detect_and_missing(local_db):
    from compliance_os.compliance import cross_check
    db = next(local_db.get_session())
    try:
        uid = _seed(db, [("i20", {"sevis_number": "N1"}), ("ead", {"valid_to": "2027-05-14"})])
        present = cross_check._present_doc_types(db, uid)
        detected = cross_check._detect_chains(present)
        assert "stem_opt" in detected and "tax" not in detected
        missing = cross_check._missing("stem_opt", present)
        missing_types = {m["doc_type"] for m in missing}
        assert "i983" in missing_types          # required, absent
        assert "i20" not in missing_types       # present
    finally:
        db.close()


def test_deadlines_and_relationship(local_db):
    from datetime import date, timedelta
    from compliance_os.compliance import cross_check
    from compliance_os.web.services.user_facts import upsert_fact

    db = next(local_db.get_session())
    try:
        from compliance_os import local_engine
        uid = local_engine.get_local_user_id(db)
        soon = (date.today() + timedelta(days=60)).isoformat()
        far = (date.today() + timedelta(days=900)).isoformat()
        for k, v in [("stem_opt_end_date", soon), ("h1b_classification_end_date", far),
                     ("h1b_classification_start_date", "2025-01-01")]:
            upsert_fact(db, user_id=uid, fact_key=k, value=v, source_type="document", source_ref={})
        db.commit()
        facts = cross_check._fact_values(db, uid)

        dls = cross_check._deadlines(["stem_opt_end_date", "h1b_classification_end_date"], facts, horizon_days=180)
        keys = {d["fact"] for d in dls}
        assert "stem_opt_end_date" in keys          # 60 days out -> surfaced
        assert "h1b_classification_end_date" not in keys  # 900 days -> beyond horizon

        rel = cross_check._relationships(
            [{"id": "h1b_after_opt", "op": "date_order", "before": "stem_opt_end_date",
              "after": "h1b_classification_start_date", "message": "..."}], facts)
        # stem_opt_end (60d future) is AFTER h1b start (2025) -> violation
        assert any(f["rule"] == "h1b_after_opt" for f in rel)
    finally:
        db.close()


def test_cross_check_end_to_end(local_db):
    from compliance_os.compliance import cross_check
    from compliance_os import local_engine

    db = next(local_db.get_session())
    try:
        # messy data room: employer-name mismatch + missing I-983 + (no EAD date)
        uid = _seed(db, [
            ("i20", {"student_name": "Jane Q", "sevis_number": "N0001234567"}),
            ("offer_letter", {"employer_name": "Acme Inc"}),
            ("employment_letter", {"employee_name": "Jane Q", "employer_name": "Acme Incorporated"}),
            ("ead", {"valid_to": "2099-01-01"}),
        ])
        report = cross_check.cross_check(db, uid)
        assert "stem_opt" in report["chains_detected"]
        cats = {f["category"] for f in report["findings"]}
        assert "mismatch" in cats          # Acme Inc vs Acme Incorporated
        assert "missing" in cats           # I-983 required, absent
        assert report["summary"]["mismatches"] >= 1
        # scoping to a non-detected chain returns no findings
        only_tax = cross_check.cross_check(db, uid, chain="tax")
        assert only_tax["chains_detected"] == []
    finally:
        db.close()


def test_mcp_cross_check_filings_tool(local_db):
    from compliance_os import local_engine, mcp_server

    db = next(local_db.get_session())
    try:
        _seed(db, [("i20", {"sevis_number": "N1"}), ("ead", {"valid_to": "2099-01-01"})])
    finally:
        db.close()
    # cross_check_filings now returns a ready-to-show Markdown card.
    out = mcp_server.cross_check_filings()
    assert "Cross-check" in out
    # and the structured engine still returns the raw shape underneath
    raw = local_engine.local_cross_check("")
    assert "findings" in raw and "chains_detected" in raw
