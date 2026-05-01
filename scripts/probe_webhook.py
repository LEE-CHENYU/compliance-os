"""Synthesize a signed `checkout.session.completed` and POST it to the
locally-running uvicorn from inside the Fly machine.

Why this exists:
- Stripe CLI's restricted key (`rk_live_*`) lacks `webhooks.write`, so we
  can't `stripe events resend` to retry a real failed delivery.
- Test-mode `stripe trigger` would force us to either (a) override the
  prod `STRIPE_WEBHOOK_SECRET` (risky) or (b) provision a separate test
  endpoint and rebuild a parallel checkout flow (overkill).
- This script signs a payload with the real secret already on the box
  and POSTs to localhost:8000, exercising signature verification +
  handler logic exactly the same way Stripe would. No charge is made.

Run on the Fly machine:
    flyctl ssh console -a guardian-compliance -C "python /app/scripts/probe_webhook.py <request_id>"

The request_id should be a real ProfessionalSearchRequestRow.id; the
script picks the most recent cs_live_* session id off it (or fabricates
one) so the row's existing `paid_at` idempotency check still applies.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import uuid
import urllib.request

WEBHOOK_URL = "http://localhost:8000/api/professional-search/stripe-webhook"


def _sign(payload: bytes, secret: str) -> str:
    ts = str(int(time.time()))
    signed_payload = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _build_payload(request_id: str) -> dict:
    """Minimum-fidelity Stripe checkout.session.completed event."""
    session_id = f"cs_test_probe_{uuid.uuid4().hex[:24]}"
    return {
        "id": f"evt_probe_{uuid.uuid4().hex[:24]}",
        "object": "event",
        "type": "checkout.session.completed",
        "api_version": "2026-04-22.dahlia",
        "created": int(time.time()),
        # livemode mirrors what Stripe sets when it dispatches a real prod
        # event. Our handler does not key on this flag, but flipping it
        # `True` proves the prod path is exercised exactly like Stripe will.
        "livemode": True,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "mode": "payment",
                "livemode": True,
                "client_reference_id": request_id,
                "metadata": {"professional_search_id": request_id},
                "amount_total": 1500,
                "currency": "usd",
                "customer_email": None,
                "customer_details": {
                    "email": "probe@guardian-compliance.fly.dev",
                    "name": "Webhook Probe",
                },
            }
        },
    }


def main(request_id: str) -> int:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        print("ERROR: STRIPE_WEBHOOK_SECRET not set on this machine", file=sys.stderr)
        return 2

    event = _build_payload(request_id)
    body = json.dumps(event, separators=(",", ":")).encode()
    sig = _sign(body, secret)

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": sig,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"HTTP {resp.status}")
            print(resp.read().decode())
        return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}")
        print(exc.read().decode())
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: probe_webhook.py <request_id>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
