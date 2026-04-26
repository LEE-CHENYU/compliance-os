"""Build a user-scoped "activity" context blob for the chat + voice assistants.

The compliance assistant historically only knew about timeline / documents /
deadlines. After a user runs lawyer searches, tracks engagements, and syncs
Gmail, those become first-order facts the assistant should be able to reason
about — "what did Klasko quote me?", "did Wolfsdorf reply yet?", "where am I
stuck?". This module formats those into a single string the assistant prompt
can include verbatim.

Two consumers:

  1. /api/chat (`_build_context`) — appends the formatted text to the
     system prompt for every chat turn.
  2. /api/me/activity-context — read-only endpoint the voice agent fetches
     at call-start so its static context blob includes the same facts.

Implementation notes:

  - Keep the result bounded — top-N per section. The assistants don't
    need every historical row; they need recent, attention-worthy ones.
  - Reuse `_compute_attention` from routers/me.py so the "new reply"
    heuristics stay in one place.
  - All formatting happens here so consumers can both inline raw text
    without re-templating.
"""
from __future__ import annotations

import datetime as _dt

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from compliance_os.web.models.tables import (
    CaseRow,
    EmailThreadRow,
    LawyerEngagementRow,
    ProfessionalSearchRequestRow,
)
from compliance_os.web.routers.me import _compute_attention

# Caps — keep the prompt bounded. Tuned so the assistant has enough to
# answer "what's recent?" without drowning the prompt in stale rows.
SEARCHES_LIMIT = 5
ENGAGEMENTS_LIMIT = 10
EMAIL_THREADS_LIMIT = 10
TOP_FIRMS_PER_SEARCH = 3


def _format_search(row: ProfessionalSearchRequestRow) -> list[str]:
    """One paid lawyer-search summary, plus the top firms by score."""
    paid_at = row.paid_at.isoformat() if row.paid_at else "?"
    grant_label = (
        " (Pro free grant)"
        if getattr(row, "pro_free_grant_at", None)
        else ""
    )
    head = (
        f"- [{row.vertical}] {row.purpose} — paid {paid_at}{grant_label} "
        f"(search_id={row.id})"
    )
    lines = [head]

    # tier_report is a JSONB list on the row. Defensive against legacy
    # rows where the column is null or shaped unexpectedly.
    tier = row.tier_report if isinstance(row.tier_report, list) else None
    if tier:
        # Sort defensively — most rows are already by score, but never
        # trust JSON ordering across DB versions.
        sorted_tier = sorted(
            (t for t in tier if isinstance(t, dict)),
            key=lambda t: t.get("score") or 0,
            reverse=True,
        )
        for firm in sorted_tier[:TOP_FIRMS_PER_SEARCH]:
            score = firm.get("score")
            score_str = f"{score}" if score is not None else "—"
            lo = firm.get("lowest_quote")
            hi = firm.get("highest_quote")
            quote = (
                f"${int(lo):,}–${int(hi):,}"
                if lo is not None and hi is not None
                else f"${int(lo):,}+"
                if lo is not None
                else "(no quote)"
            )
            lines.append(
                f"  · {firm.get('firm', '?')} (score={score_str}, fees={quote})"
            )
    return lines


def _build_searches_section(user_id: str, db: Session) -> list[str]:
    """Recent paid lawyer-search reports — newest first."""
    rows = (
        db.query(ProfessionalSearchRequestRow)
        .filter(
            ProfessionalSearchRequestRow.user_id == user_id,
            ProfessionalSearchRequestRow.paid_at.isnot(None),
        )
        .order_by(desc(ProfessionalSearchRequestRow.paid_at))
        .limit(SEARCHES_LIMIT)
        .all()
    )
    if not rows:
        return []
    out = ["## Lawyer Search Reports (paid)"]
    for r in rows:
        out.extend(_format_search(r))
    out.append("")
    return out


def _build_engagements_section(user_id: str, db: Session) -> list[str]:
    """Per-engagement summary across all the user's cases.

    Mirrors the dashboard list (most recent activity first), but only
    surfaces engagements that need attention OR are currently in
    discussion — finished/declined ones add noise, not signal.
    """
    now = _dt.datetime.utcnow()

    # Aggregate thread counts + last-message timestamp per engagement —
    # same shape used in /api/me/engagements.
    thread_count_sq = (
        db.query(
            EmailThreadRow.engagement_id.label("eid"),
            func.count(EmailThreadRow.id).label("cnt"),
            func.max(EmailThreadRow.last_message_at).label("last_at"),
        )
        .group_by(EmailThreadRow.engagement_id)
        .subquery()
    )

    rows = (
        db.query(
            LawyerEngagementRow,
            CaseRow,
            thread_count_sq.c.cnt,
            thread_count_sq.c.last_at,
        )
        .join(CaseRow, LawyerEngagementRow.case_id == CaseRow.id)
        .outerjoin(
            thread_count_sq,
            thread_count_sq.c.eid == LawyerEngagementRow.id,
        )
        .filter(CaseRow.user_id == user_id)
        .order_by(desc(LawyerEngagementRow.last_activity_at))
        .limit(40)  # filter down to attention-worthy below
        .all()
    )

    interesting: list[tuple[str, str]] = []  # (priority_key, formatted_line)
    for engagement, case, thread_count, last_at in rows:
        last_dir: str | None = None
        last_subj: str | None = None
        if thread_count and thread_count > 0:
            last_thread = (
                db.query(EmailThreadRow)
                .filter(EmailThreadRow.engagement_id == engagement.id)
                .order_by(EmailThreadRow.last_message_at.desc())
                .first()
            )
            if last_thread is not None:
                last_dir = last_thread.last_message_direction
                last_subj = last_thread.subject

        attention = _compute_attention(
            status=engagement.status,
            last_thread_at=last_at,
            last_thread_direction=last_dir,
            last_activity_at=engagement.last_activity_at,
            now=now,
        )

        # Drop engagements with no signal: not_contacted with no threads
        # and no attention label. They clutter the prompt without value.
        is_in_discussion = engagement.status == "in_discussion"
        if attention is None and not is_in_discussion:
            continue

        priority_key = attention or "in_discussion"
        last_thread_repr = (
            f" · last reply: {last_dir} \"{last_subj}\""
            if last_subj and last_dir
            else ""
        )
        line = (
            f"- {engagement.firm_name} "
            f"(case={case.workflow_type or 'unknown'}, status={engagement.status}, "
            f"attention={attention or 'discussing'}){last_thread_repr}"
        )
        interesting.append((priority_key, line))

    if not interesting:
        return []

    # Re-order: new_reply > needs_followup > awaiting_response > in_discussion
    priority_rank = {
        "new_reply": 0,
        "needs_followup": 1,
        "awaiting_response": 2,
        "in_discussion": 3,
    }
    interesting.sort(key=lambda t: priority_rank.get(t[0], 9))
    out = ["## Lawyer Engagements (active)"]
    for _, line in interesting[:ENGAGEMENTS_LIMIT]:
        out.append(line)
    out.append("")
    return out


def _build_emails_section(user_id: str, db: Session) -> list[str]:
    """Most recent email threads with the firm-side counterparty.

    Includes inbound/outbound direction, snippet, and engagement firm.
    Bounded to EMAIL_THREADS_LIMIT — the assistant rarely needs more
    than the last week or two of activity to answer "did X reply?".
    """
    rows = (
        db.query(EmailThreadRow, LawyerEngagementRow.firm_name)
        .join(LawyerEngagementRow, EmailThreadRow.engagement_id == LawyerEngagementRow.id)
        .filter(EmailThreadRow.user_id == user_id)
        .order_by(EmailThreadRow.last_message_at.desc())
        .limit(EMAIL_THREADS_LIMIT)
        .all()
    )
    if not rows:
        return []
    out = ["## Recent Email Threads"]
    for thread, firm_name in rows:
        when = thread.last_message_at.isoformat() if thread.last_message_at else "?"
        snippet = (thread.last_message_snippet or "").strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        out.append(
            f"- [{thread.last_message_direction or '?'}] {firm_name} — "
            f"\"{thread.subject or '(no subject)'}\" "
            f"({thread.message_count} msg, last {when})"
        )
        if snippet:
            out.append(f"  > {snippet}")
    out.append("")
    return out


def build_activity_context(user_id: str, db: Session) -> str:
    """Produce a markdown-style multi-line string of the user's activity.

    Returns "" when the user has no relevant activity yet — callers
    should append unconditionally; an empty string is a no-op.
    """
    parts: list[str] = []
    parts.extend(_build_searches_section(user_id, db))
    parts.extend(_build_engagements_section(user_id, db))
    parts.extend(_build_emails_section(user_id, db))
    return "\n".join(parts).strip()
