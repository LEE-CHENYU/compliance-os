"""Tests for the document classifier."""

from pathlib import Path

from compliance_os.indexer.classifier import classify_document


def test_tax_form_classification():
    result = classify_document(
        Path("/data/tax/2025_w2.txt"),
        base_dir=Path("/data"),
    )
    assert result["doc_type"] == "tax_form"
    assert result["category"] == "tax"


def test_immigration_classification():
    result = classify_document(
        Path("/data/legal/immigration/h1b_registration.pdf"),
        base_dir=Path("/data"),
    )
    assert result["doc_type"] == "immigration"
    assert result["category"] == "legal"


def test_financial_classification():
    result = classify_document(
        Path("/data/bank_statements/wire_transfers_2026.csv"),
        base_dir=Path("/data"),
    )
    assert result["doc_type"] == "financial"


def test_general_fallback():
    result = classify_document(
        Path("/data/misc/random_notes.txt"),
        base_dir=Path("/data"),
    )
    assert result["doc_type"] == "general"


def test_metadata_fields():
    result = classify_document(
        Path("/data/outgoing/drafts/reply_to_cpa.txt"),
        base_dir=Path("/data"),
    )
    assert "file_path" in result
    assert "category" in result
    assert "doc_type" in result
    assert "file_ext" in result
    assert result["file_ext"] == ".txt"
