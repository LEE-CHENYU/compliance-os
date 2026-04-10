"""Tests for the form filler service (PDF field extraction and filling)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import fitz
import pytest

from compliance_os.web.services.form_filler import (
    extract_acroform_fields,
    fill_pdf_fields,
    propose_field_values,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_with_text_field(
    field_name: str = "FirstName",
    field_value: str = "",
    *,
    field_label: str = "",
    drawn_label: str = "",
) -> bytes:
    """Create a minimal PDF with a single text widget."""
    doc = fitz.open()
    page = doc.new_page()
    if drawn_label:
        page.insert_text((50, 42), drawn_label, fontsize=11)
    widget = fitz.Widget()
    widget.rect = fitz.Rect(50, 50, 300, 80)
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.field_name = field_name
    widget.field_value = field_value
    if field_label:
        widget.field_label = field_label
    page.add_widget(widget)
    return doc.tobytes()


def _make_pdf_with_checkbox(
    field_name: str = "Check Box0",
    *,
    option_label: str = "Yes",
    question_text: str = "",
) -> bytes:
    """Create a minimal PDF with a single checkbox and nearby explanatory text."""
    doc = fitz.open()
    page = doc.new_page()
    if question_text:
        page.insert_textbox(
            fitz.Rect(50, 20, 420, 60),
            question_text,
            fontsize=11,
        )
    widget = fitz.Widget()
    widget.rect = fitz.Rect(50, 70, 62, 82)
    widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    widget.field_name = field_name
    page.add_widget(widget)
    if option_label:
        page.insert_text((72, 80), option_label, fontsize=11)
    return doc.tobytes()


def _make_empty_pdf() -> bytes:
    """Create a minimal PDF with no widgets."""
    doc = fitz.open()
    doc.new_page()
    return doc.tobytes()


# ---------------------------------------------------------------------------
# extract_acroform_fields
# ---------------------------------------------------------------------------

class TestExtractAcroformFields:
    def test_extract_acroform_fields_from_fillable_pdf(self):
        pdf_bytes = _make_pdf_with_text_field("FirstName", "")
        fields = extract_acroform_fields(pdf_bytes)

        assert len(fields) == 1
        field = fields[0]
        assert field["field_name"] == "FirstName"
        assert field["field_type"] == "Text"
        assert field["current_value"] == ""
        assert field["page"] == 0

    def test_extract_acroform_fields_returns_current_value(self):
        pdf_bytes = _make_pdf_with_text_field("LastName", "Doe")
        fields = extract_acroform_fields(pdf_bytes)

        assert len(fields) == 1
        assert fields[0]["field_name"] == "LastName"
        assert fields[0]["current_value"] == "Doe"

    def test_extract_acroform_fields_empty_pdf(self):
        pdf_bytes = _make_empty_pdf()
        fields = extract_acroform_fields(pdf_bytes)
        assert fields == []

    def test_extract_acroform_fields_invalid_bytes(self):
        with pytest.raises(ValueError):
            extract_acroform_fields(b"not a pdf at all")

    def test_extract_acroform_fields_page_number_correct(self):
        """Multi-page PDF: widget on page 1 (index 0) should report page=0."""
        pdf_bytes = _make_pdf_with_text_field("FieldOnPage0")
        fields = extract_acroform_fields(pdf_bytes)
        assert fields[0]["page"] == 0

    def test_extract_acroform_fields_prefers_embedded_widget_label(self):
        pdf_bytes = _make_pdf_with_text_field(
            "Text Field0",
            field_label="Student Name",
        )
        fields = extract_acroform_fields(pdf_bytes)

        assert fields[0]["field_label"] == "Student Name"
        assert fields[0]["field_context"] == ""

    def test_extract_acroform_fields_uses_nearby_text_for_generic_names(self):
        pdf_bytes = _make_pdf_with_text_field(
            "Text Field0",
            drawn_label="Student Name",
        )
        fields = extract_acroform_fields(pdf_bytes)

        assert fields[0]["field_label"] == "Student Name"

    def test_extract_acroform_fields_extracts_checkbox_context(self):
        pdf_bytes = _make_pdf_with_checkbox(
            "Check Box0",
            option_label="Yes",
            question_text="Do you have any bank accounts outside the US?",
        )
        fields = extract_acroform_fields(pdf_bytes)

        assert fields[0]["field_label"] == "Yes"
        assert "bank accounts outside the US" in fields[0]["field_context"]


# ---------------------------------------------------------------------------
# fill_pdf_fields
# ---------------------------------------------------------------------------

class TestFillPdfFields:
    def test_fill_pdf_fields_writes_values(self):
        pdf_bytes = _make_pdf_with_text_field("FirstName", "")
        filled_bytes = fill_pdf_fields(pdf_bytes, {"FirstName": "Alice"})

        # Verify the value persisted in the returned bytes
        doc = fitz.open(stream=filled_bytes, filetype="pdf")
        widgets = list(doc[0].widgets())
        assert len(widgets) == 1
        assert widgets[0].field_name == "FirstName"
        assert widgets[0].field_value == "Alice"

    def test_fill_pdf_fields_ignores_unknown_fields(self):
        """Unknown field names in values dict should not raise an error."""
        pdf_bytes = _make_pdf_with_text_field("FirstName", "")
        # "NonExistentField" doesn't exist in the PDF — must not raise
        filled_bytes = fill_pdf_fields(
            pdf_bytes, {"FirstName": "Bob", "NonExistentField": "ignored"}
        )

        doc = fitz.open(stream=filled_bytes, filetype="pdf")
        widgets = list(doc[0].widgets())
        assert len(widgets) == 1
        assert widgets[0].field_value == "Bob"

    def test_fill_pdf_fields_invalid_bytes(self):
        with pytest.raises(ValueError):
            fill_pdf_fields(b"garbage bytes", {"Field": "value"})

    def test_fill_pdf_fields_returns_bytes(self):
        pdf_bytes = _make_pdf_with_text_field("Email", "")
        result = fill_pdf_fields(pdf_bytes, {"Email": "test@example.com"})
        assert isinstance(result, bytes)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# propose_field_values
# ---------------------------------------------------------------------------

MOCK_PROPOSALS = [
    {
        "field_name": "FirstName",
        "proposed_value": "Alice",
        "confidence": "high",
        "source": "passport",
    },
    {
        "field_name": "LastName",
        "proposed_value": "Smith",
        "confidence": "medium",
        "source": "inferred",
    },
]


class TestProposeFieldValues:
    def test_propose_field_values_calls_llm_and_returns_proposals(self):
        fields = [
            {"field_name": "FirstName", "field_type": "Text", "current_value": "", "page": 0},
            {"field_name": "LastName", "field_type": "Text", "current_value": "", "page": 0},
        ]
        context = "User is Alice Smith. Passport number: AB123456."

        with patch(
            "compliance_os.web.services.form_filler.extract_json",
            return_value={"fields": MOCK_PROPOSALS},
        ) as mock_extract:
            result = propose_field_values(fields, context)

        mock_extract.assert_called_once()
        # Verify system_prompt and user_prompt were keyword args
        call_kwargs = mock_extract.call_args.kwargs
        assert "system_prompt" in call_kwargs
        assert "user_prompt" in call_kwargs
        # Verify the function returns the fields array directly
        assert result == MOCK_PROPOSALS

    def test_propose_field_values_handles_empty_fields(self):
        """Empty fields list must return [] without calling LLM."""
        with patch(
            "compliance_os.web.services.form_filler.extract_json"
        ) as mock_extract:
            result = propose_field_values([], "some context")

        mock_extract.assert_not_called()
        assert result == []

    def test_propose_field_values_passes_instruction_in_prompt(self):
        fields = [
            {"field_name": "TaxID", "field_type": "Text", "current_value": "", "page": 0},
        ]
        with patch(
            "compliance_os.web.services.form_filler.extract_json",
            return_value={"fields": []},
        ) as mock_extract:
            propose_field_values(fields, "context text", instruction="Use formal names")

        call_kwargs = mock_extract.call_args.kwargs
        # Instruction must appear somewhere in the prompts
        combined = call_kwargs.get("system_prompt", "") + call_kwargs.get("user_prompt", "")
        assert "Use formal names" in combined

    def test_propose_field_values_passes_usage_context(self):
        fields = [
            {"field_name": "City", "field_type": "Text", "current_value": "", "page": 0},
        ]
        usage_ctx = {"operation": "form_fill_proposal", "user_id": "u1"}
        with patch(
            "compliance_os.web.services.form_filler.extract_json",
            return_value={"fields": []},
        ) as mock_extract:
            propose_field_values(fields, "context", usage_context=usage_ctx)

        call_kwargs = mock_extract.call_args.kwargs
        assert call_kwargs.get("usage_context") == usage_ctx
