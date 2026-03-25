"""Register, login, me endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut, UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import CheckRow
from compliance_os.web.services.auth_service import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_session)):
    existing = db.query(UserRow).filter(UserRow.email == body.email).first()
    if existing:
        raise HTTPException(409, "Email already registered")
    user = UserRow(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id, user.email)
    return AuthResponse(token=token, user_id=user.id, email=user.email)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_session)):
    user = db.query(UserRow).filter(UserRow.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user.id, user.email)
    return AuthResponse(token=token, user_id=user.id, email=user.email)


@router.get("/me", response_model=UserOut)
def me(authorization: str = Header(None), db: Session = Depends(get_session)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


@router.post("/link-check/{check_id}")
def link_check_to_user(
    check_id: str,
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Link an existing check to the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization header")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    user_id = payload["user_id"]

    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    check.user_id = user_id
    db.commit()
    return {"ok": True}
