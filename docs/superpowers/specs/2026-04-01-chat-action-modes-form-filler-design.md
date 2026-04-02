# Chat Action Modes + Form Filler

**Date:** 2026-04-01
**Status:** Approved

## Overview

Add a toggleable action mode bar to the chat UI and implement the first mode — **Form Filler** — which lets users upload a blank AcroForm PDF, proposes field values from RAG context, previews them for editing, and generates a filled PDF for download.

## Mode Bar

A horizontal pill bar rendered above the chat input area.

- **Guardian** (default): Current chat behavior — RAG-powered compliance Q&A.
- **Form Filler**: Activates the form-filling flow described below.
- Only one mode active at a time.
- Mode state stored in `useChat` hook and sent with each API request as a `mode` field.
- Designed to be extensible — adding a new mode means adding a pill and its corresponding UI/backend logic.

## Form Filler Flow

### Step 1 — Upload

When Form Filler mode is active, the chat input area transforms:
- A file drop zone appears (reuse `FileDropZone` pattern) accepting a single PDF.
- The text input remains available for optional user instructions (e.g., "Use my H-1B employer info").
- Max file size: 20 MB (consistent with existing upload limits).

### Step 2 — Extract AcroForm Fields

Backend receives the PDF and extracts all AcroForm widget field names using PyMuPDF:

```python
import pymupdf
doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
fields = []
for page in doc:
    for widget in page.widgets():
        fields.append({
            "name": widget.field_name,
            "type": widget.field_type_string,  # Text, CheckBox, Choice, etc.
            "current_value": widget.field_value,
            "page": page.number,
        })
```

If the PDF has zero AcroForm fields, return an error telling the user this is not a fillable form.

### Step 3 — RAG Context + LLM Field Matching

Build RAG context using the existing `_build_context()` from `chat.py` (user profile, subject chains, extracted fields, document excerpts). Send the field list + context to Claude:

**Model:** Claude Haiku 4.5 (extraction-class work, cost-efficient).

**Prompt structure:**
```
You are a form-filling assistant. Given a user's compliance profile and a list of PDF form fields, propose the best value for each field.

Return JSON array:
[
  {
    "field_name": "...",
    "proposed_value": "...",
    "confidence": "high" | "medium" | "low",
    "source": "brief description of where this value came from"
  }
]

Rules:
- Only fill fields where you have supporting evidence from the context.
- Leave fields empty (proposed_value: "") if no evidence exists.
- For checkboxes, use "Yes"/"No" or the checkbox export value.
- For choice/dropdown fields, pick from the available options if known.
- confidence: "high" = exact match from extracted document field, "medium" = inferred from context, "low" = best guess.
```

**Request payload to LLM:**
- System prompt: form-filling instructions above
- User message: JSON with `{fields: [...], context: "..."}`
- Optional user instruction appended if provided

### Step 4 — Preview

Frontend renders a `FormPreviewCard` component:
- Table/card list of all fields with: field name, proposed value, confidence badge (green/yellow/red), source tooltip.
- Each value is an editable input — user can override any proposed value.
- Fields with empty proposed values shown at bottom as "Not filled — please provide manually".
- "Generate PDF" button at bottom, disabled until user has reviewed.

### Step 5 — Confirm & Download

User clicks "Generate PDF". Frontend sends the original PDF + confirmed values to the generate endpoint. Backend writes values into AcroForm fields:

```python
doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
for page in doc:
    for widget in page.widgets():
        if widget.field_name in confirmed_values:
            widget.field_value = confirmed_values[widget.field_name]
            widget.update()
doc.save(output_path)
```

Returns the filled PDF as a file download.

## API Endpoints

### `POST /api/checks/{check_id}/form-fill/extract`

**Request:** `multipart/form-data`
- `file`: PDF file (required)
- `instruction`: optional text instruction from user

**Response:**
```json
{
  "fields": [
    {
      "field_name": "First Name",
      "field_type": "Text",
      "proposed_value": "Chen Yu",
      "confidence": "high",
      "source": "Extracted from I-20 document"
    }
  ],
  "form_field_count": 42,
  "filled_count": 35,
  "unfilled_count": 7
}
```

### `POST /api/checks/{check_id}/form-fill/generate`

**Request:** `multipart/form-data`
- `file`: original PDF file
- `values`: JSON string of `{field_name: confirmed_value}` pairs

**Response:** Filled PDF file as `application/pdf` download with `Content-Disposition: attachment; filename="filled_<original_name>.pdf"`.

## Frontend Components

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ModeBar.tsx` | `components/chat/` | Pill toggle bar (Guardian / Form Filler) |
| `FormFillerUpload.tsx` | `components/chat/` | PDF upload zone shown in Form Filler mode |
| `FormPreviewCard.tsx` | `components/chat/` | Field value preview table with inline editing |

### Modified Components

| Component | Changes |
|-----------|---------|
| `ChatPanel.tsx` | Render `ModeBar` above input; conditionally show `FormFillerUpload` or text input based on mode; render `FormPreviewCard` as a special message type |
| `useChat.ts` | Add `mode` state, form-fill API calls (`extractFormFields`, `generateFilledPdf`), preview state management |

### No Changes

| Component | Reason |
|-----------|--------|
| `ChatMessage.tsx` | Form preview is a separate component, not a chat message |
| `FileDropZone.tsx` | Reuse pattern but `FormFillerUpload` is a distinct component with different behavior (single PDF, no doc type selection) |

## Backend Components

### New Files

| File | Location | Purpose |
|------|----------|---------|
| `form_filler.py` | `compliance_os/web/services/` | AcroForm field extraction, LLM prompt construction, PDF field writing |
| `form_fill.py` | `compliance_os/web/routers/` | FastAPI router for `/form-fill/extract` and `/form-fill/generate` |

### Modified Files

| File | Changes |
|------|---------|
| `app.py` | Register the new `form_fill` router |

### No Changes

| File | Reason |
|------|--------|
| `chat.py` (router) | Form filling is a separate flow, not a chat endpoint |
| `retrieval.py` | Reused as-is for RAG context |
| `llm_runtime.py` | Reused as-is for LLM calls |
| `tables_v2.py` | No new database tables — form filling is stateless (upload, fill, download) |

## LLM Usage

- **Model:** Claude Haiku 4.5 (configured via `ANTHROPIC_EXTRACTION_MODEL`)
- **Estimated tokens:** ~2000 input (field list + RAG context), ~500 output (field values JSON)
- **Tracked via:** existing `LlmApiUsageRow` with `operation="form_fill"`

## Error Handling

| Scenario | Behavior |
|----------|----------|
| PDF has no AcroForm fields | Return 422 with message "This PDF does not contain fillable form fields" |
| PDF is corrupted/unreadable | Return 422 with message "Could not read this PDF file" |
| File is not a PDF | Return 422 with message "Please upload a PDF file" |
| LLM call fails | Return 502 with message "Could not generate form values — please try again" |
| No RAG context available | Proceed but all fields will have "low" confidence or be empty |

## Scope Boundaries

**In scope:**
- Mode bar UI with Guardian + Form Filler pills
- AcroForm PDF field extraction and programmatic filling via PyMuPDF
- RAG-powered field value proposals with confidence levels
- Editable preview card before PDF generation
- PDF download of filled form

**Out of scope (future enhancements):**
- Flat/scanned PDF text overlay
- Form template library or auto-detection
- Saving filled forms back to the document store
- Multi-page form wizards
- Additional action modes (Research, Draft Letter, etc.)
- Persisting form-fill history
