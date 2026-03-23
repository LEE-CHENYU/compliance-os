"""Test case CRUD API endpoints."""


def test_create_case(client):
    resp = client.post("/api/cases", json={"workflow_type": "tax"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow_type"] == "tax"
    assert data["status"] == "discovery"
    assert "id" in data


def test_list_cases(client):
    client.post("/api/cases", json={"workflow_type": "tax"})
    client.post("/api/cases", json={"workflow_type": "immigration"})
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    assert len(resp.json()["cases"]) == 2


def test_get_case(client, case_id):
    resp = client.get(f"/api/cases/{case_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == case_id


def test_get_missing_case(client):
    resp = client.get("/api/cases/nonexistent")
    assert resp.status_code == 404
