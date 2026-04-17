"""Generate a synthetic H-1B demo case package for outreach to prospective counsel.

Creates a realistic-looking but entirely fictional case (no real PII)
mirroring the Klasko gold-standard structure: 7 sections, full I-20
lineage, complete corporate formation, registration, employment history,
business plans.

Every generated PDF is a single labeled page clearly marked "DEMO —
SYNTHETIC FIXTURE" so there's no ambiguity about the data being fake.

Usage:
    python scripts/generate_demo_h1b.py [output_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF


# ────────────────────────────────────────────────────────────────
#  Fictional case data
# ────────────────────────────────────────────────────────────────

DEMO_CASE = {
    "beneficiary_name": "Wei Zhang",
    "beneficiary_name_native": "张 伟",
    "beneficiary_nationality": "Chinese (PRC)",
    "beneficiary_passport": "DEMO000001",
    "beneficiary_passport_exp": "08/15/2030",
    "beneficiary_sevis": "N0099999999",
    "beneficiary_ssn": "XXX-XX-0000",
    "beneficiary_address": "1500 Demo Street, Apt 4B, Palo Alto, CA 94301",
    "beneficiary_email": "wei@example.demo",
    "petitioner_name": "Acme Research Inc.",
    "petitioner_ein": "00-1234567",
    "petitioner_state": "Delaware",
    "petitioner_inc_date": "January 5, 2026",
    "petitioner_address": "100 Innovation Way, Suite 200, Menlo Park, CA 94025",
    "petitioner_owner": "Lin Chen (100% shareholder / sole director)",
    "petitioner_owner_nationality": "Chinese national, resident of Beijing",
    "soc_code": "15-2051.00 (Data Scientists)",
    "job_title": "Research Data Scientist",
    "wage_level": "III",
    "prevailing_wage": "$148,720/yr (SF-San Mateo-Redwood City MSA)",
    "salary_filed": "$150,000–$165,000/yr",
    "lottery_year": "FY2027",
    "filing_deadline": "June 30, 2026",
    "h1b_start": "October 1, 2026",
    "attorney": "Prospective Counsel (Demo)",
    "date": "April 17, 2026",
}


# ────────────────────────────────────────────────────────────────
#  PDF generator
# ────────────────────────────────────────────────────────────────

def write_placeholder_pdf(path: Path, slot_id: str, title: str, caption: str) -> None:
    """Single-page labeled PDF placeholder."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # US Letter

    # Watermark bar
    page.draw_rect(
        fitz.Rect(0, 0, 612, 60),
        color=(0.36, 0.55, 0.93), fill=(0.36, 0.55, 0.93),
    )
    page.insert_text(
        (36, 38),
        "GUARDIAN DEMO — SYNTHETIC FIXTURE (NOT A REAL DOCUMENT)",
        fontsize=11, color=(1, 1, 1), fontname="helv",
    )

    # Slot id
    page.insert_text(
        (36, 120), f"{slot_id}", fontsize=14, color=(0.5, 0.58, 0.68),
        fontname="helv",
    )
    # Title
    page.insert_text(
        (36, 150), title, fontsize=22, color=(0.05, 0.08, 0.14),
        fontname="hebo",
    )
    # Caption, wrapped manually
    y = 200
    for line in caption.splitlines():
        if not line.strip():
            y += 12
            continue
        for chunk in _wrap(line, 82):
            page.insert_text(
                (36, y), chunk, fontsize=11,
                color=(0.33, 0.39, 0.5), fontname="helv",
            )
            y += 16

    # Footer
    page.insert_text(
        (36, 760),
        f"Case: H-1B Petition — {DEMO_CASE['petitioner_name']} / {DEMO_CASE['beneficiary_name']} (DEMO)",
        fontsize=9, color=(0.55, 0.6, 0.68), fontname="helv",
    )

    doc.save(str(path))
    doc.close()


def _wrap(text: str, width: int) -> list[str]:
    out, cur = [], ""
    for word in text.split():
        if len(cur) + 1 + len(word) > width:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        out.append(cur)
    return out or [""]


# ────────────────────────────────────────────────────────────────
#  Case brief text (H-1B SECTION N: TITLE format)
# ────────────────────────────────────────────────────────────────

def write_case_brief(path: Path) -> None:
    c = DEMO_CASE
    bar = "=" * 64
    text = f"""{bar}
CASE BRIEF — H-1B PETITION, {c['petitioner_name'].upper()} / {c['beneficiary_name'].upper()} (DEMO)
Prepared for: {c['attorney']}
Prepared by:  Guardian (synthetic demo)
Date:         {c['date']}
Re:           Sample complete H-1B package — fictional case for product demo
{bar}

This is a Guardian DEMO package. All names, identifiers, addresses, and
numbers are fictional — no real PII. The structure mirrors a real
Klasko-style H-1B petition package so prospective counsel can evaluate
how Guardian presents a complete file for review.


{bar}
SECTION 1: THE PARTIES
{bar}

PETITIONER
──────────────────────────────────────────────────────────────
Entity:         {c['petitioner_name']}
Type:           {c['petitioner_state']} C-Corporation
EIN:            {c['petitioner_ein']}
Incorporated:   {c['petitioner_inc_date']}
Address:        {c['petitioner_address']}
                Commercial lease — Acme HQ (D9)
Registered Agent: Delaware Corporate Agents Inc.
                  (SOI filed 02/18/2026 — see D4)
Sole Owner:     {c['petitioner_owner']}
                {c['petitioner_owner_nationality']}
Employees:      1 (the Beneficiary, on CPT)
Revenue:        Pre-revenue
Bank Account:   Mercury Business Checking — opened Feb 2026
                Current balance: ~$250,000 (demo figure)
Website:        acme-research.example

BENEFICIARY
──────────────────────────────────────────────────────────────
Name:           {c['beneficiary_name']}
Native Name:    {c['beneficiary_name_native']}
Nationality:    {c['beneficiary_nationality']}
SEVIS ID:       {c['beneficiary_sevis']}
Current Status: F-1, CPT at Sample Graduate School / {c['petitioner_name']}
Passport:       {c['beneficiary_passport']}, expires {c['beneficiary_passport_exp']}
Address:        {c['beneficiary_address']}
SSN:            {c['beneficiary_ssn']}
Email:          {c['beneficiary_email']}

POSITION FILED IN H-1B LOTTERY
──────────────────────────────────────────────────────────────
Title:          {c['job_title']}
SOC Code:       {c['soc_code']}
Wage Level:     {c['wage_level']}
Prevailing Wage: {c['prevailing_wage']}
Salary Filed:   {c['salary_filed']}
Work Location:  {c['petitioner_address']}


{bar}
SECTION 2: COMPLETE F-1 STATUS AND EMPLOYMENT LINEAGE
{bar}

The following is the demo chronological record, analogous to the SEVIS
record + all 12 I-20s a real case would provide.

PHASE 1  F-1 Student at Stanford         Fall 2020 – Dec 2021
PHASE 2  Post-Completion OPT             Jan 2022 – Jan 2023
PHASE 3  STEM OPT                        Jan 2023 – Sep 2025
PHASE 4  F-1 at Sample Grad — Transfer   Sep 2025 – Oct 2025
PHASE 5  CPT — Prior Employer            Nov 2025 – Mar 2026
PHASE 6  CPT — {c['petitioner_name']}            Apr 2026 – Aug 2026
PHASE 7  H-1B — {c['petitioner_name']}           Target {c['h1b_start']}


{bar}
SECTION 3: KNOWN ISSUES — PROACTIVE DISCLOSURE
{bar}

ISSUE 1: DEMO — SAMPLE OPEN SEVIS ENTRY (low risk)
──────────────────────────────────────────────────────────────
A prior OPT employer record remains open in SEVIS. Fictional — shown
to demonstrate how Guardian surfaces proactive disclosures.

ISSUE 2: DEMO — PASSPORT EXPIRES WITHIN 6 MONTHS OF FILING
──────────────────────────────────────────────────────────────
Renewal in progress. Fictional but representative.

ISSUE 3: DEMO — STARTUP ABILITY-TO-PAY (< 12 months operating history)
──────────────────────────────────────────────────────────────
Fictional. Mirrors a common small-petitioner concern.


{bar}
SECTION 4: COMPLETE DOCUMENT INVENTORY
{bar}

Status:  [✓] Included in this demo
         [!] Intentionally pending (demo of pending-items panel)

A — BENEFICIARY
──────────────────────────────────────────────────────────────
[✓] A1  Passport bio page
[✓] A2  I-94 most recent
[✓] A3  Graduate degree
[✓] A4  Transcript
[✓] A5  CV
[✓] A6  F-1 visa stamp page
[✓] A7  OPT EAD card
[✓] A8  STEM OPT EAD card
[!] A9  Current enrollment letter (pending — demo)

B — I-20 HISTORY (12 items, full chronology)
──────────────────────────────────────────────────────────────
[✓] B01–B12  Full I-20 lineage from initial issuance through current CPT

C — CPT ACADEMIC EVIDENCE
──────────────────────────────────────────────────────────────
[✓] C1  Academic evidence summary
[✓] C2  CPT training plan / application

D — CORPORATE (PETITIONER)
──────────────────────────────────────────────────────────────
[✓] D1–D13  Articles, bylaws, resolutions, SOI, governance, EIN,
            lease, board resolution (signing authority), CP-575,
            affidavit of financial support
[!] D14  Corporate bank statement (demo — pending)
[✓] D15  Full commercial lease

E — H-1B REGISTRATION
──────────────────────────────────────────────────────────────
[✓] E1  FY selection notice
[✓] E2  G-28 (primary petitioner)
[✓] E3  Primary registration draft

F — EMPLOYMENT HISTORY
──────────────────────────────────────────────────────────────
[✓] F1  SEVIS employment record (synthetic)
[✓] F2  Prior employer termination letter
[✓] F4a–F4c  I-983 forms (prior STEM OPT employers)

G — BUSINESS PLANS
──────────────────────────────────────────────────────────────
[✓] G1  Petitioner business plan
[✓] G2  Product/division business plan


{bar}
SECTION 5: NOTE ON THIS DEMO
{bar}

Guardian auto-organizes documents a beneficiary uploads against the
petition-package template, flags gaps before filing, and produces a
tokenized share URL so counsel can review the complete file in one
click. The percentages, pending flags, inline PDF preview, and
download-all button on this page are the exact surfaces your clients
would see.

Questions / to learn more:   fretin13@gmail.com

{bar}
END OF DEMO CASE BRIEF
{bar}
"""
    path.write_text(text, encoding="utf-8")


# ────────────────────────────────────────────────────────────────
#  Slot definitions — mirror the H-1B template
# ────────────────────────────────────────────────────────────────

SLOTS: list[tuple[str, str, str, str]] = [
    # (section_folder, filename, title, caption)
    ("A_Beneficiary", "A1_passport_bio_page.pdf",
     "Passport bio page — DEMO",
     "Sample passport biographic page. Real case would include full "
     "name, photo, passport number, issue/expiry dates."),
    ("A_Beneficiary", "A2_i94_most_recent.pdf",
     "I-94 most recent — DEMO",
     "Most recent admission record from CBP. Lists class of admission, "
     "admit-until date."),
    ("A_Beneficiary", "A3_graduate_degree.pdf",
     "Graduate degree — DEMO",
     "Master's or PhD diploma establishing specialty-occupation baseline."),
    ("A_Beneficiary", "A4_graduate_transcript.pdf",
     "Graduate transcript — DEMO",
     "Official transcript showing coursework relevant to SOC."),
    ("A_Beneficiary", "A5_cv_demo.pdf",
     "CV / resume — DEMO",
     "H-1B-tailored CV emphasizing specialty-occupation duties."),
    ("A_Beneficiary", "A6_f1_visa_stamp.pdf",
     "F-1 visa stamp page — DEMO",
     "Current F-1 visa foil in passport."),
    ("A_Beneficiary", "A7_opt_ead_card.pdf",
     "OPT EAD card — DEMO",
     "Post-completion OPT EAD card front/back scan."),
    ("A_Beneficiary", "A8_stem_opt_ead_card.pdf",
     "STEM OPT EAD card — DEMO",
     "STEM OPT EAD card front/back scan."),
    # B: 12 I-20s (chronological lineage)
    ("B_I20_History", "B01_i20_columbia_original.pdf",       "I-20 #1 Initial (prior school) — DEMO", "Initial F-1 issuance at prior graduate school."),
    ("B_I20_History", "B02_i20_columbia_travel_2022.pdf",    "I-20 #2 Travel 2022 — DEMO",            "Travel signature — 2022."),
    ("B_I20_History", "B03_i20_columbia_travel_2023.pdf",    "I-20 #3 Travel 2023 — DEMO",            "Travel signature — 2023."),
    ("B_I20_History", "B04_i20_columbia_opt_jan2023.pdf",    "I-20 #4 OPT — DEMO",                    "OPT endorsement."),
    ("B_I20_History", "B05_i20_columbia_stemopt_jan2024.pdf","I-20 #5 STEM OPT — DEMO",               "STEM OPT endorsement."),
    ("B_I20_History", "B06_i20_columbia_stemopt_signed.pdf", "I-20 #6 STEM OPT signed — DEMO",        "Signed STEM OPT update."),
    ("B_I20_History", "B07_i20_westcliff_transfer_pending.pdf","I-20 #7 Transfer pending — DEMO",     "Transfer to next school — pending."),
    ("B_I20_History", "B08_i20_westcliff_continued.pdf",     "I-20 #8 Transfer continued — DEMO",     "Continuation."),
    ("B_I20_History", "B09_i20_ciam_transfer_pending_sep2025.pdf","I-20 #9 Grad school transfer — DEMO","Transfer to current grad school."),
    ("B_I20_History", "B10_i20_ciam_cpt_wolff_li_nov2025.pdf","I-20 #10 CPT (prior employer) — DEMO", "CPT endorsement for prior employer."),
    ("B_I20_History", "B11_i20_ciam_current.pdf",            "I-20 #11 Current — DEMO",               "Most recent I-20 for enrolled school."),
    ("B_I20_History", "B12_i20_ciam_cpt_yangtze_apr2026.pdf","I-20 #12 CPT (petitioner) — DEMO",      "Current CPT endorsement for petitioner."),
    # C
    ("C_CPT_Evidence", "C1_cpt_academic_evidence_summary.pdf",
     "CPT academic evidence summary — DEMO",
     "Compiled evidence: enrollments, grades, submissions. Demonstrates "
     "CPT is integral to coursework."),
    ("C_CPT_Evidence", "C2_ciam_cpt_application_training_plan.pdf",
     "CPT training plan — DEMO",
     "CPT training plan signed by DSO."),
    # D
    ("D_Corporate", "D1_articles_of_incorporation_ss4.pdf", "Articles of Incorporation + SS-4 — DEMO", "Delaware C-Corp formation + EIN application."),
    ("D_Corporate", "D2_bylaws.pdf",                         "Bylaws — DEMO",                         "Corporate bylaws."),
    ("D_Corporate", "D3_corporate_resolutions.pdf",          "Corporate resolutions — DEMO",          "Resolutions authorizing petition."),
    ("D_Corporate", "D4_soi_goodstanding.pdf",               "SOI + Good Standing — DEMO",            "State Statement of Info + good-standing cert."),
    ("D_Corporate", "D5_governance_docs_signed.pdf",         "Governance docs (signed) — DEMO",       "Signed governance package."),
    ("D_Corporate", "D6_key_documents_compilation.pdf",      "Key docs compilation — DEMO",           "Consolidated key-documents exhibit."),
    ("D_Corporate", "D7_ein_cancellation_letter.pdf",        "EIN cancellation letter — DEMO",        "Duplicate EIN cancellation (if applicable)."),
    ("D_Corporate", "D8_ein_fax_notification.pdf",           "EIN fax notification — DEMO",           "IRS fax confirmation."),
    ("D_Corporate", "D9_office_lease_extract.pdf",           "Office lease (extract) — DEMO",         "Signed commercial lease excerpt."),
    ("D_Corporate", "D10_ftb_withholding_notice.pdf",        "FTB withholding notice — DEMO",         "State franchise-tax board notice."),
    ("D_Corporate", "D11_board_resolution_signing_authority.pdf","Board resolution — signing authority — DEMO","Establishes employer-employee authority."),
    ("D_Corporate", "D12_ein_cp575_notice.pdf",              "EIN CP-575 notice — DEMO",              "IRS-issued EIN confirmation."),
    ("D_Corporate", "D13_affidavit_financial_support.pdf",   "Affidavit of financial support — DEMO", "Owner's personal-support affidavit."),
    ("D_Corporate", "D15_office_lease_full_signed.pdf",      "Full commercial lease (signed) — DEMO", "Full lease agreement."),
    # E
    ("E_H1B_Registration", "E1_fy2027_selection_notice.pdf", "FY selection notice — DEMO",            "USCIS registration selection."),
    ("E_H1B_Registration", "E2_yangtze_g28_arora.pdf",       "G-28 (primary) — DEMO",                 "Notice of attorney rep for registration."),
    ("E_H1B_Registration", "E3_yangtze_registration_draft.pdf","Primary registration draft — DEMO",    "Lottery registration confirmation."),
    # F
    ("F_Employment_History", "F1_sevis_employment_record.pdf","SEVIS employment record — DEMO",       "Synthetic SEVIS extract — employment history."),
    ("F_Employment_History", "F2_claudius_termination_letter.pdf","Prior employer termination — DEMO","Clean end-date documentation."),
    ("F_Employment_History/I983_STEM_OPT", "F4a_i983_tiger_cloud_vcv_signed.pdf","I-983 #1 — DEMO","Signed I-983 training plan, STEM OPT employer #1."),
    ("F_Employment_History/I983_STEM_OPT", "F4b_i983_claudius_signed.pdf","I-983 #2 — DEMO","Signed I-983 training plan, STEM OPT employer #2."),
    ("F_Employment_History/I983_STEM_OPT", "F4c_i983_clinipulse_signed.pdf","I-983 #3 — DEMO","Signed I-983 training plan, STEM OPT employer #3."),
    # G
    ("G_Business_Plans", "G1_yangtze_capital_business_plan_v1.pdf", "Petitioner business plan — DEMO", "Full business plan for petitioning entity."),
    ("G_Business_Plans", "G2_guardian_ai_business_plan_v1.pdf",     "Product business plan — DEMO",    "Product/division plan reinforcing going-concern narrative."),
]


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/demo_h1b_petition")
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Case brief
    write_case_brief(out / "00_CASE_BRIEF_DEMO.txt")

    # Subdirs + placeholder PDFs
    for sub, fname, title, caption in SLOTS:
        sub_path = out / sub
        sub_path.mkdir(parents=True, exist_ok=True)
        slot_id = fname.split("_", 1)[0]
        write_placeholder_pdf(sub_path / fname, slot_id, title, caption)

    file_count = sum(1 for _ in out.rglob("*") if _.is_file())
    print(f"Demo fixture at {out}")
    print(f"Files generated: {file_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
