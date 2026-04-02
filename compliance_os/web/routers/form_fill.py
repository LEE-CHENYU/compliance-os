"""Form-fill API: extract AcroForm fields and generate filled PDFs."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.routers.chat import _build_context, _get_user
from compliance_os.web.services.form_filler import (
    extract_acroform_fields,
    fill_pdf_fields,
    propose_field_values,
)

router = APIRouter(prefix="/api/form-fill", tags=["form-fill"])

_MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class FieldProposal(BaseModel):
    field_name: str
    field_type: str = ""
    proposed_value: str = ""
    confidence: str = ""
    source: str = ""


class ExtractResponse(BaseModel):
    fields: list[FieldProposal]
    form_field_count: int
    filled_count: int
    unfilled_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_pdf(file: UploadFile, pdf_bytes: bytes) -> None:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(422, "File must be a PDF (.pdf)")
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(422, "PDF exceeds the 20 MB size limit")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/extract", response_model=ExtractResponse)
async def extract_and_propose(
    file: UploadFile,
    instruction: str = Form(default=""),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Extract AcroForm fields from a PDF and propose values using RAG context."""
    user = _get_user(authorization, db)

    pdf_bytes = await file.read()
    _validate_pdf(file, pdf_bytes)

    # Extract fields
    try:
        fields = extract_acroform_fields(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    if not fields:
        raise HTTPException(422, "This PDF does not contain fillable form fields")

    # Build RAG context
    context_text, _refs = _build_context(user.id, db)

    # Ask LLM to propose values
    usage_context = {
        "db_session": db,
        "operation": "form_fill",
        "user_id": user.id,
    }
    try:
        proposals = propose_field_values(
            fields,
            context_text,
            instruction=instruction or None,
            usage_context=usage_context,
        )
    except Exception:
        db.commit()
        raise HTTPException(502, "LLM service unavailable; please try again")

    db.commit()

    # Build a lookup of LLM proposals keyed by field_name
    proposal_map: dict[str, dict] = {p["field_name"]: p for p in proposals}

    # Merge: field_type comes from extraction; proposals fill the rest.
    # Add any fields the LLM missed.
    merged: list[FieldProposal] = []
    seen: set[str] = set()

    for f in fields:
        name = f["field_name"]
        seen.add(name)
        proposal = proposal_map.get(name, {})
        merged.append(
            FieldProposal(
                field_name=name,
                field_type=f.get("field_type", ""),
                proposed_value=proposal.get("proposed_value", ""),
                confidence=proposal.get("confidence", ""),
                source=proposal.get("source", ""),
            )
        )

    # Add any extra fields the LLM returned that weren't in extraction
    for name, proposal in proposal_map.items():
        if name not in seen:
            merged.append(
                FieldProposal(
                    field_name=name,
                    field_type="",
                    proposed_value=proposal.get("proposed_value", ""),
                    confidence=proposal.get("confidence", ""),
                    source=proposal.get("source", ""),
                )
            )

    filled_count = sum(1 for fp in merged if fp.proposed_value)
    unfilled_count = len(merged) - filled_count

    return ExtractResponse(
        fields=merged,
        form_field_count=len(merged),
        filled_count=filled_count,
        unfilled_count=unfilled_count,
    )


@router.post("/generate")
async def generate_filled_pdf(
    file: UploadFile,
    values: str = Form(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Fill a PDF's AcroForm fields with provided values and return the filled PDF."""
    _get_user(authorization, db)

    pdf_bytes = await file.read()
    _validate_pdf(file, pdf_bytes)

    # Parse values JSON
    try:
        field_values: dict[str, str] = json.loads(values)
        if not isinstance(field_values, dict):
            raise ValueError("values must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(422, f"Invalid values JSON: {exc}") from exc

    filled_bytes = fill_pdf_fields(pdf_bytes, field_values)

    return Response(
        content=filled_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="filled_{file.filename}"'},
    )
