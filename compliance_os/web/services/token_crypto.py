"""Symmetric encryption for OAuth refresh tokens stored at rest.

Derives a Fernet key from `JWT_SECRET` so deployments don't need a new
secret to manage. Trade-off: anyone with read access to both env vars
and the DB can decrypt — same blast radius as session JWTs.

Rotate to a dedicated env var or cloud KMS when serious prod hits.
"""
from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


def _derive_key() -> bytes:
    """Deterministically derive a Fernet key from JWT_SECRET.

    Same secret → same key, so encrypted tokens persist across restarts.
    Changing JWT_SECRET invalidates every stored Gmail token (acceptable —
    blast radius matches session JWTs).
    """
    secret = os.environ.get(
        "JWT_SECRET", "guardian-dev-secret-change-in-production"
    ).encode()
    digest = hashlib.sha256(secret + b":gmail-token-encryption").digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(_derive_key())


def encrypt_token(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Likely cause: JWT_SECRET was rotated since this token was stored.
        # Caller should treat this as "not connected" and prompt re-auth.
        return ""
