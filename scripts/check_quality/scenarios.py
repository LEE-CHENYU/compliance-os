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


def h1b_diversity_scenarios() -> list[Scenario]:
    """H-1B shapes not covered by the original set."""
    return [
        Scenario(
            service="h1b_doc_check",
            label="partial_4_of_5",
            today=date(2026, 4, 1),
            description="4 of 5 documents uploaded (status summary missing). Should not produce noise findings for the missing doc, and cross-checks for uploaded docs should run.",
            intake={
                "_docs": [
                    ("h1b_registration", {
                        "registration_number": "H1B-2026-PART-004",
                        "employer_name": "Nova Systems Corp",
                        "authorized_individual_name": "Sarah Kim",
                    }),
                    ("h1b_g28", {
                        "client_entity_name": "Nova Systems Corp",
                        "client_name": "Arjun Sharma",
                    }),
                    ("h1b_filing_invoice", {
                        "petitioner_name": "Nova Systems Corp",
                        "beneficiary_name": "Arjun Sharma",
                        "total_due_amount": "$3460",
                    }),
                    ("h1b_filing_fee_receipt", {
                        "cardholder_name": "Sarah Kim",
                        "amount": "$3460",
                    }),
                ],
            },
        ),
        Scenario(
            service="h1b_doc_check",
            label="amendment_employer_change",
            today=date(2026, 4, 1),
            description="Amendment filing where the beneficiary changed employers after H-1B approval. Invoice names the NEW employer; the original registration document was from the previous employer. Tricky cross-check case.",
            intake={
                "_docs": [
                    ("h1b_registration", {
                        "registration_number": "H1B-2024-OLD-777",
                        "employer_name": "Legacy Tech Inc",
                        "authorized_individual_name": "Bob Previous",
                    }),
                    ("h1b_status_summary", {
                        "status_title": "Amended",
                        "petition_filing_window_end_date": "2028-06-30",
                        "employment_start_date": "2026-05-01",
                    }),
                    ("h1b_g28", {
                        "client_entity_name": "NewCo Robotics Inc",
                        "client_name": "Carlos Rivera",
                    }),
                    ("h1b_filing_invoice", {
                        "petitioner_name": "NewCo Robotics Inc",
                        "beneficiary_name": "Carlos Rivera",
                        "total_due_amount": "$4660",
                    }),
                    ("h1b_filing_fee_receipt", {
                        "cardholder_name": "Dana NewEmployer",
                        "amount": "$4660",
                    }),
                ],
            },
        ),
        Scenario(
            service="h1b_doc_check",
            label="amount_off_by_ten",
            today=date(2026, 4, 1),
            description="Invoice and receipt differ by $10 ($2780 vs $2790) — within rounding error but technically different. Severity / tone needs to match reality (probably a data-entry typo, not a rejection trigger).",
            intake={
                "_docs": [
                    ("h1b_registration", {
                        "registration_number": "H1B-2026-ROUND-1",
                        "employer_name": "Round Numbers Inc",
                        "authorized_individual_name": "Alice Payer",
                    }),
                    ("h1b_g28", {
                        "client_entity_name": "Round Numbers Inc",
                        "client_name": "Lee Beneficiary",
                    }),
                    ("h1b_filing_invoice", {
                        "petitioner_name": "Round Numbers Inc",
                        "beneficiary_name": "Lee Beneficiary",
                        "total_due_amount": "$2780",
                    }),
                    ("h1b_filing_fee_receipt", {
                        "cardholder_name": "Alice Payer",
                        "amount": "$2790",
                    }),
                ],
            },
        ),
    ]


def fbar_diversity_scenarios() -> list[Scenario]:
    return [
        Scenario(
            service="fbar_check",
            label="fatca_overlap",
            description="Aggregate $125,000 — well above FBAR $10K threshold AND above single-filer Form 8938 $50K threshold. Report should distinguish FBAR (FinCEN) from Form 8938 (IRS) since both are triggered.",
            intake={
                "tax_year": 2024,
                "accounts": [
                    {"institution_name": "HSBC HK", "country": "HK", "account_type": "savings",
                     "account_number_last4": "1111", "max_balance_usd": 75000},
                    {"institution_name": "Mizuho JP", "country": "JP", "account_type": "checking",
                     "account_number_last4": "2222", "max_balance_usd": 50000},
                ],
            },
        ),
        Scenario(
            service="fbar_check",
            label="foreign_currency_balances",
            description="Three accounts in local currency: €4,000, ¥1,200,000, £3,500. User provides USD-converted balances. Output should address the currency-conversion requirement without implying the user's conversions are authoritative.",
            intake={
                "tax_year": 2024,
                "accounts": [
                    {"institution_name": "Deutsche Bank", "country": "DE", "account_type": "savings",
                     "account_number_last4": "3001", "max_balance_usd": 4300},
                    {"institution_name": "Mizuho", "country": "JP", "account_type": "checking",
                     "account_number_last4": "3002", "max_balance_usd": 7900},
                    {"institution_name": "Barclays", "country": "GB", "account_type": "savings",
                     "account_number_last4": "3003", "max_balance_usd": 4400},
                ],
            },
        ),
    ]


def student_tax_diversity_scenarios() -> list[Scenario]:
    return [
        Scenario(
            service="student_tax_1040nr",
            label="j1_research_scholar",
            description="J-1 research scholar (not F-1 student) from Germany, $45K stipend, first year in US. Different visa mechanics — J-1 scholars are exempt from SPT for 2 years (not 5 like F-1). Treaty: Germany-US has student-limited exemptions.",
            intake={
                "tax_year": 2024,
                "full_name": "Hans Weber",
                "visa_type": "J-1",
                "j1_category": "research scholar",
                "school_name": "Caltech",
                "country_citizenship": "Germany",
                "country_passport": "Germany",
                "passport_number": "D99887766",
                "arrival_date": "2024-09-01",
                "taxpayer_id_number": "",
                "wage_income_usd": 45000,
                "federal_withholding_usd": 5000,
                "state_withholding_usd": 2000,
            },
        ),
        Scenario(
            service="student_tax_1040nr",
            label="f1_year_six_potentially_resident",
            description="Chinese F-1 who arrived in 2019 — now in year 6, past the 5-year exempt period. May be a RESIDENT for tax purposes under SPT, which would invalidate 1040-NR. Output should at minimum flag this timing issue.",
            intake={
                "tax_year": 2024,
                "full_name": "Yi Chen",
                "visa_type": "F-1",
                "school_name": "UC Berkeley",
                "country_citizenship": "China",
                "country_passport": "China",
                "passport_number": "E55443322",
                "arrival_date": "2019-08-20",
                "days_present_current": 365,
                "days_present_year_1_ago": 365,
                "days_present_year_2_ago": 365,
                "taxpayer_id_number": "987-65-1234",
                "wage_income_usd": 35000,
                "federal_withholding_usd": 3500,
                "state_withholding_usd": 1200,
            },
        ),
        Scenario(
            service="student_tax_1040nr",
            label="scholarship_only_no_wages",
            description="Taiwanese F-1 with $22K scholarship, zero wages. Scholarships for room/board are taxable but tuition is not — needs nuanced handling. Not a Form 8843-only case because income exists.",
            intake={
                "tax_year": 2024,
                "full_name": "Ming Huang",
                "visa_type": "F-1",
                "school_name": "Princeton",
                "country_citizenship": "Taiwan",
                "country_passport": "Taiwan",
                "passport_number": "T12300099",
                "arrival_date": "2023-08-15",
                "taxpayer_id_number": "111-22-3333",
                "wage_income_usd": 0,
                "scholarship_income_usd": 22000,
                "federal_withholding_usd": 0,
            },
        ),
    ]


def election_83b_diversity_scenarios() -> list[Scenario]:
    today = date(2026, 4, 1)
    return [
        Scenario(
            service="election_83b",
            label="high_spread_early_exercise",
            today=today,
            description="Early-exercised ISOs after a Series B: exercise price $0.50, FMV $3.50 per share, 40,000 shares. Taxable spread is $120,000 — large tax bill at filing. Output should surface the spread amount AND flag the immediate tax-due risk.",
            intake={
                "grant_date": (today - timedelta(days=12)).isoformat(),
                "taxpayer_name": "Morgan Engineer",
                "taxpayer_address": "1 Valencia St, San Francisco, CA 94110",
                "company_name": "ScaleUp Corp",
                "property_description": "40,000 shares of common stock from early-exercised ISOs",
                "share_count": 40000,
                "fair_market_value_per_share": 3.50,
                "exercise_price_per_share": 0.50,
                "vesting_schedule": "4 years, 1-year cliff already met, monthly thereafter",
            },
        ),
        Scenario(
            service="election_83b",
            label="address_new_jersey",
            today=today,
            description="New Jersey address — should map to Kansas City service center. Tests state mapping coverage.",
            intake={
                "grant_date": (today - timedelta(days=3)).isoformat(),
                "taxpayer_name": "NJ Founder",
                "taxpayer_address": "100 Commerce Way, Hoboken, NJ 07030",
                "company_name": "Jersey Startup Inc",
                "property_description": "20,000 shares of restricted common stock",
                "share_count": 20000,
                "fair_market_value_per_share": 0.01,
                "exercise_price_per_share": 0.01,
                "vesting_schedule": "4 years, 1-year cliff",
            },
        ),
    ]


def all_scenarios() -> list[Scenario]:
    return (
        h1b_scenarios()
        + fbar_scenarios()
        + student_tax_scenarios()
        + election_83b_scenarios()
        + h1b_diversity_scenarios()
        + fbar_diversity_scenarios()
        + student_tax_diversity_scenarios()
        + election_83b_diversity_scenarios()
    )
