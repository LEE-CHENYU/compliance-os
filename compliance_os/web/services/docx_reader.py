"""Minimal DOCX text extraction using the OOXML zip structure."""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
DOCX_TEXT_PARTS = (
    "word/document.xml",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "word/comments.xml",
)


def _extract_xml_text(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""

    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        runs = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)

    if paragraphs:
        return "\n".join(paragraphs)

    tokens = [node.text or "" for node in root.findall(".//w:t", WORD_NAMESPACE)]
    return "\n".join(token.strip() for token in tokens if token and token.strip())


def extract_docx_text(file_path: str | Path) -> tuple[str, dict[str, object]]:
    """Return concatenated text and lightweight provenance metadata for a DOCX file."""
    path = Path(file_path)
    collected: list[str] = []
    read_parts: list[str] = []

    with ZipFile(path) as archive:
        part_names = list(archive.namelist())
        ordered_parts = [
            name
            for name in part_names
            if name in DOCX_TEXT_PARTS
            or (name.startswith("word/header") and name.endswith(".xml"))
            or (name.startswith("word/footer") and name.endswith(".xml"))
        ]

        for part_name in ordered_parts:
            read_parts.append(part_name)
            text = _extract_xml_text(archive.read(part_name))
            if text:
                collected.append(text)

    return "\n\n".join(collected).strip(), {
        "source": "docx_xml",
        "parts_read": read_parts,
        "part_count": len(read_parts),
    }
