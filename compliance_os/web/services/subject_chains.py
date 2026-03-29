"""Persist cross-document employment and entity chains for dashboard/history use."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
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
    "stem",
    "opt",
    "i983",
    "check",
    "checks",
}

CORPORATE_STOP_WORDS = {"inc", "llc", "ltd", "co", "corp", "capital", "the", "and"}


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min
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


def _meaningful_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in CORPORATE_STOP_WORDS
    }


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


def _document_appears_final(doc: DocumentRow) -> bool:
    reference = _normalized_text(f"{doc.source_path or ''} {doc.filename or ''}")
    if any(token in reference for token in ("draft", "unsigned", "outdated", "edited")):
        return False
    return any(token in reference for token in ("signed", "ink signed", "docusign", "final"))


def _doc_sort_key(doc: DocumentRow) -> tuple[datetime, str]:
    return (_normalized_uploaded_at(doc), doc.id)


def _employment_seed(doc: DocumentRow) -> dict[str, Any] | None:
    if doc.doc_type not in EMPLOYMENT_CHAIN_DOC_TYPES:
        return None
    fields = _field_map(doc)
    employer_name = _first_present(fields, ["employer_name", "company_name"])
    employer_ein = _normalize_ein(_first_present(fields, ["employer_ein"]))
    context_label = _context_label(doc)
    subject_token = (
        _ein_subject_token(employer_ein)
        or _slug(employer_name)
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
    ein = _normalize_ein(_first_present(fields, ["ein", "employer_ein"]))
    if doc.doc_type == "tax_return" and not entity_name and not ein:
        return None
    context_label = _context_label(doc)
    subject_token = (
        _ein_subject_token(ein)
        or _slug(entity_name)
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
        "start_date": _normalize_iso_date(_first_present(fields, ["formation_date", "start_date"])),
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


def _employment_link_role(doc: DocumentRow, chain_start_date: str | None, chain_end_date: str | None, seed: dict[str, Any]) -> tuple[str, bool]:
    if chain_end_date and seed.get("end_date") == chain_end_date:
        return ("end_evidence", doc.doc_type == "i983")
    if chain_start_date and seed.get("start_date") == chain_start_date and doc.doc_type in {
        "i983",
        "employment_contract",
        "employment_letter",
        "cpt_application",
        "h1b_registration",
    }:
        return ("start_evidence", doc.doc_type in {"i983", "employment_letter", "employment_contract"})
    if doc.doc_type in {"paystub", "i9", "e_verify_case", "employment_correspondence"}:
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
            }
        )
    return chains


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
    chains = _build_employment_chains(user_id, employment_seeds)
    chains.extend(_build_entity_chains(user_id, entity_seeds))
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


def serialize_subject_chain(chain: SubjectChainRow) -> dict[str, Any]:
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
                "document_id": link.document_id,
                "role": link.role,
                "is_primary": link.is_primary,
                "link_confidence": link.link_confidence,
                "link_reason": link.link_reason,
                "details": link.details or {},
                "filename": link.document.filename if link.document else None,
                "doc_type": link.document.doc_type if link.document else None,
            }
            for link in sorted(
                chain.document_links,
                key=lambda link: (
                    _normalized_uploaded_at(link.document) if link.document else datetime.min,
                    link.document_id,
                ),
            )
        ],
    }
