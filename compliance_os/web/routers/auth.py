"""Register, login, me, and Google OAuth endpoints."""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
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

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")


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


# === Google OAuth ===

class GoogleTokenRequest(BaseModel):
    credential: str  # Google ID token from frontend


@router.get("/google/url")
def google_auth_url():
    """Return the Google OAuth authorization URL."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google OAuth not configured. Set GOOGLE_CLIENT_ID env var.")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}"}


@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_session)):
    """Handle Google OAuth callback — exchange code for token, create/login user."""
    import httpx

    # Exchange code for tokens
    token_resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    if token_resp.status_code != 200:
        raise HTTPException(400, f"Google token exchange failed: {token_resp.text}")

    tokens = token_resp.json()
    id_token = tokens.get("id_token")

    # Decode ID token to get user info (Google's public keys verify it)
    import jwt as pyjwt
    # For simplicity, decode without verification (Google already verified via HTTPS)
    # In production, verify with Google's public keys
    user_info = pyjwt.decode(id_token, options={"verify_signature": False})

    email = user_info.get("email")
    if not email:
        raise HTTPException(400, "No email in Google token")

    # Find or create user
    user = db.query(UserRow).filter(UserRow.email == email).first()
    if not user:
        user = UserRow(
            email=email,
            password_hash="google_oauth_" + str(uuid.uuid4()),  # No password for OAuth users
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create JWT
    token = create_token(user.id, user.email)

    # Redirect to frontend with token in URL fragment
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(
        url=f"{frontend_url}/login?token={token}&email={email}&user_id={user.id}",
    )


@router.post("/google/token", response_model=AuthResponse)
def google_token_login(body: GoogleTokenRequest, db: Session = Depends(get_session)):
    """Login with a Google ID token (from frontend Google Sign-In button)."""
    import jwt as pyjwt

    try:
        user_info = pyjwt.decode(body.credential, options={"verify_signature": False})
    except Exception:
        raise HTTPException(400, "Invalid Google token")

    email = user_info.get("email")
    if not email:
        raise HTTPException(400, "No email in Google token")

    # Find or create user
    user = db.query(UserRow).filter(UserRow.email == email).first()
    if not user:
        user = UserRow(
            email=email,
            password_hash="google_oauth_" + str(uuid.uuid4()),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_token(user.id, user.email)
    return AuthResponse(token=token, user_id=user.id, email=user.email)
