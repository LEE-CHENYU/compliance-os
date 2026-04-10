"""Simple PDF builders for marketplace product deliverables."""

from __future__ import annotations

from typing import Iterable

import fitz


def _normalize_lines(lines: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for line in lines:
        if line is None:
            normalized.append("")
            continue
        for part in str(line).splitlines() or [""]:
            normalized.append(part.rstrip())
    return normalized


def build_text_pdf(title: str, lines: Iterable[str], *, subtitle: str | None = None) -> bytes:
    """Render a simple text-first PDF packet."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    margin_x = 54
    y = 56

    def new_page() -> fitz.Page:
        return doc.new_page(width=612, height=792)

    page.insert_text((margin_x, y), title, fontsize=20, fontname="helv")
    y += 26
    if subtitle:
        page.insert_text((margin_x, y), subtitle, fontsize=10, fontname="helv")
        y += 24
    else:
        y += 8

    for line in _normalize_lines(lines):
        if y > 734:
            page = new_page()
            y = 56
        if not line:
            y += 10
            continue
        page.insert_textbox(
            fitz.Rect(margin_x, y, 558, y + 20),
            line,
            fontsize=10.5,
            fontname="helv",
        )
        y += 15

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return pdf_bytes
