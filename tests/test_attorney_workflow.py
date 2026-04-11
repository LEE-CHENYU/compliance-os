"""Integration tests for the first attorney-backed marketplace workflow."""

from __future__ import annotations

from compliance_os.web.models import database
from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.marketplace import AttorneyRow
from compliance_os.web.services.auth_service import create_token, hash_password


def _user_headers(client, email: str) -> dict[str, str]:
    response = client.post("/api/auth/signup", json={"email": email, "password": "secure123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _attorney_headers(email: str = "attorney@example.com") -> dict[str, str]:
    session = database._SessionLocal()
    try:
        user = UserRow(email=email, password_hash=hash_password("secure123"), role="attorney")
        session.add(user)
        session.flush()
        session.add(
            AttorneyRow(
                full_name="Casey Counsel",
                email=email,
                bar_state="NY",
                bar_number="A1234567",
                active=True,
                bar_verified=True,
            )
        )
        session.commit()
        return {"Authorization": f"Bearer {create_token(user.id, user.email)}"}
    finally:
        session.close()


def _opt_responses() -> list[dict[str, object]]:
    return [
        {"item_id": "f1_good_standing", "checked": True},
        {"item_id": "full_time_enrolled", "checked": True},
        {"item_id": "employment_plan", "checked": True},
        {"item_id": "school_confirmed_eligible", "checked": True},
        {"item_id": "has_i20", "checked": True},
        {"item_id": "has_passport", "checked": True},
        {"item_id": "has_photos", "checked": True},
        {"item_id": "denied_before", "checked": False},
        {"item_id": "prior_rfe", "checked": False},
        {"item_id": "unauthorized_employment", "checked": False},
        {"item_id": "late_application", "checked": False},
    ]


def _disable_attorney_emails(monkeypatch) -> None:
    import compliance_os.web.routers.attorney as attorney_mod
    import compliance_os.web.routers.marketplace as marketplace_mod

    monkeypatch.setattr(
        marketplace_mod,
        "send_attorney_assignment_email",
        lambda *args, **kwargs: {"status": "skipped"},
    )
    monkeypatch.setattr(
        attorney_mod,
        "send_attorney_decision_email",
        lambda *args, **kwargs: {"status": "skipped"},
    )
    monkeypatch.setattr(
        attorney_mod,
        "send_upgrade_flag_email",
        lambda *args, **kwargs: {"status": "skipped"},
    )
    monkeypatch.setattr(
        attorney_mod,
        "send_filing_confirmation_email",
        lambda *args, **kwargs: {"status": "skipped"},
    )


def _create_opt_execution_order(client, user_headers: dict[str, str]) -> str:
    questionnaire_response = client.post(
        "/api/marketplace/products/opt_execution/questionnaire",
        headers=user_headers,
        json={"responses": _opt_responses()},
    )
    assert questionnaire_response.status_code == 200
    questionnaire_body = questionnaire_response.json()
    assert questionnaire_body["recommendation"] == "execution"

    order_response = client.post(
        "/api/marketplace/orders",
        headers=user_headers,
        json={
            "sku": "opt_execution",
            "questionnaire_response_id": questionnaire_body["questionnaire_response_id"],
            "chosen_mode": "execution",
        },
    )
    assert order_response.status_code == 200
    order_body = order_response.json()
    order_id = order_body["order_id"]
    assert order_body["product_sku"] == "opt_execution"
    assert order_body["intake_complete"] is False

    intake_response = client.post(
        f"/api/marketplace/orders/{order_id}/intake",
        headers=user_headers,
        data={
            "desired_start_date": "2026-07-01",
            "employment_plan_text": "Software engineer role aligned with computer science degree.",
        },
        files=[
            ("passport_file", ("passport.txt", b"Passport for Opt User", "text/plain")),
            ("i20_file", ("i20.txt", b"I-20 with OPT recommendation", "text/plain")),
        ],
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["intake_complete"] is True

    agreement_response = client.get(
        f"/api/marketplace/orders/{order_id}/agreement",
        headers=user_headers,
    )
    assert agreement_response.status_code == 200
    agreement_text = agreement_response.json()["agreement_text"]
    assert "LIMITED SCOPE REPRESENTATION AGREEMENT" in agreement_text

    sign_response = client.post(
        f"/api/marketplace/orders/{order_id}/sign-agreement",
        headers=user_headers,
        json={
            "signature": "Opt User",
            "agreement_text_snapshot": agreement_text,
        },
    )
    assert sign_response.status_code == 200
    sign_body = sign_response.json()
    assert sign_body["order"]["status"] == "attorney_review"
    assert sign_body["attorney_assignment"]["decision"] == "pending"
    return order_id


def test_opt_execution_questionnaire_and_attorney_flow(client, monkeypatch, tmp_path):
    import compliance_os.web.services.attorney_workflow as workflow_mod

    monkeypatch.setattr(workflow_mod, "ATTORNEY_ARTIFACT_DIR", tmp_path / "attorney")
    _disable_attorney_emails(monkeypatch)

    user_headers = _user_headers(client, "opt-user@example.com")
    attorney_headers = _attorney_headers()
    order_id = _create_opt_execution_order(client, user_headers)

    dashboard_response = client.get("/api/attorney/dashboard", headers=attorney_headers)
    assert dashboard_response.status_code == 200
    dashboard_body = dashboard_response.json()
    assert dashboard_body["stats"]["pending_review"] == 1
    assert dashboard_body["pending_cases"][0]["order_id"] == order_id

    case_response = client.get(f"/api/attorney/cases/{order_id}", headers=attorney_headers)
    assert case_response.status_code == 200
    case_body = case_response.json()
    assert case_body["order"]["product_sku"] == "opt_execution"
    assert case_body["checklist"]["service"] == "opt_execution"

    review_response = client.post(
        f"/api/attorney/cases/{order_id}/review",
        headers=attorney_headers,
        json={
            "decision": "approve",
            "notes": "Looks clean.",
            "checklist_responses": {
                "passport_match": True,
                "i20_valid": True,
                "employment_plan": True,
                "timing_ok": True,
                "no_prior_denials": True,
                "no_unauthorized_work": True,
                "photos_valid": True,
                "fee_payment_ready": True,
            },
        },
    )
    assert review_response.status_code == 200
    assert review_response.json()["next_action"] == "ready_to_file"
    review_body = review_response.json()
    assert review_body["order"]["result"]["artifacts"]
    assert review_body["order"]["result"]["notification_statuses"]["attorney_review_email"]["status"] == "skipped"

    file_response = client.post(
        f"/api/attorney/cases/{order_id}/file",
        headers=attorney_headers,
        json={
            "receipt_number": "IOE1234567890",
            "filing_confirmation": "Filed via MyUSCIS",
        },
    )
    assert file_response.status_code == 200
    assert file_response.json()["receipt_number"] == "IOE1234567890"
    assert file_response.json()["order"]["result"]["notification_statuses"]["filing_confirmation_email"]["status"] == "skipped"

    updated_order_response = client.get(
        f"/api/marketplace/orders/{order_id}",
        headers=user_headers,
    )
    assert updated_order_response.status_code == 200
    updated_order = updated_order_response.json()
    assert updated_order["status"] == "completed"
    assert updated_order["result"]["summary"]
    assert any("G-28" in artifact["label"] for artifact in updated_order["result"]["artifacts"])
    assert any("filing confirmation" in artifact["label"].lower() for artifact in updated_order["result"]["artifacts"])


def test_opt_execution_flag_upgrade_creates_advisory_order(client, monkeypatch, tmp_path):
    import compliance_os.web.services.attorney_workflow as workflow_mod

    monkeypatch.setattr(workflow_mod, "ATTORNEY_ARTIFACT_DIR", tmp_path / "attorney")
    _disable_attorney_emails(monkeypatch)

    user_headers = _user_headers(client, "opt-flagged@example.com")
    attorney_headers = _attorney_headers("flag-attorney@example.com")
    order_id = _create_opt_execution_order(client, user_headers)

    review_response = client.post(
        f"/api/attorney/cases/{order_id}/review",
        headers=attorney_headers,
        json={
            "decision": "flag_upgrade",
            "notes": "Prior status history needs legal strategy review before filing.",
            "checklist_responses": {
                "passport_match": True,
                "i20_valid": True,
                "employment_plan": True,
                "timing_ok": False,
            },
        },
    )
    assert review_response.status_code == 200
    review_body = review_response.json()
    assert review_body["next_action"] == "offer_advisory_upgrade"
    assert review_body["order"]["status"] == "flagged"
    assert review_body["order"]["result"]["upgrade_offer"]["target_sku"] == "opt_advisory"
    assert review_body["order"]["result"]["notification_statuses"]["upgrade_flag_email"]["status"] == "skipped"

    accept_response = client.post(
        f"/api/marketplace/orders/{order_id}/accept-upgrade",
        headers=user_headers,
    )
    assert accept_response.status_code == 200
    accept_body = accept_response.json()
    assert accept_body["accepted"] is True
    assert accept_body["upgraded_order"]["product_sku"] == "opt_advisory"
    assert accept_body["upgraded_order"]["status"] == "agreement_pending"
    assert accept_body["upgraded_order"]["intake_complete"] is True
    assert accept_body["original_order"]["result"]["upgrade_offer"]["accepted_order_id"] == accept_body["upgraded_order"]["order_id"]
