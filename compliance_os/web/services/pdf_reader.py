"""Extract text from the first page of a PDF using PyMuPDF.

Uses structured-block extraction when available so that table-layout PDFs
(common in H-1B invoices, employment letters, USCIS notices) preserve
column/cell boundaries instead of garbling text across columns.
"""
from __future__ import annotations


def _reconstruct_from_blocks(page) -> str:
    """Reconstruct text from PyMuPDF page blocks, grouping spans by line.

    For table PDFs, get_text("dict") returns blocks with explicit bounding
    boxes. We sort by (top, left) so that columns in the same visual row
    stay together, separated by tab. This preserves "Label:\\tValue" pairs
    that the simple get_text() call would concatenate or reorder.
    """
    try:
        data = page.get_text("dict")
    except Exception:
        return ""

    lines: list[tuple[float, float, str]] = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            origin = line.get("bbox", (0, 0, 0, 0))
            y_top = round(origin[1], 1)
            x_left = origin[0]
            text = " ".join(
                span.get("text", "").strip()
                for span in line.get("spans", [])
                if span.get("text", "").strip()
            )
            if text:
                lines.append((y_top, x_left, text))

    if not lines:
        return ""

    lines.sort(key=lambda t: (t[0], t[1]))

    output: list[str] = []
    prev_y: float | None = None
    row_parts: list[str] = []
    for y_top, _x, text in lines:
        if prev_y is not None and abs(y_top - prev_y) > 3.0:
            output.append("\t".join(row_parts))
            row_parts = []
        row_parts.append(text)
        prev_y = y_top
    if row_parts:
        output.append("\t".join(row_parts))

    return "\n".join(output)


def extract_first_page(file_path: str) -> str:
    """Return text content of the first page, or empty string on failure.

    Attempts structured-block extraction first (better for tables), falls
    back to plain get_text() if blocks are empty or fail.
    """
    try:
        import pymupdf
        doc = pymupdf.open(file_path)
        if len(doc) == 0:
            doc.close()
            return ""
        page = doc[0]
        text = _reconstruct_from_blocks(page)
        if not text.strip():
            text = page.get_text()
        doc.close()
        return text
    except FileNotFoundError:
        return ""
    except (ValueError, RuntimeError, OSError) as exc:
        import logging
        logging.getLogger(__name__).warning("PDF extraction failed for %s: %s", file_path, exc)
        return ""
