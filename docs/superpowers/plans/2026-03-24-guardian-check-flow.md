# Guardian Check Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the end-to-end "Find my risks" flow for Track A (STEM OPT) — from landing page through document upload, extraction, comparison, follow-up questions, to the final case snapshot with findings.

**Architecture:** Replace the existing 14-step wizard with a 5-screen linear flow. New backend: YAML rule engine + LLM extraction service + comparison engine. New frontend: single-page review flow with inline progression. Existing database tables are replaced with new schema.

**Tech Stack:** Next.js 14 + Tailwind (frontend), FastAPI + SQLAlchemy + SQLite (backend), OpenAI structured output (extraction), PyMuPDF (PDF text), PyYAML (rule configs)

**Spec:** `docs/superpowers/specs/2026-03-24-document-cross-checker-design.md`

---

## File Structure

### Backend — New Files

| File | Responsibility |
|---|---|
| `compliance_os/web/models/tables_v2.py` | New SQLAlchemy tables: checks, documents, extracted_fields, comparisons, followups, findings |
| `compliance_os/web/models/schemas_v2.py` | New Pydantic schemas for all API request/response models |
| `compliance_os/web/routers/checks.py` | Check session CRUD + answers |
| `compliance_os/web/routers/extraction.py` | Document upload, LLM extraction, extraction results |
| `compliance_os/web/routers/review.py` | Compare, evaluate, followups, snapshot endpoints |
| `compliance_os/web/services/extractor.py` | LLM extraction service — PDF text → OpenAI structured output → extracted fields |
| `compliance_os/web/services/comparator.py` | Field comparison engine — exact, fuzzy, numeric, semantic |
| `compliance_os/web/services/rule_engine.py` | YAML rule loader + evaluator |
| `compliance_os/web/services/followup_gen.py` | Follow-up question generator (rules → LLM phrasing) |
| `config/rules/stem_opt.yaml` | Track A comparison + logic + advisory rules |
| `config/rules/entity.yaml` | Track B rules (built in later task) |

### Backend — Modified Files

| File | Change |
|---|---|
| `compliance_os/web/app.py` | Mount new routers, keep old ones for now |
| `compliance_os/web/models/database.py` | Create new tables on startup |
| `pyproject.toml` | Add `pyyaml` and `rapidfuzz` dependencies |

### Frontend — New Files

| File | Responsibility |
|---|---|
| `frontend/src/app/page.tsx` | Replace: Guardian landing page with track selector |
| `frontend/src/app/check/stem-opt/page.tsx` | Screen A1: stage select + years in US |
| `frontend/src/app/check/stem-opt/upload/page.tsx` | Screen A2: upload I-983 + employment letter |
| `frontend/src/app/check/stem-opt/review/page.tsx` | Screens A3-A5: extraction → follow-up → snapshot (single page, inline progression) |
| `frontend/src/lib/api-v2.ts` | New API client for check flow endpoints |
| `frontend/src/components/check/StageSelect.tsx` | Stage + years chip selector |
| `frontend/src/components/check/DocUpload.tsx` | Labeled dual upload zone |
| `frontend/src/components/check/ExtractionGrid.tsx` | Side-by-side field comparison table |
| `frontend/src/components/check/FollowupPanel.tsx` | Chip-based follow-up questions |
| `frontend/src/components/check/CaseSnapshot.tsx` | Timeline + findings + advisories |
| `frontend/src/components/check/Timeline.tsx` | Visual timeline component |

### Frontend — Removed (replaced by new pages)

The old wizard, chat, upload components remain in the codebase but are no longer routed to. The old `/case/*` routes are left untouched — they still work via old API endpoints.

### Test Files

| File | Tests for |
|---|---|
| `tests/test_rule_engine.py` | Rule loading, condition evaluation, finding generation |
| `tests/test_comparator.py` | Exact, fuzzy, numeric comparison logic |
| `tests/test_extractor.py` | Extraction prompt building, response parsing (mocked OpenAI) |
| `tests/test_checks_router.py` | Check CRUD API endpoints |
| `tests/test_extraction_router.py` | Upload + extraction API endpoints |
| `tests/test_review_router.py` | Compare + evaluate + followup API endpoints |

---

## Task 1: Database Schema + Pydantic Models

**Files:**
- Create: `compliance_os/web/models/tables_v2.py`
- Create: `compliance_os/web/models/schemas_v2.py`
- Modify: `compliance_os/web/models/database.py`
- Test: `tests/test_database_v2.py`

- [ ] **Step 1: Write failing test for new tables**

```python
# tests/test_database_v2.py
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from compliance_os.web.models.tables_v2 import Base, CheckRow, DocumentRow, ExtractedFieldRow, ComparisonRow, FollowupRow, FindingRow

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
    doc = DocumentRow(check_id=check.id, doc_type="i983", filename="i983.pdf", file_path="/tmp/i983.pdf", file_size=1024, mime_type="application/pdf")
    db.add(doc)
    db.commit()
    assert len(check.documents) == 1

def test_extracted_fields(db):
    check = CheckRow(track="stem_opt", status="extracted", answers={})
    db.add(check)
    db.flush()
    doc = DocumentRow(check_id=check.id, doc_type="i983", filename="test.pdf", file_path="/tmp/test.pdf", file_size=100, mime_type="application/pdf")
    db.add(doc)
    db.flush()
    field = ExtractedFieldRow(document_id=doc.id, field_name="job_title", field_value="Data Analyst", confidence=0.95)
    db.add(field)
    db.commit()
    assert len(doc.extracted_fields) == 1

def test_comparisons_and_findings(db):
    check = CheckRow(track="stem_opt", status="reviewed", answers={})
    db.add(check)
    db.flush()
    comp = ComparisonRow(check_id=check.id, field_name="job_title", value_a="Data Analyst", value_b="Business Ops", match_type="fuzzy", status="mismatch", confidence=0.3)
    db.add(comp)
    db.flush()
    finding = FindingRow(check_id=check.id, rule_id="job_title_mismatch", rule_version="1.0.0", severity="warning", category="comparison", title="Job title mismatch", action="File amended I-983", consequence="RFE trigger", immigration_impact=True, source_comparison_id=comp.id)
    db.add(finding)
    db.commit()
    assert len(check.comparisons) == 1
    assert len(check.findings) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_database_v2.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.web.models.tables_v2'`

- [ ] **Step 3: Implement tables_v2.py**

```python
# compliance_os/web/models/tables_v2.py
"""Database tables for the Guardian check flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CheckRow(Base):
    __tablename__ = "checks"

    id = Column(String, primary_key=True, default=_uuid)
    track = Column(String, nullable=False)          # 'stem_opt' | 'entity'
    stage = Column(String, nullable=True)
    status = Column(String, default="intake")        # intake | uploaded | extracted | reviewed | saved
    answers = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    documents = relationship("DocumentRow", back_populates="check", cascade="all, delete-orphan")
    comparisons = relationship("ComparisonRow", back_populates="check", cascade="all, delete-orphan")
    followups = relationship("FollowupRow", back_populates="check", cascade="all, delete-orphan")
    findings = relationship("FindingRow", back_populates="check", cascade="all, delete-orphan")


class DocumentRow(Base):
    __tablename__ = "documents_v2"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    doc_type = Column(String, nullable=False)        # i983 | employment_letter | tax_return
    filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    uploaded_at = Column(DateTime, default=_now)

    check = relationship("CheckRow", back_populates="documents")
    extracted_fields = relationship("ExtractedFieldRow", back_populates="document", cascade="all, delete-orphan")


class ExtractedFieldRow(Base):
    __tablename__ = "extracted_fields"

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents_v2.id"), nullable=False)
    field_name = Column(String, nullable=False)
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    raw_text = Column(Text, nullable=True)

    document = relationship("DocumentRow", back_populates="extracted_fields")


class ComparisonRow(Base):
    __tablename__ = "comparisons"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    field_name = Column(String, nullable=False)
    value_a = Column(Text, nullable=True)
    value_b = Column(Text, nullable=True)
    match_type = Column(String)                      # exact | fuzzy | numeric | semantic
    status = Column(String)                          # match | mismatch | needs_review
    confidence = Column(Float, nullable=True)
    detail = Column(Text, nullable=True)

    check = relationship("CheckRow", back_populates="comparisons")


class FollowupRow(Base):
    __tablename__ = "followups"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    question_key = Column(String, nullable=False)
    question_text = Column(Text, nullable=True)
    chips = Column(JSON, nullable=True)
    answer = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)

    check = relationship("CheckRow", back_populates="followups")


class FindingRow(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    rule_version = Column(String, nullable=True)
    severity = Column(String)                        # critical | warning | info
    category = Column(String)                        # comparison | logic | advisory
    title = Column(Text)
    action = Column(Text)
    consequence = Column(String)
    immigration_impact = Column(Boolean, default=False)
    source_comparison_id = Column(String, ForeignKey("comparisons.id"), nullable=True)

    check = relationship("CheckRow", back_populates="findings")
```

- [ ] **Step 4: Implement schemas_v2.py**

```python
# compliance_os/web/models/schemas_v2.py
"""Pydantic schemas for the Guardian check flow API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CheckCreate(BaseModel):
    track: str  # 'stem_opt' | 'entity'
    answers: dict[str, Any] = {}


class CheckUpdate(BaseModel):
    answers: dict[str, Any] | None = None
    status: str | None = None


class Check(BaseModel):
    id: str
    track: str
    stage: str | None
    status: str
    answers: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: str
    check_id: str
    doc_type: str
    filename: str
    file_size: int
    mime_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ExtractedField(BaseModel):
    id: str
    document_id: str
    field_name: str
    field_value: str | None
    confidence: float | None

    class Config:
        from_attributes = True


class Comparison(BaseModel):
    id: str
    check_id: str
    field_name: str
    value_a: str | None
    value_b: str | None
    match_type: str
    status: str
    confidence: float | None
    detail: str | None

    class Config:
        from_attributes = True


class Followup(BaseModel):
    id: str
    check_id: str
    question_key: str
    question_text: str | None
    chips: list[str] | None
    answer: str | None
    answered_at: datetime | None

    class Config:
        from_attributes = True


class FollowupAnswer(BaseModel):
    answer: str


class Finding(BaseModel):
    id: str
    check_id: str
    rule_id: str
    severity: str
    category: str
    title: str
    action: str
    consequence: str
    immigration_impact: bool

    class Config:
        from_attributes = True


class Snapshot(BaseModel):
    check: Check
    extractions: dict[str, list[ExtractedField]]  # keyed by doc_type
    comparisons: list[Comparison]
    findings: list[Finding]
    followups: list[Followup]
    advisories: list[Finding]  # findings where category == 'advisory'
```

- [ ] **Step 5: Update database.py to create new tables**

In `compliance_os/web/models/database.py`, add after existing table creation:

```python
from compliance_os.web.models.tables_v2 import Base as BaseV2

# In get_engine() or lifespan:
BaseV2.metadata.create_all(engine)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_database_v2.py -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add compliance_os/web/models/tables_v2.py compliance_os/web/models/schemas_v2.py compliance_os/web/models/database.py tests/test_database_v2.py
git commit -m "feat: add Guardian check flow database schema and Pydantic models"
```

---

## Task 2: Rule Engine

**Files:**
- Create: `compliance_os/web/services/rule_engine.py`
- Create: `config/rules/stem_opt.yaml`
- Test: `tests/test_rule_engine.py`

- [ ] **Step 1: Write failing tests for rule engine**

```python
# tests/test_rule_engine.py
import pytest
from compliance_os.web.services.rule_engine import RuleEngine, EvaluationContext

@pytest.fixture
def engine():
    return RuleEngine.from_yaml("config/rules/stem_opt.yaml")

def test_load_rules(engine):
    assert len(engine.rules) > 0
    rule_ids = [r.id for r in engine.rules]
    assert "job_title_mismatch" in rule_ids
    assert "advisory_fbar" in rule_ids

def test_comparison_rule_fires_on_mismatch(engine):
    ctx = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={},
        extraction_b={},
        comparisons={"job_title": {"status": "mismatch", "confidence": 0.3}},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "job_title_mismatch" in rule_ids

def test_comparison_rule_does_not_fire_on_match(engine):
    ctx = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={},
        extraction_b={},
        comparisons={"job_title": {"status": "match", "confidence": 0.95}},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "job_title_mismatch" not in rule_ids

def test_advisory_gated_on_years(engine):
    ctx_short = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    ctx_long = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 7},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    short_ids = [f.rule_id for f in engine.evaluate(ctx_short)]
    long_ids = [f.rule_id for f in engine.evaluate(ctx_long)]
    assert "advisory_fbar" not in short_ids
    assert "advisory_fbar" in long_ids

def test_logic_rule_grace_period(engine):
    ctx = EvaluationContext(
        answers={"stage": "opt", "years_in_us": 2},
        extraction_a={"end_date": "2025-12-01"},  # in the past
        extraction_b={},
        comparisons={},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "grace_period_employment" in rule_ids

def test_findings_sorted_by_severity(engine):
    ctx = EvaluationContext(
        answers={"stage": "opt", "years_in_us": 7},
        extraction_a={"end_date": "2025-12-01"},
        extraction_b={},
        comparisons={"job_title": {"status": "mismatch", "confidence": 0.3}},
    )
    findings = engine.evaluate(ctx)
    severities = [f.severity for f in findings]
    # critical before warning before info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    for i in range(len(severities) - 1):
        assert severity_order[severities[i]] <= severity_order[severities[i + 1]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_rule_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create stem_opt.yaml rule config**

Copy the complete YAML rules from the spec document (lines 244-433) into `config/rules/stem_opt.yaml`. Add a `version: "1.0.0"` header. The file should contain all comparison rules, logic rules, and advisory rules for Track A.

- [ ] **Step 4: Implement rule_engine.py**

```python
# compliance_os/web/services/rule_engine.py
"""Deterministic YAML-based compliance rule engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FindingResult:
    rule_id: str
    severity: str        # critical | warning | info
    category: str        # comparison | logic | advisory
    title: str
    action: str
    consequence: str
    immigration_impact: bool


@dataclass
class EvaluationContext:
    answers: dict[str, Any]
    extraction_a: dict[str, Any]
    extraction_b: dict[str, Any]
    comparisons: dict[str, dict[str, Any]]
    today: date = field(default_factory=date.today)


@dataclass
class Condition:
    field: str
    operator: str
    value: Any
    source: str

    def evaluate(self, ctx: EvaluationContext) -> bool:
        actual = self._resolve(ctx)
        if self.operator == "mismatch":
            if actual is None:
                return False
            return actual.get("status") in ("mismatch", "needs_review")
        if self.operator == "missing":
            return actual is None or actual == ""
        if self.operator == "eq":
            return actual == self.value
        if self.operator == "neq":
            return actual != self.value
        if self.operator == "gt":
            return self._compare_gt(actual)
        if self.operator == "lt":
            return self._compare_lt(actual)
        if self.operator == "in":
            return actual in self.value
        if self.operator == "contains":
            return isinstance(actual, list) and self.value in actual
        return False

    def _resolve(self, ctx: EvaluationContext) -> Any:
        if self.source == "answers":
            return ctx.answers.get(self.field)
        if self.source == "extraction_a":
            return ctx.extraction_a.get(self.field)
        if self.source == "extraction_b":
            return ctx.extraction_b.get(self.field)
        if self.source == "comparison":
            return ctx.comparisons.get(self.field)
        return None

    def _resolve_date_value(self) -> date:
        if self.value == "today":
            return date.today()
        if isinstance(self.value, str) and self.value.endswith("_months_ago"):
            n = int(self.value.split("_")[0])
            return date.today() - relativedelta(months=n)
        if isinstance(self.value, str) and self.value.endswith("_days_from_now"):
            n = int(self.value.split("_")[0])
            return date.today() + relativedelta(days=n)
        return date.today()

    def _parse_date(self, val: Any) -> date | None:
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            try:
                return datetime.strptime(val, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def _compare_gt(self, actual: Any) -> bool:
        if isinstance(self.value, (int, float)) and isinstance(actual, (int, float)):
            return actual > self.value
        # Date comparison
        parsed = self._parse_date(actual)
        if parsed:
            return parsed > self._resolve_date_value()
        # Numeric for semantic scores
        if isinstance(actual, (int, float)):
            return actual > self.value
        return False

    def _compare_lt(self, actual: Any) -> bool:
        if isinstance(self.value, (int, float)) and isinstance(actual, (int, float)):
            return actual < self.value
        parsed = self._parse_date(actual)
        if parsed:
            return parsed < self._resolve_date_value()
        if isinstance(actual, (int, float)):
            return actual < self.value
        return False


@dataclass
class Rule:
    id: str
    track: str
    type: str            # comparison | logic | advisory
    conditions: list[Condition]
    severity: str
    finding: dict[str, Any]


class RuleEngine:
    def __init__(self, rules: list[Rule], version: str = "0.0.0"):
        self.rules = rules
        self.version = version

    @classmethod
    def from_yaml(cls, path: str | Path) -> RuleEngine:
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        version = data.get("version", "0.0.0")
        rules = []
        for r in data.get("rules", []):
            conditions = [
                Condition(
                    field=c["field"],
                    operator=c["operator"],
                    value=c.get("value"),
                    source=c["source"],
                )
                for c in r.get("conditions", [])
            ]
            rules.append(Rule(
                id=r["id"],
                track=r["track"],
                type=r["type"],
                conditions=conditions,
                severity=r["severity"],
                finding=r["finding"],
            ))
        return cls(rules, version)

    def evaluate(self, ctx: EvaluationContext) -> list[FindingResult]:
        findings = []
        for rule in self.rules:
            if all(c.evaluate(ctx) for c in rule.conditions):
                findings.append(FindingResult(
                    rule_id=rule.id,
                    severity=rule.severity,
                    category=rule.type,
                    title=rule.finding["title"],
                    action=rule.finding["action"],
                    consequence=rule.finding["consequence"],
                    immigration_impact=rule.finding.get("immigration_impact", False),
                ))
        # Sort: critical > warning > info
        order = {"critical": 0, "warning": 1, "info": 2}
        findings.sort(key=lambda f: order.get(f.severity, 9))
        return findings
```

- [ ] **Step 5: Install dependencies**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pip install pyyaml python-dateutil rapidfuzz`

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_rule_engine.py -v`
Expected: All 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add compliance_os/web/services/rule_engine.py config/rules/stem_opt.yaml tests/test_rule_engine.py
git commit -m "feat: add YAML-based compliance rule engine with Track A rules"
```

---

## Task 3: Comparison Engine

**Files:**
- Create: `compliance_os/web/services/comparator.py`
- Test: `tests/test_comparator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_comparator.py
import pytest
from compliance_os.web.services.comparator import compare_fields, ComparisonResult

def test_exact_match():
    result = compare_fields("employer_name", "Acme Corp", "Acme Corp", "exact")
    assert result.status == "match"
    assert result.confidence > 0.9

def test_exact_mismatch_case_insensitive():
    result = compare_fields("employer_name", "Acme Corp", "acme corp", "exact")
    assert result.status == "match"

def test_exact_mismatch():
    result = compare_fields("employer_name", "Acme Corp", "Beta LLC", "exact")
    assert result.status == "mismatch"

def test_fuzzy_match():
    result = compare_fields("job_title", "Senior Data Analyst", "Sr. Data Analyst", "fuzzy")
    assert result.status == "match"

def test_fuzzy_mismatch():
    result = compare_fields("job_title", "Data Analyst", "Marketing Manager", "fuzzy")
    assert result.status == "mismatch"

def test_numeric_match():
    result = compare_fields("compensation", "85000", "85000", "numeric")
    assert result.status == "match"

def test_numeric_match_within_tolerance():
    result = compare_fields("compensation", "85000", "85200", "numeric")
    assert result.status == "match"  # within 2%

def test_numeric_mismatch():
    result = compare_fields("compensation", "85000", "52000", "numeric")
    assert result.status == "mismatch"

def test_missing_value():
    result = compare_fields("job_title", "Data Analyst", None, "fuzzy")
    assert result.status == "needs_review"

def test_both_missing():
    result = compare_fields("job_title", None, None, "fuzzy")
    assert result.status == "needs_review"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_comparator.py -v`
Expected: FAIL

- [ ] **Step 3: Implement comparator.py**

```python
# compliance_os/web/services/comparator.py
"""Field comparison engine — exact, fuzzy, numeric, semantic."""
from __future__ import annotations

from dataclasses import dataclass
from rapidfuzz import fuzz


@dataclass
class ComparisonResult:
    field_name: str
    value_a: str | None
    value_b: str | None
    match_type: str
    status: str        # match | mismatch | needs_review
    confidence: float
    detail: str | None = None


def compare_fields(
    field_name: str,
    value_a: str | None,
    value_b: str | None,
    match_type: str,
) -> ComparisonResult:
    if value_a is None or value_b is None:
        return ComparisonResult(field_name, value_a, value_b, match_type, "needs_review", 0.0, "One or both values missing")

    a = str(value_a).strip()
    b = str(value_b).strip()

    if match_type == "exact":
        return _exact(field_name, a, b)
    if match_type == "fuzzy":
        return _fuzzy(field_name, a, b)
    if match_type == "numeric":
        return _numeric(field_name, a, b)
    # semantic handled separately via LLM
    return ComparisonResult(field_name, a, b, match_type, "needs_review", 0.0, f"Unknown match type: {match_type}")


def _exact(name: str, a: str, b: str) -> ComparisonResult:
    match = a.lower() == b.lower()
    return ComparisonResult(name, a, b, "exact", "match" if match else "mismatch", 1.0 if match else 0.0)


def _fuzzy(name: str, a: str, b: str) -> ComparisonResult:
    ratio = fuzz.token_sort_ratio(a.lower(), b.lower()) / 100.0
    status = "match" if ratio >= 0.85 else "mismatch"
    return ComparisonResult(name, a, b, "fuzzy", status, ratio)


def _numeric(name: str, a: str, b: str) -> ComparisonResult:
    try:
        va = float(a.replace(",", "").replace("$", ""))
        vb = float(b.replace(",", "").replace("$", ""))
    except ValueError:
        return ComparisonResult(name, a, b, "numeric", "needs_review", 0.0, "Could not parse numbers")

    if va == 0 and vb == 0:
        return ComparisonResult(name, a, b, "numeric", "match", 1.0)
    max_val = max(abs(va), abs(vb))
    diff_pct = abs(va - vb) / max_val if max_val > 0 else 0
    within_tolerance = diff_pct <= 0.02 or abs(va - vb) <= 500
    confidence = 1.0 - diff_pct
    return ComparisonResult(name, a, b, "numeric", "match" if within_tolerance else "mismatch", max(confidence, 0.0))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_comparator.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add compliance_os/web/services/comparator.py tests/test_comparator.py
git commit -m "feat: add field comparison engine (exact, fuzzy, numeric)"
```

---

## Task 4: LLM Extraction Service

**Files:**
- Create: `compliance_os/web/services/extractor.py`
- Test: `tests/test_extractor.py`

- [ ] **Step 1: Write failing tests (mocked OpenAI)**

```python
# tests/test_extractor.py
import pytest
from unittest.mock import patch, MagicMock
from compliance_os.web.services.extractor import extract_document, SCHEMAS

def test_schemas_defined():
    assert "i983" in SCHEMAS
    assert "employment_letter" in SCHEMAS
    assert "tax_return" in SCHEMAS
    assert "job_title" in SCHEMAS["i983"]
    assert "employer_name" in SCHEMAS["employment_letter"]

def test_extract_returns_fields():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"job_title": "Data Analyst", "employer_name": "Acme Corp", "start_date": "2025-07-01", "compensation": 85000}'

    with patch("compliance_os.web.services.extractor._call_openai", return_value=mock_response):
        fields = extract_document("i983", "Sample PDF text with job title Data Analyst at Acme Corp starting July 1 2025 salary $85,000")
        assert fields["job_title"]["value"] == "Data Analyst"
        assert fields["employer_name"]["value"] == "Acme Corp"
        assert fields["job_title"]["confidence"] >= 0.7

def test_extract_handles_missing_fields():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"job_title": "Data Analyst"}'

    with patch("compliance_os.web.services.extractor._call_openai", return_value=mock_response):
        fields = extract_document("i983", "Minimal text")
        assert fields["job_title"]["value"] == "Data Analyst"
        # Fields not in response should have null value
        assert fields.get("employer_name", {}).get("value") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_extractor.py -v`
Expected: FAIL

- [ ] **Step 3: Implement extractor.py**

Build the extraction service with:
- `SCHEMAS` dict defining expected fields per doc type (from spec lines 688-744)
- `extract_document(doc_type, text)` that builds a prompt with the schema, calls OpenAI structured output, and returns `{field_name: {"value": ..., "confidence": ...}}`
- `_call_openai(prompt, schema)` wrapper for the API call
- PDF text extraction using PyMuPDF (`_extract_pdf_text(file_path)`)

The prompt template should include field descriptions and expected formats. Use OpenAI's JSON mode / structured output for reliable parsing.

- [ ] **Step 4: Run tests**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_extractor.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add compliance_os/web/services/extractor.py tests/test_extractor.py
git commit -m "feat: add LLM extraction service with OpenAI structured output"
```

---

## Task 5: Backend API Routes (Checks + Extraction + Review)

**Files:**
- Create: `compliance_os/web/routers/checks.py`
- Create: `compliance_os/web/routers/extraction.py`
- Create: `compliance_os/web/routers/review.py`
- Modify: `compliance_os/web/app.py`
- Test: `tests/test_checks_router_v2.py`

- [ ] **Step 1: Write failing API tests**

Test the core endpoints:
- `POST /api/checks` — create check
- `GET /api/checks/{id}` — get check
- `PATCH /api/checks/{id}` — update answers
- `POST /api/checks/{id}/documents` — upload document
- `POST /api/checks/{id}/extract` — trigger extraction
- `POST /api/checks/{id}/compare` — trigger comparison
- `POST /api/checks/{id}/evaluate` — trigger rule evaluation
- `GET /api/checks/{id}/findings` — get findings

Use `TestClient` from FastAPI. Mock the OpenAI calls in extraction.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement checks.py router**

Endpoints: `POST /api/checks`, `GET /api/checks/{id}`, `PATCH /api/checks/{id}`

- [ ] **Step 4: Implement extraction.py router**

Endpoints: `POST /api/checks/{id}/documents`, `GET /api/checks/{id}/documents`, `POST /api/checks/{id}/extract`, `GET /api/checks/{id}/extractions`

The extract endpoint: reads uploaded PDF → extracts text → calls extractor service → stores ExtractedFieldRow records.

- [ ] **Step 5: Implement review.py router**

Endpoints: `POST /api/checks/{id}/compare`, `GET /api/checks/{id}/comparisons`, `POST /api/checks/{id}/evaluate`, `GET /api/checks/{id}/findings`, `POST /api/checks/{id}/followups`, `PATCH /api/checks/{id}/followups/{fid}`, `GET /api/checks/{id}/followups`

The compare endpoint: reads extracted fields from both documents → applies field mapping → runs comparator → stores ComparisonRow records.

The evaluate endpoint: loads rule engine → builds EvaluationContext from answers + extractions + comparisons → evaluates → stores FindingRow records.

- [ ] **Step 6: Mount routers in app.py**

```python
from compliance_os.web.routers import checks as checks_v2, extraction, review
app.include_router(checks_v2.router)
app.include_router(extraction.router)
app.include_router(review.router)
```

- [ ] **Step 7: Run tests**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/test_checks_router_v2.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add compliance_os/web/routers/checks.py compliance_os/web/routers/extraction.py compliance_os/web/routers/review.py compliance_os/web/app.py tests/test_checks_router_v2.py
git commit -m "feat: add Guardian check flow API routes"
```

---

## Task 6: Frontend — Landing Page + Stage Select + Upload

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/check/stem-opt/page.tsx`
- Create: `frontend/src/app/check/stem-opt/upload/page.tsx`
- Create: `frontend/src/lib/api-v2.ts`
- Create: `frontend/src/components/check/StageSelect.tsx`
- Create: `frontend/src/components/check/DocUpload.tsx`

- [ ] **Step 1: Create api-v2.ts**

New API client with functions: `createCheck`, `getCheck`, `updateCheck`, `uploadDocument`, `getDocuments`, `triggerExtraction`, `getExtractions`, `triggerCompare`, `getComparisons`, `triggerEvaluate`, `getFindings`, `getFollowups`, `answerFollowup`

- [ ] **Step 2: Replace landing page (page.tsx)**

Replace the old case-list landing page with the Guardian design: headline, subtitle, two track cards ("I'm on OPT / STEM OPT" and "I own a US business"), "Find my risks" CTA. Use the same blue palette from the mockup. Include the form cloud section.

- [ ] **Step 3: Create StageSelect component**

Chip selector for stage (5 options) + number input for years in US. Calls `createCheck({ track: "stem_opt", answers: { stage, years_in_us } })` on continue.

- [ ] **Step 4: Create stem-opt/page.tsx**

Page that renders StageSelect. On submit, creates the check and navigates to `/check/stem-opt/upload?id={checkId}`.

- [ ] **Step 5: Create DocUpload component**

Two labeled drop zones: "Form I-983" and "Employment Letter". Each accepts PDF. On upload, calls `uploadDocument(checkId, file, docType)`. Shows upload progress and filename after upload. "Continue" button enabled when both documents are uploaded.

- [ ] **Step 6: Create stem-opt/upload/page.tsx**

Page that reads `checkId` from query params, renders DocUpload. On continue, navigates to `/check/stem-opt/review?id={checkId}`.

- [ ] **Step 7: Build and test**

Run: `cd /Users/lichenyu/compliance-os/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat: add Guardian landing page, stage select, and document upload screens"
```

---

## Task 7: Frontend — Review Flow (Extraction → Follow-up → Snapshot)

**Files:**
- Create: `frontend/src/app/check/stem-opt/review/page.tsx`
- Create: `frontend/src/components/check/ExtractionGrid.tsx`
- Create: `frontend/src/components/check/FollowupPanel.tsx`
- Create: `frontend/src/components/check/CaseSnapshot.tsx`
- Create: `frontend/src/components/check/Timeline.tsx`

- [ ] **Step 1: Create ExtractionGrid component**

Side-by-side comparison table. Columns: Field | I-983 | Employment Letter | Status. Each row shows extracted values and match/mismatch/needs_review indicator. Mismatch rows highlighted in amber. Missing fields show "Could not extract" in gray.

- [ ] **Step 2: Create FollowupPanel component**

List of chip-based questions. Each question has: the mismatch description, why it matters (one sentence), and 2-4 chip options. User clicks a chip to answer. Answered questions show the selected chip highlighted.

- [ ] **Step 3: Create Timeline component**

Vertical timeline with date markers. Shows: STEM OPT start, today marker, upcoming dates (12-month eval, STEM end, grace period end). Risk markers in red/amber at relevant points.

- [ ] **Step 4: Create CaseSnapshot component**

Combines Timeline + findings list + advisory one-liners. Findings split into "Needs attention" (critical/warning) and "Looks good" (matches). Advisories section: "Also worth checking" with one-liners.

- [ ] **Step 5: Create review/page.tsx**

Single-page flow with 3 phases:
1. **Extracting** — calls `triggerExtraction`, shows progress, then shows ExtractionGrid
2. **Follow-up** — if mismatches found, shows FollowupPanel, then re-evaluates
3. **Snapshot** — calls `triggerEvaluate`, shows CaseSnapshot

Phase transitions happen inline (no page navigation). Use React state to track current phase.

- [ ] **Step 6: Build and test**

Run: `cd /Users/lichenyu/compliance-os/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 7: Manual E2E test**

Start both servers. Go through the full flow:
1. Landing → click "Find my risks" → track card → stage select
2. Upload two PDFs → continue to review
3. See extraction grid → answer follow-ups → see case snapshot

- [ ] **Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat: add review flow — extraction grid, follow-up panel, case snapshot"
```

---

## Task 8: Integration Test + Polish

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/lichenyu/compliance-os && conda run -n compliance-os pytest tests/ -v`
Expected: All tests pass (old + new)

- [ ] **Step 2: Run frontend build**

Run: `cd /Users/lichenyu/compliance-os/frontend && npm run build`
Expected: Clean build

- [ ] **Step 3: Full E2E walkthrough with real documents**

Use sample documents from `dev_dataset/` if available, or test PDFs.

- [ ] **Step 4: Fix any issues found**

- [ ] **Step 5: Final commit and push**

```bash
git add -A
git commit -m "feat: complete Guardian STEM OPT check flow — end-to-end"
git push origin feat/discovery-dataroom
```
