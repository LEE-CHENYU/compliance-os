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
        findings.append(
            _finding(
                rule_id="student_tax_resident_software",
                severity="critical",
                title="Resident-return software may route you to Form 1040 instead of 1040-NR",
                action="Double-check that your preparer or software is using the nonresident return path before filing.",
                consequence="Filing Form 1040 instead of 1040-NR can create residency-status mistakes and amendment work later.",
            )
        )
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
    if wage_income > 0 and federal_withholding <= 0:
        findings.append(
            _finding(
                rule_id="student_tax_no_withholding",
                severity="info",
                title="No federal withholding entered for wage income",
                action="Check your W-2 or payroll records to confirm whether withholding is truly zero.",
                consequence="Missing withholding data can distort the draft payment/refund expectation in the package summary.",
            )
        )
    if total_income > 0 and not taxpayer_id_present:
        findings.append(
            _finding(
                rule_id="student_tax_missing_taxpayer_id",
                severity="warning",
                title="No SSN or ITIN entered",
                action="A 1040-NR return requires an SSN or ITIN on the return. If you do not have one, file Form W-7 to request an ITIN alongside the return.",
                consequence="A return filed without a valid SSN/ITIN will be rejected by the IRS.",
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
    if state_of_residence and state_of_employer and state_of_residence != state_of_employer:
        findings.append(
            _finding(
                rule_id="student_tax_multistate_income",
                severity="info",
                title="Employer state differs from your state of residence",
                action=f"You may need to file part-year or nonresident state returns for both {state_of_residence} and {state_of_employer}. Check each state's nonresident filing rules.",
                consequence="Missing state returns can lead to back-tax notices from the state revenue department.",
            )
        )

    full_name = str(intake_data.get("full_name") or "").strip()
    visa_type = str(intake_data.get("visa_type") or "F-1").strip() or "F-1"
    school_name = str(intake_data.get("school_name") or "").strip()
    country_citizenship = str(intake_data.get("country_citizenship") or "").strip()

    form_8843_inputs = {
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

    summary = (
        f"Your student tax package for tax year {tax_year} is ready. "
        f"Guardian prepared the Form 8843 attachment, a 1040-NR package summary, and "
        f"flagged {len(findings)} issue{'s' if len(findings) != 1 else ''} worth checking before filing."
    )
    next_steps = [
        "Review the 1040-NR package summary against your W-2, 1042-S, and payroll records.",
        "Complete the 1040-NR return using the same numbers reflected in the package summary.",
        f"File the return package by {deadline.isoformat()} and attach Form 8843.",
    ]
    if claim_treaty_benefit:
        next_steps.insert(2, "Confirm the treaty article and support before claiming treaty benefits in the return package.")

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
        "total_income_usd": total_income,
    }
