"""Guardian MCP Server — unified compliance agent for Claude Code and Codex.

Exposes the same compliance intelligence as the OpenClaw integration
(documents, findings, deadlines, chat) plus form filing, document
processing, and Gmail tools via the Model Context Protocol.

Architecture: Document parsing runs locally (PyMuPDF, regex classifier)
on the user's client — no Guardian API token cost. Compliance context
is fetched from the Guardian REST API.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from urllib import error, request

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "guardian",
    instructions=(
        "You are Guardian, an immigration, tax, and business compliance assistant. "
        "Use these tools to help the user understand their compliance status, "
        "process documents, generate forms, and manage compliance correspondence.\n\n"
        "Guardian covers three tracks:\n"
        "- Young Professional: STEM OPT, H-1B, I-140, tax obligations\n"
        "- Entrepreneur: LLC/C-Corp compliance, Form 5472, entity structure\n"
        "- International Student: CPT, I-20, Form 8843, tax filing\n\n"
        "Rules:\n"
        "- Be calm and procedural. Never alarmist.\n"
        "- Use plain English. Briefly explain terms like SEVIS, DSO, FBAR.\n"
        "- Lead with the most urgent item.\n"
        "- Note that Guardian provides compliance risk detection, not legal advice.\n"
        "- For critical issues, recommend consulting an immigration attorney.\n"
        "- For tax issues, recommend a CPA experienced with nonresident filings."
    ),
)

# ─── Configuration ───────────────────────────────────────────────

GUARDIAN_API_URL = os.environ.get("GUARDIAN_API_URL", "http://localhost:8000")
GUARDIAN_TOKEN = os.environ.get("GUARDIAN_TOKEN", "")


def _is_local_api() -> bool:
    return any(h in GUARDIAN_API_URL for h in ("localhost", "127.0.0.1", "0.0.0.0"))


def _resolve_token() -> str:
    """Return the best available auth token.

    Priority:
    1. Hosted MCP client token (set by SSE/HTTP middleware per-request)
    2. GUARDIAN_TOKEN env var (set in MCP config)
    3. Auto-generated dev JWT (localhost only, reads from local SQLite)
    """
    # 1. Hosted MCP client token (per-request, from HTTP headers)
    try:
        from compliance_os.mcp_hosted import get_mcp_client_token

        client_token = get_mcp_client_token()
        if client_token:
            return client_token
    except ImportError:
        pass

    # 2. Env var
    if GUARDIAN_TOKEN:
        return GUARDIAN_TOKEN

    # 3. Auto-generate for localhost
    if not _is_local_api():
        return ""
    try:
        from compliance_os.web.services.auth_service import create_token
        from compliance_os.web.models.database import get_session
        from compliance_os.web.models.auth import UserRow

        db = next(get_session())
        user = db.query(UserRow).first()
        db.close()
        if user:
            return create_token(user.id, user.email)
    except Exception:
        pass
    return ""


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    token = _resolve_token()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _is_hosted() -> bool:
    """Check if running inside the hosted FastAPI process."""
    try:
        from compliance_os.mcp_hosted import get_mcp_client_token

        return bool(get_mcp_client_token())
    except ImportError:
        return False


async def _api_get(path: str) -> dict | list:
    """GET from the Guardian API — async for both hosted and standalone."""
    if _is_hosted():
        import httpx

        from compliance_os.mcp_hosted import get_mcp_client_token
        from compliance_os.web.app import app

        token = get_mcp_client_token()
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = await client.get(path, headers=headers)
            resp.raise_for_status()
            return resp.json()

    # Standalone: blocking HTTP (OK for stdio — runs in its own process)
    req = request.Request(f"{GUARDIAN_API_URL}{path}", headers=_headers())
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except error.HTTPError as exc:
        raise RuntimeError(f"Guardian API {exc.code}: {exc.read().decode()[:200]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Cannot reach Guardian API at {GUARDIAN_API_URL}: {exc}") from exc


async def _api_post(path: str, payload: dict) -> dict:
    """POST to the Guardian API — async for both hosted and standalone."""
    if _is_hosted():
        import httpx

        from compliance_os.mcp_hosted import get_mcp_client_token
        from compliance_os.web.app import app

        token = get_mcp_client_token()
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = await client.post(path, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    req = request.Request(
        f"{GUARDIAN_API_URL}{path}",
        data=json.dumps(payload).encode(),
        headers=_headers(),
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except error.HTTPError as exc:
        raise RuntimeError(f"Guardian API {exc.code}: {exc.read().decode()[:200]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Cannot reach Guardian API at {GUARDIAN_API_URL}: {exc}") from exc


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COMPLIANCE CONTEXT (mirrors OpenClaw — fetches from Guardian API)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
async def guardian_status() -> str:
    """Get full compliance overview: findings, deadlines, key facts, document count.

    Returns the user's compliance status including critical issues,
    warnings, active subject chains, and upcoming deadlines.
    """
    try:
        timeline = await _api_get("/api/dashboard/timeline")
        stats = await _api_get("/api/dashboard/stats")
        chains = await _api_get("/api/dashboard/chains")
    except RuntimeError as exc:
        return f"Error: {exc}"

    lines = [
        "# Guardian Compliance Status",
        "",
        f"Documents: {stats.get('documents', 0)} | Active risks: {stats.get('risks', 0)}",
        "",
    ]

    findings = timeline.get("findings", [])
    critical = [f for f in findings if f.get("severity") == "critical"]
    warnings = [f for f in findings if f.get("severity") == "warning"]

    if critical:
        lines.append("## Critical Issues")
        for f in critical:
            lines.append(f"- **{f.get('title', '')}**")
            lines.append(f"  Action: {f.get('action', '')}")
        lines.append("")

    if warnings:
        lines.append("## Warnings")
        for f in warnings:
            lines.append(f"- **{f.get('title', '')}**")
            lines.append(f"  Action: {f.get('action', '')}")
        lines.append("")

    if not critical and not warnings:
        lines.extend(["No active compliance findings.", ""])

    if chains:
        lines.append("## Active Chains")
        for c in chains:
            label = f"- [{c.get('chain_type', '')}] **{c.get('display_name', '')}**"
            dates = [d for d in [c.get("start_date"), c.get("end_date")] if d]
            if dates:
                label += f" ({' to '.join(dates)})"
            lines.append(label)
        lines.append("")

    deadlines = timeline.get("deadlines", [])
    if deadlines:
        lines.append("## Upcoming Deadlines")
        for d in sorted(deadlines, key=lambda x: x.get("days", 999)):
            days = d.get("days", 0)
            title, date_str = d.get("title", ""), d.get("date", "")
            if days < 0:
                lines.append(f"- OVERDUE ({-days}d ago): {title} -- {date_str}")
            elif days <= 30:
                lines.append(f"- **{days} days:** {title} -- {date_str}")
            else:
                lines.append(f"- {days} days: {title} -- {date_str}")
        lines.append("")

    facts = timeline.get("key_facts", [])
    if facts:
        lines.append("## Key Facts")
        for f in facts:
            lines.append(f"- **{f.get('label', '')}:** {f.get('value', '')}")

    return "\n".join(lines)


@mcp.tool()
async def guardian_deadlines() -> str:
    """Get upcoming compliance deadlines sorted by urgency.

    Shows overdue items first, then items due within 30 days,
    then the rest. Includes days remaining and target dates.
    """
    try:
        timeline = await _api_get("/api/dashboard/timeline")
    except RuntimeError as exc:
        return f"Error: {exc}"

    deadlines = timeline.get("deadlines", [])
    if not deadlines:
        return "No upcoming deadlines."

    lines = ["# Upcoming Deadlines", ""]
    for d in sorted(deadlines, key=lambda x: x.get("days", 999)):
        days = d.get("days", 0)
        title, date_str = d.get("title", ""), d.get("date", "")
        if days < 0:
            lines.append(f"- OVERDUE ({-days}d ago): {title} -- {date_str}")
        elif days <= 30:
            lines.append(f"- **{days} days:** {title} -- {date_str}")
        else:
            lines.append(f"- {days} days: {title} -- {date_str}")
    return "\n".join(lines)


@mcp.tool()
async def guardian_risks() -> str:
    """Get compliance findings grouped by severity (critical, warning, advisory).

    Each finding includes a title, description, and recommended action.
    """
    try:
        timeline = await _api_get("/api/dashboard/timeline")
    except RuntimeError as exc:
        return f"Error: {exc}"

    findings = timeline.get("findings", [])
    if not findings:
        return "No active compliance findings."

    by_severity: dict[str, list[dict]] = {}
    for f in findings:
        by_severity.setdefault(f.get("severity", "info"), []).append(f)

    lines = ["# Compliance Findings", ""]
    for sev in ["critical", "warning", "advisory", "info"]:
        group = by_severity.get(sev, [])
        if group:
            lines.append(f"## {sev.title()} ({len(group)})")
            for f in group:
                lines.append(f"- **{f.get('title', '')}**")
                if f.get("action"):
                    lines.append(f"  Action: {f['action']}")
            lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def guardian_documents() -> str:
    """List all documents in the user's Guardian data room.

    Shows filename, document type, file size, and upload date.
    Also lists subject chains with linked document counts.
    """
    try:
        docs = await _api_get("/api/dashboard/documents")
        chains = await _api_get("/api/dashboard/chains")
    except RuntimeError as exc:
        return f"Error: {exc}"

    if not docs:
        return (
            "No documents uploaded yet. Upload I-983, employment letter, "
            "tax returns, or I-20 to get started."
        )

    lines = [f"# Documents ({len(docs)} files)", ""]
    for d in docs:
        doc_type = (d.get("doc_type") or "unknown").replace("_", " ").upper()
        size_kb = round(d.get("file_size", 0) / 1024, 1)
        uploaded = (d.get("uploaded_at") or "")[:10]
        lines.append(
            f"- **{d.get('filename', '')}** ({doc_type}, {size_kb} KB) -- uploaded {uploaded}"
        )

    if chains:
        lines.extend(["", "## Subject Chains"])
        for c in chains:
            doc_count = len(c.get("documents", []))
            lines.append(
                f"- [{c.get('chain_type', '')}] **{c.get('display_name', '')}** -- {doc_count} linked docs"
            )

    return "\n".join(lines)


@mcp.tool()
async def guardian_ask(question: str) -> str:
    """Ask Guardian's AI assistant a compliance question.

    The assistant has full context of the user's documents, findings,
    and immigration status. Good for questions like:
    - "Do I need to file FBAR?"
    - "When is my I-983 self-evaluation due?"
    - "Can I travel on pending H-1B?"

    Args:
        question: The compliance question to ask.
    """
    try:
        result = await _api_post("/api/chat", {"message": question, "history": []})
        return result.get("reply", "No response received.")
    except RuntimeError as exc:
        return f"Error: {exc}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DOCUMENT PROCESSING (local — no API token cost)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
def parse_document(file_path: str) -> str:
    """Extract text from a PDF or DOCX document locally.

    Uses PyMuPDF structured-block extraction for PDFs (preserves table
    layout) and python-docx for DOCX files. Runs entirely on the client
    with no API calls — zero token cost.

    Args:
        file_path: Absolute path to the document file.
    """
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from compliance_os.web.services.pdf_reader import extract_first_page

        text = extract_first_page(str(path))
        return text if text else "No text could be extracted from this PDF."

    if suffix in {".docx", ".doc"}:
        from compliance_os.web.services.docx_reader import extract_text

        text = extract_text(str(path))
        return text if text else "No text could be extracted from this document."

    if suffix in {".txt", ".csv", ".json", ".yaml", ".yml"}:
        return path.read_text(encoding="utf-8", errors="replace")[:50_000]

    return f"Unsupported file type: {suffix}. Supported: .pdf, .docx, .txt, .csv, .json, .yaml"


@mcp.tool()
def classify_document(file_path: str) -> str:
    """Classify a document by type using filename patterns and text analysis.

    Runs locally with regex pattern matching — no API calls. Recognizes
    40+ document types: W-2, 1099, I-20, I-94, passport, employment
    letter, tax return, bank statement, and more.

    Args:
        file_path: Absolute path to the document file.
    """
    path = Path(file_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

    from compliance_os.web.services.classifier import classify_file

    result = classify_file(str(path), mime_type, allow_ocr=False)
    return json.dumps(
        {
            "file": path.name,
            "doc_type": result.doc_type,
            "confidence": result.confidence,
            "source": result.source,
        }
    )


def _upload_single_file(file_path: Path, doc_type: str = "") -> dict:
    """Upload one file to Guardian API. Returns result dict."""
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()

    # Auto-classify locally if doc_type not provided
    if not doc_type:
        from compliance_os.web.services.classifier import classify_file

        cls = classify_file(str(file_path), mime_type, allow_ocr=False)
        if cls.doc_type:
            doc_type = cls.doc_type

    boundary = "----GuardianMCPBoundary"
    body_parts = []
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode()
    )
    body_parts.append(f"Content-Type: {mime_type}\r\n\r\n".encode())
    body_parts.append(file_bytes)
    body_parts.append(b"\r\n")

    if doc_type:
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="doc_type"\r\n\r\n')
        body_parts.append(doc_type.encode())
        body_parts.append(b"\r\n")

    # Auto-keep duplicates — MCP users have already reviewed the file
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(b'Content-Disposition: form-data; name="duplicate_action"\r\n\r\n')
    body_parts.append(b"keep")
    body_parts.append(b"\r\n")

    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(body_parts)

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    token = _resolve_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(
        f"{GUARDIAN_API_URL}/api/dashboard/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


@mcp.tool()
def upload_document(
    file_path: str,
    doc_type: str = "",
) -> str:
    """Upload a document to the user's Guardian data room.

    Automatically classifies the document locally (no token cost) and
    passes the type to Guardian. Duplicates are auto-kept since you've
    already reviewed the file in Claude Code / Codex.

    Typical workflow:
    1. parse_document → preview extracted text
    2. classify_document → confirm document type
    3. upload_document → send to Guardian

    Args:
        file_path: Absolute path to the document file.
        doc_type: Document type override (e.g., "w2", "i20"). Auto-detected if blank.
    """
    path = Path(file_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    try:
        result = _upload_single_file(path, doc_type)
        return json.dumps(result, default=str)
    except error.HTTPError as exc:
        detail = exc.read().decode()[:300]
        try:
            err = json.loads(detail)
            if isinstance(err.get("detail"), dict) and err["detail"].get("error") == "duplicate_upload_detected":
                return json.dumps({
                    "status": "duplicate_detected",
                    "doc_type": err["detail"].get("resolved_doc_type"),
                    "message": "This file already exists in your data room.",
                })
        except (json.JSONDecodeError, KeyError):
            pass
        return json.dumps({"error": f"Upload failed ({exc.code}): {detail}"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def batch_upload(
    directory: str,
    extensions: str = ".pdf,.docx,.txt,.csv",
) -> str:
    """Upload all documents from a directory to Guardian.

    Scans the directory for files matching the given extensions,
    classifies each locally, and uploads to the data room.
    Skips files that are already uploaded (duplicate detection).

    Args:
        directory: Path to directory containing documents.
        extensions: Comma-separated file extensions to include (default: .pdf,.docx,.txt,.csv).
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return json.dumps({"error": f"Not a directory: {directory}"})

    exts = {e.strip().lower() for e in extensions.split(",") if e.strip()}
    files = sorted(
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in exts
    )

    if not files:
        return json.dumps({"error": f"No files found matching {extensions} in {directory}"})

    results = []
    for f in files:
        try:
            result = _upload_single_file(f)
            results.append({"file": f.name, "status": "uploaded", "doc_type": result.get("doc_type")})
        except error.HTTPError as exc:
            detail = exc.read().decode()[:200]
            results.append({"file": f.name, "status": "failed", "error": f"HTTP {exc.code}: {detail}"})
        except Exception as exc:
            results.append({"file": f.name, "status": "failed", "error": str(exc)})

    uploaded = sum(1 for r in results if r["status"] == "uploaded")
    failed = sum(1 for r in results if r["status"] == "failed")
    return json.dumps({
        "summary": f"{uploaded} uploaded, {failed} failed out of {len(files)} files",
        "results": results,
    }, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FORM FILING (local — uses existing Python services)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
def generate_form_8843(
    full_name: str,
    country_citizenship: str,
    visa_type: str,
    arrival_date: str,
    days_present_current: int,
    days_present_year_1_ago: int = 0,
    days_present_year_2_ago: int = 0,
    school_name: str = "",
    tax_year: int = 0,
    passport_number: str = "",
    us_taxpayer_id: str = "",
) -> str:
    """Generate a filled IRS Form 8843 PDF.

    Produces a ready-to-print PDF with filing guidance (deadline,
    mailing address, next steps). The PDF is returned as base64.

    Args:
        full_name: Full legal name as on passport.
        country_citizenship: Country of citizenship.
        visa_type: Current visa type (F-1, J-1, H-1B, etc.).
        arrival_date: US arrival date (YYYY-MM-DD).
        days_present_current: Days present in US for current tax year.
        days_present_year_1_ago: Days present one year ago.
        days_present_year_2_ago: Days present two years ago.
        school_name: School or program sponsor name.
        tax_year: Tax year (default: last calendar year).
        passport_number: Passport number.
        us_taxpayer_id: SSN or ITIN if available.
    """
    from compliance_os.web.services.form_8843 import generate_form_8843 as _gen
    from compliance_os.web.services.mailing_service import build_form_8843_filing_context

    inputs: dict[str, object] = {
        "full_name": full_name,
        "country_citizenship": country_citizenship,
        "visa_type": visa_type,
        "arrival_date": arrival_date,
        "days_present_current": days_present_current,
        "days_present_year_1_ago": days_present_year_1_ago,
        "days_present_year_2_ago": days_present_year_2_ago,
        "school_name": school_name,
        "passport_number": passport_number,
        "us_taxpayer_id": us_taxpayer_id,
    }
    if tax_year:
        inputs["tax_year"] = tax_year

    try:
        pdf_bytes = _gen(inputs)
        filing_ctx = build_form_8843_filing_context(inputs)
        return json.dumps({
            "status": "success",
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "pdf_size_bytes": len(pdf_bytes),
            "filing_guidance": {
                "scenario": filing_ctx.get("scenario"),
                "headline": filing_ctx.get("headline"),
                "summary": filing_ctx.get("summary"),
                "deadline": str(filing_ctx.get("filing_deadline", "")),
                "address": filing_ctx.get("address_block", ""),
                "steps": filing_ctx.get("steps", []),
            },
        })
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})


@mcp.tool()
def run_compliance_check(
    check_type: str,
    inputs_json: str,
) -> str:
    """Run a Guardian compliance check locally.

    Evaluates compliance rules against the provided inputs and returns
    findings, verdict, and recommended actions.

    Args:
        check_type: One of: h1b_doc_check, fbar, student_tax, 83b_election
        inputs_json: JSON object with check-specific inputs. Use guardian_ask
            to learn what fields each check type expects.
    """
    try:
        inputs = json.loads(inputs_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc}"})

    runners = {
        "h1b_doc_check": "compliance_os.web.services.h1b_doc_check:process_h1b_doc_check",
        "fbar": "compliance_os.web.services.fbar_check:process_fbar_check",
        "student_tax": "compliance_os.web.services.student_tax_check:process_student_tax_check",
        "83b_election": "compliance_os.web.services.election_83b:process_election_83b",
    }

    spec = runners.get(check_type)
    if not spec:
        return json.dumps({
            "error": f"Unknown check type: {check_type}",
            "available": list(runners.keys()),
        })

    module_path, func_name = spec.rsplit(":", 1)
    import importlib
    import uuid

    module = importlib.import_module(module_path)
    func = getattr(module, func_name)

    try:
        order_id = f"mcp-{uuid.uuid4().hex[:12]}"
        result = func(order_id, inputs)
        return json.dumps(result, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_filing_guidance(
    form_type: str,
    filing_with_tax_return: bool = False,
    tax_year: int = 0,
) -> str:
    """Get filing guidance, deadlines, and mailing instructions for a form.

    Args:
        form_type: Currently supported: "form_8843"
        filing_with_tax_return: True if filing Form 8843 with a 1040-NR package.
        tax_year: Tax year (default: last calendar year).
    """
    if form_type == "form_8843":
        from compliance_os.web.services.mailing_service import (
            build_form_8843_filing_context,
            build_form_8843_mailing_kit,
        )

        inputs: dict[str, object] = {"filing_with_tax_return": filing_with_tax_return}
        if tax_year:
            inputs["tax_year"] = tax_year
        ctx = build_form_8843_filing_context(inputs)
        kit = build_form_8843_mailing_kit(ctx)
        ctx["filing_deadline"] = str(ctx.get("filing_deadline", ""))
        return json.dumps({"filing_context": ctx, "mailing_kit": kit}, default=str)

    return json.dumps({"error": f"Unknown form type: {form_type}. Supported: form_8843"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GMAIL (local OAuth2 — user's own Google credentials)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _get_gmail_service():
    from compliance_os.gmail_client import get_service

    return get_service()


@mcp.tool()
def gmail_search(query: str, max_results: int = 10) -> str:
    """Search Gmail inbox.

    Args:
        query: Gmail search query (e.g., "from:irs.gov", "subject:Form 8843",
            "is:unread label:compliance", "has:attachment newer_than:7d").
        max_results: Maximum messages to return (default 10).
    """
    try:
        service = _get_gmail_service()
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        if not messages:
            return "No messages found."

        output = []
        for msg_stub in messages:
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg_stub["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )
            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            output.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId", ""),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        return json.dumps(output, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def gmail_read(message_id: str) -> str:
    """Read a Gmail message with full body and attachment metadata.

    Args:
        message_id: The message ID (from gmail_search results).
    """
    try:
        service = _get_gmail_service()
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        body = ""
        attachments = []
        payload = msg.get("payload", {})
        parts = payload.get("parts", [])

        if not parts:
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        else:
            for part in parts:
                mime = part.get("mimeType", "")
                filename = part.get("filename", "")
                if filename:
                    attachments.append({
                        "filename": filename,
                        "mime_type": mime,
                        "size": part.get("body", {}).get("size", 0),
                        "attachment_id": part.get("body", {}).get("attachmentId", ""),
                    })
                elif mime == "text/plain" and not body:
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="replace"
                        )

        return json.dumps(
            {
                "id": msg["id"],
                "thread_id": msg.get("threadId", ""),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body[:10_000],
                "attachments": attachments,
                "labels": msg.get("labelIds", []),
            },
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def gmail_draft(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    attachment_path: str = "",
) -> str:
    """Create a Gmail draft, optionally with a file attachment.

    Use this to draft compliance correspondence (filing confirmations,
    attorney emails, IRS cover letters). Pair with generate_form_8843
    to attach generated PDFs.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text).
        cc: CC recipients (comma-separated, optional).
        attachment_path: Path to file to attach (optional).
    """
    import email.encoders
    import email.mime.base
    import email.mime.multipart
    import email.mime.text

    try:
        service = _get_gmail_service()

        if attachment_path:
            path = Path(attachment_path)
            msg = email.mime.multipart.MIMEMultipart()
            msg.attach(email.mime.text.MIMEText(body, "plain"))

            if path.exists():
                with open(path, "rb") as f:
                    att = email.mime.base.MIMEBase("application", "octet-stream")
                    att.set_payload(f.read())
                email.encoders.encode_base64(att)
                att.add_header(
                    "Content-Disposition", f"attachment; filename={path.name}"
                )
                msg.attach(att)
            else:
                return json.dumps({"error": f"Attachment not found: {attachment_path}"})
        else:
            msg = email.mime.text.MIMEText(body, "plain")

        msg["to"] = to
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute()
        )

        return json.dumps({
            "status": "draft_created",
            "draft_id": draft["id"],
            "message_id": draft.get("message", {}).get("id", ""),
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def gmail_send(draft_id: str) -> str:
    """Send an existing Gmail draft.

    Args:
        draft_id: The draft ID (from gmail_draft result).
    """
    try:
        service = _get_gmail_service()
        result = (
            service.users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )
        return json.dumps({
            "status": "sent",
            "message_id": result.get("id", ""),
            "thread_id": result.get("threadId", ""),
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def gmail_reply(message_id: str, body: str) -> str:
    """Reply to a Gmail message (stays in thread).

    Args:
        message_id: The message ID to reply to.
        body: Reply body (plain text).
    """
    import email.mime.text

    try:
        service = _get_gmail_service()

        original = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["From", "Subject", "Message-ID"],
            )
            .execute()
        )
        headers = {
            h["name"]: h["value"]
            for h in original.get("payload", {}).get("headers", [])
        }

        subject = headers.get("Subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        msg = email.mime.text.MIMEText(body, "plain")
        msg["to"] = headers.get("From", "")
        msg["subject"] = subject
        msg["In-Reply-To"] = headers.get("Message-ID", "")
        msg["References"] = headers.get("Message-ID", "")

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        result = (
            service.users()
            .messages()
            .send(
                userId="me",
                body={"raw": raw, "threadId": original.get("threadId", "")},
            )
            .execute()
        )

        return json.dumps({
            "status": "sent",
            "message_id": result.get("id", ""),
            "thread_id": result.get("threadId", ""),
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def gmail_download_attachment(
    message_id: str,
    attachment_id: str,
    save_path: str,
) -> str:
    """Download a Gmail attachment to a local file.

    Use with gmail_read to find attachment_id values, then download
    for processing with parse_document and classify_document.

    Args:
        message_id: The message ID containing the attachment.
        attachment_id: The attachment ID (from gmail_read results).
        save_path: Local path to save the attachment.
    """
    try:
        service = _get_gmail_service()
        att = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        data = base64.urlsafe_b64decode(att["data"])
        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return json.dumps({
            "status": "saved",
            "path": str(out),
            "size_bytes": len(data),
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RAG QUERY (local vector store — requires indexed documents)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
def query_documents(
    question: str,
    doc_type: str = "",
    top_k: int = 5,
) -> str:
    """RAG query against locally indexed compliance documents.

    Retrieves relevant document chunks from the ChromaDB vector store
    and synthesizes an answer using LLM. Requires documents to have
    been indexed first (via the compliance-os indexer).

    Args:
        question: The question to answer from your documents.
        doc_type: Filter by document type (optional, e.g., "tax_form", "immigration").
        top_k: Number of document chunks to retrieve (default 5).
    """
    try:
        from compliance_os.query.engine import ComplianceQueryEngine

        engine = ComplianceQueryEngine()
        filters = None
        if doc_type:
            filters = engine.parse_filters([f"doc_type={doc_type}"])

        result = engine.query(question, top_k=top_k, filters=filters)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INDEXING (build/update ChromaDB vector store for RAG)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
def index_documents(
    directory: str = "uploads",
    force: bool = False,
) -> str:
    """Build or update the ChromaDB vector index for RAG queries.

    Scans uploaded documents, embeds them with OpenAI embeddings, and
    stores in ChromaDB. Incremental by default — only re-indexes
    new or changed files. Run this after uploading documents to
    enable the query_documents tool.

    Requires OPENAI_API_KEY for embeddings.

    Args:
        directory: Subdirectory to scan (default: "uploads").
            Other options: "data/uploads", "data/marketplace".
        force: If true, re-index everything from scratch.
    """
    try:
        from compliance_os.indexer.index import DocumentIndexer
        from compliance_os.web.models.database import DATA_DIR

        # Try project root first (real uploads), fall back to DATA_DIR
        project_root = Path(__file__).resolve().parents[1]
        if (project_root / directory).is_dir():
            data_dir = project_root
        elif (DATA_DIR / directory).is_dir():
            data_dir = DATA_DIR
        else:
            return json.dumps({
                "error": f"Directory '{directory}' not found in project root or data dir.",
                "searched": [str(project_root / directory), str(DATA_DIR / directory)],
            })

        indexer = DocumentIndexer(data_dir=data_dir)
        result = indexer.build_index(force=force, directories=[directory], verbose=False)
        return json.dumps({
            "status": "success",
            "data_dir": str(data_dir),
            "indexed": result.get("indexed", 0),
            "skipped": result.get("skipped", 0),
            "chunks": result.get("chunks", 0),
            "up_to_date": result.get("up_to_date", False),
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ─── Entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
