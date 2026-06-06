# cross_check_filings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local, deterministic `cross_check_filings` MCP tool that reads the on-device facts SoT and reports cross-document fact **mismatches**, **missing-from-chain documents**, and **deadline risks** in one pass — the "find my risks" loop inside Claude Desktop.

**Architecture:** A chain spec (`config/document_chains.yaml`) names, per document chain, the doc types in it, which are required, and the canonical fact keys that must agree across it. A chain-agnostic engine (`compliance_os/compliance/cross_check.py`) reads each document's extracted fields, maps them to canonical keys via the existing `EXTRACTION_TO_FACT_KEY`, and diffs them; it also flags required docs absent from the data room and date facts within a horizon. The MCP tool is a thin local-mode wrapper. No model call, no network.

**Tech Stack:** Python 3.11, SQLAlchemy (SQLite), PyYAML, FastMCP, pytest. No new deps.

**Reference (read before starting):**
- Spec: `docs/superpowers/specs/2026-06-05-cross-check-filings-design.md`
- `compliance_os/facts/extraction_map.py` — `EXTRACTION_TO_FACT_KEY: dict[(doc_type, field_name), fact_key]`, `fact_key_for(doc_type, field_name)`
- `compliance_os/web/models/tables_v2.py` — `CheckRow` (id, user_id), `DocumentRow` (id, check_id, doc_type, is_active, `extracted_fields` relationship), `ExtractedFieldRow` (document_id, field_name, field_value), `UserFactRow`
- `compliance_os/web/services/user_facts.py` — `get_active_facts(db, *, user_id, category=None, track=None)` → rows with `.fact_key`, `.value` (a `{"v": ...}` envelope)
- `compliance_os/local_engine.py` — `is_local_mode()`, `get_local_user_id(db)`, `get_session` (imported), `serialize_fact`
- `compliance_os/mcp_server.py` — tool registration pattern (`@mcp.tool(annotations=ToolAnnotations(...))`), the `is_local_mode()` import

**Verified canonical keys used by the chains (all already exist):** `legal_name`, `sevis_id`, `current_employer_legal_name`, `current_employer_ein`, `current_position_title`, `worksite_address`, `current_annual_salary`, `current_immigration_status`, `ssn_last4`, `entity_legal_name`, `entity_ein`, `entity_hq_address`, and date keys `stem_opt_start_date`, `stem_opt_end_date`, `h1b_classification_start_date`, `h1b_classification_end_date`, `i94_admit_until_date`.

---

## File Structure

- **Create** `config/document_chains.yaml` — the chain spec (stem_opt, h1b, tax, corporate).
- **Create** `compliance_os/compliance/cross_check.py` — loader + engine: `load_chains`, `_contributions`, `_normalize`, `_mismatches`, `_detect_and_missing`, `_deadlines`, `_relationships`, `cross_check`. One responsibility: compute the `RiskReport`.
- **Modify** `compliance_os/local_engine.py` — `local_cross_check(chain="")`.
- **Modify** `compliance_os/mcp_server.py` — register the `cross_check_filings` tool.
- **Create** `tests/test_cross_check.py` — per-category unit tests + an end-to-end "messy data room" fixture.

---

## Task 1: Chain spec config + loader

**Files:**
- Create: `config/document_chains.yaml`
- Create: `compliance_os/compliance/cross_check.py`
- Test: `tests/test_cross_check.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_check.py::test_load_chains_has_v1_chains -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.compliance.cross_check'`.

- [ ] **Step 3: Create the chain spec**

Create `config/document_chains.yaml`:

```yaml
chains:
  stem_opt:
    name: "STEM OPT"
    detect_when_any: [i20, ead, i983]
    documents:
      - {doc_type: i20, required: true, label: "Form I-20 (STEM)"}
      - {doc_type: ead, required: true, label: "EAD / I-766"}
      - {doc_type: i983, required: true, label: "I-983 Training Plan"}
      - {doc_type: employment_letter, required: true, label: "Employment/offer letter"}
      - {doc_type: i94, required: false, label: "I-94"}
      - {doc_type: passport, required: false, label: "Passport"}
    must_agree: [legal_name, sevis_id, current_employer_legal_name, current_employer_ein, current_position_title, worksite_address, current_annual_salary]
    relationships: []
    deadlines: [stem_opt_end_date]

  h1b:
    name: "H-1B"
    detect_when_any: [i797]
    documents:
      - {doc_type: i797, required: true, label: "I-797 Approval"}
      - {doc_type: employment_letter, required: false, label: "Offer/support letter"}
      - {doc_type: passport, required: false, label: "Passport"}
    must_agree: [legal_name, current_employer_legal_name, current_immigration_status]
    relationships:
      - {id: h1b_after_opt, op: date_order, before: stem_opt_end_date, after: h1b_classification_start_date, message: "H-1B start should not precede the STEM OPT end (cap-gap aside)."}
    deadlines: [h1b_classification_end_date, i94_admit_until_date]

  tax:
    name: "Federal + State Tax"
    detect_when_any: [w2, "1040_nr", form_8843, fbar]
    documents:
      - {doc_type: "1040_nr", required: false, label: "Form 1040-NR"}
      - {doc_type: w2, required: false, label: "W-2"}
      - {doc_type: form_8843, required: false, label: "Form 8843"}
      - {doc_type: fbar, required: false, label: "FBAR / FinCEN 114"}
    must_agree: [legal_name, ssn_last4, current_employer_legal_name, current_employer_ein]
    relationships: []
    deadlines: []

  corporate:
    name: "Corporate / Governance"
    detect_when_any: [articles, ein_letter, form_5472]
    documents:
      - {doc_type: articles, required: false, label: "Articles of Incorporation"}
      - {doc_type: ein_letter, required: false, label: "EIN / CP575"}
      - {doc_type: form_5472, required: false, label: "Form 5472"}
    must_agree: [entity_legal_name, entity_ein, entity_hq_address]
    relationships: []
    deadlines: []
```

Create `compliance_os/compliance/cross_check.py`:

```python
"""Chain-aware local compliance cross-check.

Reads the on-device facts SoT + each document's extracted fields and reports
cross-document fact mismatches, missing-from-chain documents, and deadline
risks. Deterministic and local — no model call, no network. Chain knowledge
lives in config/document_chains.yaml; this module is chain-agnostic.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG = Path(__file__).resolve().parents[2] / "config" / "document_chains.yaml"


@lru_cache(maxsize=1)
def load_chains() -> dict:
    """Load the chain spec. Cached; call load_chains.cache_clear() in tests
    that write a custom config."""
    with open(_CONFIG) as f:
        return (yaml.safe_load(f) or {}).get("chains", {})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cross_check.py::test_load_chains_has_v1_chains -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/document_chains.yaml compliance_os/compliance/cross_check.py tests/test_cross_check.py
git commit -m "feat(cross-check): chain spec config + loader"
```

---

## Task 2: Per-document fact contributions

**Files:**
- Modify: `compliance_os/compliance/cross_check.py`
- Test: `tests/test_cross_check.py`

- [ ] **Step 1: Write the failing test (with a seeding helper)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_check.py::test_contributions_maps_fields_to_canonical_keys -v`
Expected: FAIL — `AttributeError: module 'compliance_os.compliance.cross_check' has no attribute '_contributions'`.

- [ ] **Step 3: Add `_contributions`**

Append to `cross_check.py`:

```python
def _contributions(db, user_id: str) -> dict:
    """Map every active document's extracted fields to canonical fact keys.

    Returns {fact_key: [(doc_type, doc_id, value), ...]} — each document's raw
    contribution to each canonical key (via EXTRACTION_TO_FACT_KEY), preserving
    provenance so mismatches can cite their sources.
    """
    from compliance_os.facts.extraction_map import fact_key_for
    from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow

    docs = (
        db.query(DocumentRow)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user_id, DocumentRow.is_active.is_(True))
        .all()
    )
    out: dict = {}
    for doc in docs:
        for ef in doc.extracted_fields:
            if not ef.field_value:
                continue
            fk = fact_key_for(doc.doc_type, ef.field_name)
            if fk is None:
                continue
            out.setdefault(fk, []).append((doc.doc_type, doc.id, ef.field_value))
    return out


def _present_doc_types(db, user_id: str) -> set:
    from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow

    rows = (
        db.query(DocumentRow.doc_type)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user_id, DocumentRow.is_active.is_(True))
        .all()
    )
    return {r[0] for r in rows}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cross_check.py::test_contributions_maps_fields_to_canonical_keys -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/compliance/cross_check.py tests/test_cross_check.py
git commit -m "feat(cross-check): gather per-document fact contributions"
```

---

## Task 3: Normalization + fact-mismatch detection

**Files:**
- Modify: `compliance_os/compliance/cross_check.py`
- Test: `tests/test_cross_check.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_check.py::test_normalize_examples -v`
Expected: FAIL — `cannot import name '_normalize'`.

- [ ] **Step 3: Add `_normalize` + `_mismatches`**

Append to `cross_check.py`:

```python
import re

_DIGIT_KEYS = {"current_employer_ein", "entity_ein", "ssn_last4", "sevis_id",
               "i94_admission_number", "h1b_receipt_number"}
_MONEY_KEYS = {"current_annual_salary", "foreign_account_aggregate_high"}
_HIGH_SEVERITY = {"legal_name", "sevis_id", "current_employer_ein", "entity_ein",
                  "entity_legal_name", "current_employer_legal_name"}


def _normalize(fact_key: str, value: str) -> str:
    v = (value or "").strip()
    if fact_key in _DIGIT_KEYS:
        return re.sub(r"\D", "", v)
    if fact_key in _MONEY_KEYS:
        digits = re.sub(r"[^\d.]", "", v)
        try:
            return str(int(round(float(digits)))) if digits else ""
        except ValueError:
            return digits
    # names / addresses / titles: case-fold, collapse whitespace, drop common
    # corporate-suffix punctuation so "Acme Inc." == "Acme Inc" but "Acme Inc"
    # != "Acme Incorporated".
    v = re.sub(r"\s+", " ", v).strip().casefold().rstrip(".")
    return v


def _mismatches(keys, contributions) -> list:
    """For each key, if ≥2 distinct normalized values appear across its
    contributing documents, emit a mismatch finding citing every source."""
    findings = []
    for key in keys:
        items = contributions.get(key, [])
        groups: dict = {}
        for doc_type, doc_id, value in items:
            groups.setdefault(_normalize(key, value), []).append(
                {"value": value, "doc": doc_type, "doc_id": doc_id})
        groups.pop("", None)
        if len(groups) >= 2:
            findings.append({
                "category": "mismatch",
                "severity": "high" if key in _HIGH_SEVERITY else "medium",
                "fact": key,
                "values": [g[0] for g in groups.values()],  # one representative per distinct value
                "message": f"'{key}' differs across your documents — these should match.",
                "recommended_action": "Confirm the correct value and fix the document that's wrong.",
            })
    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cross_check.py::test_normalize_examples tests/test_cross_check.py::test_mismatch_flags_employer_name_not_salary_format -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/compliance/cross_check.py tests/test_cross_check.py
git commit -m "feat(cross-check): normalization + fact-mismatch detection"
```

---

## Task 4: Detect chains + missing-from-chain

**Files:**
- Modify: `compliance_os/compliance/cross_check.py`
- Test: `tests/test_cross_check.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_check.py::test_detect_and_missing -v`
Expected: FAIL — `cross_check` has no attribute `_detect_chains`.

- [ ] **Step 3: Add `_detect_chains` + `_missing`**

Append to `cross_check.py`:

```python
def _detect_chains(present_doc_types: set) -> list:
    chains = load_chains()
    return [cid for cid, c in chains.items()
            if any(dt in present_doc_types for dt in c.get("detect_when_any", []))]


def _missing(chain_id: str, present_doc_types: set) -> list:
    chain = load_chains()[chain_id]
    findings = []
    for d in chain.get("documents", []):
        if d.get("required") and d["doc_type"] not in present_doc_types:
            findings.append({
                "category": "missing",
                "severity": "high",
                "chain": chain_id,
                "doc_type": d["doc_type"],
                "label": d.get("label", d["doc_type"]),
                "message": f"{chain['name']}: required document missing — {d.get('label', d['doc_type'])}.",
                "recommended_action": f"Upload your {d.get('label', d['doc_type'])}.",
            })
    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cross_check.py::test_detect_and_missing -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/compliance/cross_check.py tests/test_cross_check.py
git commit -m "feat(cross-check): chain auto-detect + missing-required-doc findings"
```

---

## Task 5: Deadlines + relationship rules

**Files:**
- Modify: `compliance_os/compliance/cross_check.py`
- Test: `tests/test_cross_check.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_check.py::test_deadlines_and_relationship -v`
Expected: FAIL — no `_fact_values` / `_deadlines` / `_relationships`.

- [ ] **Step 3: Add `_fact_values`, `_deadlines`, `_relationships`**

Append to `cross_check.py`:

```python
from datetime import date, datetime


def _fact_values(db, user_id: str) -> dict:
    """Active SoT facts as {fact_key: scalar_value}."""
    from compliance_os.web.services.user_facts import get_active_facts

    out = {}
    for row in get_active_facts(db, user_id=user_id):
        v = row.value
        if isinstance(v, dict) and "v" in v:
            v = v["v"]
        out[row.fact_key] = v
    return out


def _as_date(value):
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (ValueError, TypeError):
        return None


def _deadlines(keys, facts, horizon_days: int = 180) -> list:
    findings = []
    today = date.today()
    for key in keys:
        d = _as_date(facts.get(key))
        if d is None:
            continue
        days = (d - today).days
        if days <= horizon_days:
            findings.append({
                "category": "deadline",
                "severity": "high" if days < 0 else "medium",
                "fact": key,
                "date": d.isoformat(),
                "days_out": days,
                "message": (f"{key} is past ({d.isoformat()})." if days < 0
                            else f"{key} is {days} days away ({d.isoformat()})."),
                "recommended_action": "Review and act before this date.",
            })
    return findings


def _relationships(rules, facts) -> list:
    findings = []
    for r in rules:
        if r.get("op") == "date_order":
            before = _as_date(facts.get(r["before"]))
            after = _as_date(facts.get(r["after"]))
            if before and after and after < before:  # 'after' should be >= 'before'
                findings.append({
                    "category": "mismatch", "severity": "high", "rule": r["id"],
                    "message": r.get("message", f"{r['after']} precedes {r['before']}."),
                    "recommended_action": "Verify these dates against the source documents.",
                })
    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cross_check.py::test_deadlines_and_relationship -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/compliance/cross_check.py tests/test_cross_check.py
git commit -m "feat(cross-check): deadline horizon + date-order relationship rules"
```

---

## Task 6: Assemble `cross_check` + the MCP tool

**Files:**
- Modify: `compliance_os/compliance/cross_check.py`
- Modify: `compliance_os/local_engine.py`
- Modify: `compliance_os/mcp_server.py`
- Test: `tests/test_cross_check.py`

- [ ] **Step 1: Write the failing test (end-to-end)**

```python
def test_cross_check_end_to_end(local_db):
    from compliance_os.compliance import cross_check
    from compliance_os import local_engine

    db = next(local_db.get_session())
    try:
        # messy data room: employer-name mismatch + missing I-983 + (no EAD date)
        uid = _seed(db, [
            ("i20", {"student_name": "Jane Q", "sevis_number": "N0001234567", "employer_name": "Acme Inc"}),
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
    import json
    from compliance_os import local_engine, mcp_server

    db = next(local_db.get_session())
    try:
        _seed(db, [("i20", {"sevis_number": "N1"}), ("ead", {"valid_to": "2099-01-01"})])
    finally:
        db.close()
    out = json.loads(mcp_server.cross_check_filings())
    assert "findings" in out and "chains_detected" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_check.py::test_cross_check_end_to_end -v`
Expected: FAIL — `cross_check` module has no attribute `cross_check`.

- [ ] **Step 3: Add the `cross_check` assembler**

Append to `cross_check.py`:

```python
def cross_check(db, user_id: str, chain: str | None = None) -> dict:
    """Run the full cross-check over the user's data room. If `chain` is given,
    only that chain is considered (and only if its docs are present)."""
    chains = load_chains()
    present = _present_doc_types(db, user_id)
    detected = _detect_chains(present)
    if chain:
        detected = [c for c in detected if c == chain]

    contributions = _contributions(db, user_id)
    facts = _fact_values(db, user_id)

    findings = []
    # Mismatches: union of must_agree keys across detected chains, compared
    # across ALL contributing docs (catches cross-chain name/EIN drift). One
    # finding per key.
    agree_keys = sorted({k for cid in detected for k in chains[cid].get("must_agree", [])})
    findings += _mismatches(agree_keys, contributions)

    seen_dl = set()
    for cid in detected:
        findings += _missing(cid, present)
        findings += _relationships(chains[cid].get("relationships", []), facts)
        dl_keys = [k for k in chains[cid].get("deadlines", []) if k not in seen_dl]
        seen_dl.update(dl_keys)
        findings += _deadlines(dl_keys, facts)

    sev_rank = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: sev_rank.get(f.get("severity"), 9))
    summary = {
        "mismatches": sum(1 for f in findings if f["category"] == "mismatch"),
        "missing": sum(1 for f in findings if f["category"] == "missing"),
        "deadlines": sum(1 for f in findings if f["category"] == "deadline"),
        "high_severity": sum(1 for f in findings if f.get("severity") == "high"),
    }
    return {"chains_detected": detected, "summary": summary, "findings": findings}
```

- [ ] **Step 4: Add the local wrapper + the MCP tool**

In `compliance_os/local_engine.py`, append:

```python
def local_cross_check(chain: str = "") -> dict:
    """Run the chain-aware cross-check over the local data room."""
    from compliance_os.compliance.cross_check import cross_check

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        return cross_check(db, user_id, chain=chain or None)
    finally:
        db.close()
```

In `compliance_os/mcp_server.py`, add the tool (extend the existing `from compliance_os.local_engine import (...)` block with `local_cross_check`):

```python
@mcp.tool(
    annotations=ToolAnnotations(
        title="Cross-check filings",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def cross_check_filings(chain: str = "") -> str:
    """Cross-check the user's uploaded filings for mismatches, missing forms,
    and deadline risks — entirely on-device. With no argument, auto-detects and
    checks every document chain your data room implies (STEM OPT, H-1B, tax,
    corporate); pass a chain id to scope to one. Returns a structured risk
    report to summarize for the user. Runs no model and sends no data off-device.

    Args:
        chain: Optional chain id — "stem_opt", "h1b", "tax", or "corporate".
    """
    if not is_local_mode():
        return json.dumps({"error": "cross_check_filings is available in local mode."})
    return json.dumps(local_cross_check(chain), default=str, indent=2)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_cross_check.py -v`
Expected: PASS (all).

- [ ] **Step 6: Regression sweep**

Run: `pytest tests/ -q`
Expected: only the pre-existing failures (`test_election_83b`, `marketplace`, `auth`, `cases_router`, `database`). Confirm zero failures in the local-first modules:
`pytest tests/ -q 2>&1 | grep -E "FAILED tests/(test_cross_check|test_mcp_server|test_local_engine|test_extraction_rehome|test_license)"` → must be empty.

- [ ] **Step 7: Commit**

```bash
git add compliance_os/compliance/cross_check.py compliance_os/local_engine.py compliance_os/mcp_server.py tests/test_cross_check.py
git commit -m "feat(cross-check): cross_check assembler + cross_check_filings MCP tool"
```

---

## Self-Review Notes

**Spec coverage:**
- Facts-SoT-driven, local-only, no model → Task 6 (`local_cross_check` reads the local DB; tool gated to local mode). ✅
- Chain spec as config, code chain-agnostic → Task 1 (`document_chains.yaml` + loader). ✅
- Fact mismatches (the new core) + normalization → Tasks 2–3. ✅
- Auto-detect chains + missing-from-chain (reusing doc-type/slot semantics) → Task 4. ✅
- Deadlines (SoT date keys) + relationship rules → Task 5. ✅
- Unified `RiskReport` + `cross_check_filings` tool → Task 6. ✅
- **Deferred (per spec):** full rule-engine integration for conditional `rule_checks` (fbar threshold, nra→8843), banking/KYC + DOL-PAF chains, derived deadlines (i983 12-month, 90-day unemployment). v1 surfaces mismatches + missing + extracted-date deadlines, which is the core "find my risks." `relationships`/`deadlines` are config so more are additive.

**Type consistency:** `_contributions → {fact_key: [(doc_type, doc_id, value)]}`; `_mismatches(keys, contributions) → [finding]`; `_normalize(fact_key, value) → str`; `_detect_chains(set) → [chain_id]`; `_missing(chain_id, set) → [finding]`; `_fact_values(db, user_id) → {key: scalar}`; `_deadlines(keys, facts, horizon_days) → [finding]`; `_relationships(rules, facts) → [finding]`; `cross_check(db, user_id, chain=None) → RiskReport`. Finding dicts always carry `category` + `severity`. The MCP tool returns `json.dumps(report)`.

**Known risks during implementation:**
- `DocumentRow.extracted_fields` relationship must be loaded within the open session (it is — same `db`). If lazy-load errors in tests, query `ExtractedFieldRow` by `document_id` explicitly.
- `load_chains` is `lru_cache`d; the v1 tests read the real config (no custom YAML), so no cache_clear needed. If a future test writes a custom config, call `load_chains.cache_clear()`.
- All chain `must_agree`/deadline keys are verified to exist in `EXTRACTION_TO_FACT_KEY`/`CANONICAL_FACTS` — no vocabulary additions required for v1.
- Delivery: like the index/batch local fixes, this reaches the installed extension only via a PyPI release — bundle into the next version bump (2.0.1+).
