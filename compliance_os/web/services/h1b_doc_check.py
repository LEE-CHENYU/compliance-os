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

_DOC_PATTERNS: dict[str, dict[str, str]] = {
    "h1b_registration": {
        "registration_number": r"Registration Number:\s*(.+)",
        "employer_name": r"Employer Name:\s*(.+)",
        "employer_ein": r"Employer EIN:\s*(.+)",
        "authorized_individual_name": r"Authorized Individual Name:\s*(.+)",
        "authorized_individual_title": r"Authorized Individual Title:\s*(.+)",
    },
    "h1b_status_summary": {
        "status_title": r"Status Title:\s*(.+)",
        "registration_window_end_date": r"Registration Window End Date:\s*(.+)",
        "petition_filing_window_end_date": r"Petition Filing Window End Date:\s*(.+)",
        "employment_start_date": r"Employment Start Date:\s*(.+)",
        "law_firm_name": r"Law Firm Name:\s*(.+)",
    },
    "h1b_g28": {
        "representative_name": r"Representative Name:\s*(.+)",
        "law_firm_name": r"Law Firm Name:\s*(.+)",
        "representative_email": r"Representative Email:\s*(.+)",
        "client_name": r"Client Name:\s*(.+)",
        "client_entity_name": r"Client Entity Name:\s*(.+)",
        "client_email": r"Client Email:\s*(.+)",
    },
    "h1b_filing_invoice": {
        "invoice_number": r"Invoice Number:\s*(.+)",
        "invoice_date": r"Invoice Date:\s*(.+)",
        "petitioner_name": r"Petitioner Name:\s*(.+)",
        "beneficiary_name": r"Beneficiary Name:\s*(.+)",
        "total_due_amount": r"Total Due Amount:\s*(.+)",
    },
    "h1b_filing_fee_receipt": {
        "transaction_id": r"Transaction ID:\s*(.+)",
        "transaction_date": r"Transaction Date:\s*(.+)",
        "response_message": r"Response Message:\s*(.+)",
        "approval_code": r"Approval Code:\s*(.+)",
        "cardholder_name": r"Cardholder Name:\s*(.+)",
        "amount": r"Amount:\s*(.+)",
        "description": r"Description:\s*(.+)",
    },
}


def _extract_value(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def extract_h1b_document_fields(doc_type: str, text: str) -> dict[str, Any]:
    patterns = _DOC_PATTERNS.get(doc_type, {})
    return {
        field: value
        for field, pattern in patterns.items()
        if (value := _extract_value(pattern, text))
    }


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
            text = path.read_text(encoding="utf-8", errors="ignore")
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

    comparisons = {}
    for name, value_a, value_b, match_type in [
        (
            "h1b_registration_g28_entity_name",
            registration.get("employer_name"),
            g28.get("client_entity_name"),
            "fuzzy",
        ),
        (
            "h1b_registration_invoice_petitioner_name",
            registration.get("employer_name"),
            invoice.get("petitioner_name"),
            "fuzzy",
        ),
        (
            "h1b_registration_receipt_signatory_name",
            registration.get("authorized_individual_name"),
            receipt.get("cardholder_name"),
            "fuzzy",
        ),
        (
            "h1b_invoice_receipt_amount",
            invoice.get("total_due_amount"),
            receipt.get("amount"),
            "numeric",
        ),
    ]:
        comparison = compare_fields(name, value_a, value_b, match_type)
        comparisons[name] = asdict(comparison)

    reference_day = today or date.today()
    petition_window_end = _parse_iso_date(status_summary.get("petition_filing_window_end_date"))
    answers = {
        "registration_number": registration.get("registration_number"),
        "petition_window_closed": bool(petition_window_end and petition_window_end < reference_day.isoformat()),
        "missing_registration_packet": not registration,
        "missing_g28": not g28,
        "missing_invoice": not invoice,
        "missing_receipt": not receipt,
    }

    findings = [asdict(finding) for finding in _engine().evaluate(EvaluationContext(
        answers=answers,
        extraction_a={},
        extraction_b={},
        comparisons=comparisons,
        today=reference_day,
    ))]

    severity_counts = {
        severity: sum(1 for finding in findings if finding["severity"] == severity)
        for severity in ("critical", "warning", "info")
    }
    summary = (
        f"Guardian reviewed {len(documents)} H-1B packet documents and found "
        f"{severity_counts['critical']} critical, {severity_counts['warning']} warning, "
        f"and {severity_counts['info']} informational items."
    )
    next_steps = [finding["action"] for finding in findings[:4]]
    if not next_steps:
        next_steps = ["The packet looks internally consistent based on the uploaded documents."]

    report_lines = [
        "Snapshot",
        summary,
        "",
        "Findings",
    ]
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
