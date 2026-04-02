"""PDF AcroForm field extraction, filling, and LLM-assisted value proposal."""
from __future__ import annotations

import json
from typing import Any

import fitz  # PyMuPDF

from compliance_os.web.services.llm_runtime import extract_json

# ---------------------------------------------------------------------------
# Widget type constant → human-readable label
# ---------------------------------------------------------------------------

_WIDGET_TYPE_LABELS: dict[int, str] = {
    fitz.PDF_WIDGET_TYPE_TEXT: "Text",
    fitz.PDF_WIDGET_TYPE_CHECKBOX: "CheckBox",
    fitz.PDF_WIDGET_TYPE_COMBOBOX: "ComboBox",
    fitz.PDF_WIDGET_TYPE_LISTBOX: "ListBox",
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "RadioButton",
    fitz.PDF_WIDGET_TYPE_BUTTON: "PushButton",
    fitz.PDF_WIDGET_TYPE_SIGNATURE: "Signature",
    fitz.PDF_WIDGET_TYPE_UNKNOWN: "Unknown",
}


def _open_pdf(pdf_bytes: bytes) -> fitz.Document:
    """Open PDF bytes and raise ValueError if they are invalid."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc
    if doc.is_closed or len(doc) == 0 and not doc.is_pdf:
        raise ValueError("Opened document is not a valid PDF")
    return doc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_acroform_fields(pdf_bytes: bytes) -> list[dict]:
    """Extract all AcroForm widget fields from a PDF.

    Parameters
    ----------
    pdf_bytes:
        Raw bytes of the PDF document.

    Returns
    -------
    list[dict]
        Each dict has keys: field_name, field_type, current_value, page.
    """
    doc = _open_pdf(pdf_bytes)
    results: list[dict] = []
    for page_index, page in enumerate(doc):
        for widget in page.widgets():
            field_type_int = widget.field_type
            field_type_label = _WIDGET_TYPE_LABELS.get(field_type_int, "Unknown")
            results.append(
                {
                    "field_name": widget.field_name,
                    "field_type": field_type_label,
                    "current_value": widget.field_value,
                    "page": page_index,
                }
            )
    return results


def fill_pdf_fields(pdf_bytes: bytes, values: dict[str, str]) -> bytes:
    """Write field values into a PDF and return the modified bytes.

    Parameters
    ----------
    pdf_bytes:
        Raw bytes of the PDF document.
    values:
        Mapping of field_name → new value.  Fields that don't exist in the
        PDF are silently ignored.

    Returns
    -------
    bytes
        The modified PDF as raw bytes.
    """
    doc = _open_pdf(pdf_bytes)
    for page in doc:
        for widget in page.widgets():
            if widget.field_name in values:
                widget.field_value = values[widget.field_name]
                widget.update()
    return doc.tobytes()


def propose_field_values(
    fields: list[dict],
    context: str,
    *,
    instruction: str | None = None,
    usage_context: dict[str, Any] | None = None,
) -> list[dict]:
    """Ask the LLM to propose values for each form field given user context.

    Parameters
    ----------
    fields:
        List of field dicts as returned by :func:`extract_acroform_fields`.
    context:
        Free-text description of the user (documents, profile, etc.).
    instruction:
        Optional extra instruction appended to the system prompt.
    usage_context:
        Optional dict forwarded to ``extract_json`` for usage tracking.

    Returns
    -------
    list[dict]
        Each dict has keys: field_name, proposed_value, confidence, source.
    """
    if not fields:
        return []

    fields_json = json.dumps(fields, ensure_ascii=False)

    system_prompt_parts = [
        "You are an expert form-filling assistant.",
        "Given a list of PDF form fields and contextual information about the user, "
        "propose the most accurate value for each field.",
        "Return ONLY valid JSON matching this schema exactly:",
        '{"fields": [{"field_name": "<name>", "proposed_value": "<value>", '
        '"confidence": "high"|"medium"|"low", "source": "<where you got it>"}]}',
        "Include every field from the input list. Use empty string if you cannot determine a value.",
    ]
    if instruction:
        system_prompt_parts.append(f"Additional instruction: {instruction}")

    system_prompt = "\n".join(system_prompt_parts)

    user_prompt = (
        f"Form fields:\n{fields_json}\n\n"
        f"User context:\n{context}"
    )

    response = extract_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0,
        max_tokens=4096,
        usage_context=usage_context,
    )
    return response.get("fields", [])
