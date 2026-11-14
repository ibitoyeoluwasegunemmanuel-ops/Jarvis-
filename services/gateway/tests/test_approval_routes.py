from fastapi.testclient import TestClient

from app.main import app
from app.owner_auth import setup_owner
from app.workspace_store import create_project


def test_approval_routes_require_gateway_and_owner_sessions(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-token-123456789")
    owner_token = setup_owner("correct-horse-battery-7")
    project = create_project("Approval API Test")
    client = TestClient(app)

    unauthenticated = client.get(f"/v1/approvals/{project['id']}")
    assert unauthenticated.status_code == 401

    headers = {
        "X-Jarvis-Session": "test-gateway-session-token-123456789",
        "X-Jarvis-Owner-Session": owner_token,
    }
    created = client.post(
        "/v1/approvals",
        headers=headers,
        json={
            "project_id": project["id"],
            "action": "browser.navigate",
            "arguments": {"url": "https://example.com"},
            "ttl_seconds": 300,
        },
    )
    assert created.status_code == 201
    approval = created.json()
    assert approval["status"] == "pending"
    assert approval["nonce"]

    history = client.get(f"/v1/approvals/{project['id']}", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["id"] == approval["id"]
    assert "nonce" not in history.json()[0]

    decision = client.post(
        f"/v1/approvals/{approval['id']}/decision",
        headers=headers,
        json={"approve": True},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    replay = client.post(
        f"/v1/approvals/{approval['id']}/decision",
        headers=headers,
        json={"approve": True},
    )
    assert replay.status_code == 409
