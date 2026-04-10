"""Tests for Form 8843 mailing guidance."""

from __future__ import annotations


def test_build_form_8843_filing_context_for_standalone_mail():
    from compliance_os.web.services.mailing_service import build_form_8843_filing_context

    context = build_form_8843_filing_context({"filing_with_tax_return": False})

    assert context["scenario"] == "standalone_mail"
    assert context["mail_required"] is True
    assert context["can_mark_mailed"] is True
    assert context["deadline_label"] == "June 15, 2026"
    assert "Austin, TX 73301-0215" in context["address_block"]


def test_build_form_8843_filing_context_for_tax_package():
    from compliance_os.web.services.mailing_service import build_form_8843_filing_context

    context = build_form_8843_filing_context({"filing_with_tax_return": True})

    assert context["scenario"] == "tax_return_package"
    assert context["mail_required"] is False
    assert context["can_mark_mailed"] is False
    assert context["deadline_label"] == "April 15, 2026"
    assert context["address_block"] == ""
