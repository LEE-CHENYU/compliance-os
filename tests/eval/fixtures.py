"""Synthetic compliance-corpus fixtures for the search eval.

Twenty representative documents covering the realistic distribution of doc
types Guardian sees: tax forms, immigration notices, employment records,
deadlines, corporate filings, and one decoy concept doc. Each file maps
to a stable doc id (the filename stem) so the eval can encode ground
truth without re-resolving paths.

The fixtures are deliberately concise — the eval cares about retrieval
discrimination, not natural-language plausibility. Each doc is one
paragraph that names enough distinguishing tokens (form numbers, dates,
employers, statuses) to be findable.
"""

from __future__ import annotations

from pathlib import Path


FIXTURES: dict[str, str] = {
    # ── Immigration ─────────────────────────────────────────
    "i797_h1b_approval_2026.txt": (
        "USCIS Form I-797A Notice of Action. H-1B petition approval for "
        "beneficiary CHENYU LI. Employer: Acme Robotics Inc. Receipt "
        "number EAC2412345678. Validity: 2026-10-01 to 2029-09-30. "
        "Approval date: 2026-04-15. Classification: H1B specialty occupation."
    ),
    "i797_h1b_amendment_2027.txt": (
        "USCIS Form I-797A Amendment notice. H-1B amended petition for "
        "CHENYU LI. Employer: Acme Robotics Inc. New worksite: Boston MA. "
        "Receipt EAC2898765432. Validity extended through 2030-09-30. "
        "Notice date: 2027-02-10."
    ),
    "i20_stem_opt_extension_2025.txt": (
        "Form I-20 Certificate of Eligibility for Nonimmigrant Student "
        "Status. STEM OPT extension authorized for CHENYU LI, SEVIS ID "
        "N0012345678. Program end date: 2027-05-15. DSO signature: "
        "Jane Smith, MIT. Issue date: 2025-04-20."
    ),
    "i983_training_plan_2025.txt": (
        "Form I-983 Training Plan for STEM OPT Students. Employer: Acme "
        "Robotics Inc. Student: CHENYU LI. Goals: applied robotics R&D. "
        "Compensation: $145,000/yr. Hours: 40/week. Signed 2025-04-12."
    ),
    "ead_card_renewal_2026.txt": (
        "Employment Authorization Document (EAD) renewal receipt notice. "
        "Form I-765 receipt for CHENYU LI. Category C03B STEM OPT. "
        "Receipt EAC2401122334. Receipt date 2026-01-08."
    ),
    # ── Tax ─────────────────────────────────────────────────
    "form_8843_2025.txt": (
        "Form 8843 Statement for Exempt Individuals and Individuals with "
        "a Medical Condition. Tax year 2024. Name: CHENYU LI. Country of "
        "residence: China. Visa type: F-1. Days present in US: 365. "
        "Filed 2025-04-10."
    ),
    "form_1040nr_2025.txt": (
        "Form 1040-NR US Nonresident Alien Income Tax Return. Tax year "
        "2024. Filer: CHENYU LI. Wages: $128,400. Federal tax withheld: "
        "$22,100. Refund claimed: $1,840. Filed 2025-04-12."
    ),
    "w2_acme_2025.txt": (
        "Form W-2 Wage and Tax Statement. Employer: Acme Robotics Inc. "
        "EIN 12-3456789. Employee: CHENYU LI. Box 1 wages: $128,400. "
        "Federal income tax withheld: $22,100. Tax year 2024."
    ),
    "fbar_fincen114_2025.txt": (
        "FinCEN Form 114 Report of Foreign Bank and Financial Accounts. "
        "Filer: CHENYU LI. Foreign account: Bank of China, Beijing. "
        "Account high balance during 2024: $34,500 USD-equivalent. "
        "Filed 2025-06-15."
    ),
    "form_5472_2025.txt": (
        "Form 5472 Information Return of a 25% Foreign-Owned US "
        "Corporation. Reporting corporation: Acme Holdings LLC. "
        "Foreign shareholder: parent entity in Cayman Islands. Tax year "
        "2024. Filed with Form 1120 on 2025-04-15."
    ),
    # ── Employment / Payroll ────────────────────────────────
    "paystub_acme_2026_03.txt": (
        "Acme Robotics Inc. pay statement. Employee: CHENYU LI. Pay "
        "period 2026-03-01 to 2026-03-15. Gross: $5,500. Federal tax: "
        "$945. Net: $4,200. YTD gross: $33,000."
    ),
    "offer_letter_acme_2025.txt": (
        "Offer letter from Acme Robotics Inc. to CHENYU LI. Position: "
        "Senior Robotics Engineer. Start date: 2025-05-01. Base salary: "
        "$145,000. Sign-on bonus: $15,000. At-will employment subject to "
        "I-9 verification."
    ),
    "i9_employment_eligibility_2025.txt": (
        "Form I-9 Employment Eligibility Verification. Section 1 "
        "completed by CHENYU LI on 2025-05-01. Section 2 documents: "
        "passport (List A). Employer: Acme Robotics Inc. authorized "
        "representative: HR Director."
    ),
    # ── Corporate ───────────────────────────────────────────
    "articles_of_incorp_acme_2024.txt": (
        "Articles of Incorporation of Acme Holdings LLC. Delaware "
        "registered agent: Corporation Trust Center. Members: CHENYU LI "
        "(60%), foreign parent (40%). Filed 2024-11-02."
    ),
    "ein_letter_acme_2024.txt": (
        "IRS EIN Confirmation letter for Acme Holdings LLC. Employer "
        "Identification Number 88-1234567. Issued 2024-11-08. Entity "
        "classification: disregarded entity."
    ),
    # ── Deadlines / calendar ────────────────────────────────
    "deadline_calendar_2026.txt": (
        "Compliance deadline calendar for 2026 tax year. Form 1040-NR "
        "due 2026-04-15. Form 8843 due 2026-04-15. FBAR FinCEN 114 due "
        "2026-04-15 (auto-extended to 2026-10-15). Form 5472 due with "
        "Form 1120 by 2026-04-15."
    ),
    "deadline_visa_renewal.txt": (
        "Visa renewal timeline reminder. Schedule consular interview at "
        "least 90 days before current I-797 expiration (2029-09-30). "
        "DS-160 form to be filed by 2029-06-30."
    ),
    # ── Correspondence ──────────────────────────────────────
    "uscis_rfe_2026.txt": (
        "USCIS Request for Evidence (RFE) for I-140 EB-2 NIW petition. "
        "Petitioner: CHENYU LI. Response due: 2026-08-22. Evidence "
        "requested: additional proof of national interest waiver "
        "criteria 2 and 3."
    ),
    "attorney_engagement_2025.txt": (
        "Engagement letter from Goodwin Procter LLP. Attorney: Sarah "
        "Park. Matter: H-1B and EB-2 NIW filings for CHENYU LI. Fee: "
        "$8,500 flat. Engagement effective 2025-09-12."
    ),
    # ── Concept / methodology (decoy for false-positive tests) ─
    "methodology_compliance_principles.txt": (
        "Compliance methodology overview. Guardian cross-checks "
        "immigration filings against employment records to surface "
        "discrepancies. Calendar deadlines, document amendments, and "
        "lineage chains are tracked across filings. This is informational "
        "only — not legal advice."
    ),
}


def write_fixtures(base_dir: Path) -> dict[str, Path]:
    """Materialize FIXTURES under base_dir/<category>/<name>.

    Category is inferred from the doc id prefix so the indexer's
    classifier picks up the right doc_type. Mtimes are nudged so the
    recency rerank has signal: newer-looking docs (2026+) get fresh
    timestamps; older fixtures get backdated by 1-2 years.
    """
    import time

    def _category(stem: str) -> str:
        if stem.startswith(("i797_", "i20_", "i983_", "ead_", "i9_", "uscis_")):
            return "immigration"
        if stem.startswith(("form_8843", "form_1040", "w2_", "fbar_", "form_5472")):
            return "tax"
        if stem.startswith(("paystub_", "offer_letter", "i9_")):
            return "payroll"
        if stem.startswith(("articles_", "ein_")):
            return "corporate"
        if stem.startswith("deadline_"):
            return "deadlines"
        if stem.startswith("attorney_"):
            return "legal"
        return "general"

    paths: dict[str, Path] = {}
    now = time.time()
    for name, body in FIXTURES.items():
        stem = name.rsplit(".", 1)[0]
        cat = _category(stem)
        cat_dir = base_dir / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / name
        path.write_text(body)
        # Crude mtime nudging: docs whose name contains a year set mtime to
        # that year's midpoint, otherwise leave at now.
        for year in (2024, 2025, 2026, 2027):
            if str(year) in stem:
                # June 30 of that year
                target = time.mktime((year, 6, 30, 12, 0, 0, 0, 0, 0))
                import os
                os.utime(path, (target, target))
                break
        paths[stem] = path
    _ = now  # silence linter
    return paths
