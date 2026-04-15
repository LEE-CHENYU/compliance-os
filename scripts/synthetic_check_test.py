"""Run each marketplace check end-to-end with synthetic intake.

Goal: examine whether each check produces sensible output. Not a unit test —
prints findings and report excerpts so a human can eyeball the result.

Run: python scripts/synthetic_check_test.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import textwrap
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compliance_os.web.services.election_83b import process_election_83b
from compliance_os.web.services.fbar_check import process_fbar_check
from compliance_os.web.services.h1b_doc_check import (
    H1B_DOC_CHECK_DIR,
    process_h1b_doc_check,
    save_uploaded_document,
)
from compliance_os.web.services.student_tax_check import process_student_tax_check


SEPARATOR = "=" * 78


def banner(label: str) -> None:
    print(f"\n{SEPARATOR}\n{label}\n{SEPARATOR}")


def dump_findings(findings: list[dict]) -> None:
    if not findings:
        print("  (no findings)")
        return
    for f in findings:
        sev = f.get("severity", "?").upper()
        print(f"  [{sev}] {f.get('title')}")
        action = f.get("action") or ""
        print(f"        -> {textwrap.shorten(action, width=120)}")


# ---------- H-1B Doc Check ----------

def make_h1b_text_doc(doc_type: str, **fields: str) -> str:
    """Build a synthetic text 'document' in the format the regex expects."""
    label_map = {
        "h1b_registration": [
            ("Registration Number", "registration_number"),
            ("Employer Name", "employer_name"),
            ("Employer EIN", "employer_ein"),
            ("Authorized Individual Name", "authorized_individual_name"),
            ("Authorized Individual Title", "authorized_individual_title"),
        ],
        "h1b_status_summary": [
            ("Status Title", "status_title"),
            ("Registration Window End Date", "registration_window_end_date"),
            ("Petition Filing Window End Date", "petition_filing_window_end_date"),
            ("Employment Start Date", "employment_start_date"),
            ("Law Firm Name", "law_firm_name"),
        ],
        "h1b_g28": [
            ("Representative Name", "representative_name"),
            ("Law Firm Name", "law_firm_name"),
            ("Representative Email", "representative_email"),
            ("Client Name", "client_name"),
            ("Client Entity Name", "client_entity_name"),
            ("Client Email", "client_email"),
        ],
        "h1b_filing_invoice": [
            ("Invoice Number", "invoice_number"),
            ("Invoice Date", "invoice_date"),
            ("Petitioner Name", "petitioner_name"),
            ("Beneficiary Name", "beneficiary_name"),
            ("Total Due Amount", "total_due_amount"),
        ],
        "h1b_filing_fee_receipt": [
            ("Transaction ID", "transaction_id"),
            ("Transaction Date", "transaction_date"),
            ("Response Message", "response_message"),
            ("Approval Code", "approval_code"),
            ("Cardholder Name", "cardholder_name"),
            ("Amount", "amount"),
            ("Description", "description"),
        ],
    }
    lines = []
    for label, key in label_map[doc_type]:
        if key in fields and fields[key] is not None:
            lines.append(f"{label}: {fields[key]}")
    return "\n".join(lines) + "\n"


def run_h1b_clean() -> None:
    """All documents internally consistent for Acme Robotics Inc."""
    banner("H-1B Doc Check — clean packet (should produce few/no findings)")
    order_id = "test-h1b-clean"
    docs = [
        ("h1b_registration", "registration.txt", make_h1b_text_doc(
            "h1b_registration",
            registration_number="H1B-2024-XYZ-001",
            employer_name="Acme Robotics Inc",
            employer_ein="12-3456789",
            authorized_individual_name="Alice Chen",
            authorized_individual_title="VP of Engineering",
        )),
        ("h1b_status_summary", "status.txt", make_h1b_text_doc(
            "h1b_status_summary",
            status_title="Selected",
            registration_window_end_date="2024-03-25",
            petition_filing_window_end_date="2024-06-30",
            employment_start_date="2024-10-01",
            law_firm_name="Smith & Park LLP",
        )),
        ("h1b_g28", "g28.txt", make_h1b_text_doc(
            "h1b_g28",
            representative_name="Jane Smith",
            law_firm_name="Smith & Park LLP",
            representative_email="jsmith@smithpark.example",
            client_name="Wei Zhang",
            client_entity_name="Acme Robotics Inc",
            client_email="hr@acmerobotics.example",
        )),
        ("h1b_filing_invoice", "invoice.txt", make_h1b_text_doc(
            "h1b_filing_invoice",
            invoice_number="INV-2024-0042",
            invoice_date="2024-04-10",
            petitioner_name="Acme Robotics Inc",
            beneficiary_name="Wei Zhang",
            total_due_amount="$2780",
        )),
        ("h1b_filing_fee_receipt", "receipt.txt", make_h1b_text_doc(
            "h1b_filing_fee_receipt",
            transaction_id="TXN-7891011",
            transaction_date="2024-04-11",
            response_message="Approved",
            approval_code="OK-998877",
            cardholder_name="Alice Chen",
            amount="$2780",
            description="USCIS H-1B filing fee",
        )),
    ]
    documents = []
    for doc_type, filename, text in docs:
        path = save_uploaded_document(order_id, filename, text.encode("utf-8"))
        documents.append({"doc_type": doc_type, "filename": filename, "path": str(path)})

    result = process_h1b_doc_check(order_id, {"documents": documents})
    print(f"summary: {result['summary']}")
    print(f"finding_count: {result['finding_count']}")
    dump_findings(result["findings"])
    print("\nExtraction sample (h1b_registration):")
    print("  " + json.dumps(result["document_summary"][0]["fields"], indent=2).replace("\n", "\n  "))


def run_h1b_mismatch() -> None:
    """Cardholder ≠ authorized signatory; petitioner ≠ employer; amount mismatch."""
    banner("H-1B Doc Check — mismatched packet (should fire mismatch rules)")
    order_id = "test-h1b-mismatch"
    docs = [
        ("h1b_registration", "registration.txt", make_h1b_text_doc(
            "h1b_registration",
            registration_number="H1B-2024-XYZ-002",
            employer_name="Acme Robotics Inc",
            authorized_individual_name="Alice Chen",
        )),
        ("h1b_filing_invoice", "invoice.txt", make_h1b_text_doc(
            "h1b_filing_invoice",
            petitioner_name="Acme Robotics LLC",  # subtle entity change
            beneficiary_name="Wei Zhang",
            total_due_amount="$2780",
        )),
        ("h1b_filing_fee_receipt", "receipt.txt", make_h1b_text_doc(
            "h1b_filing_fee_receipt",
            cardholder_name="Bob Wong",  # different from Alice Chen
            amount="$1500",  # mismatched amount
        )),
    ]
    documents = []
    for doc_type, filename, text in docs:
        path = save_uploaded_document(order_id, filename, text.encode("utf-8"))
        documents.append({"doc_type": doc_type, "filename": filename, "path": str(path)})

    result = process_h1b_doc_check(order_id, {"documents": documents})
    print(f"summary: {result['summary']}")
    print(f"finding_count: {result['finding_count']}")
    dump_findings(result["findings"])
    print("\nComparisons:")
    for c in result["comparisons"]:
        print(f"  {c.get('field')}: status={c.get('status')} ({c.get('value_a')!r} vs {c.get('value_b')!r})")


def run_h1b_real_pdf() -> None:
    """Upload an actual PDF — should now use PyMuPDF to extract text."""
    banner("H-1B Doc Check — real PDF upload (after fix, should extract fields)")
    order_id = "test-h1b-pdf"
    # Build a real PDF using the same builder the service uses for reports.
    from compliance_os.web.services.pdf_builder import build_text_pdf
    pdf_bytes = build_text_pdf(
        "H-1B Registration Notice",
        [
            "Registration Number: H1B-2026-REAL-001",
            "Employer Name: PDF Corp Inc",
            "Employer EIN: 98-7654321",
            "Authorized Individual Name: Carlos Reyes",
            "Authorized Individual Title: General Counsel",
        ],
    )
    path = save_uploaded_document(order_id, "registration.pdf", pdf_bytes)
    documents = [{"doc_type": "h1b_registration", "filename": "registration.pdf", "path": str(path)}]
    result = process_h1b_doc_check(order_id, {"documents": documents})
    print(f"summary: {result['summary']}")
    print("Extraction from real PDF:")
    print("  " + json.dumps(result["document_summary"][0]["fields"], indent=2).replace("\n", "\n  "))


# ---------- FBAR ----------

def run_fbar_below_threshold() -> None:
    banner("FBAR — accounts under $10K aggregate (should NOT require)")
    result = process_fbar_check("test-fbar-below", {
        "tax_year": 2024,
        "accounts": [
            {"institution_name": "Bank of China", "country": "CN", "account_type": "savings",
             "account_number_last4": "1234", "max_balance_usd": 4000},
            {"institution_name": "ICBC", "country": "CN", "account_type": "checking",
             "account_number_last4": "5678", "max_balance_usd": 3500},
        ],
    })
    print(f"summary: {result['summary']}")
    print(f"requires_fbar: {result['requires_fbar']}")
    print(f"aggregate: ${result['aggregate_max_balance_usd']:,}")
    print(f"deadline: {result['filing_deadline']}")
    print("Next steps:")
    for s in result["next_steps"]:
        print(f"  - {s}")


def run_fbar_above_threshold() -> None:
    banner("FBAR — accounts over $10K aggregate (should require)")
    result = process_fbar_check("test-fbar-above", {
        "tax_year": 2024,
        "accounts": [
            {"institution_name": "Bank of China", "country": "CN", "account_type": "savings",
             "account_number_last4": "1234", "max_balance_usd": 8500},
            {"institution_name": "Mizuho Japan", "country": "JP", "account_type": "checking",
             "account_number_last4": "5678", "max_balance_usd": 7200},
        ],
    })
    print(f"summary: {result['summary']}")
    print(f"requires_fbar: {result['requires_fbar']}")
    print(f"aggregate: ${result['aggregate_max_balance_usd']:,}")
    print(f"deadline: {result['filing_deadline']}")


def run_fbar_edge_exactly_10k() -> None:
    banner("FBAR — exactly $10,000 (boundary check)")
    result = process_fbar_check("test-fbar-10k", {
        "tax_year": 2024,
        "accounts": [{"institution_name": "X", "country": "CN", "account_type": "savings",
                      "account_number_last4": "0000", "max_balance_usd": 10000}],
    })
    print(f"requires_fbar at exactly $10,000: {result['requires_fbar']}")
    print(f">>> NOTE: rule is `aggregate > 10000`. The actual FinCEN threshold is 'exceeded $10,000 at any time' so > is correct.")


# ---------- Student Tax 1040-NR ----------

def run_student_tax_basic() -> None:
    banner("Student Tax 1040-NR — basic case with W-2 income")
    result = process_student_tax_check("test-student-tax-basic", {
        "tax_year": 2024,
        "full_name": "Wei Zhang",
        "visa_type": "F-1",
        "school_name": "Stanford University",
        "school_address": "450 Serra Mall, Stanford, CA 94305",
        "school_contact": "International Student Office",
        "program_director": "Dr. Smith",
        "country_citizenship": "China",
        "country_passport": "China",
        "passport_number": "E12345678",
        "arrival_date": "2022-08-15",
        "days_present_current": 365,
        "days_present_year_1_ago": 365,
        "days_present_year_2_ago": 140,
        "wage_income_usd": 25000,
        "scholarship_income_usd": 0,
        "other_income_usd": 0,
        "federal_withholding_usd": 2200,
        "state_withholding_usd": 800,
        "claim_treaty_benefit": False,
    })
    print(f"summary: {result['summary']}")
    print(f"finding_count: {result['finding_count']}")
    dump_findings(result["findings"])
    print(f"deadline: {result['filing_deadline']}")
    print(f"artifacts: {[a['filename'] for a in result['artifacts']]}")


def run_student_tax_resident_software_warning() -> None:
    banner("Student Tax 1040-NR — used resident software (should flag)")
    result = process_student_tax_check("test-student-tax-turbotax", {
        "tax_year": 2024,
        "full_name": "Test User",
        "school_name": "MIT",
        "country_citizenship": "India",
        "wage_income_usd": 30000,
        "federal_withholding_usd": 0,  # also no withholding
        "used_resident_software": True,
    })
    print(f"finding_count: {result['finding_count']}")
    dump_findings(result["findings"])


def run_student_tax_zero_income() -> None:
    banner("Student Tax 1040-NR — zero income (should suggest free Form 8843)")
    result = process_student_tax_check("test-student-tax-zero", {
        "tax_year": 2024,
        "full_name": "Test User",
        "school_name": "Berkeley",
        "country_citizenship": "Brazil",
    })
    print(f"finding_count: {result['finding_count']}")
    dump_findings(result["findings"])


def run_student_tax_treaty_no_country() -> None:
    banner("Student Tax 1040-NR — treaty claim without country (should flag)")
    result = process_student_tax_check("test-student-tax-treaty", {
        "tax_year": 2024,
        "full_name": "Test User",
        "school_name": "NYU",
        "country_citizenship": "India",
        "wage_income_usd": 18000,
        "federal_withholding_usd": 1500,
        "claim_treaty_benefit": True,
        "treaty_country": "",  # missing
        "treaty_article": "21(2)",
    })
    print(f"finding_count: {result['finding_count']}")
    dump_findings(result["findings"])


# ---------- 83(b) Election ----------

def run_83b_normal() -> None:
    banner("83(b) Election — grant 5 days ago (should give 25-day deadline)")
    grant = (date.today() - timedelta(days=5)).isoformat()
    result = process_election_83b("test-83b-normal", {
        "grant_date": grant,
        "taxpayer_name": "Wei Zhang",
        "taxpayer_address": "123 Main St, Palo Alto, CA 94301",
        "company_name": "Startup Inc",
        "property_description": "100,000 shares of restricted common stock",
        "share_count": 100000,
        "fair_market_value_per_share": 0.001,
        "exercise_price_per_share": 0.001,
        "vesting_schedule": "4 years with 1-year cliff, monthly vesting after",
    })
    print(f"summary: {result['summary']}")
    print(f"deadline: {result['filing_deadline']}  (should be {(date.today() - timedelta(days=5) + timedelta(days=30)).isoformat()})")
    print("Next steps:")
    for s in result["next_steps"]:
        print(f"  - {s}")


def run_83b_already_late() -> None:
    banner("83(b) Election — grant 45 days ago (deadline passed — should block + warn)")
    grant = (date.today() - timedelta(days=45)).isoformat()
    result = process_election_83b("test-83b-late", {
        "grant_date": grant,
        "taxpayer_name": "Late Person",
        "taxpayer_address": "1 Late St, Palo Alto, CA 94301",
        "company_name": "Late Co",
        "property_description": "1000 shares",
        "share_count": 1000,
        "fair_market_value_per_share": 0.01,
        "exercise_price_per_share": 0.01,
        "vesting_schedule": "4 years",
    })
    print(f"verdict: {result.get('verdict')}")
    print(f"deadline_passed: {result.get('deadline_passed')}")
    print(f"days_past_deadline: {result.get('days_past_deadline')}")
    print(f"summary: {result['summary']}")
    print(f"mailing headline: {result['mailing_instructions']['headline']}")


def run_83b_future_grant() -> None:
    banner("83(b) Election — grant date in the future (should block)")
    grant = (date.today() + timedelta(days=10)).isoformat()
    result = process_election_83b("test-83b-future", {
        "grant_date": grant,
        "taxpayer_name": "Premature Filer",
        "taxpayer_address": "1 Early St, Austin, TX 78701",
        "company_name": "Early Co",
        "property_description": "500 shares",
        "share_count": 500,
        "fair_market_value_per_share": 0.01,
        "exercise_price_per_share": 0.01,
        "vesting_schedule": "4 years",
    })
    print(f"verdict: {result.get('verdict')}")
    print(f"grant_in_future: {result.get('grant_in_future')}")
    print(f"summary: {result['summary']}")


def run_83b_service_center() -> None:
    banner("83(b) Election — service-center inference from taxpayer address")
    grant = (date.today() - timedelta(days=5)).isoformat()
    base = {
        "grant_date": grant,
        "taxpayer_name": "Test User",
        "company_name": "Co",
        "property_description": "100 shares",
        "share_count": 100,
        "fair_market_value_per_share": 0.01,
        "exercise_price_per_share": 0.01,
        "vesting_schedule": "4 years",
    }
    cases = [
        ("CA (Ogden)", "1 Market St, Palo Alto, CA 94301"),
        ("NY (Kansas City)", "1 Broadway, New York, NY 10004"),
        ("TX (Austin)", "1 Congress Ave, Austin, TX 78701"),
        ("No state (fallback)", "some address without a state"),
    ]
    for label, addr in cases:
        result = process_election_83b(f"test-83b-sc-{label}", {**base, "taxpayer_address": addr})
        # Re-read the cover sheet to show the inferred center
        from pathlib import Path as _P
        # Just inspect the summary/mailing_instructions
        print(f"{label}: mailing headline = {result['mailing_instructions']['headline']}")


# ---------- Run everything ----------

if __name__ == "__main__":
    run_h1b_clean()
    run_h1b_mismatch()
    run_h1b_real_pdf()
    run_fbar_below_threshold()
    run_fbar_above_threshold()
    run_fbar_edge_exactly_10k()
    run_student_tax_basic()
    run_student_tax_resident_software_warning()
    run_student_tax_zero_income()
    run_student_tax_treaty_no_country()
    run_83b_normal()
    run_83b_already_late()
    run_83b_future_grant()
    run_83b_service_center()
    print(f"\n{SEPARATOR}\nDone. Synthetic test artifacts in {H1B_DOC_CHECK_DIR.parent}\n{SEPARATOR}")
