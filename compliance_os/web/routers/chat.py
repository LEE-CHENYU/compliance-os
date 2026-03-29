"""LLM-powered chat assistant with user context."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import CheckRow
from compliance_os.web.services.auth_service import get_bearer_payload
from compliance_os.web.services.llm_runtime import chat_completion
from compliance_os.web.services.retrieval import build_check_retrieval_context, retrieve_documents_for_query
from compliance_os.web.services.subject_chains import list_user_subject_chains, serialize_subject_chain
from compliance_os.web.services.timeline_builder import build_timeline, canonical_documents_for_checks

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _newest_extracted_fields(check, doc_types: tuple[str, ...]) -> dict[str, str]:
    """Return extracted fields from the most recent active document of the given types."""
    from datetime import datetime, timezone

    best = None
    best_score = (False, datetime.min.replace(tzinfo=timezone.utc), "")
    for doc in check.documents:
        if doc.doc_type not in doc_types:
            continue
        has_fields = any(f.field_value not in (None, "") for f in doc.extracted_fields)
        uploaded = doc.uploaded_at or datetime.min.replace(tzinfo=timezone.utc)
        if uploaded.tzinfo is None:
            uploaded = uploaded.replace(tzinfo=timezone.utc)
        score = (has_fields, uploaded, doc.id)
        if score > best_score:
            best_score = score
            best = doc
    if best is None:
        return {}
    return {f.field_name: f.field_value for f in best.extracted_fields}


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []  # [{"role": "user"|"assistant", "text": "..."}]


class ChatResponse(BaseModel):
    reply: str


def _get_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow:
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def _build_context(user_id: str, db: Session, query: str | None = None) -> str:
    """Build a context summary of the user's situation for the LLM."""
    timeline = build_timeline(user_id, db)
    checks = db.query(CheckRow).filter(CheckRow.user_id == user_id).all()
    canonical_docs = canonical_documents_for_checks(checks)
    subject_chains = [
        serialize_subject_chain(chain, canonical_docs)
        for chain in list_user_subject_chains(user_id, db)
    ]

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

    if subject_chains:
        parts.append("## Subject Chains")
        for chain in subject_chains:
            dates = []
            if chain.get("start_date"):
                dates.append(f"start={chain['start_date']}")
            if chain.get("end_date"):
                dates.append(f"end={chain['end_date']}")
            date_suffix = f" ({', '.join(dates)})" if dates else ""
            parts.append(f"- [{chain['chain_type']}] {chain['display_name']}{date_suffix}")
            for doc in chain.get("documents", [])[:6]:
                role = doc.get("role") or "supporting"
                parts.append(f"  - {doc.get('filename') or 'Unknown document'} [{doc.get('doc_type')}] role={role}")
        parts.append("")

    # Current findings
    if timeline.get("findings"):
        parts.append("## Current Issues Found")
        for f in timeline["findings"]:
            parts.append(f"- [{f['severity'].upper()}] {f['title']}: {f['action']}")
        parts.append("")

    if timeline.get("all_integrity_issues"):
        parts.append("## Data Integrity And Mapping Issues")
        for issue in timeline["all_integrity_issues"]:
            issue_parts = [f"- [{issue['severity'].upper()}] {issue['title']}: {issue['message']}"]
            docs = issue.get("documents") or []
            if docs:
                issue_parts.append(
                    "  Documents: " + ", ".join(doc.get("filename", "Unknown document") for doc in docs[:5])
                )
            chains = issue.get("chains") or []
            if chains:
                issue_parts.append(
                    "  Chains: " + ", ".join(chain.get("label") or chain.get("key") or "Unknown chain" for chain in chains[:4])
                )
            parts.extend(issue_parts)
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

    if checks:
        parts.append("## Active Document Families")
        for check in checks:
            context = build_check_retrieval_context(check)
            for family in context["families"]:
                active = family["active_document"]
                if not active:
                    continue
                family_label = family["document_family"]
                series_key = family.get("document_series_key")
                if series_key and series_key != family_label:
                    family_label = f"{family_label} [{series_key}]"
                parts.append(
                    f"- Check {check.track} / {family_label}: "
                    f"{active['filename']} (v{active['document_version']}, {active['doc_type']})"
                )
        parts.append("")

    if query and checks:
        retrieved = retrieve_documents_for_query(checks, query=query, top_k=4)
        if retrieved:
            parts.append("## Retrieved Documents For Current Question")
            for doc in retrieved:
                parts.append(
                    f"- {doc['filename']} "
                    f"[family={doc['document_family']}, version={doc['document_version']}, score={doc['score']:.1f}]"
                )
                fields = doc.get("extracted_fields") or {}
                for key, value in list(fields.items())[:5]:
                    parts.append(f"  {key}: {value}")
                if doc.get("ocr_text_excerpt"):
                    parts.append(f"  Excerpt: {doc['ocr_text_excerpt']}")
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
    context = _build_context(user.id, db, query=body.message)

    # Build messages for the LLM
    system = SYSTEM_PROMPT.format(context=context)
    messages = []
    for msg in body.history:
        messages.append({"role": msg["role"], "content": msg["text"]})
    messages.append({"role": "user", "content": body.message})

    try:
        reply = chat_completion(
            system_prompt=system,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            usage_context={
                "db_session": db,
                "operation": "chat_assistant",
                "user_id": user.id,
                "request_metadata": {
                    "history_count": len(body.history),
                    "message_length": len(body.message),
                },
            },
        )
    except Exception:
        db.commit()
        raise

    db.commit()

    return ChatResponse(reply=reply)


class AnswerStore(BaseModel):
    question_id: str  # e.g. "immigration_stage", "has_entity", "foreign_accounts"
    answer: str       # the user's chip or text answer


# Mapping from question IDs to check answer fields
ANSWER_MAPPINGS: dict[str, dict] = {
    "immigration_stage": {
        "track": "stem_opt",
        "field": "stage",
        "value_map": {
            "Yes, I'm on a visa": "on_visa_unknown",
            "US citizen / PR": "us_citizen",
            "Outside the US": "outside_us",
        },
        "residency_field": "owner_residency",
        "residency_map": {
            "Yes, I'm on a visa": "on_visa",
            "US citizen / PR": "us_citizen_or_pr",
            "Outside the US": "outside_us",
        },
    },
    "has_entity": {
        "track": "entity",
        "create_check": True,
    },
    "tax_filing": {
        "track": "stem_opt",
        "field": "tax_form_filed",
    },
    "foreign_accounts": {
        "track": "stem_opt",
        "field": "has_foreign_accounts",
        "value_map": {"Yes": "yes", "No": "no"},
    },
    "tax_software": {
        "track": "stem_opt",
        "field": "tax_software_used",
        "value_map": {"TurboTax": "turbotax", "H&R Block": "hr_block", "Sprintax": "sprintax", "A CPA did it": "cpa", "Haven\u2019t filed": "not_filed"},
    },
    "foreign_gifts": {
        "track": "stem_opt",
        "field": "received_foreign_gifts",
        "value_map": {"Yes": "yes", "No": "no", "Not sure": "not_sure"},
    },
    "form_8843": {
        "track": "stem_opt",
        "field": "filed_8843",
        "value_map": {"Yes": "yes", "No": "no", "What is that?": "no"},
    },
    "govt_health_plan": {
        "track": "stem_opt",
        "field": "has_govt_health_plan",
        "value_map": {
            "Yes, free/subsidized plan": "yes",
            "Yes, but I pay full price": "no",
            "No": "no",
            "Not sure": "not_sure",
        },
    },
    "multistate_health": {
        "track": "stem_opt",
        "field": "has_multistate_health",
        "value_map": {"Yes": "yes", "No": "no"},
    },
}


@router.post("/answer")
def store_answer(
    body: AnswerStore,
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Store a chat answer into the user's check data and re-evaluate rules."""
    user = _get_user(authorization, db)

    mapping = ANSWER_MAPPINGS.get(body.question_id, {})
    track = mapping.get("track", "stem_opt")

    # Find or create a check for this track
    check = db.query(CheckRow).filter(
        CheckRow.user_id == user.id,
        CheckRow.track == track,
    ).first()

    if not check and mapping.get("create_check"):
        # Create a new check for this track
        check = CheckRow(track=track, status="saved", user_id=user.id, answers={})
        db.add(check)
        db.flush()
    elif not check:
        # Add to existing check of any track
        check = db.query(CheckRow).filter(CheckRow.user_id == user.id).first()

    if check:
        answers = dict(check.answers or {})

        # Apply value mapping if exists
        value_map = mapping.get("value_map", {})
        value = value_map.get(body.answer, body.answer)

        # Store the answer
        field = mapping.get("field", body.question_id)
        answers[field] = value

        # Special: residency field mapping
        if "residency_field" in mapping:
            res_map = mapping.get("residency_map", {})
            answers[mapping["residency_field"]] = res_map.get(body.answer, body.answer)

        check.answers = answers
        db.commit()

        # Re-evaluate rules for all user's checks
        from pathlib import Path
        from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine
        from compliance_os.web.models.tables_v2 import FindingRow

        for user_check in db.query(CheckRow).filter(CheckRow.user_id == user.id).all():
            rule_file = Path(__file__).resolve().parents[3] / "config" / "rules" / f"{user_check.track}.yaml"
            if not rule_file.exists():
                continue

            engine = RuleEngine.from_yaml(str(rule_file))

            ext_a = _newest_extracted_fields(user_check, ("i983",))
            ext_b = _newest_extracted_fields(user_check, ("employment_letter",))

            comp_dict = {c.field_name: {"status": c.status, "confidence": c.confidence} for c in user_check.comparisons}

            ctx = EvaluationContext(
                answers=user_check.answers or {},
                extraction_a=ext_a,
                extraction_b=ext_b,
                comparisons=comp_dict,
            )

            # Clear old findings and re-evaluate
            for old in user_check.findings:
                db.delete(old)

            for fr in engine.evaluate(ctx):
                db.add(FindingRow(
                    check_id=user_check.id,
                    rule_id=fr.rule_id,
                    rule_version=engine.version,
                    severity=fr.severity,
                    category=fr.category,
                    title=fr.title,
                    action=fr.action,
                    consequence=fr.consequence,
                    immigration_impact=fr.immigration_impact,
                ))
            db.commit()

    return {"ok": True, "stored": body.question_id, "answer": body.answer}
