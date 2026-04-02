#!/usr/bin/env python3
"""Ingest documents from a source directory into Neon, with deduplication.

Replaces the old seed-from-sqlite approach with a direct source-dir → Neon pipeline.
Each unique file (by content_hash) is stored in exactly ONE check, determined by
the doc_type → track mapping below.

Usage:
    python scripts/ingest_source_to_neon.py \
        --source-dir "~/Desktop/Important Docs " \
        --target-email test@123.com \
        --dry-run          # preview what would be ingested

    python scripts/ingest_source_to_neon.py \
        --source-dir "~/Desktop/Important Docs " \
        --target-email test@123.com \
        --clean-dupes      # remove existing cross-check duplicates first
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow importing project modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Track mapping: each doc_type → exactly one track
# ---------------------------------------------------------------------------

DOC_TYPE_TO_TRACK: dict[str, str] = {
    # === stem_opt track (immigration + employment core) ===
    "i20": "stem_opt",
    "i94": "stem_opt",
    "i983": "stem_opt",
    "i765": "stem_opt",
    "i9": "stem_opt",
    "ead": "stem_opt",
    "visa_stamp": "stem_opt",
    "employment_letter": "stem_opt",
    "employment_contract": "stem_opt",
    "employment_correspondence": "stem_opt",
    "employment_offer": "stem_opt",
    "employment_offer_letter": "stem_opt",
    "employment_agreement": "stem_opt",
    "employment_screenshot": "stem_opt",
    "e_verify_case": "stem_opt",
    "e_verify": "stem_opt",
    "cpt_application": "stem_opt",
    "h1b_registration": "stem_opt",
    "h1b_registration_worksheet": "stem_opt",
    "h1b_registration_checklist": "stem_opt",
    "h1b_registration_roster": "stem_opt",
    "h1b_invoice": "stem_opt",
    "h1b_receipt": "stem_opt",
    "h1b_filing_fee_receipt": "stem_opt",
    "h1b_filing_invoice": "stem_opt",
    "h1b_status_summary": "stem_opt",
    "h1b_status_overview": "stem_opt",
    "h1b_g28": "stem_opt",
    "g_28": "stem_opt",
    "g28": "stem_opt",
    "paystub": "stem_opt",
    "w2": "stem_opt",
    "1042s": "stem_opt",
    "1099": "stem_opt",
    "wage_notice": "stem_opt",
    "final_evaluation": "stem_opt",
    "transfer_pending_letter": "stem_opt",
    "filing_confirmation": "stem_opt",

    # === entity track (business + tax) ===
    "tax_return": "entity",
    "ein_letter": "entity",
    "ein_application": "entity",
    "ein_application_instructions": "entity",
    "articles_of_organization": "entity",
    "operating_agreement": "entity",
    "certificate_of_good_standing": "entity",
    "registered_agent_consent": "entity",
    "business_license": "entity",
    "company_filing": "entity",
    "entity_notice": "entity",
    "legal_services_agreement": "entity",
    "annual_account_summary": "entity",

    # === student track ===
    "admission_letter": "student",
    "enrollment_verification": "student",
    "transcript": "student",
    "degree_certificate": "student",
    "student_id": "student",
    "language_test_certificate": "student",

    # === data_room track (personal, identity, housing, insurance, misc) ===
    "passport": "data_room",
    "drivers_license": "data_room",
    "social_security_card": "data_room",
    "social_security_record": "data_room",
    "identity_document": "data_room",
    "identifier_record": "data_room",
    "visa": "data_room",
    "w4": "data_room",
    "lease": "data_room",
    "insurance_policy": "data_room",
    "insurance_card": "data_room",
    "insurance_record": "data_room",
    "health_coverage_application": "data_room",
    "bank_statement": "data_room",
    "bank_account_record": "data_room",
    "bank_account_application": "data_room",
    "payment_receipt": "data_room",
    "payment_account_record": "data_room",
    "payment_service_agreement": "data_room",
    "payment_options_notice": "data_room",
    "wire_transfer_record": "data_room",
    "check_image": "data_room",
    "cover_letter": "data_room",
    "resume": "data_room",
    "non_disclosure_agreement": "data_room",
    "offer_letter": "data_room",
    "name_change_notice": "data_room",
    "debt_clearance_letter": "data_room",
    "collection_notice": "data_room",
    "order_confirmation": "data_room",
    "tax_interview": "data_room",
    "tax_notice": "data_room",
    "chat_export_asset": "data_room",
    "profile_photo": "data_room",
    "signature_page": "data_room",
    "event_invitation": "data_room",
    "news_article": "data_room",
    "support_request": "data_room",
    "immigration_reference": "data_room",
    "membership_welcome_packet": "data_room",
    "account_security_setup": "data_room",
    "residence_certificate": "data_room",
    "recovery_codes": "data_room",
    "public_key": "data_room",
    "system_configuration_screenshot": "data_room",
    "work_sample": "data_room",
    "diploma": "student",

    # Fallback
    "unclassified": "data_room",
}

# File extensions we ingest
INGESTIBLE_EXTENSIONS = {".pdf", ".jpeg", ".jpg", ".png", ".docx", ".doc", ".txt", ".csv"}

# Files/patterns to skip
SKIP_PATTERNS = {
    ".DS_Store", "Thumbs.db", "._",
}

# Doc types that are noise — skip during ingestion
NOISE_DOC_TYPES = {
    "chat_export_asset",        # WeChat/Telegram export icons
    "system_configuration_screenshot",
    "profile_photo",
    "news_article",
    "event_invitation",
    "public_key",
    "work_sample",
    "account_security_setup",
}


def _uuid() -> str:
    return str(uuid.uuid4())


def content_hash_for_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_pg_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized[len("postgres://"):]
    if normalized.startswith("postgresql://") and "+psycopg" not in normalized:
        normalized = "postgresql+psycopg://" + normalized[len("postgresql://"):]
    return normalized


def _mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _should_skip(path: Path) -> bool:
    name = path.name
    if any(name.startswith(p) for p in SKIP_PATTERNS):
        return True
    if name.startswith("~$"):
        return True
    if path.suffix.lower() not in INGESTIBLE_EXTENSIONS:
        return True
    if path.stat().st_size < 100:  # skip near-empty files
        return True
    return False


def classify_file(path: Path) -> str:
    """Classify a file using the project's classifier module."""
    try:
        from compliance_os.web.services.classifier import classify_filename
        result = classify_filename(str(path))
        return result.doc_type or "unclassified"
    except Exception:
        return "unclassified"


def scan_source_dir(source_dir: Path) -> list[dict]:
    """Scan source directory and return deduplicated file inventory."""
    files_by_hash: dict[str, dict] = {}
    skipped = 0

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if _should_skip(path):
            skipped += 1
            continue

        content_hash = content_hash_for_file(path)
        if content_hash in files_by_hash:
            skipped += 1
            continue

        doc_type = classify_file(path)
        if doc_type in NOISE_DOC_TYPES:
            skipped += 1
            continue
        track = DOC_TYPE_TO_TRACK.get(doc_type, "data_room")

        files_by_hash[content_hash] = {
            "path": path,
            "filename": path.name,
            "content_hash": content_hash,
            "doc_type": doc_type,
            "track": track,
            "file_size": path.stat().st_size,
            "mime_type": _mime_type(path),
            "source_path": str(path.relative_to(source_dir)),
        }

    print(f"Scanned: {len(files_by_hash)} unique files, {skipped} skipped")
    return list(files_by_hash.values())


def get_existing_hashes(engine, user_email: str) -> set[str]:
    """Get content_hashes already in Neon for this user."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT d.content_hash
            FROM documents_v2 d
            JOIN checks ch ON d.check_id = ch.id
            JOIN users u ON ch.user_id = u.id
            WHERE u.email = :email AND d.content_hash IS NOT NULL
        """), {"email": user_email}).fetchall()
    return {row[0] for row in rows}


def get_or_create_check(conn, user_id: str, track: str, check_cache: dict) -> str:
    """Get or create exactly one check per track for this user."""
    if track in check_cache:
        return check_cache[track]

    row = conn.execute(text("""
        SELECT id FROM checks
        WHERE user_id = :user_id AND track = :track
        LIMIT 1
    """), {"user_id": user_id, "track": track}).fetchone()

    if row:
        check_id = row[0]
    else:
        check_id = _uuid()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(text("""
            INSERT INTO checks (id, track, status, answers, user_id, created_at, updated_at)
            VALUES (:id, :track, 'saved', '{}', :user_id, :created_at, :updated_at)
        """), {
            "id": check_id, "track": track, "user_id": user_id,
            "created_at": now, "updated_at": now,
        })
        print(f"  Created check: {track} → {check_id}")

    check_cache[track] = check_id
    return check_id


def clean_duplicates(engine, user_email: str) -> int:
    """Remove cross-check duplicate documents, keeping one per content_hash+doc_type."""
    removed = 0
    with engine.begin() as conn:
        user_id = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": user_email},
        ).scalar_one_or_none()
        if not user_id:
            print(f"User not found: {user_email}")
            return 0

        # Find all docs for this user grouped by content_hash + doc_type
        rows = conn.execute(text("""
            SELECT d.id, d.content_hash, d.doc_type, d.is_active, d.uploaded_at, ch.track
            FROM documents_v2 d
            JOIN checks ch ON d.check_id = ch.id
            WHERE ch.user_id = :user_id AND d.content_hash IS NOT NULL
            ORDER BY d.content_hash, d.doc_type, d.is_active DESC, d.uploaded_at DESC
        """), {"user_id": user_id}).fetchall()

        # Group by (content_hash, doc_type) — keep first (most recent active), delete rest
        seen: dict[tuple, str] = {}
        to_delete: list[str] = []
        for row in rows:
            key = (row[1], row[2])  # content_hash, doc_type
            if key not in seen:
                seen[key] = row[0]
            else:
                to_delete.append(row[0])

        if not to_delete:
            print("No duplicates found.")
            return 0

        # Also collect test artifact IDs to delete in same pass
        artifact_ids = [
            row[0] for row in conn.execute(text("""
                SELECT d.id FROM documents_v2 d
                JOIN checks ch ON d.check_id = ch.id
                WHERE ch.user_id = :user_id
                  AND (d.filename = 'live-duplicate-check.txt'
                       OR d.doc_type = 'support_request')
                  AND d.id != ALL(:keep)
            """), {"user_id": user_id, "keep": list(seen.values())}).fetchall()
        ]
        all_delete = list(set(to_delete + artifact_ids))

        # Delete in correct FK order:
        # 1. subject_document_links (FK → documents_v2)
        conn.execute(text("DELETE FROM subject_document_links WHERE document_id = ANY(:ids)"), {"ids": all_delete})
        # 2. extracted_fields, ingestion_issues, llm_api_usage (FK → documents_v2)
        conn.execute(text("DELETE FROM extracted_fields WHERE document_id = ANY(:ids)"), {"ids": all_delete})
        conn.execute(text("DELETE FROM ingestion_issues WHERE document_id = ANY(:ids)"), {"ids": all_delete})
        conn.execute(text("DELETE FROM llm_api_usage WHERE document_id = ANY(:ids)"), {"ids": all_delete})
        # 3. documents_v2
        conn.execute(text("DELETE FROM documents_v2 WHERE id = ANY(:ids)"), {"ids": all_delete})
        removed = len(all_delete)
        if artifact_ids:
            print(f"  Removed {len(artifact_ids)} test artifacts")

        # Clean up empty checks (no documents left)
        empty_checks = [
            row[0] for row in conn.execute(text("""
                SELECT ch.id FROM checks ch
                WHERE ch.user_id = :user_id
                  AND NOT EXISTS (SELECT 1 FROM documents_v2 d WHERE d.check_id = ch.id)
            """), {"user_id": user_id}).fetchall()
        ]
        if empty_checks:
            # Delete in FK order: subject_document_links already cleaned above
            # subject_chains uses user_id not check_id — don't delete here, user still exists
            conn.execute(text("DELETE FROM findings WHERE check_id = ANY(:ids)"), {"ids": empty_checks})
            conn.execute(text("DELETE FROM followups WHERE check_id = ANY(:ids)"), {"ids": empty_checks})
            conn.execute(text("DELETE FROM comparisons WHERE check_id = ANY(:ids)"), {"ids": empty_checks})
            conn.execute(text("DELETE FROM ingestion_issues WHERE check_id = ANY(:ids) AND document_id IS NULL"), {"ids": empty_checks})
            conn.execute(text("DELETE FROM llm_api_usage WHERE check_id = ANY(:ids) AND document_id IS NULL"), {"ids": empty_checks})
            conn.execute(text("DELETE FROM checks WHERE id = ANY(:ids)"), {"ids": empty_checks})
            print(f"  Cleaned up {len(empty_checks)} empty checks")

    print(f"Removed {removed} duplicate document rows.")
    return removed


def reassign_documents_to_correct_tracks(engine, user_email: str) -> int:
    """Move documents to the correct check based on DOC_TYPE_TO_TRACK mapping."""
    moved = 0
    with engine.begin() as conn:
        user_id = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": user_email},
        ).scalar_one_or_none()
        if not user_id:
            return 0

        check_cache: dict[str, str] = {}

        # Get all remaining documents with their current track
        rows = conn.execute(text("""
            SELECT d.id, d.doc_type, ch.track, ch.id as check_id
            FROM documents_v2 d
            JOIN checks ch ON d.check_id = ch.id
            WHERE ch.user_id = :user_id
        """), {"user_id": user_id}).fetchall()

        for doc_id, doc_type, current_track, current_check_id in rows:
            target_track = DOC_TYPE_TO_TRACK.get(doc_type, "data_room")
            if current_track == target_track:
                continue

            target_check_id = get_or_create_check(conn, user_id, target_track, check_cache)
            conn.execute(
                text("UPDATE documents_v2 SET check_id = :check_id WHERE id = :id"),
                {"check_id": target_check_id, "id": doc_id},
            )
            moved += 1

    if moved:
        print(f"Reassigned {moved} documents to correct tracks.")
    return moved


def ingest_files(
    engine,
    user_email: str,
    files: list[dict],
    remote_upload_root: str = "/data/uploads/imported",
    *,
    extract: bool = False,
) -> int:
    """Insert new document records into Neon."""
    ingested = 0
    with engine.begin() as conn:
        user_id = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": user_email},
        ).scalar_one_or_none()
        if not user_id:
            raise SystemExit(f"User not found: {user_email}")

        check_cache: dict[str, str] = {}

        for f in files:
            check_id = get_or_create_check(conn, user_id, f["track"], check_cache)
            doc_id = _uuid()
            remote_path = f"{remote_upload_root}/{check_id}/{doc_id}_{f['filename']}"
            now = datetime.now(timezone.utc).isoformat()

            conn.execute(text("""
                INSERT INTO documents_v2 (
                    id, check_id, doc_type, document_family, document_series_key,
                    document_version, is_active, filename, source_path, file_path,
                    file_size, mime_type, content_hash, uploaded_at
                ) VALUES (
                    :id, :check_id, :doc_type, :doc_type, :doc_type,
                    1, true, :filename, :source_path, :file_path,
                    :file_size, :mime_type, :content_hash, :uploaded_at
                )
            """), {
                "id": doc_id,
                "check_id": check_id,
                "doc_type": f["doc_type"],
                "filename": f["filename"],
                "source_path": f["source_path"],
                "file_path": remote_path,
                "file_size": f["file_size"],
                "mime_type": f["mime_type"],
                "content_hash": f["content_hash"],
                "uploaded_at": now,
            })

            f["document_id"] = doc_id
            f["remote_path"] = remote_path
            f["check_id"] = check_id
            ingested += 1

    print(f"Ingested {ingested} new documents into Neon.")
    return ingested


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", required=True, help="Source directory to scan")
    parser.add_argument("--target-email", required=True, help="Target user email in Neon")
    parser.add_argument("--dest-url", default=None, help="Neon Postgres URL (reads DATABASE_URL env if not set)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't insert")
    parser.add_argument("--clean-dupes", action="store_true", help="Remove cross-check duplicates first")
    parser.add_argument("--reassign-tracks", action="store_true", help="Move docs to correct tracks")
    parser.add_argument("--manifest-path", default=None, help="Save file manifest JSON")
    parser.add_argument("--extract", action="store_true", help="Run OCR+extraction after insert (requires LLM API key)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    source_dir = Path(args.source_dir).expanduser().resolve()
    if not source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {source_dir}")

    dest_url = args.dest_url or os.environ.get("DATABASE_URL")
    if not dest_url:
        raise SystemExit("No --dest-url or DATABASE_URL provided")

    engine = create_engine(_normalize_pg_url(dest_url), pool_pre_ping=True)

    # Step 1: Clean duplicates if requested
    if args.clean_dupes:
        print("\n=== Cleaning cross-check duplicates ===")
        clean_duplicates(engine, args.target_email)

    # Step 2: Reassign to correct tracks if requested
    if args.reassign_tracks:
        print("\n=== Reassigning documents to correct tracks ===")
        reassign_documents_to_correct_tracks(engine, args.target_email)

    # Step 3: Scan source directory
    print(f"\n=== Scanning {source_dir} ===")
    all_files = scan_source_dir(source_dir)

    # Step 4: Filter out already-ingested files
    existing_hashes = get_existing_hashes(engine, args.target_email)
    new_files = [f for f in all_files if f["content_hash"] not in existing_hashes]
    already = len(all_files) - len(new_files)
    print(f"Already ingested: {already}, New to ingest: {len(new_files)}")

    if not new_files:
        print("Nothing new to ingest.")
        return 0

    # Step 5: Show summary by track
    by_track: dict[str, list] = {}
    for f in new_files:
        by_track.setdefault(f["track"], []).append(f)

    print("\n=== New files by track ===")
    for track in sorted(by_track):
        files = by_track[track]
        print(f"\n  {track} ({len(files)} files):")
        for f in sorted(files, key=lambda x: x["doc_type"] or "zzz"):
            print(f"    [{f['doc_type']:30s}] {f['filename']}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return 0

    # Step 6: Ingest
    print("\n=== Ingesting into Neon ===")
    count = ingest_files(engine, args.target_email, new_files, extract=args.extract)

    # Step 7: Save manifest
    if args.manifest_path:
        manifest_path = Path(args.manifest_path).expanduser().resolve()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_data = [
            {
                "source_path": str(f["path"]),
                "remote_path": f.get("remote_path", ""),
                "check_id": f.get("check_id", ""),
                "document_id": f.get("document_id", ""),
                "filename": f["filename"],
                "doc_type": f["doc_type"],
                "track": f["track"],
                "content_hash": f["content_hash"],
            }
            for f in new_files
        ]
        manifest_path.write_text(json.dumps(manifest_data, indent=2))
        print(f"Manifest written: {manifest_path}")

    print(f"\nDone. {count} documents ingested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
