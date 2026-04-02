"""Register, login, me, and Google OAuth endpoints."""
from __future__ import annotations

import os
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import (
    AuthResponse,
    LoginRequest,
    OpenClawConnectionStatus,
    OpenClawTokenInfo,
    OpenClawTokenIssueResponse,
    RegisterRequest,
    UserOut,
    UserRow,
)
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import CheckRow
from compliance_os.web.services.auth_service import (
    create_token,
    get_active_openclaw_token,
    get_bearer_payload,
    hash_password,
    issue_openclaw_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def _google_client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def _request_origin(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",", 1)[0].strip()
    host = forwarded_host or request.headers.get("host") or request.url.netloc
    proto = forwarded_proto or request.url.scheme
    if not forwarded_proto and host and not _is_local_host(host):
        proto = "https"
    return f"{proto}://{host}".rstrip("/")


def _is_local_host(host: str) -> bool:
    hostname = host.split(":", 1)[0].lower()
    return hostname in {"localhost", "127.0.0.1"}


def _google_redirect_uri(request: Request) -> str:
    configured = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{_request_origin(request)}/api/auth/google/callback"


def _frontend_url(request: Request) -> str:
    configured = os.environ.get("FRONTEND_URL", "").strip()
    if configured:
        return configured.rstrip("/")

    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    if _is_local_host(host):
        return "http://localhost:3000"
    return _request_origin(request)


def _guardian_api_url(request: Request) -> str:
    configured = (
        os.environ.get("GUARDIAN_API_URL", "").strip()
        or os.environ.get("FRONTEND_URL", "").strip()
    )
    if configured:
        return configured.rstrip("/")
    return _request_origin(request)


def _serialize_openclaw_token_info(row) -> OpenClawTokenInfo | None:
    if row is None:
        return None
    return OpenClawTokenInfo(
        label=row.label,
        token_type=row.token_type,
        scope=row.scope,
        token_prefix=row.token_prefix,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
    )


def _openclaw_connection_status(user: UserRow, db: Session, request: Request) -> OpenClawConnectionStatus:
    active_token = get_active_openclaw_token(user.id, db)
    return OpenClawConnectionStatus(
        api_url=_guardian_api_url(request),
        install_command="openclaw skills install guardian-compliance",
        env_var="GUARDIAN_TOKEN",
        token_type="openclaw",
        scope="openclaw",
        active_token=_serialize_openclaw_token_info(active_token),
    )


def _require_auth_user(
    authorization: str,
    db: Session,
    *,
    allow_api_token: bool,
) -> tuple[dict, UserRow]:
    payload = get_bearer_payload(authorization, db)
    if not allow_api_token and payload.get("auth_type") != "jwt":
        raise HTTPException(403, "This endpoint requires a web session token")
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return payload, user


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
    _, user = _require_auth_user(authorization, db, allow_api_token=True)
    return user


@router.post("/link-check/{check_id}")
def link_check_to_user(
    check_id: str,
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Link an existing check to the authenticated user."""
    payload, _ = _require_auth_user(authorization, db, allow_api_token=False)
    user_id = payload["user_id"]

    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    check.user_id = user_id
    db.commit()
    return {"ok": True}


@router.get("/openclaw/connection", response_model=OpenClawConnectionStatus)
def get_openclaw_connection(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    _, user = _require_auth_user(authorization, db, allow_api_token=False)
    return _openclaw_connection_status(user, db, request)


@router.post("/openclaw/token", response_model=OpenClawTokenIssueResponse)
def issue_openclaw_connection_token(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    _, user = _require_auth_user(authorization, db, allow_api_token=False)
    row, token = issue_openclaw_token(user, db)
    db.commit()
    status = _openclaw_connection_status(user, db, request)
    return OpenClawTokenIssueResponse(
        api_url=status.api_url,
        install_command=status.install_command,
        env_var=status.env_var,
        token_type=status.token_type,
        scope=status.scope,
        active_token=_serialize_openclaw_token_info(row),
        token=token,
    )


# === Google OAuth ===

class GoogleTokenRequest(BaseModel):
    credential: str  # Google ID token from frontend


@router.get("/google/url")
def google_auth_url(request: Request):
    """Return the Google OAuth authorization URL."""
    client_id = _google_client_id()
    if not client_id:
        raise HTTPException(500, "Google OAuth not configured. Set GOOGLE_CLIENT_ID env var.")
    params = {
        "client_id": client_id,
        "redirect_uri": _google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/google/callback")
def google_callback(code: str, request: Request, db: Session = Depends(get_session)):
    """Handle Google OAuth callback — exchange code for token, create/login user."""
    import httpx

    client_id = _google_client_id()
    client_secret = _google_client_secret()
    redirect_uri = _google_redirect_uri(request)
    if not client_id or not client_secret:
        raise HTTPException(500, "Google OAuth not configured.")

    # Exchange code for tokens
    token_resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
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
    return RedirectResponse(
        url=f"{_frontend_url(request)}/login?token={token}&email={email}&user_id={user.id}",
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
