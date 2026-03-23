"""Case CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas import CaseCreate, CaseResponse, CaseListResponse
from compliance_os.web.models.tables import CaseRow

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseResponse)
def create_case(body: CaseCreate, session: Session = Depends(get_session)):
    case = CaseRow(workflow_type=body.workflow_type)
    session.add(case)
    session.commit()
    session.refresh(case)
    return CaseResponse(
        id=case.id,
        workflow_type=case.workflow_type,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("", response_model=CaseListResponse)
def list_cases(session: Session = Depends(get_session)):
    cases = session.query(CaseRow).order_by(CaseRow.created_at.desc()).all()
    return CaseListResponse(cases=[
        CaseResponse(
            id=c.id, workflow_type=c.workflow_type, status=c.status,
            created_at=c.created_at, updated_at=c.updated_at,
            document_count=len(c.documents), answer_count=len(c.discovery_answers),
        )
        for c in cases
    ])


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, session: Session = Depends(get_session)):
    case = session.get(CaseRow, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse(
        id=case.id, workflow_type=case.workflow_type, status=case.status,
        created_at=case.created_at, updated_at=case.updated_at,
        document_count=len(case.documents), answer_count=len(case.discovery_answers),
    )
