"""PDF AcroForm field extraction, filling, and LLM-assisted value proposal."""
from __future__ import annotations

import json
import re
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

_CHOICE_WIDGET_TYPES = {
    fitz.PDF_WIDGET_TYPE_CHECKBOX,
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON,
}

_GENERIC_FIELD_NAME_RE = re.compile(
    r"^(?:"
    r"text\s*field|textfield|"
    r"check\s*box|checkbox|"
    r"radio\s*button|radiobutton|"
    r"combo\s*box|combobox|"
    r"list\s*box|listbox|"
    r"push\s*button|pushbutton|button|"
    r"signature|sig|"
    r"date\s*field|date|"
    r"field"
    r")[\s_-]*\d+$",
    re.IGNORECASE,
)


def _open_pdf(pdf_bytes: bytes) -> fitz.Document:
    """Open PDF bytes and raise ValueError if they are invalid."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc
    if doc.is_closed or len(doc) == 0 and not doc.is_pdf:
        raise ValueError("Opened document is not a valid PDF")
    return doc


def _clean_text(value: Any) -> str:
    """Collapse whitespace and coerce ``None`` to an empty string."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _humanize_field_name(field_name: str) -> str:
    """Turn widget identifiers like ``student_name`` into readable text."""
    text = _clean_text(field_name)
    if not text:
        return ""
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return _clean_text(text)


def _is_generic_field_name(field_name: str) -> bool:
    """Return ``True`` for low-signal names like ``Text Field0``."""
    return bool(_GENERIC_FIELD_NAME_RE.match(_humanize_field_name(field_name)))


def _extract_page_lines(page: fitz.Page) -> list[dict[str, Any]]:
    """Group page words into line-level text boxes for nearby-label lookup."""
    grouped: dict[tuple[int, int], list[tuple[float, float, float, float, str, int]]] = {}
    for x0, y0, x1, y1, text, block_no, line_no, word_no in page.get_text("words"):
        cleaned = _clean_text(text)
        if not cleaned:
            continue
        grouped.setdefault((block_no, line_no), []).append((x0, y0, x1, y1, cleaned, word_no))

    lines: list[dict[str, Any]] = []
    for words in grouped.values():
        words.sort(key=lambda word: (word[5], word[0]))
        line_text = _clean_text(" ".join(word[4] for word in words))
        if not line_text:
            continue
        rect = fitz.Rect(
            min(word[0] for word in words),
            min(word[1] for word in words),
            max(word[2] for word in words),
            max(word[3] for word in words),
        )
        lines.append({"text": line_text, "rect": rect})

    lines.sort(key=lambda line: (line["rect"].y0, line["rect"].x0))
    return lines


def _axis_overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    """Return the overlap length between two 1D intervals."""
    return max(0.0, min(a1, b1) - max(a0, b0))


def _score_line_as_label(widget_rect: fitz.Rect, field_type: int, line_rect: fitz.Rect, text: str) -> float:
    """Score a nearby line as the likely human-readable label for a widget."""
    widget_center_x = (widget_rect.x0 + widget_rect.x1) / 2
    widget_center_y = (widget_rect.y0 + widget_rect.y1) / 2
    line_center_x = (line_rect.x0 + line_rect.x1) / 2
    line_center_y = (line_rect.y0 + line_rect.y1) / 2

    horizontal_delta = abs(widget_center_x - line_center_x)
    vertical_delta = abs(widget_center_y - line_center_y)
    horizontal_overlap = _axis_overlap(widget_rect.x0, widget_rect.x1, line_rect.x0, line_rect.x1)
    vertical_overlap = _axis_overlap(widget_rect.y0, widget_rect.y1, line_rect.y0, line_rect.y1)

    left_gap = widget_rect.x0 - line_rect.x1
    right_gap = line_rect.x0 - widget_rect.x1
    above_gap = widget_rect.y0 - line_rect.y1

    score = float("-inf")
    if field_type in _CHOICE_WIDGET_TYPES:
        if 0 <= right_gap <= 220 and (vertical_overlap > 0 or vertical_delta <= max(18.0, widget_rect.height * 1.75)):
            score = max(score, 320.0 - (right_gap * 1.5) - (vertical_delta * 4.0))
        if 0 <= left_gap <= 220 and (vertical_overlap > 0 or vertical_delta <= max(18.0, widget_rect.height * 1.75)):
            score = max(score, 260.0 - (left_gap * 1.4) - (vertical_delta * 4.0))
        if 0 <= above_gap <= 110 and (horizontal_overlap > 0 or horizontal_delta <= 260):
            score = max(score, 220.0 - (above_gap * 3.0) - (horizontal_delta * 0.35))
    else:
        if 0 <= left_gap <= 260 and (vertical_overlap > 0 or vertical_delta <= max(22.0, widget_rect.height * 1.5)):
            score = max(score, 320.0 - (left_gap * 1.3) - (vertical_delta * 4.0))
        if 0 <= above_gap <= 110 and (horizontal_overlap > 0 or horizontal_delta <= 260):
            score = max(score, 280.0 - (above_gap * 3.0) - (horizontal_delta * 0.35))
        if 0 <= right_gap <= 140 and (vertical_overlap > 0 or vertical_delta <= max(22.0, widget_rect.height * 1.5)):
            score = max(score, 170.0 - (right_gap * 1.8) - (vertical_delta * 4.0))

    # Very long lines are more likely to be surrounding instructions than labels.
    score -= max(len(text) - 80, 0) * 0.2
    return score


def _best_nearby_label(widget_rect: fitz.Rect, field_type: int, page_lines: list[dict[str, Any]]) -> str:
    """Pick the most likely nearby line of text describing a widget."""
    best_text = ""
    best_score = float("-inf")
    for line in page_lines:
        text = line["text"]
        score = _score_line_as_label(widget_rect, field_type, line["rect"], text)
        if score > best_score:
            best_score = score
            best_text = text
    return best_text if best_score > 0 else ""


def _context_search_rect(widget_rect: fitz.Rect, field_type: int) -> fitz.Rect:
    """Search rectangle for nearby instructional text around a widget."""
    if field_type in _CHOICE_WIDGET_TYPES:
        return fitz.Rect(
            widget_rect.x0 - 280,
            widget_rect.y0 - 140,
            widget_rect.x1 + 280,
            widget_rect.y1 + 70,
        )
    return fitz.Rect(
        widget_rect.x0 - 280,
        widget_rect.y0 - 110,
        widget_rect.x1 + 90,
        widget_rect.y1 + 60,
    )


def _strip_redundant_context(context: str, *known_strings: str) -> str:
    """Remove the main label from the surrounding context when possible."""
    cleaned = _clean_text(context)
    for item in known_strings:
        candidate = _clean_text(item)
        if not candidate:
            continue
        if cleaned == candidate:
            return ""
        if len(cleaned) > len(candidate) + 4:
            cleaned = _clean_text(cleaned.replace(candidate, " "))
    return cleaned


def _extract_field_text_context(
    page: fitz.Page,
    widget: fitz.Widget,
    page_lines: list[dict[str, Any]],
) -> tuple[str, str]:
    """Resolve a readable label and nearby context for a widget."""
    direct_label = _clean_text(widget.field_label)
    fallback_name = _humanize_field_name(widget.field_name)
    nearby_label = _best_nearby_label(widget.rect, widget.field_type, page_lines)

    if direct_label:
        field_label = direct_label
    elif _is_generic_field_name(widget.field_name):
        field_label = nearby_label or fallback_name
    else:
        field_label = fallback_name or nearby_label

    context = _clean_text(page.get_textbox(_context_search_rect(widget.rect, widget.field_type)))
    context = _strip_redundant_context(context, field_label, widget.field_name, direct_label, nearby_label)
    return field_label, context


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
        Each dict has keys: field_name, field_type, current_value, page,
        field_label, and field_context.
    """
    doc = _open_pdf(pdf_bytes)
    results: list[dict] = []
    for page_index, page in enumerate(doc):
        page_lines = _extract_page_lines(page)
        for widget in page.widgets():
            field_type_int = widget.field_type
            field_type_label = _WIDGET_TYPE_LABELS.get(field_type_int, "Unknown")
            field_label, field_context = _extract_field_text_context(page, widget, page_lines)
            results.append(
                {
                    "field_name": widget.field_name,
                    "field_type": field_type_label,
                    "current_value": widget.field_value,
                    "page": page_index,
                    "field_label": field_label,
                    "field_context": field_context,
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
        "Each field may include a human-readable field_label and nearby field_context "
        "extracted from the PDF layout. Prefer those over raw technical widget names.",
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
