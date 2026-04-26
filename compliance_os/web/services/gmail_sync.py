"""On-demand Gmail sync — pulls recent threads and matches to engagements.

Called from `POST /api/me/gmail/sync` when the user opens a case page or
clicks "Sync now". No background scheduler; sync runs in the request
handler. Bounded by user activity, no per-user cron.

Matching strategy: for each recent message in the user's mailbox where
any participant email matches an engagement's `firm_emails`, upsert an
`EmailThreadRow` keyed on (user_id, gmail_thread_id). The thread is
linked to the *first* matching engagement; same-firm-across-cases would
need a richer model, deferred until use cases prove it out.

Uses raw httpx — no google-api-python-client dep. Gmail's REST API is
small enough that the SDK isn't worth the install footprint.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from compliance_os.settings import settings
from compliance_os.web.models.tables import (
    CaseRow,
    EmailThreadRow,
    GoogleOAuthTokenRow,
    LawyerEngagementRow,
)
from compliance_os.web.services.token_crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Cap on how many messages per sync. The Gmail `q` query targets
# specific addresses, so even with many engagements this stays small.
MAX_MESSAGES_PER_SYNC = 100

# Minimum interval between syncs for a single user (debounces page-load
# triggers + double-clicks on Sync now). Override by passing force=True.
DEBOUNCE = timedelta(minutes=2)

EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")

# Public email-provider domains. We never use these for domain-fallback
# matching — a stored `lawyer@gmail.com` should match exactly, not match
# every other gmail.com sender in the user's inbox.
PUBLIC_EMAIL_DOMAINS: frozenset[str] = frozenset({
    "gmail.com", "googlemail.com",
    "yahoo.com", "yahoo.co.uk", "yahoo.co.jp",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com",
    "aol.com",
    "proton.me", "protonmail.com",
    "qq.com", "163.com", "126.com", "sina.com",
})


class GmailSyncError(RuntimeError):
    """Sync failed in a way the caller should surface to the user."""


def _ensure_fresh_access_token(db: Session, token_row: GoogleOAuthTokenRow) -> str:
    """Return a non-expired access token, refreshing via refresh_token if needed."""
    now = datetime.utcnow()
    if token_row.expires_at and token_row.expires_at > now + timedelta(seconds=60):
        access = decrypt_token(token_row.access_token_encrypted)
        if access:
            return access
        # Decryption failed — fall through to refresh, which will reset the row.

    refresh = decrypt_token(token_row.refresh_token_encrypted)
    if not refresh:
        raise GmailSyncError("Stored Gmail tokens cannot be decrypted — reconnect Gmail.")

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise GmailSyncError("Google OAuth not configured on server.")

    try:
        resp = httpx.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=15.0,
        )
    except Exception as exc:
        raise GmailSyncError(f"Token refresh network error: {exc}") from exc

    if resp.status_code != 200:
        # Refresh-token failure is usually unrecoverable (user revoked at
        # Google, or token aged out). Mark revoked so the UI prompts re-auth.
        token_row.revoked_at = now
        token_row.last_sync_error = f"refresh_failed: HTTP {resp.status_code}"
        db.commit()
        raise GmailSyncError(
            "Gmail access has been revoked at Google. Reconnect to resume sync."
        )

    data = resp.json()
    new_access = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))

    token_row.access_token_encrypted = encrypt_token(new_access)
    token_row.expires_at = now + timedelta(seconds=expires_in)
    db.commit()
    return new_access


def _gmail_get(access_token: str, path: str, params: dict[str, Any] | None = None) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = httpx.get(f"{GMAIL_API}{path}", headers=headers, params=params, timeout=15.0)
    if resp.status_code == 401:
        raise GmailSyncError("Gmail returned 401 — token rejected.")
    if resp.status_code != 200:
        raise GmailSyncError(f"Gmail API {path}: HTTP {resp.status_code} {resp.text[:200]}")
    return resp.json()


def _extract_emails(value: str) -> list[str]:
    """Pull email addresses out of a `Name <addr@host>, addr2@host` style header."""
    return [m.lower() for m in EMAIL_RE.findall(value or "")]


def _build_query(addrs: list[str], domains: list[str] | None = None) -> str:
    """Build a Gmail search query matching ANY of these addresses or domains.

    Exact addresses cap at 50, domains cap at 20 (Gmail query length limit).

    Domain match (`from:@firm.com OR to:@firm.com`) is critical because the
    address stored on an engagement is usually one specific attorney —
    actual correspondence often involves a different person at the same
    firm (intake@, partner@, secretary@). Without the domain query the
    sync would silently miss every thread the user actually has.

    The caller should pass only non-public, non-user-own domains in
    `domains` — sending `@gmail.com` would scoop the user's entire inbox.
    """
    parts: list[str] = []
    for a in (addrs or [])[:50]:
        parts.append(f"from:{a}")
        parts.append(f"to:{a}")
    for d in (domains or [])[:20]:
        parts.append(f"from:@{d}")
        parts.append(f"to:@{d}")
    if not parts:
        return ""
    return "(" + " OR ".join(parts) + ")"


def sync_user_gmail(
    db: Session, user_id: str, *, force: bool = False
) -> dict[str, Any]:
    """Sync this user's Gmail and match new threads to their engagements.

    Returns a dict the API can serialize: counts + last_synced_at. Raises
    `GmailSyncError` on unrecoverable failures (no token, revoked, etc.)
    so the caller surfaces a clear error to the UI.

    `force=True` bypasses the per-user debounce — used by the explicit
    "Sync now" button. Page-load triggers should leave it False.
    """
    token_row = (
        db.query(GoogleOAuthTokenRow)
        .filter(GoogleOAuthTokenRow.user_id == user_id)
        .first()
    )
    if token_row is None or token_row.revoked_at is not None:
        raise GmailSyncError("Gmail not connected.")

    now = datetime.utcnow()
    if (
        not force
        and token_row.last_synced_at is not None
        and (now - token_row.last_synced_at) < DEBOUNCE
    ):
        return {
            "skipped": True,
            "reason": "debounced",
            "last_synced_at": token_row.last_synced_at.isoformat(),
        }

    access_token = _ensure_fresh_access_token(db, token_row)

    profile = _gmail_get(access_token, "/users/me/profile")
    user_email = (profile.get("emailAddress") or "").lower()

    # Scope to engagements on cases owned by THIS user. Excludes cases
    # with NULL user_id (anonymous/legacy) — safer default: never let
    # one user's Gmail be matched against another user's anonymous case.
    # Anonymous cases get claimed on first authenticated access via
    # case_access.get_case_for_user, so this only filters out truly
    # orphaned cases.
    engagements = (
        db.query(LawyerEngagementRow)
        .join(CaseRow, LawyerEngagementRow.case_id == CaseRow.id)
        .filter(CaseRow.user_id == user_id)
        .all()
    )

    # Two lookups: exact-email (high precision) and domain (fallback).
    # A firm whose intake@firm.com replies but whose stored contact is
    # partner@firm.com still matches via the domain map. The user's own
    # email domain is excluded — we don't want every internal thread to
    # be matched against an engagement that happens to share our domain.
    email_to_engagement: dict[str, str] = {}
    domain_to_engagement: dict[str, str] = {}
    user_domain = user_email.split("@", 1)[-1] if "@" in user_email else ""
    for e in engagements:
        for em in (e.firm_emails or []):
            if not isinstance(em, str) or not em.strip():
                continue
            addr = em.lower().strip()
            email_to_engagement[addr] = e.id
            domain = addr.split("@", 1)[-1] if "@" in addr else ""
            if (
                domain
                and domain != user_domain
                and domain not in PUBLIC_EMAIL_DOMAINS
            ):
                # First engagement to claim a domain wins. Multiple
                # engagements at the same firm domain is rare; if it
                # happens, exact-email match (preferred above) handles it.
                domain_to_engagement.setdefault(domain, e.id)

    if not email_to_engagement and not domain_to_engagement:
        token_row.last_synced_at = now
        token_row.last_sync_error = None
        db.commit()
        return {
            "messages_scanned": 0,
            "threads_matched": 0,
            "threads_new": 0,
            "last_synced_at": now.isoformat(),
        }

    # Query Gmail by exact addresses AND by firm domain. Domain queries
    # are essential — the engagement's stored address is usually one
    # specific attorney (e.g. partner@), but actual correspondence often
    # comes from intake@, secretary@, or another colleague at the same
    # firm. Without `from:@firm.com` we'd silently return nothing for
    # users who exchange email with a different person than expected.
    # Public domains (gmail.com etc.) and the user's own domain are
    # already excluded from `domain_to_engagement` above.
    query = _build_query(
        list(email_to_engagement.keys()),
        list(domain_to_engagement.keys()),
    )
    try:
        list_resp = _gmail_get(
            access_token,
            "/users/me/messages",
            params={"q": query, "maxResults": MAX_MESSAGES_PER_SYNC},
        )
    except GmailSyncError as exc:
        token_row.last_sync_error = str(exc)[:500]
        db.commit()
        raise

    messages_scanned = 0
    threads_matched = 0
    threads_new = 0
    seen_threads: set[str] = set()

    for msg_ref in list_resp.get("messages", []) or []:
        thread_id = msg_ref.get("threadId")
        if not thread_id or thread_id in seen_threads:
            continue
        seen_threads.add(thread_id)

        try:
            thread = _gmail_get(
                access_token,
                f"/users/me/threads/{thread_id}",
                params={"format": "metadata"},
            )
        except GmailSyncError:
            continue

        thread_messages = thread.get("messages") or []
        if not thread_messages:
            continue

        # Collect all participants across the thread; first match wins.
        participants: set[str] = set()
        for m in thread_messages:
            for header in (m.get("payload") or {}).get("headers") or []:
                if header.get("name") in ("From", "To", "Cc"):
                    for addr in _extract_emails(header.get("value", "")):
                        participants.add(addr)

        matched_engagement_id: str | None = None
        # Pass 1: exact email match (high confidence).
        for p in participants:
            if p in email_to_engagement:
                matched_engagement_id = email_to_engagement[p]
                break
        # Pass 2: domain fallback (catches intake@/info@/secretary@ that
        # weren't on the engagement's stored email list). Skip the user's
        # own domain so internal threads don't accidentally match.
        if matched_engagement_id is None:
            for p in participants:
                domain = p.split("@", 1)[-1] if "@" in p else ""
                if not domain or domain == user_domain:
                    continue
                if domain in domain_to_engagement:
                    matched_engagement_id = domain_to_engagement[domain]
                    break

        messages_scanned += 1
        if not matched_engagement_id:
            continue
        threads_matched += 1

        # Last message metadata for the preview row.
        last = thread_messages[-1]
        last_headers = {
            h["name"]: h["value"] for h in (last.get("payload") or {}).get("headers") or []
        }
        last_from_raw = last_headers.get("From", "")
        last_subject = last_headers.get("Subject", "")[:500]
        try:
            last_date = datetime.utcfromtimestamp(int(last.get("internalDate", 0)) / 1000)
        except (ValueError, TypeError):
            last_date = datetime.utcnow()
        snippet = (last.get("snippet") or "")[:300]

        from_addrs = _extract_emails(last_from_raw)
        direction = (
            "outbound"
            if from_addrs and from_addrs[0] == user_email
            else "inbound"
        )

        existing = (
            db.query(EmailThreadRow)
            .filter(
                EmailThreadRow.user_id == user_id,
                EmailThreadRow.gmail_thread_id == thread_id,
            )
            .first()
        )
        if existing is None:
            db.add(EmailThreadRow(
                user_id=user_id,
                engagement_id=matched_engagement_id,
                gmail_thread_id=thread_id,
                subject=last_subject,
                last_message_at=last_date,
                last_message_snippet=snippet,
                last_message_from=last_from_raw[:320],
                last_message_direction=direction,
                message_count=len(thread_messages),
            ))
            threads_new += 1
        else:
            existing.subject = last_subject
            existing.last_message_at = last_date
            existing.last_message_snippet = snippet
            existing.last_message_from = last_from_raw[:320]
            existing.last_message_direction = direction
            existing.message_count = len(thread_messages)

        engagement = db.get(LawyerEngagementRow, matched_engagement_id)
        if engagement and (
            engagement.last_activity_at is None
            or engagement.last_activity_at < last_date
        ):
            engagement.last_activity_at = last_date

        # Auto-progression: an inbound reply moves the funnel from
        # not_contacted/outreach_sent → in_discussion. Idempotent — once
        # status is past in_discussion (engaged/declined) we don't touch it.
        # User-set statuses always win on the way "forward"; sync only
        # nudges progression, never reverses it.
        if (
            engagement
            and direction == "inbound"
            and engagement.status in ("not_contacted", "outreach_sent")
        ):
            engagement.status = "in_discussion"

    token_row.last_synced_at = now
    token_row.last_sync_error = None
    db.commit()

    # Brief LLM-generated summary of what just synced — actionable
    # signal vs raw counts. Skipped silently when no API key, no
    # threads touched, or the call fails (sync result is more
    # important than the optional summary).
    summary: str | None = None
    if (threads_new + threads_matched) > 0 and settings.anthropic_api_key:
        try:
            summary = _summarize_sync(db, user_id, threads_touched_ids=list(seen_threads))
        except Exception:
            logger.exception("gmail sync summary failed; returning counts only")

    return {
        "messages_scanned": messages_scanned,
        "threads_matched": threads_matched,
        "threads_new": threads_new,
        "last_synced_at": now.isoformat(),
        "summary": summary,
    }


SUMMARY_MODEL = "claude-haiku-4-5"
SUMMARY_TIMEOUT_S = 15


def _summarize_sync(
    db: Session, user_id: str, *, threads_touched_ids: list[str]
) -> str | None:
    """Generate a 1-2 sentence "what's new" summary using Haiku.

    Reads the touched threads back from the DB (post-upsert state) so the
    summary reflects what was actually persisted, not raw Gmail data.
    Groups by firm (engagement) and surfaces direction/age signals.
    Returns None if the LLM call fails or there's nothing notable.
    """
    if not threads_touched_ids:
        return None
    rows = (
        db.query(EmailThreadRow, LawyerEngagementRow)
        .join(LawyerEngagementRow, EmailThreadRow.engagement_id == LawyerEngagementRow.id)
        .filter(EmailThreadRow.user_id == user_id)
        .filter(EmailThreadRow.gmail_thread_id.in_(threads_touched_ids))
        .order_by(EmailThreadRow.last_message_at.desc())
        .all()
    )
    if not rows:
        return None

    # Compact line per thread; cap to keep prompt small + cheap.
    lines: list[str] = []
    for thread, engagement in rows[:20]:
        age_h = max(
            0,
            int((datetime.utcnow() - thread.last_message_at).total_seconds() / 3600),
        )
        age_label = (
            f"{age_h}h ago" if age_h < 48 else f"{age_h // 24}d ago"
        )
        lines.append(
            f"- {engagement.firm_name} | {thread.last_message_direction} | "
            f"{age_label} | subject: {thread.subject[:80]!r} | "
            f"snippet: {thread.last_message_snippet[:120]!r}"
        )
    threads_block = "\n".join(lines)

    system = (
        "You are an assistant summarizing the result of a Gmail sync for a "
        "compliance app. Write 1-2 short sentences (max 220 chars) describing "
        "what's notable for the user — focus on inbound replies, urgent items, "
        "and which firms are active. No bullet lists, no preamble like 'Here is'. "
        "Direct, actionable, present-tense. If nothing inbound and nothing new, "
        "say it briefly (e.g., 'Outbox-only sync — no replies yet')."
    )
    user_prompt = (
        f"{len(rows)} threads were synced. Details:\n{threads_block}\n\n"
        "Summarize."
    )

    try:
        import anthropic
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=SUMMARY_TIMEOUT_S,
            max_retries=1,
        )
        resp = client.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=180,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "\n".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
        # Defensive trim — model occasionally over-runs the char budget.
        return text[:280] if text else None
    except Exception as exc:
        logger.warning("gmail sync summary call failed: %s", exc)
        return None
