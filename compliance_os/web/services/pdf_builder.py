"""Simple PDF builders for marketplace product deliverables."""

from __future__ import annotations

import textwrap
from typing import Iterable

import fitz


# Approximate width budget: 504pt text box @ 10.5pt helvetica ≈ 86 chars.
# Leave margin for wider glyphs so full sentences don't clip.
_WRAP_WIDTH = 80


def _normalize_lines(lines: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for line in lines:
        if line is None:
            normalized.append("")
            continue
        for part in str(line).splitlines() or [""]:
            normalized.append(part.rstrip())
    return normalized


def _wrap(line: str) -> list[str]:
    """Soft-wrap a logical line into physical lines that fit the text box."""
    if not line:
        return [""]
    wrapped = textwrap.wrap(
        line,
        width=_WRAP_WIDTH,
        break_long_words=False,
        break_on_hyphens=False,
        replace_whitespace=False,
    )
    return wrapped or [line]


def build_text_pdf(title: str, lines: Iterable[str], *, subtitle: str | None = None) -> bytes:
    """Render a simple text-first PDF packet.

    Long lines are soft-wrapped so content isn't silently clipped by the
    fixed-size text box. A single logical line can span multiple physical
    lines in the rendered PDF.
    """
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

    for logical_line in _normalize_lines(lines):
        if not logical_line:
            if y > 734:
                page = new_page()
                y = 56
            y += 10
            continue
        for physical_line in _wrap(logical_line):
            if y > 734:
                page = new_page()
                y = 56
            page.insert_textbox(
                fitz.Rect(margin_x, y, 558, y + 20),
                physical_line,
                fontsize=10.5,
                fontname="helv",
            )
            y += 15

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return pdf_bytes
