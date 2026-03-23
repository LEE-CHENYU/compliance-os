"""Test lightweight document classification."""

from compliance_os.web.services.classifier import classify_text


def test_w2_classification():
    text = "Wage and Tax Statement 2024 Form W-2"
    result = classify_text(text)
    assert result.doc_type == "w2"


def test_i20_classification():
    text = "Certificate of Eligibility for Nonimmigrant Student Status Form I-20"
    result = classify_text(text)
    assert result.doc_type == "i20"


def test_unknown_text_returns_none():
    text = "Random document with no recognizable patterns"
    result = classify_text(text)
    assert result.doc_type is None


def test_1040nr_classification():
    text = "U.S. Nonresident Alien Income Tax Return Form 1040-NR"
    result = classify_text(text)
    assert result.doc_type == "1040nr"
