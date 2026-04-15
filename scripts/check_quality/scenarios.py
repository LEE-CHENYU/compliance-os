"""Synthetic scenarios for each check service.

Each scenario is a (label, intake_data) pair. Scenarios span:
  - Happy paths (user should see a clean result)
  - Edge cases (boundary behavior)
  - Warning paths (known-bad intake)
  - Block paths (do-not-file situations)

No real PII; names and IDs are deliberately synthetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable


@dataclass
class Scenario:
    service: str
    label: str
    intake: dict[str, Any]
    today: date | None = None  # Frozen today for deterministic runs
    description: str = ""

    @property
    def case_id(self) -> str:
        return f"{self.service}__{self.label}"


# === H-1B Doc Check ===

def _h1b_packet_text(doc_type: str, **fields: str) -> str:
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
            ("Petitioner Name", "petitioner_name"),
            ("Beneficiary Name", "beneficiary_name"),
            ("Total Due Amount", "total_due_amount"),
        ],
        "h1b_filing_fee_receipt": [
            ("Transaction ID", "transaction_id"),
            ("Cardholder Name", "cardholder_name"),
            ("Amount", "amount"),
        ],
    }
    lines = [f"{label}: {fields[key]}" for label, key in label_map[doc_type] if key in fields]
    return "\n".join(lines) + "\n"


def _h1b_material_doc(order_id: str, doc_type: str, fields: dict, save_fn: Callable) -> dict:
    """Materialize synthetic text doc through the service's save_uploaded_document."""
    text = _h1b_packet_text(doc_type, **fields)
    filename = f"{doc_type}.txt"
    path = save_fn(order_id, filename, text.encode("utf-8"))
    return {"doc_type": doc_type, "filename": filename, "path": str(path)}


def h1b_scenarios() -> list[Scenario]:
    return [
        Scenario(
            service="h1b_doc_check",
            label="clean_packet",
            today=date(2026, 4, 1),
            description="All 5 H-1B docs consistent, petition window still open. Expect clean report with no findings.",
            intake={
                "_docs": [
                    ("h1b_registration", {
                        "registration_number": "H1B-2026-XYZ-001",
                        "employer_name": "Orbital Robotics Inc",
                        "employer_ein": "12-3456789",
                        "authorized_individual_name": "Alice Chen",
                        "authorized_individual_title": "VP Engineering",
                    }),
                    ("h1b_status_summary", {
                        "status_title": "Selected",
                        "registration_window_end_date": "2026-03-25",
                        "petition_filing_window_end_date": "2028-06-30",
                        "employment_start_date": "2028-10-01",
                        "law_firm_name": "Smith & Park LLP",
                    }),
                    ("h1b_g28", {
                        "representative_name": "Jane Smith",
                        "law_firm_name": "Smith & Park LLP",
                        "representative_email": "jsmith@smithpark.example",
                        "client_name": "Wei Zhang",
                        "client_entity_name": "Orbital Robotics Inc",
                        "client_email": "hr@orbital.example",
                    }),
                    ("h1b_filing_invoice", {
                        "invoice_number": "INV-2026-0042",
                        "petitioner_name": "Orbital Robotics Inc",
                        "beneficiary_name": "Wei Zhang",
                        "total_due_amount": "$2780",
                    }),
                    ("h1b_filing_fee_receipt", {
                        "transaction_id": "TXN-7891011",
                        "cardholder_name": "Alice Chen",
                        "amount": "$2780",
                    }),
                ],
            },
        ),
        Scenario(
            service="h1b_doc_check",
            label="entity_suffix_mismatch",
            today=date(2026, 4, 1),
            description="Registration says 'Orbital Robotics Inc' but invoice says 'Orbital Robotics LLC'. Subtle entity-type difference that USCIS will flag but may look like a typo to users.",
            intake={
                "_docs": [
                    ("h1b_registration", {
                        "registration_number": "H1B-2026-XYZ-002",
                        "employer_name": "Orbital Robotics Inc",
                        "authorized_individual_name": "Alice Chen",
                    }),
                    ("h1b_g28", {
                        "client_entity_name": "Orbital Robotics Inc",
                        "client_name": "Wei Zhang",
                    }),
                    ("h1b_filing_invoice", {
                        "petitioner_name": "Orbital Robotics LLC",
                        "beneficiary_name": "Wei Zhang",
                        "total_due_amount": "$2780",
                    }),
                    ("h1b_filing_fee_receipt", {
                        "cardholder_name": "Alice Chen",
                        "amount": "$2780",
                    }),
                ],
            },
        ),
        Scenario(
            service="h1b_doc_check",
            label="only_one_doc_uploaded",
            today=date(2026, 4, 1),
            description="User only uploaded registration. Expect 'incomplete' verdict with specific guidance on what's still needed, not a noise-filled cross-check report.",
            intake={
                "_docs": [
                    ("h1b_registration", {
                        "registration_number": "H1B-2026-SOLO",
                        "employer_name": "Solo Corp",
                        "authorized_individual_name": "Single Signer",
                    }),
                ],
            },
        ),
    ]


# === FBAR ===

def fbar_scenarios() -> list[Scenario]:
    return [
        Scenario(
            service="fbar_check",
            label="under_threshold_no_filing",
            description="Aggregate $7,500 across two accounts. User should walk away understanding they don't need to file.",
            intake={
                "tax_year": 2024,
                "accounts": [
                    {"institution_name": "ICBC", "country": "CN", "account_type": "savings",
                     "account_number_last4": "1234", "max_balance_usd": 4000},
                    {"institution_name": "Bank of China", "country": "CN", "account_type": "checking",
                     "account_number_last4": "5678", "max_balance_usd": 3500},
                ],
            },
        ),
        Scenario(
            service="fbar_check",
            label="over_threshold_must_file",
            description="Aggregate $21,700 across three accounts. User must file FinCEN 114.",
            intake={
                "tax_year": 2024,
                "accounts": [
                    {"institution_name": "HSBC HK", "country": "HK", "account_type": "savings",
                     "account_number_last4": "1111", "max_balance_usd": 8500},
                    {"institution_name": "Mizuho JP", "country": "JP", "account_type": "checking",
                     "account_number_last4": "2222", "max_balance_usd": 7200},
                    {"institution_name": "Barclays UK", "country": "GB", "account_type": "savings",
                     "account_number_last4": "3333", "max_balance_usd": 6000},
                ],
            },
        ),
        Scenario(
            service="fbar_check",
            label="fractional_boundary",
            description="Two accounts at $9,999.50 + $0.51 = $10,000.01. Must fire the threshold. Tests that fractional-dollar arithmetic is handled correctly after the v1 int() truncation bug.",
            intake={
                "tax_year": 2024,
                "accounts": [
                    {"institution_name": "SG Bank", "country": "SG", "account_type": "savings",
                     "account_number_last4": "7777", "max_balance_usd": 9999.50},
                    {"institution_name": "SG Bank", "country": "SG", "account_type": "savings",
                     "account_number_last4": "8888", "max_balance_usd": 0.51},
                ],
            },
        ),
    ]


# === Student Tax 1040-NR ===

def student_tax_scenarios() -> list[Scenario]:
    return [
        Scenario(
            service="student_tax_1040nr",
            label="clean_w2_only",
            description="F-1 student, $25K wages, federal withholding present, has SSN. Expect 0 findings and clean package.",
            intake={
                "tax_year": 2024,
                "full_name": "Wei Zhang",
                "visa_type": "F-1",
                "school_name": "Stanford University",
                "country_citizenship": "China",
                "country_passport": "China",
                "passport_number": "E12345678",
                "arrival_date": "2022-08-15",
                "days_present_current": 365,
                "days_present_year_1_ago": 365,
                "days_present_year_2_ago": 140,
                "taxpayer_id_number": "123-45-6789",
                "wage_income_usd": 25000,
                "federal_withholding_usd": 2500,
                "state_withholding_usd": 800,
            },
        ),
        Scenario(
            service="student_tax_1040nr",
            label="turbotax_user_no_itin",
            description="Used TurboTax (resident software), missing SSN/ITIN, $30K wages, $0 withholding. Multiple problems — severity and tone should reflect urgency.",
            intake={
                "tax_year": 2024,
                "full_name": "Raj Patel",
                "visa_type": "F-1",
                "school_name": "MIT",
                "country_citizenship": "India",
                "country_passport": "India",
                "passport_number": "M9876543",
                "arrival_date": "2023-08-20",
                "wage_income_usd": 30000,
                "federal_withholding_usd": 0,
                "used_resident_software": True,
                "taxpayer_id_number": "",
            },
        ),
        Scenario(
            service="student_tax_1040nr",
            label="treaty_multistate",
            description="F-1 student in NY working for CA employer, claiming China treaty benefit, has 1042-S, has SSN. Treaty + multi-state case — expect useful guidance, not alarmism.",
            intake={
                "tax_year": 2024,
                "full_name": "Li Wen",
                "visa_type": "F-1",
                "school_name": "Columbia University",
                "country_citizenship": "China",
                "country_passport": "China",
                "passport_number": "E22334455",
                "arrival_date": "2022-08-15",
                "taxpayer_id_number": "987-65-4321",
                "wage_income_usd": 22000,
                "federal_withholding_usd": 1100,
                "state_withholding_usd": 200,
                "claim_treaty_benefit": True,
                "treaty_country": "China",
                "treaty_article": "20(c)",
                "has_1042s": True,
                "state_of_residence": "NY",
                "state_of_employer": "CA",
            },
        ),
    ]


# === 83(b) Election ===

def election_83b_scenarios() -> list[Scenario]:
    today = date(2026, 4, 1)
    return [
        Scenario(
            service="election_83b",
            label="normal_grant",
            today=today,
            description="Grant 5 days ago in Palo Alto, CA. Should be a clean pass with 25 days remaining.",
            intake={
                "grant_date": (today - timedelta(days=5)).isoformat(),
                "taxpayer_name": "Jordan Park",
                "taxpayer_address": "1 Market St, Palo Alto, CA 94301",
                "company_name": "MyStartup Inc",
                "property_description": "100,000 shares of restricted common stock",
                "share_count": 100000,
                "fair_market_value_per_share": 0.001,
                "exercise_price_per_share": 0.001,
                "vesting_schedule": "4 years with 1-year cliff, monthly thereafter",
            },
        ),
        Scenario(
            service="election_83b",
            label="deadline_passed",
            today=today,
            description="Grant 45 days ago. Deadline passed 15 days ago. Critical scenario — user must NOT be encouraged to mail the packet, they need to talk to an advisor.",
            intake={
                "grant_date": (today - timedelta(days=45)).isoformat(),
                "taxpayer_name": "Late Filer",
                "taxpayer_address": "100 Broadway, New York, NY 10001",
                "company_name": "Delayed Co",
                "property_description": "50,000 shares of restricted common stock",
                "share_count": 50000,
                "fair_market_value_per_share": 0.01,
                "exercise_price_per_share": 0.01,
                "vesting_schedule": "4 years",
            },
        ),
        Scenario(
            service="election_83b",
            label="texas_service_center",
            today=today,
            description="Austin, TX address. Cover sheet should include Austin IRS service center, not a generic fallback message.",
            intake={
                "grant_date": (today - timedelta(days=10)).isoformat(),
                "taxpayer_name": "Dallas Founder",
                "taxpayer_address": "1 Congress Ave, Austin, TX 78701",
                "company_name": "TexCo Inc",
                "property_description": "10,000 shares of restricted stock",
                "share_count": 10000,
                "fair_market_value_per_share": 0.005,
                "exercise_price_per_share": 0.005,
                "vesting_schedule": "4 years, no cliff",
            },
        ),
    ]


def all_scenarios() -> list[Scenario]:
    return (
        h1b_scenarios()
        + fbar_scenarios()
        + student_tax_scenarios()
        + election_83b_scenarios()
    )
