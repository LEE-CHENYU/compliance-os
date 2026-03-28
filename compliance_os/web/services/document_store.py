"""Document versioning and extraction persistence for uploaded check documents."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, ExtractedFieldRow
from compliance_os.web.services.extractor import (
    extract_document,
    extract_pdf_text_with_provenance,
    extract_supporting_excerpt,
)


def document_family_for_type(doc_type: str) -> str:
    # Broad family used for retrieval and display.
    return doc_type


def _series_slug(value: str | None) -> str | None:
    if not value:
        return None
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    if not tokens:
        return None
    return "-".join(tokens[:12])


def _field_values(doc: DocumentRow) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in doc.extracted_fields:
        if field.field_value not in (None, ""):
            out[field.field_name] = field.field_value
    return out


def _first_year_candidate(*values: str | None) -> str | None:
    for value in values:
        if not value:
            continue
        match = re.search(r"\b(20\d{2}|19\d{2})\b", value)
        if match:
            return match.group(1)
    return None


def _first_date_candidate(*values: str | None) -> str | None:
    for value in values:
        if not value:
            continue
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


def infer_document_series_key(
    doc_type: str,
    *,
    source_path: str | None = None,
    filename: str | None = None,
    extracted_values: dict[str, Any] | None = None,
    ocr_text: str | None = None,
) -> str:
    """Infer the version-chain key within a broad document family.

    `document_family` stays broad, usually equal to `doc_type`.
    `document_series_key` scopes versions for parallel documents of the same
    type, such as annual tax forms or separate lease arrangements.
    """
    extracted_values = extracted_values or {}
    reference = source_path or filename or ""
    reference_stem = Path(reference).stem if reference else ""
    family = document_family_for_type(doc_type)

    if doc_type == "1042s":
        tax_year = _first_year_candidate(
            str(extracted_values.get("tax_year") or ""),
            reference,
            ocr_text,
        )
        account = _series_slug(str(extracted_values.get("recipient_account_number") or "")) or None
        if tax_year and account:
            return f"{family}:{tax_year}:{account}"
        if tax_year:
            return f"{family}:{tax_year}"
        return family

    if doc_type == "lease":
        lease_type = _series_slug(str(extracted_values.get("lease_type") or "")) or (
            "sublease" if "sublease" in reference.lower() else "lease"
        )
        address = _series_slug(str(extracted_values.get("property_address") or ""))
        if not address:
            address = _series_slug(reference_stem) or "default"
        return f"{family}:{lease_type}:{address}"

    if doc_type == "paystub":
        employer = _series_slug(str(extracted_values.get("employer_name") or ""))
        period_end = _first_date_candidate(
            str(extracted_values.get("pay_period_end") or ""),
            str(extracted_values.get("pay_date") or ""),
            reference,
            ocr_text,
        )
        if employer and period_end:
            return f"{family}:{employer}:{period_end}"
        if period_end:
            return f"{family}:{period_end}"
        fallback = _series_slug(reference_stem) or "default"
        return f"{family}:{fallback}"

    if doc_type == "i9":
        reference_parent = _series_slug(Path(reference).parent.name if reference else "")
        employer = _series_slug(str(extracted_values.get("employer_name") or "")) or reference_parent
        if employer:
            return f"{family}:{employer}"
        fallback = _series_slug(reference_stem) or "default"
        return f"{family}:{fallback}"

    if doc_type == "i765":
        category = _series_slug(str(extracted_values.get("eligibility_category") or ""))
        lower_reference = reference.lower()
        lower_text = (ocr_text or "").lower()
        if not category:
            if "c03c" in lower_reference or "c03c" in lower_text or "stem" in lower_reference:
                category = "c03c"
            elif "c03b" in lower_reference or "c03b" in lower_text or "i-765-opt" in lower_reference or "i765-opt" in lower_reference or lower_reference.endswith("opt.pdf"):
                category = "c03b"
        if category:
            return f"{family}:{category}"
        return family

    return family


def document_series_key_for_document(doc: DocumentRow) -> str:
    return infer_document_series_key(
        doc.doc_type,
        source_path=doc.source_path,
        filename=doc.filename,
        extracted_values=_field_values(doc),
        ocr_text=doc.ocr_text,
    )


def content_hash_for_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if uploaded_at.tzinfo is None:
        return uploaded_at.replace(tzinfo=timezone.utc)
    return uploaded_at


def _set_upload_lineage_provenance(
    doc: DocumentRow,
    *,
    duplicate_of: str | None,
    supersedes_document_id: str | None,
) -> None:
    provenance = dict(doc.provenance or {})
    upload = dict(provenance.get("upload") or {})
    upload["source_path"] = doc.source_path or doc.filename
    upload["content_hash"] = doc.content_hash
    upload["registered_at"] = upload.get("registered_at") or datetime.now(timezone.utc).isoformat()
    upload["document_series_key"] = doc.document_series_key
    if duplicate_of:
        upload["duplicate_of_document_id"] = duplicate_of
    else:
        upload.pop("duplicate_of_document_id", None)
    if supersedes_document_id:
        upload["supersedes_document_id"] = supersedes_document_id
    else:
        upload.pop("supersedes_document_id", None)
    provenance["upload"] = upload
    doc.provenance = provenance


def _series_key_is_more_specific(current_key: str | None, inferred_key: str | None, family_key: str) -> bool:
    if not current_key or current_key == family_key or not inferred_key:
        return False
    if inferred_key == family_key:
        return True
    return current_key.count(":") > inferred_key.count(":")


def _reindex_documents_for_type(check: CheckRow, doc_type: str) -> None:
    docs = [doc for doc in check.documents if doc.doc_type == doc_type]
    if not docs:
        return

    for doc in docs:
        doc.document_family = document_family_for_type(doc.doc_type)
        inferred_key = document_series_key_for_document(doc)
        current_key = doc.document_series_key
        family_key = document_family_for_type(doc.doc_type)
        if _series_key_is_more_specific(current_key, inferred_key, family_key):
            doc.document_series_key = current_key
        else:
            doc.document_series_key = inferred_key

    grouped: dict[str, list[DocumentRow]] = {}
    for doc in docs:
        series_key = doc.document_series_key or document_family_for_type(doc.doc_type)
        grouped.setdefault(series_key, []).append(doc)

    for group_docs in grouped.values():
        group_docs.sort(key=lambda doc: (_normalized_uploaded_at(doc), doc.id))

        previous_distinct: DocumentRow | None = None
        previous_version = 0

        for doc in group_docs:
            duplicate_of = None
            if (
                previous_distinct is not None
                and doc.content_hash
                and previous_distinct.content_hash
                and doc.content_hash == previous_distinct.content_hash
            ):
                doc.document_version = previous_version
                doc.supersedes_document_id = previous_distinct.id
                doc.is_active = False
                duplicate_of = previous_distinct.id
            else:
                previous_version += 1
                doc.document_version = previous_version
                doc.supersedes_document_id = previous_distinct.id if previous_distinct else None
                if previous_distinct is not None:
                    previous_distinct.is_active = False
                doc.is_active = True
                previous_distinct = doc

            _set_upload_lineage_provenance(
                doc,
                duplicate_of=duplicate_of,
                supersedes_document_id=doc.supersedes_document_id,
            )


def reindex_documents_for_doc_types(check: CheckRow, doc_types: Iterable[str | None]) -> None:
    """Recompute lineage metadata for one or more doc types on a check."""
    seen: set[str] = set()
    for doc_type in doc_types:
        if not doc_type or doc_type in seen:
            continue
        seen.add(doc_type)
        _reindex_documents_for_type(check, doc_type)


def register_uploaded_document(
    check: CheckRow,
    row: DocumentRow,
    content: bytes,
    source_path: str | None = None,
) -> dict[str, Any]:
    """Assign versioning and provenance metadata to a newly uploaded document."""
    content_hash = content_hash_for_bytes(content)
    row.source_path = source_path or row.filename
    row.content_hash = content_hash
    row.document_family = document_family_for_type(row.doc_type)
    row.document_series_key = infer_document_series_key(
        row.doc_type,
        source_path=row.source_path,
        filename=row.filename,
    )
    _set_upload_lineage_provenance(
        row,
        duplicate_of=None,
        supersedes_document_id=None,
    )
    _reindex_documents_for_type(check, row.doc_type)

    upload_meta = dict((row.provenance or {}).get("upload") or {})

    return {
        "document_family": row.document_family,
        "document_series_key": row.document_series_key,
        "document_version": row.document_version or 1,
        "is_active": row.is_active is not False,
        "duplicate_of_document_id": upload_meta.get("duplicate_of_document_id"),
        "supersedes_document_id": row.supersedes_document_id,
    }


def extract_into_document(doc: DocumentRow, db: Session) -> dict[str, Any]:
    """Run OCR and structured extraction, persisting doc-level provenance."""
    text_result = extract_pdf_text_with_provenance(doc.file_path)
    fields = extract_document(doc.doc_type, text_result.text)

    for old in doc.extracted_fields:
        db.delete(old)

    for field_name, data in fields.items():
        value = data["value"]
        db.add(
            ExtractedFieldRow(
                document_id=doc.id,
                field_name=field_name,
                field_value=str(value) if value is not None else None,
                confidence=data.get("confidence"),
                raw_text=extract_supporting_excerpt(text_result.text, value),
            )
        )

    provenance = dict(doc.provenance or {})
    provenance["ocr"] = {
        "engine": text_result.engine,
        "metadata": text_result.metadata,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    provenance["structured_extraction"] = {
        "doc_type": doc.doc_type,
        "field_count": len(fields),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    doc.ocr_text = text_result.text
    doc.ocr_engine = text_result.engine
    doc.provenance = provenance
    extracted_values = {field_name: data["value"] for field_name, data in fields.items()}
    doc.document_series_key = infer_document_series_key(
        doc.doc_type,
        source_path=doc.source_path,
        filename=doc.filename,
        extracted_values=extracted_values,
        ocr_text=text_result.text,
    )
    check = doc.check or db.get(CheckRow, doc.check_id)
    if check is not None:
        _reindex_documents_for_type(check, doc.doc_type)

    return {
        "document_id": doc.id,
        "doc_type": doc.doc_type,
        "filename": doc.filename,
        "document_family": doc.document_family or document_family_for_type(doc.doc_type),
        "document_series_key": doc.document_series_key or document_series_key_for_document(doc),
        "document_version": doc.document_version or 1,
        "is_active": doc.is_active is not False,
        "fields": {k: v["value"] for k, v in fields.items()},
        "ocr_engine": text_result.engine,
    }
