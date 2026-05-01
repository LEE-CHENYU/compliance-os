"""Score the document-pipeline rubric defined in tests/eval/pipeline_rubric.md.

Reads tests/fixtures/accounting_eval_set/manifest.yaml, uploads each file
through POST /api/dashboard/upload, then scores six automatable rubric
dimensions and writes both a human-readable report and a machine-readable
JSON snapshot. Manual dimensions (finding extraction, deadline detection)
are stubbed in the report for the operator to fill in after eyeballing
the website.

Usage:
    python scripts/run_pipeline_eval.py \
        --manifest tests/fixtures/accounting_eval_set/manifest.yaml \
        --user-email eval-20260430@guardian.local \
        --api-url http://127.0.0.1:8000

The runner expects the user to already exist in the local DB. It resets
the user's documents at the start of the run so dedup numbers are clean.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import statistics
import sys
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urlerror, request as urlrequest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class UploadResult:
    path: str
    expected_doc_type: str | None
    status_code: int
    duration_ms: float
    document_id: str | None = None
    classified_doc_type: str | None = None
    duplicates: int = 0
    error: str | None = None


@dataclass
class RubricReport:
    started_at: str
    finished_at: str
    api_url: str
    user_email: str
    fixture_count: int
    ingest_reliability: float = 0.0
    classification_accuracy: float = 0.0
    classification_accuracy_by_type: dict[str, float] = field(default_factory=dict)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    dedup_correctness: float = 0.0
    index_coverage: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    overall: float = 0.0
    first_pass: list[UploadResult] = field(default_factory=list)
    second_pass: list[UploadResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _multipart_body(file_path: Path, doc_type: str | None) -> tuple[bytes, str]:
    """Build a multipart/form-data body matching what the MCP upload tool sends."""
    boundary = f"----GuardianEval{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    body = []
    body.append(f"--{boundary}\r\n".encode())
    body.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode()
    )
    body.append(f"Content-Type: {mime_type}\r\n\r\n".encode())
    body.append(file_path.read_bytes())
    body.append(b"\r\n")

    if doc_type:
        body.append(f"--{boundary}\r\n".encode())
        body.append(b'Content-Disposition: form-data; name="doc_type"\r\n\r\n')
        body.append(doc_type.encode())
        body.append(b"\r\n")

    body.append(f"--{boundary}\r\n".encode())
    body.append(b'Content-Disposition: form-data; name="duplicate_action"\r\n\r\n')
    body.append(b"keep")
    body.append(b"\r\n")

    body.append(f"--{boundary}--\r\n".encode())
    return b"".join(body), boundary


def _post_upload(api_url: str, token: str, file_path: Path) -> tuple[int, dict, float]:
    body, boundary = _multipart_body(file_path, doc_type=None)
    req = urlrequest.Request(
        f"{api_url}/api/dashboard/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
            return resp.status, payload, (time.perf_counter() - t0) * 1000
    except urlerror.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode())
        except Exception:
            payload = {"error": str(exc)}
        return exc.code, payload, (time.perf_counter() - t0) * 1000


def _get_documents(api_url: str, token: str) -> list[dict]:
    req = urlrequest.Request(
        f"{api_url}/api/dashboard/documents?limit=500",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urlrequest.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _reset_user_documents(user_email: str) -> int:
    """Delete all documents owned by the eval user. Returns count deleted.

    Documents are linked to users via CheckRow.user_id (no direct user_id
    on documents_v2) so we walk checks → docs → extracted fields.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from compliance_os.web.models.database import get_session
    from compliance_os.web.models.auth import UserRow
    from compliance_os.web.models.tables_v2 import (
        CheckRow,
        DocumentRow,
        ExtractedFieldRow,
    )

    db = next(get_session())
    user = db.query(UserRow).filter(UserRow.email == user_email).first()
    if user is None:
        raise RuntimeError(f"user {user_email} not found — provision it first")

    check_ids = [
        cid
        for (cid,) in db.query(CheckRow.id).filter(CheckRow.user_id == user.id).all()
    ]
    if not check_ids:
        db.close()
        return 0

    docs = db.query(DocumentRow).filter(DocumentRow.check_id.in_(check_ids)).all()
    n = len(docs)
    for d in docs:
        db.query(ExtractedFieldRow).filter(ExtractedFieldRow.document_id == d.id).delete()
        db.delete(d)
    db.commit()
    db.close()
    return n


def _mint_token(user_email: str) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from compliance_os.web.models.database import get_session
    from compliance_os.web.models.auth import UserRow
    from compliance_os.web.services.auth_service import create_token

    db = next(get_session())
    user = db.query(UserRow).filter(UserRow.email == user_email).first()
    if user is None:
        raise RuntimeError(f"user {user_email} not found — provision it first")
    token = create_token(user.id, user.email)
    db.close()
    return token


def run_pass(
    fixtures: list[dict],
    api_url: str,
    token: str,
    pass_label: str,
) -> list[UploadResult]:
    results: list[UploadResult] = []
    for i, entry in enumerate(fixtures, 1):
        path = Path(entry["path"])
        if not path.exists():
            results.append(
                UploadResult(
                    path=str(path),
                    expected_doc_type=entry.get("expected_doc_type"),
                    status_code=0,
                    duration_ms=0.0,
                    error="file_missing",
                )
            )
            continue

        status, payload, duration = _post_upload(api_url, token, path)
        result = UploadResult(
            path=str(path),
            expected_doc_type=entry.get("expected_doc_type"),
            status_code=status,
            duration_ms=duration,
        )
        if 200 <= status < 300:
            result.document_id = payload.get("document_id")
            dup = payload.get("duplicates", []) or []
            result.duplicates = len(dup)
            if dup:
                # the duplicates list returns the *prior* doc_type when a
                # match was found — that's what the classifier stored.
                result.classified_doc_type = dup[0].get("doc_type")
        else:
            result.error = json.dumps(payload)[:200]
        results.append(result)

        sym = "OK" if 200 <= status < 300 else "ERR"
        print(
            f"  [{pass_label} {i:>2}/{len(fixtures)}] {sym} {duration:>6.0f}ms  {path.name[:60]}",
            flush=True,
        )
    return results


def score_dim1(results: list[UploadResult]) -> float:
    ok = sum(1 for r in results if 200 <= r.status_code < 300)
    return ok / len(results) if results else 0.0


def score_dim2(
    results: list[UploadResult], docs_by_filename: dict[str, dict]
) -> tuple[float, dict[str, float], dict[str, dict[str, int]]]:
    """Score classification accuracy + per-type breakdown + confusion matrix.

    The classified doc_type is read from the actual document row (via
    docs_by_filename), not from the upload response, because the upload
    response on first-pass has no `duplicates` and the classifier writes
    the type to the row itself.
    """
    correct_overall = 0
    counted = 0
    by_type_correct: Counter[str] = Counter()
    by_type_total: Counter[str] = Counter()
    confusion: dict[str, dict[str, int]] = {}

    for r in results:
        if r.status_code < 200 or r.status_code >= 300:
            continue
        filename = Path(r.path).name
        doc = docs_by_filename.get(filename)
        if doc is None:
            continue
        actual = doc.get("doc_type") or None
        expected = r.expected_doc_type or None
        # write back so the report shows what classifier produced
        r.classified_doc_type = actual

        counted += 1
        key_expected = str(expected)
        key_actual = str(actual)
        by_type_total[key_expected] += 1
        confusion.setdefault(key_expected, {}).setdefault(key_actual, 0)
        confusion[key_expected][key_actual] += 1
        if actual == expected:
            correct_overall += 1
            by_type_correct[key_expected] += 1

    overall = correct_overall / counted if counted else 0.0
    by_type = {
        t: by_type_correct[t] / by_type_total[t] for t in by_type_total
    }
    return overall, by_type, confusion


def score_dim3(second_pass: list[UploadResult]) -> float:
    """Dedup correctness: every successful re-upload should report duplicates."""
    seen = [r for r in second_pass if 200 <= r.status_code < 300]
    if not seen:
        return 0.0
    return sum(1 for r in seen if r.duplicates > 0) / len(seen)


def score_dim4(first_pass: list[UploadResult], docs_by_filename: dict[str, dict]) -> float:
    """Index coverage: every uploaded doc must appear in /documents."""
    uploaded = [r for r in first_pass if 200 <= r.status_code < 300]
    if not uploaded:
        return 0.0
    found = sum(1 for r in uploaded if Path(r.path).name in docs_by_filename)
    return found / len(uploaded)


def score_latency(results: list[UploadResult]) -> tuple[float, float]:
    durations = [r.duration_ms for r in results if 200 <= r.status_code < 300]
    if not durations:
        return 0.0, 0.0
    durations_sorted = sorted(durations)
    p50 = statistics.median(durations_sorted)
    p95_idx = max(0, int(len(durations_sorted) * 0.95) - 1)
    p95 = durations_sorted[p95_idx]
    return p50, p95


def overall_score(
    *,
    ingest: float,
    classification: float,
    dedup: float,
    index_coverage: float,
    finding_extraction: float = 0.0,
    deadline_detection: float = 0.0,
) -> float:
    return (
        0.20 * ingest
        + 0.30 * classification
        + 0.10 * dedup
        + 0.15 * index_coverage
        + 0.15 * finding_extraction
        + 0.10 * deadline_detection
    )


def render_report(report: RubricReport, out_md: Path, out_json: Path) -> None:
    lines = []
    lines.append(f"# Pipeline eval — {report.started_at[:10]}")
    lines.append("")
    lines.append(f"- API: `{report.api_url}`")
    lines.append(f"- User: `{report.user_email}`")
    lines.append(f"- Fixture size: {report.fixture_count}")
    lines.append(f"- Started: {report.started_at}")
    lines.append(f"- Finished: {report.finished_at}")
    lines.append("")
    lines.append("## Scores")
    lines.append("")
    lines.append("| Dim | Name | Score | Pass bar | Status |")
    lines.append("|-----|------|-------|----------|--------|")
    bars = {
        1: ("Ingest reliability", report.ingest_reliability, 0.98),
        2: ("Classification accuracy", report.classification_accuracy, 0.85),
        3: ("Dedup correctness", report.dedup_correctness, 1.00),
        4: ("Index coverage", report.index_coverage, 0.95),
    }
    for dim, (name, score, bar) in bars.items():
        status = "PASS" if score >= bar else "FAIL"
        lines.append(f"| {dim} | {name} | {score*100:.1f}% | {bar*100:.0f}% | {status} |")
    lines.append(f"| 5 | Finding extraction (manual) | — | 5/5 | needs eyeball |")
    lines.append(f"| 6 | Deadline detection (manual) | — | 5/5 | needs eyeball |")
    lines.append(f"| 7 | Latency p50 / p95 | {report.p50_latency_ms:.0f}ms / {report.p95_latency_ms:.0f}ms | <30000ms | — |")
    lines.append(f"| 8 | Cost / 100 docs | (logged below) | — | baseline |")
    lines.append(f"")
    lines.append(f"**Overall (auto-only):** {report.overall*100:.1f}%")
    lines.append(f"")
    lines.append("## Classification accuracy by expected type")
    lines.append("")
    lines.append("| Expected | Score |")
    lines.append("|----------|-------|")
    for t, s in sorted(report.classification_accuracy_by_type.items()):
        lines.append(f"| `{t}` | {s*100:.0f}% |")
    lines.append("")
    lines.append("## Confusion (expected → actual)")
    lines.append("")
    for expected, actuals in sorted(report.confusion.items()):
        for actual, n in sorted(actuals.items()):
            mark = "" if expected == actual else "  ← MISMATCH"
            lines.append(f"- `{expected}` → `{actual}`  ×{n}{mark}")
    lines.append("")
    lines.append("## Per-file first-pass results")
    lines.append("")
    lines.append("| File | Expected | Classified | Status | ms |")
    lines.append("|------|----------|------------|--------|----|")
    for r in report.first_pass:
        ok = "OK" if 200 <= r.status_code < 300 else f"ERR {r.status_code}"
        lines.append(
            f"| `{Path(r.path).name}` | `{r.expected_doc_type or 'None'}` | `{r.classified_doc_type or 'None'}` | {ok} | {r.duration_ms:.0f} |"
        )
    if report.notes:
        lines.append("")
        lines.append("## Notes")
        for n in report.notes:
            lines.append(f"- {n}")

    out_md.write_text("\n".join(lines) + "\n")
    out_json.write_text(
        json.dumps(
            {
                "started_at": report.started_at,
                "finished_at": report.finished_at,
                "api_url": report.api_url,
                "user_email": report.user_email,
                "fixture_count": report.fixture_count,
                "scores": {
                    "ingest_reliability": report.ingest_reliability,
                    "classification_accuracy": report.classification_accuracy,
                    "classification_accuracy_by_type": report.classification_accuracy_by_type,
                    "dedup_correctness": report.dedup_correctness,
                    "index_coverage": report.index_coverage,
                    "p50_latency_ms": report.p50_latency_ms,
                    "p95_latency_ms": report.p95_latency_ms,
                    "overall_auto": report.overall,
                },
                "confusion": report.confusion,
                "first_pass": [vars(r) for r in report.first_pass],
                "second_pass": [vars(r) for r in report.second_pass],
                "notes": report.notes,
            },
            indent=2,
            default=str,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--user-email", required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--out-prefix",
        default=None,
        help="output filename prefix; defaults to docs/pipeline_eval_<YYYY-MM-DD>",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    fixtures = yaml.safe_load(manifest_path.read_text())["fixtures"]
    print(f"loaded {len(fixtures)} fixture entries from {manifest_path}", flush=True)

    print(f"resetting documents for {args.user_email} ...", flush=True)
    deleted = _reset_user_documents(args.user_email)
    print(f"  deleted {deleted} prior docs", flush=True)

    token = _mint_token(args.user_email)

    started = datetime.now(timezone.utc).isoformat()
    print("\n=== first-pass upload ===", flush=True)
    first = run_pass(fixtures, args.api_url, token, "1st")
    docs = _get_documents(args.api_url, token)
    docs_by_filename = {d["filename"]: d for d in docs}

    print("\n=== second-pass upload (dedup test) ===", flush=True)
    second = run_pass(fixtures, args.api_url, token, "2nd")

    finished = datetime.now(timezone.utc).isoformat()

    dim1 = score_dim1(first)
    dim2, dim2_by_type, confusion = score_dim2(first, docs_by_filename)
    dim3 = score_dim3(second)
    dim4 = score_dim4(first, docs_by_filename)
    p50, p95 = score_latency(first)
    overall = overall_score(
        ingest=dim1,
        classification=dim2,
        dedup=dim3,
        index_coverage=dim4,
    )

    report = RubricReport(
        started_at=started,
        finished_at=finished,
        api_url=args.api_url,
        user_email=args.user_email,
        fixture_count=len(fixtures),
        ingest_reliability=dim1,
        classification_accuracy=dim2,
        classification_accuracy_by_type=dim2_by_type,
        confusion=confusion,
        dedup_correctness=dim3,
        index_coverage=dim4,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        overall=overall,
        first_pass=first,
        second_pass=second,
    )

    out_prefix = args.out_prefix or f"docs/pipeline_eval_{started[:10]}"
    out_prefix_path = REPO_ROOT / out_prefix
    out_prefix_path.parent.mkdir(parents=True, exist_ok=True)
    render_report(
        report,
        out_md=Path(f"{out_prefix_path}.md"),
        out_json=Path(f"{out_prefix_path}.json"),
    )

    print(f"\n=== rubric ===")
    print(f"  ingest_reliability    : {dim1*100:6.1f}%   (>= 98% to pass)")
    print(f"  classification_accuracy: {dim2*100:6.1f}%   (>= 85% to pass)")
    print(f"  dedup_correctness     : {dim3*100:6.1f}%   (== 100% to pass)")
    print(f"  index_coverage        : {dim4*100:6.1f}%   (>= 95% to pass)")
    print(f"  latency p50 / p95     : {p50:6.0f}ms / {p95:.0f}ms")
    print(f"  overall (auto)        : {overall*100:6.1f}%")
    print(f"\nreport: {out_prefix}.md / .json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
