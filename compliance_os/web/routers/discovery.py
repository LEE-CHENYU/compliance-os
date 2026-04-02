"""Discovery intake and chat API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas import (
    CaseSummary,
    ChatHistoryResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    DiscoveryAnswerCreate,
    DiscoveryAnswerResponse,
    DiscoveryAnswersResponse,
)
from compliance_os.web.models.tables import CaseRow, ChatMessageRow, DiscoveryAnswerRow
from compliance_os.web.services.followup import generate_followups

router = APIRouter(prefix="/api/cases/{case_id}", tags=["discovery"])


def _get_case(case_id: str, session: Session) -> CaseRow:
    case = session.get(CaseRow, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/discovery", response_model=DiscoveryAnswerResponse)
def save_answer(case_id: str, body: DiscoveryAnswerCreate, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    # Upsert: replace existing answer for same step+question_key
    existing = (
        session.query(DiscoveryAnswerRow)
        .filter_by(case_id=case_id, step=body.step, question_key=body.question_key)
        .first()
    )
    if existing:
        existing.answer = body.answer
        session.commit()
        session.refresh(existing)
        row = existing
    else:
        row = DiscoveryAnswerRow(
            case_id=case_id, step=body.step,
            question_key=body.question_key, answer=body.answer,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    return DiscoveryAnswerResponse(
        id=row.id, step=row.step, question_key=row.question_key,
        answer=row.answer, answered_at=row.answered_at,
    )


@router.get("/discovery", response_model=DiscoveryAnswersResponse)
def get_answers(case_id: str, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    rows = (
        session.query(DiscoveryAnswerRow)
        .filter_by(case_id=case_id)
        .order_by(DiscoveryAnswerRow.answered_at)
        .all()
    )
    return DiscoveryAnswersResponse(answers=[
        DiscoveryAnswerResponse(
            id=r.id, step=r.step, question_key=r.question_key,
            answer=r.answer, answered_at=r.answered_at,
        )
        for r in rows
    ])


@router.post("/discovery/summary", response_model=CaseSummary)
def generate_summary(case_id: str, session: Session = Depends(get_session)):
    case = _get_case(case_id, session)
    rows = session.query(DiscoveryAnswerRow).filter_by(case_id=case_id).all()
    summary = {r.question_key: r.answer for r in rows}
    # Update case status
    case.status = "documents"
    session.commit()
    return CaseSummary(summary=summary)


@router.post("/chat", response_model=ChatHistoryResponse)
def send_chat(case_id: str, body: ChatMessageCreate, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    # Save user message
    user_msg = ChatMessageRow(case_id=case_id, role="user", content=body.content)
    session.add(user_msg)
    session.commit()
    session.refresh(user_msg)
    # Return full history
    messages = (
        session.query(ChatMessageRow)
        .filter_by(case_id=case_id)
        .order_by(ChatMessageRow.created_at)
        .all()
    )
    return ChatHistoryResponse(messages=[
        ChatMessageResponse(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
        for m in messages
    ])


@router.get("/chat", response_model=ChatHistoryResponse)
def get_chat(case_id: str, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    messages = (
        session.query(ChatMessageRow)
        .filter_by(case_id=case_id)
        .order_by(ChatMessageRow.created_at)
        .all()
    )
    # If no messages, generate initial follow-up questions
    if not messages:
        answers = session.query(DiscoveryAnswerRow).filter_by(case_id=case_id).all()
        answer_dicts = [{"question_key": a.question_key, "answer": a.answer} for a in answers]
        followups = generate_followups(answer_dicts)
        if followups:
            content = "Based on your answers, I have a few follow-up questions:\n\n"
            content += "\n\n".join(f"**{i+1}.** {q}" for i, q in enumerate(followups))
            assistant_msg = ChatMessageRow(case_id=case_id, role="assistant", content=content)
            session.add(assistant_msg)
            session.commit()
            session.refresh(assistant_msg)
            messages = [assistant_msg]
    return ChatHistoryResponse(messages=[
        ChatMessageResponse(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
        for m in messages
    ])
