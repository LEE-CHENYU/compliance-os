"""Build timeline events from user's checks, documents, and findings."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, FindingRow, SubjectChainRow
from compliance_os.web.services.rule_engine import Rule, RuleEngine
from compliance_os.web.services.subject_chains import (
    EMPLOYMENT_CHAIN_DOC_TYPES,
    ENTITY_CHAIN_DOC_TYPES,
    list_user_subject_chains,
    mapping_resolution_for_document,
)


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    return doc.uploaded_at or datetime.min


def _source_name(value: str | None) -> str:
    if not value:
        return ""
    return Path(value).name or value


def _has_rich_source_path(doc: DocumentRow) -> bool:
    source_path = doc.source_path or ""
    return "/" in source_path or "\\" in source_path


def _field_map(doc: DocumentRow) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in doc.extracted_fields:
        if field.field_value not in (None, ""):
            out[field.field_name] = field.field_value
    return out


def _normalize_iso_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value)
    for pattern, fmt in (
        (r"\b(20\d{2}-\d{2}-\d{2})\b", "%Y-%m-%d"),
        (r"\b(20\d{2}/\d{2}/\d{2})\b", "%Y/%m/%d"),
        (r"\b(\d{2}/\d{2}/20\d{2})\b", "%m/%d/%Y"),
        (r"\b(\d{2}-\d{2}-20\d{2})\b", "%m-%d-%Y"),
        (r"\b(20\d{2}\d{2}\d{2})\b", "%Y%m%d"),
    ):
        match = re.search(pattern, raw)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(1), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _normalize_ein(value: Any) -> str | None:
    if value in (None, ""):
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 9:
        return None
    return f"{digits[:2]}-{digits[2:]}"


TRACK_COMPARISON_EVIDENCE_DOC_TYPES: dict[str, dict[str, tuple[str, ...]]] = {
    "stem_opt": {
        "job_title": ("i983", "employment_letter"),
        "employer_name": ("i983", "employment_letter"),
        "work_location": ("i983", "employment_letter"),
        "start_date": ("i983", "employment_letter"),
        "compensation": ("i983", "employment_letter"),
        "duties": ("i983", "employment_letter"),
        "supervisor": ("i983", "employment_letter"),
        "full_time": ("i983", "employment_letter"),
    },
    "student": {
        "employer_name": ("i20", "employment_letter"),
        "work_location": ("i20", "employment_letter"),
        "start_date": ("i20", "employment_letter"),
        "full_time": ("i20", "employment_letter"),
    },
    "entity": {
        "entity_type": ("tax_return",),
        "form_5472": ("tax_return",),
        "form_type": ("tax_return",),
        "ein": ("tax_return",),
        "entity_name": ("tax_return",),
    },
    "data_room": {
        "employment_letter_i9_employee_name": ("employment_letter", "i9"),
        "employment_letter_paystub_employer_name": ("employment_letter", "paystub"),
        "i9_everify_employee_name": ("i9", "e_verify_case"),
        "i9_everify_first_day_of_employment": ("i9", "e_verify_case"),
        "h1b_registration_g28_entity_name": ("h1b_registration", "h1b_g28"),
        "h1b_registration_invoice_petitioner_name": ("h1b_registration", "h1b_filing_invoice"),
        "h1b_registration_receipt_signatory_name": ("h1b_registration", "h1b_filing_fee_receipt"),
        "h1b_invoice_receipt_beneficiary_name": ("h1b_filing_invoice", "h1b_filing_fee_receipt"),
        "cpt_application_i20_student_name": ("cpt_application", "i20"),
        "cpt_application_employment_letter_employer_name": ("cpt_application", "employment_letter"),
        "i20_passport_student_name": ("i20", "passport"),
        "i20_ead_student_name": ("i20", "ead"),
        "resume_passport_candidate_name": ("resume", "passport"),
        "passport_ead_date_of_birth": ("passport", "ead"),
        "passport_w2_employee_name": ("passport", "w2"),
        "passport_1042s_recipient_name": ("passport", "1042s"),
        "w2_tax_return_tax_year": ("w2", "tax_return"),
        "1042s_tax_return_tax_year": ("1042s", "tax_return"),
        "i94_i20_class_of_admission": ("i94", "i20"),
    },
}

TRACK_EXTRACTION_EVIDENCE_DOC_TYPES: dict[str, dict[str, tuple[str, ...]]] = {
    "stem_opt": {
        "extraction_a": ("i983",),
        "extraction_b": ("employment_letter",),
    },
    "student": {
        "extraction_a": ("i20",),
        "extraction_b": ("employment_letter",),
    },
    "entity": {
        "extraction_b": ("tax_return",),
    },
}

RULES_DIR = Path(__file__).resolve().parents[3] / "config" / "rules"


def _normalized_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def _slug(value: str | None) -> str:
    if not value:
        return ""
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    if not tokens:
        return ""
    return "-".join(tokens[:12])


def _meaningful_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in {"inc", "llc", "ltd", "co", "corp", "capital", "the", "and"}
    }
    return tokens


def _is_generic_parent_slug(value: str) -> bool:
    return value in {
        "",
        "tmp",
        "temp",
        "uploads",
        "upload",
        "app",
        "documents",
        "document",
        "letter",
        "letters",
        "employment",
        "stem",
        "opt",
        "i983",
        "check",
        "checks",
    }


def _document_reference_parent(doc: DocumentRow) -> str:
    reference = doc.source_path or doc.filename or ""
    if not reference:
        return ""
    return _normalized_text(Path(reference).parent.name)


def _document_reference_parent_label(doc: DocumentRow) -> str:
    reference = doc.source_path or doc.filename or ""
    if not reference:
        return ""
    label = Path(reference).parent.name
    if _is_generic_parent_slug(_normalized_text(label)):
        return ""
    return label


def _document_appears_final(doc: DocumentRow) -> bool:
    reference = _normalized_text(f"{doc.source_path or ''} {doc.filename or ''}")
    if any(token in reference for token in ("draft", "unsigned", "outdated", "edited")):
        return False
    return any(token in reference for token in ("signed", "ink signed", "docusign", "final"))


def _has_stronger_i983_successor(doc: DocumentRow, docs: list[DocumentRow]) -> bool:
    fields = _field_map(doc)
    employer_name = _normalized_text(fields.get("employer_name"))
    if not employer_name:
        return False

    for other in docs:
        if other.id == doc.id or other.doc_type != "i983":
            continue
        other_fields = _field_map(other)
        if _normalized_text(other_fields.get("employer_name")) != employer_name:
            continue
        if _normalized_uploaded_at(other) < _normalized_uploaded_at(doc):
            continue
        if _document_appears_final(other):
            return True
    return False


def _should_emit_i983_start_event(
    doc: DocumentRow,
    related_docs: list[dict[str, Any]],
    docs: list[DocumentRow],
) -> bool:
    if len(related_docs) > 1 or _document_appears_final(doc):
        return True
    return not _has_stronger_i983_successor(doc, docs)


def _matched_employment_document_rows(i983_doc: DocumentRow, docs: list[DocumentRow]) -> list[DocumentRow]:
    i983_fields = _field_map(i983_doc)
    employer_name = _normalized_text(i983_fields.get("employer_name"))
    start_date = i983_fields.get("start_date")
    i983_parent = _document_reference_parent(i983_doc)
    matches: list[DocumentRow] = []
    for doc in docs:
        if doc.doc_type != "employment_letter":
            continue
        fields = _field_map(doc)
        employment_employer = _normalized_text(fields.get("employer_name"))
        employment_start_date = fields.get("start_date")
        parent_slug = _document_reference_parent(doc)

        employer_matches = bool(employer_name and employment_employer and employment_employer == employer_name)
        start_matches = bool(start_date and employment_start_date and employment_start_date == start_date)
        parent_matches = bool(
            i983_parent
            and parent_slug
            and not _is_generic_parent_slug(i983_parent)
            and i983_parent == parent_slug
        )

        if employer_matches and (not start_date or not employment_start_date or start_matches):
            matches.append(doc)
            continue
        if start_matches and (not employer_name or not employment_employer):
            matches.append(doc)
            continue
        if parent_matches and (start_matches or employer_matches or (not employer_name and not start_date)):
            matches.append(doc)

    deduped: list[DocumentRow] = []
    seen_ids: set[str] = set()
    for doc in matches:
        if doc.id in seen_ids:
            continue
        seen_ids.add(doc.id)
        deduped.append(doc)
    return deduped


def _employment_chain_for_i983(i983_doc: DocumentRow, employment_docs: list[DocumentRow]) -> dict[str, Any] | None:
    docs = [i983_doc] + employment_docs
    field_maps = [_field_map(doc) for doc in docs]

    employer_name = next(
        (fields.get("employer_name") for fields in field_maps if fields.get("employer_name")),
        None,
    )
    start_date = next(
        (fields.get("start_date") for fields in field_maps if fields.get("start_date")),
        None,
    )
    context_label = next(
        (label for label in (_document_reference_parent_label(doc) for doc in docs) if label),
        None,
    )

    employer_slug = _slug(employer_name)
    context_slug = _slug(context_label)
    chain_subject = employer_slug or context_slug or _slug(i983_doc.filename or i983_doc.id) or i983_doc.id
    chain_key = f"employment:{chain_subject}:{start_date or 'unknown'}"

    label = employer_name or context_label or "Employment chain"
    if employer_name and context_label:
        employer_tokens = _meaningful_tokens(employer_name)
        context_tokens = _meaningful_tokens(context_label)
        if context_tokens and not (context_tokens & employer_tokens):
            label = f"{employer_name} ({context_label})"

    return {
        "type": "employment",
        "key": chain_key,
        "label": label,
        "employer_name": employer_name,
        "start_date": start_date,
        "source_context": context_label,
    }


def _documents_equivalent_for_dashboard(doc: DocumentRow, other: DocumentRow) -> bool:
    if doc.doc_type != other.doc_type:
        return False
    if doc.content_hash and other.content_hash and doc.content_hash == other.content_hash:
        return True
    if doc.source_path and other.source_path and doc.source_path == other.source_path:
        return True
    if (doc.filename or "") != (other.filename or ""):
        return False
    if (doc.file_size or 0) != (other.file_size or 0):
        return False
    if _source_name(doc.source_path or doc.filename) != _source_name(other.source_path or other.filename):
        return False
    return bool(
        doc.content_hash
        or other.content_hash
        or not _has_rich_source_path(doc)
        or not _has_rich_source_path(other)
    )


def _document_sort_key(doc: DocumentRow) -> tuple[bool, bool, bool, bool, datetime, str]:
    has_values = any(field.field_value not in (None, "") for field in doc.extracted_fields)
    return (
        doc.is_active is not False,
        bool(doc.content_hash),
        _has_rich_source_path(doc),
        has_values,
        _normalized_uploaded_at(doc),
        doc.id,
    )


@lru_cache(maxsize=8)
def _rules_for_track(track: str) -> dict[str, Rule]:
    rule_file = RULES_DIR / f"{track}.yaml"
    if not rule_file.exists():
        return {}
    engine = RuleEngine.from_yaml(rule_file)
    return {rule.id: rule for rule in engine.rules}


def _selected_document_for_type(check: CheckRow, doc_type: str) -> DocumentRow | None:
    candidates = [doc for doc in check.documents if doc.doc_type == doc_type]
    if not candidates:
        return None
    return max(candidates, key=_document_sort_key)


def _finding_evidence_rows(
    finding: FindingRow,
    check: CheckRow,
    canonical_docs: list[DocumentRow],
) -> list[DocumentRow]:
    rule = _rules_for_track(check.track).get(finding.rule_id)
    comparison_by_id = {comp.id: comp for comp in check.comparisons}
    comparison_fields: list[str] = []
    evidence_doc_types: list[str] = []

    if finding.source_comparison_id:
        source_comparison = comparison_by_id.get(finding.source_comparison_id)
        if source_comparison is not None:
            comparison_fields.append(source_comparison.field_name)

    if rule is not None:
        for condition in rule.conditions:
            if condition.source == "comparison":
                comparison_fields.append(condition.field)
            for doc_type in TRACK_EXTRACTION_EVIDENCE_DOC_TYPES.get(check.track, {}).get(condition.source, ()):
                evidence_doc_types.append(doc_type)

    for field_name in comparison_fields:
        for doc_type in TRACK_COMPARISON_EVIDENCE_DOC_TYPES.get(check.track, {}).get(field_name, ()):
            evidence_doc_types.append(doc_type)

    selected_rows: list[DocumentRow] = []
    seen_doc_types: set[str] = set()
    for doc_type in evidence_doc_types:
        if doc_type in seen_doc_types:
            continue
        seen_doc_types.add(doc_type)
        doc = _selected_document_for_type(check, doc_type)
        if doc is not None:
            selected_rows.append(doc)

    return _user_canonical_document_rows(selected_rows, canonical_docs) if selected_rows else []


def canonical_documents_for_checks(checks: list[CheckRow]) -> list[DocumentRow]:
    all_docs = [doc for check in checks for doc in check.documents]
    canonical: list[DocumentRow] = []
    for doc in sorted(all_docs, key=_document_sort_key, reverse=True):
        if any(_documents_equivalent_for_dashboard(doc, existing) for existing in canonical):
            continue
        canonical.append(doc)
    return sorted(
        canonical,
        key=lambda doc: (_normalized_uploaded_at(doc), doc.filename or "", doc.id),
        reverse=True,
    )


def serialize_dashboard_document(doc: DocumentRow) -> dict[str, Any]:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "file_size": doc.file_size,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "category": _doc_category(doc.doc_type),
    }


def _canonical_dashboard_document(doc: DocumentRow, canonical_docs: list[DocumentRow]) -> DocumentRow:
    for candidate in canonical_docs:
        if _documents_equivalent_for_dashboard(doc, candidate):
            return candidate
    return doc


def _user_canonical_document_rows(rows: list[DocumentRow], canonical_docs: list[DocumentRow]) -> list[DocumentRow]:
    resolved: list[DocumentRow] = []
    for doc in rows:
        canonical_doc = _canonical_dashboard_document(doc, canonical_docs)
        if any(_documents_equivalent_for_dashboard(canonical_doc, existing) for existing in resolved):
            continue
        resolved.append(canonical_doc)
    resolved.sort(key=lambda doc: (_normalized_uploaded_at(doc), doc.filename or "", doc.id))
    return resolved


def _serialize_timeline_chain(chain: SubjectChainRow) -> dict[str, Any]:
    return {
        "type": chain.chain_type,
        "key": chain.chain_key,
        "label": chain.display_name,
        "employer_name": chain.subject_name if chain.chain_type == "employment" else None,
        "start_date": chain.start_date,
        "source_context": chain.source_context,
    }


def _raw_documents_by_canonical_id(
    checks: list[CheckRow],
    canonical_docs: list[DocumentRow],
) -> dict[str, list[DocumentRow]]:
    mapping: dict[str, list[DocumentRow]] = {doc.id: [] for doc in canonical_docs}
    all_docs = [doc for check in checks for doc in check.documents]
    for raw_doc in all_docs:
        canonical_doc = _canonical_dashboard_document(raw_doc, canonical_docs)
        mapping.setdefault(canonical_doc.id, []).append(raw_doc)
    return mapping


def _chain_refs_by_canonical_id(
    subject_chains: list[SubjectChainRow],
    canonical_docs: list[DocumentRow],
) -> dict[str, list[dict[str, Any]]]:
    refs_by_doc_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chain in subject_chains:
        serialized_chain = _serialize_timeline_chain(chain)
        for link in chain.document_links:
            doc = link.document
            if doc is None:
                continue
            canonical_doc = _canonical_dashboard_document(doc, canonical_docs)
            existing = refs_by_doc_id[canonical_doc.id]
            if any(item["chain"]["key"] == serialized_chain["key"] for item in existing):
                continue
            existing.append(
                {
                    "chain": serialized_chain,
                    "role": link.role,
                    "link_confidence": link.link_confidence,
                    "link_reason": link.link_reason,
                    "details": link.details or {},
                }
            )
    return refs_by_doc_id


def _timeline_document_ids(events: list[dict[str, Any]]) -> set[str]:
    doc_ids: set[str] = set()
    for event in events:
        for doc in event.get("documents", []):
            if doc.get("id"):
                doc_ids.add(doc["id"])
        for risk in event.get("risks", []):
            for doc in risk.get("documents", []):
                if doc.get("id"):
                    doc_ids.add(doc["id"])
    return doc_ids


def _integrity_issue_sort_key(issue: dict[str, Any]) -> tuple[int, str, str]:
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    return (
        severity_rank.get(issue.get("severity", "info"), 3),
        issue.get("issue_code", ""),
        issue.get("title", ""),
    )


def _document_chain_type(doc: DocumentRow) -> str | None:
    if doc.doc_type in EMPLOYMENT_CHAIN_DOC_TYPES:
        return "employment"
    if doc.doc_type in ENTITY_CHAIN_DOC_TYPES:
        return "entity"
    return None


def _document_candidate_chain_refs(
    doc: DocumentRow,
    subject_chains: list[SubjectChainRow],
    excluded_chain_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    chain_type = _document_chain_type(doc)
    if chain_type is None:
        return []

    fields = _field_map(doc)
    if chain_type == "employment":
        subject_name = _normalized_text(fields.get("employer_name") or fields.get("company_name"))
        identifier = _normalize_ein(fields.get("employer_ein"))
        start_date = _normalize_iso_date(
            fields.get("start_date")
            or fields.get("employment_start_date")
            or fields.get("employee_first_day_of_employment")
        )
    else:
        subject_name = _normalized_text(
            fields.get("entity_name")
            or fields.get("legal_name")
            or fields.get("client_entity_name")
            or fields.get("business_name")
        )
        identifier = _normalize_ein(fields.get("ein") or fields.get("employer_ein"))
        start_date = _normalize_iso_date(
            fields.get("formation_date") or fields.get("start_date") or fields.get("filing_date")
        )

    context_label = _normalized_text(_document_reference_parent_label(doc) or _document_reference_parent(doc))
    subject_tokens = _meaningful_tokens(subject_name)
    excluded = excluded_chain_keys or set()
    scored: list[tuple[int, dict[str, Any]]] = []

    for chain in subject_chains:
        if chain.chain_type != chain_type or chain.chain_key in excluded:
            continue
        score = 0
        if identifier and _normalize_ein(chain.subject_identifier) == identifier:
            score += 5
        chain_subject = _normalized_text(chain.subject_name or chain.display_name)
        chain_tokens = _meaningful_tokens(chain_subject)
        if subject_name and chain_subject and subject_name == chain_subject:
            score += 4
        elif subject_tokens and chain_tokens and (subject_tokens & chain_tokens):
            score += 2
        chain_context = _normalized_text(chain.source_context)
        if context_label and (
            (chain_context and context_label == chain_context)
            or context_label in _normalized_text(chain.display_name)
        ):
            score += 2
        if start_date and chain.start_date and start_date == chain.start_date:
            score += 3
        if score <= 0:
            continue
        scored.append((score, _serialize_timeline_chain(chain)))

    scored.sort(key=lambda item: (-item[0], item[1]["label"], item[1]["key"]))
    return [chain for _, chain in scored[:4]]


def _assistant_prompt_for_integrity_issue(issue: dict[str, Any]) -> dict[str, Any] | None:
    documents = issue.get("documents") or []
    if not documents:
        return None
    primary_doc = documents[0]
    chains = issue.get("chains") or []
    issue_code = issue.get("issue_code")
    if issue_code == "ambiguous_chain_link" and chains:
        choices = [
            {"label": chain["label"], "action": "attach_chain", "chain_key": chain["key"]}
            for chain in chains
        ]
        choices.append({"label": "Keep shared", "action": "keep_shared", "chain_key": None})
        return {
            "id": f"{issue_code}:{primary_doc['id']}",
            "kind": "integrity_resolution",
            "issue_code": issue_code,
            "text": f"Should `{primary_doc['filename']}` stay shared across multiple histories, or should I attach it to one chain?",
            "documents": documents,
            "chains": chains,
            "choices": choices,
            "cadence_seconds": 45,
        }
    if issue_code in {"unmapped_document", "unchained_document"} and chains:
        choices = [
            {"label": chain["label"], "action": "attach_chain", "chain_key": chain["key"]}
            for chain in chains
        ]
        choices.append({"label": "Keep standalone", "action": "keep_standalone", "chain_key": None})
        return {
            "id": f"{issue_code}:{primary_doc['id']}",
            "kind": "integrity_resolution",
            "issue_code": issue_code,
            "text": f"Should `{primary_doc['filename']}` be attached to one of these chains, or kept standalone for now?",
            "documents": documents,
            "chains": chains,
            "choices": choices,
            "cadence_seconds": 45,
        }
    return None


def _split_integrity_issues_for_timeline(
    issues: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    visible: list[dict[str, Any]] = []
    prompts: list[dict[str, Any]] = []
    for issue in issues:
        prompt = _assistant_prompt_for_integrity_issue(issue)
        if prompt is not None:
            prompts.append(prompt)
            continue
        visible.append(issue)
    return visible, prompts


def _field_values_for_chain_conflict(
    chain: SubjectChainRow,
    docs: list[DocumentRow],
) -> list[dict[str, Any]]:
    if chain.chain_type == "employment":
        field_specs = [
            (
                "employer_name",
                "Employer name",
                lambda fields: fields.get("employer_name") or fields.get("company_name"),
            ),
            (
                "employer_ein",
                "Employer EIN",
                lambda fields: fields.get("employer_ein"),
            ),
            (
                "start_date",
                "Start date",
                lambda fields: fields.get("start_date")
                or fields.get("employment_start_date")
                or fields.get("employee_first_day_of_employment"),
            ),
            (
                "end_date",
                "End date",
                lambda fields: fields.get("end_date"),
            ),
        ]
    elif chain.chain_type == "entity":
        field_specs = [
            (
                "entity_name",
                "Entity name",
                lambda fields: fields.get("entity_name")
                or fields.get("legal_name")
                or fields.get("client_entity_name")
                or fields.get("business_name"),
            ),
            (
                "ein",
                "EIN",
                lambda fields: fields.get("ein") or fields.get("employer_ein"),
            ),
        ]
    else:
        return []

    conflicts: list[dict[str, Any]] = []
    for field_name, label, extractor in field_specs:
        values: dict[str, list[DocumentRow]] = defaultdict(list)
        for doc in docs:
            extracted_value = extractor(_field_map(doc))
            if extracted_value in (None, ""):
                continue
            normalized_value = (
                _normalize_iso_date(extracted_value)
                if field_name in {"start_date", "end_date"}
                else extracted_value
            ) or str(extracted_value)
            if field_name in {"employer_ein", "ein"}:
                normalized_value = _normalize_ein(normalized_value) or str(extracted_value)
            values[str(normalized_value)].append(doc)
        if len(values) <= 1:
            continue
        conflicts.append(
            {
                "field_name": field_name,
                "label": label,
                "values": [
                    {
                        "value": value,
                        "document_ids": [doc.id for doc in _user_canonical_document_rows(rows, docs)],
                    }
                    for value, rows in sorted(values.items(), key=lambda item: item[0])
                ],
            }
        )
    return conflicts


def _build_integrity_issues(
    checks: list[CheckRow],
    subject_chains: list[SubjectChainRow],
    canonical_docs: list[DocumentRow],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_docs_by_canonical = _raw_documents_by_canonical_id(checks, canonical_docs)
    chain_refs_by_canonical = _chain_refs_by_canonical_id(subject_chains, canonical_docs)
    timeline_doc_ids = _timeline_document_ids(events)
    issues: list[dict[str, Any]] = []

    for doc in canonical_docs:
        raw_docs = raw_docs_by_canonical.get(doc.id, [doc])
        resolution = mapping_resolution_for_document(doc, raw_docs)
        resolution_mode = resolution.get("mode") if isinstance(resolution, dict) else None
        distinct_check_ids = sorted({row.check_id for row in raw_docs if row.check_id})
        chain_refs = chain_refs_by_canonical.get(doc.id, [])
        unique_chains = {ref["chain"]["key"]: ref["chain"] for ref in chain_refs}
        candidate_chains = _document_candidate_chain_refs(
            doc,
            subject_chains,
            excluded_chain_keys=set(unique_chains),
        )
        has_chain = bool(unique_chains)
        has_timeline = doc.id in timeline_doc_ids

        if len(distinct_check_ids) > 1:
            issues.append(
                {
                    "issue_code": "duplicate_across_checks",
                    "severity": "warning",
                    "title": "Document reused across multiple checks",
                    "message": f"{doc.filename} is currently represented in {len(distinct_check_ids)} checks. Keep that reuse explicit instead of relying on display dedupe.",
                    "documents": [serialize_dashboard_document(doc)],
                    "chains": list(unique_chains.values()),
                    "details": {
                        "check_ids": distinct_check_ids,
                        "raw_document_ids": [row.id for row in raw_docs],
                    },
                }
            )

        if len(unique_chains) > 1 and resolution_mode != "keep_shared":
            issues.append(
                {
                    "issue_code": "ambiguous_chain_link",
                    "severity": "warning",
                    "title": "Document maps to multiple subject chains",
                    "message": f"{doc.filename} is linked to multiple histories. Review whether the document should stay shared, be relinked, or be duplicated explicitly.",
                    "documents": [serialize_dashboard_document(doc)],
                    "chains": list(unique_chains.values()),
                    "details": {
                        "chain_keys": sorted(unique_chains),
                    },
                }
            )

        if not has_chain and not has_timeline:
            if resolution_mode == "standalone":
                continue
            issues.append(
                {
                    "issue_code": "unmapped_document",
                    "severity": "warning",
                    "title": "Visible document is not mapped yet",
                    "message": f"{doc.filename} is visible in the data room but is not linked to a subject chain and does not appear on the timeline.",
                    "documents": [serialize_dashboard_document(doc)],
                    "chains": candidate_chains,
                    "details": {
                        "doc_type": doc.doc_type,
                    },
                }
            )
            continue

        if not has_chain:
            if resolution_mode == "standalone":
                continue
            issues.append(
                {
                    "issue_code": "unchained_document",
                    "severity": "warning",
                    "title": "Timeline document is not linked to a subject chain",
                    "message": f"{doc.filename} appears on the timeline, but it is not attached to any employment or entity chain yet.",
                    "documents": [serialize_dashboard_document(doc)],
                    "chains": candidate_chains,
                    "details": {
                        "doc_type": doc.doc_type,
                    },
                }
            )
        elif not has_timeline:
            issues.append(
                {
                    "issue_code": "untimed_document",
                    "severity": "info",
                    "title": "Chained document is not represented on the timeline",
                    "message": f"{doc.filename} is linked to a subject chain, but the current timeline does not surface it yet.",
                    "documents": [serialize_dashboard_document(doc)],
                    "chains": list(unique_chains.values()),
                    "details": {
                        "doc_type": doc.doc_type,
                    },
                }
            )

    for chain in subject_chains:
        chain_docs = _user_canonical_document_rows(_chain_event_document_rows(chain), canonical_docs)
        conflicts = _field_values_for_chain_conflict(chain, chain_docs)
        if not conflicts:
            continue
        conflicting_doc_ids = sorted(
            {
                doc_id
                for field in conflicts
                for value in field["values"]
                for doc_id in value["document_ids"]
            }
        )
        issue_docs = [doc for doc in canonical_docs if doc.id in conflicting_doc_ids]
        issues.append(
            {
                "issue_code": "conflicting_chain_evidence",
                "severity": "error",
                "title": f"Conflicting evidence inside {chain.display_name}",
                "message": "Documents inside this subject chain disagree on key identity or timing fields. Review the linked records before relying on the derived history.",
                "documents": [serialize_dashboard_document(doc) for doc in issue_docs],
                "chains": [_serialize_timeline_chain(chain)],
                "details": {
                    "fields": conflicts,
                },
            }
        )

    issues.sort(key=_integrity_issue_sort_key)
    return issues


def _chain_event_documents(
    chain: SubjectChainRow,
    document_ids: list[str] | None = None,
    canonical_docs: list[DocumentRow] | None = None,
) -> list[dict[str, Any]]:
    rows = _chain_event_document_rows(chain, document_ids)
    if canonical_docs is not None:
        rows = _user_canonical_document_rows(rows, canonical_docs)
    return [serialize_dashboard_document(doc) for doc in rows]


def _chain_event_document_rows(chain: SubjectChainRow, document_ids: list[str] | None = None) -> list[DocumentRow]:
    requested_ids = set(document_ids or [])
    all_docs: list[DocumentRow] = []
    selected_docs: list[DocumentRow] = []
    for link in sorted(
        chain.document_links,
        key=lambda item: (_normalized_uploaded_at(item.document), item.document_id),
    ):
        doc = link.document
        if doc is None:
            continue
        all_docs.append(doc)

    if requested_ids:
        seed_docs = [doc for doc in all_docs if doc.id in requested_ids]
        for doc in all_docs:
            if any(_documents_equivalent_for_dashboard(doc, seed) for seed in seed_docs):
                selected_docs.append(doc)
    else:
        selected_docs = list(all_docs)

    canonical: list[DocumentRow] = []
    for doc in sorted(selected_docs, key=_document_sort_key, reverse=True):
        if any(_documents_equivalent_for_dashboard(doc, existing) for existing in canonical):
            continue
        canonical.append(doc)

    canonical.sort(key=lambda doc: (_normalized_uploaded_at(doc), doc.filename or "", doc.id))
    return canonical


def _event_doc_ids_by_date(chain: SubjectChainRow, doc_type: str, field_names: tuple[str, ...]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for doc in _chain_event_document_rows(chain):
        if doc.doc_type != doc_type:
            continue
        fields = _field_map(doc)
        event_date = next((fields.get(name) for name in field_names if fields.get(name)), None)
        if not event_date:
            continue
        grouped.setdefault(event_date, []).append(doc.id)
    return grouped


def _formation_doc_ids_for_date(chain: SubjectChainRow, event_date: str) -> list[str]:
    matched: list[str] = []
    fallback: list[str] = []
    for doc in _chain_event_document_rows(chain):
        if doc.doc_type not in {
            "articles_of_organization",
            "certificate_of_good_standing",
            "ein_application",
            "registered_agent_consent",
        }:
            continue
        fallback.append(doc.id)
        fields = _field_map(doc)
        candidate_dates = (
            fields.get("formation_date"),
            fields.get("start_date"),
            fields.get("filing_date"),
            fields.get("consent_date"),
        )
        if event_date in candidate_dates:
            matched.append(doc.id)
    return matched or fallback


def _documents_overlap_with_rows(doc: DocumentRow, others: list[DocumentRow]) -> bool:
    return any(_documents_equivalent_for_dashboard(doc, other) for other in others)


def _match_employment_documents(i983_doc: DocumentRow, docs: list[DocumentRow]) -> list[dict[str, Any]]:
    return [serialize_dashboard_document(doc) for doc in _matched_employment_document_rows(i983_doc, docs)]


def _finding_identity_key(finding: FindingRow | dict[str, Any]) -> tuple[Any, ...]:
    if isinstance(finding, dict):
        return (
            finding.get("rule_id"),
            finding.get("severity"),
            finding.get("category"),
            finding.get("title"),
            finding.get("action"),
            finding.get("consequence"),
            bool(finding.get("immigration_impact")),
        )
    return (
        finding.rule_id,
        finding.severity,
        finding.category,
        finding.title,
        finding.action,
        finding.consequence,
        bool(finding.immigration_impact),
    )


def _dedupe_finding_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in items:
        key = _finding_identity_key(item)
        existing = unique.get(key)
        if existing is None:
            unique[key] = {
                **item,
                "documents": list(item.get("documents", [])),
                "source_comparison_ids": list(item.get("source_comparison_ids", [])),
            }
            continue

        seen_doc_ids = {doc["id"] for doc in existing.get("documents", [])}
        for doc in item.get("documents", []):
            if doc["id"] not in seen_doc_ids:
                existing.setdefault("documents", []).append(doc)
                seen_doc_ids.add(doc["id"])

        seen_comparison_ids = set(existing.get("source_comparison_ids", []))
        for comparison_id in item.get("source_comparison_ids", []):
            if comparison_id and comparison_id not in seen_comparison_ids:
                existing.setdefault("source_comparison_ids", []).append(comparison_id)
                seen_comparison_ids.add(comparison_id)
    return list(unique.values())


def _dedupe_comparison_keys(checks: list[CheckRow]) -> list[tuple[Any, ...]]:
    seen: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    for check in checks:
        for comp in check.comparisons:
            key = (
                comp.field_name,
                comp.value_a,
                comp.value_b,
                comp.match_type,
                comp.status,
                comp.detail,
            )
            seen.setdefault(key, key)
    return list(seen.values())


def _dedupe_upload_prompts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in items:
        key = (
            item.get("doc_type"),
            item.get("prompt"),
            item.get("why"),
            item.get("event_date"),
        )
        unique.setdefault(key, item)
    return list(unique.values())


def _dedupe_deadlines(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in items:
        key = (
            item.get("title"),
            item.get("date"),
            item.get("category"),
            item.get("action"),
        )
        existing = unique.get(key)
        if existing is None or item.get("days", 0) < existing.get("days", 0):
            unique[key] = item
    result = list(unique.values())
    result.sort(key=lambda item: (item["date"], item["title"]))
    return result


def _merge_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    for event in events:
        chain_key = (event.get("chain") or {}).get("key")
        key = (event["date"], event["title"], event["type"], event.get("category"), chain_key)
        current = merged.get(key)
        if current is None:
            merged[key] = {
                **event,
                "documents": list(event.get("documents", [])),
                "risks": list(event.get("risks", [])),
            }
            continue

        seen_docs = {doc["id"] for doc in current.get("documents", [])}
        for doc in event.get("documents", []):
            if doc["id"] not in seen_docs:
                current.setdefault("documents", []).append(doc)
                seen_docs.add(doc["id"])

        current["risks"] = _dedupe_finding_dicts(current.get("risks", []) + event.get("risks", []))

    result = list(merged.values())
    result.sort(key=lambda e: e["date"])
    return result


def _active_stem_opt_chains(subject_chains: list[SubjectChainRow]) -> list[SubjectChainRow]:
    active: list[SubjectChainRow] = []
    for chain in subject_chains:
        snapshot = dict(chain.snapshot or {})
        if chain.chain_type != "employment":
            continue
        if chain.status == "superseded" or not snapshot.get("timeline_visible", True):
            continue
        if snapshot.get("stage") != "stem_opt":
            continue
        active.append(chain)
    return active


def build_timeline(user_id: str, db: Session) -> dict:
    """Build a full timeline for a user from their checks and documents."""
    checks = db.query(CheckRow).filter(CheckRow.user_id == user_id).all()
    subject_chains = list_user_subject_chains(user_id, db)

    events: list[dict[str, Any]] = []
    all_docs: list[dict] = []
    all_findings: list[dict] = []
    all_advisories: list[dict] = []
    upload_prompts: list[dict] = []

    doc_types_uploaded: set[str] = set()
    canonical_docs = canonical_documents_for_checks(checks)
    for doc in canonical_docs:
        serialized = serialize_dashboard_document(doc)
        all_docs.append(serialized)
        doc_types_uploaded.add(doc.doc_type)

    entity_linked_tax_docs: list[DocumentRow] = []
    for chain in subject_chains:
        snapshot = dict(chain.snapshot or {})
        serialized_chain = _serialize_timeline_chain(chain)
        if chain.chain_type == "employment":
            if chain.status == "superseded" or not snapshot.get("timeline_visible", True):
                continue
            stage = snapshot.get("stage")
            category = "immigration" if stage == "stem_opt" else "employment"
            if chain.start_date:
                events.append({
                    "date": chain.start_date,
                    "title": "STEM OPT started" if stage == "stem_opt" else "Employment started",
                    "type": "milestone",
                    "category": category,
                    "documents": _chain_event_documents(
                        chain,
                        snapshot.get("start_document_ids") or snapshot.get("document_ids"),
                        canonical_docs,
                    ),
                    "chain": serialized_chain,
                })
            if chain.end_date:
                events.append({
                    "date": chain.end_date,
                    "title": "STEM OPT ends" if stage == "stem_opt" else "Employment ends",
                    "type": "deadline",
                    "category": category,
                    "documents": _chain_event_documents(
                        chain,
                        snapshot.get("end_document_ids") or snapshot.get("document_ids"),
                        canonical_docs,
                    ),
                    "chain": serialized_chain,
                })
            for pay_date, document_ids in sorted(
                _event_doc_ids_by_date(chain, "paystub", ("pay_date", "pay_period_end", "pay_period_start")).items()
            ):
                events.append({
                    "date": pay_date,
                    "title": "Payroll observed",
                    "type": "record",
                    "category": "employment",
                    "documents": _chain_event_documents(chain, document_ids, canonical_docs),
                    "chain": serialized_chain,
                })
            for report_date, document_ids in sorted(
                _event_doc_ids_by_date(chain, "e_verify_case", ("report_prepared_date",)).items()
            ):
                events.append({
                    "date": report_date,
                    "title": "E-Verify case recorded",
                    "type": "record",
                    "category": "employment",
                    "documents": _chain_event_documents(chain, document_ids, canonical_docs),
                    "chain": serialized_chain,
                })
        elif chain.chain_type == "entity":
            if chain.start_date:
                events.append({
                    "date": chain.start_date,
                    "title": "Entity formed",
                    "type": "milestone",
                    "category": "business",
                    "documents": _chain_event_documents(
                        chain,
                        _formation_doc_ids_for_date(chain, chain.start_date),
                        canonical_docs,
                    ),
                    "chain": serialized_chain,
                })
            for assigned_date, document_ids in sorted(
                _event_doc_ids_by_date(chain, "ein_letter", ("assigned_date",)).items()
            ):
                events.append({
                    "date": assigned_date,
                    "title": "EIN assigned",
                    "type": "milestone",
                    "category": "business",
                    "documents": _chain_event_documents(chain, document_ids, canonical_docs),
                    "chain": serialized_chain,
                })
            for consent_date, document_ids in sorted(
                _event_doc_ids_by_date(chain, "registered_agent_consent", ("consent_date",)).items()
            ):
                events.append({
                    "date": consent_date,
                    "title": "Registered agent consented",
                    "type": "record",
                    "category": "business",
                    "documents": _chain_event_documents(chain, document_ids, canonical_docs),
                    "chain": serialized_chain,
                })
            for tax_event in snapshot.get("tax_events") or []:
                document_ids = tax_event.get("document_ids") or []
                entity_linked_tax_docs.extend(
                    _user_canonical_document_rows(_chain_event_document_rows(chain, document_ids), canonical_docs)
                )
                events.append({
                    "date": tax_event["date"],
                    "title": tax_event["title"],
                    "type": "filing",
                    "category": "tax",
                    "documents": _chain_event_documents(chain, document_ids, canonical_docs),
                    "chain": serialized_chain,
                })

    for doc in canonical_docs:
        fields = _field_map(doc)

        if doc.doc_type == "tax_return" and not _documents_overlap_with_rows(doc, entity_linked_tax_docs):
            tax_year = fields.get("tax_year")
            if tax_year:
                events.append({
                    "date": f"{tax_year}-04-15",
                    "title": f"{tax_year} Tax Return filed",
                    "type": "filing",
                    "category": "tax",
                    "documents": [serialize_dashboard_document(doc)],
                })

    for check in checks:
        for finding in check.findings:
            evidence_docs = [
                serialize_dashboard_document(doc)
                for doc in _finding_evidence_rows(finding, check, canonical_docs)
            ]
            f_data = {
                "id": finding.id,
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "category": finding.category,
                "title": finding.title,
                "action": finding.action,
                "consequence": finding.consequence,
                "immigration_impact": finding.immigration_impact,
                "documents": evidence_docs,
                "source_comparison_ids": [finding.source_comparison_id] if finding.source_comparison_id else [],
            }
            if finding.category == "advisory":
                all_advisories.append(f_data)
            else:
                all_findings.append(f_data)

    # Add "today" marker
    today = date.today().isoformat()
    events.append({
        "date": today,
        "title": "Today",
        "type": "now",
        "category": None,
        "documents": [],
    })

    # Generate upload prompts based on what's missing
    if checks:
        stage = None
        for c in checks:
            if c.answers and c.answers.get("stage"):
                stage = c.answers["stage"]

        if stage in ("stem_opt", "opt") and "i983" not in doc_types_uploaded:
            upload_prompts.append({
                "doc_type": "i983",
                "prompt": "Upload your I-983 Training Plan",
                "why": "Needed to verify your STEM OPT authorization and employer details.",
            })

        if "employment_letter" not in doc_types_uploaded:
            upload_prompts.append({
                "doc_type": "employment_letter",
                "prompt": "Upload your employment letter",
                "why": "Cross-checks job title, salary, and location against your I-983.",
            })

        # Check for 12-month evaluations from active STEM chains only.
        for chain in _active_stem_opt_chains(subject_chains):
            if not chain.start_date:
                continue
            try:
                start_date = datetime.strptime(chain.start_date, "%Y-%m-%d").date()
                from dateutil.relativedelta import relativedelta
                eval_due = start_date + relativedelta(months=12)
                if date.today() > eval_due:
                    upload_prompts.append({
                        "doc_type": "i983_evaluation",
                        "prompt": "Upload your completed 12-month evaluation",
                        "why": f"Due by {eval_due.isoformat()}. Must be signed by employer within 10 days of anniversary.",
                        "event_date": eval_due.isoformat(),
                    })
            except ValueError:
                pass

    # Sort and merge duplicate events by identity
    events = _merge_events(events)
    all_findings = _dedupe_finding_dicts(all_findings)
    all_advisories = _dedupe_finding_dicts(all_advisories)
    upload_prompts = _dedupe_upload_prompts(upload_prompts)

    # Attach findings to relevant events
    for event in events:
        event["risks"] = []
    # Attach findings to the closest event
    for finding in all_findings:
        if events:
            # Attach to "today" event
            for event in events:
                if event["type"] == "now":
                    event.setdefault("risks", []).append(finding)
                    break

    all_integrity_issues = _build_integrity_issues(checks, subject_chains, canonical_docs, events)
    integrity_issues, assistant_prompts = _split_integrity_issues_for_timeline(all_integrity_issues)

    # Build key facts from check answers
    STAGE_LABELS = {
        "pre_completion": "CPT (Pre-completion)",
        "opt": "Post-completion OPT",
        "stem_opt": "STEM OPT Extension",
        "h1b": "H-1B",
        "i140": "I-140 / Green Card",
        "not_sure": "Not sure",
    }
    ENTITY_LABELS = {
        "smllc": "Single-member LLC",
        "multi_llc": "Multi-member LLC",
        "c_corp": "C-Corporation",
        "s_corp": "S-Corporation",
    }
    RESIDENCY_LABELS = {
        "us_citizen_or_pr": "US Citizen / PR",
        "on_visa": "On a visa",
        "outside_us": "Outside US",
    }
    EMPLOYMENT_LABELS = {
        "employed": "Employed",
        "between_jobs": "Between jobs",
        "not_employed": "Not employed",
    }

    key_facts: list[dict[str, str]] = []
    for check in checks:
        a = check.answers or {}
        if check.track == "stem_opt":
            if a.get("stage"):
                key_facts.append({"label": "Immigration stage", "value": STAGE_LABELS.get(a["stage"], a["stage"])})
            if a.get("years_in_us"):
                key_facts.append({"label": "Years in US", "value": f"{a['years_in_us']} years"})
            if a.get("employment_status"):
                key_facts.append({"label": "Employment", "value": EMPLOYMENT_LABELS.get(a["employment_status"], a["employment_status"])})
            if a.get("employer_changed") == "yes":
                key_facts.append({"label": "Changed employers", "value": "Yes"})
            if a.get("petition_status"):
                key_facts.append({"label": "Petition status", "value": a["petition_status"].capitalize()})
        elif check.track == "entity":
            if a.get("entity_type"):
                key_facts.append({"label": "Entity type", "value": ENTITY_LABELS.get(a["entity_type"], a["entity_type"]), "category": "entity"})
            if a.get("owner_residency"):
                key_facts.append({"label": "Owner residency", "value": RESIDENCY_LABELS.get(a["owner_residency"], a["owner_residency"]), "category": "entity"})
            if a.get("state_of_formation"):
                key_facts.append({"label": "State of formation", "value": a["state_of_formation"], "category": "entity"})
            if a.get("formation_age"):
                age_labels = {"this_year": "This year", "1_2_years": "1-2 years ago", "3_plus_years": "3+ years ago"}
                key_facts.append({"label": "Entity age", "value": age_labels.get(a["formation_age"], a["formation_age"]), "category": "entity"})

        # Extract facts from documents
        EXTRACT_FIELDS = {
            "i983": {
                "student_name": ("Full name", "immigration"),
                "sevis_number": ("SEVIS number", "immigration"),
                "school_name": ("School", "immigration"),
                "major": ("Major / field of study", "immigration"),
                "employer_name": ("Employer", "employment"),
                "employer_ein": ("Employer EIN", "employment"),
                "job_title": ("Job title", "employment"),
                "start_date": ("Employment start", "employment"),
                "end_date": ("Employment end", "employment"),
                "compensation": ("Compensation", "employment"),
                "work_site_address": ("Work location", "employment"),
                "supervisor_name": ("Supervisor", "employment"),
            },
            "employment_letter": {
                "employee_name": ("Full name", "immigration"),
                "employer_name": ("Employer", "employment"),
                "job_title": ("Job title", "employment"),
                "compensation": ("Compensation", "employment"),
                "work_location": ("Work location", "employment"),
                "manager_name": ("Manager", "employment"),
                "start_date": ("Start date", "employment"),
            },
            "tax_return": {
                "form_type": ("Tax form filed", "tax"),
                "tax_year": ("Tax year", "tax"),
                "total_income": ("Total income", "tax"),
                "entity_name": ("Entity name", "entity"),
                "ein": ("Entity EIN", "entity"),
                "filing_status": ("Filing status", "tax"),
            },
        }
        for doc in check.documents:
            field_map = EXTRACT_FIELDS.get(doc.doc_type, {})
            for field in doc.extracted_fields:
                if field.field_name in field_map and field.field_value and field.field_value != "None":
                    label, cat = field_map[field.field_name]
                    key_facts.append({"label": label, "value": field.field_value, "category": cat})

    # Deduplicate by label (keep first)
    seen = set()
    unique_facts = []
    for f in key_facts:
        if f["label"] not in seen:
            seen.add(f["label"])
            unique_facts.append(f)

    # Build deadlines
    deadlines = _build_deadlines(checks, subject_chains)

    return {
        "events": events,
        "documents": all_docs,
        "findings": all_findings,
        "advisories": all_advisories,
        "all_integrity_issues": all_integrity_issues,
        "integrity_issues": integrity_issues,
        "assistant_prompts": assistant_prompts,
        "upload_prompts": upload_prompts,
        "key_facts": unique_facts,
        "deadlines": deadlines,
    }


def build_stats(user_id: str, db: Session) -> dict:
    """Build aggregate stats for the user's dashboard."""
    checks = db.query(CheckRow).filter(CheckRow.user_id == user_id).all()

    doc_count = len(canonical_documents_for_checks(checks))
    risk_count = len(
        _dedupe_finding_dicts(
            [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "action": f.action,
                    "consequence": f.consequence,
                    "immigration_impact": f.immigration_impact,
                }
                for check in checks
                for f in check.findings
                if f.category != "advisory"
            ]
        )
    )
    verified_count = sum(1 for key in _dedupe_comparison_keys(checks) if key[4] == "match")
    next_deadline_days = None

    # Use the full deadline builder for next_deadline_days
    subject_chains = list_user_subject_chains(user_id, db)
    deadlines = _build_deadlines(checks, subject_chains)
    for d in deadlines:
        if d["days"] > 0 and (next_deadline_days is None or d["days"] < next_deadline_days):
            next_deadline_days = d["days"]

    return {
        "documents": doc_count,
        "risks": risk_count,
        "verified": verified_count,
        "next_deadline_days": next_deadline_days,
    }


def _doc_category(doc_type: str) -> str:
    if doc_type in ("i20", "i94"):
        return "student_status"
    if doc_type in ("i797", "i485", "i765", "i131"):
        return "immigration"
    if doc_type in ("i983", "employment_letter", "ead"):
        return "employment"
    if doc_type in ("tax_return", "w2"):
        return "tax"
    return "business"


def _build_deadlines(
    checks: list,
    subject_chains: list[SubjectChainRow] | None = None,
) -> list[dict]:
    """Build upcoming deadlines from check answers and extracted dates."""
    from dateutil.relativedelta import relativedelta

    today = date.today()
    deadlines: list[dict] = []

    active_stem_chains = _active_stem_opt_chains(subject_chains or [])

    for chain in active_stem_chains:
        if chain.start_date:
            try:
                start_dt = datetime.strptime(chain.start_date, "%Y-%m-%d").date()
                eval_due = start_dt + relativedelta(months=12)
                days = (eval_due - today).days
                deadlines.append({
                    "title": "I-983 12-month evaluation due",
                    "date": eval_due.isoformat(),
                    "days": days,
                    "category": "immigration",
                    "severity": "critical" if days < 0 else "warning" if days < 30 else "info",
                    "action": "Complete self-evaluation with employer signature within 10 days of anniversary",
                })
            except ValueError:
                pass

        if chain.end_date:
            try:
                end_dt = datetime.strptime(chain.end_date, "%Y-%m-%d").date()
                days = (end_dt - today).days
                deadlines.append({
                    "title": "OPT/STEM authorization ends",
                    "date": end_dt.isoformat(),
                    "days": days,
                    "category": "immigration",
                    "severity": "critical" if days < 0 else "warning" if days < 60 else "info",
                    "action": "Ensure you have a plan: STEM extension, H-1B, or departure within 60-day grace period",
                })

                grace_end = end_dt + relativedelta(days=60)
                deadlines.append({
                    "title": "60-day grace period ends",
                    "date": grace_end.isoformat(),
                    "days": (grace_end - today).days,
                    "category": "immigration",
                    "severity": "critical" if (grace_end - today).days < 0 else "warning" if (grace_end - today).days < 14 else "info",
                    "action": "Must depart the US, change status, or have a new petition filed by this date",
                })
            except ValueError:
                pass

    for check in checks:
        a = check.answers or {}
        stage = a.get("stage", "")

        # --- Deadlines from extracted document dates ---
        for doc in check.documents:
            fields = {f.field_name: f.field_value for f in doc.extracted_fields}

        # --- Static annual deadlines ---
        current_year = today.year

        # Tax filing: April 15
        tax_deadline = date(current_year, 4, 15)
        if tax_deadline < today:
            tax_deadline = date(current_year + 1, 4, 15)
        deadlines.append({
            "title": f"{tax_deadline.year - 1} Tax return due",
            "date": tax_deadline.isoformat(),
            "days": (tax_deadline - today).days,
            "category": "tax",
            "severity": "warning" if (tax_deadline - today).days < 30 else "info",
            "action": "File 1040-NR (if NRA) or 1040 with all schedules",
        })

        # FBAR: April 15 (auto-extension to October 15)
        fbar_deadline = date(current_year, 10, 15)
        if fbar_deadline < today:
            fbar_deadline = date(current_year + 1, 10, 15)
        years_in_us = a.get("years_in_us")
        if years_in_us and int(years_in_us) > 5:
            deadlines.append({
                "title": "FBAR filing deadline",
                "date": fbar_deadline.isoformat(),
                "days": (fbar_deadline - today).days,
                "category": "tax",
                "severity": "info",
                "action": "File FinCEN 114 if foreign accounts exceeded $10K aggregate at any point",
            })

        # Entity: state annual report
        if check.track == "entity":
            state = a.get("state_of_formation", "").lower()
            if "delaware" in state or "de" == state:
                de_deadline = date(current_year, 6, 1)
                if de_deadline < today:
                    de_deadline = date(current_year + 1, 6, 1)
                deadlines.append({
                    "title": "Delaware annual report + $300 tax due",
                    "date": de_deadline.isoformat(),
                    "days": (de_deadline - today).days,
                    "category": "entity",
                    "severity": "warning" if (de_deadline - today).days < 30 else "info",
                    "action": "File annual report and pay $300 LLC tax to maintain good standing",
                })
            elif "wyoming" in state or "wy" == state:
                # Wyoming: anniversary month
                deadlines.append({
                    "title": "Wyoming annual report due",
                    "date": f"{current_year}-12-31",
                    "days": (date(current_year, 12, 31) - today).days,
                    "category": "entity",
                    "severity": "info",
                    "action": "File annual report — due first day of anniversary month",
                })

            # Form 5472 for foreign-owned SMLLC
            owner = a.get("owner_residency")
            entity_type = a.get("entity_type")
            if owner and owner != "us_citizen_or_pr" and entity_type == "smllc":
                f5472_deadline = tax_deadline  # same as tax return
                deadlines.append({
                    "title": "Form 5472 + pro forma 1120 due",
                    "date": f5472_deadline.isoformat(),
                    "days": (f5472_deadline - today).days,
                    "category": "entity",
                    "severity": "warning" if (f5472_deadline - today).days < 30 else "info",
                    "action": "Required annually for foreign-owned single-member LLCs, even with $0 revenue",
                })

    return _dedupe_deadlines(deadlines)
