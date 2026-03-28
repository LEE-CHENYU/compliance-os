"""Version-aware retrieval context over uploaded check documents."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow
from compliance_os.web.services.document_store import (
    document_family_for_type,
    document_series_key_for_document,
)


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if uploaded_at.tzinfo is None:
        return uploaded_at.replace(tzinfo=timezone.utc)
    return uploaded_at


def _field_map(doc: DocumentRow) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in doc.extracted_fields:
        if field.field_value is not None:
            out[field.field_name] = field.field_value
    return out


def _field_text_fragments(doc: DocumentRow) -> list[str]:
    fragments: list[str] = []
    for field in doc.extracted_fields:
        label = field.field_name.replace("_", " ")
        if field.field_value not in (None, ""):
            fragments.append(f"{label}: {field.field_value}")
        else:
            fragments.append(label)
        if field.raw_text:
            fragments.append(field.raw_text)
    return fragments


def _doc_text(doc: DocumentRow) -> str:
    return doc.ocr_text or ""


def _tokenize(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", text.lower())
        if token not in {"the", "and", "for", "with", "that", "this", "from"}
    }


def _best_excerpt(text: str, query: str, width: int = 240) -> str | None:
    if not text:
        return None
    tokens = list(_tokenize(query))
    lower = text.lower()
    for token in tokens:
        idx = lower.find(token)
        if idx != -1:
            start = max(0, idx - width // 2)
            end = min(len(text), idx + width // 2)
            return text[start:end].strip()
    return text[:width].strip() or None


def _best_field_excerpt(doc: DocumentRow, query: str) -> str | None:
    tokens = list(_tokenize(query))
    if not tokens:
        return None

    for field in doc.extracted_fields:
        label = field.field_name.replace("_", " ")
        haystacks = [
            label,
            field.field_value or "",
            field.raw_text or "",
            f"{label}: {field.field_value}" if field.field_value not in (None, "") else label,
        ]
        joined = " ".join(part for part in haystacks if part).lower()
        if any(token in joined for token in tokens):
            return field.raw_text or (f"{label}: {field.field_value}" if field.field_value not in (None, "") else label)
    return None


def _document_sort_key(doc: DocumentRow):
    has_values = any(field.field_value not in (None, "") for field in doc.extracted_fields)
    return has_values, doc.document_version or 1, _normalized_uploaded_at(doc), doc.id


def select_active_document(documents: list[DocumentRow]) -> DocumentRow | None:
    if not documents:
        return None
    active = [doc for doc in documents if doc.is_active is not False]
    if active:
        return max(active, key=_document_sort_key)
    return max(documents, key=_document_sort_key)


def serialize_document(doc: DocumentRow, query: str | None = None) -> dict:
    fields = _field_map(doc)
    excerpt = _best_field_excerpt(doc, query or "")
    if excerpt is None:
        excerpt = _best_excerpt(_doc_text(doc), query or "", width=320)
    return {
        "document_id": doc.id,
        "doc_type": doc.doc_type,
        "document_family": doc.document_family or document_family_for_type(doc.doc_type),
        "document_series_key": doc.document_series_key or document_series_key_for_document(doc),
        "document_version": doc.document_version or 1,
        "is_active": doc.is_active is not False,
        "filename": doc.filename,
        "source_path": doc.source_path,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "content_hash": doc.content_hash,
        "ocr_engine": doc.ocr_engine,
        "provenance": doc.provenance or {},
        "extracted_fields": fields,
        "ocr_text_excerpt": excerpt,
    }


def build_check_retrieval_context(check: CheckRow, query: str | None = None) -> dict:
    families = _family_contexts(check, query=query)
    retrieved_documents = retrieve_documents_for_query([check], query) if query else []
    return {
        "check_id": check.id,
        "track": check.track,
        "families": families,
        "retrieved_documents": retrieved_documents,
        "llm_context": render_check_retrieval_context(check, query=query),
    }


def _family_contexts(check: CheckRow, query: str | None = None) -> list[dict]:
    grouped: dict[str, list[DocumentRow]] = defaultdict(list)
    for doc in check.documents:
        grouped[doc.document_series_key or document_series_key_for_document(doc)].append(doc)

    families = []
    for series_key, docs in sorted(grouped.items()):
        docs = sorted(docs, key=_document_sort_key, reverse=True)
        active = select_active_document(docs)
        history = [doc for doc in docs if active is None or doc.id != active.id]
        family = (
            active.document_family
            if active and active.document_family
            else document_family_for_type(active.doc_type if active else docs[0].doc_type)
        )
        families.append(
            {
                "document_family": family,
                "document_series_key": series_key,
                "active_document": serialize_document(active, query=query) if active else None,
                "prior_versions": [serialize_document(doc, query=query) for doc in history],
            }
        )
    return families


def _score_document(doc: DocumentRow, query: str) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    haystacks = [
        doc.doc_type or "",
        doc.document_family or document_family_for_type(doc.doc_type),
        doc.filename or "",
        doc.source_path or "",
        " ".join(_field_map(doc).values()),
        " ".join(_field_text_fragments(doc)),
        _doc_text(doc),
    ]
    score = 0.0
    for text in haystacks:
        tokens = _tokenize(text)
        overlap = len(query_tokens & tokens)
        if overlap:
            score += overlap

    if doc.is_active is not False:
        score += 0.5
    if any(token in (doc.doc_type or "").lower() for token in query_tokens):
        score += 1.0
    return score


def retrieve_documents_for_query(
    checks: Iterable[CheckRow],
    query: str,
    top_k: int = 4,
) -> list[dict]:
    scored: list[tuple[float, DocumentRow]] = []
    for check in checks:
        for doc in check.documents:
            score = _score_document(doc, query)
            if score > 0:
                scored.append((score, doc))

    scored.sort(key=lambda item: (item[0], _document_sort_key(item[1])), reverse=True)
    return [
        {**serialize_document(doc, query=query), "score": score}
        for score, doc in scored[:top_k]
    ]


def render_check_retrieval_context(check: CheckRow, query: str | None = None) -> str:
    """Render retrieval-ready context for an LLM prompt."""
    families = _family_contexts(check, query=None)
    parts = [f"# Check {check.id} ({check.track})"]

    for family in families:
        active = family["active_document"]
        if not active:
            continue
        heading = family["document_family"]
        if family.get("document_series_key") and family["document_series_key"] != family["document_family"]:
            heading = f"{heading} [{family['document_series_key']}]"
        parts.append(f"## {heading}")
        parts.append(
            f"Active document: {active['filename']} "
            f"(type={active['doc_type']}, version={active['document_version']}, engine={active['ocr_engine'] or 'unknown'})"
        )
        if active.get("source_path"):
            parts.append(f"Source path: {active['source_path']}")
        fields = active.get("extracted_fields") or {}
        if fields:
            parts.append("Key extracted fields:")
            for key, value in list(fields.items())[:8]:
                parts.append(f"- {key}: {value}")
        if family["prior_versions"]:
            parts.append(
                "Prior versions: "
                + ", ".join(
                    f"{doc['filename']} (v{doc['document_version']})"
                    for doc in family["prior_versions"][:4]
                )
            )

    if query:
        retrieved = retrieve_documents_for_query([check], query)
        if retrieved:
            parts.append(f"## Query Retrieval For: {query}")
            for doc in retrieved:
                parts.append(
                    f"- {doc['filename']} [family={doc['document_family']}, v{doc['document_version']}, score={doc['score']:.1f}]"
                )
                if doc.get("ocr_text_excerpt"):
                    parts.append(f"  Excerpt: {doc['ocr_text_excerpt']}")

    return "\n".join(parts)
