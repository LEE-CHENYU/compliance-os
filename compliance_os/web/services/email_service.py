"""Transactional email helpers for marketplace flows."""

from __future__ import annotations

import base64
import html
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


def _steps_html(steps: list[str]) -> str:
    if not steps:
        return ""
    return "<ol>" + "".join(f"<li>{html.escape(step)}</li>" for step in steps) + "</ol>"


def _send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    attachments: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    from_email = (os.environ.get("RESEND_FROM_EMAIL") or "Guardian <hello@guardiancompliance.app>").strip()
    if not api_key:
        return {"status": "skipped", "reason": "missing_resend_api_key"}

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    if attachments:
        payload["attachments"] = attachments

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


def send_form_8843_welcome(
    to_email: str,
    full_name: str,
    pdf_bytes: bytes,
    filing_context: dict[str, object] | None = None,
) -> dict[str, str]:
    """Send the generated Form 8843 as an email attachment when Resend is configured."""
    next_context = filing_context or {}
    address_block = str(next_context.get("address_block", "") or "").strip()
    address_block_html = "<br/>".join(html.escape(line) for line in address_block.splitlines()) if address_block else ""
    filing_deadline = str(next_context.get("deadline_label", "") or "")
    filing_summary = html.escape(str(next_context.get("summary", "") or ""))
    steps = [str(step) for step in next_context.get("steps", []) if str(step).strip()]
    return _send_email(
        to_email=to_email,
        subject="Your Form 8843 is ready",
        html_body=_render_template(
            "form_8843_welcome.html",
            {
                "full_name": html.escape(full_name),
                "filing_summary": filing_summary,
                "filing_deadline": html.escape(filing_deadline),
                "address_block": address_block_html,
                "filing_steps": _steps_html(steps),
            },
        ),
        attachments=[
            {
                "filename": "Form_8843.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ],
    )


def send_marketplace_delivery_email(
    to_email: str,
    *,
    full_name: str,
    product_name: str,
    summary: str,
    next_steps: list[str] | None = None,
    filing_deadline: str | None = None,
) -> dict[str, str]:
    body = [
        f"<p>Hi {html.escape(full_name or to_email)},</p>",
        f"<p>Your <strong>{html.escape(product_name)}</strong> result is ready in Guardian.</p>",
        f"<p>{html.escape(summary)}</p>",
    ]
    if filing_deadline:
        body.append(f"<p><strong>Deadline:</strong> {html.escape(filing_deadline)}</p>")
    if next_steps:
        body.append(_steps_html(next_steps))
    body.append("<p>Open your order dashboard to review the result, download artifacts, and complete any remaining filing steps.</p>")
    body.append("<p>Guardian</p>")
    return _send_email(
        to_email=to_email,
        subject=f"Your {product_name} result is ready",
        html_body="".join(body),
    )


def send_attorney_assignment_email(
    to_email: str,
    *,
    attorney_name: str,
    client_name: str,
    product_name: str,
) -> dict[str, str]:
    return _send_email(
        to_email=to_email,
        subject=f"New Guardian case assigned: {product_name}",
        html_body=(
            f"<p>Hi {html.escape(attorney_name or to_email)},</p>"
            f"<p>A new Guardian case has been assigned to you.</p>"
            f"<p><strong>Client:</strong> {html.escape(client_name)}</p>"
            f"<p><strong>Service:</strong> {html.escape(product_name)}</p>"
            "<p>Open the attorney dashboard to review the checklist and filing packet.</p>"
        ),
    )


def send_attorney_decision_email(
    to_email: str,
    *,
    full_name: str,
    product_name: str,
    decision: str,
    notes: str | None = None,
) -> dict[str, str]:
    decision_copy = "approved for filing" if decision == "approve" else "flagged for advisory upgrade"
    body = [
        f"<p>Hi {html.escape(full_name or to_email)},</p>",
        f"<p>Your <strong>{html.escape(product_name)}</strong> order was {decision_copy}.</p>",
    ]
    if notes:
        body.append(f"<p><strong>Attorney note:</strong> {html.escape(notes)}</p>")
    body.append("<p>Open your Guardian order to review the latest status and next steps.</p>")
    return _send_email(
        to_email=to_email,
        subject=f"Update on your {product_name} order",
        html_body="".join(body),
    )


def send_upgrade_flag_email(
    to_email: str,
    *,
    full_name: str,
    product_name: str,
    reason: str,
    credit_cents: int,
) -> dict[str, str]:
    return _send_email(
        to_email=to_email,
        subject=f"Action needed: {product_name} needs Advisory Mode",
        html_body=(
            f"<p>Hi {html.escape(full_name or to_email)},</p>"
            f"<p>Your <strong>{html.escape(product_name)}</strong> order was flagged for Advisory Mode before filing.</p>"
            f"<p><strong>Why:</strong> {html.escape(reason)}</p>"
            f"<p>Guardian recorded a ${credit_cents / 100:,.0f} execution credit on the upgrade recommendation. "
            "Open the order in Guardian to continue into the advisory lane.</p>"
        ),
    )


def send_filing_confirmation_email(
    to_email: str,
    *,
    full_name: str,
    product_name: str,
    receipt_number: str,
    filing_confirmation: str | None = None,
) -> dict[str, str]:
    body = [
        f"<p>Hi {html.escape(full_name or to_email)},</p>",
        f"<p>Your <strong>{html.escape(product_name)}</strong> filing has been recorded.</p>",
        f"<p><strong>Receipt number:</strong> {html.escape(receipt_number)}</p>",
    ]
    if filing_confirmation:
        body.append(f"<p>{html.escape(filing_confirmation)}</p>")
    body.append("<p>You can view the filing record and any artifacts in your Guardian order history.</p>")
    return _send_email(
        to_email=to_email,
        subject=f"Filing confirmation for {product_name}",
        html_body="".join(body),
    )
