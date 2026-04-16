"""H-1B document check service."""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from compliance_os.web.models.database import DATA_DIR
from compliance_os.web.services.comparator import compare_fields
from compliance_os.web.services.pdf_builder import build_text_pdf
from compliance_os.web.services.pdf_reader import extract_first_page
from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine


H1B_DOC_CHECK_DIR = DATA_DIR / "marketplace" / "h1b_doc_check"
RULE_PATH = Path(__file__).resolve().parents[3] / "config" / "rules" / "h1b_doc_check.yaml"

H1B_FILE_FIELDS = {
    "h1b_registration_file": "h1b_registration",
    "h1b_status_summary_file": "h1b_status_summary",
    "h1b_g28_file": "h1b_g28",
    "h1b_filing_invoice_file": "h1b_filing_invoice",
    "h1b_filing_fee_receipt_file": "h1b_filing_fee_receipt",
}

# Plain-language labels the end user can recognize when uploading. Keep in
# sync with H1B_FILE_FIELDS — these are user-facing.
DOC_TYPE_LABELS: dict[str, str] = {
    "h1b_registration": "H-1B registration record (USCIS registration confirmation for the beneficiary)",
    "h1b_status_summary": "Status summary from the attorney or employer summarizing registration and filing window dates",
    "h1b_g28": "Form G-28 (attorney's Notice of Entry of Appearance representing the petitioner)",
    "h1b_filing_invoice": "Filing invoice from the attorney or vendor listing fees owed for the petition",
    "h1b_filing_fee_receipt": "Payment receipt for the USCIS filing fee (credit-card or ACH confirmation)",
}

_DOC_PATTERNS: dict[str, dict[str, str]] = {
    "h1b_registration": {
        "registration_number": r"Registration Number:\s*([^\r\n]+)",
        "employer_name": r"Employer Name:\s*([^\r\n]+)",
        "employer_ein": r"Employer EIN:\s*([^\r\n]+)",
        "authorized_individual_name": r"Authorized Individual Name:\s*([^\r\n]+)",
        "authorized_individual_title": r"Authorized Individual Title:\s*([^\r\n]+)",
    },
    "h1b_status_summary": {
        "status_title": r"Status Title:\s*([^\r\n]+)",
        "registration_window_end_date": r"Registration Window End Date:\s*([^\r\n]+)",
        "petition_filing_window_end_date": r"Petition Filing Window End Date:\s*([^\r\n]+)",
        "employment_start_date": r"Employment Start Date:\s*([^\r\n]+)",
        "law_firm_name": r"Law Firm Name:\s*([^\r\n]+)",
    },
    "h1b_g28": {
        "representative_name": r"Representative Name:\s*([^\r\n]+)",
        "law_firm_name": r"Law Firm Name:\s*([^\r\n]+)",
        "representative_email": r"Representative Email:\s*([^\r\n]+)",
        "client_name": r"Client Name:\s*([^\r\n]+)",
        "client_entity_name": r"Client Entity Name:\s*([^\r\n]+)",
        "client_email": r"Client Email:\s*([^\r\n]+)",
    },
    "h1b_filing_invoice": {
        "invoice_number": r"Invoice Number:\s*([^\r\n]+)",
        "invoice_date": r"Invoice Date:\s*([^\r\n]+)",
        "petitioner_name": r"Petitioner Name:\s*([^\r\n]+)",
        "beneficiary_name": r"Beneficiary Name:\s*([^\r\n]+)",
        "total_due_amount": r"Total Due Amount:\s*([^\r\n]+)",
        # Fee breakdown — useful for comparing to actual receipts. See also
        # _derive_invoice_total_charged below, which sums these into a
        # 'total_charged' field the comparator can actually use.
        "legal_fee_amount": r"Legal Fee(?: Amount)?:\s*([^\r\n]+)",
        "uscis_fee_amount": r"USCIS Fee(?: Amount)?:\s*([^\r\n]+)",
        "payment_status": r"Payment Status:\s*([^\r\n]+)",
    },
    "h1b_filing_fee_receipt": {
        "transaction_id": r"Transaction ID:\s*([^\r\n]+)",
        "transaction_date": r"Transaction Date:\s*([^\r\n]+)",
        "response_message": r"Response Message:\s*([^\r\n]+)",
        "approval_code": r"Approval Code:\s*([^\r\n]+)",
        "cardholder_name": r"Cardholder Name:\s*([^\r\n]+)",
        "amount": r"Amount:\s*([^\r\n]+)",
        "description": r"Description:\s*([^\r\n]+)",
    },
}


# USCIS H-1B registration numbers have an H1B prefix and a multi-character
# identifier. The extraction regex sometimes grabs a literal label fragment
# like "H-1B#" from a multi-line PDF. This validator accepts reasonable
# formats (H1B..., H1BR...) with at least 3 identifying characters after
# the prefix, and rejects obvious garbage like "H1B#" or bare prefixes.
_REGISTRATION_NUMBER_RE = re.compile(
    r"^(H1BR?|H-1B)[-_]?[A-Z0-9][A-Z0-9\-_]{2,}$",
    re.IGNORECASE,
)


def _looks_like_registration_number(value: str) -> bool:
    cleaned = re.sub(r"[\s]", "", value)
    if not _REGISTRATION_NUMBER_RE.match(cleaned):
        return False
    # Require at least one digit somewhere — real numbers always have them.
    return bool(re.search(r"\d", cleaned))


def _parse_money(value: Any) -> float | None:
    if value is None:
        return None
    raw = re.sub(r"[,$\s]", "", str(value))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _derive_invoice_total_charged(fields: dict[str, Any]) -> float | None:
    """Compute what the invoice actually CHARGED (legal + USCIS fees), NOT the
    residual balance. 'total_due_amount' on a paid invoice is 0 — meaningless to
    compare against a receipt that shows the actual payment."""
    legal = _parse_money(fields.get("legal_fee_amount"))
    uscis = _parse_money(fields.get("uscis_fee_amount"))
    if legal is None and uscis is None:
        return None
    return (legal or 0.0) + (uscis or 0.0)


def _has_filing_evidence(fields: dict[str, Any]) -> bool:
    """Does the receipt show the user already successfully filed?"""
    approval = str(fields.get("approval_code") or "").strip()
    response = str(fields.get("response_message") or "").strip().lower()
    txn_id = str(fields.get("transaction_id") or "").strip()
    return bool(approval) or response in {"approval", "approved", "success"} or bool(txn_id)


def _extract_value(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def extract_h1b_document_fields(doc_type: str, text: str) -> dict[str, Any]:
    patterns = _DOC_PATTERNS.get(doc_type, {})
    fields: dict[str, Any] = {}
    for field_name, pattern in patterns.items():
        value = _extract_value(pattern, text)
        if not value:
            continue
        # Post-extraction validation: reject obviously malformed matches so the
        # regex doesn't silently hand rules a label fragment instead of a real
        # value. Today we only validate registration_number; extend per field
        # as other brittle formats surface.
        if field_name == "registration_number" and not _looks_like_registration_number(value):
            continue
        fields[field_name] = value
    return fields


def _read_document_text(path: Path) -> str:
    """Read a document's text. Uses pdfreader for PDFs, read_text for everything else."""
    if path.suffix.lower() == ".pdf":
        return extract_first_page(str(path))
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def save_uploaded_document(order_id: str, filename: str, content: bytes) -> Path:
    order_dir = H1B_DOC_CHECK_DIR / order_id / "uploads"
    order_dir.mkdir(parents=True, exist_ok=True)
    path = order_dir / filename
    path.write_bytes(content)
    return path


@lru_cache(maxsize=1)
def _engine() -> RuleEngine:
    return RuleEngine.from_yaml(RULE_PATH)


def _parse_iso_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    match = re.search(r"\d{4}-\d{2}-\d{2}", raw)
    return match.group(0) if match else None


def process_h1b_doc_check(order_id: str, intake_data: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    documents = intake_data.get("documents") or []
    extracted: dict[str, dict[str, Any]] = {}
    document_summary: list[dict[str, Any]] = []

    for document in documents:
        doc_type = str(document["doc_type"])
        provided_fields = document.get("fields")
        if isinstance(provided_fields, dict) and provided_fields:
            fields = {
                str(field_name): value
                for field_name, value in provided_fields.items()
                if value not in (None, "")
            }
        else:
            path = Path(str(document["path"]))
            text = _read_document_text(path)
            fields = extract_h1b_document_fields(doc_type, text)
        extracted[doc_type] = fields
        document_summary.append(
            {
                "doc_type": doc_type,
                "filename": document["filename"],
                "fields": fields,
            }
        )

    registration = extracted.get("h1b_registration", {})
    status_summary = extracted.get("h1b_status_summary", {})
    g28 = extracted.get("h1b_g28", {})
    invoice = extracted.get("h1b_filing_invoice", {})
    receipt = extracted.get("h1b_filing_fee_receipt", {})

    # For invoice↔receipt amount, compare what the invoice CHARGED (sum of
    # legal + USCIS fees) against the receipt's payment amount. Using
    # 'total_due_amount' is wrong for paid invoices — a paid invoice shows 0
    # due, which never matches the receipt. If the invoice has no itemized
    # fees AND its residual balance is 0 (indicating it's been paid), skip
    # the comparison entirely — we have no meaningful invoice total to check.
    invoice_total_charged = _derive_invoice_total_charged(invoice)
    if invoice_total_charged is not None:
        invoice_compare_amount: float | None = invoice_total_charged
    else:
        due_raw = _parse_money(invoice.get("total_due_amount"))
        payment_status = str(invoice.get("payment_status") or "").strip().lower()
        looks_already_paid = due_raw == 0.0 or "paid" in payment_status
        invoice_compare_amount = None if looks_already_paid else due_raw

    # Only run comparisons where both source documents were uploaded. Running
    # a "mismatch" rule against a None value produces needs_review which fires
    # the same rule as an actual mismatch — that's how phantom "Entity names
    # don't align" findings appeared against a G-28 that was never uploaded.
    comparison_specs = [
        ("h1b_registration_g28_entity_name",
         registration.get("employer_name"), g28.get("client_entity_name"), "entity"),
        ("h1b_registration_invoice_petitioner_name",
         registration.get("employer_name"), invoice.get("petitioner_name"), "entity"),
        ("h1b_registration_receipt_signatory_name",
         registration.get("authorized_individual_name"), receipt.get("cardholder_name"), "fuzzy"),
        ("h1b_invoice_receipt_amount",
         invoice_compare_amount, _parse_money(receipt.get("amount")), "numeric"),
    ]
    comparisons: dict[str, dict[str, Any]] = {}
    for name, value_a, value_b, match_type in comparison_specs:
        if value_a in (None, "") or value_b in (None, ""):
            continue
        comparison = compare_fields(name, value_a, value_b, match_type)
        comparisons[name] = asdict(comparison)

    # PEO / staffing detection: if invoice.petitioner differs from
    # registration.employer BUT matches g28.client_entity, the petitioner on
    # the invoice is likely the PEO/staffing company that filed on behalf of
    # the end-client employer. Suppress the mismatch and emit a softer context
    # finding instead of a false-positive critical.
    invoice_petitioner = invoice.get("petitioner_name")
    g28_entity = g28.get("client_entity_name")
    reg_employer = registration.get("employer_name")
    inv_reg_comparison = comparisons.get("h1b_registration_invoice_petitioner_name", {})
    if (
        inv_reg_comparison.get("status") in ("mismatch", "needs_review")
        and invoice_petitioner and g28_entity and reg_employer
    ):
        g28_vs_invoice = compare_fields("_peo_check", invoice_petitioner, g28_entity, "entity")
        if g28_vs_invoice.status == "match":
            comparisons.pop("h1b_registration_invoice_petitioner_name", None)

    reference_day = today or date.today()
    petition_window_end = _parse_iso_date(status_summary.get("petition_filing_window_end_date"))

    # Amendment / change-of-employer detection. If status_summary status_title
    # signals "Amended" / "Transfer" / "Change of Employer", the registration
    # may name the PRIOR employer while G-28 / invoice name the new one.
    # Treating this as a single-employer entity-mismatch produces actively
    # harmful advice (the Claude judge caught this).
    status_title = str(status_summary.get("status_title") or "").lower()
    is_amendment_or_transfer = any(
        kw in status_title for kw in ("amend", "transfer", "change of employer", "porting")
    )
    if is_amendment_or_transfer:
        # Suppress entity comparisons that would compare old vs new employer
        comparisons.pop("h1b_registration_g28_entity_name", None)
        comparisons.pop("h1b_registration_invoice_petitioner_name", None)
        # Cross-check the NEW-employer documents against each other instead:
        # G-28 client_entity_name should match invoice petitioner_name.
        g28_entity = g28.get("client_entity_name")
        invoice_petitioner = invoice.get("petitioner_name")
        if g28_entity and invoice_petitioner:
            new_employer_compare = compare_fields(
                "h1b_g28_invoice_entity_name", g28_entity, invoice_petitioner, "entity",
            )
            comparisons["h1b_g28_invoice_entity_name"] = asdict(new_employer_compare)

    # If the receipt shows filing evidence (transaction ID + approval), the
    # user has already filed. That flips the framing of several rules — e.g.,
    # 'petition window closed' is a warning to BLOCK a filing when you haven't
    # filed, but merely a timeline fact when you already did.
    already_filed = _has_filing_evidence(receipt)

    answers = {
        "registration_number": registration.get("registration_number"),
        "petition_window_closed": bool(petition_window_end and petition_window_end < reference_day.isoformat()),
        "already_filed": already_filed,
        "missing_registration_packet": not registration,
        "missing_g28": not g28,
        "missing_invoice": not invoice,
        "missing_receipt": not receipt,
        "is_amendment_or_transfer": is_amendment_or_transfer,
    }

    findings = [asdict(finding) for finding in _engine().evaluate(EvaluationContext(
        answers=answers,
        extraction_a={},
        extraction_b={},
        comparisons=comparisons,
        today=reference_day,
    ))]

    if is_amendment_or_transfer:
        # Inject amendment-specific context that the rule engine can't easily
        # express (cross-cutting documentation requirements per 8 CFR §214.2(h)
        # and AC21 portability under INA §214(n)).
        findings.append({
            "rule_id": "h1b_amendment_context",
            "severity": "warning",
            "category": "amendment",
            "title": "Amendment / change-of-employer petition — entity-name mismatches are expected, but this packet needs amendment-specific documents",
            "action": (
                "Because this is an amendment/transfer, expect the original USCIS registration to name the prior employer. "
                "An adjudicator will want: (1) a NEW or recently-certified LCA from the new employer (ETA Form 9035), "
                "(2) the I-797 approval notice from the prior H-1B petition as proof of valid status, "
                "(3) current I-94 record, "
                "(4) the new employer's support / specialty-occupation letter, "
                "(5) the new employer's own H-1B registration receipt if cap-subject. "
                "Also confirm AC21 portability eligibility under INA §214(n) — the beneficiary can begin work for the new "
                "employer once USCIS receives a properly-filed amendment, but only if the prior status was valid at the time."
            ),
            "consequence": "Without the new employer's LCA and prior-approval evidence, USCIS will RFE or deny — and any work "
            "performed for the new employer before the amendment is properly filed may be unauthorized employment under "
            "INA §274A.",
            "immigration_impact": True,
        })

    severity_counts = {
        severity: sum(1 for finding in findings if finding["severity"] == severity)
        for severity in ("critical", "warning", "info")
    }

    expected_doc_types = list(H1B_FILE_FIELDS.values())
    uploaded_doc_types = {document["doc_type"] for document in document_summary}
    missing_doc_types = [dt for dt in expected_doc_types if dt not in uploaded_doc_types]
    packet_complete = not missing_doc_types

    if not packet_complete and len(documents) < 3:
        verdict = "incomplete"
    elif severity_counts["critical"] > 0:
        verdict = "block"
    elif severity_counts["warning"] > 0:
        verdict = "investigate"
    else:
        verdict = "pass"

    verdict_label = {
        "pass": "PASS — packet looks internally consistent",
        "investigate": "INVESTIGATE — warnings found, review before filing",
        "block": "BLOCK — critical issues found, do not file as-is",
        "incomplete": "INCOMPLETE — upload remaining documents before filing",
    }[verdict]

    if verdict == "incomplete":
        summary = (
            f"Only {len(documents)} of {len(expected_doc_types)} expected H-1B packet documents were uploaded. "
            f"Upload the remaining documents ("
            + ", ".join(DOC_TYPE_LABELS.get(dt, dt) for dt in missing_doc_types)
            + ") and re-run the check — cross-checks are unreliable on partial packets."
        )
        next_steps = [
            f"Upload the {DOC_TYPE_LABELS.get(dt, dt)}"
            for dt in missing_doc_types
        ]
    else:
        summary = (
            f"Guardian reviewed {len(documents)} of {len(expected_doc_types)} H-1B packet documents and found "
            f"{severity_counts['critical']} critical, {severity_counts['warning']} warning, "
            f"and {severity_counts['info']} informational items."
        )
        next_steps = [finding["action"] for finding in findings[:4]]
        if missing_doc_types:
            next_steps.extend(
                f"Upload the {DOC_TYPE_LABELS.get(dt, dt)} and re-run the check — this document was not provided."
                for dt in missing_doc_types
            )
        if not next_steps:
            next_steps = [
                "Packet is internally consistent. Confirm your attorney has the original signed G-28 (Notice of Entry of Appearance) on file before USCIS submission.",
                "Verify the employer is actively enrolled in E-Verify — this is required for STEM OPT continuity cases and a frequent USCIS Request-for-Evidence (RFE) trigger on H-1B petitions.",
                "Keep the original receipt notice and track petition status at egov.uscis.gov using the receipt number (IOE/EAC/WAC/LIN/SRC format).",
            ]

    report_lines = [
        f"Verdict: {verdict_label}",
        "",
        f"Packet completeness: {len(uploaded_doc_types)} of {len(expected_doc_types)} documents uploaded",
    ]
    if missing_doc_types:
        report_lines.append(f"  Missing: {', '.join(missing_doc_types)}")
    report_lines.extend([
        "",
        "Snapshot",
        summary,
        "",
        "Findings",
    ])
    for finding in findings:
        report_lines.extend(
            [
                f"{finding['severity'].upper()} - {finding['title']}",
                f"Action: {finding['action']}",
                f"Why it matters: {finding['consequence']}",
                "",
            ]
        )
    report_lines.append("Document summary")
    for document in document_summary:
        report_lines.append(f"{document['doc_type']}: {document['filename']}")
        for field_name, value in document["fields"].items():
            report_lines.append(f"  {field_name}: {value}")
        report_lines.append("")

    artifacts_dir = H1B_DOC_CHECK_DIR / order_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / "h1b-doc-check-report.pdf"
    report_path.write_bytes(build_text_pdf("H-1B Document Check Report", report_lines))

    return {
        "summary": summary,
        "verdict": verdict,
        "packet_complete": packet_complete,
        "missing_doc_types": missing_doc_types,
        "findings": findings,
        "finding_count": len(findings),
        "document_summary": document_summary,
        "comparisons": list(comparisons.values()),
        "next_steps": next_steps,
        "artifacts": [
            {
                "label": "Download H-1B review report",
                "filename": report_path.name,
                "path": str(report_path),
            }
        ],
    }
