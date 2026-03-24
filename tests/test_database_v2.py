"""Tests for Guardian check flow database tables."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from compliance_os.web.models.tables_v2 import (
    Base,
    CheckRow,
    ComparisonRow,
    DocumentRow,
    ExtractedFieldRow,
    FindingRow,
    FollowupRow,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_check(db):
    check = CheckRow(track="stem_opt", status="intake", answers={"stage": "stem_opt"})
    db.add(check)
    db.commit()
    assert check.id is not None
    assert check.track == "stem_opt"


def test_check_with_documents(db):
    check = CheckRow(track="stem_opt", status="uploaded", answers={})
    db.add(check)
    db.flush()
    doc = DocumentRow(
        check_id=check.id,
        doc_type="i983",
        filename="i983.pdf",
        file_path="/tmp/i983.pdf",
        file_size=1024,
        mime_type="application/pdf",
    )
    db.add(doc)
    db.commit()
    assert len(check.documents) == 1


def test_extracted_fields(db):
    check = CheckRow(track="stem_opt", status="extracted", answers={})
    db.add(check)
    db.flush()
    doc = DocumentRow(
        check_id=check.id,
        doc_type="i983",
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        file_size=100,
        mime_type="application/pdf",
    )
    db.add(doc)
    db.flush()
    field = ExtractedFieldRow(
        document_id=doc.id,
        field_name="job_title",
        field_value="Data Analyst",
        confidence=0.95,
    )
    db.add(field)
    db.commit()
    assert len(doc.extracted_fields) == 1


def test_comparisons_and_findings(db):
    check = CheckRow(track="stem_opt", status="reviewed", answers={})
    db.add(check)
    db.flush()
    comp = ComparisonRow(
        check_id=check.id,
        field_name="job_title",
        value_a="Data Analyst",
        value_b="Business Ops",
        match_type="fuzzy",
        status="mismatch",
        confidence=0.3,
    )
    db.add(comp)
    db.flush()
    finding = FindingRow(
        check_id=check.id,
        rule_id="job_title_mismatch",
        rule_version="1.0.0",
        severity="warning",
        category="comparison",
        title="Job title mismatch",
        action="File amended I-983",
        consequence="RFE trigger",
        immigration_impact=True,
        source_comparison_id=comp.id,
    )
    db.add(finding)
    db.commit()
    assert len(check.comparisons) == 1
    assert len(check.findings) == 1


def test_followups(db):
    check = CheckRow(track="stem_opt", status="reviewed", answers={})
    db.add(check)
    db.flush()
    followup = FollowupRow(
        check_id=check.id,
        question_key="job_title_mismatch",
        question_text="Which title is correct?",
        chips=["Data Analyst", "Business Ops", "Other"],
    )
    db.add(followup)
    db.commit()
    assert len(check.followups) == 1
    assert followup.chips == ["Data Analyst", "Business Ops", "Other"]
