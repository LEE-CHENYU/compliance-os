"""Register, login, me, and Google OAuth endpoints."""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta
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
from compliance_os.web.models.marketplace import MarketplaceUserRow
from compliance_os.web.models.tables import GoogleOAuthTokenRow
from compliance_os.web.models.tables_v2 import CheckRow
from compliance_os.web.services.auth_service import (
    JWT_SECRET,
    create_token,
    get_active_openclaw_token,
    get_bearer_payload,
    hash_password,
    issue_openclaw_token,
    verify_password,
)
from compliance_os.web.services.token_crypto import decrypt_token, encrypt_token

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


def _safe_next_path(next_path: str | None) -> str | None:
    if not next_path:
        return None
    value = next_path.strip()
    if not value.startswith("/") or value.startswith("//"):
        return None
    return value


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


def _sync_marketplace_user(user: UserRow, db: Session) -> None:
    marketplace_user = (
        db.query(MarketplaceUserRow)
        .filter(MarketplaceUserRow.email == user.email)
        .first()
    )
    if marketplace_user is None:
        db.add(
            MarketplaceUserRow(
                email=user.email,
                source="direct",
                role=user.role or "user",
            )
        )
        db.flush()
        return

    marketplace_user.role = user.role or marketplace_user.role or "user"


def _auth_response_for_user(user: UserRow, db: Session) -> AuthResponse:
    _sync_marketplace_user(user, db)
    db.commit()
    db.refresh(user)
    token = create_token(user.id, user.email)
    return AuthResponse(token=token, user_id=user.id, email=user.email, role=user.role)


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_session)):
    existing = db.query(UserRow).filter(UserRow.email == body.email).first()
    if existing:
        raise HTTPException(409, "Email already registered")
    user = UserRow(email=body.email, password_hash=hash_password(body.password), role="user")
    db.add(user)
    db.flush()
    return _auth_response_for_user(user, db)


@router.post("/signup", response_model=AuthResponse)
def signup(body: RegisterRequest, db: Session = Depends(get_session)):
    return register(body, db)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_session)):
    user = db.query(UserRow).filter(UserRow.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return _auth_response_for_user(user, db)


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
def google_auth_url(request: Request, next: str | None = None):
    """Return the Google OAuth authorization URL."""
    client_id = _google_client_id()
    if not client_id:
        raise HTTPException(500, "Google OAuth not configured. Set GOOGLE_CLIENT_ID env var.")
    next_path = _safe_next_path(next)
    params = {
        "client_id": client_id,
        "redirect_uri": _google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    if next_path:
        params["state"] = next_path
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/google/callback")
def google_callback(
    code: str,
    request: Request,
    state: str | None = None,
    db: Session = Depends(get_session),
):
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
            role="user",
        )
        db.add(user)
        db.flush()

    _sync_marketplace_user(user, db)
    db.commit()
    db.refresh(user)

    # Create JWT
    token = create_token(user.id, user.email)

    # Redirect to frontend with token in URL fragment
    query = {
        "token": token,
        "email": email,
        "user_id": user.id,
        "role": user.role,
    }
    next_path = _safe_next_path(state)
    if next_path:
        query["next"] = next_path
    return RedirectResponse(url=f"{_frontend_url(request)}/login?{urlencode(query)}")


# --- Gmail connection (separate flow from sign-in) ---
#
# Sign-in uses minimal scopes (openid+email+profile). The user opts into
# Gmail access via a *second* OAuth round-trip after they're already
# logged in — keeps the trust ask narrow and lets users decline Gmail
# without losing their account.
#
# State is a short-lived JWT keyed off the user's session, so the callback
# can verify the connection belongs to the right account without trusting
# anything from the URL.

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _gmail_callback_uri(request: Request) -> str:
    return _request_origin(request) + "/api/auth/google/connect-gmail/callback"


@router.get("/google/connect-gmail/url")
def google_connect_gmail_url(
    request: Request,
    next: str | None = None,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """Return the Google OAuth URL for granting Gmail read access.

    Requires the user to already be signed in (Authorization: Bearer).
    The `next` query param controls where the user lands post-callback.
    """
    payload = get_bearer_payload(authorization, db)
    user_id = payload["user_id"]

    client_id = _google_client_id()
    if not client_id:
        raise HTTPException(500, "Google OAuth not configured. Set GOOGLE_CLIENT_ID env var.")

    import jwt as pyjwt
    state_payload = {
        "user_id": user_id,
        "purpose": "connect_gmail",
        "next": _safe_next_path(next) or "/dashboard",
        "exp": int(time.time()) + 600,  # 10-min OAuth window
    }
    state = pyjwt.encode(state_payload, JWT_SECRET, algorithm="HS256")

    params = {
        "client_id": client_id,
        "redirect_uri": _gmail_callback_uri(request),
        "response_type": "code",
        # Request the full scope set so Google honors `prompt=consent` and
        # actually returns a refresh_token. Incremental auth would skip
        # already-granted scopes, but we need consent to refresh-token.
        "scope": f"openid email profile {GMAIL_READONLY_SCOPE}",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    }
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/google/connect-gmail/callback")
def google_connect_gmail_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_session),
):
    """Handle the Gmail-connect callback — store encrypted tokens, redirect."""
    import httpx
    import jwt as pyjwt

    frontend = _frontend_url(request)
    fallback_path = "/dashboard"
    next_path = fallback_path

    try:
        state_payload = pyjwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        if state_payload.get("purpose") != "connect_gmail":
            raise ValueError("bad purpose")
        user_id = str(state_payload["user_id"])
        next_path = _safe_next_path(state_payload.get("next")) or fallback_path
    except Exception:
        return RedirectResponse(url=f"{frontend}{fallback_path}?gmail=invalid_state")

    user = db.query(UserRow).filter(UserRow.id == user_id).first()
    if not user:
        return RedirectResponse(url=f"{frontend}{next_path}?gmail=user_not_found")

    client_id = _google_client_id()
    client_secret = _google_client_secret()
    redirect_uri = _gmail_callback_uri(request)
    if not client_id or not client_secret:
        return RedirectResponse(url=f"{frontend}{next_path}?gmail=not_configured")

    try:
        token_resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15.0,
        )
    except Exception:
        return RedirectResponse(url=f"{frontend}{next_path}?gmail=network_error")

    if token_resp.status_code != 200:
        return RedirectResponse(url=f"{frontend}{next_path}?gmail=token_exchange_failed")

    tokens = token_resp.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token or not refresh_token:
        # Without a refresh_token we can't keep syncing past the access
        # token's 1-hour life. Most often this means the user already
        # granted in the past; have them revoke at myaccount.google.com.
        return RedirectResponse(url=f"{frontend}{next_path}?gmail=no_refresh_token")

    expires_in = int(tokens.get("expires_in", 3600))
    scope = tokens.get("scope", "")
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    existing = (
        db.query(GoogleOAuthTokenRow)
        .filter(GoogleOAuthTokenRow.user_id == user_id)
        .first()
    )
    if existing is not None:
        existing.access_token_encrypted = encrypt_token(access_token)
        existing.refresh_token_encrypted = encrypt_token(refresh_token)
        existing.scope = scope
        existing.expires_at = expires_at
        existing.granted_at = datetime.utcnow()
        existing.revoked_at = None
    else:
        db.add(GoogleOAuthTokenRow(
            user_id=user_id,
            access_token_encrypted=encrypt_token(access_token),
            refresh_token_encrypted=encrypt_token(refresh_token),
            scope=scope,
            expires_at=expires_at,
            granted_at=datetime.utcnow(),
        ))
    db.commit()

    return RedirectResponse(url=f"{frontend}{next_path}?gmail=connected")


@router.get("/me/gmail/status")
def gmail_status(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """Whether the signed-in user has connected Gmail (and the granted scope)."""
    payload = get_bearer_payload(authorization, db)
    row = (
        db.query(GoogleOAuthTokenRow)
        .filter(GoogleOAuthTokenRow.user_id == payload["user_id"])
        .first()
    )
    if row is None or row.revoked_at is not None:
        return {"connected": False}
    return {
        "connected": True,
        "scope": row.scope,
        "granted_at": row.granted_at.isoformat() if row.granted_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


@router.post("/me/gmail/sync")
def gmail_sync(
    force: bool = False,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """Trigger an on-demand Gmail sync for the signed-in user.

    Returns counts + last_synced_at. Synchronous: blocks until Gmail
    queries complete (~5-15s for 100 messages). The frontend can show a
    spinner; debounced server-side so page-load triggers don't hammer.

    Set `?force=true` to bypass the debounce (used by the manual button).
    """
    payload = get_bearer_payload(authorization, db)
    from compliance_os.web.services.gmail_sync import sync_user_gmail, GmailSyncError
    try:
        result = sync_user_gmail(db, payload["user_id"], force=force)
    except GmailSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/me/gmail/disconnect")
def gmail_disconnect(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """Revoke the Gmail token at Google + delete the row locally.

    Best-effort revoke: even if Google's revoke endpoint fails (e.g. the
    refresh token is already invalid), we still delete the local row so
    the user is fully disconnected from our side.
    """
    import httpx
    payload = get_bearer_payload(authorization, db)
    row = (
        db.query(GoogleOAuthTokenRow)
        .filter(GoogleOAuthTokenRow.user_id == payload["user_id"])
        .first()
    )
    if row is None:
        return {"ok": True, "already_disconnected": True}

    try:
        refresh = decrypt_token(row.refresh_token_encrypted)
        if refresh:
            httpx.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": refresh},
                timeout=5.0,
            )
    except Exception:
        pass  # local delete is the source of truth

    db.delete(row)
    db.commit()
    return {"ok": True}


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
            role="user",
        )
        db.add(user)
        db.flush()

    return _auth_response_for_user(user, db)
