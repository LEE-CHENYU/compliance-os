#!/usr/bin/env python3
"""Upload files to Guardian via the real dashboard API endpoint.

This exercises the full pipeline: classify → dedup → OCR → extract → issue detect → subject chains.

Usage:
    python scripts/upload_via_api.py \
        --source-dir "~/Desktop/Important Docs " \
        --api-url https://guardiancompliance.app \
        --email test@123.com --password test123 \
        --batch-size 10 \
        --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
import time
from pathlib import Path

import requests

# File extensions we ingest
INGESTIBLE_EXTENSIONS = {".pdf", ".jpeg", ".jpg", ".png", ".docx", ".doc", ".txt", ".csv"}

# Doc types that are noise — skip
NOISE_FILENAMES = {
    ".DS_Store", "Thumbs.db",
}

# Filename patterns to skip (chat icons, retina assets, etc.)
SKIP_PREFIXES = ("._", "~$", "media_", "section_", "back@", "back.")
SKIP_SUFFIXES = ("@2x.png", "@2x.jpg", "_thumb.jpg")


def content_hash_for_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_skip(path: Path) -> bool:
    name = path.name
    if name in NOISE_FILENAMES:
        return True
    if any(name.startswith(p) for p in SKIP_PREFIXES):
        return True
    if any(name.endswith(s) for s in SKIP_SUFFIXES):
        return True
    if path.suffix.lower() not in INGESTIBLE_EXTENSIONS:
        return True
    if path.stat().st_size < 100:
        return True
    return False


def scan_source(source_dir: Path) -> list[Path]:
    """Return deduplicated list of files to upload."""
    seen_hashes: set[str] = set()
    files: list[Path] = []
    skipped = 0

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if should_skip(path):
            skipped += 1
            continue

        h = content_hash_for_file(path)
        if h in seen_hashes:
            skipped += 1
            continue
        seen_hashes.add(h)
        files.append(path)

    print(f"Scanned: {len(files)} unique files, {skipped} skipped")
    return files


def login(api_url: str, email: str, password: str) -> str:
    resp = requests.post(
        f"{api_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def get_existing_docs(api_url: str, token: str) -> set[str]:
    """Get filenames already in the dashboard."""
    resp = requests.get(
        f"{api_url}/api/dashboard/documents",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return {doc["filename"] for doc in resp.json()}


def upload_file(api_url: str, token: str, file_path: Path, source_path: str) -> dict:
    """Upload a single file via the dashboard API."""
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{api_url}/api/dashboard/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (file_path.name, f, mime)},
            data={
                "source_path": source_path,
                "duplicate_action": "skip",
            },
            timeout=120,
        )
    if resp.status_code == 200:
        data = resp.json()
        data["_status_code"] = 200
        return data
    else:
        return {"error": resp.status_code, "detail": resp.text[:300]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--api-url", default="https://guardiancompliance.app")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--batch-size", type=int, default=10, help="Files per batch (pause between batches)")
    parser.add_argument("--start-at", type=int, default=0, help="Skip first N files (resume from failure)")
    parser.add_argument("--max-files", type=int, default=0, help="Max files to upload (0 = all)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--results-path", default="output/upload_results.json")
    args = parser.parse_args(argv)

    source_dir = Path(args.source_dir).expanduser().resolve()
    if not source_dir.is_dir():
        raise SystemExit(f"Not a directory: {source_dir}")

    # Scan
    print(f"=== Scanning {source_dir} ===")
    files = scan_source(source_dir)

    if args.dry_run:
        for i, f in enumerate(files):
            print(f"  {i:3d}. {f.name}")
        print(f"\n[DRY RUN] {len(files)} files would be uploaded.")
        return 0

    # Login
    print(f"\n=== Logging in as {args.email} ===")
    token = login(args.api_url, args.email, args.password)
    print("Authenticated.")

    # Check existing
    existing = get_existing_docs(args.api_url, token)
    print(f"Already in dashboard: {len(existing)} documents")

    # Upload
    to_upload = files[args.start_at:]
    if args.max_files > 0:
        to_upload = to_upload[:args.max_files]

    print(f"\n=== Uploading {len(to_upload)} files (batch_size={args.batch_size}) ===")
    results: list[dict] = []
    success = 0
    errors = 0
    skipped = 0

    for i, file_path in enumerate(to_upload):
        idx = args.start_at + i
        source_rel = str(file_path.relative_to(source_dir))

        if file_path.name in existing:
            print(f"  [{idx:3d}] SKIP (exists) {file_path.name}")
            skipped += 1
            results.append({"index": idx, "file": file_path.name, "status": "skipped_exists"})
            continue

        print(f"  [{idx:3d}] Uploading {file_path.name} ({file_path.stat().st_size // 1024}KB)...", end=" ", flush=True)
        t0 = time.time()
        result = upload_file(args.api_url, token, file_path, source_rel)
        elapsed = time.time() - t0

        if "error" in result:
            detail = result.get("detail", "")
            # If classification failed, try with pre-classified doc_type
            if "Could not determine document type" in detail:
                print(f"SKIP (unclassifiable, {elapsed:.1f}s)")
                skipped += 1
                results.append({"index": idx, "file": file_path.name, "status": "skipped_unclassifiable"})
            else:
                print(f"ERROR {result['error']} ({elapsed:.1f}s) {detail[:80]}")
                errors += 1
                results.append({"index": idx, "file": file_path.name, "status": "error", "detail": detail})
        else:
            status = result.get("status", "ok")
            doc_id = result.get("document_id", "?")[:8]
            dupes = len(result.get("duplicates", []))
            dupe_note = f", {dupes} dupes" if dupes else ""
            print(f"OK → {status} (doc={doc_id}{dupe_note}, {elapsed:.1f}s)")
            success += 1
            results.append({
                "index": idx, "file": file_path.name, "status": status,
                "document_id": result.get("document_id"),
                "content_hash": result.get("content_hash"),
                "elapsed": round(elapsed, 1),
            })
            existing.add(file_path.name)

        # Pause between batches
        if (i + 1) % args.batch_size == 0 and i + 1 < len(to_upload):
            print(f"  --- batch {(i + 1) // args.batch_size} complete, pausing 2s ---")
            time.sleep(2)

    # Save results
    results_path = Path(args.results_path).expanduser().resolve()
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(results, indent=2))

    print(f"\n=== Done ===")
    print(f"  Success: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")
    print(f"  Results: {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
