"""Transactional email helpers for marketplace flows."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from urllib import error, request


EMAIL_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "emails"
RESEND_API_URL = "https://api.resend.com/emails"


def _render_template(name: str, context: dict[str, str]) -> str:
    template_path = EMAIL_TEMPLATE_DIR / name
    if template_path.exists():
        content = template_path.read_text(encoding="utf-8")
    else:
        content = (
            "<p>Hi {{full_name}},</p>"
            "<p>Your Form 8843 is ready. The PDF is attached to this email.</p>"
            "<p>Guardian</p>"
        )
    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def send_form_8843_welcome(to_email: str, full_name: str, pdf_bytes: bytes) -> dict[str, str]:
    """Send the generated Form 8843 as an email attachment when Resend is configured."""
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    from_email = (os.environ.get("RESEND_FROM_EMAIL") or "Guardian <hello@guardiancompliance.app>").strip()

    if not api_key:
        return {"status": "skipped", "reason": "missing_resend_api_key"}

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": "Your Form 8843 is ready",
        "html": _render_template("form_8843_welcome.html", {"full_name": full_name}),
        "attachments": [
            {
                "filename": "Form_8843.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ],
    }

    req = request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8") or "{}")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "reason": f"http_{exc.code}:{detail}"}
    except Exception as exc:  # pragma: no cover - network failures vary by environment
        return {"status": "error", "reason": str(exc)}

    return {"status": "sent", "id": str(body.get("id", ""))}
