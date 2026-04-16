"""Tests for the Guardian MCP server tools."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    """Run an async tool synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)

from compliance_os.mcp_server import (
    batch_upload,
    classify_document,
    generate_form_8843,
    get_filing_guidance,
    guardian_ask,
    guardian_deadlines,
    guardian_documents,
    guardian_risks,
    guardian_status,
    index_documents,
    parse_document,
    run_compliance_check,
    upload_document,
)


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "pdfs"


class TestLocalDocumentTools:

    def test_parse_pdf(self):
        pdf_path = TEMPLATE_DIR / "form_8843_template.pdf"
        if not pdf_path.exists():
            pytest.skip("Template PDF not available")
        result = parse_document(file_path=str(pdf_path))
        assert "Form 8843" in result
        assert len(result) > 100

    def test_parse_missing_file(self):
        result = parse_document(file_path="/nonexistent/file.pdf")
        assert "not found" in result.lower()

    def test_parse_unsupported_type(self):
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            result = parse_document(file_path=path)
            assert "unsupported" in result.lower()
        finally:
            os.unlink(path)

    def test_parse_text_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("Hello, Guardian!")
            path = f.name
        try:
            result = parse_document(file_path=path)
            assert result == "Hello, Guardian!"
        finally:
            os.unlink(path)

    def test_classify_pdf(self):
        pdf_path = TEMPLATE_DIR / "form_8843_template.pdf"
        if not pdf_path.exists():
            pytest.skip("Template PDF not available")
        result = json.loads(classify_document(file_path=str(pdf_path)))
        assert "file" in result
        assert "doc_type" in result

    def test_classify_missing_file(self):
        result = json.loads(classify_document(file_path="/nonexistent/file.pdf"))
        assert "error" in result


class TestFormFilingTools:

    def test_generate_form_8843_success(self):
        result = json.loads(
            generate_form_8843(
                full_name="Test User",
                country_citizenship="China",
                visa_type="F-1",
                arrival_date="2022-08-15",
                days_present_current=183,
                school_name="MIT",
            )
        )
        assert result["status"] == "success"
        assert result["pdf_size_bytes"] > 0
        assert result["filing_guidance"]["scenario"] in ("standalone_mail", "tax_return_package")

    def test_generate_form_8843_with_tax_return(self):
        result = json.loads(
            generate_form_8843(
                full_name="Jane Doe",
                country_citizenship="India",
                visa_type="F-1",
                arrival_date="2021-01-10",
                days_present_current=365,
                tax_year=2025,
            )
        )
        assert result["status"] == "success"
        assert "deadline" in result["filing_guidance"]

    def test_get_filing_guidance_form_8843(self):
        result = json.loads(
            get_filing_guidance(form_type="form_8843", filing_with_tax_return=False)
        )
        assert "filing_context" in result
        assert result["filing_context"]["scenario"] == "standalone_mail"
        assert result["mailing_kit"]["address_block"]

    def test_get_filing_guidance_unknown(self):
        result = json.loads(get_filing_guidance(form_type="unknown_form"))
        assert "error" in result

    def test_run_compliance_check_fbar(self):
        inputs = {
            "accounts": [
                {"institution_name": "Bank of China", "country": "China", "max_balance_usd": 5000},
                {"institution_name": "MUFG", "country": "Japan", "max_balance_usd": 8000},
            ]
        }
        result = json.loads(
            run_compliance_check(
                check_type="fbar",
                inputs_json=json.dumps(inputs),
            )
        )
        assert result.get("aggregate_max_balance_usd") == 13000.0

    def test_run_compliance_check_unknown_type(self):
        result = json.loads(
            run_compliance_check(check_type="nonexistent", inputs_json="{}")
        )
        assert "error" in result
        assert "available" in result

    def test_run_compliance_check_bad_json(self):
        result = json.loads(
            run_compliance_check(check_type="fbar", inputs_json="not json")
        )
        assert "error" in result


class TestContextToolsOffline:
    """Context tools call the Guardian API — test error handling when offline."""

    @patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock, side_effect=RuntimeError("Connection refused"))
    def test_status_offline(self, mock_get):
        result = _run(guardian_status())
        assert "Error" in result

    @patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock, side_effect=RuntimeError("Connection refused"))
    def test_deadlines_offline(self, mock_get):
        result = _run(guardian_deadlines())
        assert "Error" in result

    @patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock, side_effect=RuntimeError("Connection refused"))
    def test_risks_offline(self, mock_get):
        result = _run(guardian_risks())
        assert "Error" in result

    @patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock, side_effect=RuntimeError("Connection refused"))
    def test_documents_offline(self, mock_get):
        result = _run(guardian_documents())
        assert "Error" in result

    @patch("compliance_os.mcp_server._api_post", new_callable=AsyncMock, side_effect=RuntimeError("Connection refused"))
    def test_ask_offline(self, mock_post):
        result = _run(guardian_ask(question="When is my FBAR due?"))
        assert "Error" in result


class TestContextToolsMocked:
    """Test context tools with mocked API responses."""

    @patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock)
    def test_status_full(self, mock_get):
        mock_get.side_effect = [
            {
                "findings": [
                    {"severity": "critical", "title": "I-983 overdue", "action": "File immediately"},
                    {"severity": "warning", "title": "FBAR due soon", "action": "File by April 15"},
                ],
                "deadlines": [
                    {"title": "FBAR", "date": "2026-04-15", "days": 30},
                ],
                "key_facts": [
                    {"label": "Visa", "value": "F-1"},
                ],
            },
            {"documents": 12, "risks": 2},
            [{"chain_type": "employment", "display_name": "Google LLC", "start_date": "2024-01-15"}],
        ]
        result = _run(guardian_status())
        assert "Critical Issues" in result
        assert "I-983 overdue" in result
        assert "FBAR due soon" in result
        assert "Documents: 12" in result
        assert "Google LLC" in result

    @patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock)
    def test_deadlines_sorted(self, mock_get):
        mock_get.return_value = {
            "deadlines": [
                {"title": "FBAR", "date": "2026-04-15", "days": 30},
                {"title": "I-983", "date": "2026-03-01", "days": -15},
                {"title": "Tax return", "date": "2026-10-15", "days": 183},
            ],
        }
        result = _run(guardian_deadlines())
        lines = result.strip().split("\n")
        assert "OVERDUE" in lines[2]
        assert "30 days" in lines[3]
        assert "183 days" in lines[4]

    @patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock)
    def test_documents_empty(self, mock_get):
        mock_get.side_effect = [[], []]
        result = _run(guardian_documents())
        assert "No documents" in result

    @patch("compliance_os.mcp_server._api_post", new_callable=AsyncMock)
    def test_ask_returns_reply(self, mock_post):
        mock_post.return_value = {"reply": "Your FBAR is due April 15, 2026."}
        result = _run(guardian_ask(question="When is my FBAR due?"))
        assert "April 15" in result


class TestGmailToolsOffline:
    """Gmail tools require OAuth — test graceful error handling."""

    @patch(
        "compliance_os.mcp_server._get_gmail_service",
        side_effect=FileNotFoundError("Gmail credentials not found"),
    )
    def test_search_no_credentials(self, mock_svc):
        result = json.loads(gmail_search(query="from:irs.gov"))
        assert "error" in result

    @patch(
        "compliance_os.mcp_server._get_gmail_service",
        side_effect=FileNotFoundError("Gmail credentials not found"),
    )
    def test_read_no_credentials(self, mock_svc):
        from compliance_os.mcp_server import gmail_read
        result = json.loads(gmail_read(message_id="abc123"))
        assert "error" in result


class TestUploadTools:

    def test_upload_missing_file(self):
        result = json.loads(upload_document(file_path="/nonexistent/file.pdf"))
        assert "error" in result

    @patch("compliance_os.mcp_server._upload_single_file", return_value={"ok": True, "doc_type": "w2"})
    def test_upload_success(self, mock_upload):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-test")
            path = f.name
        try:
            result = json.loads(upload_document(file_path=path))
            assert result.get("ok") is True
        finally:
            os.unlink(path)

    def test_batch_upload_not_a_directory(self):
        result = json.loads(batch_upload(directory="/nonexistent/dir"))
        assert "error" in result

    def test_batch_upload_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            result = json.loads(batch_upload(directory=d))
            assert "error" in result
            assert "No files found" in result["error"]

    @patch("compliance_os.mcp_server._upload_single_file", return_value={"ok": True, "doc_type": "w2"})
    def test_batch_upload_success(self, mock_upload):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "w2_2024.pdf").write_bytes(b"%PDF-test")
            (Path(d) / "i20.pdf").write_bytes(b"%PDF-test")
            (Path(d) / "notes.txt").write_text("hello")
            (Path(d) / "photo.jpg").write_bytes(b"jpg")  # should be skipped
            result = json.loads(batch_upload(directory=d, extensions=".pdf,.txt"))
            assert "3 uploaded" in result["summary"]
            assert len(result["results"]) == 3


class TestIndexDocuments:

    def test_index_missing_openai_key(self):
        """Indexer needs OPENAI_API_KEY — graceful error when missing."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            result = json.loads(index_documents(directory="nonexistent"))
            # Either succeeds with 0 docs or errors gracefully
            assert "error" in result or result.get("indexed", 0) == 0


# Import for the gmail offline tests
from compliance_os.mcp_server import gmail_search
