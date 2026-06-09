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
from mcp.types import TextContent, ToolAnnotations

from compliance_os.licensing import activation_block, feature_for_tool
from compliance_os.local_engine import (
    force_local_embeddings,
    is_local_mode,
    local_ask_grounding,
    local_cross_check,
    local_get_facts,
    local_record_extracted_facts,
    local_resolve_conflict,
    local_set_fact,
    local_share_data_room,
    local_upload_document,
)

class GatedMCP(FastMCP):
    """FastMCP that gates every tool dispatch on license activation when
    running as the standalone local extension. The hosted /mcp mount
    (where users authenticate per-request) is never gated, and direct
    function calls (tests, internal use) bypass this entirely."""

    def add_tool(
        self,
        fn,
        name=None,
        title=None,
        description=None,
        annotations=None,
        icons=None,
        meta=None,
        structured_output=None,
    ):
        """Register every tool as UNSTRUCTURED by default.

        Newer FastMCP (mcp >= 1.10) auto-generates an outputSchema
        ({"result": str}) for any ``-> str`` tool. Our tools return plain JSON
        text, and the license-gate block path returns bare TextContent with no
        structured content — a declared outputSchema with no structuredContent
        makes Claude Desktop reject EVERY tool call ("outputSchema defined but
        no structured output returned"). Forcing structured_output=False drops
        the schema so both the block path and the normal passthrough are
        client-valid. A future tool that genuinely returns structured data can
        still opt in with @mcp.tool(structured_output=True).
        """
        if structured_output is None:
            structured_output = False
        return super().add_tool(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            icons=icons,
            meta=meta,
            structured_output=structured_output,
        )

    async def call_tool(self, name, arguments):
        if not _is_hosted():
            block = activation_block(feature_for_tool(name))
            if block is not None:
                return [TextContent(type="text", text=json.dumps(block))]
        return await super().call_tool(name, arguments)


GUARDIAN_INSTRUCTIONS = (
    "You are Guardian, an immigration, tax, and business compliance assistant "
    "that runs LOCALLY on the user's own machine. Help the user understand "
    "their compliance status, process documents, generate forms, and manage "
    "compliance correspondence.\n\n"
    "IN SCOPE: F-1/J-1/H-1B/green-card-STAGE immigration (CPT, OPT, STEM OPT, "
    "H-1B including owner-beneficiary/founder, I-485/Advance Parole), "
    "foreign-owned US entities (Form 5472), startup equity tax (83(b)), FBAR, "
    "and nonresident tax (Form 8843, 1040-NR). OUT OF SCOPE: US citizens / "
    "naturalization, asylum/TPS/DACA, removal defense, and non-US-country "
    "matters -- for those say honestly 'that's outside what I'm built for; "
    "you'd want an immigration attorney or USCIS.gov' rather than guessing. "
    "Fail closed, never into the nearest box.\n\n"
    "COLD START (first interaction): you are a blank slate -- you cannot see "
    "the user's files, email, or situation until they tell you or point you at "
    "a document. Do NOT call read-state tools (guardian_status / "
    "guardian_deadlines / guardian_risks / guardian_documents) to 'discover' "
    "the user; they are empty at cold start. Instead: (1) reassure and answer "
    "the user's actual worry in ONE line before asking for anything; (2) state "
    "scope so out-of-scope users self-deselect; (3) get the one-line problem "
    "and invite any date or dollar figure (a deadline or amount often routes "
    "the case immediately).\n\n"
    "VALUE BEFORE EXTRACTION, TRIAGE BEFORE ROUTE: answer the fear first, then "
    "ask the single question that decides the path. Batch the 2-3 minimum "
    "facts in ONE message; never drip one question per turn.\n\n"
    "ROUTING FORKS (disambiguate only genuine collisions): OWNERSHIP splits "
    "normal CPT/H-1B from the founder/owner-beneficiary path ('someone else's "
    "company, or one you own?'). PRINCIPAL-VS-DEPENDENT splits a visa holder "
    "from an F-2/J-2/H-4 dependent -- dependents have different work/study "
    "rules, so never apply F-1 rules to an F-2. A green card is either "
    "I-485-pending-IN-THE-US (Advance Parole / AC21 logic applies) or consular "
    "processing abroad (it does NOT). INCOME is a THREE-WAY fork: wages / any "
    "scholarship-or-stipend / truly nothing -- treat any scholarship or stipend "
    "as a 1040-NR signal, and route a genuinely zero-income student to a "
    "standalone Form 8843, not a 1040-NR package.\n\n"
    "HONESTY ABOUT TOOLS (critical): NEVER narrate a tool call you did not make, "
    "fabricate tool output, or AUTHOR a tool RETURN you did not actually receive "
    "-- do not write an example/simulated return and then treat its contents as "
    "fact. NEVER state a specific identifier or field value (a SEVIS ID, DSO "
    "name, receipt/case number, draft ID, plan ID, date, or dollar amount) as if "
    "read from a document or returned by a tool unless it came from a REAL tool "
    "result; if you have not received a parse_document result yet, say 'once you "
    "point me at the file I'll read what's actually on it' instead of inventing "
    "values. The ONLY compliance checks that exist are run_compliance_check("
    "'h1b_doc_check' | 'fbar' | 'student_tax' | '83b_election'); "
    "get_filing_guidance supports only form_type='form_8843'. There is NO check "
    "for 5472, RCL/reinstatement, AOS/Advance-Parole, EB-1A, founder eligibility, "
    "or dependents -- for those, give your reasoned read and LABEL it as such "
    "('here's my read of the rules, not a number my tools compute'). For the "
    "checks that DO exist (run_compliance_check, get_filing_guidance): say 'I ran "
    "it' / 'it confirms' / 'the check returns X' ONLY if a real call to that exact "
    "check appears in THIS turn and you received its return; if you have NOT "
    "actually called it, do not narrate a completed result -- give the deadline or "
    "figure as your own reasoning and offer to run the check once you have the "
    "inputs. REAL return "
    "shapes (do not invent others): parse_document returns a bare first-page text "
    "string; classify_document returns {file, doc_type, confidence} with "
    "confidence 'high' or none (never a percentage); case_active_search returns a "
    "coverage / missing-required / missing-optional / unmatched-files gap report "
    "for a registered template (h1b, cpa, founder_h1b, form_5472, eb1a, "
    "dependent_status) -- it is a FILE SCANNER over a folder, NOT a legal or "
    "eligibility verdict; lawyer_search_plan only BUILDS dispatch prompts (status: "
    "planned, not yet run) and returns NO firm names -- do not claim a shortlist "
    "is 'running' or 'finishing' until you have dispatched the searches and called "
    "lawyer_search_ingest.\n\n"
    "DOCUMENTS FIRST where a document is the source of truth (forms, audits, "
    "extraction): ask the user to point you at the file with an OS-correct "
    "copy-path how-to (ask Mac or Windows first; on a Mac: right-click + hold "
    "Option then 'Copy as Pathname'; on Windows: Shift + right-click then 'Copy "
    "as path'; or drag it in), with read-it-aloud as a fallback. Then "
    "parse_document + classify_document + record_extracted_facts.\n\n"
    "DELIVER ARTIFACTS HONESTLY: generators like generate_form_8843 return a "
    "PDF as base64 -- to land it on the user's disk call save_artifact("
    "content_base64, output_path) and tell them the real path. Do NOT claim a "
    "file was 'saved to your folder' unless you actually called save_artifact. "
    "Gmail: Guardian ships no Gmail OAuth by default -- DRAFT correspondence "
    "and hand the user the recipient to send via their own mail connector; only "
    "offer to send if a Gmail config probe succeeds.\n\n"
    "RECOMMEND A HUMAN when stakes demand it: a consult-an-attorney hedge is "
    "MANDATORY for any travel or status determination delivered WITHOUT "
    "document verification -- Advance-Parole travel safety, possible status "
    "violations / reinstatement, and owner-beneficiary/founder restructuring "
    "especially. Offer lawyer_search_plan to find and vet counsel. Verify "
    "volatile external facts (H-1B cap windows, current addresses) with a live "
    "lookup and tell the user to confirm on the source the day they act -- but "
    "prefer a local check's own output (e.g. the 83(b) check emits the correct "
    "IRS service-center address) over a memorized one.\n\n"
    "SOURCE-OF-TRUTH FACTS: call get_user_facts before guessing a value; "
    "set_user_fact to lock a user-decided value, using ONE consistent track per "
    "workflow (e.g. f1_cpt, f1_status, foreign_owned_llc, fbar, h1b_petition, "
    "dependent_status) and resolve_fact_conflict when a value changes -- do not "
    "fragment a fact across tracks.\n\n"
    "GENERAL RULES: be calm and procedural, never alarmist; use plain English "
    "and briefly explain terms like SEVIS, DSO, FBAR; lead with the most urgent "
    "item; Guardian provides compliance risk detection, not legal advice; "
    "recommend an immigration attorney for critical issues and a CPA "
    "experienced with nonresident filings for tax issues. When the user "
    "expresses intent to save / file / record / add / ingest a document they "
    "provided, call upload_document. Engage proactively on immigration, tax, or "
    "corporate-compliance topics, but do not announce yourself or fire tools on "
    "an incidental mention. Also engage when the user explicitly says 'guardian' "
    "or 'guardian extension'."
)

mcp = GatedMCP("guardian", instructions=GUARDIAN_INSTRUCTIONS)

# ─── Configuration ───────────────────────────────────────────────

GUARDIAN_API_URL = os.environ.get("GUARDIAN_API_URL", "http://localhost:8000")
GUARDIAN_TOKEN = os.environ.get("GUARDIAN_TOKEN", "")


import threading

# Background prewarm state. The MCP server returns its tool list
# immediately; only the search-dependent tools (query_documents,
# index_documents) wait on _EMBED_READY before running. Everything else
# (status, deadlines, gmail, ...) is unaffected by the download.
_EMBED_READY = threading.Event()
_EMBED_ERROR: Exception | None = None
_EMBED_LOCK = threading.Lock()


def _prewarm_embedding_model_bg() -> None:
    """Resolve the embedding model in the background so the first local
    model download doesn't block server startup or non-search tools.

    Subsequent calls to resolve_embed_model() are near-instant because
    embedding runtimes cache weights on disk; we don't need to share a
    model handle.
    Skipped when GUARDIAN_DISABLE_PREWARM=1 (eval harness, tests).
    """
    global _EMBED_ERROR
    if os.environ.get("GUARDIAN_DISABLE_PREWARM") == "1":
        _EMBED_READY.set()
        return
    try:
        from compliance_os.query.engine import resolve_embed_model
        resolve_embed_model()
    except Exception as exc:  # pragma: no cover — best-effort prewarm
        with _EMBED_LOCK:
            _EMBED_ERROR = exc
        import sys
        print(f"[guardian] embedding prewarm failed: {exc}", file=sys.stderr)
    finally:
        _EMBED_READY.set()


def _embedding_error_message(exc: Exception) -> str:
    return (
        "Embeddings unavailable: "
        f"{type(exc).__name__}: {exc}. "
        "Guardian uses a local on-device embedding model by default — no API "
        "key needed. The first run downloads it (~100-130MB); if that failed, "
        "check your network and the server logs, then restart the extension."
    )


def _retry_embedding_model_after_error() -> tuple[str, str] | None:
    global _EMBED_ERROR
    with _EMBED_LOCK:
        if _EMBED_ERROR is None:
            return None
        try:
            from compliance_os.query.engine import resolve_embed_model
            resolve_embed_model()
        except Exception as exc:
            _EMBED_ERROR = exc
            return ("embeddings_unavailable", _embedding_error_message(exc))
        _EMBED_ERROR = None
    return None


def _ensure_embeddings_ready(wait_timeout: float = 60.0) -> tuple[str, str] | None:
    """Block until the prewarm finishes (or short-circuit if already done).

    Returns None on success, or (error_code, message) the caller should
    surface as the tool result. Search-dependent tools call this before
    touching the index so users get a clear "still warming up" message
    instead of a silent stall.
    """
    if _EMBED_READY.wait(timeout=wait_timeout):
        retry_result = _retry_embedding_model_after_error()
        if retry_result is not None:
            return retry_result
        return None
    return (
        "embeddings_warming",
        "Embeddings are still downloading in the background "
        f"(timed out after {wait_timeout:.0f}s). "
        "Try again in a moment — first-time setup needs to fetch the "
        "model weights once.",
    )


threading.Thread(
    target=_prewarm_embedding_model_bg,
    daemon=True,
    name="guardian-embed-prewarm",
).start()

if is_local_mode():
    force_local_embeddings()


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


_LOCAL_API_TOKEN: str | None = None


def _local_token() -> str:
    """Mint (and cache) a bearer token for the single local user so in-process
    API calls authenticate in the standalone local extension."""
    global _LOCAL_API_TOKEN
    if _LOCAL_API_TOKEN is None:
        from compliance_os.local_engine import get_local_user_id, get_session
        from compliance_os.web.models.auth import UserRow
        from compliance_os.web.services.auth_service import create_token

        db = next(get_session())
        try:
            uid = get_local_user_id(db)
            user = db.query(UserRow).filter(UserRow.id == uid).first()
            _LOCAL_API_TOKEN = create_token(user.id, user.email)
        finally:
            db.close()
    return _LOCAL_API_TOKEN


async def _api_get(path: str) -> dict | list:
    """GET from the Guardian API — async for both hosted and standalone.

    Hosted and local-extension modes both run the FastAPI app in-process via an
    ASGI transport (against the local SQLite in local mode); only a *remote*
    standalone setup (GUARDIAN_API_URL pointing at a real server) uses HTTP.
    """
    if _is_hosted() or is_local_mode():
        import httpx

        from compliance_os.web.app import app

        if _is_hosted():
            from compliance_os.mcp_hosted import get_mcp_client_token

            token = get_mcp_client_token()
        else:
            token = _local_token()
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = await client.get(path, headers=headers)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(f"Guardian API {resp.status_code}: {resp.text[:200]}") from exc
            return resp.json()

    # Remote standalone: blocking HTTP (OK for stdio — runs in its own process)
    req = request.Request(f"{GUARDIAN_API_URL}{path}", headers=_headers())
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except error.HTTPError as exc:
        raise RuntimeError(f"Guardian API {exc.code}: {exc.read().decode()[:200]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Cannot reach Guardian API at {GUARDIAN_API_URL}: {exc}") from exc


async def _api_post(path: str, payload: dict) -> dict:
    """POST to the Guardian API — async for both hosted and standalone.

    Hosted and local-extension modes run the FastAPI app in-process via ASGI;
    only a remote standalone setup uses HTTP.
    """
    if _is_hosted() or is_local_mode():
        import httpx

        from compliance_os.web.app import app

        if _is_hosted():
            from compliance_os.mcp_hosted import get_mcp_client_token

            token = get_mcp_client_token()
        else:
            token = _local_token()
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = await client.post(path, json=payload, headers=headers)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(f"Guardian API {resp.status_code}: {resp.text[:200]}") from exc
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Guardian status",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def guardian_status() -> str:
    """Get full compliance overview: findings, deadlines, key facts, document count.

    Returns the user's compliance status including critical issues,
    warnings, active subject chains, and upcoming deadlines.
    """
    try:
        timeline = await _api_get("/api/dashboard/timeline")
        stats = await _api_get("/api/dashboard/stats")
        chains = await _api_get("/api/dashboard/chains")
    except RuntimeError:
        return (
            "# Guardian Compliance Status\n\n"
            "_Guardian's local store isn't reachable yet — nothing has been set up "
            "on this machine, or the local app isn't running — so there's no status "
            "to show._\n\n"
            "That's normal on a fresh start. Tell me what you're trying to figure out "
            "(for example: an F-1 internship, a Form 5472 question, an 83(b) clock), or "
            "point me at a document, and I'll work from that directly."
        )

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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Upcoming deadlines",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Active risks",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Data-room documents",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Ask Guardian",
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
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
    if is_local_mode():
        return json.dumps(local_ask_grounding(question), default=str, indent=2)

    try:
        result = await _api_post("/api/chat", {"message": question, "history": []})
        return result.get("reply", "No response received.")
    except RuntimeError as exc:
        return f"Error: {exc}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DOCUMENT PROCESSING (local — no API token cost)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool(
    annotations=ToolAnnotations(
        title="Parse document",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Classify document",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get extraction schema",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def get_extraction_schema(doc_type: str) -> str:
    """List the fields to extract from a document of this type.

    Returns the SoT-tracked targets — each with the raw `source_field`
    to read, the canonical `fact_key` it maps to, a human `label`, and
    the value `shape` (string|number|date|object|list). After parsing a
    document, read these fields out of the text and submit them with
    record_extracted_facts. Runs locally with no token cost.

    Args:
        doc_type: The document type (e.g. "i20", "i797", "w2").
    """
    from compliance_os.facts.extraction_map import schema_for_doc_type

    return json.dumps(schema_for_doc_type(doc_type), indent=2)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Record extracted facts",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
def record_extracted_facts(doc_id: str, facts: list) -> str:
    """Submit the field values you read from a document into the SoT.

    Call this after parse_document + get_extraction_schema: read each
    schema field's value out of the document text, then submit them here.
    The engine writes them with provenance to the stored document and
    projects mapped fields into the user-facts source-of-truth, detecting
    conflicts with existing facts. Local mode only.

    Args:
        doc_id: The id returned by upload_document.
        facts: List of {"field_name": str, "value": str,
            "confidence": number (optional), "raw_text": str (optional)}.
    """
    if not is_local_mode():
        return json.dumps(
            {"error": "record_extracted_facts is only available in local mode."}
        )
    return json.dumps(
        local_record_extracted_facts(doc_id, facts), default=str, indent=2
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Save artifact to disk",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def save_artifact(content_base64: str, output_path: str, is_text: bool = False) -> str:
    """Write a generated artifact (PDF, form, letter) to a path on disk.

    Use this to land an artifact returned by another tool — e.g. the
    `pdf_base64` from generate_form_8843 — at a real, user-visible
    location. Runs locally; nothing leaves the machine. Parent
    directories are created if missing. Tell the user the returned
    `path` so they can find the file.

    Args:
        content_base64: The artifact bytes, base64-encoded. When
            is_text=True this is instead treated as raw UTF-8 text.
        output_path: Absolute or ~-relative path to write to.
        is_text: When True, write content_base64 as plain UTF-8 text
            rather than base64-decoding it.
    """
    if not output_path or not output_path.strip():
        return json.dumps({"status": "error", "error": "output_path is empty"})
    try:
        if is_text:
            data = content_base64.encode("utf-8")
        else:
            data = base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        return json.dumps({"status": "error", "error": f"Could not read artifact content: {exc}"})
    try:
        dest = Path(output_path).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return json.dumps({
            "status": "success",
            "path": str(dest.resolve()),
            "bytes_written": len(data),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})


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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Upload document to data room",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
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
    if is_local_mode():
        return json.dumps(local_upload_document(file_path, doc_type), default=str, indent=2)

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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Batch upload folder",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
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

    # Local mode: store each file on-device via the in-process upload path
    # (the hosted _upload_single_file POSTs to the Guardian API, which a local
    # extension has no account for). Lets a folder upload in one tool call.
    if is_local_mode():
        results = []
        for f in files:
            try:
                r = local_upload_document(str(f))
                if "error" in r:
                    results.append({"file": f.name, "status": "failed", "error": r["error"]})
                else:
                    results.append({"file": f.name, "status": "uploaded",
                                    "doc_id": r.get("doc_id"), "doc_type": r.get("doc_type")})
            except Exception as exc:
                results.append({"file": f.name, "status": "failed", "error": str(exc)})
        uploaded = sum(1 for r in results if r["status"] == "uploaded")
        failed = sum(1 for r in results if r["status"] == "failed")
        return json.dumps({
            "summary": f"{uploaded} uploaded, {failed} failed out of {len(files)} files",
            "results": results,
        }, indent=2)

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
#  USER FACTS — source of truth for distilled compliance facts
#  (see docs/architecture/context-management.md). Always call
#  get_user_facts before guessing a value.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get user facts (SoT)",
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=False,
    ),
)
async def get_user_facts(
    category: str = "",
    track: str = "",
) -> str:
    """Return the user's active SoT facts (current employer, visa end
    date, EIN, etc.).

    Facts are the distilled, authoritative version of what's in the
    user's documents — derived by extraction and surviving document
    supersession. Always check this first before asking the user or
    inferring from a single document.

    Args:
        category: Optional category filter (immigration | tax |
            corporate | personal | employment | education).
        track: Optional track filter (young_professional | student |
            entrepreneur). Returns shared facts in addition to track-
            specific ones.
    """
    if is_local_mode():
        return json.dumps(local_get_facts(category, track), default=str, indent=2)
    params = []
    if category:
        params.append(f"category={category}")
    if track:
        params.append(f"track={track}")
    path = "/api/facts" + (("?" + "&".join(params)) if params else "")
    try:
        result = await _api_get(path)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Set / lock a user fact",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
async def set_user_fact(
    fact_key: str,
    value: str,
    notes: str = "",
    label: str = "",
) -> str:
    """Record a user-locked SoT fact.

    Call this when the user explicitly states a value as decided —
    "my salary is $135K now", "use this address going forward",
    "the LCA case number is I-200-26139-927332". Don't lock
    implicitly-mentioned values.

    The previous value (if any) is preserved as a superseded row;
    history is queryable via /api/facts/<key>/history.

    Args:
        fact_key: Canonical key (see vocabulary in
            compliance_os.facts.vocabulary) or "custom:<slug>".
        value: The new value. Pass scalars as strings; the backend
            wraps in the {"v": ...} JSON envelope.
        notes: Optional long-form qualifiers (e.g., "Decision-locked
            2026-05-22 after Kuck Baxter consultation").
        label: Override the human label (only needed for custom keys
            or when correcting a default).
    """
    if is_local_mode():
        return json.dumps(
            local_set_fact(fact_key, value, notes=notes, label=label),
            default=str, indent=2,
        )
    payload: dict = {"fact_key": fact_key, "value": value}
    if notes:
        payload["notes"] = notes
    if label:
        payload["label"] = label
    try:
        result = await _api_post("/api/facts", payload)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Resolve a fact conflict",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
async def resolve_fact_conflict(
    fact_id: str,
    choice: str,
    user_value: str = "",
) -> str:
    """Apply a user decision to a fact's detected_conflicts list.

    Use this when get_user_facts returned a fact with non-empty
    detected_conflicts and the user has told you how to resolve.

    Args:
        fact_id: The fact row UUID (from get_user_facts).
        choice: One of "use_new" | "keep_current" | "user_value".
        user_value: Required when choice == "user_value".
    """
    if is_local_mode():
        return json.dumps(
            local_resolve_conflict(fact_id, choice, user_value=user_value),
            default=str, indent=2,
        )
    payload: dict = {"choice": choice}
    if user_value:
        payload["user_value"] = user_value
    try:
        result = await _api_post(f"/api/facts/{fact_id}/resolve", payload)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FORM FILING (local — uses existing Python services)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool(
    annotations=ToolAnnotations(
        title="Generate Form 8843",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Run compliance check",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get filing guidance",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
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


def _gmail_guard() -> str | None:
    """Return a redirect message (JSON) if Guardian's own Gmail isn't
    configured, else None. In the local-first default the user's assistant
    Gmail connector (or a Gmail MCP plugin) is the intended path — Guardian
    ships no Gmail OAuth of its own."""
    from compliance_os.gmail_client import is_gmail_configured

    if is_gmail_configured():
        return None
    return json.dumps(
        {
            "error": "gmail_not_configured",
            "message": (
                "Guardian isn't managing Gmail here. Use your assistant's own "
                "Gmail connector (or a Gmail MCP plugin) to read or draft email, "
                "then save any attachment and call upload_document to bring it "
                "into your data room. To use Guardian's built-in Gmail "
                "integration instead, add OAuth credentials at "
                "~/.config/guardian/gmail_credentials.json."
            ),
        }
    )


def _get_gmail_service():
    from compliance_os.gmail_client import get_service

    return get_service()


@mcp.tool(
    annotations=ToolAnnotations(
        title="Search Gmail",
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
def gmail_search(query: str, max_results: int = 10) -> str:
    """Search Gmail inbox.

    Args:
        query: Gmail search query (e.g., "from:irs.gov", "subject:Form 8843",
            "is:unread label:compliance", "has:attachment newer_than:7d").
        max_results: Maximum messages to return (default 10).
    """
    if (msg := _gmail_guard()) is not None:
        return msg
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read Gmail message",
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
def gmail_read(message_id: str) -> str:
    """Read a Gmail message with full body and attachment metadata.

    Args:
        message_id: The message ID (from gmail_search results).
    """
    if (msg := _gmail_guard()) is not None:
        return msg
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Draft Gmail message",
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
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
    if (msg := _gmail_guard()) is not None:
        return msg
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Send Gmail draft",
        readOnlyHint=False,
        destructiveHint=True,
        openWorldHint=True,
    ),
)
def gmail_send(draft_id: str) -> str:
    """Send an existing Gmail draft.

    Args:
        draft_id: The draft ID (from gmail_draft result).
    """
    if (msg := _gmail_guard()) is not None:
        return msg
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Reply to Gmail thread",
        readOnlyHint=False,
        destructiveHint=True,
        openWorldHint=True,
    ),
)
def gmail_reply(message_id: str, body: str) -> str:
    """Reply to a Gmail message (stays in thread).

    Args:
        message_id: The message ID to reply to.
        body: Reply body (plain text).
    """
    if (msg := _gmail_guard()) is not None:
        return msg
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Download Gmail attachment",
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
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
    if (msg := _gmail_guard()) is not None:
        return msg
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Query documents (RAG)",
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
def query_documents(
    question: str,
    doc_type: str = "",
    category: str = "",
    top_k: int = 5,
    smart: bool = True,
) -> str:
    """Search locally indexed compliance documents.

    By default uses smart_search — Tier 1 filtered RAG (doc_type / category
    metadata pre-filter) auto-escalates to Tier 2 open RAG with recency
    rerank when Tier 1 is thin. Pass smart=False to get the legacy
    LLM-synthesized RAG answer instead.

    Args:
        question: The question to answer from your documents.
        doc_type: Filter by document type (immigration, tax, deadline, ...).
        category: Filter by top-level corpus category (immigration, tax, ...).
        top_k: Number of chunks/docs to return (default 5).
        smart: If True (default), return ranked chunks. If False, run the
            legacy single-tier RAG + LLM synthesis.
    """
    warmup_result = _ensure_embeddings_ready(wait_timeout=60.0)
    if warmup_result:
        error_code, warmup_msg = warmup_result
        return json.dumps({"error": error_code, "message": warmup_msg})
    try:
        from compliance_os.query.engine import ComplianceQueryEngine

        engine = ComplianceQueryEngine()

        if smart:
            res = engine.smart_search(
                query=question,
                doc_type=doc_type or None,
                category=category or None,
                top_k=top_k,
                prefer_recent=True,
            )
            chunks = res["results"]
            sources = []
            seen = set()
            for c in chunks:
                fp = c["metadata"].get("file_path", "unknown")
                if fp in seen:
                    continue
                seen.add(fp)
                sources.append({
                    "file_path": fp,
                    "file_name": c["metadata"].get("file_name"),
                    "doc_type": c["metadata"].get("doc_type"),
                    "category": c["metadata"].get("category"),
                    "score": c.get("final_score") or c.get("score"),
                    "snippet": (c.get("text") or "")[:280],
                    "tier2_match": c.get("tier2_match", False),
                })
            return json.dumps(
                {
                    "tier_used": res["tier_used"],
                    "tier1_count": res["tier1_count"],
                    "sources": sources,
                    "note": res["note"],
                    "latency_ms": res["latency_ms"],
                },
                default=str,
                indent=2,
            )

        filters = None
        if doc_type:
            filters = engine.parse_filters([f"doc_type={doc_type}"])
        result = engine.query(question, top_k=top_k, filters=filters)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        msg = str(exc)
        if "does not exist" in msg or "Collection" in msg:
            return json.dumps({
                "error": "no_index",
                "message": (
                    "No documents indexed yet. Upload documents in the "
                    "Guardian dashboard (or via batch_upload), then run "
                    "index_documents to enable RAG search."
                ),
            })
        return json.dumps({"error": msg})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INDEXING (build/update ChromaDB vector store for RAG)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool(
    annotations=ToolAnnotations(
        title="Index documents for RAG",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def index_documents(
    directory: str = "uploads",
    force: bool = False,
) -> str:
    """Build or update the ChromaDB vector index for RAG queries.

    Scans uploaded documents, embeds them (OpenAI if a key is configured,
    otherwise a local model), and stores in ChromaDB. Incremental by
    default — only re-indexes new or changed files. Run this after
    uploading documents to enable the query_documents tool.

    Args:
        directory: Subdirectory to scan (default: "uploads").
            Other options: "data/uploads", "data/marketplace".
        force: If true, re-index everything from scratch.
    """
    warmup_result = _ensure_embeddings_ready(wait_timeout=120.0)
    if warmup_result:
        error_code, warmup_msg = warmup_result
        return json.dumps({"error": error_code, "message": warmup_msg})
    try:
        from compliance_os.indexer.index import DocumentIndexer

        # Local mode: index the on-device data room (<uploads_root>/<check_id>/),
        # the same place local_upload_document writes to. The project-root /
        # DATA_DIR heuristic below is for the hosted server only.
        if is_local_mode():
            from compliance_os.local_engine import local_uploads_root

            data_dir = local_uploads_root()
            indexer = DocumentIndexer(data_dir=data_dir)
            result = indexer.build_index(force=force, directories=None, verbose=False)
            return json.dumps({
                "status": "success",
                "data_dir": str(data_dir),
                "indexed": result.get("indexed", 0),
                "skipped": result.get("skipped", 0),
                "chunks": result.get("chunks", 0),
                "up_to_date": result.get("up_to_date", False),
            })

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ACTIVE TARGET SEARCH (template-driven document scan)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool(
    annotations=ToolAnnotations(
        title="Scan folder against case template",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def case_active_search(
    template: str,
    folder: str,
    verbose: bool = False,
    as_json: bool = False,
) -> str:
    """Scan a local folder against any registered case template.

    Generic active-target search: walks the folder, scores each file
    against the template's slots, and emits a gap report with coverage
    by section, missing required/optional slots, lineage issues,
    misplaced files, and unmatched extras.

    This is a FILE SCANNER over a folder: it reports document
    coverage and gaps for the chosen template. It does NOT render an
    eligibility or legal verdict.

    Args:
        template: Template key — one of: "h1b" (H-1B petition package),
            "cpa" (CPA tax engagement, nonresident + disregarded
            entity), "founder_h1b" (founder / owner-beneficiary H-1B:
            E-Verify, controlling interest, governance), "form_5472"
            (foreign-owned single-member LLC), "eb1a" (EB-1A
            extraordinary-ability evidence), or "dependent_status"
            (F-2 / J-2 / H-4). All templates are generic and PII-free.
        folder: Absolute path to the folder to scan.
        verbose: Include match reasons and alternate matches per slot.
        as_json: Return structured JSON instead of formatted text.
    """
    try:
        from compliance_os.case_templates import (
            format_report,
            match_folder,
            resolve_template,
        )

        tpl = resolve_template(template)
        report = match_folder(folder, tpl)

        if as_json:
            return json.dumps({
                "template_id": report.template_id,
                "template_name": tpl.name,
                "folder": report.folder,
                "files_scanned": report.files_scanned,
                "coverage": report.coverage,
                "matched": {
                    sid: [{"file": m.file_path, "score": m.score, "reasons": m.reasons} for m in ms]
                    for sid, ms in report.matched.items()
                },
                "missing_required": [
                    {"id": s.id, "title": s.title, "section": s.section} for s in report.missing_required
                ],
                "missing_optional": [
                    {"id": s.id, "title": s.title, "section": s.section} for s in report.missing_optional
                ],
                "unmatched_files": report.unmatched_files,
                "misplaced": [
                    {"file": f, "current_section": c, "expected_section": e} for f, c, e in report.misplaced
                ],
                "lineage_issues": report.lineage_issues,
            }, indent=2)

        return format_report(report, tpl, verbose=verbose)
    except (KeyError, NotADirectoryError) as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="H-1B petition gap report",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def h1b_active_search(folder: str, verbose: bool = False, as_json: bool = False) -> str:
    """Shorthand for case_active_search(template='h1b', ...). See that tool."""
    return case_active_search("h1b", folder, verbose=verbose, as_json=as_json)


@mcp.tool(
    annotations=ToolAnnotations(
        title="CPA tax-engagement gap report",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def cpa_active_search(folder: str, verbose: bool = False, as_json: bool = False) -> str:
    """Shorthand for case_active_search(template='cpa', ...). See that tool."""
    return case_active_search("cpa", folder, verbose=verbose, as_json=as_json)


# ─── Professional search (attorneys / CPAs / bankers) ────────────


@mcp.tool(
    annotations=ToolAnnotations(
        title="Plan a parallel lawyer / professional search",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def lawyer_search_plan(
    case_brief: str,
    purpose: str,
    vertical: str = "immigration_attorney",
    personas: list[str] | None = None,
    output_dir: str | None = None,
) -> str:
    """Build dispatch prompts for parallel sub-agent professional search.

    Returns one prompt per search persona (elite boutique, startup-
    focused, litigation-focused, ...). The caller is expected to
    dispatch each prompt to a sub-agent (e.g. via the Task tool) in
    parallel; each sub-agent writes a YAML to its assigned output
    path. When all sub-agents finish, call `lawyer_search_ingest`
    with the list of output paths to merge results into the diligence
    SQLite DB at `data/diligence.db`.

    Args:
        case_brief: 1-3 paragraph description of the case the user is
            hiring for (facts, regulatory wrinkles, constraints). Used
            by every persona as context.
        purpose: Short engagement label, e.g. "H-1B petition — 2026 cap".
            Becomes engagements.purpose.
        vertical: Persona directory to use (default
            "immigration_attorney"). Available directories are under
            `data/professional_search/personas/<vertical>/`.
        personas: Optional subset of persona ids. If omitted, every
            persona in the vertical is used.
        output_dir: Optional override for where sub-agent YAMLs are
            written (default: `output/professional_search/<YYYY-MM-DD>/`).

    Returns:
        JSON with per-persona prompts, output paths, and a hint for
        ingest after dispatch completes.
    """
    try:
        from compliance_os.professional_search.personas import build_search_plan
        from pathlib import Path as _P

        plan = build_search_plan(
            case_brief=case_brief,
            purpose=purpose,
            vertical=vertical,
            personas=personas,
            output_dir=_P(output_dir) if output_dir else None,
        )
        plan["privacy_note"] = (
            "Claude will search the web using generic persona queries; your "
            "personal facts are not included."
        )
        return json.dumps(plan, indent=2)
    except (FileNotFoundError, ValueError) as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Ingest search-agent YAML into diligence DB",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def lawyer_search_ingest(yaml_paths: list[str]) -> str:
    """Merge one or more search-agent YAMLs into the diligence DB.

    Each file must match the schema described by `lawyer_search_plan`'s
    output (firms with name, contact, credentials, fees, confidence).
    Upserts are by vendor name (case-insensitive + first-word fuzzy),
    so re-ingesting the same YAML is safe.

    Args:
        yaml_paths: Absolute paths to one or more YAML files produced
            by the search sub-agents.

    Returns:
        JSON summary with new-vendor and updated counts.
    """
    try:
        from compliance_os.professional_search.ingest import ingest_docs

        summary = ingest_docs(yaml_paths)
        return json.dumps(summary, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Attorney / vendor tier comparison",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def lawyer_tier_report(
    vendor_type: str = "attorney",
    as_json: bool = False,
) -> str:
    """Ranked tier report from the diligence DB, scored high-to-low.

    Queries `v_attorney_comparison` (when vendor_type='attorney') or
    `v_vendor_comparison` (any other vendor type). Rows are sorted by
    engagement.score descending; open-risk count included inline.

    Args:
        vendor_type: One of attorney | bank | cpa | caa | notary |
            insurance | registered_agent | ... (the vendor_type enum).
        as_json: Return JSON instead of a formatted text table.
    """
    try:
        from compliance_os.professional_search.db import (
            attorney_comparison,
            connect,
            init_schema,
            vendor_comparison,
        )

        init_schema()
        with connect() as conn:
            rows = (
                attorney_comparison(conn)
                if vendor_type == "attorney"
                else vendor_comparison(conn, vendor_type=vendor_type)
            )

        if as_json:
            return json.dumps(rows, indent=2, default=str)

        if not rows:
            return f"(no {vendor_type} engagements in diligence DB yet)"

        lines = [
            f"{vendor_type.upper()} TIER REPORT  ({len(rows)} engagements)",
            "=" * 72,
        ]
        for r in rows:
            name = r.get("firm") or r.get("vendor") or "?"
            score = r.get("score")
            prio = r.get("priority") or "-"
            status = r.get("status") or "-"
            low = r.get("lowest_quote")
            high = r.get("highest_quote")
            fee = (
                f"${low:,.0f}-${high:,.0f}"
                if low and high and low != high
                else f"${low:,.0f}"
                if low
                else "-"
            )
            open_risks = r.get("open_risks") or 0
            lines.append(
                f"  [{score if score is not None else '--':>3}] "
                f"{name[:40]:40s}  {prio:>8s}  {status:>13s}  "
                f"fee={fee:<20s}  risks={open_risks}"
            )
            if r.get("next_action"):
                lines.append(
                    f"        next: {r['next_action']}"
                    + (f" (by {r['next_action_date']})" if r.get("next_action_date") else "")
                )
        return "\n".join(lines)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Vendor directory (phone book)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def vendor_directory(vendor_type: str | None = None, as_json: bool = False) -> str:
    """List every vendor with primary contact, email, phone.

    Args:
        vendor_type: Optional filter by vendor_type.
        as_json: Return JSON instead of a formatted text list.
    """
    try:
        from compliance_os.professional_search.db import (
            connect,
            init_schema,
            vendor_directory as vd,
        )

        init_schema()
        with connect() as conn:
            rows = vd(conn, vendor_type=vendor_type)

        if as_json:
            return json.dumps(rows, indent=2, default=str)
        if not rows:
            return "(no vendors in diligence DB yet)"

        lines = [f"VENDOR DIRECTORY ({len(rows)})", "=" * 72]
        current_type = None
        for r in rows:
            if r["vendor_type"] != current_type:
                current_type = r["vendor_type"]
                lines.append(f"\n## {current_type}")
            loc = r.get("location") or "-"
            contact = r.get("primary_contact") or "(no contact)"
            email = r.get("primary_email") or "-"
            phone = r.get("primary_phone") or "-"
            lines.append(f"  {r['name']}  [{loc}]")
            lines.append(f"      {contact}  |  {email}  |  {phone}")
        return "\n".join(lines)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Vendor dossier (contacts, engagements, quotes, risks)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def vendor_detail(name: str) -> str:
    """Full dossier for one vendor (fuzzy name match).

    Returns every contact, engagement, quote, evaluation, risk, and
    recent interaction for the first vendor whose name contains the
    given fragment. If multiple match, returns the candidate list.

    Args:
        name: Substring of the vendor name (case-sensitive LIKE match).
    """
    try:
        from compliance_os.professional_search.db import (
            connect,
            init_schema,
            vendor_detail as vdet,
        )

        init_schema()
        with connect() as conn:
            result = vdet(conn, name)
        if result is None:
            return json.dumps({"error": f"No vendor matching '{name}'"})
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Cross-check filings",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def cross_check_filings(chain: str = "") -> str:
    """Cross-check the user's uploaded filings for mismatches, missing forms,
    and deadline risks — entirely on-device. With no argument, auto-detects and
    checks every document chain your data room implies (STEM OPT, H-1B, tax,
    corporate); pass a chain id to scope to one. Returns a structured risk
    report to summarize for the user. Runs no model and sends no data off-device.

    Args:
        chain: Optional chain id — "stem_opt", "h1b", "tax", or "corporate".
    """
    if not is_local_mode():
        return json.dumps({"error": "cross_check_filings is only available in local mode."})
    return json.dumps(local_cross_check(chain), default=str, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Share data room (cloud)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
def share_data_room(purpose: str, confirm: bool = False, remember: str = "once") -> str:
    """Upload your local facts source-of-truth + documents to Guardian's cloud
    for a named purpose (e.g. a lawyer-matching service) — ONLY with your explicit
    approval. With no prior 'always' grant and confirm=false, this returns a consent
    request describing exactly what will be sent and where; show it to the user and,
    if they approve, call again with confirm=true and remember='once'|'session'|'always'.
    Nothing leaves the device until confirm=true (or a prior 'always' grant exists).

    Args:
        purpose: The service/purpose the data is shared for (e.g. "lawyer-matching").
        confirm: Set true only after the user has approved this upload.
        remember: How long to remember approval — "once", "session", or "always".
    """
    if not is_local_mode():
        return json.dumps({"error": "share_data_room is only available in local mode."})
    return json.dumps(local_share_data_room(purpose, confirm=confirm, remember=remember), default=str, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(title="List egress consents", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
)
def list_egress_consents() -> str:
    """List the purposes you've approved for sharing your data room to Guardian cloud."""
    if not is_local_mode():
        return json.dumps({"error": "list_egress_consents is only available in local mode."})
    from compliance_os import consent
    return json.dumps({"consents": consent.list_consents()}, default=str, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(title="Revoke egress consent", readOnlyHint=False, destructiveHint=False, idempotentHint=True),
)
def revoke_egress_consent(purpose: str) -> str:
    """Revoke a previously granted data-room sharing consent for a purpose.

    Args:
        purpose: The purpose to revoke (e.g. "lawyer-matching").
    """
    if not is_local_mode():
        return json.dumps({"error": "revoke_egress_consent is only available in local mode."})
    from compliance_os import consent
    consent.revoke_consent(purpose)
    return json.dumps({"revoked": purpose}, default=str, indent=2)


# ─── Entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
