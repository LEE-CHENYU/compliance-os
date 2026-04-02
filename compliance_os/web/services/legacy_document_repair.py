"""Repair legacy imported document rows for cleaner dashboard inspection."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_engine
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow
from compliance_os.web.services.document_intake import UploadValidationError, resolve_document_type
from compliance_os.web.services.document_store import (
    _reindex_documents_for_type,
    content_hash_for_bytes,
    document_family_for_type,
    extract_into_document,
    infer_document_series_key,
)


@dataclass
class RepairSummary:
    inspected_documents: int = 0
    hash_backfilled: int = 0
    source_path_normalized: int = 0
    doc_type_reclassified: int = 0
    reextracted_documents: int = 0
    skipped_missing_file: int = 0
    skipped_unresolved_conflict_groups: int = 0
    skipped_reextract_failures: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "inspected_documents": self.inspected_documents,
            "hash_backfilled": self.hash_backfilled,
            "source_path_normalized": self.source_path_normalized,
            "doc_type_reclassified": self.doc_type_reclassified,
            "reextracted_documents": self.reextracted_documents,
            "skipped_missing_file": self.skipped_missing_file,
            "skipped_unresolved_conflict_groups": self.skipped_unresolved_conflict_groups,
            "skipped_reextract_failures": self.skipped_reextract_failures,
        }


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if uploaded_at.tzinfo is None:
        return uploaded_at.replace(tzinfo=timezone.utc)
    return uploaded_at


def _source_path_score(value: str | None) -> tuple[int, int]:
    if not value:
        return (0, 0)
    richness = 1 if ("/" in value or "\\" in value) else 0
    return (richness, len(value))


def _path_basename(value: str | None) -> str:
    if not value:
        return ""
    return Path(value).name


def _needs_source_path_normalization(doc: DocumentRow) -> bool:
    if not doc.source_path:
        return True
    return _path_basename(doc.source_path) == doc.source_path


def _update_repair_provenance(doc: DocumentRow, **changes: Any) -> None:
    provenance = dict(doc.provenance or {})
    legacy_repair = dict(provenance.get("legacy_repair") or {})
    history = list(legacy_repair.get("history") or [])
    history.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "changes": changes,
        }
    )
    legacy_repair["history"] = history[-20:]
    provenance["legacy_repair"] = legacy_repair
    doc.provenance = provenance


def _load_bytes(path: str | None) -> bytes | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    return file_path.read_bytes()


def _classify_document_from_file(doc: DocumentRow) -> str | None:
    if not doc.file_path or not Path(doc.file_path).exists():
        return None
    try:
        resolved = resolve_document_type(
            doc.file_path,
            doc.mime_type or "application/octet-stream",
            allow_ocr=False,
        )
    except UploadValidationError:
        return None
    return resolved.doc_type


def _doc_preference_key(doc: DocumentRow) -> tuple[bool, int, int, datetime, str]:
    return (
        bool(doc.content_hash),
        *_source_path_score(doc.source_path),
        _normalized_uploaded_at(doc),
        doc.id,
    )


def _canonical_doc_type_for_group(group: list[DocumentRow]) -> str | None:
    classified = [doc_type for doc_type in (_classify_document_from_file(doc) for doc in group) if doc_type]
    if classified:
        counts = Counter(classified)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return ranked[0][0]

    ranked_docs = sorted(group, key=_doc_preference_key, reverse=True)
    return ranked_docs[0].doc_type if ranked_docs else None


def repair_user_documents(
    db: Session,
    *,
    email: str,
    apply_changes: bool = False,
    reextract_changed: bool = True,
) -> dict[str, Any]:
    user = db.query(UserRow).filter(UserRow.email == email).first()
    if not user:
        raise ValueError(f"User not found: {email}")

    docs = (
        db.query(DocumentRow)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user.id)
        .all()
    )

    summary = RepairSummary(inspected_documents=len(docs))
    touched_doc_ids: set[str] = set()
    touched_checks: dict[str, set[str]] = defaultdict(set)

    for doc in docs:
        changes: dict[str, Any] = {}
        if not doc.content_hash:
            content = _load_bytes(doc.file_path)
            if content is None:
                summary.skipped_missing_file += 1
            else:
                doc.content_hash = content_hash_for_bytes(content)
                summary.hash_backfilled += 1
                touched_doc_ids.add(doc.id)
                touched_checks[doc.check_id].add(doc.doc_type)
                changes["content_hash"] = "backfilled"

        if not doc.source_path:
            doc.source_path = doc.filename
            summary.source_path_normalized += 1
            touched_doc_ids.add(doc.id)
            touched_checks[doc.check_id].add(doc.doc_type)
            changes["source_path"] = doc.source_path

        if changes:
            _update_repair_provenance(doc, **changes)

    docs_by_hash: dict[str, list[DocumentRow]] = defaultdict(list)
    for doc in docs:
        if doc.content_hash:
            docs_by_hash[doc.content_hash].append(doc)

    docs_to_reextract: list[DocumentRow] = []
    for group in docs_by_hash.values():
        if len(group) < 2:
            continue

        richest_source_path = max(
            (doc.source_path for doc in group if doc.source_path),
            key=_source_path_score,
            default=None,
        )
        for doc in group:
            if richest_source_path and _needs_source_path_normalization(doc) and doc.source_path != richest_source_path:
                doc.source_path = richest_source_path
                doc.document_series_key = infer_document_series_key(
                    doc.doc_type,
                    source_path=doc.source_path,
                    filename=doc.filename,
                )
                summary.source_path_normalized += 1
                touched_doc_ids.add(doc.id)
                touched_checks[doc.check_id].add(doc.doc_type)
                _update_repair_provenance(doc, source_path=richest_source_path)

        doc_types = {doc.doc_type for doc in group}
        if len(doc_types) <= 1:
            continue

        canonical_doc_type = _canonical_doc_type_for_group(group)
        if not canonical_doc_type:
            summary.skipped_unresolved_conflict_groups += 1
            continue

        for doc in group:
            if doc.doc_type == canonical_doc_type:
                continue
            previous_doc_type = doc.doc_type
            doc.doc_type = canonical_doc_type
            doc.document_family = document_family_for_type(canonical_doc_type)
            doc.document_series_key = infer_document_series_key(
                canonical_doc_type,
                source_path=doc.source_path,
                filename=doc.filename,
            )
            summary.doc_type_reclassified += 1
            touched_doc_ids.add(doc.id)
            touched_checks[doc.check_id].update({previous_doc_type, canonical_doc_type})
            _update_repair_provenance(
                doc,
                doc_type={
                    "from": previous_doc_type,
                    "to": canonical_doc_type,
                },
            )
            if reextract_changed:
                docs_to_reextract.append(doc)

    if apply_changes:
        db.flush()

    for check_id, doc_types in touched_checks.items():
        check = db.get(CheckRow, check_id)
        if check is None:
            continue
        for doc_type in sorted(doc_types):
            _reindex_documents_for_type(check, doc_type)

    if apply_changes:
        db.flush()

    if apply_changes and reextract_changed:
        seen_reextract_ids: set[str] = set()
        for doc in docs_to_reextract:
            if doc.id in seen_reextract_ids:
                continue
            seen_reextract_ids.add(doc.id)
            try:
                extract_into_document(doc, db)
            except Exception:
                summary.skipped_reextract_failures += 1
                continue
            summary.reextracted_documents += 1
            touched_checks[doc.check_id].add(doc.doc_type)

        for check_id, doc_types in touched_checks.items():
            check = db.get(CheckRow, check_id)
            if check is None:
                continue
            for doc_type in sorted(doc_types):
                _reindex_documents_for_type(check, doc_type)

    if apply_changes:
        db.commit()
    else:
        db.rollback()

    duplicate_filename_summary: dict[str, int] = {}
    visible_docs = (
        db.query(DocumentRow)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user.id)
        .all()
    )
    filename_counts = Counter(doc.filename for doc in visible_docs if doc.filename)
    for filename, count in filename_counts.items():
        if count > 1:
            duplicate_filename_summary[filename] = count

    return {
        "user_id": user.id,
        "summary": summary.as_dict(),
        "duplicate_filenames": duplicate_filename_summary,
        "touched_documents": len(touched_doc_ids),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Target user email")
    parser.add_argument("--apply", action="store_true", help="Persist changes")
    parser.add_argument(
        "--skip-reextract",
        action="store_true",
        help="Do not rerun structured extraction for reclassified rows",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    SessionLocal = sessionmaker(bind=get_engine())
    session = SessionLocal()
    try:
        result = repair_user_documents(
            session,
            email=args.email,
            apply_changes=args.apply,
            reextract_changed=not args.skip_reextract,
        )
    finally:
        session.close()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
