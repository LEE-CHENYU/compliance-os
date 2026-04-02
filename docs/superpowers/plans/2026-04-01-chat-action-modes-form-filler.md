# Chat Action Modes + Form Filler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a toggleable mode bar to the dashboard chat panel with "Guardian" (default) and "Form Filler" modes, and implement a full PDF form-filling flow that extracts AcroForm fields, proposes values from RAG context, previews for editing, and generates a filled PDF.

**Architecture:** The mode bar is a presentational component rendered inside the existing dashboard chat panel (right sidebar). Form Filler mode replaces the text input area with a PDF upload zone plus optional instruction input. The backend adds two new endpoints under `/api/checks/{id}/form-fill/` — one to extract fields + propose values, one to write values into the PDF. The form filler service reuses the existing `_build_context()` from `chat.py` and `extract_json()` from `llm_runtime.py`.

**Tech Stack:** Next.js 14 (React), FastAPI, PyMuPDF (already installed), Anthropic Claude API (Haiku for extraction), Tailwind CSS.

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `frontend/src/components/chat/ModeBar.tsx` | Pill toggle bar rendering Guardian / Form Filler modes |
| `frontend/src/components/chat/FormFillerUpload.tsx` | PDF upload drop zone + optional instruction input for Form Filler mode |
| `frontend/src/components/chat/FormPreviewCard.tsx` | Editable preview table of proposed field values with confidence badges |
| `compliance_os/web/services/form_filler.py` | AcroForm field extraction, LLM prompt construction, PDF field writing |
| `compliance_os/web/routers/form_fill.py` | FastAPI router for `/api/checks/{id}/form-fill/extract` and `/generate` |
| `tests/test_form_filler.py` | Unit tests for the form_filler service |

### Modified Files

| File | Changes |
|------|---------|
| `compliance_os/web/app.py:61-72` | Add `from compliance_os.web.routers import form_fill as form_fill_router` and `app.include_router(form_fill_router.router)` |
| `frontend/src/app/dashboard/page.tsx:85-91` | Add `ChatMode` type, `chatMode` state, form-fill state variables |
| `frontend/src/app/dashboard/page.tsx:1584-1696` | Integrate ModeBar, swap input area based on mode, render FormPreviewCard |

---

## Task 1: Backend — Form Filler Service

**Files:**
- Create: `compliance_os/web/services/form_filler.py`
- Test: `tests/test_form_filler.py`

- [ ] **Step 1: Write failing test for AcroForm field extraction**

```python
# tests/test_form_filler.py
"""Tests for the form filler service."""
import pytest
from compliance_os.web.services.form_filler import extract_acroform_fields


def test_extract_acroform_fields_from_fillable_pdf(tmp_path):
    """A PDF with AcroForm widgets should return field descriptors."""
    import pymupdf

    # Create a test PDF with two text widgets
    doc = pymupdf.open()
    page = doc.new_page()
    from pymupdf import Widget
    w1 = Widget()
    w1.field_name = "FirstName"
    w1.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w1.rect = pymupdf.Rect(50, 50, 200, 70)
    page.add_widget(w1)
    w2 = Widget()
    w2.field_name = "LastName"
    w2.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w2.rect = pymupdf.Rect(50, 80, 200, 100)
    page.add_widget(w2)
    pdf_path = tmp_path / "test.pdf"
    doc.save(str(pdf_path))
    doc.close()

    pdf_bytes = pdf_path.read_bytes()
    fields = extract_acroform_fields(pdf_bytes)
    assert len(fields) == 2
    names = {f["field_name"] for f in fields}
    assert names == {"FirstName", "LastName"}
    assert all(f["field_type"] == "Text" for f in fields)


def test_extract_acroform_fields_empty_pdf():
    """A PDF with no widgets should return an empty list."""
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    fields = extract_acroform_fields(pdf_bytes)
    assert fields == []


def test_extract_acroform_fields_invalid_bytes():
    """Non-PDF bytes should raise ValueError."""
    with pytest.raises(ValueError, match="Could not read"):
        extract_acroform_fields(b"not a pdf")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/lichenyu/compliance-os && python -m pytest tests/test_form_filler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.web.services.form_filler'`

- [ ] **Step 3: Implement extract_acroform_fields**

```python
# compliance_os/web/services/form_filler.py
"""AcroForm PDF field extraction, LLM-powered value proposal, and PDF filling."""
from __future__ import annotations

import json
import logging
from typing import Any

import pymupdf

from compliance_os.web.services.llm_runtime import extract_json

logger = logging.getLogger(__name__)

# --- Field type mapping ---
_WIDGET_TYPE_NAMES = {
    pymupdf.PDF_WIDGET_TYPE_TEXT: "Text",
    pymupdf.PDF_WIDGET_TYPE_CHECKBOX: "CheckBox",
    pymupdf.PDF_WIDGET_TYPE_COMBOBOX: "ComboBox",
    pymupdf.PDF_WIDGET_TYPE_LISTBOX: "ListBox",
    pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON: "RadioButton",
    pymupdf.PDF_WIDGET_TYPE_PUSHBUTTON: "PushButton",
    pymupdf.PDF_WIDGET_TYPE_SIGNATURE: "Signature",
}


def extract_acroform_fields(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extract all AcroForm widget fields from a PDF.

    Returns a list of dicts with keys: field_name, field_type, current_value, page.
    Raises ValueError if the bytes cannot be opened as a PDF.
    """
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not read this PDF file: {exc}") from exc

    fields: list[dict[str, Any]] = []
    try:
        for page in doc:
            for widget in page.widgets():
                fields.append({
                    "field_name": widget.field_name or "",
                    "field_type": _WIDGET_TYPE_NAMES.get(widget.field_type, "Unknown"),
                    "current_value": widget.field_value or "",
                    "page": page.number,
                })
    finally:
        doc.close()
    return fields
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/lichenyu/compliance-os && python -m pytest tests/test_form_filler.py -v`
Expected: 3 passed

- [ ] **Step 5: Write failing test for PDF field writing**

Add to `tests/test_form_filler.py`:

```python
from compliance_os.web.services.form_filler import fill_pdf_fields


def test_fill_pdf_fields_writes_values(tmp_path):
    """fill_pdf_fields should write values into AcroForm widgets and return valid PDF bytes."""
    import pymupdf
    from pymupdf import Widget

    doc = pymupdf.open()
    page = doc.new_page()
    w = Widget()
    w.field_name = "FullName"
    w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w.rect = pymupdf.Rect(50, 50, 200, 70)
    page.add_widget(w)
    pdf_bytes = doc.tobytes()
    doc.close()

    filled_bytes = fill_pdf_fields(pdf_bytes, {"FullName": "Jane Doe"})

    # Verify the value was written
    doc2 = pymupdf.open(stream=filled_bytes, filetype="pdf")
    widgets = list(doc2[0].widgets())
    assert len(widgets) == 1
    assert widgets[0].field_value == "Jane Doe"
    doc2.close()


def test_fill_pdf_fields_ignores_unknown_fields(tmp_path):
    """Fields not present in the PDF should be silently ignored."""
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    filled_bytes = fill_pdf_fields(pdf_bytes, {"NonExistent": "value"})
    assert len(filled_bytes) > 0  # Still returns valid PDF
```

- [ ] **Step 6: Run tests to verify the new ones fail**

Run: `cd /Users/lichenyu/compliance-os && python -m pytest tests/test_form_filler.py::test_fill_pdf_fields_writes_values tests/test_form_filler.py::test_fill_pdf_fields_ignores_unknown_fields -v`
Expected: FAIL — `ImportError: cannot import name 'fill_pdf_fields'`

- [ ] **Step 7: Implement fill_pdf_fields**

Add to `compliance_os/web/services/form_filler.py`:

```python
def fill_pdf_fields(pdf_bytes: bytes, values: dict[str, str]) -> bytes:
    """Write values into AcroForm fields of a PDF and return the modified bytes.

    Fields in `values` that don't exist in the PDF are silently ignored.
    Raises ValueError if the PDF cannot be opened.
    """
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not read this PDF file: {exc}") from exc

    try:
        for page in doc:
            for widget in page.widgets():
                name = widget.field_name or ""
                if name in values:
                    widget.field_value = values[name]
                    widget.update()
        return doc.tobytes()
    finally:
        doc.close()
```

- [ ] **Step 8: Run all tests to verify they pass**

Run: `cd /Users/lichenyu/compliance-os && python -m pytest tests/test_form_filler.py -v`
Expected: 5 passed

- [ ] **Step 9: Write failing test for propose_field_values**

Add to `tests/test_form_filler.py`:

```python
from unittest.mock import patch
from compliance_os.web.services.form_filler import propose_field_values


def test_propose_field_values_calls_llm_and_returns_proposals():
    """propose_field_values should call extract_json and return structured proposals."""
    fields = [
        {"field_name": "FirstName", "field_type": "Text", "current_value": "", "page": 0},
        {"field_name": "LastName", "field_type": "Text", "current_value": "", "page": 0},
    ]
    context = "## Key Facts\n- First Name: Jane\n- Last Name: Doe"
    mock_llm_response = {
        "fields": [
            {"field_name": "FirstName", "proposed_value": "Jane", "confidence": "high", "source": "Key Facts"},
            {"field_name": "LastName", "proposed_value": "Doe", "confidence": "high", "source": "Key Facts"},
        ]
    }

    with patch("compliance_os.web.services.form_filler.extract_json", return_value=mock_llm_response) as mock_ej:
        result = propose_field_values(fields, context)
        mock_ej.assert_called_once()
        assert len(result) == 2
        assert result[0]["field_name"] == "FirstName"
        assert result[0]["proposed_value"] == "Jane"
        assert result[0]["confidence"] == "high"


def test_propose_field_values_handles_empty_fields():
    """With no fields, should return empty list without calling LLM."""
    with patch("compliance_os.web.services.form_filler.extract_json") as mock_ej:
        result = propose_field_values([], "some context")
        mock_ej.assert_not_called()
        assert result == []
```

- [ ] **Step 10: Run tests to verify the new ones fail**

Run: `cd /Users/lichenyu/compliance-os && python -m pytest tests/test_form_filler.py::test_propose_field_values_calls_llm_and_returns_proposals tests/test_form_filler.py::test_propose_field_values_handles_empty_fields -v`
Expected: FAIL — `ImportError: cannot import name 'propose_field_values'`

- [ ] **Step 11: Implement propose_field_values**

Add to `compliance_os/web/services/form_filler.py`:

```python
FORM_FILL_SYSTEM_PROMPT = """You are a form-filling assistant. Given a user's compliance profile and a list of PDF form fields, propose the best value for each field.

Return a JSON object with a single key "fields" containing an array:
{
  "fields": [
    {
      "field_name": "exact field name from input",
      "proposed_value": "the value to fill in",
      "confidence": "high" | "medium" | "low",
      "source": "brief description of where this value came from"
    }
  ]
}

Rules:
- Only fill fields where you have supporting evidence from the context.
- Leave fields empty (proposed_value: "") if no evidence exists.
- For checkboxes, use "Yes" or "No".
- For choice/dropdown fields, pick from available options if known.
- confidence: "high" = exact match from extracted document field, "medium" = inferred from context, "low" = best guess.
- Return ALL fields from the input list, even if you cannot fill them."""


def propose_field_values(
    fields: list[dict[str, Any]],
    context: str,
    *,
    instruction: str | None = None,
    usage_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Use an LLM to propose values for AcroForm fields based on RAG context.

    Returns a list of dicts with keys: field_name, proposed_value, confidence, source.
    """
    if not fields:
        return []

    user_prompt_parts = [
        "Form fields to fill:\n",
        json.dumps(fields, indent=2),
        "\n\nUser's compliance profile and documents:\n",
        context,
    ]
    if instruction:
        user_prompt_parts.append(f"\n\nAdditional user instruction: {instruction}")

    result = extract_json(
        system_prompt=FORM_FILL_SYSTEM_PROMPT,
        user_prompt="".join(user_prompt_parts),
        temperature=0,
        max_tokens=4096,
        usage_context=usage_context,
    )

    return result.get("fields", [])
```

- [ ] **Step 12: Run all tests to verify they pass**

Run: `cd /Users/lichenyu/compliance-os && python -m pytest tests/test_form_filler.py -v`
Expected: 7 passed

- [ ] **Step 13: Commit**

```bash
git add compliance_os/web/services/form_filler.py tests/test_form_filler.py
git commit -m "feat: add form filler service — AcroForm extraction, LLM proposals, PDF writing"
```

---

## Task 2: Backend — Form Fill API Router

**Files:**
- Create: `compliance_os/web/routers/form_fill.py`
- Modify: `compliance_os/web/app.py:17-72`

- [ ] **Step 1: Create the router with extract endpoint**

```python
# compliance_os/web/routers/form_fill.py
"""API endpoints for PDF form filling."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import CheckRow
from compliance_os.web.routers.chat import _build_context, _get_user
from compliance_os.web.services.form_filler import (
    extract_acroform_fields,
    fill_pdf_fields,
    propose_field_values,
)

router = APIRouter(prefix="/api/checks/{check_id}/form-fill", tags=["form-fill"])


class FieldProposal(BaseModel):
    field_name: str
    field_type: str = ""
    proposed_value: str = ""
    confidence: str = ""  # high | medium | low
    source: str = ""


class ExtractResponse(BaseModel):
    fields: list[FieldProposal]
    form_field_count: int
    filled_count: int
    unfilled_count: int


@router.post("/extract", response_model=ExtractResponse)
async def extract_and_propose(
    check_id: str,
    file: UploadFile = File(...),
    instruction: str = Form(""),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Upload a PDF form, extract AcroForm fields, and propose values from RAG context."""
    user = _get_user(authorization, db)

    # Validate check belongs to user
    check = db.query(CheckRow).filter(
        CheckRow.id == check_id, CheckRow.user_id == user.id
    ).first()
    if not check:
        raise HTTPException(404, "Check not found")

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(422, "Please upload a PDF file")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:
        raise HTTPException(422, "File exceeds 20MB limit")

    # Extract AcroForm fields
    try:
        fields = extract_acroform_fields(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    if not fields:
        raise HTTPException(422, "This PDF does not contain fillable form fields")

    # Build RAG context (reuse chat's context builder)
    context_text, _ = _build_context(user.id, db)

    # Propose values via LLM
    try:
        proposals = propose_field_values(
            fields,
            context_text,
            instruction=instruction.strip() or None,
            usage_context={
                "db_session": db,
                "operation": "form_fill",
                "user_id": user.id,
                "check_id": check_id,
            },
        )
    except Exception:
        db.commit()
        raise HTTPException(502, "Could not generate form values — please try again")

    db.commit()

    # Merge field types from extraction with LLM proposals
    field_type_map = {f["field_name"]: f["field_type"] for f in fields}
    result_fields = []
    proposed_names = set()
    for p in proposals:
        proposed_names.add(p.get("field_name", ""))
        result_fields.append(FieldProposal(
            field_name=p.get("field_name", ""),
            field_type=field_type_map.get(p.get("field_name", ""), ""),
            proposed_value=p.get("proposed_value", ""),
            confidence=p.get("confidence", ""),
            source=p.get("source", ""),
        ))

    # Add any fields the LLM missed
    for f in fields:
        if f["field_name"] not in proposed_names:
            result_fields.append(FieldProposal(
                field_name=f["field_name"],
                field_type=f["field_type"],
            ))

    filled = sum(1 for f in result_fields if f.proposed_value)
    return ExtractResponse(
        fields=result_fields,
        form_field_count=len(result_fields),
        filled_count=filled,
        unfilled_count=len(result_fields) - filled,
    )


@router.post("/generate")
async def generate_filled_pdf(
    check_id: str,
    file: UploadFile = File(...),
    values: str = Form(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Write confirmed values into a PDF's AcroForm fields and return the filled PDF."""
    user = _get_user(authorization, db)

    check = db.query(CheckRow).filter(
        CheckRow.id == check_id, CheckRow.user_id == user.id
    ).first()
    if not check:
        raise HTTPException(404, "Check not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(422, "Please upload a PDF file")

    pdf_bytes = await file.read()

    import json
    try:
        field_values = json.loads(values)
    except json.JSONDecodeError:
        raise HTTPException(422, "Invalid values JSON")

    try:
        filled_bytes = fill_pdf_fields(pdf_bytes, field_values)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    original_name = file.filename or "form.pdf"
    filled_name = f"filled_{original_name}"

    return Response(
        content=filled_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filled_name}"'},
    )
```

- [ ] **Step 2: Register the router in app.py**

In `compliance_os/web/app.py`, add the import and include:

After line 21 (`from compliance_os.web.routers import chat as chat_router`), add:
```python
from compliance_os.web.routers import form_fill as form_fill_router
```

After line 72 (`app.include_router(chat_router.router)`), add:
```python
app.include_router(form_fill_router.router)
```

- [ ] **Step 3: Verify the server starts without errors**

Run: `cd /Users/lichenyu/compliance-os && python -c "from compliance_os.web.routers.form_fill import router; print('Router loaded:', router.prefix)"`
Expected: `Router loaded: /api/checks/{check_id}/form-fill`

- [ ] **Step 4: Commit**

```bash
git add compliance_os/web/routers/form_fill.py compliance_os/web/app.py
git commit -m "feat: add form-fill API endpoints — extract/propose and generate"
```

---

## Task 3: Frontend — ModeBar Component

**Files:**
- Create: `frontend/src/components/chat/ModeBar.tsx`

- [ ] **Step 1: Create the ModeBar component**

```tsx
// frontend/src/components/chat/ModeBar.tsx
"use client";

export type ChatMode = "guardian" | "form-filler";

interface ModeOption {
  id: ChatMode;
  label: string;
}

const MODES: ModeOption[] = [
  { id: "guardian", label: "Guardian" },
  { id: "form-filler", label: "Form Filler" },
];

interface Props {
  active: ChatMode;
  onChange: (mode: ChatMode) => void;
}

export default function ModeBar({ active, onChange }: Props) {
  return (
    <div className="flex gap-1.5 px-5 py-3 border-b border-blue-50/40 flex-shrink-0">
      {MODES.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onChange(mode.id)}
          className={`px-3.5 py-1.5 rounded-xl text-[12px] font-medium transition-all ${
            active === mode.id
              ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-sm"
              : "bg-white/50 text-[#556480] border border-white/60 hover:bg-white/70 hover:text-[#3a5a8c]"
          }`}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/ModeBar.tsx
git commit -m "feat: add ModeBar component — pill toggle for chat modes"
```

---

## Task 4: Frontend — FormFillerUpload Component

**Files:**
- Create: `frontend/src/components/chat/FormFillerUpload.tsx`

- [ ] **Step 1: Create the FormFillerUpload component**

```tsx
// frontend/src/components/chat/FormFillerUpload.tsx
"use client";

import { useCallback, useState } from "react";

interface Props {
  onSubmit: (file: File, instruction: string) => void;
  disabled?: boolean;
}

export default function FormFillerUpload({ onSubmit, disabled }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [instruction, setInstruction] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validate = (f: File): string | null => {
    if (!f.name.toLowerCase().endsWith(".pdf")) return "Please upload a PDF file";
    if (f.size > 20 * 1024 * 1024) return "File exceeds 20MB limit";
    return null;
  };

  const handleFile = useCallback((f: File) => {
    const err = validate(f);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setFile(f);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [disabled, handleFile]
  );

  const handleClick = () => {
    if (disabled) return;
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,application/pdf";
    input.onchange = () => {
      const f = input.files?.[0];
      if (f) handleFile(f);
    };
    input.click();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || disabled) return;
    onSubmit(file, instruction);
  };

  return (
    <div className="p-4 border-t border-blue-50/40 flex-shrink-0 space-y-3">
      {/* Drop zone */}
      {!file ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={handleClick}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
            dragOver
              ? "border-[#5b8dee] bg-blue-50/30"
              : "border-white/70 hover:border-[#5b8dee]/40 bg-white/30"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <p className="text-[13px] text-[#556480]">
            Drop a fillable PDF form here
          </p>
          <p className="text-[11px] text-[#7b8ba5] mt-1">or click to browse</p>
        </div>
      ) : (
        <div className="flex items-center gap-2 bg-white/50 rounded-xl px-3 py-2 border border-white/60">
          <div className="flex-1 min-w-0">
            <p className="text-[12px] font-medium text-[#0d1424] truncate">{file.name}</p>
            <p className="text-[11px] text-[#7b8ba5]">{(file.size / 1024).toFixed(0)} KB</p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); setFile(null); setError(null); }}
            className="text-[#7b8ba5] hover:text-[#0d1424] text-sm w-6 h-6 flex items-center justify-center rounded-lg hover:bg-white/50"
          >
            &times;
          </button>
        </div>
      )}
      {error && <p className="text-[11px] text-red-500">{error}</p>}

      {/* Instruction + submit */}
      {file && (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="Optional instructions..."
            disabled={disabled}
            className="flex-1 px-3 py-2 rounded-xl border border-white/70 bg-white/60 text-[12px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
          />
          <button
            type="submit"
            disabled={disabled}
            className="px-4 py-2 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-[12px] font-medium flex-shrink-0 disabled:opacity-50"
          >
            {disabled ? "..." : "Fill"}
          </button>
        </form>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/FormFillerUpload.tsx
git commit -m "feat: add FormFillerUpload — PDF drop zone with optional instructions"
```

---

## Task 5: Frontend — FormPreviewCard Component

**Files:**
- Create: `frontend/src/components/chat/FormPreviewCard.tsx`

- [ ] **Step 1: Create the FormPreviewCard component**

```tsx
// frontend/src/components/chat/FormPreviewCard.tsx
"use client";

import { useState } from "react";

export interface FieldProposal {
  field_name: string;
  field_type: string;
  proposed_value: string;
  confidence: string;
  source: string;
}

interface Props {
  fields: FieldProposal[];
  formFieldCount: number;
  filledCount: number;
  unfilledCount: number;
  onGenerate: (values: Record<string, string>) => void;
  onCancel: () => void;
  disabled?: boolean;
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-red-100 text-red-700",
};

export default function FormPreviewCard({
  fields,
  formFieldCount,
  filledCount,
  unfilledCount,
  onGenerate,
  onCancel,
  disabled,
}: Props) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const f of fields) {
      initial[f.field_name] = f.proposed_value || "";
    }
    return initial;
  });

  const handleGenerate = () => {
    onGenerate(values);
  };

  // Sort: filled fields first, then unfilled
  const sorted = [...fields].sort((a, b) => {
    const aFilled = values[a.field_name] ? 0 : 1;
    const bFilled = values[b.field_name] ? 0 : 1;
    return aFilled - bFilled;
  });

  return (
    <div className="bg-white/60 backdrop-blur rounded-2xl border border-white/60 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-blue-50/40">
        <div className="text-[13px] font-semibold text-[#0d1424]">Form Preview</div>
        <div className="text-[11px] text-[#7b8ba5] mt-0.5">
          {filledCount} of {formFieldCount} fields filled
          {unfilledCount > 0 && ` \u00b7 ${unfilledCount} need your input`}
        </div>
      </div>

      {/* Fields */}
      <div className="max-h-80 overflow-y-auto divide-y divide-blue-50/30">
        {sorted.map((field) => (
          <div key={field.field_name} className="px-4 py-2.5">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[11px] font-medium text-[#556480] flex-1 truncate">
                {field.field_name}
              </span>
              {field.confidence && (
                <span
                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md ${
                    CONFIDENCE_STYLES[field.confidence] || "bg-gray-100 text-gray-600"
                  }`}
                  title={field.source}
                >
                  {field.confidence}
                </span>
              )}
            </div>
            <input
              value={values[field.field_name] || ""}
              onChange={(e) =>
                setValues((prev) => ({ ...prev, [field.field_name]: e.target.value }))
              }
              placeholder="Enter value..."
              className="w-full px-2.5 py-1.5 rounded-lg border border-white/70 bg-white/60 text-[12px] text-[#0d1424] focus:border-[#5b8dee] focus:outline-none focus:ring-1 focus:ring-blue-200/30"
            />
            {field.source && (
              <p className="text-[10px] text-[#7b8ba5] mt-0.5 truncate" title={field.source}>
                Source: {field.source}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t border-blue-50/40 flex gap-2 justify-end">
        <button
          onClick={onCancel}
          disabled={disabled}
          className="px-3.5 py-2 rounded-xl text-[12px] font-medium bg-white/70 border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleGenerate}
          disabled={disabled}
          className="px-3.5 py-2 rounded-xl text-[12px] font-medium bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white disabled:opacity-50"
        >
          {disabled ? "Generating..." : "Generate PDF"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/FormPreviewCard.tsx
git commit -m "feat: add FormPreviewCard — editable field preview with confidence badges"
```

---

## Task 6: Frontend — Integrate Mode Bar and Form Filler into Dashboard

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`

This is the largest task. It wires the mode bar, form filler upload, and preview card into the existing dashboard chat panel.

- [ ] **Step 1: Add imports and state variables**

At the top of `frontend/src/app/dashboard/page.tsx`, after the existing imports (around line 1-15), add:

```tsx
import ModeBar, { ChatMode } from "@/components/chat/ModeBar";
import FormFillerUpload from "@/components/chat/FormFillerUpload";
import FormPreviewCard, { FieldProposal } from "@/components/chat/FormPreviewCard";
```

Inside the `DashboardPage` component, after the existing state declarations (around line 292, near `const [chatMessages, setChatMessages]`), add:

```tsx
  const [chatMode, setChatMode] = useState<ChatMode>("guardian");
  const [formFillLoading, setFormFillLoading] = useState(false);
  const [formFillPreview, setFormFillPreview] = useState<{
    fields: FieldProposal[];
    formFieldCount: number;
    filledCount: number;
    unfilledCount: number;
    originalFile: File;
  } | null>(null);
```

- [ ] **Step 2: Add form-fill handler functions**

After the `sendChatMessage` function (around line 799), add:

```tsx
  async function handleFormFillSubmit(file: File, instruction: string) {
    if (!checks.length) return;
    const checkId = checks[0].id;
    setFormFillLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (instruction) formData.append("instruction", instruction);

      const resp = await fetch(
        `${API}/checks/${checkId}/form-fill/extract`,
        { method: "POST", body: formData, headers: authHeaders() }
      );
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Failed to process form" }));
        throw new Error(err.detail || "Failed to process form");
      }
      const data = await resp.json();
      setFormFillPreview({
        fields: data.fields,
        formFieldCount: data.form_field_count,
        filledCount: data.filled_count,
        unfilledCount: data.unfilled_count,
        originalFile: file,
      });
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: nextChatMessageId(),
          role: "assistant",
          text: err instanceof Error ? err.message : "Failed to process the form. Please try again.",
        },
      ]);
    } finally {
      setFormFillLoading(false);
    }
  }

  async function handleFormFillGenerate(values: Record<string, string>) {
    if (!formFillPreview || !checks.length) return;
    const checkId = checks[0].id;
    setFormFillLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", formFillPreview.originalFile);
      formData.append("values", JSON.stringify(values));

      const resp = await fetch(
        `${API}/checks/${checkId}/form-fill/generate`,
        { method: "POST", body: formData, headers: authHeaders() }
      );
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Failed to generate PDF" }));
        throw new Error(err.detail || "Failed to generate PDF");
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `filled_${formFillPreview.originalFile.name}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setFormFillPreview(null);
      setChatMessages((prev) => [
        ...prev,
        {
          id: nextChatMessageId(),
          role: "assistant",
          text: `Your filled form "${formFillPreview.originalFile.name}" has been downloaded.`,
        },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: nextChatMessageId(),
          role: "assistant",
          text: err instanceof Error ? err.message : "Failed to generate the filled PDF. Please try again.",
        },
      ]);
    } finally {
      setFormFillLoading(false);
    }
  }
```

- [ ] **Step 3: Add ModeBar to the chat panel header**

In the chat panel JSX, find the header section (around line 1588-1595):

```tsx
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-blue-50/40 flex-shrink-0">
              <div>
                <div className="text-[14px] font-semibold text-[#0d1424]">Guardian Assistant</div>
                <div className="text-[11px] text-[#7b8ba5]">Ask anything about your compliance</div>
              </div>
              <button onClick={() => setChatOpen(false)} className="text-[#7b8ba5] hover:text-[#0d1424] text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/50 transition-all">&times;</button>
            </div>
```

Replace with:

```tsx
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-blue-50/40 flex-shrink-0">
              <div>
                <div className="text-[14px] font-semibold text-[#0d1424]">Guardian Assistant</div>
                <div className="text-[11px] text-[#7b8ba5]">
                  {chatMode === "guardian" ? "Ask anything about your compliance" : "Upload a fillable PDF to auto-complete"}
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} className="text-[#7b8ba5] hover:text-[#0d1424] text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/50 transition-all">&times;</button>
            </div>
            <ModeBar active={chatMode} onChange={setChatMode} />
```

- [ ] **Step 4: Add FormPreviewCard rendering in the messages area**

Find the chat loading indicator in the messages area (around line 1660-1668):

```tsx
              {chatLoading && (
                <div className="bg-white/50 backdrop-blur rounded-2xl p-4 border border-white/60">
                  <div className="flex gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-[#5b8dee] animate-bounce" style={{animationDelay:'0ms'}} />
                    <div className="w-2 h-2 rounded-full bg-[#5b8dee] animate-bounce" style={{animationDelay:'150ms'}} />
                    <div className="w-2 h-2 rounded-full bg-[#5b8dee] animate-bounce" style={{animationDelay:'300ms'}} />
                  </div>
                </div>
              )}
```

After it (before `</div>` closing the scroll area), add:

```tsx
              {formFillPreview && (
                <FormPreviewCard
                  fields={formFillPreview.fields}
                  formFieldCount={formFillPreview.formFieldCount}
                  filledCount={formFillPreview.filledCount}
                  unfilledCount={formFillPreview.unfilledCount}
                  onGenerate={handleFormFillGenerate}
                  onCancel={() => setFormFillPreview(null)}
                  disabled={formFillLoading}
                />
              )}
```

- [ ] **Step 5: Replace the input area with mode-conditional rendering**

Find the input section (around line 1671-1696):

```tsx
            {/* Input */}
            <div className="p-4 border-t border-blue-50/40 flex-shrink-0">
              <form onSubmit={async (e) => {
                e.preventDefault();
                const input = (e.target as HTMLFormElement).elements.namedItem("msg") as HTMLInputElement;
                const msg = input.value.trim();
                if (!msg || chatLoading) return;
                input.value = "";
                await sendChatMessage(msg);
              }} className="flex gap-2">
                <input
                  name="msg"
                  type="text"
                  placeholder="Ask about your compliance..."
                  className="flex-1 px-4 py-2.5 rounded-xl border border-white/70 bg-white/60 text-[13px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
                  disabled={chatLoading}
                />
                <button
                  type="submit"
                  disabled={chatLoading}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-[13px] font-medium flex-shrink-0 disabled:opacity-50"
                >
                  Send
                </button>
              </form>
            </div>
```

Replace with:

```tsx
            {/* Input — mode-conditional */}
            {chatMode === "guardian" ? (
              <div className="p-4 border-t border-blue-50/40 flex-shrink-0">
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  const input = (e.target as HTMLFormElement).elements.namedItem("msg") as HTMLInputElement;
                  const msg = input.value.trim();
                  if (!msg || chatLoading) return;
                  input.value = "";
                  await sendChatMessage(msg);
                }} className="flex gap-2">
                  <input
                    name="msg"
                    type="text"
                    placeholder="Ask about your compliance..."
                    className="flex-1 px-4 py-2.5 rounded-xl border border-white/70 bg-white/60 text-[13px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
                    disabled={chatLoading}
                  />
                  <button
                    type="submit"
                    disabled={chatLoading}
                    className="px-4 py-2.5 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-[13px] font-medium flex-shrink-0 disabled:opacity-50"
                  >
                    Send
                  </button>
                </form>
              </div>
            ) : (
              <FormFillerUpload
                onSubmit={handleFormFillSubmit}
                disabled={formFillLoading}
              />
            )}
```

- [ ] **Step 6: Verify frontend builds**

Run: `cd /Users/lichenyu/compliance-os/frontend && npx next build 2>&1 | tail -20`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/dashboard/page.tsx
git commit -m "feat: integrate mode bar and form filler into dashboard chat panel"
```

---

## Task 7: End-to-End Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/lichenyu/compliance-os && python -m pytest tests/ -v`
Expected: All tests pass including the new form filler tests.

- [ ] **Step 2: Verify frontend builds cleanly**

Run: `cd /Users/lichenyu/compliance-os/frontend && npx next build 2>&1 | tail -20`
Expected: Build succeeds.

- [ ] **Step 3: Verify router loads with all imports**

Run: `cd /Users/lichenyu/compliance-os && python -c "from compliance_os.web.app import app; routes = [r.path for r in app.routes]; print([r for r in routes if 'form-fill' in r])"`
Expected: `['/api/checks/{check_id}/form-fill/extract', '/api/checks/{check_id}/form-fill/generate']`

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues from end-to-end verification"
```
