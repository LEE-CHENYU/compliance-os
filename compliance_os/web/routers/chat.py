"""LLM-powered chat assistant with user context."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import CheckRow
from compliance_os.web.services.auth_service import decode_token
from compliance_os.web.services.timeline_builder import build_timeline

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []  # [{"role": "user"|"assistant", "text": "..."}]


class ChatResponse(BaseModel):
    reply: str


def _get_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization")
    payload = decode_token(authorization.split(" ", 1)[1])
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def _build_context(user_id: str, db: Session) -> str:
    """Build a context summary of the user's situation for the LLM."""
    timeline = build_timeline(user_id, db)

    parts = ["# User's Compliance Profile\n"]

    # Key facts
    if timeline.get("key_facts"):
        parts.append("## Key Facts")
        for fact in timeline["key_facts"]:
            parts.append(f"- {fact['label']}: {fact['value']}")
        parts.append("")

    # Documents on file
    if timeline.get("documents"):
        parts.append("## Documents Uploaded")
        for doc in timeline["documents"]:
            parts.append(f"- {doc['filename']} ({doc['doc_type']})")
        parts.append("")

    # Current findings
    if timeline.get("findings"):
        parts.append("## Current Issues Found")
        for f in timeline["findings"]:
            parts.append(f"- [{f['severity'].upper()}] {f['title']}: {f['action']}")
        parts.append("")

    # Advisories
    if timeline.get("advisories"):
        parts.append("## Potential Risks to Investigate")
        for a in timeline["advisories"]:
            parts.append(f"- {a['title']}: {a['action']} (consequence: {a['consequence']})")
        parts.append("")

    # Deadlines
    if timeline.get("deadlines"):
        parts.append("## Upcoming Deadlines")
        for d in timeline["deadlines"]:
            status = "OVERDUE" if d["days"] < 0 else f"{d['days']} days"
            parts.append(f"- {d['title']}: {d['date']} ({status})")
        parts.append("")

    return "\n".join(parts)


SYSTEM_PROMPT = """You are Guardian, a compliance assistant for immigrants in the US. You help users understand their immigration, tax, and business compliance obligations.

IMPORTANT RULES:
1. You are NOT a lawyer. Never provide legal advice. Always recommend consulting a qualified attorney for specific legal questions.
2. Be calm, procedural, and evidence-based. Never be alarmist.
3. When you identify a potential risk, explain what it is, why it matters, and what the user should do next.
4. Use plain English. Avoid jargon. When you must reference a form number, explain what it is.
5. Keep responses concise — 2-3 sentences for simple questions, more for complex ones.
6. If you need more information to help, ask one specific follow-up question.
7. Always frame findings as "potential risks" or "things worth looking into", never as definitive legal conclusions.

You have access to the user's compliance profile below. Use this context to give personalized, relevant answers.

{context}
"""


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    context = _build_context(user.id, db)

    # Build messages for the LLM
    system = SYSTEM_PROMPT.format(context=context)
    messages = []
    for msg in body.history:
        messages.append({"role": msg["role"], "content": msg["text"]})
    messages.append({"role": "user", "content": body.message})

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if anthropic_key:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system=system,
            messages=messages,
            temperature=0.3,
        )
        reply = response.content[0].text
    else:
        # Fallback to OpenAI
        from openai import OpenAI
        client = OpenAI()
        oai_messages = [{"role": "system", "content": system}] + messages
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=oai_messages,
            temperature=0.3,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content

    return ChatResponse(reply=reply)
