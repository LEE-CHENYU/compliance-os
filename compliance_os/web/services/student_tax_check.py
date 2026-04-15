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

    findings: list[dict[str, Any]] = []
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
        # Estimate ballpark federal liability: roughly 10-12% on wages under $50K
        # for a nonresident, ignoring treaty. Use 10% as a conservative floor.
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
    # Country-specific treaty auto-suggestions (flagged for users who haven't
    # claimed a benefit they're likely eligible for). Do not auto-apply — the
    # user should make an informed election.
    is_f1_or_j1 = visa_type.upper().replace(" ", "").startswith(("F-1", "F1", "J-1", "J1"))
    suggested_treaty_country: str | None = None
    suggested_treaty_article: str | None = None
    if (not claim_treaty_benefit) and is_f1_or_j1 and wage_income > 0:
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

    # F-1/J-1 FICA exemption reminder — students in first 5 calendar years are
    # generally exempt. Payroll errors are common and the refund path (Form 843)
    # is often missed.
    if is_f1_or_j1 and wage_income > 0:
        findings.append(
            _finding(
                rule_id="student_tax_fica_exemption_check",
                severity="info",
                title="Confirm FICA (Social Security / Medicare) was not withheld in error",
                action="F-1 and J-1 students in their first 5 calendar years in the US are generally exempt from FICA. Check Box 4 (SS tax) and Box 6 (Medicare tax) on your W-2. If FICA was withheld, ask your employer to refund it first; if they refuse, you can file Form 843 with Form 8316 to claim a refund from the IRS.",
                consequence="Improperly withheld FICA on a nonresident student's wages commonly costs ~7.65% of gross wages and is recoverable but only if you claim it.",
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
    if has_blockers:
        summary = (
            f"Your student tax package for tax year {tax_year} has been prepared, but Guardian found "
            f"{critical_count} blocking issue{'s' if critical_count != 1 else ''} that must be resolved before you file. "
            f"{len(findings)} total finding{'s' if len(findings) != 1 else ''} — resolve the critical ones first."
        )
    elif warning_count > 0:
        summary = (
            f"Your student tax package for tax year {tax_year} is ready. "
            f"Guardian prepared the Form 8843 attachment, a 1040-NR package summary, and "
            f"flagged {warning_count} issue{'s' if warning_count != 1 else ''} worth checking before filing"
            f"{f', plus {info_count} optimization tip' if info_count == 1 else (f', plus {info_count} optimization tips' if info_count else '')}."
        )
    elif info_count > 0:
        summary = (
            f"Your student tax package for tax year {tax_year} is ready. "
            f"Guardian prepared the Form 8843 attachment and a 1040-NR package summary, and surfaced "
            f"{info_count} tip{'s' if info_count != 1 else ''} that could save you money or clarify next steps."
        )
    else:
        summary = (
            f"Your student tax package for tax year {tax_year} is ready. "
            f"Guardian prepared the Form 8843 attachment and a 1040-NR package summary. No issues flagged."
        )

    next_steps = []
    if has_blockers:
        next_steps.append(
            "Resolve the critical findings above before filing. Do not submit the return until every blocker is addressed."
        )
    next_steps.extend([
        "Review the 1040-NR package summary against your W-2, 1042-S, and payroll records.",
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
