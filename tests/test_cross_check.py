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
