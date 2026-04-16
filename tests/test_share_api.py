"""End-to-end tests for the data-room share API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from compliance_os.web.app import app
from compliance_os.web.services.share_tokens import create_share_token

KLASKO = Path("/Users/lichenyu/accounting/outgoing/klasko/upload_041626")

client = TestClient(app)


@pytest.fixture
def token() -> str:
    if not KLASKO.is_dir():
        pytest.skip("Klasko reference package not available")
    return create_share_token(
        folder=str(KLASKO),
        template_id="h1b_petition",
        recipient="Elise Fialkowski",
        issuer="chenyu@guardian",
    )


class TestShareAPI:
    def test_get_share_returns_structured_data(self, token):
        r = client.get(f"/api/share/{token}")
        assert r.status_code == 200
        data = r.json()
        assert data["template_name"] == "H-1B Petition Package"
        assert data["recipient"] == "Elise Fialkowski"
        assert data["files_scanned"] > 40
        assert len(data["sections"]) == 7
        # Coverage shape
        assert set(data["coverage"].keys()) == {"A", "B", "C", "D", "E", "F", "G"}
        # A section should have 11 slots (required+optional)
        a = next(s for s in data["sections"] if s["code"] == "A")
        assert len(a["slots"]) == 11

    def test_summary_has_key_facts(self, token):
        r = client.get(f"/api/share/{token}")
        summary = r.json()["summary"]
        labels = [f["label"] for f in summary["key_facts"]]
        assert "Petitioner" in labels or "Beneficiary" in labels
        # Timeline should have F-1 phases parsed
        assert len(summary["timeline"]) >= 3
        # Issues parsed from brief
        assert len(summary["issues"]) >= 3

    def test_file_endpoint_serves_matched_slot(self, token):
        r = client.get(f"/api/share/{token}/file/A1")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/")
        assert b"JFIF" in r.content or len(r.content) > 1000

    def test_file_endpoint_404_for_unknown_slot(self, token):
        r = client.get(f"/api/share/{token}/file/ZZ99")
        assert r.status_code == 404

    def test_invalid_token(self):
        r = client.get("/api/share/not-a-real-token")
        assert r.status_code == 401

    def test_expired_token(self):
        tok = create_share_token(
            folder=str(KLASKO),
            template_id="h1b_petition",
            expires_in_days=-1,
        )
        r = client.get(f"/api/share/{tok}")
        assert r.status_code == 410
