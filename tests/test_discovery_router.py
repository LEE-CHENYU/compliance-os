"""Test discovery and chat API endpoints."""


def test_save_and_get_answers(client, case_id):
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "concern_area", "question_key": "concern_area", "answer": ["Tax Filing"],
    })
    resp = client.get(f"/api/cases/{case_id}/discovery")
    assert resp.status_code == 200
    assert len(resp.json()["answers"]) == 1
    assert resp.json()["answers"][0]["answer"] == ["Tax Filing"]


def test_upsert_answer(client, case_id):
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "concern_area", "question_key": "concern_area", "answer": ["Tax Filing"],
    })
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "concern_area", "question_key": "concern_area", "answer": ["Immigration"],
    })
    resp = client.get(f"/api/cases/{case_id}/discovery")
    assert len(resp.json()["answers"]) == 1
    assert resp.json()["answers"][0]["answer"] == ["Immigration"]


def test_generate_summary_updates_status(client, case_id):
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "concern_area", "question_key": "concern_area", "answer": ["Tax Filing"],
    })
    resp = client.post(f"/api/cases/{case_id}/discovery/summary")
    assert resp.status_code == 200
    assert "concern_area" in resp.json()["summary"]
    # Check status updated
    case_resp = client.get(f"/api/cases/{case_id}")
    assert case_resp.json()["status"] == "documents"


def test_chat_generates_followups(client, case_id):
    # Save answers that trigger follow-up rules
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "residency_status", "question_key": "residency_status", "answer": "F-1",
    })
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "prior_filings", "question_key": "prior_filings", "answer": ["1040"],
    })
    resp = client.get(f"/api/cases/{case_id}/chat")
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert len(messages) >= 1
    assert messages[0]["role"] == "assistant"


def test_send_chat_message(client, case_id):
    resp = client.post(f"/api/cases/{case_id}/chat", json={"content": "My CPA filed it"})
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert any(m["role"] == "user" and m["content"] == "My CPA filed it" for m in messages)
