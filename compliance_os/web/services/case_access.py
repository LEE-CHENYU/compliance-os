"""Per-user scoping for case-bound endpoints.

Used by every router that loads a `CaseRow` from a URL path param —
cases, discovery, documents, and the Gmail sync — to ensure one user
can't access another user's case by guessing a UUID.

The model accepts both authenticated and anonymous callers because the
discovery wizard can run without sign-up: cases created without a
session have `user_id IS NULL` and remain accessible via direct URL
until an authenticated user touches them, at which point they're
*claimed* (user_id set). After claim, only that user can see the case.

Auth is intentionally optional everywhere this is called — sending a
401 to an anonymous user mid-discovery would break a flow we want to
keep frictionless.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from compliance_os.web.models.tables import CaseRow
from compliance_os.web.services.auth_service import get_bearer_payload


def maybe_user_id(authorization: str | None, db: Session) -> str | None:
    """Return the user_id from the bearer token, or None if no/invalid token.

    Never raises — soft-auth: missing or invalid tokens read as anonymous,
    which is what every case-bound endpoint expects.
    """
    if not authorization:
        return None
    try:
        payload = get_bearer_payload(authorization, db)
    except HTTPException:
        return None
    return payload.get("user_id")


def get_case_for_user(
    case_id: str,
    user_id: str | None,
    session: Session,
    *,
    claim: bool = True,
) -> CaseRow:
    """Look up a case scoped to the (possibly anonymous) caller.

    Rules:
    - case not found → 404
    - case.user_id is None and caller is anonymous → allow (anon flow)
    - case.user_id is None and caller is authenticated → allow + CLAIM
      (commits user_id = caller, then anonymous URLs lose access)
    - case.user_id == caller → allow
    - case.user_id is set and caller doesn't match → 404 (don't leak
      existence with 403)

    `claim=False` skips the auto-claim — useful for read-only paths
    where mutating the row on a GET would be surprising.
    """
    case = session.get(CaseRow, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    if case.user_id is None:
        if user_id is not None and claim:
            case.user_id = user_id
            session.commit()
        return case

    if user_id is not None and case.user_id == user_id:
        return case

    # 404 over 403 — don't tell strangers a case exists with this UUID.
    raise HTTPException(status_code=404, detail="Case not found")
