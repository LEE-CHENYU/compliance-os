"""Phase 2 — dogfood batch upload from /Users/lichenyu/accounting → cl4183 on prod.

Walks /accounting, applies a primary-source filter (skip agent analyses,
voice memos, screenshots, vector DB internals), and uploads each
matching file to https://guardian-compliance.fly.dev as cl4183@columbia.edu.

The filter is deliberately conservative — when in doubt, skip. Phase 2's
job is to put a *clean* primary-source data room in front of the user,
not to maximize document count.

Usage:
    # mint a token first by SSHing into prod:
    flyctl ssh console -a guardian-compliance -C \
      "python -c 'from compliance_os.web.services.auth_service import create_token; \
       from compliance_os.web.models.database import get_session; \
       from compliance_os.web.models.auth import UserRow; \
       db=next(get_session()); u=db.query(UserRow).filter_by(email=\"cl4183@columbia.edu\").one(); \
       print(create_token(u.id, u.email))'"

    # save it to env, then:
    export PROD_CL4183_TOKEN=<paste token>
    python scripts/dogfood_cl4183.py --root /Users/lichenyu/accounting \
        --api-url https://guardian-compliance.fly.dev \
        --dry-run    # always do this first to review the filtered list

    # if the dry-run looks right:
    python scripts/dogfood_cl4183.py --root /Users/lichenyu/accounting \
        --api-url https://guardian-compliance.fly.dev
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from urllib import error as urlerror, request as urlrequest


# ── filter rules ────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".csv"}

# directory components that mark derived / agent-generated content,
# vector DB internals, scratch, or stuff that obviously isn't a primary
# source doc. case-insensitive substring match against the path.
SKIP_DIR_TOKENS = {
    "/.git/",
    "/.playwright-mcp/",
    "/.qwen/",
    "/.superpowers/",
    "/.agents/",
    "/.claude/",
    "/.dropbox/",
    "/chroma_db/",
    "/parsed/",
    "/scripts/",
    "/concerns/",
    "/obsidian/",
    "/output/",
    "/notebooks/",
    "/__pycache__/",
    "/node_modules/",
    "/temp/",
    "/old/",
    "/archive/",
    "/draft/",
    "/drafts/",
    "/.cache/",
}

# directories under /accounting/docs/ are mostly agent-generated analyses
# we identified those explicitly as negative controls in Phase 1
SKIP_DOCS_DIR = "/accounting/docs/"

# size cap — anything bigger than this is probably a recording, archive,
# or a multi-hundred-page batch we don't want to spam through the API
MAX_BYTES = 25 * 1024 * 1024  # 25 MB

# filename-substring skips (lowercase): scratch / generated / tooling
SKIP_FILENAME_TOKENS = {
    "draft_obsolete",
    "_obsolete",
    "_scratch",
    "_generated",
    "_dump",
    "_test",
}


def is_primary_source(path: Path, root: Path) -> tuple[bool, str]:
    """Return (keep, reason). reason describes why if rejected."""
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"ext {ext} not in allowlist"

    # POSIX-like path string for substring matches
    rel = "/" + str(path.relative_to(root)).replace(os.sep, "/").lower()
    abs_lower = str(path).lower()

    for token in SKIP_DIR_TOKENS:
        if token in abs_lower:
            return False, f"skip-dir token {token!r}"

    if SKIP_DOCS_DIR in abs_lower:
        return False, "in /accounting/docs/ (agent analyses)"

    name = path.name.lower()
    for token in SKIP_FILENAME_TOKENS:
        if token in name:
            return False, f"filename token {token!r}"

    try:
        size = path.stat().st_size
    except OSError as exc:
        return False, f"stat error: {exc}"
    if size > MAX_BYTES:
        return False, f"size {size/1e6:.1f}MB exceeds {MAX_BYTES/1e6:.0f}MB cap"
    if size == 0:
        return False, "empty file"

    return True, "ok"


def scan(root: Path) -> tuple[list[Path], list[tuple[Path, str]]]:
    keep: list[Path] = []
    skip: list[tuple[Path, str]] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        ok, reason = is_primary_source(p, root)
        if ok:
            keep.append(p)
        else:
            skip.append((p, reason))
    return keep, skip


def upload_one(api_url: str, token: str, file_path: Path) -> tuple[int, dict, float]:
    boundary = f"----GuardianDogfood{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    try:
        file_bytes = file_path.read_bytes()
    except FileNotFoundError:
        # the file was scanned at startup but moved/deleted before we got
        # to it — happens when the user is reorganizing /accounting in
        # the middle of a long dogfood run. soft skip with a marker.
        return -1, {"error": "file_vanished", "detail": "file no longer exists at scan-time path"}, 0.0
    except OSError as exc:
        return -2, {"error": "file_read_error", "detail": str(exc)}, 0.0

    body = []
    body.append(f"--{boundary}\r\n".encode())
    body.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode()
    )
    body.append(f"Content-Type: {mime_type}\r\n\r\n".encode())
    body.append(file_bytes)
    body.append(b"\r\n")
    body.append(f"--{boundary}\r\n".encode())
    body.append(b'Content-Disposition: form-data; name="duplicate_action"\r\n\r\n')
    body.append(b"keep")
    body.append(b"\r\n")
    body.append(f"--{boundary}--\r\n".encode())

    req = urlrequest.Request(
        f"{api_url}/api/dashboard/upload",
        data=b"".join(body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode())
            return resp.status, payload, (time.perf_counter() - t0) * 1000
    except urlerror.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode())
        except Exception:
            payload = {"error": str(exc)}
        return exc.code, payload, (time.perf_counter() - t0) * 1000
    except Exception as exc:
        return 0, {"error": str(exc)}, (time.perf_counter() - t0) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/Users/lichenyu/accounting")
    parser.add_argument("--api-url", default="https://guardian-compliance.fly.dev")
    parser.add_argument(
        "--dry-run", action="store_true", help="list filtered files without uploading"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="cap upload count for testing (0 = no cap)"
    )
    parser.add_argument(
        "--manifest-out",
        default="/tmp/guardian-eval/dogfood_manifest.json",
        help="where to write the keep/skip manifest",
    )
    parser.add_argument(
        "--report-out",
        default="docs/dogfood_cl4183_2026-04-30.json",
        help="where to write the upload-result report",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "skip any path that already appears in --report-out with a "
            "definitive status (2xx or 4xx). useful after a crash so we "
            "don't re-pay the dedup cost on hundreds of already-seen files."
        ),
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    print(f"scanning {root} ...", flush=True)
    keep, skip = scan(root)
    print(f"  keep: {len(keep)}", flush=True)
    print(f"  skip: {len(skip)}", flush=True)

    Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifest_out, "w") as f:
        json.dump(
            {
                "root": str(root),
                "keep": [str(p) for p in keep],
                "skip": [{"path": str(p), "reason": r} for p, r in skip],
            },
            f,
            indent=2,
        )
    print(f"  manifest: {args.manifest_out}", flush=True)

    # bucket the skip list to make it scannable
    skip_buckets = Counter(r.split(":")[0] for _, r in skip)
    print("\nskip reasons:")
    for reason, count in skip_buckets.most_common(10):
        print(f"  ×{count:>4} {reason}")

    if args.dry_run:
        print("\n--dry-run set — exiting before upload")
        print("\nfirst 30 kept files:")
        for p in keep[:30]:
            print(f"  {p}")
        return 0

    token = os.environ.get("PROD_CL4183_TOKEN", "").strip()
    if not token:
        print("\nERROR: set PROD_CL4183_TOKEN env var with cl4183 prod JWT", file=sys.stderr)
        return 2

    files = keep[: args.limit] if args.limit else keep

    results: list[dict] = []
    seen_paths: set[str] = set()
    if args.resume and Path(args.report_out).exists():
        prior = json.loads(Path(args.report_out).read_text())
        for r in prior.get("results", []):
            status = r.get("status", 0)
            if 200 <= status < 300 or 400 <= status < 500:
                seen_paths.add(r["path"])
        results = prior.get("results", [])
        files = [p for p in files if str(p) not in seen_paths]
        print(
            f"resume: loaded {len(prior.get('results', []))} prior records, "
            f"skipping {len(seen_paths)} settled paths; "
            f"{len(files)} new files to upload",
            flush=True,
        )

    print(f"\nuploading {len(files)} files to {args.api_url} ...", flush=True)

    ok_count = sum(1 for r in results if 200 <= r.get("status", 0) < 300)
    err_count = sum(1 for r in results if r.get("status", 0) >= 400 or r.get("status", 0) < 0)
    dup_count = sum(1 for r in results if r.get("status", 0) >= 200 and r.get("status", 0) < 300 and r.get("doc_type"))
    for i, p in enumerate(files, 1):
        status, payload, duration = upload_one(args.api_url, token, p)
        sym = "OK"
        if 200 <= status < 300:
            ok_count += 1
            if (payload.get("duplicates") or []):
                dup_count += 1
                sym = "DUP"
        else:
            err_count += 1
            sym = f"ERR{status}"

        results.append(
            {
                "path": str(p),
                "status": status,
                "ms": round(duration),
                "doc_type": (
                    (payload.get("duplicates") or [{}])[0].get("doc_type")
                    if (payload.get("duplicates") or [])
                    else None
                ),
                "error": payload.get("detail") if status >= 400 else None,
                "size": p.stat().st_size,
            }
        )
        print(
            f"  [{i:>3}/{len(files)}] {sym:>5} {duration:>6.0f}ms  {p.name[:70]}",
            flush=True,
        )

        if i % 25 == 0:
            with open(args.report_out, "w") as f:
                json.dump(
                    {
                        "api_url": args.api_url,
                        "ok": ok_count,
                        "duplicates": dup_count,
                        "errors": err_count,
                        "total": len(files),
                        "results": results,
                    },
                    f,
                    indent=2,
                )

    Path(args.report_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.report_out, "w") as f:
        json.dump(
            {
                "api_url": args.api_url,
                "ok": ok_count,
                "duplicates": dup_count,
                "errors": err_count,
                "total": len(files),
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n=== summary ===")
    print(f"  ok       : {ok_count}/{len(files)}")
    print(f"  duplicates: {dup_count}")
    print(f"  errors   : {err_count}")
    print(f"  report   : {args.report_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
