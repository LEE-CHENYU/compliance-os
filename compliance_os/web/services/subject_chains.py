"""Persist cross-document employment and entity chains for dashboard/history use."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, selectinload

from compliance_os.web.models.tables_v2 import (
    CheckRow,
    DocumentRow,
    SubjectChainRow,
    SubjectDocumentLinkRow,
)

EMPLOYMENT_CHAIN_DOC_TYPES = {
    "cpt_application",
    "e_verify_case",
    "employment_contract",
    "employment_correspondence",
    "employment_letter",
    "h1b_registration",
    "h1b_registration_worksheet",
    "i9",
    "i983",
    "paystub",
}

ENTITY_CHAIN_DOC_TYPES = {
    "articles_of_organization",
    "certificate_of_good_standing",
    "ein_application",
    "ein_letter",
    "operating_agreement",
    "registered_agent_consent",
    "tax_return",
}

GENERIC_CONTEXT_SLUGS = {
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
    "entity",
    "business",
    "tax",
    "article",
    "articles",
    "filing",
    "filings",
    "stem",
    "opt",
    "i983",
    "check",
    "checks",
}

CORPORATE_STOP_WORDS = {"inc", "llc", "ltd", "co", "corp", "capital", "the", "and"}
EMPLOYMENT_SUPPORTING_DOC_TYPES = {"paystub", "i9", "e_verify_case", "employment_correspondence"}
EMPLOYMENT_START_EVIDENCE_DOC_TYPES = {
    "i983",
    "employment_contract",
    "employment_letter",
    "cpt_application",
    "h1b_registration",
}


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if uploaded_at.tzinfo is None:
        return uploaded_at.replace(tzinfo=timezone.utc)
    return uploaded_at


def _normalized_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def _slug(value: str | None) -> str | None:
    if not value:
        return None
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    if not tokens:
        return None
    return "-".join(tokens[:12])


def _source_name(value: str | None) -> str:
    if not value:
        return ""
    return Path(value).name or value


def _has_rich_source_path(doc: DocumentRow) -> bool:
    source_path = doc.source_path or ""
    return "/" in source_path or "\\" in source_path


def _meaningful_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in CORPORATE_STOP_WORDS
    }


def _is_low_signal_subject_name(value: str | None) -> bool:
    if not value:
        return True
    normalized = _normalized_text(value)
    if not normalized:
        return True
    if re.fullmatch(r"(19|20)\d{2}", normalized):
        return True
    return normalized in GENERIC_CONTEXT_SLUGS


def _field_map(doc: DocumentRow) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in doc.extracted_fields:
        if field.field_value not in (None, ""):
            out[field.field_name] = field.field_value
    return out


def _first_present(fields: dict[str, str], names: list[str]) -> str | None:
    for name in names:
        value = fields.get(name)
        if value not in (None, ""):
            return value
    return None


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


def _ein_subject_token(value: str | None) -> str | None:
    normalized = _normalize_ein(value)
    if not normalized:
        return None
    return "ein-" + re.sub(r"\D", "", normalized)


def _context_label(doc: DocumentRow) -> str | None:
    reference = doc.source_path or doc.filename or ""
    if not reference:
        return None
    label = Path(reference).parent.name
    if _slug(label) in GENERIC_CONTEXT_SLUGS:
        return None
    return label or None


def _display_name(subject_name: str | None, context_label: str | None, fallback: str) -> str:
    if subject_name and context_label:
        subject_tokens = _meaningful_tokens(subject_name)
        context_tokens = _meaningful_tokens(context_label)
        if context_tokens and not (context_tokens & subject_tokens):
            return f"{subject_name} ({context_label})"
    if subject_name:
        return subject_name
    if context_label:
        return context_label
    return fallback


def _documents_equivalent(doc: DocumentRow, other: DocumentRow) -> bool:
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


def equivalent_documents_for_user_document(
    target_doc: DocumentRow,
    docs: list[DocumentRow],
) -> list[DocumentRow]:
    return [doc for doc in docs if _documents_equivalent(doc, target_doc)]


def mapping_resolution_for_document(
    target_doc: DocumentRow,
    docs: list[DocumentRow] | None = None,
) -> dict[str, Any] | None:
    candidates = docs or [target_doc]
    resolved = sorted(
        (
            doc
            for doc in candidates
            if (
                isinstance(doc.provenance, dict)
                and isinstance(doc.provenance.get("manual_chain_resolution"), dict)
            )
        ),
        key=_dashboard_document_sort_key,
        reverse=True,
    )
    for doc in resolved:
        resolution = doc.provenance.get("manual_chain_resolution")
        if isinstance(resolution, dict) and resolution.get("mode"):
            return resolution
    return None


def _parsed_chain_resolution_key(chain_key: str | None) -> tuple[str, str, str | None] | None:
    if not chain_key:
        return None
    parts = str(chain_key).split(":")
    if len(parts) < 2:
        return None
    chain_type = parts[0]
    if chain_type == "employment" and len(parts) >= 3:
        return ("employment", parts[1], parts[2] if parts[2] != "unknown" else None)
    if chain_type == "entity":
        return ("entity", parts[1], None)
    return None


def persist_document_mapping_resolution(
    *,
    user_id: str,
    document_id: str,
    mode: str,
    db: Session,
    chain_key: str | None = None,
) -> list[DocumentRow]:
    if mode not in {"single_chain", "keep_shared", "standalone"}:
        raise ValueError("Unsupported mapping resolution mode")

    docs = (
        db.query(DocumentRow)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user_id)
        .options(selectinload(DocumentRow.extracted_fields))
        .all()
    )
    target_doc = next((doc for doc in docs if doc.id == document_id), None)
    if target_doc is None:
        raise ValueError("Document not found for user")

    if mode == "single_chain":
        parsed = _parsed_chain_resolution_key(chain_key)
        if parsed is None:
            raise ValueError("A valid chain_key is required for single_chain resolution")

    equivalent_docs = equivalent_documents_for_user_document(target_doc, docs)
    resolution = {
        "mode": mode,
        "chain_key": chain_key,
        "resolved_at": datetime.utcnow().isoformat() + "Z",
        "source": "user_input",
    }
    for doc in equivalent_docs:
        provenance = dict(doc.provenance or {})
        provenance["manual_chain_resolution"] = resolution
        doc.provenance = provenance
    db.flush()
    return equivalent_docs


def _document_appears_final(doc: DocumentRow) -> bool:
    reference = _normalized_text(f"{doc.source_path or ''} {doc.filename or ''}")
    if any(token in reference for token in ("draft", "unsigned", "outdated", "edited")):
        return False
    return any(token in reference for token in ("signed", "ink signed", "docusign", "final"))


def _has_extracted_values(doc: DocumentRow | None) -> bool:
    if doc is None:
        return False
    return any(field.field_value not in (None, "") for field in doc.extracted_fields)


def _dashboard_document_sort_key(doc: DocumentRow | None) -> tuple[bool, bool, bool, bool, datetime, str]:
    if doc is None:
        return (False, False, False, False, datetime.min, "")
    return (
        doc.is_active is not False,
        bool(doc.content_hash),
        _has_rich_source_path(doc),
        _has_extracted_values(doc),
        _normalized_uploaded_at(doc),
        doc.id,
    )


def _canonical_dashboard_document(
    doc: DocumentRow | None,
    canonical_documents: list[DocumentRow] | None,
) -> DocumentRow | None:
    if doc is None or not canonical_documents:
        return doc
    for candidate in canonical_documents:
        if _documents_equivalent(doc, candidate):
            return candidate
    return doc


def _doc_sort_key(doc: DocumentRow) -> tuple[datetime, str]:
    return (_normalized_uploaded_at(doc), doc.id)


def _employment_seed(doc: DocumentRow) -> dict[str, Any] | None:
    if doc.doc_type not in EMPLOYMENT_CHAIN_DOC_TYPES:
        return None
    fields = _field_map(doc)
    employer_name = _first_present(fields, ["employer_name", "company_name"])
    if _is_low_signal_subject_name(employer_name):
        employer_name = None
    employer_ein = _normalize_ein(_first_present(fields, ["employer_ein"]))
    context_label = _context_label(doc)
    subject_token = (
        _slug(employer_name)
        or _ein_subject_token(employer_ein)
        or _slug(context_label)
        or (f"hash-{doc.content_hash[:12]}" if doc.content_hash else None)
        or _slug(Path(doc.filename or "").stem)
    )
    if not subject_token:
        return None
    return {
        "chain_type": "employment",
        "subject_token": subject_token,
        "subject_name": employer_name,
        "subject_identifier": employer_ein,
        "context_label": context_label,
        "start_date": _normalize_iso_date(
            _first_present(fields, ["start_date", "employment_start_date", "employee_first_day_of_employment"])
        ),
        "end_date": _normalize_iso_date(_first_present(fields, ["end_date"])),
        "tax_year": None,
        "doc": doc,
    }


def _entity_seed(doc: DocumentRow) -> dict[str, Any] | None:
    if doc.doc_type not in ENTITY_CHAIN_DOC_TYPES:
        return None
    fields = _field_map(doc)
    entity_name = _first_present(fields, ["entity_name", "legal_name", "client_entity_name", "business_name"])
    if _is_low_signal_subject_name(entity_name):
        entity_name = None
    ein = _normalize_ein(_first_present(fields, ["ein", "employer_ein"]))
    if doc.doc_type == "tax_return" and not entity_name and not ein:
        return None
    context_label = _context_label(doc)
    subject_token = (
        _slug(entity_name)
        or _ein_subject_token(ein)
        or _slug(context_label)
        or (f"hash-{doc.content_hash[:12]}" if doc.content_hash else None)
        or _slug(Path(doc.filename or "").stem)
    )
    if not subject_token:
        return None
    tax_year_value = _first_present(fields, ["tax_year"])
    tax_year_match = re.search(r"(20\d{2}|19\d{2})", str(tax_year_value or ""))
    return {
        "chain_type": "entity",
        "subject_token": subject_token,
        "subject_name": entity_name,
        "subject_identifier": ein,
        "context_label": context_label,
        "start_date": _normalize_iso_date(_first_present(fields, ["formation_date", "start_date", "filing_date"])),
        "end_date": None,
        "tax_year": int(tax_year_match.group(1)) if tax_year_match else None,
        "doc": doc,
    }


def _chain_seed(doc: DocumentRow) -> dict[str, Any] | None:
    return _employment_seed(doc) or _entity_seed(doc)


def _pick_common(values: list[str | None]) -> str | None:
    filtered = [value for value in values if value]
    if not filtered:
        return None
    return Counter(filtered).most_common(1)[0][0]


def _seed_score(seed: dict[str, Any]) -> tuple[int, int, int, int, int, datetime, str]:
    doc = seed["doc"]
    return (
        1 if seed.get("subject_name") else 0,
        1 if seed.get("subject_identifier") else 0,
        1 if seed.get("start_date") else 0,
        1 if _document_appears_final(doc) else 0,
        1 if seed.get("context_label") else 0,
        _normalized_uploaded_at(doc),
        doc.id,
    )


def _propagate_seed_identity(seed: dict[str, Any], source: dict[str, Any]) -> None:
    for key in ("subject_name", "subject_identifier", "context_label", "tax_year"):
        if not seed.get(key) and source.get(key):
            seed[key] = source[key]
    if not seed.get("subject_token") or str(seed.get("subject_token", "")).startswith("hash-"):
        if source.get("subject_token"):
            seed["subject_token"] = source["subject_token"]
    if seed["doc"].doc_type not in EMPLOYMENT_START_EVIDENCE_DOC_TYPES:
        if not seed.get("start_date") and source.get("start_date"):
            seed["start_date"] = source["start_date"]
        if not seed.get("end_date") and source.get("end_date"):
            seed["end_date"] = source["end_date"]


def _enrich_equivalent_seeds(seeds: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for seed in seeds:
        doc = seed["doc"]
        if doc.content_hash:
            groups[("hash", doc.content_hash)].append(seed)
        if doc.source_path:
            groups[("path", doc.source_path)].append(seed)

    seen_group_ids: set[int] = set()
    for group in groups.values():
        group_id = id(group)
        if group_id in seen_group_ids or len(group) < 2:
            continue
        seen_group_ids.add(group_id)
        richest = max(group, key=_seed_score)
        for seed in group:
            if seed is richest:
                continue
            _propagate_seed_identity(seed, richest)


def _apply_manual_mapping_resolutions(
    seeds: list[dict[str, Any]],
    docs: list[DocumentRow],
) -> list[dict[str, Any]]:
    resolved_seeds: list[dict[str, Any]] = []
    for seed in seeds:
        resolution = mapping_resolution_for_document(
            seed["doc"],
            equivalent_documents_for_user_document(seed["doc"], docs),
        )
        if not resolution:
            resolved_seeds.append(seed)
            continue
        mode = resolution.get("mode")
        if mode == "standalone":
            continue
        if mode == "single_chain":
            parsed = _parsed_chain_resolution_key(resolution.get("chain_key"))
            if parsed and parsed[0] == seed["chain_type"]:
                _, subject_token, start_date = parsed
                seed["subject_token"] = subject_token
                if seed["chain_type"] == "employment":
                    seed["start_date"] = start_date
        resolved_seeds.append(seed)
    return resolved_seeds


def _unique_seed_target(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None
    tokens = {item.get("subject_token") for item in items if item.get("subject_token")}
    if len(tokens) != 1:
        return None
    return max(items, key=_seed_score)


def _names_compatible(left: str | None, right: str | None) -> bool:
    left_tokens = _meaningful_tokens(left)
    right_tokens = _meaningful_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    return (
        left_tokens == right_tokens
        or left_tokens <= right_tokens
        or right_tokens <= left_tokens
    )


def _canonicalize_seed_subject_tokens(seeds: list[dict[str, Any]]) -> None:
    if not seeds:
        return

    strong_named = [
        seed
        for seed in seeds
        if seed.get("subject_name")
        and (
            seed.get("subject_identifier")
            or seed["doc"].doc_type not in EMPLOYMENT_SUPPORTING_DOC_TYPES
            or (
                seed["doc"].doc_type in EMPLOYMENT_START_EVIDENCE_DOC_TYPES
                and seed.get("start_date")
            )
        )
    ]
    by_identifier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for seed in strong_named:
        identifier = seed.get("subject_identifier")
        if identifier:
            by_identifier[identifier].append(seed)
        context_key = _normalized_text(seed.get("context_label"))
        if context_key:
            by_context[context_key].append(seed)

    for seed in seeds:
        target = None
        identifier = seed.get("subject_identifier")
        if identifier:
            target = _unique_seed_target(by_identifier.get(identifier, []))
        if target is None:
            context_key = _normalized_text(seed.get("context_label"))
            if context_key and (not seed.get("subject_name") or seed.get("subject_token") == _slug(seed.get("context_label"))):
                target = _unique_seed_target(by_context.get(context_key, []))
        if target is None and seed.get("subject_name"):
            compatible = [
                other
                for other in strong_named
                if other is not seed and _names_compatible(seed.get("subject_name"), other.get("subject_name"))
            ]
            target = _unique_seed_target(compatible)
        if target is None or target is seed:
            continue
        _propagate_seed_identity(seed, target)
        seed["subject_token"] = target["subject_token"]
        if seed["doc"].doc_type in EMPLOYMENT_SUPPORTING_DOC_TYPES:
            seed["start_date"] = None
            seed["end_date"] = None


def _employment_link_role(doc: DocumentRow, chain_start_date: str | None, chain_end_date: str | None, seed: dict[str, Any]) -> tuple[str, bool]:
    if chain_end_date and seed.get("end_date") == chain_end_date:
        return ("end_evidence", doc.doc_type == "i983")
    if chain_start_date and seed.get("start_date") == chain_start_date and doc.doc_type in EMPLOYMENT_START_EVIDENCE_DOC_TYPES:
        return ("start_evidence", doc.doc_type in {"i983", "employment_letter", "employment_contract"})
    if doc.doc_type in EMPLOYMENT_SUPPORTING_DOC_TYPES:
        return ("supporting", False)
    return ("context", False)


def _entity_link_role(doc: DocumentRow) -> tuple[str, bool]:
    if doc.doc_type in {
        "articles_of_organization",
        "certificate_of_good_standing",
        "ein_application",
        "ein_letter",
        "operating_agreement",
        "registered_agent_consent",
    }:
        return ("formation", True)
    if doc.doc_type == "tax_return":
        return ("tax_filing", True)
    return ("supporting", False)


def _build_employment_chains(user_id: str, seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for seed in seeds:
        by_subject[seed["subject_token"]].append(seed)

    chains: list[dict[str, Any]] = []

    for subject_token, subject_items in by_subject.items():
        dated_contexts: dict[str, set[str]] = defaultdict(set)
        dated_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        undated_items: list[dict[str, Any]] = []

        for seed in subject_items:
            if seed.get("start_date"):
                dated_groups[seed["start_date"]].append(seed)
                if seed.get("context_label"):
                    dated_contexts[seed["start_date"]].add(_normalized_text(seed["context_label"]))
            else:
                undated_items.append(seed)

        if not dated_groups:
            dated_groups["unknown"] = list(subject_items)
        else:
            for seed in undated_items:
                assigned_start = None
                context_key = _normalized_text(seed.get("context_label"))
                if context_key:
                    matching_starts = [
                        start_date
                        for start_date, contexts in dated_contexts.items()
                        if context_key in contexts
                    ]
                    if len(matching_starts) == 1:
                        assigned_start = matching_starts[0]
                    elif len(matching_starts) > 1 and seed["doc"].doc_type in EMPLOYMENT_SUPPORTING_DOC_TYPES:
                        assigned_start = max(matching_starts)
                if assigned_start is None and len(dated_groups) == 1:
                    assigned_start = next(iter(dated_groups))
                dated_groups[assigned_start or "unknown"].append(seed)

        subject_chains: list[dict[str, Any]] = []
        for start_key, group in dated_groups.items():
            docs = [seed["doc"] for seed in group]
            docs.sort(key=_doc_sort_key)
            subject_name = _pick_common([seed.get("subject_name") for seed in group])
            subject_identifier = _pick_common([seed.get("subject_identifier") for seed in group])
            context_label = _pick_common([seed.get("context_label") for seed in group])
            start_date = None if start_key == "unknown" else start_key
            end_dates = [seed.get("end_date") for seed in group if seed.get("end_date")]
            end_date = max(end_dates) if end_dates else None
            display_name = _display_name(subject_name, context_label, "Employment chain")
            chain_key = f"employment:{subject_token}:{start_key}"

            links = []
            start_document_ids: list[str] = []
            end_document_ids: list[str] = []
            for seed in group:
                doc = seed["doc"]
                role, is_primary = _employment_link_role(doc, start_date, end_date, seed)
                if role == "start_evidence":
                    start_document_ids.append(doc.id)
                if role == "end_evidence":
                    end_document_ids.append(doc.id)
                links.append(
                    {
                        "document_id": doc.id,
                        "role": role,
                        "is_primary": is_primary,
                        "link_confidence": 0.95 if role in {"start_evidence", "end_evidence"} else 0.8,
                        "link_reason": f"{doc.doc_type} linked to employment chain {display_name}",
                        "details": {
                            "doc_type": doc.doc_type,
                            "start_date": seed.get("start_date"),
                            "end_date": seed.get("end_date"),
                            "source_context": seed.get("context_label"),
                        },
                    }
                )

            linked_doc_types = sorted({doc.doc_type for doc in docs})
            subject_chains.append(
                {
                    "chain_type": "employment",
                    "chain_key": chain_key,
                    "subject_token": subject_token,
                    "display_name": display_name,
                    "subject_name": subject_name,
                    "subject_identifier": subject_identifier,
                    "source_context": context_label,
                    "status": "active",
                    "start_date": start_date,
                    "end_date": end_date,
                    "snapshot": {
                        "stage": "stem_opt" if "i983" in linked_doc_types else "employment",
                        "document_ids": [doc.id for doc in docs],
                        "start_document_ids": start_document_ids,
                        "end_document_ids": end_document_ids,
                        "linked_doc_types": linked_doc_types,
                        "has_final_document": any(_document_appears_final(doc) for doc in docs),
                        "has_external_support": any(doc.doc_type != "i983" for doc in docs),
                        "timeline_visible": True,
                    },
                    "links": links,
                    "_docs": docs,
                }
            )

        subject_chains.sort(
            key=lambda chain: (
                chain["start_date"] or "9999-12-31",
                chain["display_name"],
                chain["chain_key"],
            )
        )
        for index, chain in enumerate(subject_chains):
            if chain["start_date"] is None:
                continue
            if chain["snapshot"]["has_final_document"] or chain["snapshot"]["has_external_support"]:
                continue
            stronger_successor = next(
                (
                    other
                    for other in subject_chains[index + 1:]
                    if (other["snapshot"]["has_final_document"] or other["snapshot"]["has_external_support"])
                ),
                None,
            )
            if stronger_successor is None:
                continue
            chain["status"] = "superseded"
            chain["snapshot"]["timeline_visible"] = False
            chain["snapshot"]["superseded_by_chain_key"] = stronger_successor["chain_key"]

        chains.extend(subject_chains)

    return chains


def _build_entity_chains(user_id: str, seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for seed in seeds:
        by_subject[seed["subject_token"]].append(seed)

    chains: list[dict[str, Any]] = []
    for subject_token, subject_items in by_subject.items():
        subject_items.sort(key=lambda seed: _doc_sort_key(seed["doc"]))
        docs = [seed["doc"] for seed in subject_items]
        subject_name = _pick_common([seed.get("subject_name") for seed in subject_items])
        subject_identifier = _pick_common([seed.get("subject_identifier") for seed in subject_items])
        context_label = _pick_common([seed.get("context_label") for seed in subject_items])
        display_name = _display_name(subject_name, context_label, "Entity chain")
        start_dates = [seed.get("start_date") for seed in subject_items if seed.get("start_date")]
        start_date = min(start_dates) if start_dates else None
        linked_doc_types = sorted({doc.doc_type for doc in docs})

        tax_events: list[dict[str, Any]] = []
        tax_docs_by_year: dict[int, list[DocumentRow]] = defaultdict(list)
        for seed in subject_items:
            if seed["doc"].doc_type == "tax_return" and seed.get("tax_year"):
                tax_docs_by_year[seed["tax_year"]].append(seed["doc"])
        for year, year_docs in sorted(tax_docs_by_year.items()):
            year_docs.sort(key=_doc_sort_key, reverse=True)
            tax_events.append(
                {
                    "date": f"{year}-04-15",
                    "title": f"{year} Tax Return filed",
                    "document_ids": [doc.id for doc in year_docs],
                }
            )

        links = []
        for seed in subject_items:
            doc = seed["doc"]
            role, is_primary = _entity_link_role(doc)
            links.append(
                {
                    "document_id": doc.id,
                    "role": role,
                    "is_primary": is_primary,
                    "link_confidence": 0.95 if is_primary else 0.8,
                    "link_reason": f"{doc.doc_type} linked to entity chain {display_name}",
                    "details": {
                        "doc_type": doc.doc_type,
                        "tax_year": seed.get("tax_year"),
                        "source_context": seed.get("context_label"),
                    },
                }
            )

        chains.append(
            {
                "chain_type": "entity",
                "chain_key": f"entity:{subject_token}",
                "subject_token": subject_token,
                "display_name": display_name,
                "subject_name": subject_name,
                "subject_identifier": subject_identifier,
                "source_context": context_label,
                "status": "active",
                "start_date": start_date,
                "end_date": None,
                "snapshot": {
                    "document_ids": [doc.id for doc in docs],
                    "linked_doc_types": linked_doc_types,
                    "tax_events": tax_events,
                    "timeline_visible": True,
                },
                "links": links,
                "_docs": docs,
            }
        )
    return chains


def _dedupe_doc_ids(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _chain_strength(chain: dict[str, Any]) -> tuple[int, int, int, int, int, int, str]:
    snapshot = dict(chain.get("snapshot") or {})
    return (
        1 if not str(chain.get("chain_key") or "").endswith(":unknown") else 0,
        1 if chain.get("subject_name") else 0,
        1 if chain.get("subject_identifier") else 0,
        1 if chain.get("start_date") else 0,
        1 if snapshot.get("has_final_document") else 0,
        1 if snapshot.get("has_external_support") else 0,
        len(chain.get("_docs") or []),
        chain["chain_key"],
    )


def _chain_context_key(chain: dict[str, Any]) -> str:
    return _normalized_text(chain.get("source_context"))


def _chain_docs_overlap(source: dict[str, Any], target: dict[str, Any]) -> bool:
    for source_doc in source.get("_docs") or []:
        for target_doc in target.get("_docs") or []:
            if _documents_equivalent(source_doc, target_doc):
                return True
    return False


def _is_support_only_employment_chain(chain: dict[str, Any]) -> bool:
    linked_doc_types = set((chain.get("snapshot") or {}).get("linked_doc_types") or [])
    return bool(linked_doc_types) and linked_doc_types <= EMPLOYMENT_SUPPORTING_DOC_TYPES


def _is_low_signal_employment_chain(chain: dict[str, Any]) -> bool:
    snapshot = dict(chain.get("snapshot") or {})
    return (
        _is_support_only_employment_chain(chain)
        or (
            str(chain.get("chain_key") or "").endswith(":unknown")
            and not list(snapshot.get("start_document_ids") or [])
            and chain.get("start_date") is None
        )
        or (
            chain.get("start_date") is None
            and not snapshot.get("has_external_support")
            and not snapshot.get("has_final_document")
        )
    )


def _is_low_signal_entity_chain(chain: dict[str, Any]) -> bool:
    chain_key = str(chain.get("chain_key") or "")
    return (
        chain_key.startswith("entity:hash-")
        or chain_key.startswith("entity:ein-")
        or _is_low_signal_subject_name(chain.get("subject_name"))
    )


def _merge_chain_models(target: dict[str, Any], source: dict[str, Any]) -> None:
    if not target.get("subject_name") and source.get("subject_name"):
        target["subject_name"] = source["subject_name"]
    if not target.get("subject_identifier") and source.get("subject_identifier"):
        target["subject_identifier"] = source["subject_identifier"]
    if not target.get("source_context") and source.get("source_context"):
        target["source_context"] = source["source_context"]
    target["display_name"] = _display_name(
        target.get("subject_name"),
        target.get("source_context"),
        "Employment chain" if target["chain_type"] == "employment" else "Entity chain",
    )

    target_docs = list(target.get("_docs") or [])
    for doc in source.get("_docs") or []:
        if any(_documents_equivalent(doc, existing) for existing in target_docs):
            continue
        target_docs.append(doc)
    target["_docs"] = sorted(target_docs, key=_doc_sort_key)

    target_links = list(target.get("links") or [])
    seen_link_docs = {link["document_id"] for link in target_links}
    for link in source.get("links") or []:
        if link["document_id"] in seen_link_docs:
            continue
        target_links.append(link)
        seen_link_docs.add(link["document_id"])
    target["links"] = target_links

    target_snapshot = dict(target.get("snapshot") or {})
    source_snapshot = dict(source.get("snapshot") or {})
    target_snapshot["document_ids"] = _dedupe_doc_ids(
        list(target_snapshot.get("document_ids") or []) + list(source_snapshot.get("document_ids") or [])
    )
    target_snapshot["linked_doc_types"] = sorted(
        set(target_snapshot.get("linked_doc_types") or []) | set(source_snapshot.get("linked_doc_types") or [])
    )

    if target["chain_type"] == "employment":
        target_snapshot["start_document_ids"] = _dedupe_doc_ids(
            list(target_snapshot.get("start_document_ids") or []) + list(source_snapshot.get("start_document_ids") or [])
        )
        target_snapshot["end_document_ids"] = _dedupe_doc_ids(
            list(target_snapshot.get("end_document_ids") or []) + list(source_snapshot.get("end_document_ids") or [])
        )
        target_snapshot["has_final_document"] = bool(
            target_snapshot.get("has_final_document") or source_snapshot.get("has_final_document")
        )
        target_snapshot["has_external_support"] = bool(
            target_snapshot.get("has_external_support") or source_snapshot.get("has_external_support")
        )
        if source_snapshot.get("stage") == "stem_opt":
            target_snapshot["stage"] = "stem_opt"
        elif "stage" not in target_snapshot:
            target_snapshot["stage"] = source_snapshot.get("stage")
        target_snapshot["timeline_visible"] = bool(
            target_snapshot.get("timeline_visible", True) or source_snapshot.get("timeline_visible", True)
        )
        if target.get("start_date") is None:
            target["start_date"] = source.get("start_date")
        if (
            source.get("end_date")
            and source.get("status") != "superseded"
            and (not target.get("end_date") or source["end_date"] > target["end_date"])
        ):
            target["end_date"] = source["end_date"]
    else:
        combined_tax_events = list(target_snapshot.get("tax_events") or []) + list(source_snapshot.get("tax_events") or [])
        deduped_tax_events: dict[tuple[str, str], dict[str, Any]] = {}
        for event in combined_tax_events:
            key = (event["date"], event["title"])
            current = deduped_tax_events.get(key)
            if current is None:
                deduped_tax_events[key] = {
                    "date": event["date"],
                    "title": event["title"],
                    "document_ids": list(event.get("document_ids") or []),
                }
                continue
            current["document_ids"] = _dedupe_doc_ids(
                list(current.get("document_ids") or []) + list(event.get("document_ids") or [])
            )
        target_snapshot["tax_events"] = sorted(
            deduped_tax_events.values(),
            key=lambda item: (item["date"], item["title"]),
        )
        if target.get("start_date") is None:
            target["start_date"] = source.get("start_date")

    target["snapshot"] = target_snapshot


def _rekey_chain_model(chain: dict[str, Any]) -> None:
    if chain["chain_type"] == "employment":
        start_key = chain.get("start_date") or "unknown"
        chain["chain_key"] = f"employment:{chain['subject_token']}:{start_key}"
    else:
        chain["chain_key"] = f"entity:{chain['subject_token']}"


def _consolidate_employment_chains(chains: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = list(chains)
    changed = True
    while changed:
        changed = False
        for source in list(remaining):
            candidates = [target for target in remaining if target is not source]
            overlap_matches = [
                target
                for target in candidates
                if _chain_docs_overlap(source, target)
                and (_is_low_signal_employment_chain(source) or _is_low_signal_employment_chain(target))
            ]
            if overlap_matches:
                target = max(overlap_matches, key=_chain_strength)
                _merge_chain_models(target, source)
                _rekey_chain_model(target)
                remaining.remove(source)
                changed = True
                break

            if not _is_low_signal_employment_chain(source):
                continue

            compatible = [
                target
                for target in candidates
                if not _is_low_signal_employment_chain(target)
                and (
                    (
                        _chain_context_key(source)
                        and _chain_context_key(source) == _chain_context_key(target)
                    )
                    or _names_compatible(source.get("subject_name"), target.get("subject_name"))
                )
            ]
            if not compatible:
                continue

            preferred = [target for target in compatible if target.get("status") != "superseded"]
            if preferred:
                compatible = preferred
            stem_opt = [target for target in compatible if (target.get("snapshot") or {}).get("stage") == "stem_opt"]
            if len(stem_opt) == 1:
                target = stem_opt[0]
            elif len(compatible) == 1:
                target = compatible[0]
            else:
                target = max(
                    compatible,
                    key=lambda chain: (
                        1 if chain.get("start_date") else 0,
                        chain.get("start_date") or "",
                        _chain_strength(chain),
                    ),
                )
            _merge_chain_models(target, source)
            _rekey_chain_model(target)
            remaining.remove(source)
            changed = True
            break

    for chain in remaining:
        _rekey_chain_model(chain)
    remaining.sort(key=lambda chain: (chain["start_date"] or "", chain["display_name"], chain["chain_key"]))
    return remaining


def _consolidate_entity_chains(chains: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = list(chains)
    changed = True
    while changed:
        changed = False
        named_targets = [chain for chain in remaining if chain.get("subject_name")]
        for source in list(remaining):
            candidates = [target for target in remaining if target is not source]
            overlap_matches = [
                target
                for target in candidates
                if _chain_docs_overlap(source, target)
                and (_is_low_signal_entity_chain(source) or _is_low_signal_entity_chain(target))
            ]
            if overlap_matches:
                target = max(overlap_matches, key=_chain_strength)
                _merge_chain_models(target, source)
                _rekey_chain_model(target)
                remaining.remove(source)
                changed = True
                break

            identifier = source.get("subject_identifier")
            if identifier:
                identifier_matches = [
                    target for target in candidates if target.get("subject_identifier") == identifier
                ]
                if len(identifier_matches) == 1:
                    _merge_chain_models(identifier_matches[0], source)
                    _rekey_chain_model(identifier_matches[0])
                    remaining.remove(source)
                    changed = True
                    break

            compatible_names = [
                target for target in candidates
                if _names_compatible(source.get("subject_name"), target.get("subject_name"))
            ]
            if len(compatible_names) == 1:
                _merge_chain_models(compatible_names[0], source)
                _rekey_chain_model(compatible_names[0])
                remaining.remove(source)
                changed = True
                break

            if _is_low_signal_entity_chain(source) and len(named_targets) == 1:
                _merge_chain_models(named_targets[0], source)
                _rekey_chain_model(named_targets[0])
                remaining.remove(source)
                changed = True
                break

    for chain in remaining:
        _rekey_chain_model(chain)
    remaining.sort(key=lambda chain: (chain["start_date"] or "", chain["display_name"], chain["chain_key"]))
    return remaining


def _build_user_chain_models(user_id: str, docs: list[DocumentRow]) -> list[dict[str, Any]]:
    employment_seeds: list[dict[str, Any]] = []
    entity_seeds: list[dict[str, Any]] = []
    for doc in docs:
        seed = _chain_seed(doc)
        if seed is None:
            continue
        if seed["chain_type"] == "employment":
            employment_seeds.append(seed)
        elif seed["chain_type"] == "entity":
            entity_seeds.append(seed)
    _enrich_equivalent_seeds(employment_seeds)
    _enrich_equivalent_seeds(entity_seeds)
    employment_seeds = _apply_manual_mapping_resolutions(employment_seeds, docs)
    entity_seeds = _apply_manual_mapping_resolutions(entity_seeds, docs)
    _canonicalize_seed_subject_tokens(employment_seeds)
    _canonicalize_seed_subject_tokens(entity_seeds)
    chains = _build_employment_chains(user_id, employment_seeds)
    chains = _consolidate_employment_chains(chains)
    entity_chains = _build_entity_chains(user_id, entity_seeds)
    entity_chains = _consolidate_entity_chains(entity_chains)
    chains.extend(entity_chains)
    chains.sort(key=lambda chain: (chain["chain_type"], chain["start_date"] or "", chain["display_name"], chain["chain_key"]))
    return chains


def sync_user_subject_chains(user_id: str, db: Session) -> list[SubjectChainRow]:
    docs = (
        db.query(DocumentRow)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user_id)
        .options(selectinload(DocumentRow.extracted_fields))
        .all()
    )
    models = _build_user_chain_models(user_id, docs)

    existing_rows = (
        db.query(SubjectChainRow)
        .filter(SubjectChainRow.user_id == user_id)
        .options(selectinload(SubjectChainRow.document_links))
        .all()
    )
    existing = {(row.chain_type, row.chain_key): row for row in existing_rows}
    keep_keys = {(model["chain_type"], model["chain_key"]) for model in models}

    for row in existing_rows:
        if (row.chain_type, row.chain_key) not in keep_keys:
            db.delete(row)
    db.flush()

    for model in models:
        key = (model["chain_type"], model["chain_key"])
        row = existing.get(key)
        if row is None:
            row = SubjectChainRow(
                user_id=user_id,
                chain_type=model["chain_type"],
                chain_key=model["chain_key"],
                display_name=model["display_name"],
            )
            db.add(row)

        row.display_name = model["display_name"]
        row.subject_name = model["subject_name"]
        row.subject_identifier = model["subject_identifier"]
        row.source_context = model["source_context"]
        row.status = model["status"]
        row.start_date = model["start_date"]
        row.end_date = model["end_date"]
        row.snapshot = model["snapshot"]

        db.flush()

        db.query(SubjectDocumentLinkRow).filter(
            SubjectDocumentLinkRow.chain_id == row.id
        ).delete(synchronize_session=False)
        for link in model["links"]:
            db.add(
                SubjectDocumentLinkRow(
                    chain_id=row.id,
                    document_id=link["document_id"],
                    role=link["role"],
                    is_primary=link["is_primary"],
                    link_confidence=link["link_confidence"],
                    link_reason=link["link_reason"],
                    details=link["details"],
                )
            )

    db.flush()
    return list_user_subject_chains(user_id, db)


def sync_check_subject_chains(check: CheckRow, db: Session) -> list[SubjectChainRow]:
    if not check.user_id:
        return []
    return sync_user_subject_chains(check.user_id, db)


def list_user_subject_chains(
    user_id: str,
    db: Session,
    *,
    chain_type: str | None = None,
) -> list[SubjectChainRow]:
    query = (
        db.query(SubjectChainRow)
        .filter(SubjectChainRow.user_id == user_id)
        .options(
            selectinload(SubjectChainRow.document_links)
            .selectinload(SubjectDocumentLinkRow.document)
            .selectinload(DocumentRow.extracted_fields)
        )
        .order_by(
            SubjectChainRow.chain_type.asc(),
            SubjectChainRow.start_date.asc(),
            SubjectChainRow.display_name.asc(),
            SubjectChainRow.id.asc(),
        )
    )
    if chain_type:
        query = query.filter(SubjectChainRow.chain_type == chain_type)
    return query.all()


def serialize_subject_chain(
    chain: SubjectChainRow,
    canonical_documents: list[DocumentRow] | None = None,
) -> dict[str, Any]:
    canonical_links: list[tuple[SubjectDocumentLinkRow, DocumentRow | None]] = []
    for link in sorted(
        chain.document_links,
        key=lambda item: (
            _dashboard_document_sort_key(item.document),
            item.is_primary,
            item.link_confidence or 0.0,
            _document_appears_final(item.document) if item.document else False,
            item.document_id,
        ),
        reverse=True,
    ):
        doc = _canonical_dashboard_document(link.document, canonical_documents)
        if doc is not None and any(existing_doc and _documents_equivalent(doc, existing_doc) for _, existing_doc in canonical_links):
            continue
        canonical_links.append((link, doc))

    canonical_links.sort(
        key=lambda item: (
            _normalized_uploaded_at(item[1]) if item[1] else datetime.min,
            item[0].document_id,
        )
    )
    return {
        "id": chain.id,
        "chain_type": chain.chain_type,
        "chain_key": chain.chain_key,
        "display_name": chain.display_name,
        "subject_name": chain.subject_name,
        "subject_identifier": chain.subject_identifier,
        "source_context": chain.source_context,
        "status": chain.status,
        "start_date": chain.start_date,
        "end_date": chain.end_date,
        "snapshot": chain.snapshot or {},
        "documents": [
            {
                "document_id": doc.id if doc is not None else link.document_id,
                "role": link.role,
                "is_primary": link.is_primary,
                "link_confidence": link.link_confidence,
                "link_reason": link.link_reason,
                "details": link.details or {},
                "filename": doc.filename if doc else None,
                "doc_type": doc.doc_type if doc else None,
            }
            for link, doc in canonical_links
        ],
    }
