"""Student tax package preparation workflow."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from compliance_os.web.models.database import DATA_DIR
from compliance_os.web.services.form_8843 import generate_form_8843
from compliance_os.web.services.mailing_service import (
    build_form_8843_filing_context,
    serialize_filing_context,
)
from compliance_os.web.services.pdf_builder import build_text_pdf


STUDENT_TAX_DIR = DATA_DIR / "marketplace" / "student_tax_1040nr"


def _as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _tax_deadline(tax_year: int) -> date:
    return date(tax_year + 1, 4, 15)


def _finding(
    *,
    rule_id: str,
    severity: str,
    title: str,
    action: str,
    consequence: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "category": "tax",
        "title": title,
        "action": action,
        "consequence": consequence,
        "immigration_impact": False,
    }


def process_student_tax_check(order_id: str, intake_data: dict[str, Any]) -> dict[str, Any]:
    tax_year = int(intake_data.get("tax_year") or date.today().year - 1)
    deadline = _tax_deadline(tax_year)

    wage_income = _as_float(intake_data.get("wage_income_usd"))
    scholarship_income = _as_float(intake_data.get("scholarship_income_usd"))
    other_income = _as_float(intake_data.get("other_income_usd"))
    federal_withholding = _as_float(intake_data.get("federal_withholding_usd"))
    state_withholding = _as_float(intake_data.get("state_withholding_usd"))
    total_income = wage_income + scholarship_income + other_income

    claim_treaty_benefit = bool(intake_data.get("claim_treaty_benefit"))
    treaty_country = str(intake_data.get("treaty_country") or "").strip()
    treaty_article = str(intake_data.get("treaty_article") or "").strip()
    used_resident_software = bool(intake_data.get("used_resident_software"))

    taxpayer_id_present = bool(str(intake_data.get("taxpayer_id_number") or "").strip())
    has_1042s = bool(intake_data.get("has_1042s"))
    state_of_residence = str(intake_data.get("state_of_residence") or "").strip().upper()
    state_of_employer = str(intake_data.get("state_of_employer") or "").strip().upper()

    full_name = str(intake_data.get("full_name") or "").strip()
    visa_type = str(intake_data.get("visa_type") or "F-1").strip() or "F-1"
    school_name = str(intake_data.get("school_name") or "").strip()
    country_citizenship = str(intake_data.get("country_citizenship") or "").strip()
    country_citizenship_key = country_citizenship.lower()

    # Visa-category awareness for SPT exempt-period and FICA scope.
    # F-1 / J-1 STUDENT: 5-year SPT exempt period (IRC §7701(b)(5)(D)(ii) for J-1
    # students; §7701(b)(5)(E) for F-1)
    # J-1 SCHOLAR / TEACHER / TRAINEE / RESEARCHER: 2-year SPT exempt period (IRC
    # §7701(b)(5)(D)(i)) — much shorter window
    visa_clean = visa_type.upper().replace(" ", "").replace("-", "")
    j1_category_str = str(intake_data.get("j1_category") or "").lower().strip()
    is_j1_scholar = visa_clean.startswith("J1") and (
        any(kw in j1_category_str for kw in ("scholar", "research", "teacher", "trainee", "professor"))
        or any(
            kw in school_name.lower() or kw in str(intake_data.get("program_director") or "").lower()
            for kw in ("scholar", "research", "teacher", "trainee")
        )
    )
    is_f1_or_j1_student = visa_clean.startswith(("F1", "J1")) and not is_j1_scholar
    spt_exempt_years = 2 if is_j1_scholar else (5 if is_f1_or_j1_student else 0)

    # Substantial Presence Test crossover detection
    arrival_date_str = str(intake_data.get("arrival_date") or "").strip()
    spt_crossover_warning = False
    spt_year_in_us: int | None = None
    if arrival_date_str and spt_exempt_years > 0:
        try:
            from datetime import date as _date_cls
            arrival = _date_cls.fromisoformat(arrival_date_str)
            spt_year_in_us = tax_year - arrival.year + 1
            if spt_year_in_us > spt_exempt_years:
                spt_crossover_warning = True
        except (TypeError, ValueError):
            pass

    findings: list[dict[str, Any]] = []

    # If the user explicitly says they already filed the correct form (e.g.,
    # switched to 1040 after SPT crossover), downgrade the crossover finding.
    already_filed_correct_return = bool(intake_data.get("already_filed_correct_return"))

    # SPT crossover — fires before any other rule because it changes the form path
    if spt_crossover_warning and already_filed_correct_return:
        category = "J-1 scholar" if is_j1_scholar else "F-1/J-1 student"
        findings.append(
            _finding(
                rule_id="student_tax_spt_crossover_acknowledged",
                severity="info",
                title=f"Noted: you crossed the {spt_exempt_years}-year {category} SPT exempt window",
                action="You indicated you already filed the correct return for your residency status. No action required here. Keep a copy of the correct return (1040 if resident, 1040-NR if still nonresident) and any Form 8833 treaty-based disclosures.",
                consequence="This is informational context only.",
            )
        )
    elif spt_crossover_warning:
        category = "J-1 scholar" if is_j1_scholar else "F-1/J-1 student"
        exempt_label = f"{spt_exempt_years} calendar years"
        findings.append(
            _finding(
                rule_id="student_tax_spt_crossover_risk",
                severity="critical",
                title=f"Possible resident-alien status — {category} past the {exempt_label} SPT exemption",
                action=(
                    f"You arrived {arrival_date_str} and tax year {tax_year} is your year {spt_year_in_us} in the US. "
                    f"The {exempt_label} exempt-individual period under IRC §7701(b)(5) has likely expired, which means "
                    f"the Substantial Presence Test now counts your days of presence. With 183+ counted days you would "
                    f"file Form 1040 (resident alien), NOT Form 1040-NR. Stop and verify your residency status before filing — "
                    f"a tax professional or Sprintax's residency determination tool can confirm. Filing 1040-NR as a resident is "
                    f"the wrong form."
                ),
                consequence="Filing the wrong form (1040-NR vs 1040) triggers IRS notices, accuracy-related penalties, "
                "and can flag during H-1B/green card adjudication. Treaty benefits and FICA exemption that apply to "
                "nonresidents do not apply to residents.",
            )
        )
    if total_income <= 0:
        findings.append(
            _finding(
                rule_id="student_tax_zero_income",
                severity="warning",
                title="Income looks like a standalone Form 8843 case",
                action="Confirm whether you had any U.S. wages, scholarship income, or taxable payments. If income was truly zero, the free Form 8843 flow may be enough.",
                consequence="Users with no U.S. income usually do not need a full 1040-NR package, so this order may be more than you need.",
            )
        )
    if used_resident_software:
        finding = _finding(
            rule_id="student_tax_resident_software",
            severity="critical",
            title="Resident-return software cannot file Form 1040-NR",
            action="Stop using resident-return software (TurboTax, H&R Block, FreeTaxUSA) for this return. Use a nonresident-specific preparer — Sprintax and GLACIER Tax Prep are the common ones for F-1/J-1 filers — or work with a CPA who files 1040-NR.",
            consequence="Filing Form 1040 instead of 1040-NR can create residency-status mistakes that trigger IRS notices, require amendment, and may surface during H-1B or green card adjudication.",
        )
        finding["immigration_impact"] = True
        findings.append(finding)
    if claim_treaty_benefit and not treaty_country:
        findings.append(
            _finding(
                rule_id="student_tax_missing_treaty_country",
                severity="warning",
                title="Treaty benefit selected without a treaty country",
                action="Confirm the treaty country and article before you rely on a treaty position in the filing package.",
                consequence="An incomplete treaty claim weakens the filing package and can delay review by a CPA or tax preparer.",
            )
        )
    if claim_treaty_benefit and treaty_country.lower() == "china" and "20" in treaty_article and wage_income > 0:
        exempt_amount = min(5000.0, wage_income)
        taxable_after = max(wage_income - 5000.0, 0.0)
        findings.append(
            _finding(
                rule_id="student_tax_china_treaty_amount",
                severity="info",
                title=f"Article 20(c) reduces your taxable wages by ${exempt_amount:,.0f}",
                action=f"Apply the $5,000 Article 20(c) exemption: ${wage_income:,.0f} of wages becomes ${taxable_after:,.0f} of treaty-taxable wages. Your Form 1042-S should reflect the exempt amount (usually income code 19 or 20).",
                consequence="If you don't state the exempt amount explicitly on the return, the IRS may not apply the treaty benefit you're entitled to.",
            )
        )
    if wage_income > 0 and federal_withholding <= 0:
        est_liability = int(wage_income * 0.10)
        severity = "warning" if wage_income >= 10000 else "info"
        findings.append(
            _finding(
                rule_id="student_tax_no_withholding",
                severity=severity,
                title="No federal withholding on wage income — you likely owe tax",
                action=f"Confirm with your W-2 whether withholding is truly zero. If it is, budget for roughly ${est_liability:,}+ in federal tax owed with your return. Consider filing Form 1040-ES for the current year to avoid underpayment penalties.",
                consequence="Zero withholding on significant wages usually means a tax balance due at filing plus potential underpayment/estimated-tax penalties.",
            )
        )

    # Scholarship taxability split — IRC §117 distinguishes qualified tuition
    # (excludable) from room/board/incidentals (taxable). Standard nonresident
    # students often miss this and either over-report or under-report.
    if scholarship_income > 0:
        findings.append(
            _finding(
                rule_id="student_tax_scholarship_taxability_split",
                severity="warning",
                title=f"Split your ${scholarship_income:,.0f} scholarship into taxable vs non-taxable portions",
                action=(
                    f"Under IRC §117, scholarship amounts used for qualified tuition and required fees are NON-TAXABLE; "
                    f"amounts used for room, board, travel, and incidentals are TAXABLE wages. Get Form 1042-S from your "
                    f"school (income code 16 typically, with chapter 3 status code 21 for students) and a Form 1098-T to "
                    f"determine the qualified-tuition portion. Without this split, you can't correctly fill line 8 of "
                    f"Form 1040-NR. Sprintax/GLACIER walk through this calculation."
                ),
                consequence="Reporting the entire scholarship as income overpays tax. Reporting nothing under-reports — "
                "if Form 1042-S was issued, the IRS already has the gross figure and will issue a CP2000 notice.",
            )
        )
        if federal_withholding <= 0:
            findings.append(
                _finding(
                    rule_id="student_tax_scholarship_no_withholding",
                    severity="warning",
                    title="Scholarship income with $0 withholding — likely owe tax at filing",
                    action="If any portion of your scholarship is taxable (room/board/etc.), you owe federal tax on it. "
                    "Schools commonly withhold at the 14% NRA rate under IRC §1441 on the taxable portion if 1042-S was "
                    "issued — confirm whether this happened. Otherwise plan for a balance due, and consider Form 1040-ES "
                    "going forward.",
                    consequence="Missing tax on a taxable scholarship portion creates a balance due plus possible "
                    "underpayment penalty under IRC §6654.",
                )
            )
    if total_income > 0 and not taxpayer_id_present:
        findings.append(
            _finding(
                rule_id="student_tax_missing_taxpayer_id",
                severity="critical",
                title="No SSN or ITIN — return will be rejected without one",
                action="Obtain an SSN (if work-authorized) or file Form W-7 to request an ITIN. The W-7 must be filed with the paper 1040-NR return along with original or certified-copy identity documents (passport + visa). This is a filing blocker — do not submit the return without a valid TIN.",
                consequence="The IRS will reject any 1040-NR filed without a valid SSN or ITIN.",
            )
        )
    if claim_treaty_benefit and not has_1042s:
        findings.append(
            _finding(
                rule_id="student_tax_treaty_without_1042s",
                severity="warning",
                title="Treaty benefit claimed without a 1042-S",
                action="If treaty-exempt income was paid, you should have received a Form 1042-S. Confirm with your payer before the return is filed.",
                consequence="A treaty claim without a 1042-S is often challenged and can delay processing.",
            )
        )
    # Country-specific treaty auto-suggestions — don't fire if SPT crossover
    # already warned. Treaty rules differ for STUDENTS vs SCHOLARS.
    is_f1_or_j1 = is_f1_or_j1_student
    suggested_treaty_country: str | None = None
    suggested_treaty_article: str | None = None

    # J-1 scholars/researchers have a separate treaty article family (Teachers
    # & Researchers, typically Article 19/20 across treaties). The most common
    # ones cover compensation for research at a host institution for up to
    # 2 years. Auto-suggest when the country has such an article.
    SCHOLAR_TREATY_BY_COUNTRY: dict[str, tuple[str, str]] = {
        "germany": ("Germany", "Article 20 (Teachers and Researchers) — up to 2 years exempt"),
        "france": ("France", "Article 20 (Teachers and Researchers) — up to 2 years exempt"),
        "italy": ("Italy", "Article 20 (Teachers and Researchers) — up to 2 years exempt"),
        "netherlands": ("Netherlands", "Article 21 (Teachers and Researchers) — up to 2 years exempt"),
        "uk": ("UK", "Article 20A (Teachers and Researchers) — up to 2 years exempt"),
        "united kingdom": ("UK", "Article 20A (Teachers and Researchers) — up to 2 years exempt"),
        "japan": ("Japan", "Article 20 (Teachers and Researchers) — up to 2 years exempt"),
        "korea": ("Korea", "Article 20 (Teachers and Researchers) — up to 2 years exempt"),
        "south korea": ("Korea", "Article 20 (Teachers and Researchers) — up to 2 years exempt"),
        "china": ("China", "Article 19 (Teachers, Professors and Researchers) — up to 3 years exempt"),
    }
    if is_j1_scholar and wage_income > 0 and not claim_treaty_benefit and not spt_crossover_warning:
        match = SCHOLAR_TREATY_BY_COUNTRY.get(country_citizenship_key)
        if match:
            suggested_treaty_country, suggested_treaty_article = match
            findings.append(
                _finding(
                    rule_id="student_tax_scholar_treaty_eligible",
                    severity="warning",
                    title=f"{match[0]}-US Teacher/Researcher treaty article may exempt your stipend",
                    action=(
                        f"As a J-1 research scholar from {match[0]} at a US educational/research institution, "
                        f"you may be eligible to exempt your compensation under {match[1]}. File Form 8233 with your "
                        f"PAYER (not the IRS) to claim the exemption at source going forward, and reference the article "
                        f"on your 1040-NR. The exemption typically applies only if the visit was originally intended to "
                        f"last <=2 years; check the specific treaty article and your DS-2019 program duration."
                    ),
                    consequence=(
                        f"Not claiming this benefit on ${wage_income:,.0f} of stipend income can cost ~$5,000+ "
                        f"in federal tax. Once claimed retroactively on the return, your refund increases accordingly."
                    ),
                )
            )

    if (not claim_treaty_benefit) and is_f1_or_j1 and wage_income > 0 and not spt_crossover_warning:
        if country_citizenship_key == "china":
            exempt = min(5000.0, wage_income)
            taxable_after = max(wage_income - 5000.0, 0.0)
            suggested_treaty_country = "China"
            suggested_treaty_article = "20(c)"
            findings.append(
                _finding(
                    rule_id="student_tax_china_treaty_eligible",
                    severity="info",
                    title="China-US treaty Article 20(c) may reduce your taxable wages by up to $5,000",
                    action=(
                        f"If you're a Chinese national on F-1/J-1 and earned student-type income, Article 20(c) typically exempts up to $5,000/yr. "
                        f"On your ${wage_income:,.0f} of wages, that reduces taxable wages from ${wage_income:,.0f} to ${taxable_after:,.0f}. "
                        f"Confirm eligibility and whether your payer issued a Form 1042-S before claiming."
                    ),
                    consequence=f"Not claiming this benefit on ${exempt:,.0f} of exempt income can cost several hundred dollars of federal tax.",
                )
            )
        elif country_citizenship_key == "india":
            suggested_treaty_country = "India"
            suggested_treaty_article = "Article 21(2) — standard deduction"
            findings.append(
                _finding(
                    rule_id="student_tax_india_treaty_eligible",
                    severity="info",
                    title="India-US treaty may let you claim the standard deduction",
                    action="The India-US income tax treaty uniquely lets Indian students on F-1 claim the standard deduction on 1040-NR (other nationalities generally cannot). Confirm with a nonresident-aware preparer before relying on this.",
                    consequence=f"Missing the standard deduction on ${wage_income:,.0f} of wages can cost ~$1,000+ of federal tax.",
                )
            )

    # FICA exemption reminder — visa-category aware.
    # F-1/J-1 STUDENTS: exempt for 5 calendar years (IRC §3121(b)(19) + nonresident status)
    # J-1 SCHOLARS/RESEARCHERS: exempt for 2 calendar years (same reg, shorter SPT exempt period)
    # Only fire when user is still within the exempt window AND has wages.
    if wage_income > 0 and not spt_crossover_warning:
        if is_f1_or_j1_student:
            findings.append(
                _finding(
                    rule_id="student_tax_fica_exemption_check_student",
                    severity="info",
                    title="Confirm FICA (Social Security / Medicare) was not withheld in error",
                    action="F-1 and J-1 students in their first 5 calendar years in the US are generally exempt from FICA under IRC §3121(b)(19). Check Box 4 (SS tax) and Box 6 (Medicare tax) on your W-2. If FICA was withheld, ask your employer to refund it first; if they refuse, file Form 843 with Form 8316 to claim a refund from the IRS.",
                    consequence="Improperly withheld FICA on a nonresident student's wages commonly costs ~7.65% of gross wages and is recoverable but only if you claim it.",
                )
            )
        elif is_j1_scholar:
            findings.append(
                _finding(
                    rule_id="student_tax_fica_exemption_check_scholar",
                    severity="info",
                    title="Confirm FICA was not withheld — J-1 scholar/researcher exempt window is 2 calendar years",
                    action="J-1 research scholars, teachers, and trainees are exempt from FICA only during their first 2 calendar years in the US (IRC §7701(b)(5)(D)(i) for SPT + §3121(b)(19) FICA exemption). Check Box 4 (SS tax) and Box 6 (Medicare tax) on your W-2. If FICA was withheld during the exempt period, request a refund from your employer or file Form 843 + Form 8316.",
                    consequence="J-1 scholars become subject to FICA in year 3 and beyond. Confusing the J-1 scholar 2-year window with the F-1 student 5-year window can lead to either erroneous refund claims (which the IRS rejects) or missed refunds.",
                )
            )

    # California (and a few other states) do not conform to federal tax treaties.
    # If the user is in CA and claims (or is suggested) a treaty benefit, the
    # state treats the income as fully taxable.
    state_for_residence = state_of_residence or (
        # Try to infer from school address (e.g., Caltech is CA)
        "CA" if "california" in str(intake_data.get("school_address") or "").lower() else ""
    )
    NONCONFORMING_STATES = {"CA", "NJ", "PA", "AL", "MS"}
    will_claim_treaty = claim_treaty_benefit or suggested_treaty_country is not None
    if state_for_residence in NONCONFORMING_STATES and will_claim_treaty and wage_income > 0:
        findings.append(
            _finding(
                rule_id="student_tax_state_treaty_nonconformity",
                severity="warning",
                title=f"{state_for_residence} does not conform to federal tax treaties — full income remains state-taxable",
                action=(
                    f"Even if you claim a federal treaty exemption, {state_for_residence} (and a few other states) require "
                    f"you to report the FULL untreated income amount on the state return. Compute state tax on the gross "
                    f"compensation, not the federal-treaty-reduced amount. Use the appropriate {state_for_residence} "
                    f"nonresident form."
                ),
                consequence=f"Underpaying state tax by basing it on federal treaty-exempt amounts can trigger {state_for_residence} "
                f"FTB/DOR notices and back-tax assessments.",
            )
        )

    if state_of_residence and state_of_employer and state_of_residence != state_of_employer:
        # Name-specific state forms for the most common multi-state student cases
        _STATE_FORM_HINT = {
            "CA": "Form 540NR (Franchise Tax Board, ftb.ca.gov)",
            "NY": "Form IT-203 (NY DTF, tax.ny.gov)",
            "MA": "Form 1-NR/PY (Mass DOR, mass.gov/dor)",
            "IL": "Form IL-1040 + Schedule NR (Illinois DOR, tax.illinois.gov)",
            "NJ": "Form NJ-1040NR (NJ Division of Taxation, nj.gov/treasury/taxation)",
            "TX": "no state income tax",
            "FL": "no state income tax",
            "WA": "no state income tax",
        }
        res_form = _STATE_FORM_HINT.get(state_of_residence, f"{state_of_residence}'s nonresident income tax return")
        emp_form = _STATE_FORM_HINT.get(state_of_employer, f"{state_of_employer}'s nonresident income tax return")
        findings.append(
            _finding(
                rule_id="student_tax_multistate_income",
                severity="info",
                title="Employer state differs from your state of residence",
                action=(
                    f"You likely need to file in both states. Resident state ({state_of_residence}): {res_form}. "
                    f"Employer state ({state_of_employer}): {emp_form}. If all work was physically performed in your "
                    f"state of residence ({state_of_residence}), the employer state may have no sourcing claim — confirm "
                    f"the physical-presence rule for {state_of_employer} before filing there."
                ),
                consequence="Missing state returns can lead to back-tax notices from the state revenue department.",
            )
        )

    form_8843_inputs = {
        "tax_year": tax_year,
        "full_name": full_name,
        "visa_type": visa_type,
        "school_name": school_name,
        "country_citizenship": country_citizenship,
        "country_passport": intake_data.get("country_passport") or country_citizenship,
        "passport_number": intake_data.get("passport_number"),
        "arrival_date": intake_data.get("arrival_date"),
        "school_address": intake_data.get("school_address"),
        "school_contact": intake_data.get("school_contact"),
        "program_director": intake_data.get("program_director"),
        "days_present_current": intake_data.get("days_present_current") or 0,
        "days_present_year_1_ago": intake_data.get("days_present_year_1_ago") or 0,
        "days_present_year_2_ago": intake_data.get("days_present_year_2_ago") or 0,
        "filing_with_tax_return": True,
        "has_us_income": True,
    }
    filing_context = build_form_8843_filing_context(form_8843_inputs)

    artifacts_dir = STUDENT_TAX_DIR / order_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    form_8843_path = artifacts_dir / "form-8843.pdf"
    form_8843_path.write_bytes(generate_form_8843(form_8843_inputs))

    package_lines = [
        f"Student tax package for {tax_year}",
        "",
        f"Client: {full_name}",
        f"School: {school_name}",
        f"Visa status: {visa_type}",
        f"Citizenship: {country_citizenship}",
        "",
        "Income summary",
        f"- Wage income: ${wage_income:,.2f}",
        f"- Scholarship income: ${scholarship_income:,.2f}",
        f"- Other income: ${other_income:,.2f}",
        f"- Federal withholding: ${federal_withholding:,.2f}",
        f"- State withholding: ${state_withholding:,.2f}",
        f"- Total income reviewed: ${total_income:,.2f}",
        "",
        "Filing posture",
        "- Form 8843 should be included with the 1040-NR package.",
        f"- Filing deadline: {deadline.isoformat()}",
        "- Review treaty eligibility before claiming any exemption or reduced withholding benefit.",
        "",
        "Guardian checks",
    ]
    package_lines.extend(
        [f"- {finding['title']}: {finding['action']}" for finding in findings]
        or ["- No major nonresident-student filing flags were detected from the intake you entered."]
    )
    package_lines.extend(
        [
            "",
            "Next steps",
            "- Review the package summary against your W-2 and any 1042-S statements.",
            "- Complete the 1040-NR return using the same tax-year figures reflected here.",
            "- Attach Form 8843 to the return package before filing.",
        ]
    )

    package_path = artifacts_dir / "1040nr-package-summary.pdf"
    package_path.write_bytes(
        build_text_pdf(
            "Student Tax Package Summary",
            package_lines,
            subtitle=f"Tax year {tax_year}",
        )
    )

    if spt_crossover_warning:
        # When SPT crossover fires, the user is likely a RESIDENT alien and
        # neither 1040-NR nor Form 8843 applies. Relabel artifacts as
        # advisor-review-only to prevent the user from filing the wrong form.
        artifacts = [
            {
                "label": "Download 1040-NR package summary (REVIEW ONLY — wrong form if you are a resident alien)",
                "filename": package_path.name,
                "path": str(package_path),
            },
            {
                "label": "Download Form 8843 (REVIEW ONLY — does not apply to resident aliens)",
                "filename": form_8843_path.name,
                "path": str(form_8843_path),
            },
        ]
    else:
        artifacts = [
            {
                "label": "Download 1040-NR package summary",
                "filename": package_path.name,
                "path": str(package_path),
            },
            {
                "label": "Download Form 8843",
                "filename": form_8843_path.name,
                "path": str(form_8843_path),
            },
        ]

    if claim_treaty_benefit:
        treaty_lines = [
            f"Treaty country: {treaty_country or 'Confirm with preparer'}",
            f"Treaty article: {treaty_article or 'Confirm with preparer'}",
            "",
            "Guardian note",
            "Treaty claims should be checked against the current treaty text and the specific income category before filing.",
            "Use this memo as a review aid, not as a substitute for the actual treaty form or statement required by the return package.",
        ]
        treaty_path = artifacts_dir / "treaty-benefit-review-memo.pdf"
        treaty_path.write_bytes(build_text_pdf("Treaty Benefit Review Memo", treaty_lines))
        artifacts.append(
            {
                "label": "Download treaty review memo",
                "filename": treaty_path.name,
                "path": str(treaty_path),
            }
        )

    critical_count = sum(1 for f in findings if f["severity"] == "critical")
    warning_count = sum(1 for f in findings if f["severity"] == "warning")
    info_count = sum(1 for f in findings if f["severity"] == "info")
    has_blockers = critical_count > 0
    # Brand the package by visa category — "student tax package" is wrong for J-1 scholars.
    if is_j1_scholar:
        package_name = "nonresident scholar tax package"
    elif is_f1_or_j1_student:
        package_name = "student tax package"
    else:
        package_name = "nonresident tax package"

    if has_blockers:
        summary = (
            f"Your {package_name} for tax year {tax_year} has been prepared, but Guardian found "
            f"{critical_count} blocking issue{'s' if critical_count != 1 else ''} that must be resolved before you file. "
            f"{len(findings)} total finding{'s' if len(findings) != 1 else ''} — resolve the critical ones first."
        )
    elif warning_count > 0:
        summary = (
            f"Your {package_name} for tax year {tax_year} is ready. "
            f"Guardian prepared the Form 8843 attachment, a 1040-NR package summary, and "
            f"flagged {warning_count} issue{'s' if warning_count != 1 else ''} worth checking before filing"
            f"{f', plus {info_count} optimization tip' if info_count == 1 else (f', plus {info_count} optimization tips' if info_count else '')}."
        )
    elif info_count > 0:
        summary = (
            f"Your {package_name} for tax year {tax_year} is ready. "
            f"Guardian prepared the Form 8843 attachment and a 1040-NR package summary, and surfaced "
            f"{info_count} tip{'s' if info_count != 1 else ''} that could save you money or clarify next steps."
        )
    else:
        summary = (
            f"Your {package_name} for tax year {tax_year} is ready. "
            f"Guardian prepared the Form 8843 attachment and a 1040-NR package summary. No issues flagged."
        )

    next_steps = []
    if has_blockers:
        next_steps.append(
            "Resolve the critical findings above before filing. Do not submit the return until every blocker is addressed."
        )
    # Choose document references to match the actual income shape
    income_docs = []
    if wage_income > 0:
        income_docs.append("W-2")
    if scholarship_income > 0:
        income_docs.append("1042-S and 1098-T")
    if other_income > 0:
        income_docs.append("1099 / 1042-S")
    docs_phrase = " and ".join(income_docs) if income_docs else "any tax statements you received"
    next_steps.extend([
        f"Review the 1040-NR package summary against your {docs_phrase}.",
        "Prepare the 1040-NR using nonresident-aware software (Sprintax or GLACIER Tax Prep) or a CPA familiar with nonresident filings — standard consumer software (TurboTax, H&R Block, FreeTaxUSA) cannot produce a valid 1040-NR.",
        f"File the return package by {deadline.isoformat()} and attach Form 8843.",
    ])
    if claim_treaty_benefit:
        next_steps.insert(
            -1,
            "Claim the treaty benefit explicitly on the return, reference the article, and attach Form 8833 if a treaty-based position requires disclosure."
        )

    return {
        "summary": summary,
        "findings": findings,
        "finding_count": len(findings),
        "next_steps": next_steps,
        "filing_deadline": deadline.isoformat(),
        "mailing_instructions": {
            "headline": str(filing_context.get("headline") or ""),
            "summary": str(filing_context.get("summary") or ""),
            "steps": [str(step) for step in filing_context.get("steps", [])],
        },
        "artifacts": artifacts,
        "filing_context": serialize_filing_context(filing_context),
        "claim_treaty_benefit": claim_treaty_benefit,
        "treaty_country": treaty_country or None,
        "treaty_article": treaty_article or None,
        "suggested_treaty_country": suggested_treaty_country,
        "suggested_treaty_article": suggested_treaty_article,
        "total_income_usd": total_income,
    }
